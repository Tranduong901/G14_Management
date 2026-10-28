from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from decimal import Decimal

from accounts.models import Role
from accounts.decorators import role_required
from finance.models import CashLedger, Payable, PayablePayment, LedgerType, PaymentMethod, PayableStatus, ReferenceType
from finance.forms import PayablePaymentForm, OtherLedgerForm, ReversalForm
from finance.services import pay_payable, create_other_ledger_entry, reverse_ledger_entry, get_financial_summary
from catalog.models import Supplier

# ==================== CASH LEDGER VIEWS ====================

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def cash_ledger_list_view(request):
    ledgers = CashLedger.objects.select_related('recorded_by').all()
    q = request.GET.get('q', '').strip()
    tx_type = request.GET.get('type', '')
    method = request.GET.get('method', '')

    if q:
        ledgers = ledgers.filter(
            Q(code__icontains=q) |
            Q(reference_id__icontains=q) |
            Q(reason__icontains=q)
        )
    if tx_type:
        ledgers = ledgers.filter(transaction_type=tx_type)
    if method:
        ledgers = ledgers.filter(payment_method=method)

    paginator = Paginator(ledgers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    summary = get_financial_summary()

    return render(request, 'finance/cash_ledger_list.html', {
        'page_obj': page_obj,
        'q': q,
        'type_filter': tx_type,
        'method_filter': method,
        'types': LedgerType.choices,
        'methods': PaymentMethod.choices,
        'summary': summary,
    })

@login_required
@role_required([Role.KT, Role.ADMIN])
def ledger_create_other_view(request):
    if request.method == 'POST':
        form = OtherLedgerForm(request.POST)
        if form.is_valid():
            try:
                entry = create_other_ledger_entry(
                    transaction_type=form.cleaned_data['transaction_type'],
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    reason=form.cleaned_data['reason'],
                    user=request.user
                )
                messages.success(request, f"Đã ghi nhận bút toán {entry.code} vào sổ quỹ thành công!")
                return redirect('finance:cash_ledger_list')
            except Exception as e:
                messages.error(request, f"Lỗi: {str(e)}")
    else:
        form = OtherLedgerForm()

    return render(request, 'finance/ledger_form.html', {'form': form, 'title': 'Lập bút toán thu / chi khác'})

@login_required
@role_required([Role.KT, Role.ADMIN])
def ledger_reverse_view(request, pk):
    original_entry = get_object_or_404(CashLedger, pk=pk)
    if request.method == 'POST':
        form = ReversalForm(request.POST)
        if form.is_valid():
            try:
                reversal = reverse_ledger_entry(
                    original_entry=original_entry,
                    reason=form.cleaned_data['reason'],
                    user=request.user
                )
                messages.success(request, f"Đã tạo bút toán đảo {reversal.code} thành công!")
                return redirect('finance:cash_ledger_list')
            except Exception as e:
                messages.error(request, f"Lỗi: {str(e)}")
    else:
        form = ReversalForm()

    return render(request, 'finance/ledger_reversal_form.html', {
        'form': form,
        'original_entry': original_entry
    })

# ==================== PAYABLES VIEWS ====================

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def payable_list_view(request):
    payables = Payable.objects.select_related('supplier', 'purchase_receipt').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    supplier_id = request.GET.get('supplier', '')
    filter_overdue = request.GET.get('overdue', '') == '1'

    if q:
        payables = payables.filter(
            Q(code__icontains=q) |
            Q(supplier__name__icontains=q) |
            Q(purchase_receipt__code__icontains=q)
        )
    if status:
        payables = payables.filter(status=status)
    if supplier_id:
        payables = payables.filter(supplier_id=supplier_id)

    if filter_overdue:
        from django.utils import timezone
        payables = payables.filter(remaining_amount__gt=0, due_date__lt=timezone.now().date())

    paginator = Paginator(payables, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    suppliers = Supplier.objects.all()
    summary = get_financial_summary()

    return render(request, 'finance/payable_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'supplier_filter': supplier_id,
        'filter_overdue': filter_overdue,
        'suppliers': suppliers,
        'statuses': PayableStatus.choices,
        'summary': summary,
    })

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def payable_detail_view(request, pk):
    payable = get_object_or_404(
        Payable.objects.select_related('supplier', 'purchase_receipt'),
        pk=pk
    )
    payments = payable.payments.select_related('ledger_entry').all()
    payment_form = PayablePaymentForm(initial={'amount': payable.remaining_amount}) if payable.remaining_amount > 0 else None

    return render(request, 'finance/payable_detail.html', {
        'payable': payable,
        'payments': payments,
        'payment_form': payment_form,
    })

@login_required
@role_required([Role.KT, Role.ADMIN])
def payable_pay_view(request, pk):
    payable = get_object_or_404(Payable, pk=pk)
    if request.method == 'POST':
        form = PayablePaymentForm(request.POST)
        if form.is_valid():
            try:
                pay_payable(
                    payable=payable,
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    notes=form.cleaned_data['notes'],
                    user=request.user
                )
                messages.success(request, f"Đã thanh toán {form.cleaned_data['amount']:,.0f} đ cho nhà cung cấp {payable.supplier.name} thành công!")
            except Exception as e:
                messages.error(request, f"Lỗi thanh toán: {str(e)}")
    return redirect('finance:payable_detail', pk=payable.pk)

# ==================== RECONCILIATION VIEW ====================

@login_required
@role_required([Role.QL, Role.KT, Role.ADMIN])
def financial_reconciliation_view(request):
    """
    Reconciliation view (Mục 2.5.7, TC23: Đối soát số liệu tài chính).
    Compares:
    1. Total completed and paid sales orders vs Total CashLedger receipts from orders.
    2. Total completed purchase receipts vs Total Payables created.
    """
    from sales.models import SalesOrder, OrderStatus, PaymentStatus
    from purchasing.models import PurchaseReceipt, ReceiptStatus

    # Revenue vs Sổ quỹ thu
    total_sales_revenue = SalesOrder.objects.filter(
        status=OrderStatus.COMPLETED,
        payment_status=PaymentStatus.PAID
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    total_ledger_sales_receipts = CashLedger.objects.filter(
        reference_type=ReferenceType.SALES_ORDER,
        is_reversed=False
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    sales_diff = total_sales_revenue - total_ledger_sales_receipts

    # Purchase vs Công nợ
    total_purchase_val = PurchaseReceipt.objects.filter(
        status=ReceiptStatus.COMPLETED
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    total_payables_orig = Payable.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    purchase_diff = total_purchase_val - total_payables_orig

    return render(request, 'finance/reconciliation.html', {
        'total_sales_revenue': total_sales_revenue,
        'total_ledger_sales_receipts': total_ledger_sales_receipts,
        'sales_diff': sales_diff,
        'sales_matched': sales_diff == 0,
        'total_purchase_val': total_purchase_val,
        'total_payables_orig': total_payables_orig,
        'purchase_diff': purchase_diff,
        'purchase_matched': purchase_diff == 0,
    })

