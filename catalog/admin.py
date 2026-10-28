from django.contrib import admin
from catalog.models import Product, Customer, Supplier

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'price', 'cost_price', 'min_stock', 'has_serial', 'status']
    list_filter = ['category', 'status', 'has_serial']
    search_fields = ['code', 'name']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'phone', 'email', 'customer_type']
    list_filter = ['customer_type']
    search_fields = ['code', 'name', 'phone']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'phone', 'payment_terms_days']
    search_fields = ['code', 'name', 'phone']

