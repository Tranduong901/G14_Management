from decimal import Decimal
from datetime import date, time
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import Role, Branch, DataScope
from hr.models import (
    Employee,
    LaborContract,
    ContractType,
    WorkShift,
    AttendanceRecord,
    AttendanceStatus,
    LeaveEntitlement,
    LeaveRequest,
    LeaveType,
    LeaveStatus,
    PayrollPeriod,
    PayrollItem,
    PayrollPeriodStatus,
)
from hr.services import (
    create_labor_contract,
    transfer_employee,
    record_attendance_manual,
    update_attendance_manual,
    submit_leave_request,
)
from hr.payroll_services import (
    generate_payroll_period,
    submit_payroll_for_approval,
    lock_payroll_period,
    disburse_payroll,
    calculate_progressive_pit,
)
from approvals.services import ensure_default_workflow_configs, approve_request
from approvals.models import ApprovalRequest, ApprovalStatus
from finance.models import CashLedger, LedgerType, ReferenceType
from catalog.models import Customer, Product, ProductCategory
from sales.models import SalesOrder, SalesOrderDetail, OrderStatus, PaymentStatus

User = get_user_model()

class Phase2HRAndPayrollTestCase(TestCase):
    def setUp(self):
        ensure_default_workflow_configs()

        self.branch_hn = Branch.objects.create(code='CN-HN', name='Chi nhánh Hà Nội')
        self.branch_hcm = Branch.objects.create(code='CN-HCM', name='Chi nhánh TP.HCM')

        # Users
        self.hr_user = User.objects.create_user(
            username='hr_admin', email='hr@g14.vn', password='password123',
            role=Role.HR, branch=self.branch_hn, can_view_payroll=True
        )
        self.kt_user = User.objects.create_user(
            username='kt_user', email='kt@g14.vn', password='password123',
            role=Role.KT, branch=self.branch_hn, can_view_payroll=True
        )
        self.ql_user = User.objects.create_user(
            username='ql_user', email='ql@g14.vn', password='password123',
            role=Role.QL, branch=self.branch_hn, can_view_payroll=True
        )
        self.admin_no_payroll = User.objects.create_superuser(
            username='admin_nopayroll', email='admin_no@g14.vn', password='password123',
            role=Role.ADMIN, can_view_payroll=False
        )
        self.staff_user = User.objects.create_user(
            username='staff_nv1', email='nv1@g14.vn', password='password123',
            role=Role.BH, branch=self.branch_hn
        )
        self.staff_user2 = User.objects.create_user(
            username='staff_nv2', email='nv2@g14.vn', password='password123',
            role=Role.BH, branch=self.branch_hn
        )

        # Employees
        self.emp1 = Employee.objects.create(
            code='NV-TEST01',
            full_name='Nguyễn Văn Test',
            department='KD',
            position='Chuyên viên Bán hàng',
            phone='0988000001',
            email='nv1@g14.vn',
            user=self.staff_user,
            branch=self.branch_hn,
            id_card_number='001090000001',
            tax_code='8000000001',
            bank_account_number='1900000001',
            bank_name='Vietcombank',
            dependents_count=1,
            status='ACTIVE'
        )
        self.emp2 = Employee.objects.create(
            code='NV-TEST02',
            full_name='Trần Thị Test 2',
            department='KD',
            position='Tư vấn viên',
            phone='0988000002',
            email='nv2@g14.vn',
            user=self.staff_user2,
            branch=self.branch_hn,
            dependents_count=0,
            status='ACTIVE'
        )

        # Contracts
        self.contract1 = create_labor_contract(
            employee=self.emp1,
            contract_type=ContractType.DEFINITE_1Y,
            start_date=date(2026, 1, 1),
            base_salary=Decimal('20000000.00'),
            allowance=Decimal('2000000.00'),
            insurance_salary=Decimal('20000000.00'),
            user=self.hr_user
        )
        self.contract2 = create_labor_contract(
            employee=self.emp2,
            contract_type=ContractType.DEFINITE_1Y,
            start_date=date(2026, 1, 1),
            base_salary=Decimal('15000000.00'),
            allowance=Decimal('1000000.00'),
            insurance_salary=Decimal('15000000.00'),
            user=self.hr_user
        )

        # Shift
        self.shift = WorkShift.objects.create(
            code='CA-HC', name='Ca Hành chính',
            start_time=time(8, 0), end_time=time(17, 30),
            standard_work_units=Decimal('1.00')
        )

        # Leave entitlement
        LeaveEntitlement.objects.create(
            employee=self.emp1, year=2026,
            total_days=Decimal('12.00'), used_days=Decimal('0.00'), remaining_days=Decimal('12.00')
        )

    # 1. D1: Hồ sơ nhân viên, hợp đồng & điều chuyển chi nhánh
    def test_01_employee_contract_and_transfer(self):
        self.assertEqual(self.emp1.active_contract.base_salary, Decimal('20000000.00'))
        
        # New contract replaces previous active contract
        new_c = create_labor_contract(
            employee=self.emp1,
            contract_type=ContractType.INDEFINITE,
            start_date=date(2026, 6, 1),
            base_salary=Decimal('25000000.00'),
            allowance=Decimal('3000000.00'),
            user=self.hr_user
        )
        self.contract1.refresh_from_db()
        self.assertFalse(self.contract1.is_active)
        self.assertEqual(self.emp1.active_contract.base_salary, Decimal('25000000.00'))

        # Transfer employee to HCM branch
        transfer_employee(
            employee=self.emp1,
            new_branch=self.branch_hcm,
            new_position='Trưởng nhóm Bán hàng HCM',
            decision_number='QD-2026-001',
            reason='Mở rộng chi nhánh miền Nam',
            user=self.hr_user
        )
        self.emp1.refresh_from_db()
        self.assertEqual(self.emp1.branch.code, 'CN-HCM')
        self.assertEqual(self.emp1.position, 'Trưởng nhóm Bán hàng HCM')
        self.assertTrue(self.emp1.history_records.filter(decision_number='QD-2026-001').exists())

    # 2. D2: Chấm công thủ công, chống trùng lặp & audit log khi sửa
    def test_02_attendance_manual_and_audit_log(self):
        today = date(2026, 11, 2)
        # Record attendance manually
        rec = record_attendance_manual(
            employee=self.emp1,
            date=today,
            shift=self.shift,
            work_units=Decimal('1.00'),
            check_in=time(8, 0),
            check_out=time(17, 30),
            status=AttendanceStatus.PRESENT,
            user=self.hr_user
        )
        self.assertEqual(rec.work_units, Decimal('1.00'))

        # Duplicate check: same employee, date, and shift MUST fail
        with self.assertRaises(ValidationError):
            record_attendance_manual(
                employee=self.emp1,
                date=today,
                shift=self.shift,
                work_units=Decimal('1.00'),
                user=self.hr_user
            )

        # Edit attendance: mandatory reason required
        with self.assertRaises(ValidationError):
            update_attendance_manual(
                record=rec,
                new_work_units=Decimal('0.50'),
                new_status=AttendanceStatus.HALF_DAY,
                reason="",  # Missing reason
                user=self.hr_user
            )

        # Edit with valid reason creates audit log
        update_attendance_manual(
            record=rec,
            new_work_units=Decimal('0.50'),
            new_status=AttendanceStatus.HALF_DAY,
            reason="Nhân viên xin về sớm buổi chiều đi khám bệnh",
            user=self.hr_user
        )
        rec.refresh_from_db()
        self.assertEqual(rec.work_units, Decimal('0.50'))
        self.assertEqual(rec.status, AttendanceStatus.HALF_DAY)
        self.assertEqual(rec.audit_logs.count(), 1)
        audit = rec.audit_logs.first()
        self.assertEqual(audit.old_values['work_units'], '1.00')
        self.assertEqual(audit.new_values['work_units'], '0.50')

    # 3. D2: Đơn xin nghỉ phép & tự động trừ quỹ phép năm
    def test_03_leave_request_and_entitlement_calculation(self):
        # Exceeding remaining days must fail
        with self.assertRaises(ValidationError):
            submit_leave_request(
                employee=self.emp1,
                leave_type=LeaveType.ANNUAL,
                start_date=date(2026, 11, 10),
                end_date=date(2026, 11, 25),
                days_count=Decimal('15.0'),  # 15 > 12 remaining
                reason="Nghỉ phép dài ngày",
                user=self.staff_user
            )

        # Valid leave request submits to approval engine
        lv = submit_leave_request(
            employee=self.emp1,
            leave_type=LeaveType.ANNUAL,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 11),
            days_count=Decimal('2.0'),
            reason="Việc gia đình",
            user=self.staff_user
        )
        self.assertEqual(lv.status, LeaveStatus.PENDING)

        # Manager approves via Approval Request
        app_req = ApprovalRequest.objects.filter(object_id=str(lv.pk)).first()
        self.assertIsNotNone(app_req)
        approve_request(app_req, user=self.ql_user, comment="Duyệt cho nghỉ 2 ngày")

        lv.refresh_from_db()
        self.assertEqual(lv.status, LeaveStatus.APPROVED)
        ent = self.emp1.leave_entitlement
        ent.refresh_from_db()
        self.assertEqual(ent.used_days, Decimal('2.00'))
        self.assertEqual(ent.remaining_days, Decimal('10.00'))

    # 4. D3: Tính thưởng hoa hồng F04, thuế TNCN lũy tiến & chi sổ quỹ F08
    def test_04_payroll_commission_progressive_tax_and_f08_cashledger(self):
        # Create completed paid sales order for staff_user to earn commission
        customer = Customer.objects.create(code='KH-PAY01', name='Khách hàng mua VIP')
        product = Product.objects.create(
            code='SP-PAY01', name='Laptop Gaming Asus',
            price=Decimal('50000000'), cost_price=Decimal('40000000'),
            category=ProductCategory.LAPTOP
        )
        order = SalesOrder.objects.create(
            code='DH-PAY-01',
            customer=customer,
            staff=self.staff_user,
            total_amount=Decimal('50000000'),
            order_date=timezone.now(),
            status=OrderStatus.COMPLETED,
            payment_status=PaymentStatus.PAID
        )

        now = timezone.now()
        # Generate Payroll
        period = generate_payroll_period(year=now.year, month=now.month, standard_work_days=Decimal('26.0'), user=self.hr_user)
        self.assertEqual(period.items.count(), 2)

        item1 = period.items.filter(employee=self.emp1).first()
        # Base salary = 20M, Allowance = 2M
        # Commission: 1% of 50M = 500,000 đ
        self.assertEqual(item1.sales_commission, Decimal('500000'))
        # Gross = 20M + 2M + 500k = 22,500,000 đ
        self.assertEqual(item1.gross_income, Decimal('22500000'))
        # Insurance (10.5% of 20M) = 2,100,000 đ (BHXH 1.6M, BHYT 300k, BHTN 200k)
        self.assertEqual(item1.total_insurance, Decimal('2100000'))
        # Deductions: personal 11M + dependent 4.4M (1 dependent) = 15.4M
        # Taxable income = 22.5M - 2.1M - 15.4M = 5,000,000 đ
        self.assertEqual(item1.taxable_income, Decimal('5000000'))
        # PIT: 5M * 5% = 250,000 đ
        self.assertEqual(item1.income_tax, Decimal('250000'))
        # Net = 22.5M - 2.1M - 250k = 20,150,000 đ
        self.assertEqual(item1.net_salary, Decimal('20150000'))

        # Submit payroll for approval (2 steps: KT -> QL)
        app_req = submit_payroll_for_approval(period, user=self.hr_user)
        self.assertEqual(period.status, PayrollPeriodStatus.PENDING)

        # Step 1: KT approves
        approve_request(app_req, user=self.kt_user, comment="KT đã kiểm tra")
        # Step 2: QL approves final step
        approve_request(app_req, user=self.ql_user, comment="Giám đốc phê duyệt chi lương")
        period.refresh_from_db()
        self.assertEqual(period.status, PayrollPeriodStatus.APPROVED)

        # Disburse payroll -> F08 CashLedger
        period, ledger = disburse_payroll(period, user=self.kt_user)
        self.assertEqual(period.status, PayrollPeriodStatus.PAID)
        self.assertIsNotNone(period.cash_ledger)
        self.assertEqual(ledger.transaction_type, LedgerType.PAYMENT)
        self.assertEqual(ledger.reference_type, ReferenceType.PAYROLL)
        self.assertEqual(ledger.amount, period.total_net)

    # 5. Phân quyền xem lương bảo mật tuyệt đối
    def test_05_payroll_access_confidentiality(self):
        client = Client()
        now = timezone.now()
        period = generate_payroll_period(year=now.year, month=now.month, standard_work_days=Decimal('26.0'), user=self.hr_user)
        item1 = period.items.filter(employee=self.emp1).first()
        item2 = period.items.filter(employee=self.emp2).first()

        # Regular employee (staff_user) CANNOT access global payroll list
        client.force_login(self.staff_user)
        resp = client.get('/hr/payroll/')
        self.assertNotEqual(resp.status_code, 200)

        # Regular employee CANNOT view another employee's payslip
        resp = client.get(f'/hr/payroll/payslip/{item2.pk}/')
        self.assertRedirects(resp, '/hr/my-payslips/')

        # Regular employee CAN view their own payslip
        resp = client.get(f'/hr/payroll/payslip/{item1.pk}/')
        self.assertEqual(resp.status_code, 200)

        # Admin WITHOUT can_view_payroll CANNOT access global payroll
        client.force_login(self.admin_no_payroll)
        resp = client.get('/hr/payroll/')
        self.assertNotEqual(resp.status_code, 200)

        # HR and KT CAN view global payroll
        client.force_login(self.hr_user)
        resp = client.get('/hr/payroll/')
        self.assertEqual(resp.status_code, 200)
