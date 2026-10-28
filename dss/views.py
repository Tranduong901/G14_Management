from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Role
from accounts.decorators import role_required
from catalog.models import Product
from dss.services import (
    calculate_gross_margins,
    calculate_procurement_suggestion,
    get_monthly_sales_history,
    forecast_demand_sma,
    optimize_procurement_ortools
)
from dss.models import ForecastResult

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def dss_analytics_view(request):
    """Gross margin analysis by product and category (Mục 2.5.9, TC29)."""
    product_margins, category_margins = calculate_gross_margins()
    return render(request, 'dss/analytics.html', {
        'product_margins': product_margins,
        'category_margins': category_margins,
    })

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def dss_forecast_view(request):
    """
    Demand forecasting using 3-month simple moving average (SMA) (BR21).
    Displays actual sales history, forecast value, and forecast error if recorded.
    """
    products = Product.objects.filter(status='ACTIVE')
    forecast_data = []

    for p in products:
        history = get_monthly_sales_history(p, num_months=6)
        forecast_val = forecast_demand_sma(p, n_periods=3)
        past_results = ForecastResult.objects.filter(product=p).order_by('-forecast_period')[:3]

        forecast_data.append({
            'product': p,
            'history': history,
            'forecast_val': forecast_val,
            'has_sufficient_data': forecast_val is not None,
            'past_results': past_results,
        })

    return render(request, 'dss/forecast.html', {
        'forecast_data': forecast_data,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def dss_suggestions_view(request):
    """
    Procurement suggestions using the mandated formula:
    Số lượng gợi ý = Dự báo + Tồn tối thiểu - Tồn khả dụng - Số lượng đã duyệt chưa nhập.
    """
    products = Product.objects.filter(status='ACTIVE')
    suggestions = [calculate_procurement_suggestion(p) for p in products]

    # Filter to only products with positive suggestion if requested
    filter_needed = request.GET.get('needed_only', '1') == '1'
    if filter_needed:
        display_suggestions = [s for s in suggestions if s['suggested_quantity'] > 0 or s['is_low_stock']]
    else:
        display_suggestions = suggestions

    total_est_cost = sum(s['estimated_cost'] for s in display_suggestions)

    return render(request, 'dss/suggestions.html', {
        'suggestions': display_suggestions,
        'filter_needed': filter_needed,
        'total_est_cost': total_est_cost,
    })

@login_required
@role_required([Role.QL, Role.ADMIN])
def dss_optimizer_view(request):
    """
    Interactive OR-Tools procurement optimizer under budget limit.
    """
    budget_input = request.GET.get('budget', '50000000')  # Default 50M VND
    try:
        budget = float(budget_input)
    except ValueError:
        budget = 50000000.0

    result = optimize_procurement_ortools(budget_limit=budget)

    return render(request, 'dss/optimizer.html', {
        'budget': budget,
        'result': result,
    })

