from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import Branch, Role
from accounts.decorators import role_required
from accounts.scoping import get_scoped_queryset
from inventory.models import InventoryTransaction, StockAdjustment, TransactionType, AdjustmentStatus, Warehouse
from inventory.forms import StockAdjustmentForm
from inventory.services import create_stock_adjustment, approve_stock_adjustment, reject_stock_adjustment
from catalog.models import Product, ProductCategory

@login_required
@role_required([Role.QL, Role.KHO, Role.KT, Role.ADMIN])
def inventory_summary_view(request):
    products = Product.objects.all()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    filter_low_stock = request.GET.get('low_stock', '') == '1'
    warehouse_id = request.GET.get('warehouse', '')
    branch_id = request.GET.get('branch', '')
    warehouses = Warehouse.objects.filter(is_active=True).select_related('branch')
    warehouses = get_scoped_queryset(warehouses, request.user, branch_field='branch', user_field=None)
    branches = Branch.objects.filter(is_active=True)
    if not request.user.is_superuser and request.user.data_scope != 'ALL' and request.user.branch_id:
        branches = branches.filter(pk=request.user.branch_id)
    branch = branches.filter(pk=branch_id).first() if branch_id else None
    if branch is None and request.user.data_scope != 'ALL' and request.user.branch_id:
        branch = request.user.branch
    warehouse = warehouses.filter(pk=warehouse_id).first() if warehouse_id else None
    if warehouse and branch and warehouse.branch_id != branch.pk:
        warehouse = None
    if warehouse:
        branch = warehouse.branch

    if q:
        products = products.filter(Q(code__icontains=q) | Q(name__icontains=q))
    if category:
        products = products.filter(category=category)

    product_list = []
    total_inventory_value = 0
    total_low_stock_count = 0

    for p in products:
        stock = p.get_current_stock(warehouse=warehouse, branch=branch)
        val = stock * p.cost_price
        total_inventory_value += val
        is_low = stock <= p.min_stock
        if is_low:
            total_low_stock_count += 1

        if filter_low_stock and not is_low:
            continue

        p.stock_qty = stock
        p.inventory_val = val
        p.is_alert = is_low
        product_list.append(p)

    paginator = Paginator(product_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/inventory_summary.html', {
        'page_obj': page_obj,
        'q': q,
        'category_filter': category,
        'filter_low_stock': filter_low_stock,
        'categories': ProductCategory.choices,
        'total_inventory_value': total_inventory_value,
        'total_low_stock_count': total_low_stock_count,
        'warehouses': warehouses,
        'warehouse_filter': warehouse_id,
        'branch_filter': branch_id,
        'branches': branches,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.KT, Role.ADMIN])
def transaction_list_view(request):
    txs = InventoryTransaction.objects.select_related('product', 'created_by').all()
    txs = get_scoped_queryset(
        txs,
        request.user,
        branch_field='warehouse__branch',
        user_field='created_by',
    )
    q = request.GET.get('q', '').strip()
    tx_type = request.GET.get('type', '')

    if q:
        txs = txs.filter(
            Q(reference_code__icontains=q) |
            Q(product__name__icontains=q) |
            Q(product__code__icontains=q)
        )
    if tx_type:
        txs = txs.filter(transaction_type=tx_type)

    paginator = Paginator(txs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/transaction_list.html', {
        'page_obj': page_obj,
        'q': q,
        'type_filter': tx_type,
        'transaction_types': TransactionType.choices,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def adjustment_list_view(request):
    adjustments = StockAdjustment.objects.select_related('product', 'created_by', 'approved_by').all()
    adjustments = get_scoped_queryset(
        adjustments,
        request.user,
        branch_field='warehouse__branch',
        user_field='created_by',
    )
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    if q:
        adjustments = adjustments.filter(
            Q(code__icontains=q) |
            Q(product__name__icontains=q) |
            Q(product__code__icontains=q)
        )
    if status:
        adjustments = adjustments.filter(status=status)

    paginator = Paginator(adjustments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/adjustment_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'statuses': AdjustmentStatus.choices,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def adjustment_create_view(request):
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST, user=request.user)
        if request.user.branch_id:
            form.fields['warehouse'].required = True
        if form.is_valid():
            try:
                adj = create_stock_adjustment(
                    product=form.cleaned_data['product'],
                    actual_quantity=form.cleaned_data['actual_quantity'],
                    reason=form.cleaned_data['reason'],
                    user=request.user,
                    warehouse=form.cleaned_data['warehouse'],
                )
                if adj.status == AdjustmentStatus.PENDING_APPROVAL:
                    messages.warning(request, f"Phiếu điều chỉnh {adj.code} có giá trị chênh lệch lớn nên đã được gửi chờ Quản lý phê duyệt.")
                else:
                    messages.success(request, f"Đã lập và cập nhật tồn kho theo phiếu điều chỉnh {adj.code} thành công!")
                return redirect('inventory:adjustment_list')
            except Exception as e:
                messages.error(request, f"Lỗi: {str(e)}")
    else:
        initial_data = {}
        prod_id = request.GET.get('product')
        if prod_id:
            initial_data['product'] = prod_id
        form = StockAdjustmentForm(initial=initial_data, user=request.user)
        if request.user.branch_id:
            form.fields['warehouse'].required = True

    return render(request, 'inventory/adjustment_form.html', {'form': form, 'title': 'Lập phiếu kiểm kê & điều chỉnh tồn kho'})

@login_required
@role_required([Role.QL, Role.ADMIN])
def adjustment_action_view(request, pk, action):
    adjustment = get_object_or_404(StockAdjustment, pk=pk)
    if request.method == 'POST':
        notes = request.POST.get('approval_notes', '')
        try:
            if action == 'approve':
                approve_stock_adjustment(adjustment, request.user, approval_notes=notes)
                messages.success(request, f"Đã phê duyệt phiếu điều chỉnh {adjustment.code} và cập nhật tồn kho thành công!")
            elif action == 'reject':
                reject_stock_adjustment(adjustment, request.user, rejection_reason=notes)
                messages.info(request, f"Đã từ chối phiếu điều chỉnh {adjustment.code}.")
        except Exception as e:
            messages.error(request, f"Lỗi: {str(e)}")
    return redirect('inventory:adjustment_list')
