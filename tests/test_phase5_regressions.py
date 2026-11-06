from datetime import date, time
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Branch, DataScope, Role, User
from crm.models import Lead, Opportunity, OpportunityStage
from crm.services import generate_lead_code, generate_opportunity_code
from catalog.models import Customer, Product, Supplier
from hr.models import (
    AttendanceRecord,
    AttendanceStatus,
    Employee,
    LeaveEntitlement,
    LeaveType,
    PayrollPeriodStatus,
    WorkShift,
)
from hr.payroll_services import generate_payroll_period, lock_payroll_period
from hr.services import (
    calculate_monthly_attendance_summary,
    resign_employee,
)
from inventory.models import Warehouse, InventoryTransaction, TransactionType
from inventory.services import transfer_stock
from devices.models import ItemStatus, ProductItem
from purchasing.models import PurchaseDetail, PurchaseReceipt
from purchasing.services import complete_purchase_receipt, generate_receipt_code
from sales.models import SalesOrder, SalesOrderDetail
from sales.services import complete_sales_order, generate_order_code


class Phase5RegressionTestCase(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(code='CN-REG', name='Chi nhánh Regression')
        self.admin = User.objects.create_superuser(
            username='reg_admin',
            password='password123',
            role=Role.ADMIN,
            data_scope='ALL',
            can_view_payroll=True,
        )
        self.employee_user = User.objects.create_user(
            username='reg_employee',
            password='password123',
            role=Role.BH,
            branch=self.branch,
            data_scope=DataScope.BRANCH,
        )
        self.hr_user = User.objects.create_user(
            username='reg_hr',
            password='password123',
            role=Role.HR,
            branch=self.branch,
            data_scope=DataScope.BRANCH,
        )
        self.accountant = User.objects.create_user(
            username='reg_accountant',
            password='password123',
            role=Role.KT,
            branch=self.branch,
            data_scope=DataScope.BRANCH,
        )
        self.manager = User.objects.create_user(
            username='reg_manager',
            password='password123',
            role=Role.QL,
            branch=self.branch,
            data_scope=DataScope.BRANCH,
        )
        self.employee = Employee.objects.create(
            code='NV-REG',
            full_name='Nhân viên Regression',
            position='Tư vấn',
            phone='0900000000',
            user=self.employee_user,
            branch=self.branch,
        )
        self.shift = WorkShift.objects.create(
            code='CA-REG',
            name='Ca Regression',
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

    def test_payroll_lock_freezes_period_and_rejects_recalculation(self):
        period = generate_payroll_period(2026, 11, user=self.admin)
        period.status = PayrollPeriodStatus.APPROVED
        period.save(update_fields=['status'])

        lock_payroll_period(period, user=self.admin)
        period.refresh_from_db()

        self.assertEqual(period.status, PayrollPeriodStatus.LOCKED)
        self.assertIsNotNone(period.locked_at)
        with self.assertRaises(ValidationError):
            generate_payroll_period(2026, 11, user=self.admin)

    def test_resignation_preserves_employee_history_and_deactivates_account(self):
        resign_employee(
            self.employee,
            reason='Kết thúc hợp đồng',
            decision_number='QD-REG-01',
            user=self.admin,
        )
        self.employee.refresh_from_db()
        self.employee_user.refresh_from_db()

        self.assertEqual(self.employee.status, 'RESIGNED')
        self.assertFalse(self.employee_user.is_active)
        self.assertTrue(
            self.employee.history_records.filter(
                event_type='RESIGNATION',
                decision_number='QD-REG-01',
            ).exists()
        )

    def test_summary_includes_ot_and_approved_unpaid_leave_without_double_counting(self):
        LeaveEntitlement.objects.create(
            employee=self.employee,
            year=2026,
            total_days=Decimal('12.00'),
            remaining_days=Decimal('12.00'),
        )
        AttendanceRecord.objects.create(
            employee=self.employee,
            date=date(2026, 11, 3),
            shift=self.shift,
            work_units=Decimal('1.00'),
            ot_hours=Decimal('2.00'),
            status=AttendanceStatus.PRESENT,
        )
        AttendanceRecord.objects.create(
            employee=self.employee,
            date=date(2026, 11, 4),
            shift=self.shift,
            work_units=Decimal('1.00'),
            ot_hours=Decimal('1.00'),
            status=AttendanceStatus.LEAVE_UNPAID,
        )
        from hr.models import LeaveRequest, LeaveStatus

        LeaveRequest.objects.create(
            code='NP-REG-01',
            employee=self.employee,
            leave_type=LeaveType.UNPAID,
            start_date=date(2026, 11, 4),
            end_date=date(2026, 11, 5),
            days_count=Decimal('2.0'),
            reason='Việc riêng',
            status=LeaveStatus.APPROVED,
        )

        summary = calculate_monthly_attendance_summary(self.employee, 2026, 11)

        self.assertEqual(summary.actual_work_days, Decimal('1.00'))
        self.assertEqual(summary.unpaid_leave_days, Decimal('2.00'))
        self.assertEqual(summary.ot_hours, Decimal('3.00'))

    def test_warehouse_is_bound_to_branch(self):
        warehouse = Warehouse.objects.create(
            code='KHO-REG',
            name='Kho Regression',
            branch=self.branch,
        )
        self.assertEqual(warehouse.branch, self.branch)
        self.assertEqual(self.branch.warehouses.get(pk=warehouse.pk), warehouse)

    def test_branch_user_cannot_view_other_branch_inventory_transactions(self):
        other_branch = Branch.objects.create(code='CN-OTHER', name='Chi nhánh khác')
        own_warehouse = Warehouse.objects.create(
            code='KHO-OWN',
            name='Kho cùng chi nhánh',
            branch=self.branch,
        )
        other_warehouse = Warehouse.objects.create(
            code='KHO-OTHER',
            name='Kho khác chi nhánh',
            branch=other_branch,
        )
        from catalog.models import Product

        product = Product.objects.create(
            code='SP-REG',
            name='Sản phẩm Regression',
            price=Decimal('100'),
            cost_price=Decimal('50'),
        )
        InventoryTransaction.objects.create(
            warehouse=own_warehouse,
            transaction_type=TransactionType.IN,
            product=product,
            quantity=1,
            reference_code='REG-OWN',
            created_by=self.employee_user,
        )
        InventoryTransaction.objects.create(
            warehouse=other_warehouse,
            transaction_type=TransactionType.IN,
            product=product,
            quantity=1,
            reference_code='REG-OTHER',
            created_by=self.admin,
        )
        from accounts.scoping import get_scoped_queryset

        visible = get_scoped_queryset(
            InventoryTransaction.objects.all(),
            self.employee_user,
            branch_field='warehouse__branch',
            user_field='created_by',
        )
        self.assertEqual(list(visible.values_list('reference_code', flat=True)), ['REG-OWN'])

    def test_stock_isolated_by_warehouse_and_transfer_preserves_total(self):
        source = Warehouse.objects.create(
            code='KHO-SOURCE',
            name='Kho nguồn',
            branch=self.branch,
        )
        target = Warehouse.objects.create(
            code='KHO-TARGET',
            name='Kho đích',
            branch=self.branch,
        )
        from catalog.models import Product

        bulk_product = Product.objects.create(
            code='SP-BULK-REG',
            name='Sản phẩm rời',
            price=Decimal('100'),
            cost_price=Decimal('50'),
            has_serial=False,
        )
        InventoryTransaction.objects.create(
            warehouse=source,
            transaction_type=TransactionType.IN,
            product=bulk_product,
            quantity=10,
            reference_code='REG-IN',
            created_by=self.employee_user,
        )
        self.assertEqual(bulk_product.get_current_stock(), 10)
        self.assertEqual(bulk_product.get_current_stock(warehouse=source), 10)
        self.assertEqual(bulk_product.get_current_stock(warehouse=target), 0)

        reference = transfer_stock(
            bulk_product,
            4,
            source,
            target,
            user=self.admin,
        )
        self.assertTrue(reference.startswith('CK-'))
        self.assertEqual(bulk_product.get_current_stock(), 10)
        self.assertEqual(bulk_product.get_current_stock(warehouse=source), 6)
        self.assertEqual(bulk_product.get_current_stock(warehouse=target), 4)

        serial_product = Product.objects.create(
            code='SP-SERIAL-REG',
            name='Sản phẩm serial',
            price=Decimal('100'),
            cost_price=Decimal('50'),
            has_serial=True,
        )
        serial = ProductItem.objects.create(
            serial_number='REG-SERIAL-01',
            product=serial_product,
            status=ItemStatus.IN_STOCK,
            warehouse=source,
            created_by=self.admin,
        )
        transfer_stock(
            serial_product,
            1,
            source,
            target,
            user=self.admin,
            serial_numbers=[serial.serial_number],
        )
        self.assertEqual(serial_product.get_current_stock(warehouse=source), 0)
        self.assertEqual(serial_product.get_current_stock(warehouse=target), 1)
        self.assertEqual(serial_product.get_current_stock(), 1)

    def test_branch_user_inventory_summary_defaults_to_own_branch(self):
        other_branch = Branch.objects.create(code='CN-SUM-OTHER', name='Chi nhánh khác')
        own_warehouse = Warehouse.objects.create(
            code='KHO-SUM-OWN',
            name='Kho báo cáo cùng chi nhánh',
            branch=self.branch,
        )
        other_warehouse = Warehouse.objects.create(
            code='KHO-SUM-OTHER',
            name='Kho báo cáo khác chi nhánh',
            branch=other_branch,
        )
        from catalog.models import Product

        product = Product.objects.create(
            code='SP-SUM-REG',
            name='Sản phẩm báo cáo',
            price=Decimal('100'),
            cost_price=Decimal('50'),
            has_serial=False,
        )
        for warehouse, reference in [
            (own_warehouse, 'SUM-OWN'),
            (other_warehouse, 'SUM-OTHER'),
        ]:
            InventoryTransaction.objects.create(
                warehouse=warehouse,
                transaction_type=TransactionType.IN,
                product=product,
                quantity=3,
                reference_code=reference,
                created_by=self.admin,
            )

        self.client.force_login(self.manager)
        response = self.client.get('/inventory/')
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.context['page_obj'] if item.pk == product.pk)
        self.assertEqual(row.stock_qty, 3)

    def test_purchase_and_sale_update_the_selected_warehouse(self):
        warehouse = Warehouse.objects.create(
            code='KHO-FLOW',
            name='Kho luồng nhập xuất',
            branch=self.branch,
        )
        supplier = Supplier.objects.create(
            code='NCC-FLOW',
            name='Nhà cung cấp luồng kho',
            phone='0933333333',
        )
        customer = Customer.objects.create(
            code='KH-FLOW',
            name='Khách hàng luồng kho',
            phone='0944444444',
        )
        product = Product.objects.create(
            code='SP-FLOW',
            name='Sản phẩm luồng kho',
            price=Decimal('100'),
            cost_price=Decimal('50'),
            has_serial=False,
        )
        receipt = PurchaseReceipt.objects.create(
            code=generate_receipt_code(),
            supplier=supplier,
            warehouse=warehouse,
            emergency_reason='Kiểm thử staging',
            created_by=self.admin,
        )
        PurchaseDetail.objects.create(
            receipt=receipt,
            product=product,
            quantity=5,
            unit_price=Decimal('50'),
        )
        complete_purchase_receipt(receipt, user=self.admin)
        self.assertEqual(product.get_current_stock(warehouse=warehouse), 5)

        order = SalesOrder.objects.create(
            code=generate_order_code(),
            customer=customer,
            staff=self.admin,
            branch=self.branch,
            warehouse=warehouse,
            created_by=self.admin,
        )
        SalesOrderDetail.objects.create(
            order=order,
            product=product,
            quantity=2,
            unit_price=Decimal('100'),
        )
        complete_sales_order(order, user=self.admin)
        self.assertEqual(product.get_current_stock(warehouse=warehouse), 3)
        self.assertEqual(product.get_current_stock(), 3)

    def test_crm_delete_requires_role_post_and_preserves_converted_records(self):
        lead = Lead.objects.create(
            code=generate_lead_code(),
            name='Lead xóa',
            phone='0911111111',
            assigned_to=self.admin,
            branch=self.branch,
        )
        client = self.client
        client.force_login(self.employee_user)
        response = client.post(reverse('crm:lead_delete', args=[lead.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Lead.objects.filter(pk=lead.pk).exists())

        client.force_login(self.admin)
        response = client.get(reverse('crm:lead_delete', args=[lead.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Lead.objects.filter(pk=lead.pk).exists())

        response = client.post(reverse('crm:lead_delete', args=[lead.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Lead.objects.filter(pk=lead.pk).exists())

        converted_lead = Lead.objects.create(
            code=generate_lead_code(),
            name='Lead đã dùng',
            phone='0922222222',
            assigned_to=self.admin,
            branch=self.branch,
            status='CONVERTED',
        )
        response = client.post(reverse('crm:lead_delete', args=[converted_lead.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Lead.objects.filter(pk=converted_lead.pk).exists())

        opportunity = Opportunity.objects.create(
            code=generate_opportunity_code(),
            name='Cơ hội xóa',
            assigned_to=self.admin,
            branch=self.branch,
            stage=OpportunityStage.PROSPECTING,
        )
        response = client.post(reverse('crm:opportunity_delete', args=[opportunity.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Opportunity.objects.filter(pk=opportunity.pk).exists())

    def test_ui_role_matrix_and_invalid_form_validation(self):
        admin_client = self.client
        admin_client.force_login(self.admin)
        admin_urls = [
            '/hr/create/',
            '/hr/attendance/create/',
            '/hr/leave/create/',
            '/hr/payroll/create/',
            '/crm/leads/create/',
            '/crm/opportunities/create/',
        ]
        for url in admin_urls:
            self.assertEqual(admin_client.get(url).status_code, 200, url)

        invalid_employee = admin_client.post(
            '/hr/create/',
            {
                'code': '',
                'full_name': '',
                'department': 'INVALID',
                'position': '',
                'phone': '',
            },
        )
        self.assertEqual(invalid_employee.status_code, 200)
        self.assertTrue(invalid_employee.context['form'].errors)

        self.client.force_login(self.employee_user)
        self.assertNotEqual(self.client.get('/hr/create/').status_code, 200)
        self.assertNotEqual(self.client.get('/hr/payroll/').status_code, 200)
        self.assertEqual(self.client.get('/hr/leave/create/').status_code, 200)
        self.assertEqual(self.client.get('/crm/leads/create/').status_code, 200)
        self.assertNotEqual(self.client.get('/finance/ledger/').status_code, 200)

        for user in [self.hr_user, self.accountant, self.manager]:
            self.client.force_login(user)
            self.assertEqual(self.client.get('/hr/payroll/').status_code, 200)
