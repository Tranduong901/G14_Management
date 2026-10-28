from django.urls import path
from purchasing import views

app_name = 'purchasing'

urlpatterns = [
    path('', views.receipt_list_view, name='receipt_list'),
    path('create/', views.receipt_create_view, name='receipt_create'),
    path('<int:pk>/', views.receipt_detail_view, name='receipt_detail'),
    path('<int:pk>/complete/', views.receipt_complete_view, name='receipt_complete'),
    path('<int:pk>/cancel/', views.receipt_cancel_view, name='receipt_cancel'),
]

