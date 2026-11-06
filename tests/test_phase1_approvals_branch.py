from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Role, Branch, DataScope
from accounts.scoping import get_scoped_queryset
from catalog.models import Customer
from sales.models import SalesOrder, OrderStatus
from approvals.models import ApprovalWorkflowConfig, ApprovalStepConfig, ApprovalRequest, ApprovalStatus, WorkflowType
from approvals.services import ensure_default_workflow_configs, submit_for_approval, approve_request, reject_request

User = get_user_model()

class Phase1ArchitectureTestCase(TestCase):
    def setUp(self):
        # 1. Create Branches
        self.branch_hn = Branch.objects.create(code='CN-HN', name='Chi nhánh Hà Nội')
        self.branch_hcm = Branch.objects.create(code='CN-HCM', name='Chi nhánh TP.HCM')

        # 2. Create Users with different scopes
        self.admin = User.objects.create_superuser(
            username='admin_arch', email='admin@g14.vn', password='password123',
            role=Role.ADMIN, data_scope=DataScope.ALL
        )
        self.manager = User.objects.create_user(
            username='manager_arch', email='ql@g14.vn', password='password123',
            role=Role.QL, branch=self.branch_hn, data_scope=DataScope.BRANCH
        )
        self.staff_hn = User.objects.create_user(
            username='staff_hn', email='staff_hn@g14.vn', password='password123',
            role=Role.BH, branch=self.branch_hn, data_scope=DataScope.PERSONAL
        )
        self.staff_hcm = User.objects.create_user(
            username='staff_hcm', email='staff_hcm@g14.vn', password='password123',
            role=Role.BH, branch=self.branch_hcm, data_scope=DataScope.PERSONAL
        )

        # 3. Create Orders in different branches
        self.customer = Customer.objects.create(code='KH-ARCH01', name='Khách Demo')
        self.order_hn = SalesOrder.objects.create(
            code='DH-ARCH-HN', customer=self.customer, staff=self.staff_hn,
            branch=self.branch_hn, created_by=self.staff_hn
        )
        self.order_hcm = SalesOrder.objects.create(
            code='DH-ARCH-HCM', customer=self.customer, staff=self.staff_hcm,
            branch=self.branch_hcm, created_by=self.staff_hcm
        )

    def test_01_branch_and_data_scope_filtering(self):
        qs = SalesOrder.objects.all()

        # Admin with ALL scope sees both orders
        admin_qs = get_scoped_queryset(qs, self.admin, branch_field='branch', user_field='staff')
        self.assertEqual(admin_qs.count(), 2)

        # Manager with BRANCH scope sees only HN orders
        manager_qs = get_scoped_queryset(qs, self.manager, branch_field='branch', user_field='staff')
        self.assertEqual(manager_qs.count(), 1)
        self.assertEqual(manager_qs.first().branch.code, 'CN-HN')

        # Staff with PERSONAL scope sees only their own order
        staff_qs = get_scoped_queryset(qs, self.staff_hn, branch_field='branch', user_field='staff')
        self.assertEqual(staff_qs.count(), 1)
        self.assertEqual(staff_qs.first().code, 'DH-ARCH-HN')

    def test_02_approval_engine_lifecycle(self):
        # Ensure default workflows
        ensure_default_workflow_configs()
        payroll_wf = ApprovalWorkflowConfig.objects.get(workflow_type=WorkflowType.PAYROLL)
        self.assertGreaterEqual(payroll_wf.steps.count(), 2)

        # Submit an order for approval using multi-step payroll workflow
        app_req = submit_for_approval(
            self.order_hn, requester=self.staff_hn, title="Duyệt đơn hàng đặc biệt",
            workflow_type=WorkflowType.PAYROLL
        )
        self.assertEqual(app_req.status, ApprovalStatus.PENDING)
        self.assertEqual(app_req.current_step, 1)

        # Step 1 approval
        step1_cfg = app_req.current_step_config
        # An accountant or superuser can approve step 1
        accountant = User.objects.create_user(
            username='kt_arch', password='password123', role=Role.KT
        )
        self.assertTrue(app_req.can_user_approve(accountant))

        approve_request(app_req, user=accountant, comment="KT đã kiểm tra khớp tiền")
        app_req.refresh_from_db()
        self.assertEqual(app_req.current_step, 2)
        self.assertEqual(app_req.status, ApprovalStatus.PENDING)

        # Step 2: Manager approves final step
        self.assertTrue(app_req.can_user_approve(self.manager))
        approve_request(app_req, user=self.manager, comment="Giám đốc duyệt hoàn tất")
        app_req.refresh_from_db()
        self.assertEqual(app_req.status, ApprovalStatus.APPROVED)

    def test_03_approval_rejection_requires_comment(self):
        ensure_default_workflow_configs()
        app_req = submit_for_approval(self.order_hn, requester=self.staff_hn, title="Duyệt đơn thử từ chối")
        
        # Empty comment must fail
        with self.assertRaises(Exception):
            reject_request(app_req, user=self.admin, comment="")

        # Non-empty comment succeeds
        reject_request(app_req, user=self.admin, comment="Không đạt tiêu chuẩn công nợ")
        app_req.refresh_from_db()
        self.assertEqual(app_req.status, ApprovalStatus.REJECTED)
