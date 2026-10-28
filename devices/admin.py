from django.contrib import admin
from devices.models import ProductItem, WarrantyReturn

@admin.register(ProductItem)
class ProductItemAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'product', 'status', 'warranty_start_date', 'warranty_end_date']
    list_filter = ['status', 'product__category']
    search_fields = ['serial_number', 'product__name']

@admin.register(WarrantyReturn)
class WarrantyReturnAdmin(admin.ModelAdmin):
    list_display = ['code', 'item', 'customer', 'action_type', 'status', 'received_date', 'resolved_date']
    list_filter = ['status', 'action_type']
    search_fields = ['code', 'item__serial_number', 'customer__name']

