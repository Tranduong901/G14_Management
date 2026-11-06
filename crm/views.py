from decimal import Decimal
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from accounts.models import Role, Branch
from accounts.decorators import role_required
from accounts.scoping import get_scoped_queryset
from auditlog.services import log_activity
from crm.models import (
    Lead,
    LeadStatus,
    LeadSource,
    Opportunity,
    OpportunityStage,
    CrmActivity,
    ActivityStatus,
    ActivityType,
)
from crm.forms import (
    LeadForm,
    OpportunityForm,
    CrmActivityForm,
)
from crm.services import (
    generate_lead_code,
    generate_opportunity_code,
    convert_lead_to_opportunity,
    convert_opportunity_to_customer_and_order,
    get_sales_funnel_analytics,
)

# ----------------- 1. LEADS -----------------

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def lead_list_view(request):
    leads = Lead.objects.select_related('assigned_to', 'branch', 'converted_customer').all()
    leads = get_scoped_queryset(leads, request.user, branch_field='branch', user_field='assigned_to')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    source = request.GET.get('source', '')

    if q:
        leads = leads.filter(
            Q(code__icontains=q) |
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(company__icontains=q)
        )
    if status:
        leads = leads.filter(status=status)
    if source:
        leads = leads.filter(source=source)

    paginator = Paginator(leads, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'crm/lead_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status,
        'source_filter': source,
        'statuses': LeadStatus.choices,
        'sources': LeadSource.choices,
    })

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def lead_create_view(request):
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.code = generate_lead_code()
            lead.created_by = request.user
            if not lead.assigned_to:
                lead.assigned_to = request.user
            if not lead.branch and request.user.branch:
                lead.branch = request.user.branch
            lead.save()

            log_activity(
                user=request.user,
                action='CREATE',
                obj=lead,
                changes={'code': lead.code, 'name': lead.name}
            )
            messages.success(request, f"Đã tiếp nhận khách hàng tiềm năng {lead.name} ({lead.code}).")
            return redirect('crm:lead_list')
    else:
        initial = {'assigned_to': request.user}
        if request.user.branch:
            initial['branch'] = request.user.branch
        form = LeadForm(initial=initial)

    return render(request, 'crm/lead_form.html', {'form': form, 'title': 'Thêm mới Lead tiềm năng'})

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def lead_edit_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            updated = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated,
                changes={'code': updated.code, 'name': updated.name, 'status': updated.status}
            )
            messages.success(request, f"Cập nhật thông tin Lead {updated.name} thành công.")
            return redirect('crm:lead_list')
    else:
        form = LeadForm(instance=lead)

    return render(request, 'crm/lead_form.html', {'form': form, 'title': f"Sửa Lead {lead.name}", 'lead': lead})

@login_required
@role_required([Role.QL, Role.ADMIN])
def lead_delete_view(request, pk):
    """Deletes only an unconverted lead after explicit POST confirmation."""
    lead = get_object_or_404(
        get_scoped_queryset(Lead.objects.all(), request.user, branch_field='branch', user_field='assigned_to'),
        pk=pk,
    )
    if request.method != 'POST':
        messages.error(request, "Xóa Lead phải được xác nhận bằng biểu mẫu POST.")
        return redirect('crm:lead_list')
    if lead.status == LeadStatus.CONVERTED or lead.converted_customer_id or lead.opportunities.exists():
        messages.error(request, "Không thể xóa Lead đã liên kết dữ liệu CRM/F04; hãy cập nhật trạng thái thay thế.")
        return redirect('crm:lead_list')
    code = lead.code
    with transaction.atomic():
        lead.delete()
    messages.success(request, f"Đã xóa Lead {code}.")
    return redirect('crm:lead_list')

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def lead_convert_to_opp_view(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        opp_name = request.POST.get('opp_name', f"Cơ hội - {lead.name}")
        expected_revenue = request.POST.get('expected_revenue', '0')
        expected_close_date = request.POST.get('expected_close_date') or None

        opp = convert_lead_to_opportunity(
            lead=lead,
            opp_name=opp_name,
            expected_revenue=expected_revenue,
            expected_close_date=expected_close_date,
            user=request.user
        )
        messages.success(request, f"Đã chuyển đổi Lead thành cơ hội bán hàng {opp.name} ({opp.code}).")
        return redirect('crm:opportunity_detail', pk=opp.pk)

    return render(request, 'crm/lead_convert_form.html', {'lead': lead})

# ----------------- 2. OPPORTUNITIES -----------------

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def opportunity_list_view(request):
    opps = Opportunity.objects.select_related('lead', 'customer', 'assigned_to', 'branch', 'converted_order').all()
    opps = get_scoped_queryset(opps, request.user, branch_field='branch', user_field='assigned_to')

    q = request.GET.get('q', '').strip()
    stage = request.GET.get('stage', '')

    if q:
        opps = opps.filter(
            Q(code__icontains=q) |
            Q(name__icontains=q) |
            Q(customer__name__icontains=q) |
            Q(lead__name__icontains=q)
        )
    if stage:
        opps = opps.filter(stage=stage)

    paginator = Paginator(opps, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'crm/opportunity_list.html', {
        'page_obj': page_obj,
        'q': q,
        'stage_filter': stage,
        'stages': OpportunityStage.choices,
    })

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def opportunity_create_view(request):
    if request.method == 'POST':
        form = OpportunityForm(request.POST)
        if form.is_valid():
            opp = form.save(commit=False)
            opp.code = generate_opportunity_code()
            opp.created_by = request.user
            if not opp.assigned_to:
                opp.assigned_to = request.user
            if not opp.branch and request.user.branch:
                opp.branch = request.user.branch
            opp.save()

            log_activity(
                user=request.user,
                action='CREATE',
                obj=opp,
                changes={'code': opp.code, 'name': opp.name, 'revenue': str(opp.expected_revenue)}
            )
            messages.success(request, f"Đã tạo cơ hội bán hàng {opp.name} ({opp.code}).")
            return redirect('crm:opportunity_detail', pk=opp.pk)
    else:
        initial = {'assigned_to': request.user}
        if request.user.branch:
            initial['branch'] = request.user.branch
        form = OpportunityForm(initial=initial)

    return render(request, 'crm/opportunity_form.html', {'form': form, 'title': 'Tạo Cơ hội bán hàng'})

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def opportunity_detail_view(request, pk):
    opp = get_object_or_404(
        Opportunity.objects.select_related('lead', 'customer', 'assigned_to', 'branch', 'converted_order'),
        pk=pk
    )
    activities = opp.activities.select_related('assigned_to').all().order_by('-due_date')

    if request.method == 'POST' and 'convert_to_order' in request.POST:
        customer, order = convert_opportunity_to_customer_and_order(opp, user=request.user)
        messages.success(request, f"Đã chuyển đổi cơ hội thành công! Sinh ra đơn bán hàng {order.code} thuộc phân hệ F04.")
        return redirect('sales:order_detail', pk=order.pk)

    return render(request, 'crm/opportunity_detail.html', {
        'opp': opp,
        'activities': activities,
    })

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def opportunity_edit_view(request, pk):
    opp = get_object_or_404(Opportunity, pk=pk)
    if request.method == 'POST':
        form = OpportunityForm(request.POST, instance=opp)
        if form.is_valid():
            updated = form.save()
            log_activity(
                user=request.user,
                action='UPDATE',
                obj=updated,
                changes={'code': updated.code, 'stage': updated.stage, 'revenue': str(updated.expected_revenue)}
            )
            messages.success(request, f"Cập nhật cơ hội {updated.name} thành công.")
            return redirect('crm:opportunity_detail', pk=updated.pk)
    else:
        form = OpportunityForm(instance=opp)

    return render(request, 'crm/opportunity_form.html', {'form': form, 'title': f"Sửa cơ hội {opp.name}", 'opp': opp})

@login_required
@role_required([Role.QL, Role.ADMIN])
def opportunity_delete_view(request, pk):
    """Deletes only an opportunity that has not produced an F04 order."""
    opp = get_object_or_404(
        get_scoped_queryset(
            Opportunity.objects.all(),
            request.user,
            branch_field='branch',
            user_field='assigned_to',
        ),
        pk=pk,
    )
    if request.method != 'POST':
        messages.error(request, "Xóa cơ hội phải được xác nhận bằng biểu mẫu POST.")
        return redirect('crm:opportunity_detail', pk=opp.pk)
    if opp.converted_order_id or opp.stage == OpportunityStage.CLOSED_WON:
        messages.error(request, "Không thể xóa cơ hội đã tạo đơn F04; hãy giữ lại để bảo toàn lịch sử bán hàng.")
        return redirect('crm:opportunity_detail', pk=opp.pk)
    code = opp.code
    with transaction.atomic():
        opp.delete()
    messages.success(request, f"Đã xóa cơ hội {code}.")
    return redirect('crm:opportunity_list')

# ----------------- 3. ACTIVITIES -----------------

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def activity_list_view(request):
    activities = CrmActivity.objects.select_related('lead', 'opportunity', 'assigned_to').all()
    status = request.GET.get('status', '')
    act_type = request.GET.get('type', '')

    if status:
        activities = activities.filter(status=status)
    if act_type:
        activities = activities.filter(activity_type=act_type)

    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'crm/activity_list.html', {
        'page_obj': page_obj,
        'status_filter': status,
        'type_filter': act_type,
        'statuses': ActivityStatus.choices,
        'types': ActivityType.choices,
    })

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN])
def activity_create_view(request):
    lead_id = request.GET.get('lead')
    opp_id = request.GET.get('opportunity')

    if request.method == 'POST':
        form = CrmActivityForm(request.POST)
        if form.is_valid():
            act = form.save(commit=False)
            act.created_by = request.user
            if not act.assigned_to:
                act.assigned_to = request.user
            act.save()
            messages.success(request, f"Đã ghi nhận hoạt động '{act.subject}'.")
            if act.opportunity:
                return redirect('crm:opportunity_detail', pk=act.opportunity.pk)
            return redirect('crm:activity_list')
    else:
        initial = {'assigned_to': request.user}
        if lead_id:
            initial['lead'] = get_object_or_404(Lead, pk=lead_id)
        if opp_id:
            initial['opportunity'] = get_object_or_404(Opportunity, pk=opp_id)
        form = CrmActivityForm(initial=initial)

    return render(request, 'crm/activity_form.html', {'form': form, 'title': 'Ghi nhận hoạt động chăm sóc'})

# ----------------- 4. SALES FUNNEL REPORT -----------------

@login_required
@role_required([Role.BH, Role.QL, Role.ADMIN, Role.KT])
def sales_funnel_view(request):
    """Visual Sales Funnel report with conversion rates and Chart.js."""
    branch_id = request.GET.get('branch', '')
    branch = None
    if branch_id:
        branch = Branch.objects.filter(pk=branch_id).first()
    elif request.user.data_scope == 'BRANCH' and request.user.branch:
        branch = request.user.branch

    report = get_sales_funnel_analytics(branch=branch)

    stage_labels = [s['stage_label'] for s in report['stages_data']]
    stage_counts = [s['count'] for s in report['stages_data']]
    stage_revenues = [s['total_revenue'] for s in report['stages_data']]

    branches = Branch.objects.filter(is_active=True)

    return render(request, 'crm/sales_funnel.html', {
        'report': report,
        'stage_labels_json': json.dumps(stage_labels),
        'stage_counts_json': json.dumps(stage_counts),
        'stage_revenues_json': json.dumps(stage_revenues),
        'branches': branches,
        'current_branch': branch,
    })
