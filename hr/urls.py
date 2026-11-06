from django.urls import path
from hr import views

app_name = 'hr'

urlpatterns = [
    # D1: Hồ sơ nhân viên, Hợp đồng & Lịch sử
    path('', views.employee_list_view, name='employee_list'),
    path('create/', views.employee_create_view, name='employee_create'),
    path('<int:pk>/', views.employee_detail_view, name='employee_detail'),
    path('<int:pk>/edit/', views.employee_edit_view, name='employee_edit'),
    path('<int:employee_pk>/contracts/create/', views.contract_create_view, name='contract_create'),

    # D2: Chấm công thủ công, Ca làm việc & Nghỉ phép
    path('attendance/', views.attendance_list_view, name='attendance_list'),
    path('attendance/create/', views.attendance_manual_create_view, name='attendance_create'),
    path('attendance/<int:pk>/edit/', views.attendance_edit_view, name='attendance_edit'),
    path('attendance/summary/', views.attendance_summary_view, name='attendance_summary'),
    path('leave/', views.leave_list_view, name='leave_list'),
    path('leave/create/', views.leave_create_view, name='leave_create'),

    # D3: Tính lương & Phiếu lương (Payroll)
    path('payroll/', views.payroll_list_view, name='payroll_list'),
    path('payroll/create/', views.payroll_create_view, name='payroll_create'),
    path('payroll/<int:pk>/', views.payroll_detail_view, name='payroll_detail'),
    path('payroll/payslip/<int:pk>/', views.payslip_detail_view, name='payslip_detail'),
    path('my-payslips/', views.my_payslips_view, name='my_payslips'),
]
