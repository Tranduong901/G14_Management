from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import Role, Branch
from crm.models import (
    Lead,
    LeadStatus,
    LeadSource,
    Opportunity,
    OpportunityStage,
    CrmActivity,
    ActivityType,
    ActivityStatus,
)
from crm.services import (
    generate_lead_code,
    generate_opportunity_code,
    convert_lead_to_opportunity,
    convert_opportunity_to_customer_and_order,
    get_sales_funnel_analytics,
)
from catalog.models import Customer
from sales.models import SalesOrder, OrderStatus

User = get_user_model()

class Phase4CRMTestCase(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(code='CN-HN-CRM', name='Chi nhánh Hà Nội CRM')
        self.sales_user = User.objects.create_user(
            username='sales_crm_test', email='sales_crm@g14.vn', password='password123',
            role=Role.BH, branch=self.branch
        )
        self.manager_user = User.objects.create_user(
            username='manager_crm_test', email='ql_crm@g14.vn', password='password123',
            role=Role.QL, branch=self.branch
        )

    def test_01_lead_creation_and_conversion_to_opportunity(self):
        # 1. Create Lead
        lead = Lead.objects.create(
            code=generate_lead_code(),
            name='Công ty Công nghệ Alpha',
            phone='0988111222',
            email='contact@alpha.vn',
            company='Alpha Corp',
            source=LeadSource.WEBSITE,
            status=LeadStatus.NEW,
            assigned_to=self.sales_user,
            branch=self.branch
        )
        self.assertEqual(lead.status, LeadStatus.NEW)

        # 2. Convert to Opportunity
        opp = convert_lead_to_opportunity(
            lead=lead,
            opp_name='Cung cấp 30 iPad Air cho Alpha Corp',
            expected_revenue=Decimal('450000000.00'),
            expected_close_date=timezone.now().date(),
            user=self.sales_user
        )

        lead.refresh_from_db()
        self.assertEqual(lead.status, LeadStatus.QUALIFIED)
        self.assertEqual(opp.lead, lead)
        self.assertEqual(opp.stage, OpportunityStage.PROSPECTING)
        self.assertEqual(opp.probability, 10)
        self.assertEqual(opp.expected_revenue, Decimal('450000000.00'))

    def test_02_crm_activities_tracking(self):
        lead = Lead.objects.create(
            code=generate_lead_code(),
            name='Nguyễn Văn Beta',
            phone='0977333444',
            assigned_to=self.sales_user,
            branch=self.branch
        )
        opp = convert_lead_to_opportunity(
            lead=lead,
            opp_name='Mua sắm MacBook Pro cho nhân viên',
            expected_revenue=Decimal('120000000.00'),
            user=self.sales_user
        )

        # Create Activity
        act = CrmActivity.objects.create(
            activity_type=ActivityType.CALL,
            subject='Gọi điện tư vấn cấu hình MacBook M3',
            lead=lead,
            opportunity=opp,
            due_date=timezone.now(),
            status=ActivityStatus.COMPLETED,
            assigned_to=self.sales_user,
            result='Khách hàng đồng ý nhận bảng báo giá 3 cấu hình'
        )
        self.assertEqual(act.status, ActivityStatus.COMPLETED)
        self.assertEqual(opp.activities.count(), 1)

    def test_03_convert_opportunity_to_f04_customer_and_sales_order(self):
        lead = Lead.objects.create(
            code=generate_lead_code(),
            name='Đỗ Minh Doanh Nghiệp',
            phone='0911555666',
            email='do.minh@vietcorp.vn',
            company='VietCorp JSC',
            assigned_to=self.sales_user,
            branch=self.branch
        )
        opp = convert_lead_to_opportunity(
            lead=lead,
            opp_name='Gói điện thoại Samsung Galaxy S24 Ultra',
            expected_revenue=Decimal('280000000.00'),
            user=self.sales_user
        )

        # Convert Opportunity to Customer & Sales Order in F04
        customer, order = convert_opportunity_to_customer_and_order(opp, user=self.sales_user)

        # Verify Customer created in catalog
        self.assertIsNotNone(customer)
        self.assertEqual(customer.phone, '0911555666')
        self.assertEqual(customer.name, 'Đỗ Minh Doanh Nghiệp')

        # Verify SalesOrder created in sales module (F04)
        self.assertIsNotNone(order)
        self.assertEqual(order.customer, customer)
        self.assertEqual(order.staff, self.sales_user)
        self.assertEqual(order.branch, self.branch)
        self.assertEqual(order.status, OrderStatus.DRAFT)
        self.assertEqual(order.total_amount, Decimal('280000000.00'))

        # Verify Opportunity updated to CLOSED_WON
        opp.refresh_from_db()
        self.assertEqual(opp.stage, OpportunityStage.CLOSED_WON)
        self.assertEqual(opp.probability, 100)
        self.assertEqual(opp.converted_order, order)

        # Verify Lead marked as CONVERTED
        lead.refresh_from_db()
        self.assertEqual(lead.status, LeadStatus.CONVERTED)
        self.assertEqual(lead.converted_customer, customer)

    def test_04_sales_funnel_and_conversion_rates_analytics(self):
        # Create opportunities in various stages
        Opportunity.objects.create(
            code=generate_opportunity_code(), name='Opp 1', stage=OpportunityStage.PROSPECTING,
            expected_revenue=Decimal('50000000'), assigned_to=self.sales_user, branch=self.branch
        )
        Opportunity.objects.create(
            code=generate_opportunity_code(), name='Opp 2', stage=OpportunityStage.PROPOSAL,
            expected_revenue=Decimal('80000000'), assigned_to=self.sales_user, branch=self.branch
        )
        Opportunity.objects.create(
            code=generate_opportunity_code(), name='Opp 3', stage=OpportunityStage.CLOSED_WON,
            expected_revenue=Decimal('100000000'), assigned_to=self.sales_user, branch=self.branch
        )

        analytics = get_sales_funnel_analytics(branch=self.branch)

        self.assertEqual(analytics['total_opps'], 3)
        self.assertEqual(analytics['won_opps'], 1)
        self.assertEqual(analytics['total_won_value'], 100000000.0)
        self.assertAlmostEqual(analytics['win_rate'], 33.3, places=1)
