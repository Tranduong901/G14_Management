from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal

from accounts.models import Role
from accounts.decorators import role_required
from purchasing.models import PurchaseReceipt, PurchaseDetail, ReceiptStatus
from purchasing.forms import PurchaseReceiptForm, PurchaseDetailFormSet
from purchasing.services import complete_purchase_receipt, cancel_purchase_receipt, generate_receipt_code
from catalog.models import Product, Supplier
from inventory.models import Warehouse

@login_required
@role_required([Role.QL, Role.KHO, Role.KT, Role.ADMIN])
def receipt_list_view(request):
    receipts = PurchaseReceipt.objects.select_related('supplier', 'created_by', 'request').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    supplier_id = request.GET.get('supplier', '')

    if q:
        receipts = receipts.filter(
            Q(code__icontains=q) |
            Q(supplier__name__icontains=q) |
            Q(supplier__code__icontains=q)
        )
    if status:
        receipts = receipts.filter(status=status)
    if supplier_id:
        receipts = receipts.filter(supplier_id=supplier_id)

    paginator = Paginator(receipts, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    suppliers = Supplier.objects.all()

    return render(request, 'purchasing/receipt_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'supplier_filter': supplier_id,
        'suppliers': suppliers,
        'statuses': ReceiptStatus.choices,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.KT, Role.ADMIN])
def receipt_detail_view(request, pk):
    receipt = get_object_or_404(
        PurchaseReceipt.objects.select_related('supplier', 'created_by', 'request'),
        pk=pk
    )
    details = receipt.details.select_related('product').all()
    from finance.models import Payable
    payable = Payable.objects.filter(purchase_receipt=receipt).first()

    return render(request, 'purchasing/receipt_detail.html', {
        'receipt': receipt,
        'details': details,
        'payable': payable,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def receipt_create_view(request):
    if request.method == 'POST':
        form = PurchaseReceiptForm(request.POST)
        if request.user.branch_id:
            form.fields['warehouse'].required = True
        formset = PurchaseDetailFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            receipt = form.save(commit=False)
            receipt.code = generate_receipt_code()
            receipt.created_by = request.user
            if receipt.warehouse and not request.user.can_access_branch(receipt.warehouse.branch):
                form.add_error('warehouse', 'Bạn không có quyền thao tác kho thuộc chi nhánh này.')
                return render(request, 'purchasing/receipt_form.html', {
                    'form': form, 'formset': formset, 'products': Product.objects.filter(status='ACTIVE'),
                    'title': 'Lập phiếu nhập hàng mới'
                })
            receipt.save()

            formset.instance = receipt
            formset.save()

            receipt.recalculate_total()

            messages.success(request, f"Đã lập phiếu nhập {receipt.code} ở trạng thái Nháp thành công!")
            return redirect('purchasing:receipt_detail', pk=receipt.pk)
    else:
        form = PurchaseReceiptForm()
        if request.user.branch_id:
            form.fields['warehouse'].required = True
        formset = PurchaseDetailFormSet()

    products = Product.objects.filter(status='ACTIVE')
    warehouses = Warehouse.objects.filter(is_active=True)
    if not request.user.is_superuser and request.user.data_scope != 'ALL' and request.user.branch_id:
        warehouses = warehouses.filter(branch_id=request.user.branch_id)
    form.fields['warehouse'].queryset = warehouses
    return render(request, 'purchasing/receipt_form.html', {
        'form': form,
        'formset': formset,
        'products': products,
        'title': 'Lập phiếu nhập hàng mới'
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def receipt_complete_view(request, pk):
    receipt = get_object_or_404(PurchaseReceipt, pk=pk)
    if request.method == 'POST':
        try:
            complete_purchase_receipt(receipt, request.user)
            messages.success(request, f"Đã hoàn tất phiếu nhập {receipt.code}! Tồn kho và công nợ phải trả đã được cập nhật.")
        except Exception as e:
            messages.error(request, f"Không thể hoàn tất phiếu nhập: {str(e)}")
    return redirect('purchasing:receipt_detail', pk=receipt.pk)

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def receipt_cancel_view(request, pk):
    receipt = get_object_or_404(PurchaseReceipt, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('cancel_reason', 'Hủy theo yêu cầu người dùng')
        try:
            cancel_purchase_receipt(receipt, request.user, reason=reason)
            messages.info(request, f"Đã hủy phiếu nhập {receipt.code}.")
        except Exception as e:
            messages.error(request, f"Lỗi: {str(e)}")
    return redirect('purchasing:receipt_detail', pk=receipt.pk)
