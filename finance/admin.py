from django.contrib import admin
from finance.models import CashLedger, Payable, PayablePayment

@admin.register(CashLedger)
class CashLedgerAdmin(admin.ModelAdmin):
    list_display = ['code', 'entry_date', 'transaction_type', 'amount', 'payment_method', 'reference_type', 'reference_id', 'recorded_by']
    list_filter = ['transaction_type', 'payment_method', 'reference_type', 'is_reversed']
    search_fields = ['code', 'reference_id', 'reason']

@admin.register(Payable)
class PayableAdmin(admin.ModelAdmin):
    list_display = ['code', 'supplier', 'total_amount', 'paid_amount', 'remaining_amount', 'due_date', 'status']
    list_filter = ['status', 'due_date']
    search_fields = ['code', 'supplier__name']

@admin.register(PayablePayment)
class PayablePaymentAdmin(admin.ModelAdmin):
    list_display = ['payable', 'payment_date', 'amount', 'payment_method', 'ledger_entry']

