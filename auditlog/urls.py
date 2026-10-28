from django.urls import path
from auditlog import views

app_name = 'auditlog'

urlpatterns = [
    path('', views.auditlog_list_view, name='auditlog_list'),
    path('<int:pk>/', views.auditlog_detail_view, name='auditlog_detail'),
]

