from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from accounts.models import BaseModel

class OrderStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Đơn nháp'
    COMPLETED = 'COMPLETED', 'Đã hoàn tất'
    CANCELLED = 'CANCELLED', 'Đã hủy'

class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Tiền mặt'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Chuyển khoản ngân hàng'

class PaymentStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Chưa thanh toán'
    PAID = 'PAID', 'Đã thanh toán'

class SalesOrder(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã đơn hàng")
    customer = models.ForeignKey(
        'catalog.Customer',
        on_delete=models.PROTECT,
        related_name='sales_orders',
        verbose_name="Khách hàng"
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_sales_orders',
        verbose_name="Nhân viên bán hàng"
    )
    order_date = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm tạo đơn")
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
        verbose_name="Trạng thái đơn hàng"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Phương thức thanh toán"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        verbose_name="Trạng thái thanh toán"
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng tiền đơn hàng (VNĐ)"
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm hoàn tất")
    notes = models.TextField(blank=True, verbose_name="Ghi chú đơn hàng")

    class Meta:
        verbose_name = "Đơn bán hàng"
        verbose_name_plural = "Danh mục đơn bán hàng"
        ordering = ['-order_date', '-created_at']

    def __str__(self):
        return f"{self.code} - {self.customer.name} ({self.get_status_display()})"

    def recalculate_total(self):
        total = sum(d.total_price for d in self.details.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

class SalesOrderDetail(BaseModel):
    order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name="Đơn hàng"
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='order_details',
        verbose_name="Sản phẩm"
    )
    quantity = models.PositiveIntegerField(verbose_name="Số lượng")
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Đơn giá bán tại thời điểm (BR05)"
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Thành tiền (VNĐ)"
    )
    selected_serials_text = models.TextField(
        blank=True,
        verbose_name="Các mã Serial/IMEI đã chọn",
        help_text="Nhập các Serial/IMEI cách nhau bằng dấu phẩy."
    )

    class Meta:
        verbose_name = "Chi tiết đơn hàng"
        verbose_name_plural = "Chi tiết đơn hàng"

    def save(self, *args, **kwargs):
        self.total_price = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} = {self.total_price:,.0f}"

