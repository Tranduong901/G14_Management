from django.urls import path
from reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('revenue/', views.revenue_report_view, name='revenue_report'),
    path('inventory/', views.inventory_report_view, name='inventory_report'),
    path('purchasing/', views.purchasing_report_view, name='purchasing_report'),
    path('customers/', views.customer_report_view, name='customer_report'),
    path('finance/', views.financial_report_view, name='financial_report'),
]

