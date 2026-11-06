from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import BaseModel

class ItemStatus(models.TextChoices):
    IN_STOCK = 'IN_STOCK', 'Trong kho'
    SOLD = 'SOLD', 'Đã xuất bán'
    DEFECTIVE = 'DEFECTIVE', 'Lỗi / Chờ xử lý bảo hành'
    RETURNED = 'RETURNED', 'Đã trả nhà cung cấp'

class ProductItem(BaseModel):
    serial_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Mã Serial/IMEI"
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.PROTECT,
        related_name='items',
        verbose_name="Sản phẩm"
    )
    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.IN_STOCK,
        verbose_name="Trạng thái thiết bị"
    )
    purchase_receipt = models.ForeignKey(
        'purchasing.PurchaseReceipt',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        verbose_name="Phiếu nhập gốc"
    )
    sales_order = models.ForeignKey(
        'sales.SalesOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        verbose_name="Đơn bán hàng"
    )
    warehouse = models.ForeignKey(
        'inventory.Warehouse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_items',
        verbose_name="Kho lưu trữ"
    )
    warranty_months = models.PositiveIntegerField(default=12, verbose_name="Thời hạn bảo hành (tháng)")
    warranty_start_date = models.DateField(null=True, blank=True, verbose_name="Ngày kích hoạt bảo hành")
    warranty_end_date = models.DateField(null=True, blank=True, verbose_name="Hạn bảo hành")

    class Meta:
        verbose_name = "Thiết bị Serial/IMEI"
        verbose_name_plural = "Danh sách thiết bị (Serial/IMEI)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} (SN: {self.serial_number}) - {self.get_status_display()}"

    def activate_warranty(self, start_date=None):
        if not start_date:
            start_date = timezone.now().date()
        self.warranty_start_date = start_date
        self.warranty_end_date = start_date + timedelta(days=self.warranty_months * 30)
        self.save()

    def is_warranty_valid(self, check_date=None):
        if not check_date:
            check_date = timezone.now().date()
        if self.status != ItemStatus.SOLD:
            return False
        if not self.warranty_end_date:
            return False
        return self.warranty_end_date >= check_date

class WarrantyAction(models.TextChoices):
    REPAIR = 'REPAIR', 'Sửa chữa bảo hành'
    REPLACE = 'REPLACE', 'Đổi máy mới (Đổi 1-1)'

class WarrantyStatus(models.TextChoices):
    PENDING = 'PENDING', 'Tiếp nhận mới'
    PROCESSING = 'PROCESSING', 'Đang xử lý'
    COMPLETED = 'COMPLETED', 'Đã hoàn tất xử lý'
    REJECTED = 'REJECTED', 'Từ chối bảo hành'

class WarrantyReturn(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã phiếu bảo hành")
    item = models.ForeignKey(
        ProductItem,
        on_delete=models.PROTECT,
        related_name='warranty_claims',
        verbose_name="Thiết bị bảo hành"
    )
    customer = models.ForeignKey(
        'catalog.Customer',
        on_delete=models.PROTECT,
        related_name='warranty_claims',
        verbose_name="Khách hàng"
    )
    issue_description = models.TextField(verbose_name="Mô tả lỗi kỹ thuật")
    action_type = models.CharField(
        max_length=20,
        choices=WarrantyAction.choices,
        default=WarrantyAction.REPAIR,
        verbose_name="Hướng xử lý"
    )
    replacement_item = models.ForeignKey(
        ProductItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacement_for',
        verbose_name="Thiết bị thay thế (nếu đổi mới)"
    )
    status = models.CharField(
        max_length=20,
        choices=WarrantyStatus.choices,
        default=WarrantyStatus.PENDING,
        verbose_name="Trạng thái xử lý"
    )
    received_date = models.DateField(auto_now_add=True, verbose_name="Ngày tiếp nhận")
    resolved_date = models.DateField(null=True, blank=True, verbose_name="Ngày hoàn tất xử lý")
    notes = models.TextField(blank=True, verbose_name="Ghi chú kỹ thuật")

    class Meta:
        verbose_name = "Phiếu bảo hành / Đổi trả"
        verbose_name_plural = "Danh mục bảo hành / Đổi trả"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.item.product.name} ({self.item.serial_number})"

