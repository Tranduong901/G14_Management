from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import BaseModel

class LeadSource(models.TextChoices):
    WEBSITE = 'WEBSITE', 'Website / Trực tuyến'
    REFERRAL = 'REFERRAL', 'Khách hàng giới thiệu'
    EXHIBITION = 'EXHIBITION', 'Hội thảo / Sự kiện'
    HOTLINE = 'HOTLINE', 'Hotline / Tư vấn tổng đài'
    DIRECT = 'DIRECT', 'Trực tiếp tại showroom'
    OTHER = 'OTHER', 'Nguồn khác'

class LeadStatus(models.TextChoices):
    NEW = 'NEW', 'Mới tiếp nhận'
    CONTACTED = 'CONTACTED', 'Đang liên hệ tư vấn'
    QUALIFIED = 'QUALIFIED', 'Tiềm năng xác thực'
    CONVERTED = 'CONVERTED', 'Đã chuyển đổi thành khách hàng'
    LOST = 'LOST', 'Không có nhu cầu / Thất bại'

class Lead(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã Lead")
    name = models.CharField(max_length=150, verbose_name="Họ tên khách tiềm năng")
    phone = models.CharField(max_length=20, verbose_name="Số điện thoại")
    email = models.EmailField(blank=True, verbose_name="Email")
    company = models.CharField(max_length=150, blank=True, verbose_name="Công ty / Đơn vị")
    source = models.CharField(
        max_length=20,
        choices=LeadSource.choices,
        default=LeadSource.HOTLINE,
        verbose_name="Nguồn tiếp cận"
    )
    status = models.CharField(
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW,
        verbose_name="Trạng thái Lead"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        verbose_name="Nhân viên phụ trách"
    )
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
        verbose_name="Chi nhánh"
    )
    converted_customer = models.ForeignKey(
        'catalog.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='converted_leads',
        verbose_name="Khách hàng đã tạo"
    )
    notes = models.TextField(blank=True, verbose_name="Nhu cầu / Ghi chú")

    class Meta:
        verbose_name = "Khách hàng tiềm năng (Lead)"
        verbose_name_plural = "Danh mục Lead (CRM)"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.code}] {self.name} - {self.phone} ({self.get_status_display()})"

class OpportunityStage(models.TextChoices):
    PROSPECTING = 'PROSPECTING', 'Tìm hiểu nhu cầu'
    QUALIFICATION = 'QUALIFICATION', 'Khảo sát / Đánh giá'
    PROPOSAL = 'PROPOSAL', 'Gửi báo giá / Đề xuất'
    NEGOTIATION = 'NEGOTIATION', 'Thương thảo hợp đồng'
    CLOSED_WON = 'CLOSED_WON', 'Thành công (Won)'
    CLOSED_LOST = 'CLOSED_LOST', 'Thất bại (Lost)'

class Opportunity(BaseModel):
    STAGE_PROBABILITY = {
        OpportunityStage.PROSPECTING: 10,
        OpportunityStage.QUALIFICATION: 30,
        OpportunityStage.PROPOSAL: 60,
        OpportunityStage.NEGOTIATION: 80,
        OpportunityStage.CLOSED_WON: 100,
        OpportunityStage.CLOSED_LOST: 0,
    }

    code = models.CharField(max_length=50, unique=True, verbose_name="Mã cơ hội")
    name = models.CharField(max_length=200, verbose_name="Tên cơ hội bán hàng")
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities',
        verbose_name="Lead liên quan"
    )
    customer = models.ForeignKey(
        'catalog.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities',
        verbose_name="Khách hàng (F04)"
    )
    stage = models.CharField(
        max_length=30,
        choices=OpportunityStage.choices,
        default=OpportunityStage.PROSPECTING,
        verbose_name="Giai đoạn bán hàng"
    )
    probability = models.PositiveIntegerField(
        default=10,
        verbose_name="Xác suất thành công (%)"
    )
    expected_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Giá trị kỳ vọng (VNĐ)"
    )
    expected_close_date = models.DateField(null=True, blank=True, verbose_name="Ngày dự kiến chốt")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_opportunities',
        verbose_name="Chuyên viên phụ trách"
    )
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities',
        verbose_name="Chi nhánh"
    )
    converted_order = models.ForeignKey(
        'sales.SalesOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='origin_opportunities',
        verbose_name="Đơn bán hàng F04 sinh ra"
    )
    loss_reason = models.TextField(blank=True, verbose_name="Lý do thất bại nếu Lost")
    notes = models.TextField(blank=True, verbose_name="Ghi chú cơ hội")

    class Meta:
        verbose_name = "Cơ hội bán hàng (Opportunity)"
        verbose_name_plural = "Danh sách cơ hội bán hàng"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.code}] {self.name} - {self.expected_revenue:,.0f} đ ({self.get_stage_display()})"

    def save(self, *args, **kwargs):
        # Update default probability if not explicitly provided or on stage change
        if self.stage in self.STAGE_PROBABILITY:
            if not self.probability or self.probability == 10:
                self.probability = self.STAGE_PROBABILITY[self.stage]
        super().save(*args, **kwargs)

class ActivityType(models.TextChoices):
    CALL = 'CALL', 'Cuộc gọi điện'
    MEETING = 'MEETING', 'Gặp mặt trực tiếp'
    QUOTE = 'QUOTE', 'Gửi bảng báo giá'
    TASK = 'TASK', 'Nhắc việc / Nhiệm vụ'
    EMAIL = 'EMAIL', 'Gửi email trao đổi'

class ActivityStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ thực hiện'
    COMPLETED = 'COMPLETED', 'Đã hoàn thành'
    CANCELLED = 'CANCELLED', 'Đã hủy'

class CrmActivity(BaseModel):
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.CALL,
        verbose_name="Loại hoạt động"
    )
    subject = models.CharField(max_length=200, verbose_name="Tiêu đề hoạt động")
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Lead liên quan"
    )
    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name="Cơ hội liên quan"
    )
    due_date = models.DateTimeField(default=timezone.now, verbose_name="Thời gian thực hiện")
    status = models.CharField(
        max_length=20,
        choices=ActivityStatus.choices,
        default=ActivityStatus.PENDING,
        verbose_name="Trạng thái"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crm_activities',
        verbose_name="Người thực hiện"
    )
    result = models.TextField(blank=True, verbose_name="Kết quả trao đổi / Diễn giải")

    class Meta:
        verbose_name = "Hoạt động chăm sóc (CRM)"
        verbose_name_plural = "Lịch sử hoạt động chăm sóc"
        ordering = ['-due_date']

    def __str__(self):
        return f"[{self.get_activity_type_display()}] {self.subject} ({self.get_status_display()})"
