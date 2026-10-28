from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from decimal import Decimal
import uuid

from inventory.models import InventoryTransaction, StockAdjustment, TransactionType, AdjustmentStatus
from auditlog.services import log_activity

def generate_adjustment_code():
    return f"KK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

@transaction.atomic
def create_stock_adjustment(product, actual_quantity, reason, user):
    """
    Creates a stock adjustment / audit record.
    BR07: Mandatory reason, timestamp, and executor.
    If value difference exceeds limit, sets to PENDING_APPROVAL unless user is QL/ADMIN.
    """
    if not reason or not reason.strip():
        raise ValidationError("Lý do điều chỉnh tồn kho là bắt buộc theo quy định kiểm soát nội bộ (Mã BR07).")

    system_quantity = product.get_current_stock()
    difference_qty = actual_quantity - system_quantity
    
    if difference_qty == 0:
        raise ValidationError("Số lượng thực tế khớp với tồn hệ thống, không cần lập phiếu điều chỉnh.")

    diff_val = abs(Decimal(str(difference_qty)) * product.cost_price)
    limit = Decimal(str(getattr(settings, 'AUDIT_ADJUSTMENT_LIMIT', 5000000)))

    # Determine if approval is needed
    is_manager = user.is_superuser or getattr(user, 'role', '') in ['QL', 'ADMIN']
    needs_approval = (diff_val > limit) and not is_manager

    status = AdjustmentStatus.PENDING_APPROVAL if needs_approval else AdjustmentStatus.APPROVED

    adjustment = StockAdjustment.objects.create(
        code=generate_adjustment_code(),
        product=product,
        system_quantity=system_quantity,
        actual_quantity=actual_quantity,
        difference_quantity=difference_qty,
        estimated_difference_value=diff_val,
        reason=reason.strip(),
        status=status,
        created_by=user,
        approved_by=user if not needs_approval else None,
        approved_at=timezone.now() if not needs_approval else None
    )

    if not needs_approval:
        # Apply immediately to inventory
        apply_adjustment_transaction(adjustment, user)

    log_activity(
        user=user,
        action='ADJUST',
        obj=adjustment,
        changes={
            'code': adjustment.code,
            'product': product.name,
            'diff_qty': difference_qty,
            'status': status
        }
    )
    return adjustment

@transaction.atomic
def apply_adjustment_transaction(adjustment, user):
    """Generates the inventory transaction reflecting the adjustment."""
    product = adjustment.product
    diff = adjustment.difference_quantity

    if diff > 0:
        tx_type = TransactionType.ADJUST_INC
        qty = diff
    else:
        tx_type = TransactionType.ADJUST_DEC
        qty = abs(diff)

    InventoryTransaction.objects.create(
        transaction_type=tx_type,
        product=product,
        quantity=qty,
        reference_code=adjustment.code,
        notes=f"Điều chỉnh kiểm kê: {adjustment.reason}",
        created_by=user
    )

@transaction.atomic
def approve_stock_adjustment(adjustment, user, approval_notes=''):
    """Manager approves a pending stock adjustment."""
    if adjustment.status != AdjustmentStatus.PENDING_APPROVAL:
        raise ValidationError(f"Phiếu điều chỉnh {adjustment.code} không ở trạng thái Chờ duyệt.")

    adjustment.status = AdjustmentStatus.APPROVED
    adjustment.approved_by = user
    adjustment.approved_at = timezone.now()
    adjustment.approval_notes = approval_notes
    adjustment.save()

    apply_adjustment_transaction(adjustment, user)

    log_activity(
        user=user,
        action='APPROVE',
        obj=adjustment,
        changes={'code': adjustment.code, 'status': 'APPROVED'}
    )
    return adjustment

@transaction.atomic
def reject_stock_adjustment(adjustment, user, rejection_reason=''):
    """Manager rejects a pending stock adjustment."""
    if adjustment.status != AdjustmentStatus.PENDING_APPROVAL:
        raise ValidationError(f"Phiếu điều chỉnh {adjustment.code} không ở trạng thái Chờ duyệt.")

    adjustment.status = AdjustmentStatus.REJECTED
    adjustment.approved_by = user
    adjustment.approved_at = timezone.now()
    adjustment.approval_notes = f"Từ chối: {rejection_reason}"
    adjustment.save()

    log_activity(
        user=user,
        action='REJECT',
        obj=adjustment,
        changes={'code': adjustment.code, 'status': 'REJECTED', 'reason': rejection_reason}
    )
    return adjustment

