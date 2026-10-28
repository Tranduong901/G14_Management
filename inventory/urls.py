from django.urls import path
from inventory import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_summary_view, name='inventory_summary'),
    path('transactions/', views.transaction_list_view, name='transaction_list'),
    path('adjustments/', views.adjustment_list_view, name='adjustment_list'),
    path('adjustments/create/', views.adjustment_create_view, name='adjustment_create'),
    path('adjustments/<int:pk>/<str:action>/', views.adjustment_action_view, name='adjustment_action'),
]

