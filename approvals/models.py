from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from accounts.models import BaseModel, Role

class WorkflowType(models.TextChoices):
    LEAVE = 'LEAVE', 'Đơn xin nghỉ phép'
    PURCHASE_REQUEST = 'PURCHASE_REQUEST', 'Đề nghị nhập hàng (SCM)'
    PAYROLL = 'PAYROLL', 'Bảng tính lương & Chi lương'
    GENERAL = 'GENERAL', 'Đề nghị & Phê duyệt khác'

class ApprovalStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Nháp'
    PENDING = 'PENDING', 'Chờ phê duyệt'
    APPROVED = 'APPROVED', 'Đã phê duyệt'
    REJECTED = 'REJECTED', 'Từ chối'
    CANCELLED = 'CANCELLED', 'Đã hủy'

class ApprovalWorkflowConfig(BaseModel):
    workflow_type = models.CharField(
        max_length=50,
        choices=WorkflowType.choices,
        unique=True,
        verbose_name="Loại quy trình"
    )
    name = models.CharField(max_length=150, verbose_name="Tên quy trình phê duyệt")
    description = models.TextField(blank=True, verbose_name="Mô tả quy trình")
    is_active = models.BooleanField(default=True, verbose_name="Đang kích hoạt")

    class Meta:
        verbose_name = "Cấu hình quy trình phê duyệt"
        verbose_name_plural = "Cấu hình quy trình phê duyệt"
        ordering = ['workflow_type']

    def __str__(self):
        return f"{self.name} ({self.get_workflow_type_display()})"

class ApprovalStepConfig(BaseModel):
    workflow = models.ForeignKey(
        ApprovalWorkflowConfig,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name="Quy trình"
    )
    step_number = models.PositiveIntegerField(default=1, verbose_name="Thứ tự bước (1, 2, ...)")
    name = models.CharField(max_length=150, verbose_name="Tên bước duyệt")
    approver_role = models.CharField(
        max_length=10,
        choices=Role.choices,
        blank=True,
        verbose_name="Vai trò có quyền duyệt"
    )
    specific_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_approval_steps',
        verbose_name="Hoặc người duyệt cụ thể"
    )
    is_final_step = models.BooleanField(default=False, verbose_name="Là bước duyệt cuối cùng")

    class Meta:
        verbose_name = "Bước phê duyệt"
        verbose_name_plural = "Các bước phê duyệt"
        ordering = ['workflow', 'step_number']
        unique_together = ['workflow', 'step_number']

    def __str__(self):
        return f"{self.workflow.name} - Bước {self.step_number}: {self.name}"

class ApprovalRequest(BaseModel):
    workflow = models.ForeignKey(
        ApprovalWorkflowConfig,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name="Quy trình áp dụng"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=100, verbose_name="ID đối tượng")
    content_object = GenericForeignKey('content_type', 'object_id')

    title = models.CharField(max_length=255, verbose_name="Tiêu đề yêu cầu duyệt")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_approvals',
        verbose_name="Người gửi yêu cầu"
    )
    current_step = models.PositiveIntegerField(default=1, verbose_name="Bước hiện tại")
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name="Trạng thái"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú trình duyệt")

    class Meta:
        verbose_name = "Yêu cầu phê duyệt"
        verbose_name_plural = "Danh sách yêu cầu phê duyệt"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title} (Bước {self.current_step})"

    @property
    def current_step_config(self):
        return self.workflow.steps.filter(step_number=self.current_step).first()

    def can_user_approve(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        step = self.current_step_config
        if not step:
            return False
        if step.specific_approver and step.specific_approver == user:
            return True
        if step.approver_role and getattr(user, 'role', '') == step.approver_role:
            return True
        return False

class ApprovalActionLog(BaseModel):
    approval_request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='action_logs',
        verbose_name="Yêu cầu phê duyệt"
    )
    step_number = models.PositiveIntegerField(default=1, verbose_name="Bước duyệt")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_actions',
        verbose_name="Người thực hiện"
    )
    action = models.CharField(
        max_length=20,
        choices=[('APPROVE', 'Phê duyệt'), ('REJECT', 'Từ chối')],
        verbose_name="Hành động"
    )
    comment = models.TextField(blank=True, verbose_name="Ý kiến phê duyệt / Lý do từ chối")
    action_date = models.DateTimeField(default=timezone.now, verbose_name="Thời gian thực hiện")

    class Meta:
        verbose_name = "Nhật ký phê duyệt"
        verbose_name_plural = "Nhật ký phê duyệt"
        ordering = ['-action_date']

    def __str__(self):
        return f"{self.actor} - {self.get_action_display()} bước {self.step_number}"
