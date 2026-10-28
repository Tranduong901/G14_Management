import json
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import Role, User
from accounts.decorators import role_required
from reports.services import (
    get_dashboard_kpis,
    get_chart_data,
    get_revenue_report_data,
    get_customer_report_data
)
from catalog.models import Product, Supplier, ProductCategory
from purchasing.models import PurchaseReceipt, ReceiptStatus
from finance.models import CashLedger, Payable
from django.db.models import Sum, Count

@login_required
def dashboard_view(request):
    """
    Central executive management dashboard (FR-09, FR-16).
    Displays business KPI summary cards and interactive Chart.js charts.
    """
    kpis = get_dashboard_kpis()
    chart_data = get_chart_data()

    # Low stock items for quick action
    low_stock_products = []
    for p in Product.objects.filter(status='ACTIVE'):
        st = p.get_current_stock()
        if st <= p.min_stock:
            p.stock_qty = st
            low_stock_products.append(p)

    # Overdue payables
    from django.utils import timezone
    overdue_payables = Payable.objects.filter(remaining_amount__gt=0, due_date__lt=timezone.now().date())[:5]

    # Pending purchase requests
    from scm.models import PurchaseRequest, PurchaseRequestStatus
    pending_requests = PurchaseRequest.objects.filter(status=PurchaseRequestStatus.PENDING)[:5]

    return render(request, 'reports/dashboard.html', {
        'kpis': kpis,
        'chart_data_json': json.dumps(chart_data),
        'low_stock_products': low_stock_products[:5],
        'overdue_payables': overdue_payables,
        'pending_requests': pending_requests,
    })

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def revenue_report_view(request):
    """Revenue report (Doanh thu theo ngày/tháng/quý, nhân viên) (TC01, TC06)."""
    from_date = request.GET.get('from_date') or None
    to_date = request.GET.get('to_date') or None
    staff_id = request.GET.get('staff') or None

    data = get_revenue_report_data(from_date=from_date, to_date=to_date, staff_id=staff_id)
    staff_users = User.objects.filter(role__in=[Role.BH, Role.QL])

    return render(request, 'reports/revenue_report.html', {
        'data': data,
        'from_date': from_date,
        'to_date': to_date,
        'staff_filter': staff_id,
        'staff_users': staff_users,
    })

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def inventory_report_view(request):
    """Inventory valuation and stock report (TC10, TC11, TC12)."""
    products = Product.objects.all()
    prod_data = []
    total_val = Decimal('0.00')
    total_low = 0

    for p in products:
        stock = p.get_current_stock()
        val = stock * p.cost_price
        total_val += val
        is_low = stock <= p.min_stock
        if is_low:
            total_low += 1
        prod_data.append({
            'product': p,
            'stock': stock,
            'valuation': val,
            'is_low': is_low,
        })

    return render(request, 'reports/inventory_report.html', {
        'products_data': prod_data,
        'total_val': total_val,
        'total_low': total_low,
    })

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def purchasing_report_view(request):
    """Purchasing report (Giá trị nhập theo NCC, thời gian) (TC08, TC09)."""
    receipts = PurchaseReceipt.objects.filter(status=ReceiptStatus.COMPLETED).select_related('supplier')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    if from_date:
        receipts = receipts.filter(receipt_date__gte=from_date)
    if to_date:
        receipts = receipts.filter(receipt_date__lte=to_date)

    supplier_summary = (
        receipts.values('supplier__name', 'supplier__code')
        .annotate(total_receipts=Count('id'), total_val=Sum('total_amount'))
        .order_by('-total_val')
    )

    total_purchase_val = receipts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    return render(request, 'reports/purchasing_report.html', {
        'receipts': receipts[:50],
        'supplier_summary': supplier_summary,
        'total_purchase_val': total_purchase_val,
        'from_date': from_date,
        'to_date': to_date,
    })

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def customer_report_view(request):
    """Customer frequency and purchase valuation report (TC07)."""
    customers_data = get_customer_report_data()
    return render(request, 'reports/customer_report.html', {
        'customers_data': customers_data,
    })

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def financial_report_view(request):
    """Financial report (Sổ quỹ & Công nợ phải trả) (TC20, TC21, TC22)."""
    from finance.services import get_financial_summary
    summary = get_financial_summary()
    recent_ledgers = CashLedger.objects.all()[:20]
    overdue_payables = Payable.objects.filter(remaining_amount__gt=0).order_by('due_date')[:15]

    return render(request, 'reports/financial_report.html', {
        'summary': summary,
        'recent_ledgers': recent_ledgers,
        'overdue_payables': overdue_payables,
    })

