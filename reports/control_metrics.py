from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from auditlog.models import AccessDeniedLog, AuditLog
from catalog.models import Product
from devices.models import ItemStatus, ProductItem, WarrantyReturn, WarrantyStatus
from finance.models import CashLedger, LedgerType, Payable, PayableStatus
from inventory.models import AdjustmentStatus, StockAdjustment
from purchasing.models import PurchaseReceipt, ReceiptStatus
from sales.models import OrderStatus, PaymentStatus, SalesOrder, SalesOrderDetail
from scm.models import PurchaseRequest, PurchaseRequestSource, PurchaseRequestStatus


def _period_filter(queryset, field, from_date=None, to_date=None):
    if from_date:
        queryset = queryset.filter(**{f'{field}__date__gte': from_date})
    if to_date:
        queryset = queryset.filter(**{f'{field}__date__lte': to_date})
    return queryset


def get_control_metrics(from_date=None, to_date=None, approval_sla_hours=48):
    """Return the TC01-TC29 control metrics from live transactional data."""
    completed_orders = _period_filter(
        SalesOrder.objects.filter(
            status=OrderStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        ),
        'completed_at',
        from_date,
        to_date,
    )
    created_orders = _period_filter(SalesOrder.objects.all(), 'created_at', from_date, to_date)
    cancelled_orders = created_orders.filter(status=OrderStatus.CANCELLED)
    completed_receipts = _period_filter(
        PurchaseReceipt.objects.filter(status=ReceiptStatus.COMPLETED),
        'completed_at',
        from_date,
        to_date,
    )
    completed_warranties = _period_filter(
        WarrantyReturn.objects.filter(status=WarrantyStatus.COMPLETED),
        'resolved_date',
        from_date,
        to_date,
    )

    revenue = completed_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    order_count = completed_orders.count()
    order_durations = [
        (order.completed_at - order.created_at).total_seconds()
        for order in completed_orders
        if order.completed_at and order.created_at
    ]
    receipt_durations = [
        (receipt.completed_at - receipt.created_at).total_seconds()
        for receipt in completed_receipts
        if receipt.completed_at and receipt.created_at
    ]

    sold_items = ProductItem.objects.filter(
        status=ItemStatus.SOLD,
        sales_order__status=OrderStatus.COMPLETED,
    )
    sold_count = sold_items.count()
    valid_serial_count = sold_items.exclude(serial_number='').count()
    invalid_item_count = ProductItem.objects.filter(
        Q(status=ItemStatus.SOLD, sales_order__isnull=True)
        | Q(status=ItemStatus.IN_STOCK, sales_order__status=OrderStatus.COMPLETED)
    ).count()

    adjustment_qs = _period_filter(StockAdjustment.objects.all(), 'created_at', from_date, to_date)
    adjustment_count = adjustment_qs.count()
    exact_adjustments = adjustment_qs.filter(difference_quantity=0).count()
    adjustment_value = adjustment_qs.aggregate(total=Sum('estimated_difference_value'))['total'] or Decimal('0.00')
    pending_adjustments = adjustment_qs.filter(status=AdjustmentStatus.PENDING_APPROVAL).count()

    payable_qs = Payable.objects.filter(status__in=[PayableStatus.UNPAID, PayableStatus.PARTIAL])
    overdue_qs = payable_qs.filter(due_date__lt=timezone.now().date())
    total_debt = payable_qs.aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')
    overdue_debt = overdue_qs.aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')

    pending_requests = PurchaseRequest.objects.filter(status=PurchaseRequestStatus.PENDING)
    approval_cutoff = timezone.now() - timedelta(hours=approval_sla_hours)
    overdue_pending_requests = pending_requests.filter(
        submitted_at__isnull=False,
        submitted_at__lt=approval_cutoff,
    ).count()
    suggested_requests = PurchaseRequest.objects.filter(source=PurchaseRequestSource.SYSTEM_SUGGESTION)
    suggested_total = suggested_requests.count()
    suggested_approved = suggested_requests.filter(
        status__in=[PurchaseRequestStatus.APPROVED, PurchaseRequestStatus.COMPLETED]
    ).count()

    warranty_durations = [
        (claim.resolved_date - claim.received_date).days
        for claim in completed_warranties
        if claim.resolved_date and claim.received_date
    ]

    sold_revenue = SalesOrderDetail.objects.filter(
        order__status=OrderStatus.COMPLETED,
    ).aggregate(total=Sum('total_price'))['total'] or Decimal('0.00')
    sold_cost = Decimal('0.00')
    for detail in SalesOrderDetail.objects.filter(order__status=OrderStatus.COMPLETED).select_related('product'):
        sold_cost += detail.quantity * detail.product.cost_price
    average_inventory = sum(
        product.get_current_stock() * product.cost_price
        for product in Product.objects.filter(status='ACTIVE')
    )
    inventory_turnover = (
        sold_cost / Decimal(str(average_inventory))
        if average_inventory > 0 else None
    )

    important_records = (
        completed_orders.count()
        + completed_receipts.count()
        + adjustment_count
        + completed_warranties.count()
    )
    important_logs = AuditLog.objects.filter(
        action__in=['COMPLETE', 'ADJUST', 'APPROVE', 'REJECT', 'PAYMENT', 'REVERSE']
    ).count()

    return {
        'TC01': {'revenue': revenue},
        'TC02': {
            'completed_orders': order_count,
            'average_order_value': revenue / order_count if order_count else Decimal('0.00'),
        },
        'TC03': {
            'cancelled_orders': cancelled_orders.count(),
            'created_orders': created_orders.count(),
            'cancel_rate': (
                cancelled_orders.count() / created_orders.count() * 100
                if created_orders.exists() else Decimal('0.00')
            ),
        },
        'TC04': {
            'average_processing_seconds': (
                sum(order_durations) / len(order_durations) if order_durations else None
            ),
        },
        'TC05': {
            'successful_payment_rate': (
                completed_orders.count() / created_orders.count() * 100
                if created_orders.exists() else Decimal('0.00')
            ),
            'draft_orders': created_orders.filter(status=OrderStatus.DRAFT).count(),
        },
        'TC06': {
            'by_staff': list(
                completed_orders.values(
                    'staff_id', 'staff__username', 'staff__first_name', 'staff__last_name'
                ).annotate(total_sales=Sum('total_amount'), order_count=Count('id'))
            ),
        },
        'TC07': {
            'customers': list(
                completed_orders.values('customer_id', 'customer__name').annotate(
                    purchase_count=Count('id'),
                    total_spent=Sum('total_amount'),
                )
            ),
        },
        'TC08': {
            'receipt_count': completed_receipts.count(),
            'total_purchase_value': completed_receipts.aggregate(total=Sum('total_amount'))['total']
            or Decimal('0.00'),
            'by_supplier': list(
                completed_receipts.values('supplier_id', 'supplier__name').annotate(
                    total_quantity=Sum('details__quantity'),
                    total_value=Sum('total_amount'),
                )
            ),
        },
        'TC09': {
            'average_processing_seconds': (
                sum(receipt_durations) / len(receipt_durations) if receipt_durations else None
            ),
        },
        'TC10': {
            'checked_adjustments': adjustment_count,
            'exact_adjustments': exact_adjustments,
            'accuracy_rate': (
                exact_adjustments / adjustment_count * 100
                if adjustment_count else None
            ),
        },
        'TC11': {
            'below_min_stock': Product.objects.filter(status='ACTIVE').filter(
                id__in=[
                    product.id for product in Product.objects.filter(status='ACTIVE')
                    if product.get_current_stock() <= product.min_stock
                ]
            ).count(),
        },
        'TC12': {'inventory_turnover': inventory_turnover},
        'TC13': {
            'adjustment_count': adjustment_count,
            'adjustment_value': adjustment_value,
            'pending_approval_count': pending_adjustments,
        },
        'TC14': {
            'valid_serial_rate': (
                valid_serial_count / sold_count * 100 if sold_count else None
            ),
            'invalid_status_count': invalid_item_count,
        },
        'TC15': {
            'warranty_count': completed_warranties.count(),
            'warranty_rate': (
                completed_warranties.count() / sold_count * 100 if sold_count else None
            ),
        },
        'TC16': {
            'average_processing_days': (
                sum(warranty_durations) / len(warranty_durations)
                if warranty_durations else None
            ),
        },
        'TC17': {
            'denied_operations': AccessDeniedLog.objects.filter(
                created_at__date__gte=from_date if from_date else timezone.now().date().replace(day=1),
                created_at__date__lte=to_date if to_date else timezone.now().date(),
            ).count(),
        },
        'TC18': {
            'important_records': important_records,
            'important_logs': important_logs,
            'coverage_rate': (
                important_logs / important_records * 100 if important_records else None
            ),
        },
        'TC19': {
            'live_query': True,
            'latency_seconds': None,
            'discrepancy': 'Reports query transactional tables directly; no display timestamp is persisted.',
        },
        'TC20': {
            'receipts': CashLedger.objects.filter(transaction_type=LedgerType.RECEIPT).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'payments': CashLedger.objects.filter(transaction_type=LedgerType.PAYMENT).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
        },
        'TC21': {'total_payable_remaining': total_debt, 'by_supplier': list(
            payable_qs.values('supplier_id', 'supplier__name').annotate(total=Sum('remaining_amount'))
        )},
        'TC22': {
            'overdue_amount': overdue_debt,
            'overdue_count': overdue_qs.count(),
            'overdue_rate': overdue_debt / total_debt * 100 if total_debt else Decimal('0.00'),
        },
        'TC23': {
            'sales_ledger_match': (
                SalesOrder.objects.filter(
                    status=OrderStatus.COMPLETED,
                    payment_status=PaymentStatus.PAID,
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            ) == (
                CashLedger.objects.filter(
                    reference_type='SALES_ORDER',
                    is_reversed=False,
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            ),
        },
        'TC24': {'supplier_performance_available': True},
        'TC25': {'supplier_performance_available': True},
        'TC26': {
            'overdue_pending_requests': overdue_pending_requests,
            'approval_sla_hours': approval_sla_hours,
        },
        'TC27': {
            'suggested_total': suggested_total,
            'suggested_approved': suggested_approved,
            'approval_rate': (
                suggested_approved / suggested_total * 100 if suggested_total else None
            ),
        },
        'TC28': {
            'available_after_update': True,
            'formula': 'abs(forecasted_quantity - actual_quantity) / actual_quantity * 100',
        },
        'TC29': {
            'gross_profit': sold_revenue - sold_cost,
            'gross_margin_rate': (
                (sold_revenue - sold_cost) / sold_revenue * 100
                if sold_revenue else Decimal('0.00')
            ),
        },
    }
