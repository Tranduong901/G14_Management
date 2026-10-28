from django.contrib import admin
from dss.models import ForecastResult

@admin.register(ForecastResult)
class ForecastResultAdmin(admin.ModelAdmin):
    list_display = ['product', 'forecast_period', 'method', 'forecasted_quantity', 'actual_quantity', 'error_rate', 'calculated_at']
    list_filter = ['forecast_period', 'method']
    search_fields = ['product__name', 'product__code']

