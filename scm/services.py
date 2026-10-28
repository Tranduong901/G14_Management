from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Avg

from scm.models import PurchaseRequest, PurchaseRequestDetail, PurchaseRequestStatus, PurchaseRequestSource, SupplierProduct
from purchasing.models import PurchaseReceipt, PurchaseDetail, ReceiptStatus
from catalog.models import Product, Supplier
from devices.models import ProductItem, WarrantyReturn, ItemStatus
from finance.models import Payable, PayableStatus
from auditlog.services import log_activity
import uuid

def generate_request_code():
    return f"DN-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

@transaction.atomic
def submit_purchase_request(request_obj, user):
    """Submits draft request for manager approval."""
    if request_obj.status != PurchaseRequestStatus.DRAFT:
        raise ValidationError(f"Chỉ có thể gửi duyệt đề nghị ở trạng thái Nháp.")
    if not request_obj.details.exists():
        raise ValidationError("Đề nghị nhập hàng chưa có sản phẩm nào.")

    request_obj.status = PurchaseRequestStatus.PENDING
    request_obj.save(update_fields=['status'])

    log_activity(
        user=user,
        action='UPDATE',
        obj=request_obj,
        changes={'code': request_obj.code, 'status': 'PENDING'}
    )
    return request_obj

@transaction.atomic
def approve_purchase_request(request_obj, user):
    """Manager approves purchase request (BR19)."""
    if request_obj.status != PurchaseRequestStatus.PENDING:
        raise ValidationError(f"Đề nghị {request_obj.code} không ở trạng thái Chờ duyệt.")

    request_obj.status = PurchaseRequestStatus.APPROVED
    request_obj.approver = user
    request_obj.approved_at = timezone.now()
    request_obj.save()

    log_activity(
        user=user,
        action='APPROVE',
        obj=request_obj,
        changes={'code': request_obj.code, 'status': 'APPROVED', 'approver': user.username}
    )
    return request_obj

@transaction.atomic
def reject_purchase_request(request_obj, reason, user):
    """Manager rejects purchase request with mandatory reason."""
    if request_obj.status != PurchaseRequestStatus.PENDING:
        raise ValidationError(f"Đề nghị {request_obj.code} không ở trạng thái Chờ duyệt.")
    if not reason or not reason.strip():
        raise ValidationError("Lý do từ chối đề nghị nhập hàng là bắt buộc theo quy định quản trị.")

    request_obj.status = PurchaseRequestStatus.REJECTED
    request_obj.approver = user
    request_obj.approved_at = timezone.now()
    request_obj.rejection_reason = reason.strip()
    request_obj.save()

    log_activity(
        user=user,
        action='REJECT',
        obj=request_obj,
        changes={'code': request_obj.code, 'status': 'REJECTED', 'reason': reason}
    )
    return request_obj

@transaction.atomic
def convert_request_to_receipt(request_obj, user):
    """
    Converts an APPROVED purchase request into a draft PurchaseReceipt (BR19).
    Prevents double conversion.
    """
    if request_obj.status != PurchaseRequestStatus.APPROVED:
        raise ValidationError(
            f"Chỉ đề nghị nhập hàng ở trạng thái 'Đã phê duyệt' mới được phép chuyển thành phiếu nhập "
            f"(Mã BR19). Đề nghị {request_obj.code} đang ở trạng thái '{request_obj.get_status_display()}'."
        )

    # Check if a receipt was already created from this request
    existing_receipt = PurchaseReceipt.objects.filter(request=request_obj).exclude(status=ReceiptStatus.CANCELLED).first()
    if existing_receipt:
        raise ValidationError(f"Đề nghị này đã được chuyển thành phiếu nhập {existing_receipt.code} trước đó.")

    first_detail = request_obj.details.first()
    if not first_detail or not first_detail.suggested_supplier:
        raise ValidationError("Đề nghị chưa có thông tin nhà cung cấp đề xuất để tạo phiếu nhập.")

    supplier = first_detail.suggested_supplier

    from purchasing.services import generate_receipt_code
    receipt = PurchaseReceipt.objects.create(
        code=generate_receipt_code(),
        supplier=supplier,
        request=request_obj,
        receipt_date=timezone.now().date(),
        status=ReceiptStatus.DRAFT,
        notes=f"Tạo tự động từ đề nghị nhập hàng đã duyệt: {request_obj.code}",
        created_by=user
    )

    for d in request_obj.details.all():
        PurchaseDetail.objects.create(
            receipt=receipt,
            product=d.product,
            quantity=d.requested_quantity,
            unit_price=d.estimated_price,
            created_by=user
        )

    receipt.recalculate_total()

    log_activity(
        user=user,
        action='CREATE',
        obj=receipt,
        changes={
            'code': receipt.code,
            'source_request': request_obj.code,
            'total_amount': str(receipt.total_amount)
        }
    )
    return receipt

def get_supplier_performance():
    """
    Computes performance scorecard for each supplier (Mục 2.5.8, TC15, TC24, TC25).
    """
    suppliers = Supplier.objects.all()
    scorecards = []

    for s in suppliers:
        # Completed receipts
        receipts = PurchaseReceipt.objects.filter(supplier=s, status=ReceiptStatus.COMPLETED)
        receipt_count = receipts.count()
        total_spent = receipts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        # Outstanding debt
        total_debt = Payable.objects.filter(supplier=s).exclude(status=PayableStatus.PAID).aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')

        # Warranty return rate
        total_items_supplied = ProductItem.objects.filter(purchase_receipt__supplier=s).count()
        warranty_returns = WarrantyReturn.objects.filter(item__purchase_receipt__supplier=s).count()
        warranty_rate = (warranty_returns / total_items_supplied * 100) if total_items_supplied > 0 else 0.0

        # Lead time calculation from requests
        lead_days_list = []
        on_time_count = 0
        total_delivered_orders = 0

        for r in receipts:
            if r.request and r.request.approved_at:
                actual_days = (r.receipt_date - r.request.approved_at.date()).days
                lead_days_list.append(actual_days)
                total_delivered_orders += 1
                if actual_days <= s.payment_terms_days:  # or comparison with standard lead days
                    on_time_count += 1

        avg_lead_days = (sum(lead_days_list) / len(lead_days_list)) if lead_days_list else 3.0
        on_time_rate = (on_time_count / total_delivered_orders * 100) if total_delivered_orders > 0 else 100.0

        scorecards.append({
            'supplier': s,
            'receipt_count': receipt_count,
            'total_spent': total_spent,
            'total_debt': total_debt,
            'avg_lead_days': round(avg_lead_days, 1),
            'on_time_rate': round(on_time_rate, 1),
            'warranty_returns': warranty_returns,
            'warranty_rate': round(warranty_rate, 1),
        })

    return scorecards

