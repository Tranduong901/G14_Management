import re
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from sales.models import SalesOrder, SalesOrderDetail, OrderStatus, PaymentStatus, PaymentMethod
from inventory.models import InventoryTransaction, TransactionType
from devices.models import ProductItem, ItemStatus
from finance.models import CashLedger, LedgerType, PaymentMethod as FinancePaymentMethod
from auditlog.services import log_activity
import uuid

def generate_order_code():
    return f"DH-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

def parse_serials(serials_text):
    if not serials_text:
        return []
    raw_list = re.split(r'[,;\n\r\t]+', serials_text)
    return [s.strip() for s in raw_list if s.strip()]

@transaction.atomic
def complete_sales_order(order, payment_method=PaymentMethod.CASH, user=None):
    """
    Completes sales order:
    - BR03: Cannot oversell available stock.
    - BR04: Only COMPLETED records revenue, reduces inventory, and records in cash ledger.
    - BR11 & BR13: Serial/IMEI must be IN_STOCK and transitions to SOLD + activates warranty.
    - BR12: Sales KPI recorded for the assigned staff.
    - BR17: Records CashLedger Thu entry immediately upon payment.
    - Idempotent: cannot be completed multiple times.
    """
    if order.status == OrderStatus.COMPLETED:
        raise ValidationError(f"Đơn hàng {order.code} đã hoàn tất trước đó. Không cho phép ghi nhận trùng doanh thu (Mã BR04).")
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError(f"Không thể hoàn tất đơn hàng {order.code} đã bị hủy.")

    details = order.details.select_related('product').all()
    if not details.exists():
        raise ValidationError("Đơn hàng chưa có chi tiết sản phẩm nào.")

    total_amount = Decimal('0.00')
    today = timezone.now().date()

    # Process each order line
    for detail in details:
        product = detail.product
        qty = detail.quantity
        line_total = detail.unit_price * Decimal(str(qty))
        total_amount += line_total

        # Check available stock (BR03)
        available_stock = product.get_current_stock()
        if available_stock < qty:
            raise ValidationError(
                f"Sản phẩm '{product.name}' không đủ tồn kho khả dụng để hoàn tất đơn hàng "
                f"(Yêu cầu: {qty}, Tồn khả dụng: {available_stock}) (Mã BR03)."
            )

        # Handle Serial/IMEI products (BR11, BR13)
        if product.has_serial:
            serials = parse_serials(detail.selected_serials_text)
            if len(serials) != qty:
                # If user didn't enter serials manually, auto-assign from available in-stock devices
                avail_items = list(ProductItem.objects.filter(product=product, status=ItemStatus.IN_STOCK)[:qty])
                if len(avail_items) < qty:
                    raise ValidationError(f"Không đủ thiết bị có Serial/IMEI khả dụng trong kho cho sản phẩm '{product.name}'.")
                serials = [item.serial_number for item in avail_items]
                detail.selected_serials_text = ', '.join(serials)
                detail.save(update_fields=['selected_serials_text'])

            # Verify all serials are currently IN_STOCK
            items = list(ProductItem.objects.filter(product=product, serial_number__in=serials))
            if len(items) != len(serials):
                found_serials = {it.serial_number for it in items}
                missing = set(serials) - found_serials
                raise ValidationError(f"Các mã Serial/IMEI sau không tồn tại trong kho cho sản phẩm {product.name}: {', '.join(missing)}.")

            for it in items:
                if it.status != ItemStatus.IN_STOCK:
                    raise ValidationError(
                        f"Thiết bị Serial/IMEI '{it.serial_number}' đang ở trạng thái '{it.get_status_display()}', "
                        f"không thể xuất bán (Mã BR13)."
                    )
                # Mark as sold and activate warranty (BR11)
                it.status = ItemStatus.SOLD
                it.sales_order = order
                it.activate_warranty(today)

        # Deduct stock via inventory transaction (OUT)
        InventoryTransaction.objects.create(
            transaction_type=TransactionType.OUT,
            product=product,
            quantity=qty,
            reference_code=order.code,
            notes=f"Xuất bán cho khách hàng: {order.customer.name}",
            created_by=user
        )

    order.total_amount = total_amount
    order.payment_method = payment_method
    order.payment_status = PaymentStatus.PAID
    order.status = OrderStatus.COMPLETED
    order.completed_at = timezone.now()
    if user and not order.staff:
        order.staff = user
    order.save()

    # BR17: Automatically record Thu (RECEIPT) entry into CashLedger
    cash_method = FinancePaymentMethod.CASH if payment_method == PaymentMethod.CASH else FinancePaymentMethod.BANK_TRANSFER
    ledger_entry, created = CashLedger.objects.get_or_create(
        reference_type='SALES_ORDER',
        reference_id=order.code,
        defaults={
            'code': f"PT-{order.code}",
            'transaction_type': LedgerType.RECEIPT,
            'amount': total_amount,
            'payment_method': cash_method,
            'reason': f"Thu tiền bán hàng đơn {order.code} - Khách: {order.customer.name}",
            'recorded_by': user,
            'created_by': user,
        }
    )

    log_activity(
        user=user,
        action='COMPLETE',
        obj=order,
        changes={
            'code': order.code,
            'customer': order.customer.name,
            'total_amount': str(total_amount),
            'payment_method': payment_method,
            'ledger_code': ledger_entry.code
        }
    )
    return order

@transaction.atomic
def cancel_sales_order(order, user, reason=''):
    """Cancels a draft sales order. Does not modify inventory or revenue (BR04)."""
    if order.status != OrderStatus.DRAFT:
        raise ValidationError(f"Chỉ có thể hủy đơn hàng ở trạng thái Nháp. Đơn {order.code} đang ở trạng thái '{order.get_status_display()}'.")

    order.status = OrderStatus.CANCELLED
    order.notes = f"{order.notes}\n[Hủy đơn]: {reason}".strip()
    order.save()

    log_activity(
        user=user,
        action='CANCEL',
        obj=order,
        changes={'code': order.code, 'status': 'CANCELLED', 'reason': reason}
    )
    return order

