import re
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from purchasing.models import PurchaseReceipt, PurchaseDetail, ReceiptStatus
from inventory.models import InventoryTransaction, TransactionType
from devices.models import ProductItem, ItemStatus
from finance.models import Payable, PayableStatus
from scm.models import SupplierProduct, PurchaseRequestStatus
from auditlog.services import log_activity
import uuid

def generate_receipt_code():
    return f"PN-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

def parse_serials(serials_text):
    if not serials_text:
        return []
    # Split by comma, semicolon, newline or spaces
    raw_list = re.split(r'[,;\n\r\t]+', serials_text)
    return [s.strip() for s in raw_list if s.strip()]

@transaction.atomic
def complete_purchase_receipt(receipt, user):
    """
    Completes purchase receipt according to business rules:
    - BR04: Only COMPLETED updates stock & creates payable.
    - BR13: Serial/IMEI must be unique.
    - BR15: Automatically creates exactly ONE Payable record.
    - Idempotent: cannot be completed multiple times.
    """
    if receipt.status == ReceiptStatus.COMPLETED:
        raise ValidationError(f"Phiếu nhập {receipt.code} đã ở trạng thái Hoàn tất trước đó.")
    if receipt.status == ReceiptStatus.CANCELLED:
        raise ValidationError(f"Không thể hoàn tất phiếu nhập {receipt.code} đã bị hủy.")

    details = receipt.details.select_related('product').all()
    if not details.exists():
        raise ValidationError("Phiếu nhập chưa có chi tiết sản phẩm nào.")

    # Check emergency reason if not created from request (BR19)
    if not receipt.request and not receipt.emergency_reason:
        receipt.emergency_reason = "Nhập hàng phát sinh trực tiếp tại kho"

    total_amount = Decimal('0.00')

    # Process each product detail
    for detail in details:
        product = detail.product
        qty = detail.quantity
        line_total = detail.unit_price * Decimal(str(qty))
        total_amount += line_total

        # Update product cost price
        product.cost_price = detail.unit_price
        product.save(update_fields=['cost_price'])

        # If product requires Serial/IMEI tracking (BR11, BR13)
        if product.has_serial:
            serials = parse_serials(detail.serials_text)
            if len(serials) != qty:
                raise ValidationError(
                    f"Sản phẩm '{product.name}' yêu cầu khai báo đúng {qty} mã Serial/IMEI, "
                    f"nhưng hiện có {len(serials)} mã (Mã BR11)."
                )

            # Check duplicates in batch
            if len(serials) != len(set(serials)):
                raise ValidationError(f"Phát hiện mã Serial/IMEI bị trùng lặp ngay trong danh sách nhập của sản phẩm '{product.name}'.")

            # Check duplicates in database
            existing = ProductItem.objects.filter(serial_number__in=serials).values_list('serial_number', flat=True)
            if existing:
                raise ValidationError(f"Mã Serial/IMEI sau đã tồn tại trong hệ thống: {', '.join(existing)} (Mã BR13).")

            # Create items in stock
            items_to_create = [
                ProductItem(
                    serial_number=sn,
                    product=product,
                    status=ItemStatus.IN_STOCK,
                    purchase_receipt=receipt,
                    warranty_months=12,
                    created_by=user
                )
                for sn in serials
            ]
            ProductItem.objects.bulk_create(items_to_create)

        # Record inventory transaction (IN)
        InventoryTransaction.objects.create(
            transaction_type=TransactionType.IN,
            product=product,
            quantity=qty,
            reference_code=receipt.code,
            notes=f"Nhập kho từ NCC: {receipt.supplier.name}",
            created_by=user
        )

        # Update SupplierProduct catalog info
        SupplierProduct.objects.update_or_create(
            supplier=receipt.supplier,
            product=product,
            defaults={
                'last_purchase_price': detail.unit_price,
            }
        )

    receipt.total_amount = total_amount
    receipt.status = ReceiptStatus.COMPLETED
    receipt.completed_at = timezone.now()
    receipt.save()

    # BR15: Automatically create exactly one Payable record
    due_date = receipt.receipt_date + timedelta(days=receipt.supplier.payment_terms_days)
    payable, created = Payable.objects.get_or_create(
        purchase_receipt=receipt,
        defaults={
            'code': f"CN-{receipt.code}",
            'supplier': receipt.supplier,
            'total_amount': total_amount,
            'paid_amount': Decimal('0.00'),
            'remaining_amount': total_amount,
            'due_date': due_date,
            'status': PayableStatus.UNPAID,
            'created_by': user
        }
    )

    # If linked to a purchase request, update request status and record delivery performance
    if receipt.request:
        req = receipt.request
        req.status = PurchaseRequestStatus.COMPLETED
        req.save(update_fields=['status'])
        
        # Calculate delivery days
        if req.approved_at:
            lead_days = (receipt.receipt_date - req.approved_at.date()).days
            # update standard lead days in supplier_product
            for detail in details:
                sp = SupplierProduct.objects.filter(supplier=receipt.supplier, product=detail.product).first()
                if sp and (sp.standard_lead_days == 0 or lead_days > 0):
                    sp.standard_lead_days = max(1, lead_days)
                    sp.save(update_fields=['standard_lead_days'])

    log_activity(
        user=user,
        action='COMPLETE',
        obj=receipt,
        changes={
            'code': receipt.code,
            'supplier': receipt.supplier.name,
            'total_amount': str(total_amount),
            'payable_code': payable.code
        }
    )
    return receipt

@transaction.atomic
def cancel_purchase_receipt(receipt, user, reason=''):
    """Cancels a draft purchase receipt. Does not modify inventory or finance."""
    if receipt.status != ReceiptStatus.DRAFT:
        raise ValidationError(f"Chỉ có thể hủy phiếu nhập ở trạng thái Nháp. Phiếu {receipt.code} đang ở trạng thái '{receipt.get_status_display()}'.")

    receipt.status = ReceiptStatus.CANCELLED
    receipt.notes = f"{receipt.notes}\n[Hủy phiếu]: {reason}".strip()
    receipt.save()

    log_activity(
        user=user,
        action='CANCEL',
        obj=receipt,
        changes={'code': receipt.code, 'status': 'CANCELLED', 'reason': reason}
    )
    return receipt

