from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'Đăng nhập'),
        ('LOGOUT', 'Đăng xuất'),
        ('CREATE', 'Tạo mới'),
        ('UPDATE', 'Cập nhật'),
        ('DELETE', 'Xóa'),
        ('COMPLETE', 'Hoàn tất giao dịch'),
        ('CANCEL', 'Hủy giao dịch'),
        ('APPROVE', 'Phê duyệt'),
        ('REJECT', 'Từ chối'),
        ('ADJUST', 'Điều chỉnh kho'),
        ('PAYMENT', 'Ghi nhận thanh toán'),
        ('REVERSE', 'Bút toán đảo'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Người thực hiện"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Hành động")
    app_label = models.CharField(max_length=50, blank=True, verbose_name="Phân hệ")
    model_name = models.CharField(max_length=50, blank=True, verbose_name="Bảng dữ liệu")
    object_id = models.CharField(max_length=100, blank=True, verbose_name="ID đối tượng")
    object_repr = models.CharField(max_length=255, verbose_name="Đối tượng tác động")
    changes_json = models.JSONField(default=dict, blank=True, verbose_name="Chi tiết thay đổi")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Địa chỉ IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm ghi nhận")

    class Meta:
        verbose_name = "Nhật ký hệ thống"
        verbose_name_plural = "Danh sách nhật ký hệ thống"
        ordering = ['-created_at']

    def __str__(self):
        user_name = self.user.username if self.user else "Hệ thống"
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {user_name} - {self.get_action_display()} - {self.object_repr}"


class AccessDeniedLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_denied_logs',
    )
    role = models.CharField(max_length=20, blank=True)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
