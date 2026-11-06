from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal

from accounts.models import Role
from accounts.decorators import role_required
from sales.models import SalesOrder, SalesOrderDetail, OrderStatus, PaymentMethod
from sales.forms import SalesOrderForm, SalesOrderDetailFormSet, OrderCompleteForm
from sales.services import complete_sales_order, cancel_sales_order, generate_order_code
from catalog.models import Product, Customer
from inventory.models import Warehouse

@login_required
@role_required([Role.QL, Role.BH, Role.KT, Role.ADMIN])
def order_list_view(request):
    orders = SalesOrder.objects.select_related('customer', 'staff').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    customer_id = request.GET.get('customer', '')

    # If BH role (sales staff) and not manager/admin, restrict to orders handled by this staff
    if request.user.role == Role.BH and not request.user.is_superuser:
        orders = orders.filter(staff=request.user)

    if q:
        orders = orders.filter(
            Q(code__icontains=q) |
            Q(customer__name__icontains=q) |
            Q(customer__phone__icontains=q)
        )
    if status:
        orders = orders.filter(status=status)
    if customer_id:
        orders = orders.filter(customer_id=customer_id)

    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    customers = Customer.objects.all()

    return render(request, 'sales/order_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'customer_filter': customer_id,
        'customers': customers,
        'statuses': OrderStatus.choices,
    })

@login_required
@role_required([Role.QL, Role.BH, Role.KT, Role.ADMIN])
def order_detail_view(request, pk):
    order = get_object_or_404(
        SalesOrder.objects.select_related('customer', 'staff'),
        pk=pk
    )
    details = order.details.select_related('product').all()
    complete_form = OrderCompleteForm(initial={'payment_method': order.payment_method}) if order.status == OrderStatus.DRAFT else None

    return render(request, 'sales/order_detail.html', {
        'order': order,
        'details': details,
        'complete_form': complete_form,
    })

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def order_create_view(request):
    if request.method == 'POST':
        form = SalesOrderForm(request.POST)
        if request.user.branch_id:
            form.fields['warehouse'].required = True
        formset = SalesOrderDetailFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.code = generate_order_code()
            order.staff = request.user
            order.branch = request.user.branch
            if order.warehouse and not request.user.can_access_branch(order.warehouse.branch):
                form.add_error('warehouse', 'Bạn không có quyền thao tác kho thuộc chi nhánh này.')
                return render(request, 'sales/order_form.html', {
                    'form': form, 'formset': formset, 'products': Product.objects.filter(status='ACTIVE'),
                    'title': 'Tạo đơn bán hàng mới'
                })
            order.created_by = request.user
            order.save()

            formset.instance = order
            formset.save()

            order.recalculate_total()
            messages.success(request, f"Đã tạo đơn hàng mới {order.code} ở trạng thái Nháp!")
            return redirect('sales:order_detail', pk=order.pk)
    else:
        form = SalesOrderForm()
        if request.user.branch_id:
            form.fields['warehouse'].required = True
        formset = SalesOrderDetailFormSet()

    products = Product.objects.filter(status='ACTIVE')
    warehouses = Warehouse.objects.filter(is_active=True)
    if not request.user.is_superuser and request.user.data_scope != 'ALL' and request.user.branch_id:
        warehouses = warehouses.filter(branch_id=request.user.branch_id)
    form.fields['warehouse'].queryset = warehouses
    return render(request, 'sales/order_form.html', {
        'form': form,
        'formset': formset,
        'products': products,
        'title': 'Tạo đơn bán hàng mới'
    })

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def order_complete_view(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if request.method == 'POST':
        form = OrderCompleteForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data['payment_method']
            try:
                complete_sales_order(order, payment_method=method, user=request.user)
                messages.success(request, f"Đã hoàn tất đơn hàng {order.code}! Doanh thu, tồn kho và sổ quỹ đã được cập nhật thành công.")
            except Exception as e:
                messages.error(request, f"Không thể hoàn tất đơn hàng: {str(e)}")
    return redirect('sales:order_detail', pk=order.pk)

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def order_cancel_view(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('cancel_reason', 'Khách hàng yêu cầu hủy đơn')
        try:
            cancel_sales_order(order, request.user, reason=reason)
            messages.info(request, f"Đã hủy đơn hàng {order.code}.")
        except Exception as e:
            messages.error(request, f"Lỗi: {str(e)}")
    return redirect('sales:order_detail', pk=order.pk)

@login_required
def order_invoice_view(request, pk):
    order = get_object_or_404(
        SalesOrder.objects.select_related('customer', 'staff'),
        pk=pk
    )
    details = order.details.select_related('product').all()
    return render(request, 'sales/order_invoice.html', {
        'order': order,
        'details': details,
    })
