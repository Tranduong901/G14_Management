from django.urls import path
from finance import views

app_name = 'finance'

urlpatterns = [
    # Cash Ledger
    path('ledger/', views.cash_ledger_list_view, name='cash_ledger_list'),
    path('ledger/create-other/', views.ledger_create_other_view, name='ledger_create_other'),
    path('ledger/<int:pk>/reverse/', views.ledger_reverse_view, name='ledger_reverse'),

    # Payables
    path('payables/', views.payable_list_view, name='payable_list'),
    path('payables/<int:pk>/', views.payable_detail_view, name='payable_detail'),
    path('payables/<int:pk>/pay/', views.payable_pay_view, name='payable_pay'),

    # Reconciliation
    path('reconciliation/', views.financial_reconciliation_view, name='reconciliation'),
]

