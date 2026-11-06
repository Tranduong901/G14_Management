from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from approvals.models import (
    ApprovalWorkflowConfig,
    ApprovalStepConfig,
    ApprovalRequest,
    ApprovalActionLog,
    WorkflowType,
    ApprovalStatus,
)
from accounts.models import Role

@transaction.atomic
def ensure_default_workflow_configs():
    """Seeds standard approval workflows for Leave, Purchase Requests, and Payroll."""
    # 1. Leave Request Workflow
    leave_wf, _ = ApprovalWorkflowConfig.objects.get_or_create(
        workflow_type=WorkflowType.LEAVE,
        defaults={'name': 'Quy trình phê duyệt đơn nghỉ phép', 'description': 'Quản lý phê duyệt ngày nghỉ của nhân viên.'}
    )
    if not leave_wf.steps.exists():
        ApprovalStepConfig.objects.create(
            workflow=leave_wf,
            step_number=1,
            name='Quản lý phê duyệt',
            approver_role=Role.QL,
            is_final_step=True
        )

    # 2. Purchase Request Workflow
    scm_wf, _ = ApprovalWorkflowConfig.objects.get_or_create(
        workflow_type=WorkflowType.PURCHASE_REQUEST,
        defaults={'name': 'Quy trình phê duyệt đề nghị nhập hàng', 'description': 'Quản lý phê duyệt đề xuất mua hàng SCM.'}
    )
    if not scm_wf.steps.exists():
        ApprovalStepConfig.objects.create(
            workflow=scm_wf,
            step_number=1,
            name='Quản lý xem xét & phê duyệt',
            approver_role=Role.QL,
            is_final_step=True
        )

    # 3. Payroll Workflow (2-step approval: KT kiểm soát -> QL duyệt chi)
    payroll_wf, _ = ApprovalWorkflowConfig.objects.get_or_create(
        workflow_type=WorkflowType.PAYROLL,
        defaults={'name': 'Quy trình phê duyệt bảng tính lương', 'description': 'Kế toán kiểm tra đối soát, Giám đốc/QL phê duyệt chi lương.'}
    )
    if not payroll_wf.steps.exists():
        ApprovalStepConfig.objects.create(
            workflow=payroll_wf,
            step_number=1,
            name='Kế toán kiểm tra bảng lương & khấu trừ',
            approver_role=Role.KT,
            is_final_step=False
        )
        ApprovalStepConfig.objects.create(
            workflow=payroll_wf,
            step_number=2,
            name='Quản lý / Giám đốc phê duyệt chi lương',
            approver_role=Role.QL,
            is_final_step=True
        )

    # 4. General / Other Workflow
    general_wf, _ = ApprovalWorkflowConfig.objects.get_or_create(
        workflow_type=WorkflowType.GENERAL,
        defaults={'name': 'Quy trình phê duyệt chung', 'description': 'Áp dụng cho các đề xuất và phê duyệt nghiệp vụ khác.'}
    )
    if not general_wf.steps.exists():
        ApprovalStepConfig.objects.create(
            workflow=general_wf,
            step_number=1,
            name='Quản lý xem xét & phê duyệt',
            approver_role=Role.QL,
            is_final_step=True
        )

    return {
        WorkflowType.LEAVE: leave_wf,
        WorkflowType.PURCHASE_REQUEST: scm_wf,
        WorkflowType.PAYROLL: payroll_wf,
        WorkflowType.GENERAL: general_wf,
    }

def get_workflow_for_object(obj, workflow_type=None):
    if not workflow_type:
        ct = ContentType.objects.get_for_model(obj)
        model_name = ct.model.lower()
        if 'leave' in model_name:
            workflow_type = WorkflowType.LEAVE
        elif 'purchaserequest' in model_name:
            workflow_type = WorkflowType.PURCHASE_REQUEST
        elif 'payroll' in model_name:
            workflow_type = WorkflowType.PAYROLL
        else:
            workflow_type = WorkflowType.GENERAL

    ensure_default_workflow_configs()
    wf = ApprovalWorkflowConfig.objects.filter(workflow_type=workflow_type, is_active=True).first()
    if not wf:
        wf = ApprovalWorkflowConfig.objects.filter(workflow_type=workflow_type).first()
    return wf

@transaction.atomic
def submit_for_approval(obj, requester, title='', notes='', workflow_type=None):
    """Submits any model instance to the approval engine."""
    workflow = get_workflow_for_object(obj, workflow_type=workflow_type)
    if not workflow:
        raise ValidationError("Không tìm thấy quy trình phê duyệt phù hợp.")

    ct = ContentType.objects.get_for_model(obj)
    obj_id = str(obj.pk)

    if not title:
        title = f"Yêu cầu phê duyệt {obj}"

    # Close previous pending request if any
    ApprovalRequest.objects.filter(
        content_type=ct,
        object_id=obj_id,
        status=ApprovalStatus.PENDING
    ).update(status=ApprovalStatus.CANCELLED)

    approval_request = ApprovalRequest.objects.create(
        workflow=workflow,
        content_type=ct,
        object_id=obj_id,
        title=title,
        requester=requester,
        current_step=1,
        status=ApprovalStatus.PENDING,
        notes=notes,
        created_by=requester
    )
    return approval_request

@transaction.atomic
def approve_request(approval_request, user, comment=''):
    """Approves the current step of an approval request."""
    if approval_request.status != ApprovalStatus.PENDING:
        raise ValidationError("Yêu cầu này không ở trạng thái chờ phê duyệt.")

    if not approval_request.can_user_approve(user):
        raise ValidationError("Bạn không có quyền phê duyệt ở bước hiện tại.")

    current_step_cfg = approval_request.current_step_config
    ApprovalActionLog.objects.create(
        approval_request=approval_request,
        step_number=approval_request.current_step,
        actor=user,
        action='APPROVE',
        comment=comment,
        created_by=user
    )

    is_final = False
    if current_step_cfg and current_step_cfg.is_final_step:
        is_final = True
    else:
        next_step = approval_request.workflow.steps.filter(
            step_number__gt=approval_request.current_step
        ).order_by('step_number').first()
        if not next_step:
            is_final = True

    if is_final:
        approval_request.status = ApprovalStatus.APPROVED
        approval_request.save()
        _trigger_target_object_callback(approval_request.content_object, approved=True, user=user, comment=comment)
    else:
        approval_request.current_step += 1
        approval_request.save()

    return approval_request

@transaction.atomic
def reject_request(approval_request, user, comment):
    """Rejects an approval request with a required comment."""
    if approval_request.status != ApprovalStatus.PENDING:
        raise ValidationError("Yêu cầu này không ở trạng thái chờ phê duyệt.")

    if not comment or not comment.strip():
        raise ValidationError("Vui lòng nhập lý do từ chối phê duyệt.")

    if not approval_request.can_user_approve(user):
        raise ValidationError("Bạn không có quyền từ chối ở bước này.")

    ApprovalActionLog.objects.create(
        approval_request=approval_request,
        step_number=approval_request.current_step,
        actor=user,
        action='REJECT',
        comment=comment,
        created_by=user
    )

    approval_request.status = ApprovalStatus.REJECTED
    approval_request.save()
    _trigger_target_object_callback(approval_request.content_object, approved=False, user=user, comment=comment)

    return approval_request

def _trigger_target_object_callback(target_obj, approved, user, comment):
    """Invokes lifecycle updates on target domain objects when approvals complete."""
    if not target_obj:
        return

    # 1. PurchaseRequest (SCM)
    if hasattr(target_obj, 'status') and hasattr(target_obj, 'rejection_reason'):
        from scm.models import PurchaseRequestStatus
        if approved:
            target_obj.status = PurchaseRequestStatus.APPROVED
            target_obj.approver = user
            target_obj.approved_at = timezone.now()
        else:
            target_obj.status = PurchaseRequestStatus.REJECTED
            target_obj.approver = user
            target_obj.rejection_reason = comment
        target_obj.save()

    # 2. LeaveRequest (HR)
    elif hasattr(target_obj, 'leave_type') and hasattr(target_obj, 'days_count'):
        if approved:
            target_obj.status = 'APPROVED'
            target_obj.approver = user
            target_obj.approved_at = timezone.now()
            # If annual leave, deduct from LeaveEntitlement
            if target_obj.leave_type == 'ANNUAL':
                entitlement = getattr(target_obj.employee, 'leave_entitlement', None)
                if entitlement:
                    entitlement.used_days += target_obj.days_count
                    entitlement.remaining_days = max(0, entitlement.total_days - entitlement.used_days)
                    entitlement.save()
        else:
            target_obj.status = 'REJECTED'
            target_obj.approver = user
            target_obj.approval_notes = comment
        target_obj.save()

    # 3. PayrollPeriod (HR)
    elif hasattr(target_obj, 'standard_work_days') and hasattr(target_obj, 'total_gross'):
        if approved:
            target_obj.status = 'APPROVED'
        else:
            target_obj.status = 'DRAFT'
            target_obj.notes = f"Bị từ chối duyệt: {comment}"
        target_obj.save()
