from django.contrib import admin
from sales.models import SalesOrder, SalesOrderDetail

class SalesOrderDetailInline(admin.TabularInline):
    model = SalesOrderDetail
    extra = 1

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ['code', 'customer', 'staff', 'order_date', 'status', 'total_amount', 'payment_method', 'payment_status']
    list_filter = ['status', 'payment_method', 'payment_status', 'order_date']
    search_fields = ['code', 'customer__name', 'customer__phone']
    inlines = [SalesOrderDetailInline]

