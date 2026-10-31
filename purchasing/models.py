from django.db import models
from django.utils import timezone
from decimal import Decimal
from accounts.models import BaseModel

class ReceiptStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Phiếu nháp'
    COMPLETED = 'COMPLETED', 'Đã hoàn tất nhập kho'
    CANCELLED = 'CANCELLED', 'Đã hủy'

class PurchaseReceipt(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã phiếu nhập")
    supplier = models.ForeignKey(
        'catalog.Supplier',
        on_delete=models.PROTECT,
        related_name='purchase_receipts',
        verbose_name="Nhà cung cấp"
    )
    request = models.ForeignKey(
        'scm.PurchaseRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_receipts',
        verbose_name="Đề nghị nhập hàng đã duyệt"
    )
    receipt_date = models.DateField(default=timezone.now, verbose_name="Ngày nhập hàng")
    status = models.CharField(
        max_length=20,
        choices=ReceiptStatus.choices,
        default=ReceiptStatus.DRAFT,
        verbose_name="Trạng thái phiếu"
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng giá trị phiếu (VNĐ)"
    )
    emergency_reason = models.TextField(
        blank=True,
        verbose_name="Lý do nhập khẩn / ngoài kế hoạch (nếu không tạo từ đề nghị theo BR19)"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm hoàn tất")

    class Meta:
        verbose_name = "Phiếu nhập hàng"
        verbose_name_plural = "Danh mục phiếu nhập hàng"
        ordering = ['-receipt_date', '-created_at']

    def __str__(self):
        return f"{self.code} - {self.supplier.name} ({self.get_status_display()})"

    def recalculate_total(self):
        total = sum(d.total_price for d in self.details.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

class PurchaseDetail(BaseModel):
    receipt = models.ForeignKey(
        PurchaseReceipt,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name="Phiếu nhập"
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='purchase_details',
        verbose_name="Sản phẩm"
    )
    quantity = models.PositiveIntegerField(verbose_name="Số lượng")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Đơn giá nhập (VNĐ)")
    total_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Thành tiền (VNĐ)")
    serials_text = models.TextField(
        blank=True,
        verbose_name="Danh sách Serial/IMEI",
        help_text="Nhập các Serial/IMEI cách nhau bằng dấu phẩy hoặc xuống dòng (bắt buộc với hàng quản lý IMEI)."
    )

    class Meta:
        verbose_name = "Chi tiết phiếu nhập"
        verbose_name_plural = "Chi tiết phiếu nhập"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='purchase_detail_quantity_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name='purchase_detail_unit_price_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(total_price__gte=0),
                name='purchase_detail_total_price_non_negative',
            ),
        ]

    def save(self, *args, **kwargs):
        self.total_price = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} = {self.total_price:,.0f}"
