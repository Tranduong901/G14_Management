from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate, TruncMonth

from sales.models import SalesOrder, SalesOrderDetail, OrderStatus, PaymentStatus
from purchasing.models import PurchaseReceipt, PurchaseDetail, ReceiptStatus
from catalog.models import Product, Customer, Supplier
from finance.models import CashLedger, Payable, LedgerType, PayableStatus
from scm.models import PurchaseRequest, PurchaseRequestStatus
from devices.models import ProductItem, WarrantyReturn, ItemStatus

def get_dashboard_kpis():
    """Aggregates high-level management metrics for executive dashboard."""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    # 1. Total revenue (completed & paid orders only - BR04, BR08)
    total_revenue = SalesOrder.objects.filter(
        status=OrderStatus.COMPLETED,
        payment_status=PaymentStatus.PAID
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Month revenue
    month_revenue = SalesOrder.objects.filter(
        status=OrderStatus.COMPLETED,
        payment_status=PaymentStatus.PAID,
        completed_at__date__gte=start_of_month
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # 2. Total completed orders count
    completed_orders_count = SalesOrder.objects.filter(status=OrderStatus.COMPLETED).count()

    # 3. Inventory valuation & alerts
    products = Product.objects.filter(status='ACTIVE')
    total_inventory_val = Decimal('0.00')
    low_stock_count = 0
    for p in products:
        stock = p.get_current_stock()
        total_inventory_val += stock * p.cost_price
        if stock <= p.min_stock:
            low_stock_count += 1

    # 4. Cash balance
    receipts = CashLedger.objects.filter(transaction_type=LedgerType.RECEIPT).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    payments = CashLedger.objects.filter(transaction_type=LedgerType.PAYMENT).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_balance = receipts - payments

    # 5. Overdue payables
    overdue_payables = Payable.objects.filter(remaining_amount__gt=0, due_date__lt=today)
    overdue_debt = overdue_payables.aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')
    overdue_count = overdue_payables.count()

    # 6. Pending purchase requests awaiting approval
    pending_requests_count = PurchaseRequest.objects.filter(status=PurchaseRequestStatus.PENDING).count()

    # 7. Active warranty tickets
    active_warranty_count = WarrantyReturn.objects.filter(status__in=['PENDING', 'PROCESSING']).count()

    return {
        'total_revenue': total_revenue,
        'month_revenue': month_revenue,
        'completed_orders_count': completed_orders_count,
        'total_inventory_val': total_inventory_val,
        'low_stock_count': low_stock_count,
        'cash_balance': cash_balance,
        'overdue_debt': overdue_debt,
        'overdue_count': overdue_count,
        'pending_requests_count': pending_requests_count,
        'active_warranty_count': active_warranty_count,
    }

def get_chart_data():
    """Generates time-series and breakdown data for Chart.js."""
    today = timezone.now().date()

    # 1. Monthly revenue (last 6 months) for continuous managerial trend
    monthly_sales = (
        SalesOrder.objects.filter(status=OrderStatus.COMPLETED)
        .annotate(m=TruncMonth('completed_at'))
        .values('m')
        .annotate(total=Sum('total_amount'), count=Count('id'))
        .order_by('m')
    )
    month_map = {item['m'].strftime('%m/%Y'): float(item['total']) for item in monthly_sales}

    monthly_labels = []
    monthly_values = []
    curr_year = today.year
    curr_month = today.month

    for i in range(5, -1, -1):
        m = curr_month - i
        y = curr_year
        while m <= 0:
            m += 12
            y -= 1
        key = f'{m:02d}/{y}'
        label = f'Tháng {m:02d}/{y}'
        monthly_labels.append(label)
        monthly_values.append(month_map.get(key, 0.0))

    # 2. Daily revenue past 7 days
    past_7_days = today - timedelta(days=6)
    daily_sales_7 = (
        SalesOrder.objects.filter(
            status=OrderStatus.COMPLETED,
            completed_at__date__gte=past_7_days
        )
        .annotate(day=TruncDate('completed_at'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )
    daily_map_7 = {item['day']: float(item['total']) for item in daily_sales_7}
    dates_labels_7 = []
    daily_values_7 = []
    for i in range(7):
        d = past_7_days + timedelta(days=i)
        dates_labels_7.append(d.strftime('%d/%m'))
        daily_values_7.append(daily_map_7.get(d, 0.0))

    # 3. Daily revenue past 30 days
    past_30_days = today - timedelta(days=29)
    daily_sales_30 = (
        SalesOrder.objects.filter(
            status=OrderStatus.COMPLETED,
            completed_at__date__gte=past_30_days
        )
        .annotate(day=TruncDate('completed_at'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )
    daily_map_30 = {item['day']: float(item['total']) for item in daily_sales_30}
    dates_labels_30 = []
    daily_values_30 = []
    for i in range(30):
        d = past_30_days + timedelta(days=i)
        dates_labels_30.append(d.strftime('%d/%m'))
        daily_values_30.append(daily_map_30.get(d, 0.0))

    # 4. Revenue share by Category (BR04, FR-09)
    category_data = (
        SalesOrderDetail.objects.filter(order__status=OrderStatus.COMPLETED)
        .values('product__category')
        .annotate(total=Sum('total_price'), qty=Sum('quantity'))
        .order_by('-total')
    )
    from catalog.models import ProductCategory
    cat_names = dict(ProductCategory.choices)
    category_labels = [cat_names.get(c['product__category'], c['product__category'] or 'Khác') for c in category_data]
    category_values = [float(c['total']) for c in category_data]
    category_quantities = [int(c['qty']) for c in category_data]

    # 5. Top 5 selling products
    top_products = (
        SalesOrderDetail.objects.filter(order__status=OrderStatus.COMPLETED)
        .values('product__name')
        .annotate(qty=Sum('quantity'), total=Sum('total_price'))
        .order_by('-qty')[:5]
    )
    top_prod_labels = [p['product__name'][:20] + '...' if len(p['product__name']) > 20 else p['product__name'] for p in top_products]
    top_prod_quantities = [int(p['qty']) for p in top_products]
    top_prod_revenues = [float(p['total']) for p in top_products]

    return {
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'dates_labels_7': dates_labels_7,
        'daily_values_7': daily_values_7,
        'dates_labels_30': dates_labels_30,
        'daily_values_30': daily_values_30,
        'dates_labels': dates_labels_7,  # backward compatibility
        'daily_values': daily_values_7,  # backward compatibility
        'category_labels': category_labels,
        'category_values': category_values,
        'category_quantities': category_quantities,
        'top_prod_labels': top_prod_labels,
        'top_prod_quantities': top_prod_quantities,
        'top_prod_revenues': top_prod_revenues,
    }

def get_revenue_report_data(from_date=None, to_date=None, staff_id=None, category=None):
    orders = SalesOrder.objects.filter(status=OrderStatus.COMPLETED).select_related('customer', 'staff')
    if from_date:
        orders = orders.filter(completed_at__date__gte=from_date)
    if to_date:
        orders = orders.filter(completed_at__date__lte=to_date)
    if staff_id:
        orders = orders.filter(staff_id=staff_id)

    # Monthly summary
    monthly_summary = (
        orders.annotate(m=TruncMonth('completed_at'))
        .values('m')
        .annotate(total_orders=Count('id'), total_amount=Sum('total_amount'))
        .order_by('-m')
    )

    # Staff KPI breakdown (BR12, TC06)
    staff_breakdown = (
        orders.values('staff__id', 'staff__username', 'staff__first_name', 'staff__last_name')
        .annotate(order_count=Count('id'), total_sales=Sum('total_amount'))
        .order_by('-total_sales')
    )

    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    return {
        'orders': orders[:50],
        'monthly_summary': monthly_summary,
        'staff_breakdown': staff_breakdown,
        'total_revenue': total_revenue,
        'total_orders': orders.count(),
    }

def get_customer_report_data():
    customers = Customer.objects.all()
    cust_data = []
    for c in customers:
        orders = SalesOrder.objects.filter(customer=c, status=OrderStatus.COMPLETED)
        count = orders.count()
        total_val = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        cust_data.append({
            'customer': c,
            'order_count': count,
            'total_spent': total_val,
            'avg_order_value': (total_val / count) if count > 0 else Decimal('0.00'),
        })
    # Sort by total spent
    cust_data.sort(key=lambda x: x['total_spent'], reverse=True)
    return cust_data

