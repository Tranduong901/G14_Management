from django.urls import path
from dss import views

app_name = 'dss'

urlpatterns = [
    path('analytics/', views.dss_analytics_view, name='analytics'),
    path('forecast/', views.dss_forecast_view, name='forecast'),
    path(
        'forecast/update-accuracy/',
        views.update_forecast_accuracy_view,
        name='update_forecast_accuracy',
    ),
    path('suggestions/', views.dss_suggestions_view, name='suggestions'),
    path('optimizer/', views.dss_optimizer_view, name='optimizer'),
]
