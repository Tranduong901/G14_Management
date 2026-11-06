from decimal import Decimal
import uuid
from datetime import datetime, date
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum

from hr.models import (
    Employee,
    LaborContract,
    EmployeeHistory,
    HistoryEventType,
    WorkShift,
    WorkSchedule,
    AttendanceRecord,
    AttendanceAuditLog,
    AttendanceStatus,
    LeaveEntitlement,
    LeaveRequest,
    LeaveType,
    LeaveStatus,
    MonthlyAttendanceSummary,
)
from approvals.services import submit_for_approval, WorkflowType
from auditlog.services import log_activity

def generate_leave_code():
    return f"NP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

def generate_contract_code():
    return f"HDLD-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"

# ----------------- D1 Services -----------------

@transaction.atomic
def create_labor_contract(employee, contract_type, start_date, end_date=None,
                          base_salary=Decimal('0.00'), allowance=Decimal('0.00'),
                          insurance_salary=Decimal('0.00'), position='', branch=None,
                          notes='', user=None):
    """Creates a new labor contract and sets it as the active contract."""
    contract_code = generate_contract_code()
    
    # Deactivate older contracts if this is active
    LaborContract.objects.filter(employee=employee, is_active=True).update(is_active=False)

    if not position:
        position = employee.position
    if not branch:
        branch = employee.branch
    if insurance_salary <= Decimal('0.00'):
        insurance_salary = base_salary

    contract = LaborContract.objects.create(
        employee=employee,
        contract_code=contract_code,
        contract_type=contract_type,
        start_date=start_date,
        end_date=end_date,
        base_salary=base_salary,
        allowance=allowance,
        insurance_salary=insurance_salary,
        position=position,
        branch=branch,
        is_active=True,
        notes=notes,
        created_by=user
    )

    # Record salary / contract event in employee history
    EmployeeHistory.objects.create(
        employee=employee,
        event_type=HistoryEventType.SALARY_CHANGE,
        event_date=start_date,
        decision_number=contract_code,
        old_value=f"Lương cũ",
        new_value=f"HĐ {contract.get_contract_type_display()}: Lương CB {base_salary:,.0f} đ, Phụ cấp {allowance:,.0f} đ",
        reason=f"Ký hợp đồng lao động mới {contract_code}",
        created_by=user
    )

    log_activity(
        user=user,
        action='CREATE',
        obj=contract,
        changes={'code': contract.contract_code, 'employee': employee.full_name}
    )
    return contract

@transaction.atomic
def transfer_employee(employee, new_branch=None, new_department=None, new_position=None,
                      decision_number='', reason='', user=None):
    """Transfers employee to a new branch, department, or position."""
    old_info = f"Chi nhánh: {employee.branch.name if employee.branch else 'Chưa có'} | Phòng: {employee.get_department_display()} | Vị trí: {employee.position}"
    
    if new_branch:
        employee.branch = new_branch
    if new_department:
        employee.department = new_department
    if new_position:
        employee.position = new_position
    employee.save()

    new_info = f"Chi nhánh: {employee.branch.name if employee.branch else 'Chưa có'} | Phòng: {employee.get_department_display()} | Vị trí: {employee.position}"

    EmployeeHistory.objects.create(
        employee=employee,
        event_type=HistoryEventType.TRANSFER,
        event_date=timezone.now().date(),
        decision_number=decision_number,
        old_value=old_info,
        new_value=new_info,
        reason=reason,
        created_by=user
    )

    log_activity(
        user=user,
        action='UPDATE',
        obj=employee,
        changes={'action': 'TRANSFER', 'old': old_info, 'new': new_info}
    )
    return employee

@transaction.atomic
def resign_employee(employee, reason='', decision_number='', user=None):
    """Marks an employee as resigned."""
    employee.status = 'RESIGNED'
    employee.save(update_fields=['status'])

    # Deactivate system user if linked
    if employee.user:
        employee.user.is_active = False
        employee.user.save(update_fields=['is_active'])

    EmployeeHistory.objects.create(
        employee=employee,
        event_type=HistoryEventType.RESIGNATION,
        event_date=timezone.now().date(),
        decision_number=decision_number,
        old_value='Đang làm việc',
        new_value='Đã nghỉ việc',
        reason=reason,
        created_by=user
    )
    return employee

# ----------------- D2 Services -----------------

@transaction.atomic
def record_attendance_manual(employee, date, shift, work_units=Decimal('1.00'),
                            check_in=None, check_out=None, status=AttendanceStatus.PRESENT,
                            ot_hours=Decimal('0.00'), notes='', user=None):
    """
    Manually inputs an attendance record.
    Enforces check for duplicate employee, date, and shift.
    """
    if AttendanceRecord.objects.filter(employee=employee, date=date, shift=shift).exists():
        raise ValidationError(
            f"Nhân viên {employee.full_name} đã được chấm công ca '{shift.name}' vào ngày {date.strftime('%d/%m/%Y')} (Trùng lặp dữ liệu)."
        )

    rec = AttendanceRecord.objects.create(
        employee=employee,
        date=date,
        shift=shift,
        check_in=check_in,
        check_out=check_out,
        work_units=work_units,
        ot_hours=ot_hours,
        status=status,
        notes=notes,
        recorded_by=user,
        created_by=user
    )
    return rec

@transaction.atomic
def update_attendance_manual(record, new_work_units, new_status, reason,
                             new_check_in=None, new_check_out=None,
                             new_ot_hours=Decimal('0.00'), notes='', user=None):
    """
    Edits an existing attendance record.
    Mandatory reason is recorded in AttendanceAuditLog.
    """
    if not reason or not reason.strip():
        raise ValidationError("Lý do chỉnh sửa chấm công là bắt buộc theo quy định quản trị HR.")

    old_values = {
        'work_units': str(record.work_units),
        'status': record.status,
        'check_in': record.check_in.strftime('%H:%M') if record.check_in else None,
        'check_out': record.check_out.strftime('%H:%M') if record.check_out else None,
        'ot_hours': str(record.ot_hours),
        'notes': record.notes,
    }

    record.work_units = new_work_units
    record.status = new_status
    record.check_in = new_check_in
    record.check_out = new_check_out
    record.ot_hours = new_ot_hours
    if notes:
        record.notes = notes
    record.save()

    new_values = {
        'work_units': str(record.work_units),
        'status': record.status,
        'check_in': record.check_in.strftime('%H:%M') if record.check_in else None,
        'check_out': record.check_out.strftime('%H:%M') if record.check_out else None,
        'ot_hours': str(record.ot_hours),
        'notes': record.notes,
    }

    AttendanceAuditLog.objects.create(
        record=record,
        modified_by=user,
        reason=reason.strip(),
        old_values=old_values,
        new_values=new_values,
        created_by=user
    )
    return record

@transaction.atomic
def submit_leave_request(employee, leave_type, start_date, end_date, days_count, reason, user=None):
    """
    Creates a leave request, checks remaining leave entitlement, and submits to approval engine.
    """
    days_count = Decimal(str(days_count))
    if days_count <= Decimal('0.0'):
        raise ValidationError("Số ngày nghỉ phải lớn hơn 0.")

    if start_date > end_date:
        raise ValidationError("Ngày bắt đầu nghỉ không được lớn hơn ngày kết thúc.")

    # Check remaining leave balance if Annual Leave
    if leave_type == LeaveType.ANNUAL:
        entitlement, _ = LeaveEntitlement.objects.get_or_create(
            employee=employee,
            year=start_date.year,
            defaults={'total_days': Decimal('12.00'), 'used_days': Decimal('0.00'), 'remaining_days': Decimal('12.00')}
        )
        if entitlement.remaining_days < days_count:
            raise ValidationError(
                f"Số ngày xin nghỉ ({days_count} ngày) vượt quá số ngày phép còn lại "
                f"({entitlement.remaining_days} ngày) của nhân viên {employee.full_name}."
            )

    leave_req = LeaveRequest.objects.create(
        code=generate_leave_code(),
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days_count=days_count,
        reason=reason,
        status=LeaveStatus.PENDING,
        created_by=user
    )

    # Submit to approval engine
    submit_for_approval(
        leave_req,
        requester=user or getattr(employee, 'user', None),
        title=f"Đơn nghỉ phép: {employee.full_name} ({days_count} ngày - {leave_req.get_leave_type_display()})",
        notes=f"Lý do: {reason}",
        workflow_type=WorkflowType.LEAVE
    )

    return leave_req

@transaction.atomic
def calculate_monthly_attendance_summary(employee, year, month, standard_days=Decimal('26.0')):
    """Aggregates all attendance and leaves for an employee in a given month."""
    period_str = f"{year:04d}-{month:02d}"

    records = AttendanceRecord.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    )

    actual_work_days = Decimal('0.00')
    paid_leave_days = Decimal('0.00')
    unpaid_leave_days = Decimal('0.00')
    ot_hours = Decimal('0.00')
    late_early_count = 0

    for r in records:
        if r.status in [AttendanceStatus.PRESENT, AttendanceStatus.HALF_DAY]:
            actual_work_days += r.work_units
        elif r.status == AttendanceStatus.LATE_EARLY:
            actual_work_days += r.work_units
            late_early_count += 1
        elif r.status == AttendanceStatus.LEAVE_PAID:
            paid_leave_days += r.work_units
        elif r.status in [AttendanceStatus.LEAVE_UNPAID, AttendanceStatus.ABSENT]:
            unpaid_leave_days += r.work_units

        ot_hours += r.ot_hours

    # Include approved leave requests in the period
    approved_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveStatus.APPROVED,
        start_date__year=year,
        start_date__month=month
    )
    for al in approved_leaves:
        if al.leave_type == LeaveType.UNPAID:
            # Do not double count days already recorded as unpaid attendance.
            recorded_unpaid_days = records.filter(
                status=AttendanceStatus.LEAVE_UNPAID,
                date__gte=al.start_date,
                date__lte=al.end_date,
            ).aggregate(total=Sum('work_units'))['total'] or Decimal('0.00')
            unpaid_leave_days += max(
                Decimal('0.00'),
                al.days_count - recorded_unpaid_days,
            )

    summary, _ = MonthlyAttendanceSummary.objects.update_or_create(
        employee=employee,
        period=period_str,
        defaults={
            'standard_days': standard_days,
            'actual_work_days': actual_work_days,
            'paid_leave_days': paid_leave_days,
            'unpaid_leave_days': unpaid_leave_days,
            'ot_hours': ot_hours,
            'late_early_count': late_early_count,
        }
    )
    return summary
