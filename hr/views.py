from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from accounts.models import Role, Branch
from accounts.decorators import role_required
from accounts.scoping import get_scoped_queryset
from auditlog.services import log_activity
from hr.models import (
    Employee,
    LaborContract,
    EmployeeHistory,
    WorkShift,
    AttendanceRecord,
    AttendanceAuditLog,
    AttendanceStatus,
    LeaveRequest,
    LeaveEntitlement,
    LeaveType,
    LeaveStatus,
    MonthlyAttendanceSummary,
    PayrollPeriod,
    PayrollItem,
    PayrollPeriodStatus,
)
from hr.forms import (
    EmployeeForm,
    LaborContractForm,
    WorkShiftForm,
    AttendanceManualEntryForm,
    AttendanceEditForm,
    LeaveRequestForm,
    PayrollPeriodForm,
)
from hr.services import (
    create_labor_contract,
    transfer_employee,
    resign_employee,
    record_attendance_manual,
    update_attendance_manual,
    submit_leave_request,
    calculate_monthly_attendance_summary,
)
from hr.payroll_services import (
    generate_payroll_period,
    submit_payroll_for_approval,
    lock_payroll_period,
    disburse_payroll,
)
from hr.permissions import (
    user_can_view_payroll_management,
    payroll_access_required,
)

# =====================================================================
# D1: HỒ SƠ NHÂN VIÊN, HỢP ĐỒNG & LỊCH SỬ BIẾN ĐỘNG
# =====================================================================

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR])
def employee_list_view(request):
    employees = Employee.objects.select_related('user', 'branch').all()
    employees = get_scoped_queryset(employees, request.user, branch_field='branch', user_field=None)

    q = request.GET.get('q', '').strip()
    dept = request.GET.get('department', '')
    status = request.GET.get('status', '')
    branch_id = request.GET.get('branch', '')

    if q:
        employees = employees.filter(
            Q(code__icontains=q) |
            Q(full_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
    if dept:
        employees = employees.filter(department=dept)
    if status:
        employees = employees.filter(status=status)
    if branch_id:
        employees = employees.filter(branch_id=branch_id)

    paginator = Paginator(employees, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    branches = Branch.objects.filter(is_active=True)

    return render(request, 'hr/employee_list.html', {
        'page_obj': page_obj,
        'q': q,
        'department_filter': dept,
        'status_filter': status,
        'branch_filter': branch_id,
        'branches': branches,
        'departments': Employee.DEPARTMENT_CHOICES,
        'statuses': Employee.STATUS_CHOICES,
    })

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR])
def employee_create_view(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.created_by = request.user
            # Default branch if not set
            if not employee.branch and request.user.branch:
                employee.branch = request.user.branch
            employee.save()

            # Initialize leave entitlement
            LeaveEntitlement.objects.get_or_create(
                employee=employee,
                year=timezone.now().year,
                defaults={'total_days': Decimal('12.00'), 'used_days': Decimal('0.00'), 'remaining_days': Decimal('12.00')}
            )

            log_activity(
                user=request.user,
                action='CREATE',
                obj=employee,
                changes={'code': employee.code, 'full_name': employee.full_name},
                request=request
            )
            messages.success(request, f"Đã thêm nhân viên {employee.full_name} ({employee.code}) thành công!")
            return redirect('hr:employee_detail', pk=employee.pk)
    else:
        initial = {}
        if request.user.branch:
            initial['branch'] = request.user.branch
        form = EmployeeForm(initial=initial)

    return render(request, 'hr/employee_form.html', {'form': form, 'title': 'Thêm mới nhân viên'})

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR])
def employee_edit_view(request, pk):
    employee = get_object_or_404(
        get_scoped_queryset(Employee.objects.all(), request.user, branch_field='branch', user_field=None),
        pk=pk,
    )
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            updated = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated,
                changes={'code': updated.code, 'full_name': updated.full_name, 'status': updated.status},
                request=request
            )
            messages.success(request, f"Cập nhật hồ sơ nhân viên {updated.full_name} thành công!")
            return redirect('hr:employee_detail', pk=updated.pk)
    else:
        form = EmployeeForm(instance=employee)

    return render(request, 'hr/employee_form.html', {'form': form, 'title': f'Sửa nhân viên {employee.full_name}', 'employee': employee})

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR])
def employee_detail_view(request, pk):
    employee = get_object_or_404(
        get_scoped_queryset(
            Employee.objects.select_related('user', 'branch'),
            request.user,
            branch_field='branch',
            user_field=None,
        ),
        pk=pk
    )
    contracts = employee.contracts.select_related('branch').all().order_by('-start_date')
    history_records = employee.history_records.all().order_by('-event_date', '-created_at')
    leave_entitlement, _ = LeaveEntitlement.objects.get_or_create(
        employee=employee,
        year=timezone.now().year,
        defaults={'total_days': Decimal('12.00'), 'used_days': Decimal('0.00'), 'remaining_days': Decimal('12.00')}
    )
    recent_leaves = employee.leave_requests.all().order_by('-created_at')[:10]

    return render(request, 'hr/employee_detail.html', {
        'employee': employee,
        'contracts': contracts,
        'history_records': history_records,
        'entitlement': leave_entitlement,
        'recent_leaves': recent_leaves,
    })

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR])
def contract_create_view(request, employee_pk):
    employee = get_object_or_404(
        get_scoped_queryset(Employee.objects.all(), request.user, branch_field='branch', user_field=None),
        pk=employee_pk,
    )
    if request.method == 'POST':
        form = LaborContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user
            if contract.is_active:
                LaborContract.objects.filter(employee=employee, is_active=True).update(is_active=False)
            contract.save()
            messages.success(request, f"Đã tạo hợp đồng lao động {contract.contract_code} cho {employee.full_name}.")
            return redirect('hr:employee_detail', pk=employee.pk)
    else:
        form = LaborContractForm(initial={
            'employee': employee,
            'position': employee.position,
            'branch': employee.branch,
            'start_date': timezone.now().date(),
            'is_active': True
        })

    return render(request, 'hr/contract_form.html', {
        'form': form,
        'employee': employee,
        'title': f"Tạo Hợp đồng lao động - {employee.full_name}"
    })

# =====================================================================
# D2: CA LÀM VIỆC, CHẤM CÔNG THỦ CÔNG & NGHỈ PHÉP
# =====================================================================

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR, Role.KHO, Role.BH, Role.KT])
def attendance_list_view(request):
    """View manual attendance log."""
    records = AttendanceRecord.objects.select_related('employee', 'employee__branch', 'shift', 'recorded_by').all()
    records = get_scoped_queryset(records, request.user, branch_field='employee__branch', user_field='recorded_by')

    date_str = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))
    emp_id = request.GET.get('employee', '')
    status = request.GET.get('status', '')

    if date_str:
        records = records.filter(date=date_str)
    if emp_id:
        records = records.filter(employee_id=emp_id)
    if status:
        records = records.filter(status=status)

    paginator = Paginator(records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    employees = Employee.objects.filter(status='ACTIVE')
    employees = get_scoped_queryset(employees, request.user, branch_field='branch', user_field=None)

    return render(request, 'hr/attendance_list.html', {
        'page_obj': page_obj,
        'date_filter': date_str,
        'employee_filter': emp_id,
        'status_filter': status,
        'employees': employees,
        'statuses': AttendanceStatus.choices,
    })

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR])
def attendance_manual_create_view(request):
    """
    Manually inputs attendance for an employee.
    Enforces check for duplicate employee, date, and shift.
    """
    if request.method == 'POST':
        form = AttendanceManualEntryForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                rec = record_attendance_manual(
                    employee=cd['employee'],
                    date=cd['date'],
                    shift=cd['shift'],
                    work_units=cd['work_units'],
                    check_in=cd.get('check_in'),
                    check_out=cd.get('check_out'),
                    status=cd['status'],
                    ot_hours=cd.get('ot_hours', Decimal('0.00')),
                    notes=cd.get('notes', ''),
                    user=request.user
                )
                messages.success(request, f"Đã ghi nhận chấm công cho {rec.employee.full_name} ngày {rec.date.strftime('%d/%m/%Y')}.")
                return redirect('hr:attendance_list')
            except Exception as e:
                messages.error(request, f"Lỗi chấm công: {str(e)}")
    else:
        default_shift = WorkShift.objects.filter(is_active=True).first()
        form = AttendanceManualEntryForm(initial={
            'date': timezone.now().date(),
            'shift': default_shift,
            'work_units': Decimal('1.00'),
            'status': AttendanceStatus.PRESENT
        })

    return render(request, 'hr/attendance_form.html', {'form': form, 'title': 'Chấm công thủ công'})

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR])
def attendance_edit_view(request, pk):
    """
    Edits an attendance record.
    Requires mandatory reason and stores audit log.
    """
    record = get_object_or_404(
        get_scoped_queryset(
            AttendanceRecord.objects.select_related('employee', 'shift'),
            request.user,
            branch_field='employee__branch',
            user_field='recorded_by',
        ),
        pk=pk,
    )

    if request.method == 'POST':
        form = AttendanceEditForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                update_attendance_manual(
                    record=record,
                    new_work_units=cd['work_units'],
                    new_status=cd['status'],
                    reason=cd['reason'],
                    new_check_in=cd.get('check_in'),
                    new_check_out=cd.get('check_out'),
                    new_ot_hours=cd.get('ot_hours', Decimal('0.00')),
                    notes=cd.get('notes', ''),
                    user=request.user
                )
                messages.success(request, f"Cập nhật chấm công cho {record.employee.full_name} thành công.")
                return redirect('hr:attendance_list')
            except Exception as e:
                messages.error(request, f"Lỗi cập nhật: {str(e)}")
    else:
        form = AttendanceEditForm(initial={
            'work_units': record.work_units,
            'status': record.status,
            'check_in': record.check_in,
            'check_out': record.check_out,
            'ot_hours': record.ot_hours,
            'notes': record.notes,
        })

    audit_logs = record.audit_logs.select_related('modified_by').all()
    return render(request, 'hr/attendance_edit.html', {
        'form': form,
        'record': record,
        'audit_logs': audit_logs,
    })

@login_required
@role_required([Role.QL, Role.ADMIN, Role.HR, Role.KT])
def attendance_summary_view(request):
    """Monthly attendance aggregation."""
    now = timezone.now()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    period_str = f"{year:04d}-{month:02d}"

    # Recalculate if requested
    if request.method == 'POST' and 'recalculate' in request.POST:
        active_emps = Employee.objects.filter(status='ACTIVE')
        for emp in active_emps:
            calculate_monthly_attendance_summary(emp, year, month)
        messages.success(request, f"Đã tổng hợp lại ngày công kỳ {period_str} thành công!")
        return redirect(f"{request.path}?year={year}&month={month}")

    summaries = MonthlyAttendanceSummary.objects.filter(period=period_str).select_related('employee', 'employee__branch')
    summaries = get_scoped_queryset(summaries, request.user, branch_field='employee__branch', user_field=None)

    return render(request, 'hr/attendance_summary.html', {
        'summaries': summaries,
        'year': year,
        'month': month,
        'period_str': period_str,
    })

@login_required
def leave_list_view(request):
    """Lists leave requests. Employees see their own; HR/QL see scoped."""
    user = request.user
    if user.role in [Role.HR, Role.QL, Role.ADMIN]:
        leaves = LeaveRequest.objects.select_related('employee', 'employee__branch', 'approver').all()
        leaves = get_scoped_queryset(leaves, user, branch_field='employee__branch', user_field='created_by')
    else:
        leaves = LeaveRequest.objects.filter(employee__user=user).select_related('employee', 'approver')

    paginator = Paginator(leaves, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hr/leave_list.html', {'page_obj': page_obj})

@login_required
def leave_create_view(request):
    """Submits a leave request with automatic remaining days check."""
    user = request.user
    # Find employee profile
    employee = getattr(user, 'employee_profile', None)

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            emp = cd['employee'] if user.role in [Role.HR, Role.QL, Role.ADMIN] else employee
            if not emp:
                messages.error(request, "Tài khoản của bạn chưa liên kết với hồ sơ nhân viên.")
                return redirect('hr:leave_list')

            try:
                leave_req = submit_leave_request(
                    employee=emp,
                    leave_type=cd['leave_type'],
                    start_date=cd['start_date'],
                    end_date=cd['end_date'],
                    days_count=cd['days_count'],
                    reason=cd['reason'],
                    user=user
                )
                messages.success(request, f"Đã gửi đơn xin nghỉ {leave_req.code} lên quy trình phê duyệt.")
                return redirect('hr:leave_list')
            except Exception as e:
                messages.error(request, f"Lỗi tạo đơn: {str(e)}")
    else:
        initial = {}
        if employee:
            initial['employee'] = employee
        initial['start_date'] = timezone.now().date()
        initial['end_date'] = timezone.now().date()
        form = LeaveRequestForm(initial=initial)

    return render(request, 'hr/leave_form.html', {'form': form, 'title': 'Lập đơn xin nghỉ phép'})

# =====================================================================
# D3: TÍNH LƯƠNG & XUẤT PHIẾU LƯƠNG (PAYROLL)
# =====================================================================

@login_required
@payroll_access_required
def payroll_list_view(request):
    periods = PayrollPeriod.objects.all().order_by('-year', '-month')
    return render(request, 'hr/payroll_list.html', {'periods': periods})

@login_required
@payroll_access_required
def payroll_create_view(request):
    now = timezone.now()
    if request.method == 'POST':
        form = PayrollPeriodForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                period = generate_payroll_period(
                    year=cd['year'],
                    month=cd['month'],
                    standard_work_days=cd['standard_work_days'],
                    user=request.user,
                    notes=cd.get('notes', '')
                )
                messages.success(request, f"Đã tạo và tính toán bảng lương {period.code} ({period.items.count()} nhân viên).")
                return redirect('hr:payroll_detail', pk=period.pk)
            except Exception as e:
                messages.error(request, f"Lỗi tính lương: {str(e)}")
    else:
        form = PayrollPeriodForm(initial={
            'month': now.month,
            'year': now.year,
            'standard_work_days': Decimal('26.0')
        })

    return render(request, 'hr/payroll_form.html', {'form': form, 'title': 'Tạo bảng lương mới'})

@login_required
@payroll_access_required
def payroll_detail_view(request, pk):
    period = get_object_or_404(PayrollPeriod.objects.prefetch_related('items__employee'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'recalculate':
                generate_payroll_period(period.year, period.month, period.standard_work_days, user=request.user)
                messages.success(request, f"Đã tính toán lại toàn bộ bảng lương {period.code}.")
            elif action == 'submit_approval':
                submit_payroll_for_approval(period, user=request.user)
                messages.success(request, f"Đã gửi bảng lương lên quy trình phê duyệt.")
            elif action == 'lock':
                lock_payroll_period(period, user=request.user)
                messages.success(request, f"Đã khóa bảng lương {period.code}. Các số liệu đã được chốt.")
            elif action == 'disburse':
                period, ledger = disburse_payroll(period, user=request.user)
                messages.success(request, f"Đã chi trả lương thành công! Ghi nhận bút toán chi {ledger.code} vào sổ quỹ F08.")
            return redirect('hr:payroll_detail', pk=period.pk)
        except Exception as e:
            messages.error(request, f"Thao tác thất bại: {str(e)}")

    items = period.items.select_related('employee', 'employee__branch').order_by('employee__code')
    return render(request, 'hr/payroll_detail.html', {
        'period': period,
        'items': items,
    })

@login_required
def payslip_detail_view(request, pk):
    """
    Shows individual payslip.
    Confidentiality rule:
    - Employee can ONLY view their own payslip.
    - HR, KT, and QL can view all payslips.
    - Admin can view ONLY if granted can_view_payroll.
    """
    item = get_object_or_404(
        PayrollItem.objects.select_related('period', 'employee', 'employee__branch', 'contract'),
        pk=pk
    )

    is_owner = (item.employee.user_id == request.user.id)
    has_mgmt_access = user_can_view_payroll_management(request.user)

    if not is_owner and not has_mgmt_access:
        messages.error(request, "Bạn không có quyền xem phiếu lương của nhân viên khác.")
        return redirect('hr:my_payslips')

    return render(request, 'hr/payslip_detail.html', {
        'item': item,
        'period': item.period,
        'employee': item.employee,
    })

@login_required
def my_payslips_view(request):
    """Personal payslip history for the logged-in user."""
    employee = getattr(request.user, 'employee_profile', None)
    if not employee:
        return render(request, 'hr/my_payslips.html', {
            'payslips': [],
            'error_message': 'Tài khoản của bạn chưa được liên kết với hồ sơ nhân viên trong hệ thống.'
        })

    payslips = PayrollItem.objects.filter(employee=employee).select_related('period').order_by('-period__year', '-period__month')
    return render(request, 'hr/my_payslips.html', {
        'payslips': payslips,
        'employee': employee,
    })
