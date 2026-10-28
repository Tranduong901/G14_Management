from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class Role(models.TextChoices):
    ADMIN = 'ADMIN', 'Quản trị hệ thống (ADMIN)'
    QL = 'QL', 'Quản lý doanh nghiệp (QL)'
    BH = 'BH', 'Nhân viên bán hàng (BH)'
    KHO = 'KHO', 'Nhân viên kho (KHO)'
    KT = 'KT', 'Kế toán (KT)'

class BaseModel(models.Model):
    """Abstract base model with timestamps and audit trail fields."""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Thời gian cập nhật")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name="Người tạo"
    )

    class Meta:
        abstract = True

class User(AbstractUser):
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.BH,
        verbose_name="Vai trò"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")

    class Meta:
        verbose_name = "Tài khoản người dùng"
        verbose_name_plural = "Danh sách tài khoản"
        ordering = ['-date_joined']

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{self.username} - {full_name} ({self.get_role_display()})"
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_ql(self):
        return self.role == Role.QL or self.is_admin

    @property
    def is_bh(self):
        return self.role == Role.BH or self.is_admin

    @property
    def is_kho(self):
        return self.role == Role.KHO or self.is_admin

    @property
    def is_kt(self):
        return self.role == Role.KT or self.is_admin

