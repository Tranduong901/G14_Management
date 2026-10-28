from django.contrib import admin
from hr.models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_name', 'department', 'position', 'phone', 'status', 'user']
    list_filter = ['department', 'status']
    search_fields = ['code', 'full_name', 'phone', 'email']

