from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import Role
from accounts.decorators import role_required
from devices.models import ProductItem, WarrantyReturn, ItemStatus, WarrantyStatus
from devices.forms import ProductItemForm, WarrantyReturnForm, WarrantyResolveForm
from devices.services import create_warranty_claim, resolve_warranty_claim

@login_required
@role_required([Role.QL, Role.BH, Role.KHO, Role.ADMIN])
def device_list_view(request):
    items = ProductItem.objects.select_related('product', 'sales_order', 'purchase_receipt').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    product_id = request.GET.get('product', '')

    if q:
        items = items.filter(
            Q(serial_number__icontains=q) |
            Q(product__name__icontains=q) |
            Q(product__code__icontains=q)
        )
    if status:
        items = items.filter(status=status)
    if product_id:
        items = items.filter(product_id=product_id)

    paginator = Paginator(items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from catalog.models import Product
    products = Product.objects.filter(has_serial=True)

    return render(request, 'devices/device_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'product_filter': product_id,
        'statuses': ItemStatus.choices,
        'products': products,
    })

@login_required
def device_lookup_view(request):
    """Lookup warranty information by IMEI/Serial or Customer Phone."""
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        # Search by serial number or customer phone
        results = ProductItem.objects.select_related('product', 'sales_order__customer').filter(
            Q(serial_number__icontains=query) |
            Q(sales_order__customer__phone__icontains=query) |
            Q(sales_order__customer__name__icontains=query)
        )[:15]

    return render(request, 'devices/device_lookup.html', {
        'query': query,
        'results': results,
    })

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def warranty_list_view(request):
    claims = WarrantyReturn.objects.select_related('item__product', 'customer', 'replacement_item').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if q:
        claims = claims.filter(
            Q(code__icontains=q) |
            Q(item__serial_number__icontains=q) |
            Q(customer__name__icontains=q) |
            Q(customer__phone__icontains=q)
        )
    if status:
        claims = claims.filter(status=status)

    paginator = Paginator(claims, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'devices/warranty_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'statuses': WarrantyStatus.choices,
    })

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def warranty_create_view(request):
    prefill_serial = request.GET.get('serial', '')
    initial_data = {}
    if prefill_serial:
        item = ProductItem.objects.filter(serial_number=prefill_serial, status=ItemStatus.SOLD).first()
        if item:
            initial_data['item'] = item.pk
            if item.sales_order and item.sales_order.customer:
                initial_data['customer'] = item.sales_order.customer.pk

    if request.method == 'POST':
        form = WarrantyReturnForm(request.POST)
        if form.is_valid():
            try:
                claim = create_warranty_claim(
                    item=form.cleaned_data['item'],
                    customer=form.cleaned_data['customer'],
                    issue_description=form.cleaned_data['issue_description'],
                    action_type=form.cleaned_data['action_type'],
                    user=request.user,
                    notes=form.cleaned_data['notes']
                )
                messages.success(request, f"Đã tiếp nhận yêu cầu bảo hành thành công (Mã phiếu: {claim.code})!")
                return redirect('devices:warranty_detail', pk=claim.pk)
            except Exception as e:
                messages.error(request, f"Lỗi khi tiếp nhận bảo hành: {str(e)}")
    else:
        form = WarrantyReturnForm(initial=initial_data)

    return render(request, 'devices/warranty_form.html', {'form': form, 'title': 'Lập phiếu tiếp nhận bảo hành'})

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def warranty_detail_view(request, pk):
    claim = get_object_or_404(
        WarrantyReturn.objects.select_related('item__product', 'customer', 'replacement_item', 'created_by'),
        pk=pk
    )
    resolve_form = WarrantyResolveForm() if claim.status in [WarrantyStatus.PENDING, WarrantyStatus.PROCESSING] else None

    return render(request, 'devices/warranty_detail.html', {
        'claim': claim,
        'resolve_form': resolve_form,
    })

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def warranty_resolve_view(request, pk):
    claim = get_object_or_404(WarrantyReturn, pk=pk)
    if request.method == 'POST':
        form = WarrantyResolveForm(request.POST)
        if form.is_valid():
            try:
                resolve_warranty_claim(
                    claim=claim,
                    status=form.cleaned_data['status'],
                    replacement_item=form.cleaned_data['replacement_item'],
                    resolution_notes=form.cleaned_data['resolution_notes'],
                    user=request.user
                )
                messages.success(request, f"Đã hoàn tất xử lý phiếu bảo hành {claim.code}!")
            except Exception as e:
                messages.error(request, f"Lỗi xử lý: {str(e)}")
    return redirect('devices:warranty_detail', pk=claim.pk)

@login_required
def warranty_print_view(request, pk):
    claim = get_object_or_404(
        WarrantyReturn.objects.select_related('item__product', 'customer', 'replacement_item'),
        pk=pk
    )
    return render(request, 'devices/warranty_print.html', {'claim': claim})

