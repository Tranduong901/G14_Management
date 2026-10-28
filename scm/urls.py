from django.urls import path
from scm import views

app_name = 'scm'

urlpatterns = [
    path('requests/', views.request_list_view, name='request_list'),
    path('requests/create/', views.request_create_view, name='request_create'),
    path('requests/<int:pk>/', views.request_detail_view, name='request_detail'),
    path('requests/<int:pk>/submit/', views.request_submit_view, name='request_submit'),
    path('requests/<int:pk>/approve/', views.request_approve_view, name='request_approve'),
    path('requests/<int:pk>/reject/', views.request_reject_view, name='request_reject'),
    path('requests/<int:pk>/convert/', views.request_convert_view, name='request_convert'),
    path('suppliers/evaluation/', views.supplier_evaluation_view, name='supplier_evaluation'),
]

