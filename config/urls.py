from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from config.api import ProductViewSet, CustomerViewSet, SalesOrderViewSet, api_dashboard_stats, api_procurement_suggestions

# REST API Router
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='api-product')
router.register(r'customers', CustomerViewSet, basename='api-customer')
router.register(r'orders', SalesOrderViewSet, basename='api-order')

def root_redirect_view(request):
    if request.user.is_authenticated:
        return redirect('reports:dashboard')
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect_view, name='root'),

    # Apps
    path('accounts/', include('accounts.urls')),
    path('catalog/', include('catalog.urls')),
    path('hr/', include('hr.urls')),
    path('sales/', include('sales.urls')),
    path('purchasing/', include('purchasing.urls')),
    path('inventory/', include('inventory.urls')),
    path('devices/', include('devices.urls')),
    path('finance/', include('finance.urls')),
    path('scm/', include('scm.urls')),
    path('dss/', include('dss.urls')),
    path('reports/', include('reports.urls')),
    path('auditlog/', include('auditlog.urls')),
    path('approvals/', include('approvals.urls')),
    path('crm/', include('crm.urls')),

    # REST API endpoints
    path('api/v1/', include(router.urls)),
    path('api/v1/dashboard-stats/', api_dashboard_stats, name='api-dashboard-stats'),
    path('api/v1/procurement-suggestions/', api_procurement_suggestions, name='api-procurement-suggestions'),
]

