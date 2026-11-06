from django.urls import path
from approvals import views

app_name = 'approvals'

urlpatterns = [
    path('workflows/', views.workflow_list_view, name='workflow_list'),
    path('workflows/<int:pk>/', views.workflow_edit_view, name='workflow_edit'),
    path('workflows/<int:workflow_pk>/steps/<int:step_pk>/delete/', views.step_delete_view, name='step_delete'),
    path('pending/', views.pending_approvals_view, name='pending_list'),
    path('<int:pk>/', views.approval_detail_view, name='approval_detail'),
]
