from django.urls import path
from hr import views

app_name = 'hr'

urlpatterns = [
    path('', views.employee_list_view, name='employee_list'),
    path('create/', views.employee_create_view, name='employee_create'),
    path('<int:pk>/edit/', views.employee_edit_view, name='employee_edit'),
]

