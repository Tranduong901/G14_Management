from django.contrib import admin
from purchasing.models import PurchaseReceipt, PurchaseDetail

class PurchaseDetailInline(admin.TabularInline):
    model = PurchaseDetail
    extra = 1

@admin.register(PurchaseReceipt)
class PurchaseReceiptAdmin(admin.ModelAdmin):
    list_display = ['code', 'supplier', 'receipt_date', 'status', 'total_amount', 'created_by']
    list_filter = ['status', 'receipt_date']
    search_fields = ['code', 'supplier__name']
    inlines = [PurchaseDetailInline]

