from django.db import models
from django.conf import settings
from accounts.models import BaseModel

class Employee(BaseModel):
    DEPARTMENT_CHOICES = [
        ('BQL', 'Ban quản lý'),
        ('KD', 'Phòng Kinh doanh'),
        ('KHO', 'Bộ phận Kho'),
        ('KT', 'Phòng Kế toán'),
        ('IT', 'Công nghệ thông tin'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Đang làm việc'),
        ('ON_LEAVE', 'Nghỉ phép'),
        ('RESIGNED', 'Đã nghỉ việc'),
    ]

    code = models.CharField(max_length=20, unique=True, verbose_name="Mã nhân viên")
    full_name = models.CharField(max_length=150, verbose_name="Họ và tên")
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES, default='KD', verbose_name="Phòng ban")
    position = models.CharField(max_length=100, verbose_name="Chức danh / Vị trí")
    phone = models.CharField(max_length=20, verbose_name="Số điện thoại")
    email = models.EmailField(blank=True, verbose_name="Email")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name="Trạng thái")
    join_date = models.DateField(null=True, blank=True, verbose_name="Ngày vào làm")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile',
        verbose_name="Tài khoản hệ thống liên kết"
    )

    class Meta:
        verbose_name = "Nhân viên"
        verbose_name_plural = "Danh sách nhân viên"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.full_name} ({self.get_department_display()})"

