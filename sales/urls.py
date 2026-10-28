from django.urls import path
from sales import views

app_name = 'sales'

urlpatterns = [
    path('', views.order_list_view, name='order_list'),
    path('create/', views.order_create_view, name='order_create'),
    path('<int:pk>/', views.order_detail_view, name='order_detail'),
    path('<int:pk>/complete/', views.order_complete_view, name='order_complete'),
    path('<int:pk>/cancel/', views.order_cancel_view, name='order_cancel'),
    path('<int:pk>/invoice/', views.order_invoice_view, name='order_invoice'),
]

