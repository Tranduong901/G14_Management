from django.urls import path
from dss import views

app_name = 'dss'

urlpatterns = [
    path('analytics/', views.dss_analytics_view, name='analytics'),
    path('forecast/', views.dss_forecast_view, name='forecast'),
    path('suggestions/', views.dss_suggestions_view, name='suggestions'),
    path('optimizer/', views.dss_optimizer_view, name='optimizer'),
]

