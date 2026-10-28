from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from devices.models import ProductItem, WarrantyReturn, ItemStatus, WarrantyStatus, WarrantyAction
from auditlog.services import log_activity
import uuid

def generate_warranty_code():
    return f"BH-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

@transaction.atomic
def create_warranty_claim(item, customer, issue_description, action_type=WarrantyAction.REPAIR, user=None, notes=''):
    """
    Creates a warranty claim ticket according to BR14.
    Validates that item was SOLD.
    """
    if item.status != ItemStatus.SOLD:
        raise ValidationError(f"Thiết bị {item.serial_number} có trạng thái '{item.get_status_display()}', không đủ điều kiện tiếp nhận bảo hành (Mã BR14).")

    # Change item status to DEFECTIVE during warranty process
    item.status = ItemStatus.DEFECTIVE
    item.save(update_fields=['status'])

    claim = WarrantyReturn.objects.create(
        code=generate_warranty_code(),
        item=item,
        customer=customer,
        issue_description=issue_description,
        action_type=action_type,
        status=WarrantyStatus.PENDING,
        notes=notes,
        created_by=user
    )

    log_activity(
        user=user,
        action='CREATE',
        obj=claim,
        changes={
            'code': claim.code,
            'serial_number': item.serial_number,
            'action_type': action_type,
            'customer': customer.name
        }
    )
    return claim

@transaction.atomic
def resolve_warranty_claim(claim, status, replacement_item=None, resolution_notes='', user=None):
    """
    Resolves or rejects a warranty claim.
    If REPLACE: consumes replacement_item (must be IN_STOCK), sets it to SOLD, activates warranty.
    """
    if claim.status in [WarrantyStatus.COMPLETED, WarrantyStatus.REJECTED]:
        raise ValidationError(f"Phiếu bảo hành {claim.code} đã hoàn tất hoặc bị từ chối trước đó.")

    today = timezone.now().date()

    if status == WarrantyStatus.COMPLETED:
        if claim.action_type == WarrantyAction.REPAIR:
            # Device repaired and returned to customer
            claim.item.status = ItemStatus.SOLD
            claim.item.save(update_fields=['status'])
        elif claim.action_type == WarrantyAction.REPLACE:
            if not replacement_item:
                raise ValidationError("Trường hợp đổi mới bắt buộc phải chỉ định thiết bị thay thế (Serial/IMEI mới) đang trong kho.")
            if replacement_item.status != ItemStatus.IN_STOCK:
                raise ValidationError(f"Thiết bị thay thế {replacement_item.serial_number} không ở trạng thái 'Trong kho'.")
            
            # Update replacement item
            replacement_item.status = ItemStatus.SOLD
            replacement_item.sales_order = claim.item.sales_order
            replacement_item.activate_warranty(today)
            claim.replacement_item = replacement_item

            # Record inventory transaction for warranty replacement
            from inventory.models import InventoryTransaction
            InventoryTransaction.objects.create(
                transaction_type='WARRANTY_OUT',
                product=replacement_item.product,
                quantity=1,
                reference_code=claim.code,
                notes=f"Xuất đổi mới bảo hành cho máy cũ {claim.item.serial_number}",
                created_by=user
            )

        claim.status = WarrantyStatus.COMPLETED
        claim.resolved_date = today
    elif status == WarrantyStatus.REJECTED:
        # Rejected warranty, return device back to customer in SOLD status
        claim.item.status = ItemStatus.SOLD
        claim.item.save(update_fields=['status'])
        claim.status = WarrantyStatus.REJECTED
        claim.resolved_date = today

    if resolution_notes:
        claim.notes = f"{claim.notes}\n[Xử lý {today}]: {resolution_notes}".strip()

    claim.save()

    log_activity(
        user=user,
        action='UPDATE',
        obj=claim,
        changes={
            'status': claim.status,
            'resolved_date': str(claim.resolved_date),
            'replacement_item': replacement_item.serial_number if replacement_item else 'None'
        }
    )
    return claim

