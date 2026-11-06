from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.models import Role
from accounts.decorators import role_required
from auditlog.services import log_activity
from approvals.models import (
    ApprovalWorkflowConfig,
    ApprovalStepConfig,
    ApprovalRequest,
    ApprovalStatus,
)
from approvals.forms import (
    ApprovalWorkflowConfigForm,
    ApprovalStepConfigForm,
    ApprovalDecisionForm,
)
from approvals.services import (
    ensure_default_workflow_configs,
    approve_request,
    reject_request,
)

@login_required
@role_required([Role.QL, Role.ADMIN])
def workflow_list_view(request):
    ensure_default_workflow_configs()
    workflows = ApprovalWorkflowConfig.objects.prefetch_related('steps').all()
    return render(request, 'approvals/workflow_list.html', {
        'workflows': workflows,
    })

@login_required
@role_required([Role.QL, Role.ADMIN])
def workflow_edit_view(request, pk):
    workflow = get_object_or_404(ApprovalWorkflowConfig, pk=pk)
    step_form = ApprovalStepConfigForm()

    if request.method == 'POST':
        if 'update_workflow' in request.POST:
            form = ApprovalWorkflowConfigForm(request.POST, instance=workflow)
            if form.is_valid():
                form.save()
                messages.success(request, f"Cập nhật quy trình '{workflow.name}' thành công.")
                return redirect('approvals:workflow_edit', pk=workflow.pk)
        elif 'add_step' in request.POST:
            step_form = ApprovalStepConfigForm(request.POST)
            if step_form.is_valid():
                step = step_form.save(commit=False)
                step.workflow = workflow
                step.save()
                messages.success(request, f"Đã thêm bước duyệt #{step.step_number}: {step.name}.")
                return redirect('approvals:workflow_edit', pk=workflow.pk)
    else:
        form = ApprovalWorkflowConfigForm(instance=workflow)

    return render(request, 'approvals/workflow_form.html', {
        'workflow': workflow,
        'form': form,
        'step_form': step_form,
        'steps': workflow.steps.all().order_by('step_number'),
    })

@login_required
@role_required([Role.QL, Role.ADMIN])
def step_delete_view(request, workflow_pk, step_pk):
    step = get_object_or_404(ApprovalStepConfig, pk=step_pk, workflow_id=workflow_pk)
    if request.method == 'POST':
        step.delete()
        messages.success(request, f"Đã xóa bước duyệt thành công.")
    return redirect('approvals:workflow_edit', pk=workflow_pk)

@login_required
def pending_approvals_view(request):
    """Lists requests waiting for approval by the current user."""
    user = request.user
    pending_qs = ApprovalRequest.objects.filter(status=ApprovalStatus.PENDING).select_related(
        'workflow', 'requester', 'content_type'
    ).order_by('-created_at')

    # Filter by user role / specific approver / superuser
    my_pending = []
    for req in pending_qs:
        if req.can_user_approve(user):
            my_pending.append(req)

    # History of requests I submitted
    my_submitted = ApprovalRequest.objects.filter(requester=user).select_related(
        'workflow', 'content_type'
    ).order_by('-created_at')[:20]

    return render(request, 'approvals/pending_list.html', {
        'my_pending': my_pending,
        'my_submitted': my_submitted,
    })

@login_required
def approval_detail_view(request, pk):
    approval_req = get_object_or_404(
        ApprovalRequest.objects.select_related('workflow', 'requester', 'content_type'),
        pk=pk
    )
    can_approve = approval_req.can_user_approve(request.user) and approval_req.status == ApprovalStatus.PENDING

    if request.method == 'POST' and can_approve:
        form = ApprovalDecisionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            comment = form.cleaned_data['comment']
            try:
                if action == 'APPROVE':
                    approve_request(approval_req, request.user, comment=comment)
                    messages.success(request, f"Đã phê duyệt yêu cầu thành công.")
                else:
                    reject_request(approval_req, request.user, comment=comment)
                    messages.warning(request, f"Đã từ chối yêu cầu thành công.")
                return redirect('approvals:approval_detail', pk=approval_req.pk)
            except Exception as e:
                messages.error(request, f"Lỗi xử lý: {str(e)}")
    else:
        form = ApprovalDecisionForm()

    action_logs = approval_req.action_logs.select_related('actor').all()
    workflow_steps = approval_req.workflow.steps.all().order_by('step_number')

    return render(request, 'approvals/approval_detail.html', {
        'req': approval_req,
        'target_obj': approval_req.content_object,
        'can_approve': can_approve,
        'form': form,
        'action_logs': action_logs,
        'workflow_steps': workflow_steps,
    })
