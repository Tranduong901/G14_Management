import math
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncMonth

from catalog.models import Product
from sales.models import SalesOrderDetail, OrderStatus
from scm.models import PurchaseRequestDetail, PurchaseRequestStatus
from dss.models import ForecastResult

def get_monthly_sales_history(product, num_months=6):
    """
    Returns monthly sales history for a product from completed sales orders.
    Returns: list of (YYYY-MM, quantity) sorted chronologically.
    """
    sales = (
        SalesOrderDetail.objects.filter(
            product=product,
            order__status=OrderStatus.COMPLETED
        )
        .annotate(month=TruncMonth('order__order_date'))
        .values('month')
        .annotate(total_qty=Sum('quantity'))
        .order_by('month')
    )

    history = []
    for s in sales:
        m_str = s['month'].strftime('%Y-%m')
        history.append((m_str, s['total_qty']))

    return history

def forecast_demand_sma(product, n_periods=3):
    """
    3-month simple moving average demand forecast (BR21).
    Returns float forecasted quantity if >= n_periods exist, else None.
    """
    history = get_monthly_sales_history(product)
    if len(history) < n_periods:
        # Not enough historical periods (BR21)
        return None

    # Take the last n_periods
    recent_quantities = [h[1] for h in history[-n_periods:]]
    forecast_value = sum(recent_quantities) / len(recent_quantities)
    return round(forecast_value, 1)

def get_approved_on_order_qty(product):
    """Calculates quantity already approved in purchase requests but not yet received."""
    qty = (
        PurchaseRequestDetail.objects.filter(
            product=product,
            request__status=PurchaseRequestStatus.APPROVED
        ).aggregate(total=Sum('requested_quantity'))['total'] or 0
    )
    return qty

def calculate_procurement_suggestion(product):
    """
    Calculates procurement suggestion using the mandated formula:
    Số lượng gợi ý = Dự báo nhu cầu kỳ tới + Tồn tối thiểu - Tồn khả dụng - Số lượng đã duyệt nhưng chưa nhập.
    If result <= 0 -> 0 (BR20).
    """
    forecast = forecast_demand_sma(product)
    available_stock = product.get_current_stock()
    min_stock = product.min_stock
    on_order = get_approved_on_order_qty(product)

    effective_forecast = forecast if forecast is not None else 0.0

    raw_suggested = effective_forecast + min_stock - available_stock - on_order
    suggested_qty = math.ceil(raw_suggested) if raw_suggested > 0 else 0

    return {
        'product': product,
        'forecast': forecast,
        'has_forecast': forecast is not None,
        'min_stock': min_stock,
        'available_stock': available_stock,
        'approved_on_order': on_order,
        'suggested_quantity': suggested_qty,
        'is_low_stock': available_stock <= min_stock,
        'estimated_cost': Decimal(str(suggested_qty)) * product.cost_price,
    }

def calculate_gross_margins():
    """
    Calculates gross profit margin by product and category (Mục 2.5.9, TC29).
    Biên lợi nhuận gộp = (Doanh thu - Giá vốn) / Doanh thu * 100%.
    """
    items = (
        SalesOrderDetail.objects.filter(order__status=OrderStatus.COMPLETED)
        .values('product__id', 'product__code', 'product__name', 'product__category')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum('total_price'),
        )
        .order_by('-total_revenue')
    )

    results = []
    category_summary = {}

    for item in items:
        p_id = item['product__id']
        product = Product.objects.filter(pk=p_id).first()
        cost_price = product.cost_price if product else Decimal('0.00')

        qty = item['total_qty'] or 0
        rev = item['total_revenue'] or Decimal('0.00')
        cogs = Decimal(str(qty)) * cost_price
        gross_profit = rev - cogs
        margin_pct = (gross_profit / rev * 100) if rev > 0 else Decimal('0.00')

        results.append({
            'code': item['product__code'],
            'name': item['product__name'],
            'category': item['product__category'],
            'quantity': qty,
            'revenue': rev,
            'cogs': cogs,
            'gross_profit': gross_profit,
            'margin_pct': round(margin_pct, 1),
        })

        # Category aggregate
        cat = item['product__category']
        if cat not in category_summary:
            category_summary[cat] = {'revenue': Decimal('0.00'), 'cogs': Decimal('0.00'), 'profit': Decimal('0.00')}
        category_summary[cat]['revenue'] += rev
        category_summary[cat]['cogs'] += cogs
        category_summary[cat]['profit'] += gross_profit

    cat_list = []
    for cat, vals in category_summary.items():
        m_pct = (vals['profit'] / vals['revenue'] * 100) if vals['revenue'] > 0 else Decimal('0.00')
        cat_list.append({
            'category': cat,
            'revenue': vals['revenue'],
            'cogs': vals['cogs'],
            'profit': vals['profit'],
            'margin_pct': round(m_pct, 1)
        })

    return results, cat_list

def optimize_procurement_ortools(budget_limit, candidate_products=None):
    """
    Uses Google OR-Tools (Linear Programming / MIP) to optimize procurement under a budget constraint.
    Problem:
      Maximize Expected Profit: Sum( quantity_i * (price_i - cost_price_i) )
      Subject to:
        Sum( quantity_i * cost_price_i ) <= budget_limit
        quantity_i <= max_need_i
        quantity_i >= 0 (integer)
    """
    from ortools.linear_solver import pywraplp

    if candidate_products is None:
        candidate_products = Product.objects.filter(status='ACTIVE')

    # Prepare product data
    prod_data = []
    for p in candidate_products:
        sugg = calculate_procurement_suggestion(p)
        suggested_qty = sugg['suggested_quantity']
        # If no suggestion, allow up to min_stock
        max_limit = max(suggested_qty, p.min_stock, 2)
        profit_unit = float(p.price - p.cost_price)
        cost_unit = float(p.cost_price)

        if cost_unit > 0 and profit_unit > 0:
            prod_data.append({
                'product': p,
                'cost': cost_unit,
                'profit': profit_unit,
                'min_limit': 0,
                'max_limit': max_limit,
                'suggested_qty': suggested_qty,
            })

    if not prod_data or budget_limit <= 0:
        return {
            'status': 'NO_DATA',
            'plan': [],
            'total_cost': 0,
            'expected_profit': 0,
            'budget_utilization': 0,
        }

    # Create solver
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        # Fallback to CBC
        solver = pywraplp.Solver.CreateSolver('CBC')

    variables = []
    for idx, item in enumerate(prod_data):
        var = solver.IntVar(item['min_limit'], item['max_limit'], f"x_{idx}")
        variables.append(var)

    # Budget constraint: sum(x_i * cost_i) <= budget_limit
    solver.Add(solver.Sum([variables[idx] * item['cost'] for idx, item in enumerate(prod_data)]) <= float(budget_limit))

    # Objective: Maximize sum(x_i * profit_i)
    solver.Maximize(solver.Sum([variables[idx] * item['profit'] for idx, item in enumerate(prod_data)]))

    status = solver.Solve()

    plan = []
    total_cost = 0.0
    total_profit = 0.0

    if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
        for idx, item in enumerate(prod_data):
            val = int(round(variables[idx].solution_value()))
            if val > 0:
                cost = val * item['cost']
                profit = val * item['profit']
                total_cost += cost
                total_profit += profit
                plan.append({
                    'product': item['product'],
                    'optimal_qty': val,
                    'unit_cost': item['cost'],
                    'unit_profit': item['profit'],
                    'total_cost': cost,
                    'total_profit': profit,
                })

    utilization = (total_cost / float(budget_limit) * 100) if budget_limit > 0 else 0.0

    return {
        'status': 'OPTIMAL' if status == pywraplp.Solver.OPTIMAL else 'FEASIBLE',
        'plan': plan,
        'total_cost': total_cost,
        'expected_profit': total_profit,
        'budget_utilization': round(utilization, 1),
        'budget_limit': budget_limit,
    }
