from django.db import models
from django.utils import timezone
from accounts.models import BaseModel
from decimal import Decimal

class TransactionType(models.TextChoices):
    IN = 'IN', 'Nhập kho mua hàng'
    OUT = 'OUT', 'Xuất kho bán hàng'
    ADJUST_INC = 'ADJUST_INC', 'Điều chỉnh kiểm kê (Tăng)'
    ADJUST_DEC = 'ADJUST_DEC', 'Điều chỉnh kiểm kê (Giảm)'
    WARRANTY_OUT = 'WARRANTY_OUT', 'Xuất kho đổi mới bảo hành'

class InventoryTransaction(BaseModel):
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="Loại giao dịch"
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='inventory_transactions',
        verbose_name="Sản phẩm"
    )
    quantity = models.PositiveIntegerField(verbose_name="Số lượng")
    reference_code = models.CharField(
        max_length=100,
        verbose_name="Mã chứng từ liên quan (Đơn bán, Phiếu nhập, Phiếu kiểm kê)"
    )
    notes = models.TextField(blank=True, verbose_name="Lý do / Diễn giải")
    transaction_date = models.DateTimeField(default=timezone.now, verbose_name="Thời gian giao dịch")

    class Meta:
        verbose_name = "Giao dịch kho"
        verbose_name_plural = "Lịch sử giao dịch kho (Nhập - Xuất - Tồn)"
        ordering = ['-transaction_date']

    def __str__(self):
        return f"[{self.get_transaction_type_display()}] {self.product.name} - SL: {self.quantity} ({self.reference_code})"

class AdjustmentStatus(models.TextChoices):
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Chờ Quản lý phê duyệt'
    APPROVED = 'APPROVED', 'Đã duyệt & Cập nhật tồn kho'
    REJECTED = 'REJECTED', 'Từ chối điều chỉnh'

class StockAdjustment(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã phiếu kiểm kê")
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='stock_adjustments',
        verbose_name="Sản phẩm kiểm kê"
    )
    system_quantity = models.IntegerField(verbose_name="Tồn hệ thống")
    actual_quantity = models.IntegerField(verbose_name="Tồn thực tế kiểm kê")
    difference_quantity = models.IntegerField(verbose_name="Chênh lệch (Thực tế - Hệ thống)")
    estimated_difference_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Ước tính giá trị chênh lệch (VNĐ)"
    )
    reason = models.TextField(verbose_name="Lý do điều chỉnh (Bắt buộc theo BR07)")
    status = models.CharField(
        max_length=20,
        choices=AdjustmentStatus.choices,
        default=AdjustmentStatus.APPROVED,
        verbose_name="Trạng thái phê duyệt"
    )
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_stock_adjustments',
        verbose_name="Người phê duyệt"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm duyệt")
    approval_notes = models.TextField(blank=True, verbose_name="Ý kiến phê duyệt")

    class Meta:
        verbose_name = "Phiếu kiểm kê & điều chỉnh tồn kho"
        verbose_name_plural = "Danh sách kiểm kê & điều chỉnh kho"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.product.name} (Lệch: {self.difference_quantity})"

