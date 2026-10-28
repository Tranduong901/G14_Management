from django.contrib import admin
from inventory.models import InventoryTransaction, StockAdjustment

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_date', 'transaction_type', 'product', 'quantity', 'reference_code', 'created_by']
    list_filter = ['transaction_type', 'transaction_date']
    search_fields = ['reference_code', 'product__name']

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'product', 'system_quantity', 'actual_quantity', 'difference_quantity', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['code', 'product__name']

