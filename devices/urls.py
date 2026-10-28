from django.urls import path
from devices import views

app_name = 'devices'

urlpatterns = [
    path('', views.device_list_view, name='device_list'),
    path('lookup/', views.device_lookup_view, name='device_lookup'),
    path('warranty/', views.warranty_list_view, name='warranty_list'),
    path('warranty/create/', views.warranty_create_view, name='warranty_create'),
    path('warranty/<int:pk>/', views.warranty_detail_view, name='warranty_detail'),
    path('warranty/<int:pk>/resolve/', views.warranty_resolve_view, name='warranty_resolve'),
    path('warranty/<int:pk>/print/', views.warranty_print_view, name='warranty_print'),
]

