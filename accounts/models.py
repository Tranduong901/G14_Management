from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class Role(models.TextChoices):
    ADMIN = 'ADMIN', 'Quản trị hệ thống (ADMIN)'
    QL = 'QL', 'Quản lý doanh nghiệp (QL)'
    BH = 'BH', 'Nhân viên bán hàng (BH)'
    KHO = 'KHO', 'Nhân viên kho (KHO)'
    KT = 'KT', 'Kế toán (KT)'
    HR = 'HR', 'Quản trị nhân sự (HR)'

class DataScope(models.TextChoices):
    ALL = 'ALL', 'Toàn hệ thống'
    BRANCH = 'BRANCH', 'Theo chi nhánh'
    PERSONAL = 'PERSONAL', 'Cá nhân'

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

class Branch(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã chi nhánh")
    name = models.CharField(max_length=150, verbose_name="Tên chi nhánh")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")

    class Meta:
        verbose_name = "Chi nhánh"
        verbose_name_plural = "Danh mục chi nhánh"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

class User(AbstractUser):
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.BH,
        verbose_name="Vai trò"
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Chi nhánh làm việc"
    )
    data_scope = models.CharField(
        max_length=20,
        choices=DataScope.choices,
        default=DataScope.ALL,
        verbose_name="Phạm vi dữ liệu"
    )
    can_view_payroll = models.BooleanField(
        default=False,
        verbose_name="Quyền xem thông tin lương",
        help_text="Cấp quyền xem bảng lương và phiếu lương cho Admin/Nhân sự cụ thể."
    )

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

    @property
    def is_hr(self):
        return self.role == Role.HR or self.is_admin

    def can_access_branch(self, branch):
        if self.is_superuser or self.data_scope == DataScope.ALL:
            return True
        if not branch:
            return True
        branch_id = getattr(branch, 'id', branch)
        return self.branch_id == branch_id

