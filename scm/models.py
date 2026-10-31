from django.db import models
from django.conf import settings
from decimal import Decimal
from accounts.models import BaseModel

class SupplierProduct(BaseModel):
    supplier = models.ForeignKey(
        'catalog.Supplier',
        on_delete=models.CASCADE,
        related_name='supplier_pricings',
        verbose_name="Nhà cung cấp"
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='supplier_pricings',
        verbose_name="Sản phẩm"
    )
    last_purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Giá nhập gần nhất (VNĐ)"
    )
    standard_lead_days = models.PositiveIntegerField(
        default=3,
        verbose_name="Thời gian giao hàng chuẩn (ngày)"
    )

    class Meta:
        verbose_name = "Hồ sơ giá & thời gian giao NCC"
        verbose_name_plural = "Hồ sơ nhà cung cấp theo sản phẩm"
        unique_together = ['supplier', 'product']

    def __str__(self):
        return f"{self.supplier.name} - {self.product.name}: {self.last_purchase_price:,.0f} đ ({self.standard_lead_days} ngày)"

class PurchaseRequestStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Đề nghị nháp'
    PENDING = 'PENDING', 'Chờ Quản lý phê duyệt'
    APPROVED = 'APPROVED', 'Đã phê duyệt'
    REJECTED = 'REJECTED', 'Từ chối'
    COMPLETED = 'COMPLETED', 'Đã chuyển phiếu nhập & nhập kho'

class PurchaseRequestSource(models.TextChoices):
    MANUAL = 'MANUAL', 'Lập thủ công'
    SYSTEM_SUGGESTION = 'SYSTEM_SUGGESTION', 'Gợi ý tự động từ cảnh báo tồn thấp'

class PurchaseRequest(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã đề nghị nhập hàng")
    status = models.CharField(
        max_length=20,
        choices=PurchaseRequestStatus.choices,
        default=PurchaseRequestStatus.DRAFT,
        verbose_name="Trạng thái đề nghị"
    )
    source = models.CharField(
        max_length=20,
        choices=PurchaseRequestSource.choices,
        default=PurchaseRequestSource.MANUAL,
        verbose_name="Nguồn phát sinh"
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_requests',
        verbose_name="Người lập đề nghị"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_requests',
        verbose_name="Người phê duyệt"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm duyệt")
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Lý do từ chối (bắt buộc khi từ chối theo Mục 2.5.8)"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú kế hoạch")

    class Meta:
        verbose_name = "Đề nghị nhập hàng"
        verbose_name_plural = "Danh mục đề nghị nhập hàng (SCM)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"

    def recalculate_estimated_total(self):
        return sum(d.estimated_total for d in self.details.all())

class PurchaseRequestDetail(BaseModel):
    request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name="Đề nghị nhập hàng"
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='request_details',
        verbose_name="Sản phẩm đề xuất"
    )
    suggested_supplier = models.ForeignKey(
        'catalog.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggested_requests',
        verbose_name="Nhà cung cấp đề xuất"
    )
    requested_quantity = models.PositiveIntegerField(verbose_name="Số lượng đề xuất")
    estimated_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Đơn giá dự kiến (VNĐ)"
    )
    estimated_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng tiền dự kiến (VNĐ)"
    )

    class Meta:
        verbose_name = "Chi tiết đề nghị nhập hàng"
        verbose_name_plural = "Chi tiết đề nghị nhập hàng"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_quantity__gt=0),
                name='purchase_request_quantity_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(estimated_price__gte=0),
                name='purchase_request_price_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(estimated_total__gte=0),
                name='purchase_request_total_non_negative',
            ),
        ]

    def save(self, *args, **kwargs):
        self.estimated_total = Decimal(str(self.requested_quantity)) * self.estimated_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.requested_quantity}"
