from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal

from accounts.models import Role
from accounts.decorators import role_required
from scm.models import PurchaseRequest, PurchaseRequestDetail, PurchaseRequestStatus, PurchaseRequestSource
from scm.forms import PurchaseRequestForm, PurchaseRequestDetailFormSet, RequestRejectForm
from scm.services import (
    generate_request_code,
    submit_purchase_request,
    approve_purchase_request,
    reject_purchase_request,
    convert_request_to_receipt,
    get_supplier_performance
)
from catalog.models import Product, Supplier

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def request_list_view(request):
    requests = PurchaseRequest.objects.select_related('requester', 'approver').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if q:
        requests = requests.filter(
            Q(code__icontains=q) |
            Q(requester__username__icontains=q) |
            Q(notes__icontains=q)
        )
    if status:
        requests = requests.filter(status=status)

    paginator = Paginator(requests, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'scm/request_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'statuses': PurchaseRequestStatus.choices,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def request_detail_view(request, pk):
    req_obj = get_object_or_404(
        PurchaseRequest.objects.select_related('requester', 'approver'),
        pk=pk
    )
    details = req_obj.details.select_related('product', 'suggested_supplier').all()
    reject_form = RequestRejectForm() if req_obj.status == PurchaseRequestStatus.PENDING else None

    # Check if converted receipt exists
    from purchasing.models import PurchaseReceipt
    linked_receipt = PurchaseReceipt.objects.filter(request=req_obj).first()

    return render(request, 'scm/request_detail.html', {
        'req_obj': req_obj,
        'details': details,
        'reject_form': reject_form,
        'linked_receipt': linked_receipt,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def request_create_view(request):
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST)
        formset = PurchaseRequestDetailFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            req_obj = form.save(commit=False)
            req_obj.code = generate_request_code()
            req_obj.requester = request.user
            req_obj.created_by = request.user
            req_obj.save()

            formset.instance = req_obj
            formset.save()

            messages.success(request, f"Đã lập đề nghị nhập hàng {req_obj.code} ở trạng thái Nháp!")
            return redirect('scm:request_detail', pk=req_obj.pk)
    else:
        # Pre-fill from GET parameters if coming from DSS suggestion
        initial_data = {}
        suggested_prod_id = request.GET.get('product')
        suggested_qty = request.GET.get('qty')
        form = PurchaseRequestForm()
        formset = PurchaseRequestDetailFormSet()

    products = Product.objects.filter(status='ACTIVE')
    suppliers = Supplier.objects.all()
    return render(request, 'scm/request_form.html', {
        'form': form,
        'formset': formset,
        'products': products,
        'suppliers': suppliers,
        'title': 'Lập đề nghị nhập hàng mới'
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def request_submit_view(request, pk):
    req_obj = get_object_or_404(PurchaseRequest, pk=pk)
    if request.method == 'POST':
        try:
            submit_purchase_request(req_obj, request.user)
            messages.success(request, f"Đã gửi đề nghị {req_obj.code} lên Quản lý phê duyệt!")
        except Exception as e:
            messages.error(request, f"Lỗi: {str(e)}")
    return redirect('scm:request_detail', pk=req_obj.pk)

@login_required
@role_required([Role.QL, Role.ADMIN])
def request_approve_view(request, pk):
    req_obj = get_object_or_404(PurchaseRequest, pk=pk)
    if request.method == 'POST':
        try:
            approve_purchase_request(req_obj, request.user)
            messages.success(request, f"Đã phê duyệt đề nghị nhập hàng {req_obj.code} thành công!")
        except Exception as e:
            messages.error(request, f"Lỗi: {str(e)}")
    return redirect('scm:request_detail', pk=req_obj.pk)

@login_required
@role_required([Role.QL, Role.ADMIN])
def request_reject_view(request, pk):
    req_obj = get_object_or_404(PurchaseRequest, pk=pk)
    if request.method == 'POST':
        form = RequestRejectForm(request.POST)
        if form.is_valid():
            try:
                reject_purchase_request(req_obj, form.cleaned_data['rejection_reason'], request.user)
                messages.info(request, f"Đã từ chối đề nghị nhập hàng {req_obj.code}.")
            except Exception as e:
                messages.error(request, f"Lỗi: {str(e)}")
    return redirect('scm:request_detail', pk=req_obj.pk)

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def request_convert_view(request, pk):
    req_obj = get_object_or_404(PurchaseRequest, pk=pk)
    if request.method == 'POST':
        try:
            receipt = convert_request_to_receipt(req_obj, request.user)
            messages.success(request, f"Đã chuyển đề nghị {req_obj.code} thành phiếu nhập {receipt.code} thành công!")
            return redirect('purchasing:receipt_detail', pk=receipt.pk)
        except Exception as e:
            messages.error(request, f"Không thể chuyển thành phiếu nhập: {str(e)}")
    return redirect('scm:request_detail', pk=req_obj.pk)

@login_required
@role_required([Role.QL, Role.KHO, Role.KT, Role.ADMIN])
def supplier_evaluation_view(request):
    scorecards = get_supplier_performance()
    return render(request, 'scm/supplier_evaluation.html', {'scorecards': scorecards})

