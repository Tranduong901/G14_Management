from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum

from finance.models import CashLedger, Payable, PayablePayment, LedgerType, PaymentMethod, PayableStatus, ReferenceType
from auditlog.services import log_activity
import uuid

def generate_ledger_code(prefix='PC'):
    return f"{prefix}-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

def generate_payment_code():
    return f"TT-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

@transaction.atomic
def pay_payable(payable, amount, payment_method=PaymentMethod.BANK_TRANSFER, notes='', user=None):
    """
    Executes payment for supplier debt:
    - BR16: Must link to payable and cannot exceed remaining debt.
    - Creates Chi entry in CashLedger.
    - Updates payable balance and status (PARTIAL or PAID).
    """
    payable = Payable.objects.select_for_update().select_related(
        'supplier',
        'purchase_receipt',
    ).get(pk=payable.pk)
    amount = Decimal(str(amount))
    if amount <= Decimal('0.00'):
        raise ValidationError("Số tiền thanh toán phải lớn hơn 0.")

    if amount > payable.remaining_amount:
        raise ValidationError(
            f"Số tiền chi trả ({amount:,.0f} đ) không được vượt quá số còn nợ của khoản công nợ "
            f"({payable.remaining_amount:,.0f} đ) (Mã BR16)."
        )

    # 1. Create CashLedger Chi entry
    ledger_entry = CashLedger.objects.create(
        code=generate_ledger_code(prefix='PC'),
        transaction_type=LedgerType.PAYMENT,
        amount=amount,
        payment_method=payment_method,
        reference_type=ReferenceType.PAYABLE,
        reference_id=payable.code,
        reason=f"Chi thanh toán tiền hàng cho NCC: {payable.supplier.name} theo phiếu {payable.purchase_receipt.code}. {notes}".strip(),
        recorded_by=user,
        created_by=user
    )

    # 2. Create PayablePayment record
    payment_rec = PayablePayment.objects.create(
        payable=payable,
        amount=amount,
        payment_method=payment_method,
        ledger_entry=ledger_entry,
        notes=notes,
        created_by=user
    )

    # 3. Update payable numbers
    payable.paid_amount += amount
    payable.remaining_amount -= amount
    if payable.remaining_amount == Decimal('0.00'):
        payable.status = PayableStatus.PAID
    else:
        payable.status = PayableStatus.PARTIAL
    payable.save()

    log_activity(
        user=user,
        action='PAYMENT',
        obj=payable,
        changes={
            'payable_code': payable.code,
            'paid_amount': str(amount),
            'remaining_amount': str(payable.remaining_amount),
            'ledger_code': ledger_entry.code,
            'status': payable.status
        }
    )
    return payment_rec

@transaction.atomic
def create_other_ledger_entry(transaction_type, amount, payment_method=PaymentMethod.CASH, reason='', user=None):
    """Creates a manual other income / expense entry with mandatory reason (BR17)."""
    amount = Decimal(str(amount))
    if amount <= Decimal('0.00'):
        raise ValidationError("Số tiền phải lớn hơn 0.")
    if not reason or not reason.strip():
        raise ValidationError("Lý do thu / chi là bắt buộc theo quy định kiểm soát sổ quỹ (Mã BR17).")

    prefix = 'PT' if transaction_type == LedgerType.RECEIPT else 'PC'
    ref_type = ReferenceType.OTHER_INCOME if transaction_type == LedgerType.RECEIPT else ReferenceType.OTHER_EXPENSE

    entry = CashLedger.objects.create(
        code=generate_ledger_code(prefix=prefix),
        transaction_type=transaction_type,
        amount=amount,
        payment_method=payment_method,
        reference_type=ref_type,
        reference_id='',
        reason=reason.strip(),
        recorded_by=user,
        created_by=user
    )

    log_activity(
        user=user,
        action='CREATE',
        obj=entry,
        changes={
            'code': entry.code,
            'type': transaction_type,
            'amount': str(amount),
            'reason': reason
        }
    )
    return entry

@transaction.atomic
def reverse_ledger_entry(original_entry, reason, user=None):
    """
    Executes reversing entry (bút toán đảo) for an existing ledger entry according to BR17.
    Does not modify original entry, creates opposite entry with reference.
    """
    if original_entry.is_reversed:
        raise ValidationError(f"Bút toán {original_entry.code} đã được đảo trước đó.")
    if not reason or not reason.strip():
        raise ValidationError("Lý do lập bút toán đảo là bắt buộc (Mã BR17).")

    # Determine opposite type
    opp_type = LedgerType.PAYMENT if original_entry.transaction_type == LedgerType.RECEIPT else LedgerType.RECEIPT
    prefix = 'BTD'

    # If original entry was a payable payment, reverse the payable remaining amount
    if original_entry.reference_type == ReferenceType.PAYABLE:
        payable = Payable.objects.filter(code=original_entry.reference_id).first()
        if payable:
            payable.paid_amount -= original_entry.amount
            payable.remaining_amount += original_entry.amount
            if payable.paid_amount == Decimal('0.00'):
                payable.status = PayableStatus.UNPAID
            else:
                payable.status = PayableStatus.PARTIAL
            payable.save()

    original_entry.is_reversed = True
    original_entry.save(update_fields=['is_reversed'])

    reversal = CashLedger.objects.create(
        code=generate_ledger_code(prefix=prefix),
        transaction_type=opp_type,
        amount=original_entry.amount,
        payment_method=original_entry.payment_method,
        reference_type=ReferenceType.REVERSAL,
        reference_id=original_entry.code,
        reason=f"Bút toán đảo cho chứng từ {original_entry.code}. Lý do: {reason}".strip(),
        reversal_of=original_entry,
        recorded_by=user,
        created_by=user
    )

    log_activity(
        user=user,
        action='REVERSE',
        obj=original_entry,
        changes={
            'original_code': original_entry.code,
            'reversal_code': reversal.code,
            'amount': str(original_entry.amount),
            'reason': reason
        }
    )
    return reversal

def get_financial_summary():
    """Computes cashbook balances and payables status."""
    today = timezone.now().date()
    
    # Active ledger entries (exclude if reversed pairs or handle simple sum)
    # Sum of all Receipts vs Payments
    receipts = CashLedger.objects.filter(transaction_type=LedgerType.RECEIPT).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    payments = CashLedger.objects.filter(transaction_type=LedgerType.PAYMENT).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_balance = receipts - payments

    cash_receipts = CashLedger.objects.filter(transaction_type=LedgerType.RECEIPT, payment_method=PaymentMethod.CASH).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_payments = CashLedger.objects.filter(transaction_type=LedgerType.PAYMENT, payment_method=PaymentMethod.CASH).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_balance = cash_receipts - cash_payments

    bank_receipts = CashLedger.objects.filter(transaction_type=LedgerType.RECEIPT, payment_method=PaymentMethod.BANK_TRANSFER).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    bank_payments = CashLedger.objects.filter(transaction_type=LedgerType.PAYMENT, payment_method=PaymentMethod.BANK_TRANSFER).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    bank_balance = bank_receipts - bank_payments

    # Payables summary
    total_payable = Payable.objects.exclude(status=PayableStatus.PAID).aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')
    overdue_payables = Payable.objects.filter(remaining_amount__gt=0, due_date__lt=today)
    overdue_amount = overdue_payables.aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')
    overdue_count = overdue_payables.count()

    return {
        'total_receipts': receipts,
        'total_payments': payments,
        'total_balance': total_balance,
        'cash_balance': cash_balance,
        'bank_balance': bank_balance,
        'total_payable': total_payable,
        'overdue_amount': overdue_amount,
        'overdue_count': overdue_count,
    }
