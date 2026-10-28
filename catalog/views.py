from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import Role
from accounts.decorators import role_required
from catalog.models import Product, Customer, Supplier, ProductCategory, ProductStatus
from catalog.forms import ProductForm, CustomerForm, SupplierForm
from auditlog.services import log_activity

# ==================== PRODUCT VIEWS ====================

@login_required
def product_list_view(request):
    products = Product.objects.all()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')

    if q:
        products = products.filter(
            Q(code__icontains=q) |
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )
    if category:
        products = products.filter(category=category)
    if status:
        products = products.filter(status=status)

    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Attach current stock to objects for display
    for p in page_obj:
        p.stock_qty = p.get_current_stock()
        p.is_alert = p.stock_qty <= p.min_stock

    return render(request, 'catalog/product_list.html', {
        'page_obj': page_obj,
        'q': q,
        'category_filter': category,
        'status_filter': status,
        'categories': ProductCategory.choices,
        'statuses': ProductStatus.choices,
    })

@login_required
def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    stock_qty = product.get_current_stock()
    
    # If product has serials, fetch available devices
    items = []
    if product.has_serial:
        from devices.models import ProductItem
        items = ProductItem.objects.filter(product=product).order_by('-created_at')[:20]

    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'stock_qty': stock_qty,
        'items': items,
    })

@login_required
@role_required([Role.QL, Role.ADMIN])
def product_create_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            log_activity(
                user=request.user,
                action='CREATE',
                obj=product,
                changes={'code': product.code, 'name': product.name, 'price': str(product.price)},
                request=request
            )
            messages.success(request, f"Đã thêm sản phẩm mới '{product.name}' thành công!")
            return redirect('catalog:product_list')
    else:
        form = ProductForm()

    return render(request, 'catalog/product_form.html', {'form': form, 'title': 'Thêm sản phẩm mới'})

@login_required
@role_required([Role.QL, Role.ADMIN])
def product_edit_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            updated = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated,
                changes={'code': updated.code, 'name': updated.name, 'price': str(updated.price), 'status': updated.status},
                request=request
            )
            messages.success(request, f"Cập nhật thông tin sản phẩm '{updated.name}' thành công!")
            return redirect('catalog:product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'catalog/product_form.html', {'form': form, 'title': f"Sửa sản phẩm: {product.name}"})

# ==================== CUSTOMER VIEWS ====================

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def customer_list_view(request):
    customers = Customer.objects.all()
    q = request.GET.get('q', '').strip()
    cust_type = request.GET.get('customer_type', '')

    if q:
        customers = customers.filter(
            Q(code__icontains=q) |
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
    if cust_type:
        customers = customers.filter(customer_type=cust_type)

    paginator = Paginator(customers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalog/customer_list.html', {
        'page_obj': page_obj,
        'q': q,
        'customer_type_filter': cust_type,
        'customer_types': Customer.CUSTOMER_TYPE_CHOICES,
    })

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def customer_detail_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    from sales.models import SalesOrder
    orders = SalesOrder.objects.filter(customer=customer).order_by('-created_at')[:10]
    return render(request, 'catalog/customer_detail.html', {
        'customer': customer,
        'orders': orders,
    })

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def customer_create_view(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            log_activity(
                user=request.user,
                action='CREATE',
                obj=customer,
                changes={'code': customer.code, 'name': customer.name, 'phone': customer.phone},
                request=request
            )
            messages.success(request, f"Đã thêm khách hàng '{customer.name}' thành công!")
            return redirect('catalog:customer_list')
    else:
        form = CustomerForm()

    return render(request, 'catalog/customer_form.html', {'form': form, 'title': 'Thêm khách hàng mới'})

@login_required
@role_required([Role.QL, Role.BH, Role.ADMIN])
def customer_edit_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            updated = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated,
                changes={'code': updated.code, 'name': updated.name, 'phone': updated.phone},
                request=request
            )
            messages.success(request, f"Cập nhật thông tin khách hàng '{updated.name}' thành công!")
            return redirect('catalog:customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'catalog/customer_form.html', {'form': form, 'title': f"Sửa khách hàng: {customer.name}"})

# ==================== SUPPLIER VIEWS ====================

@login_required
@role_required([Role.QL, Role.KHO, Role.KT, Role.ADMIN])
def supplier_list_view(request):
    suppliers = Supplier.objects.all()
    q = request.GET.get('q', '').strip()

    if q:
        suppliers = suppliers.filter(
            Q(code__icontains=q) |
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(suppliers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'catalog/supplier_list.html', {
        'page_obj': page_obj,
        'q': q,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.KT, Role.ADMIN])
def supplier_detail_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    from purchasing.models import PurchaseReceipt
    from finance.models import Payable
    receipts = PurchaseReceipt.objects.filter(supplier=supplier).order_by('-created_at')[:10]
    payables = Payable.objects.filter(supplier=supplier).order_by('-created_at')[:10]
    return render(request, 'catalog/supplier_detail.html', {
        'supplier': supplier,
        'receipts': receipts,
        'payables': payables,
    })

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def supplier_create_view(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()
            log_activity(
                user=request.user,
                action='CREATE',
                obj=supplier,
                changes={'code': supplier.code, 'name': supplier.name, 'phone': supplier.phone},
                request=request
            )
            messages.success(request, f"Đã thêm nhà cung cấp '{supplier.name}' thành công!")
            return redirect('catalog:supplier_list')
    else:
        form = SupplierForm()

    return render(request, 'catalog/supplier_form.html', {'form': form, 'title': 'Thêm nhà cung cấp mới'})

@login_required
@role_required([Role.QL, Role.KHO, Role.ADMIN])
def supplier_edit_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            updated = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated,
                changes={'code': updated.code, 'name': updated.name, 'payment_terms_days': updated.payment_terms_days},
                request=request
            )
            messages.success(request, f"Cập nhật thông tin nhà cung cấp '{updated.name}' thành công!")
            return redirect('catalog:supplier_list')
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'catalog/supplier_form.html', {'form': form, 'title': f"Sửa nhà cung cấp: {supplier.name}"})

