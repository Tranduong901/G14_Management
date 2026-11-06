from django.db import models
from decimal import Decimal
from accounts.models import BaseModel

class ProductCategory(models.TextChoices):
    PHONE = 'PHONE', 'Điện thoại thông minh'
    TABLET = 'TABLET', 'Máy tính bảng'
    LAPTOP = 'LAPTOP', 'Máy tính xách tay (Laptop)'
    ACCESSORY = 'ACCESSORY', 'Phụ kiện công nghệ'
    WEARABLE = 'WEARABLE', 'Thiết bị đeo thông minh'

class ProductStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Đang kinh doanh'
    DISCONTINUED = 'DISCONTINUED', 'Ngừng kinh doanh'

class Product(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã sản phẩm")
    name = models.CharField(max_length=255, verbose_name="Tên sản phẩm")
    category = models.CharField(
        max_length=50,
        choices=ProductCategory.choices,
        default=ProductCategory.PHONE,
        verbose_name="Nhóm sản phẩm"
    )
    unit = models.CharField(max_length=20, default='Chiếc', verbose_name="Đơn vị tính")
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Giá bán niêm yết (VNĐ)")
    cost_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Giá vốn / Giá nhập tham chiếu (VNĐ)"
    )
    min_stock = models.PositiveIntegerField(default=5, verbose_name="Ngưỡng tồn tối thiểu")
    has_serial = models.BooleanField(
        default=True,
        verbose_name="Quản lý theo Serial/IMEI",
        help_text="Đánh dấu Có đối với điện thoại, tablet, laptop cần truy vết từng máy."
    )
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        verbose_name="Trạng thái kinh doanh"
    )
    description = models.TextField(blank=True, verbose_name="Mô tả sản phẩm")

    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Danh mục sản phẩm"
        ordering = ['code']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='product_price_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(cost_price__gte=0),
                name='product_cost_price_non_negative',
            ),
        ]

    def __str__(self):
        return f"[{self.code}] {self.name}"

    def get_current_stock(self, branch=None, warehouse=None):
        """
        Calculates available in-stock quantity according to business rules:
        - If has_serial: count of ProductItem in status 'IN_STOCK'
        - If not has_serial: net sum of InventoryTransaction

        A warehouse filter is authoritative. A branch filter includes all
        warehouses in that branch. With no filter, legacy unassigned stock is
        included in the company-wide total.
        """
        if self.has_serial:
            from devices.models import ProductItem
            items = ProductItem.objects.filter(product=self, status='IN_STOCK')
            if warehouse is not None:
                items = items.filter(warehouse=warehouse)
            elif branch is not None:
                items = items.filter(warehouse__branch=branch)
            return items.count()
        else:
            from inventory.models import InventoryTransaction
            transactions = InventoryTransaction.objects.filter(product=self)
            if warehouse is not None:
                transactions = transactions.filter(warehouse=warehouse)
            elif branch is not None:
                transactions = transactions.filter(warehouse__branch=branch)
            total = 0
            for tx in transactions:
                if tx.transaction_type in ['IN', 'ADJUST_INC']:
                    total += tx.quantity
                elif tx.transaction_type in ['OUT', 'ADJUST_DEC', 'WARRANTY_OUT']:
                    total -= tx.quantity
            return max(0, total)

    @property
    def current_stock(self):
        return self.get_current_stock()

    @property
    def is_low_stock(self):
        return self.get_current_stock() <= self.min_stock

class Customer(BaseModel):
    CUSTOMER_TYPE_CHOICES = [
        ('RETAIL', 'Khách hàng cá nhân (Khách lẻ)'),
        ('WHOLESALE', 'Khách hàng doanh nghiệp / Đại lý'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="Mã khách hàng")
    name = models.CharField(max_length=150, verbose_name="Tên khách hàng")
    phone = models.CharField(max_length=20, unique=True, verbose_name="Số điện thoại")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ")
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default='RETAIL',
        verbose_name="Loại khách hàng"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Khách hàng"
        verbose_name_plural = "Danh mục khách hàng"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.phone} ({self.code})"

class Supplier(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã nhà cung cấp")
    name = models.CharField(max_length=200, verbose_name="Tên nhà cung cấp")
    phone = models.CharField(max_length=20, unique=True, verbose_name="Số điện thoại")
    email = models.EmailField(blank=True, verbose_name="Email")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ")
    payment_terms_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Điều khoản thanh toán (số ngày)",
        help_text="Số ngày kể từ ngày nhập hàng đến hạn thanh toán công nợ (0 = thanh toán ngay)."
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Nhà cung cấp"
        verbose_name_plural = "Danh mục nhà cung cấp"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"
