from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from decimal import Decimal
import uuid

from inventory.models import InventoryTransaction, StockAdjustment, TransactionType, AdjustmentStatus
from devices.models import ProductItem, ItemStatus
from auditlog.services import log_activity

def generate_adjustment_code():
    return f"KK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

@transaction.atomic
def create_stock_adjustment(product, actual_quantity, reason, user, warehouse=None):
    """
    Creates a stock adjustment / audit record.
    BR07: Mandatory reason, timestamp, and executor.
    If value difference exceeds limit, sets to PENDING_APPROVAL unless user is QL/ADMIN.
    """
    if not reason or not reason.strip():
        raise ValidationError("Lý do điều chỉnh tồn kho là bắt buộc theo quy định kiểm soát nội bộ (Mã BR07).")
    if user and user.branch_id and warehouse is None:
        raise ValidationError("Tài khoản thuộc chi nhánh phải chỉ định kho kiểm kê.")
    if warehouse and user and not user.can_access_branch(warehouse.branch):
        raise ValidationError("Bạn không có quyền kiểm kê kho thuộc chi nhánh này.")

    system_quantity = product.get_current_stock(warehouse=warehouse)
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
        warehouse=warehouse,
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
        warehouse=adjustment.warehouse,
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
def transfer_stock(product, quantity, source_warehouse, target_warehouse, user,
                   serial_numbers=None):
    """Moves stock between two warehouses without changing company total stock."""
    if source_warehouse.pk == target_warehouse.pk:
        raise ValidationError("Kho nguồn và kho đích phải khác nhau.")
    if quantity <= 0:
        raise ValidationError("Số lượng chuyển kho phải lớn hơn 0.")
    if not user.is_superuser and getattr(user, 'data_scope', '') != 'ALL':
        allowed = {getattr(user, 'branch_id', None)}
        if source_warehouse.branch_id not in allowed or target_warehouse.branch_id not in allowed:
            raise ValidationError("Bạn không có quyền chuyển hàng giữa các chi nhánh ngoài phạm vi được cấp.")

    available = product.get_current_stock(warehouse=source_warehouse)
    if available < quantity:
        raise ValidationError(f"Kho nguồn không đủ tồn khả dụng: {available}.")

    if product.has_serial:
        serials = [sn.strip() for sn in (serial_numbers or []) if sn.strip()]
        if len(serials) != quantity or len(set(serials)) != quantity:
            raise ValidationError("Phải chỉ định đúng các Serial/IMEI cần chuyển kho.")
        items = list(ProductItem.objects.select_for_update().filter(
            product=product,
            warehouse=source_warehouse,
            status=ItemStatus.IN_STOCK,
            serial_number__in=serials,
        ))
        if len(items) != quantity:
            raise ValidationError("Một hoặc nhiều Serial/IMEI không thuộc kho nguồn.")
        ProductItem.objects.filter(pk__in=[item.pk for item in items]).update(
            warehouse=target_warehouse,
        )

    reference = f"CK-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    InventoryTransaction.objects.create(
        transaction_type=TransactionType.OUT,
        product=product,
        quantity=quantity,
        warehouse=source_warehouse,
        reference_code=reference,
        notes=f"Chuyển kho đến {target_warehouse.code}",
        created_by=user,
    )
    InventoryTransaction.objects.create(
        transaction_type=TransactionType.IN,
        product=product,
        quantity=quantity,
        warehouse=target_warehouse,
        reference_code=reference,
        notes=f"Chuyển kho từ {source_warehouse.code}",
        created_by=user,
    )
    return reference

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
