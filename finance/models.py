from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from accounts.models import BaseModel

class LedgerType(models.TextChoices):
    RECEIPT = 'RECEIPT', 'Thu tiền'
    PAYMENT = 'PAYMENT', 'Chi tiền'

class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Tiền mặt'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Chuyển khoản'

class ReferenceType(models.TextChoices):
    SALES_ORDER = 'SALES_ORDER', 'Thu tiền bán hàng (Đơn hàng)'
    PAYABLE = 'PAYABLE', 'Chi thanh toán công nợ NCC'
    PAYROLL = 'PAYROLL', 'Chi trả lương nhân viên (Bảng lương)'
    OTHER_INCOME = 'OTHER_INCOME', 'Thu khác'
    OTHER_EXPENSE = 'OTHER_EXPENSE', 'Chi khác'
    REVERSAL = 'REVERSAL', 'Bút toán đảo điều chỉnh'

class CashLedger(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã bút toán")
    entry_date = models.DateTimeField(default=timezone.now, verbose_name="Ngày ghi sổ")
    transaction_type = models.CharField(
        max_length=10,
        choices=LedgerType.choices,
        verbose_name="Loại bút toán (Thu/Chi)"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Số tiền (VNĐ)"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="Hình thức thanh toán"
    )
    reference_type = models.CharField(
        max_length=30,
        choices=ReferenceType.choices,
        default=ReferenceType.OTHER_INCOME,
        verbose_name="Loại chứng từ gốc"
    )
    reference_id = models.CharField(max_length=100, blank=True, verbose_name="Mã chứng từ gốc")
    reason = models.TextField(verbose_name="Lý do thu / chi (Bắt buộc theo BR17)")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_ledgers',
        verbose_name="Kế toán ghi sổ"
    )
    is_reversed = models.BooleanField(
        default=False,
        verbose_name="Đã bị đảo",
        help_text="Đánh dấu Có nếu bút toán này đã được điều chỉnh bằng một bút toán đảo."
    )
    reversal_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversals',
        verbose_name="Đảo cho bút toán"
    )

    class Meta:
        verbose_name = "Bút toán sổ quỹ"
        verbose_name_plural = "Sổ quỹ thu - chi (ERP)"
        ordering = ['-entry_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name='cash_ledger_amount_non_negative',
            ),
        ]

    def __str__(self):
        return f"[{self.get_transaction_type_display()}] {self.code} - {self.amount:,.0f} đ ({self.get_payment_method_display()})"

class PayableStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Chưa thanh toán'
    PARTIAL = 'PARTIAL', 'Thanh toán một phần'
    PAID = 'PAID', 'Đã thanh toán đủ'

class Payable(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã công nợ")
    supplier = models.ForeignKey(
        'catalog.Supplier',
        on_delete=models.PROTECT,
        related_name='payables',
        verbose_name="Nhà cung cấp"
    )
    purchase_receipt = models.OneToOneField(
        'purchasing.PurchaseReceipt',
        on_delete=models.PROTECT,
        related_name='payable_record',
        verbose_name="Phiếu nhập gốc"
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Tổng nợ phải trả (VNĐ)"
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Số tiền đã trả (VNĐ)"
    )
    remaining_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Số tiền còn nợ (VNĐ)"
    )
    due_date = models.DateField(verbose_name="Hạn thanh toán")
    status = models.CharField(
        max_length=20,
        choices=PayableStatus.choices,
        default=PayableStatus.UNPAID,
        verbose_name="Trạng thái công nợ"
    )

    class Meta:
        verbose_name = "Công nợ phải trả NCC"
        verbose_name_plural = "Danh mục công nợ phải trả NCC"
        ordering = ['due_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name='payable_total_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(paid_amount__gte=0),
                name='payable_paid_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(remaining_amount__gte=0),
                name='payable_remaining_non_negative',
            ),
            models.CheckConstraint(
                condition=models.Q(paid_amount__lte=models.F('total_amount')),
                name='payable_paid_not_over_total',
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.supplier.name} - Còn nợ: {self.remaining_amount:,.0f} đ"

    @property
    def is_overdue(self):
        return self.remaining_amount > Decimal('0.00') and self.due_date < timezone.now().date()

class PayablePayment(BaseModel):
    payable = models.ForeignKey(
        Payable,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Khoản công nợ"
    )
    payment_date = models.DateTimeField(default=timezone.now, verbose_name="Ngày thanh toán")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Số tiền thanh toán")
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
        verbose_name="Phương thức thanh toán"
    )
    ledger_entry = models.ForeignKey(
        CashLedger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payable_payments',
        verbose_name="Bút toán chi tương ứng"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú thanh toán")

    class Meta:
        verbose_name = "Lịch sử thanh toán công nợ"
        verbose_name_plural = "Lịch sử thanh toán công nợ"
        ordering = ['-payment_date']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='payable_payment_amount_positive',
            ),
        ]
