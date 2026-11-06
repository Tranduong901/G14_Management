from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum

from hr.models import (
    Employee,
    LaborContract,
    PayrollPeriod,
    PayrollItem,
    PayrollPeriodStatus,
    MonthlyAttendanceSummary,
)
from hr.services import calculate_monthly_attendance_summary
from finance.models import CashLedger, LedgerType, PaymentMethod, ReferenceType
from finance.services import generate_ledger_code
from approvals.services import submit_for_approval, WorkflowType
from auditlog.services import log_activity

COMMISSION_DEFAULT_RATE = Decimal('0.01')  # 1% hoa hồng trên đơn hàng thanh toán thành công
BHXH_RATE = Decimal('0.08')                # 8%
BHYT_RATE = Decimal('0.015')               # 1.5%
BHTN_RATE = Decimal('0.01')                # 1%
PERSONAL_DEDUCTION = Decimal('11000000.00') # 11 triệu VNĐ
DEPENDENT_DEDUCTION = Decimal('4400000.00') # 4.4 triệu VNĐ / người

def calculate_progressive_pit(taxable_income):
    """Calculates Vietnamese Progressive Personal Income Tax (7 brackets)."""
    if taxable_income <= Decimal('0.00'):
        return Decimal('0.00')

    ti = Decimal(str(taxable_income))
    if ti <= Decimal('5000000'):
        tax = ti * Decimal('0.05')
    elif ti <= Decimal('10000000'):
        tax = ti * Decimal('0.10') - Decimal('250000')
    elif ti <= Decimal('18000000'):
        tax = ti * Decimal('0.15') - Decimal('750000')
    elif ti <= Decimal('32000000'):
        tax = ti * Decimal('0.20') - Decimal('1650000')
    elif ti <= Decimal('52000000'):
        tax = ti * Decimal('0.25') - Decimal('3250000')
    elif ti <= Decimal('80000000'):
        tax = ti * Decimal('0.30') - Decimal('5850000')
    else:
        tax = ti * Decimal('0.35') - Decimal('9850000')

    return max(Decimal('0.00'), tax.quantize(Decimal('1')))

def get_employee_commission(employee, year, month, commission_rate=COMMISSION_DEFAULT_RATE):
    """Calculates commission from successful paid sales orders handled by this staff."""
    if not employee.user:
        return Decimal('0.00'), Decimal('0.00')

    from sales.models import SalesOrder, PaymentStatus
    orders = SalesOrder.objects.filter(
        staff=employee.user,
        payment_status=PaymentStatus.PAID,
        order_date__year=year,
        order_date__month=month
    )
    total_rev = orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    commission = (total_rev * commission_rate).quantize(Decimal('1'))
    return commission, total_rev

@transaction.atomic
def generate_payroll_period(year, month, standard_work_days=Decimal('26.0'), user=None, notes=''):
    """
    Generates or recalculates a payroll period for all active employees.
    """
    code = f"BL-{year:04d}-{month:02d}"
    name = f"Bảng lương tháng {month:02d}/{year}"

    period, created = PayrollPeriod.objects.get_or_create(
        code=code,
        defaults={
            'name': name,
            'year': year,
            'month': month,
            'standard_work_days': standard_work_days,
            'status': PayrollPeriodStatus.DRAFT,
            'notes': notes,
            'created_by': user,
        }
    )

    if period.status in [PayrollPeriodStatus.LOCKED, PayrollPeriodStatus.PAID]:
        raise ValidationError(f"Bảng lương {period.code} đã khóa hoặc đã chi trả, không thể tính toán lại.")

    # Remove existing draft items to recalculate cleanly
    period.items.all().delete()

    active_employees = Employee.objects.filter(status='ACTIVE')
    for emp in active_employees:
        contract = emp.active_contract
        base_salary = contract.base_salary if contract else Decimal('0.00')
        allowance = contract.allowance if contract else Decimal('0.00')
        ins_salary = contract.insurance_salary if (contract and contract.insurance_salary > 0) else base_salary

        # Get attendance summary
        att_summary = calculate_monthly_attendance_summary(emp, year, month, standard_days=standard_work_days)
        actual_work_days = att_summary.actual_work_days
        paid_leave_days = att_summary.paid_leave_days
        ot_hours = att_summary.ot_hours

        # If no attendance recorded yet, default to full standard days for calculation demo
        if actual_work_days == Decimal('0.00') and paid_leave_days == Decimal('0.00'):
            actual_work_days = standard_work_days

        # Salary calculations
        daily_rate = (base_salary / standard_work_days) if standard_work_days > 0 else Decimal('0.00')
        actual_salary = (daily_rate * actual_work_days).quantize(Decimal('1'))
        paid_leave_salary = (daily_rate * paid_leave_days).quantize(Decimal('1'))

        # OT pay (150% standard hourly rate)
        hourly_rate = (daily_rate / Decimal('8.0')) if daily_rate > 0 else Decimal('0.00')
        ot_pay = (ot_hours * hourly_rate * Decimal('1.5')).quantize(Decimal('1'))

        # Commission
        commission, eligible_revenue = get_employee_commission(emp, year, month)

        # Gross Income
        gross_income = actual_salary + paid_leave_salary + allowance + ot_pay + commission

        # Social Insurances (employee share)
        bhxh = (ins_salary * BHXH_RATE).quantize(Decimal('1'))
        bhyt = (ins_salary * BHYT_RATE).quantize(Decimal('1'))
        bhtn = (ins_salary * BHTN_RATE).quantize(Decimal('1'))
        total_insurance = bhxh + bhyt + bhtn

        # PIT calculations
        dep_deduction = (Decimal(emp.dependents_count) * DEPENDENT_DEDUCTION).quantize(Decimal('1'))
        taxable_income = max(Decimal('0.00'), gross_income - total_insurance - PERSONAL_DEDUCTION - dep_deduction)
        income_tax = calculate_progressive_pit(taxable_income)

        # Net salary
        net_salary = max(Decimal('0.00'), gross_income - total_insurance - income_tax)

        PayrollItem.objects.create(
            period=period,
            employee=emp,
            contract=contract,
            base_salary=base_salary,
            allowance=allowance,
            standard_work_days=standard_work_days,
            actual_work_days=actual_work_days,
            actual_salary=actual_salary,
            paid_leave_days=paid_leave_days,
            paid_leave_salary=paid_leave_salary,
            sales_commission=commission,
            eligible_sales_revenue=eligible_revenue,
            ot_pay=ot_pay,
            gross_income=gross_income,
            bhxh_amount=bhxh,
            bhyt_amount=bhyt,
            bhtn_amount=bhtn,
            total_insurance=total_insurance,
            personal_deduction=PERSONAL_DEDUCTION,
            dependent_deduction=dep_deduction,
            taxable_income=taxable_income,
            income_tax=income_tax,
            net_salary=net_salary,
            status='UNPAID',
            created_by=user
        )

    period.recalculate_totals()
    log_activity(
        user=user,
        action='CREATE' if created else 'UPDATE',
        obj=period,
        changes={'code': period.code, 'total_net': str(period.total_net)}
    )
    return period

@transaction.atomic
def submit_payroll_for_approval(period, user=None):
    """Submits payroll period to multi-step approval engine."""
    if period.status not in [PayrollPeriodStatus.DRAFT, PayrollPeriodStatus.PENDING]:
        raise ValidationError("Chỉ bảng lương ở trạng thái Dự thảo mới có thể gửi phê duyệt.")

    period.status = PayrollPeriodStatus.PENDING
    period.save(update_fields=['status'])

    app_req = submit_for_approval(
        period,
        requester=user,
        title=f"Phê duyệt {period.name} (Tổng chi: {period.total_net:,.0f} đ)",
        notes=f"Bảng lương {period.items.count()} nhân sự. Tổng thu nhập Gross: {period.total_gross:,.0f} đ, Thuế: {period.total_tax:,.0f} đ.",
        workflow_type=WorkflowType.PAYROLL
    )
    return app_req

@transaction.atomic
def lock_payroll_period(period, user=None):
    """Locks approved payroll period to freeze all figures before payout."""
    if period.status != PayrollPeriodStatus.APPROVED:
        raise ValidationError("Chỉ bảng lương đã được Quản lý/Giám đốc phê duyệt mới được khóa sổ.")

    period.status = PayrollPeriodStatus.LOCKED
    period.locked_at = timezone.now()
    period.locked_by = user
    period.save(update_fields=['status', 'locked_at', 'locked_by'])

    log_activity(
        user=user,
        action='UPDATE',
        obj=period,
        changes={'action': 'LOCK', 'code': period.code}
    )
    return period

@transaction.atomic
def disburse_payroll(period, payment_method=PaymentMethod.BANK_TRANSFER, user=None):
    """
    Executes payout for payroll period:
    - F08 Integration: Creates CashLedger payment record in finance module.
    - Marks period and all payslips as PAID.
    """
    if period.status not in [PayrollPeriodStatus.APPROVED, PayrollPeriodStatus.LOCKED]:
        raise ValidationError("Bảng lương phải được phê duyệt hoặc khóa sổ trước khi thực hiện chi trả.")

    if period.total_net <= Decimal('0.00'):
        raise ValidationError("Tổng tiền thực lĩnh chi trả phải lớn hơn 0.")

    # 1. Create CashLedger entry in Finance F08
    ledger_entry = CashLedger.objects.create(
        code=generate_ledger_code(prefix='PC-LUONG'),
        transaction_type=LedgerType.PAYMENT,
        amount=period.total_net,
        payment_method=payment_method,
        reference_type=ReferenceType.PAYROLL,
        reference_id=period.code,
        reason=f"Chi trả lương tháng {period.month}/{period.year} theo bảng lương {period.code} ({period.items.count()} CBNV).",
        recorded_by=user,
        created_by=user
    )

    # 2. Update period status
    period.status = PayrollPeriodStatus.PAID
    period.paid_at = timezone.now()
    period.paid_by = user
    period.cash_ledger = ledger_entry
    period.save(update_fields=['status', 'paid_at', 'paid_by', 'cash_ledger'])

    # 3. Update all individual payslips
    now = timezone.now()
    for item in period.items.all():
        item.status = 'PAID'
        item.paid_at = now
        item.cash_ledger_item = ledger_entry
        item.save(update_fields=['status', 'paid_at', 'cash_ledger_item'])

    log_activity(
        user=user,
        action='PAYMENT',
        obj=period,
        changes={
            'code': period.code,
            'ledger_code': ledger_entry.code,
            'total_net': str(period.total_net),
            'status': 'PAID'
        }
    )
    return period, ledger_entry
