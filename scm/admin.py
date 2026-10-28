from django.contrib import admin
from scm.models import SupplierProduct, PurchaseRequest, PurchaseRequestDetail

@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'product', 'last_purchase_price', 'standard_lead_days']
    list_filter = ['supplier']

class PurchaseRequestDetailInline(admin.TabularInline):
    model = PurchaseRequestDetail
    extra = 1

@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ['code', 'status', 'source', 'requester', 'approver', 'created_at']
    list_filter = ['status', 'source']
    inlines = [PurchaseRequestDetailInline]

