from decimal import Decimal
import uuid
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum, Q

from crm.models import (
    Lead,
    LeadStatus,
    Opportunity,
    OpportunityStage,
    CrmActivity,
    ActivityStatus,
)
from catalog.models import Customer
from sales.models import SalesOrder, OrderStatus, PaymentMethod, PaymentStatus
from sales.services import generate_order_code
from auditlog.services import log_activity

def generate_lead_code():
    return f"LEAD-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"

def generate_opportunity_code():
    return f"OPP-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:4].upper()}"

@transaction.atomic
def convert_lead_to_opportunity(lead, opp_name, expected_revenue, expected_close_date=None, user=None):
    """Converts a Lead into an active sales Opportunity."""
    lead.status = LeadStatus.QUALIFIED
    lead.save(update_fields=['status'])

    opp = Opportunity.objects.create(
        code=generate_opportunity_code(),
        name=opp_name,
        lead=lead,
        stage=OpportunityStage.PROSPECTING,
        probability=Opportunity.STAGE_PROBABILITY[OpportunityStage.PROSPECTING],
        expected_revenue=Decimal(str(expected_revenue)),
        expected_close_date=expected_close_date,
        assigned_to=lead.assigned_to or user,
        branch=lead.branch,
        created_by=user
    )

    log_activity(
        user=user,
        action='CREATE',
        obj=opp,
        changes={'code': opp.code, 'from_lead': lead.code}
    )
    return opp

@transaction.atomic
def convert_opportunity_to_customer_and_order(opportunity, user=None, initial_notes=''):
    """
    F04 Integration:
    Converts an Opportunity into a formal Customer (catalog.Customer)
    and generates a Draft Sales Order (sales.SalesOrder).
    Marks opportunity as CLOSED_WON (100%).
    """
    if opportunity.converted_order:
        return opportunity.customer, opportunity.converted_order

    # 1. Resolve or create Customer
    customer = opportunity.customer
    if not customer and opportunity.lead:
        phone = opportunity.lead.phone.strip()
        existing_cust = Customer.objects.filter(phone=phone).first()
        if existing_cust:
            customer = existing_cust
        else:
            cust_code = f"KH-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
            customer = Customer.objects.create(
                code=cust_code,
                name=opportunity.lead.name,
                phone=phone,
                email=opportunity.lead.email or f"{opportunity.lead.phone}@customer.g14.vn",
                address=opportunity.lead.company or "Khách hàng CRM",
                customer_type='RETAIL' if not opportunity.lead.company else 'WHOLESALE',
                created_by=user
            )

    if not customer:
        cust_code = f"KH-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        customer = Customer.objects.create(
            code=cust_code,
            name=opportunity.name,
            phone=f"09{uuid.uuid4().int % 100000000:08d}",
            email=f"crm_{uuid.uuid4().hex[:6]}@g14.vn",
            address="Khách hàng chuyển đổi từ cơ hội CRM",
            customer_type='RETAIL',
            created_by=user
        )

    # 2. Create SalesOrder in F04 module
    order_code = generate_order_code()
    order = SalesOrder.objects.create(
        code=order_code,
        customer=customer,
        staff=opportunity.assigned_to or user,
        branch=opportunity.branch,
        order_date=timezone.now(),
        status=OrderStatus.DRAFT,
        payment_method=PaymentMethod.CASH,
        payment_status=PaymentStatus.UNPAID,
        total_amount=opportunity.expected_revenue,
        notes=f"Đơn bán hàng chuyển đổi từ cơ hội CRM: {opportunity.name} ({opportunity.code}). {initial_notes}".strip(),
        created_by=user
    )

    # 3. Update Opportunity & Lead status
    opportunity.stage = OpportunityStage.CLOSED_WON
    opportunity.probability = 100
    opportunity.customer = customer
    opportunity.converted_order = order
    opportunity.save()

    if opportunity.lead:
        opportunity.lead.status = LeadStatus.CONVERTED
        opportunity.lead.converted_customer = customer
        opportunity.lead.save(update_fields=['status', 'converted_customer'])

    log_activity(
        user=user,
        action='UPDATE',
        obj=opportunity,
        changes={
            'action': 'CONVERT_TO_ORDER',
            'order_code': order.code,
            'customer_code': customer.code,
            'stage': 'CLOSED_WON'
        }
    )
    return customer, order

def get_sales_funnel_analytics(branch=None, start_date=None, end_date=None):
    """Calculates Sales Funnel stages and conversion metrics."""
    opps = Opportunity.objects.all()
    leads = Lead.objects.all()

    if branch:
        opps = opps.filter(branch=branch)
        leads = leads.filter(branch=branch)
    if start_date:
        opps = opps.filter(created_at__gte=start_date)
        leads = leads.filter(created_at__gte=start_date)
    if end_date:
        opps = opps.filter(created_at__lte=end_date)
        leads = leads.filter(created_at__lte=end_date)

    stages_data = []
    ordered_stages = [
        (OpportunityStage.PROSPECTING, '1. Tìm hiểu nhu cầu'),
        (OpportunityStage.QUALIFICATION, '2. Khảo sát / Đánh giá'),
        (OpportunityStage.PROPOSAL, '3. Báo giá / Đề xuất'),
        (OpportunityStage.NEGOTIATION, '4. Đàm phán thương thảo'),
        (OpportunityStage.CLOSED_WON, '5. Chốt thành công (Won)'),
        (OpportunityStage.CLOSED_LOST, '6. Thất bại (Lost)'),
    ]

    for stage_code, stage_label in ordered_stages:
        stage_opps = opps.filter(stage=stage_code)
        count = stage_opps.count()
        val = stage_opps.aggregate(s=Sum('expected_revenue'))['s'] or Decimal('0.00')
        stages_data.append({
            'stage_code': stage_code,
            'stage_label': stage_label,
            'count': count,
            'total_revenue': float(val),
        })

    total_leads = leads.count()
    qualified_leads = leads.filter(status__in=[LeadStatus.QUALIFIED, LeadStatus.CONVERTED]).count()
    total_opps = opps.count()
    won_opps = opps.filter(stage=OpportunityStage.CLOSED_WON).count()
    lost_opps = opps.filter(stage=OpportunityStage.CLOSED_LOST).count()

    total_won_value = opps.filter(stage=OpportunityStage.CLOSED_WON).aggregate(
        s=Sum('expected_revenue')
    )['s'] or Decimal('0.00')

    # Conversion Rates
    lead_to_opp_rate = (total_opps / total_leads * 100) if total_leads > 0 else 0.0
    win_rate = (won_opps / total_opps * 100) if total_opps > 0 else 0.0
    overall_conversion_rate = (won_opps / total_leads * 100) if total_leads > 0 else 0.0

    return {
        'stages_data': stages_data,
        'total_leads': total_leads,
        'qualified_leads': qualified_leads,
        'total_opps': total_opps,
        'won_opps': won_opps,
        'lost_opps': lost_opps,
        'total_won_value': float(total_won_value),
        'lead_to_opp_rate': round(lead_to_opp_rate, 1),
        'win_rate': round(win_rate, 1),
        'overall_conversion_rate': round(overall_conversion_rate, 1),
    }
