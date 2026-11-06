from django.urls import path
from crm import views

app_name = 'crm'

urlpatterns = [
    # Leads
    path('leads/', views.lead_list_view, name='lead_list'),
    path('leads/create/', views.lead_create_view, name='lead_create'),
    path('leads/<int:pk>/edit/', views.lead_edit_view, name='lead_edit'),
    path('leads/<int:pk>/delete/', views.lead_delete_view, name='lead_delete'),
    path('leads/<int:pk>/convert/', views.lead_convert_to_opp_view, name='lead_convert'),

    # Opportunities
    path('opportunities/', views.opportunity_list_view, name='opportunity_list'),
    path('opportunities/create/', views.opportunity_create_view, name='opportunity_create'),
    path('opportunities/<int:pk>/', views.opportunity_detail_view, name='opportunity_detail'),
    path('opportunities/<int:pk>/edit/', views.opportunity_edit_view, name='opportunity_edit'),
    path('opportunities/<int:pk>/delete/', views.opportunity_delete_view, name='opportunity_delete'),

    # Activities
    path('activities/', views.activity_list_view, name='activity_list'),
    path('activities/create/', views.activity_create_view, name='activity_create'),

    # Funnel Report
    path('funnel/', views.sales_funnel_view, name='sales_funnel'),
]
