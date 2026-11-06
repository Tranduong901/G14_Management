from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import BaseModel

class Employee(BaseModel):
    DEPARTMENT_CHOICES = [
        ('BQL', 'Ban quản lý'),
        ('KD', 'Phòng Kinh doanh'),
        ('KHO', 'Bộ phận Kho'),
        ('KT', 'Phòng Kế toán'),
        ('IT', 'Công nghệ thông tin'),
        ('HR', 'Phòng Nhân sự'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Đang làm việc'),
        ('ON_LEAVE', 'Nghỉ phép'),
        ('RESIGNED', 'Đã nghỉ việc'),
    ]

    GENDER_CHOICES = [
        ('M', 'Nam'),
        ('F', 'Nữ'),
        ('O', 'Khác'),
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

    # D1 Expansion: Chi nhánh, Nhân thân, Pháp lý & Ngân hàng
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name="Chi nhánh trực thuộc"
    )
    gender = models.CharField(max_length=5, choices=GENDER_CHOICES, default='M', verbose_name="Giới tính")
    dob = models.DateField(null=True, blank=True, verbose_name="Ngày sinh")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ thường trú")
    id_card_number = models.CharField(max_length=30, blank=True, verbose_name="Số CCCD / CMND")
    id_card_date = models.DateField(null=True, blank=True, verbose_name="Ngày cấp CCCD")
    id_card_place = models.CharField(max_length=150, blank=True, verbose_name="Nơi cấp CCCD")
    tax_code = models.CharField(max_length=30, blank=True, verbose_name="Mã số thuế cá nhân")
    social_insurance_code = models.CharField(max_length=30, blank=True, verbose_name="Mã số sổ BHXH")
    bank_account_number = models.CharField(max_length=50, blank=True, verbose_name="Số tài khoản ngân hàng")
    bank_name = models.CharField(max_length=150, blank=True, verbose_name="Ngân hàng & Chi nhánh")
    dependents_count = models.PositiveIntegerField(default=0, verbose_name="Số người phụ thuộc")

    class Meta:
        verbose_name = "Nhân viên"
        verbose_name_plural = "Danh sách nhân viên"
        ordering = ['code']

    def __str__(self):
        branch_name = f" - {self.branch.name}" if self.branch else ""
        return f"{self.code} - {self.full_name} ({self.get_department_display()}{branch_name})"

    @property
    def active_contract(self):
        return self.contracts.filter(is_active=True).order_by('-start_date').first()

class ContractType(models.TextChoices):
    PROBATION = 'PROBATION', 'Thử việc'
    DEFINITE_1Y = 'DEFINITE_1Y', 'Xác định thời hạn 1 năm'
    DEFINITE_3Y = 'DEFINITE_3Y', 'Xác định thời hạn 3 năm'
    INDEFINITE = 'INDEFINITE', 'Không xác định thời hạn'

class LaborContract(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name="Nhân viên"
    )
    contract_code = models.CharField(max_length=50, unique=True, verbose_name="Mã hợp đồng lao động")
    contract_type = models.CharField(
        max_length=20,
        choices=ContractType.choices,
        default=ContractType.DEFINITE_1Y,
        verbose_name="Loại hợp đồng"
    )
    start_date = models.DateField(verbose_name="Ngày bắt đầu")
    end_date = models.DateField(null=True, blank=True, verbose_name="Ngày kết thúc")
    base_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Lương cơ bản (VNĐ)"
    )
    allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Phụ cấp cố định (VNĐ)"
    )
    insurance_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Mức đóng BHXH (VNĐ)"
    )
    position = models.CharField(max_length=100, verbose_name="Vị trí công việc")
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contracts',
        verbose_name="Chi nhánh làm việc"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang áp dụng")
    notes = models.TextField(blank=True, verbose_name="Ghi chú điều khoản")

    class Meta:
        verbose_name = "Hợp đồng lao động"
        verbose_name_plural = "Danh sách hợp đồng lao động"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.contract_code} - {self.employee.full_name} ({self.get_contract_type_display()})"

class HistoryEventType(models.TextChoices):
    TRANSFER = 'TRANSFER', 'Điều chuyển chi nhánh / bộ phận'
    SALARY_CHANGE = 'SALARY_CHANGE', 'Điều chỉnh / Tăng lương'
    RESIGNATION = 'RESIGNATION', 'Thôi việc / Nghỉ việc'
    PROMOTION = 'PROMOTION', 'Bổ nhiệm / Thăng chức'
    OTHER = 'OTHER', 'Biến động khác'

class EmployeeHistory(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='history_records',
        verbose_name="Nhân viên"
    )
    event_type = models.CharField(
        max_length=30,
        choices=HistoryEventType.choices,
        default=HistoryEventType.TRANSFER,
        verbose_name="Loại biến động"
    )
    event_date = models.DateField(default=timezone.now, verbose_name="Ngày hiệu lực")
    decision_number = models.CharField(max_length=100, blank=True, verbose_name="Số quyết định căn cứ")
    old_value = models.TextField(blank=True, verbose_name="Thông tin cũ")
    new_value = models.TextField(blank=True, verbose_name="Thông tin mới")
    reason = models.TextField(blank=True, verbose_name="Lý do biến động")

    class Meta:
        verbose_name = "Lịch sử biến động nhân sự"
        verbose_name_plural = "Lịch sử biến động nhân sự"
        ordering = ['-event_date', '-created_at']

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_event_type_display()} ({self.event_date})"

# ----------------- D2: Chấm công & Nghỉ phép -----------------

class WorkShift(BaseModel):
    code = models.CharField(max_length=30, unique=True, verbose_name="Mã ca làm việc")
    name = models.CharField(max_length=100, verbose_name="Tên ca")
    start_time = models.TimeField(verbose_name="Giờ bắt đầu")
    end_time = models.TimeField(verbose_name="Giờ kết thúc")
    standard_work_units = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name="Quy đổi công chuẩn (1.0 = 1 công)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang sử dụng")

    class Meta:
        verbose_name = "Ca làm việc"
        verbose_name_plural = "Danh mục ca làm việc"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

class WorkSchedule(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name="Nhân viên"
    )
    date = models.DateField(verbose_name="Ngày làm việc")
    shift = models.ForeignKey(
        WorkShift,
        on_delete=models.PROTECT,
        related_name='schedules',
        verbose_name="Ca làm việc"
    )
    notes = models.CharField(max_length=255, blank=True, verbose_name="Ghi chú phân ca")

    class Meta:
        verbose_name = "Lịch làm việc / Phân ca"
        verbose_name_plural = "Lịch làm việc / Phân ca"
        ordering = ['-date', 'employee']
        unique_together = ['employee', 'date', 'shift']

    def __str__(self):
        return f"{self.employee.full_name} - {self.date}: {self.shift.name}"

class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', 'Đi làm đủ'
    LATE_EARLY = 'LATE_EARLY', 'Đi muộn / Về sớm'
    HALF_DAY = 'HALF_DAY', 'Nửa ngày công'
    ABSENT = 'ABSENT', 'Nghỉ không phép'
    LEAVE_PAID = 'LEAVE_PAID', 'Nghỉ phép hưởng lương'
    LEAVE_UNPAID = 'LEAVE_UNPAID', 'Nghỉ không lương'

class AttendanceRecord(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name="Nhân viên"
    )
    date = models.DateField(verbose_name="Ngày chấm công")
    shift = models.ForeignKey(
        WorkShift,
        on_delete=models.PROTECT,
        related_name='attendance_records',
        verbose_name="Ca làm việc"
    )
    check_in = models.TimeField(null=True, blank=True, verbose_name="Giờ vào")
    check_out = models.TimeField(null=True, blank=True, verbose_name="Giờ ra")
    work_units = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name="Ngày công ghi nhận"
    )
    ot_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Giờ làm thêm (OT)"
    )
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        verbose_name="Trạng thái chấm công"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_attendances',
        verbose_name="Người nhập công"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú")

    class Meta:
        verbose_name = "Bảng chấm công thủ công"
        verbose_name_plural = "Bảng chấm công thủ công"
        ordering = ['-date', 'employee']
        unique_together = ['employee', 'date', 'shift']

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.get_status_display()} - {self.work_units} công)"

class AttendanceAuditLog(BaseModel):
    record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name="Bản ghi chấm công"
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Người chỉnh sửa"
    )
    modified_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian chỉnh sửa")
    reason = models.TextField(verbose_name="Lý do chỉnh sửa chấm công (Bắt buộc)")
    old_values = models.JSONField(default=dict, verbose_name="Dữ liệu trước sửa")
    new_values = models.JSONField(default=dict, verbose_name="Dữ liệu sau sửa")

    class Meta:
        verbose_name = "Nhật ký chỉnh sửa chấm công"
        verbose_name_plural = "Nhật ký chỉnh sửa chấm công"
        ordering = ['-modified_at']

    def __str__(self):
        return f"Sửa công {self.record.employee.full_name} lúc {self.modified_at.strftime('%d/%m/%Y %H:%M')}"

class LeaveEntitlement(BaseModel):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_entitlement',
        verbose_name="Nhân viên"
    )
    year = models.PositiveIntegerField(default=2026, verbose_name="Năm tính phép")
    total_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        verbose_name="Tổng tiêu chuẩn phép năm"
    )
    used_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Số ngày phép đã nghỉ"
    )
    remaining_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        verbose_name="Số ngày phép còn lại"
    )

    class Meta:
        verbose_name = "Quỹ phép năm nhân viên"
        verbose_name_plural = "Quỹ phép năm nhân viên"

    def __str__(self):
        return f"{self.employee.full_name} - Năm {self.year}: Còn {self.remaining_days}/{self.total_days} ngày phép"

class LeaveType(models.TextChoices):
    ANNUAL = 'ANNUAL', 'Nghỉ phép năm (có hưởng lương)'
    SICK = 'SICK', 'Nghỉ ốm đau / BHXH'
    MATERNITY = 'MATERNITY', 'Nghỉ thai sản'
    WEDDING_BEREAVEMENT = 'WEDDING_BEREAVEMENT', 'Nghỉ việc riêng hưởng lương (cưới hỏi, tang chế)'
    UNPAID = 'UNPAID', 'Nghỉ không hưởng lương'

class LeaveStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ phê duyệt'
    APPROVED = 'APPROVED', 'Đã phê duyệt'
    REJECTED = 'REJECTED', 'Từ chối'
    CANCELLED = 'CANCELLED', 'Đã hủy'

class LeaveRequest(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã đơn xin nghỉ")
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests',
        verbose_name="Nhân viên xin nghỉ"
    )
    leave_type = models.CharField(
        max_length=30,
        choices=LeaveType.choices,
        default=LeaveType.ANNUAL,
        verbose_name="Loại nghỉ phép"
    )
    start_date = models.DateField(verbose_name="Từ ngày")
    end_date = models.DateField(verbose_name="Đến ngày")
    days_count = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal('1.0'),
        verbose_name="Số ngày xin nghỉ"
    )
    reason = models.TextField(verbose_name="Lý do xin nghỉ")
    status = models.CharField(
        max_length=20,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
        verbose_name="Trạng thái đơn"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leave_requests',
        verbose_name="Người phê duyệt"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm duyệt")
    approval_notes = models.TextField(blank=True, verbose_name="Ý kiến phê duyệt")

    class Meta:
        verbose_name = "Đơn xin nghỉ phép"
        verbose_name_plural = "Danh sách đơn xin nghỉ phép"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.employee.full_name} ({self.get_leave_type_display()}: {self.days_count} ngày)"

class MonthlyAttendanceSummary(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='monthly_summaries',
        verbose_name="Nhân viên"
    )
    period = models.CharField(max_length=7, verbose_name="Kỳ công (YYYY-MM)")
    standard_days = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal('26.0'),
        verbose_name="Công chuẩn"
    )
    actual_work_days = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Công thực tế đi làm"
    )
    paid_leave_days = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Nghỉ hưởng lương"
    )
    unpaid_leave_days = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Nghỉ không lương"
    )
    ot_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng giờ làm thêm"
    )
    late_early_count = models.PositiveIntegerField(default=0, verbose_name="Số lần đi muộn/về sớm")

    class Meta:
        verbose_name = "Tổng hợp công theo kỳ"
        verbose_name_plural = "Tổng hợp công theo kỳ"
        ordering = ['-period', 'employee']
        unique_together = ['employee', 'period']

    def __str__(self):
        return f"{self.employee.full_name} - Kỳ {self.period}: {self.actual_work_days} công"

# ----------------- D3: Tính lương (Payroll) -----------------

class PayrollPeriodStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Dự thảo'
    PENDING = 'PENDING', 'Chờ phê duyệt'
    APPROVED = 'APPROVED', 'Đã phê duyệt'
    LOCKED = 'LOCKED', 'Đã khóa bảng lương'
    PAID = 'PAID', 'Đã chi trả lương'

class PayrollPeriod(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã kỳ lương")
    name = models.CharField(max_length=150, verbose_name="Tên bảng lương")
    month = models.PositiveIntegerField(verbose_name="Tháng")
    year = models.PositiveIntegerField(verbose_name="Năm")
    standard_work_days = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal('26.0'),
        verbose_name="Số ngày làm việc tiêu chuẩn"
    )
    status = models.CharField(
        max_length=20,
        choices=PayrollPeriodStatus.choices,
        default=PayrollPeriodStatus.DRAFT,
        verbose_name="Trạng thái bảng lương"
    )
    total_gross = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng thu nhập Gross (VNĐ)"
    )
    total_insurance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng bảo hiểm trích nộp (VNĐ)"
    )
    total_tax = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng thuế TNCN (VNĐ)"
    )
    total_net = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng thực lĩnh chi trả (VNĐ)"
    )
    locked_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm khóa")
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_payroll_periods',
        verbose_name="Người khóa sổ"
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm chi trả")
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disbursed_payroll_periods',
        verbose_name="Người thực hiện chi"
    )
    cash_ledger = models.ForeignKey(
        'finance.CashLedger',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_periods',
        verbose_name="Bút toán chi sổ quỹ F08"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú bảng lương")

    class Meta:
        verbose_name = "Bảng tính lương theo kỳ"
        verbose_name_plural = "Danh mục bảng lương theo kỳ"
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.get_status_display()})"

    def recalculate_totals(self):
        items = self.items.all()
        self.total_gross = sum(it.gross_income for it in items)
        self.total_insurance = sum(it.total_insurance for it in items)
        self.total_tax = sum(it.income_tax for it in items)
        self.total_net = sum(it.net_salary for it in items)
        self.save(update_fields=['total_gross', 'total_insurance', 'total_tax', 'total_net'])

class PayrollItem(BaseModel):
    period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Kỳ lương"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='payroll_items',
        verbose_name="Nhân viên"
    )
    contract = models.ForeignKey(
        LaborContract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_items',
        verbose_name="Hợp đồng căn cứ"
    )
    base_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Lương cơ bản HĐ"
    )
    allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Phụ cấp cố định"
    )
    standard_work_days = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal('26.0'),
        verbose_name="Công chuẩn kỳ"
    )
    actual_work_days = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Ngày công thực tế"
    )
    actual_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Lương theo ngày công"
    )
    paid_leave_days = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Ngày nghỉ hưởng lương"
    )
    paid_leave_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Lương ngày nghỉ phép"
    )
    sales_commission = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Thưởng hoa hồng doanh số"
    )
    eligible_sales_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Doanh thu bán thành công trong kỳ"
    )
    ot_pay = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Lương làm thêm giờ"
    )
    gross_income = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng thu nhập (Gross)"
    )

    # Các khoản bảo hiểm bắt buộc theo luật lao động VN
    bhxh_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="BHXH người LĐ nộp (8%)"
    )
    bhyt_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="BHYT người LĐ nộp (1.5%)"
    )
    bhtn_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="BHTN người LĐ nộp (1%)"
    )
    total_insurance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng bảo hiểm trích trừ"
    )

    # Thuế thu nhập cá nhân lũy tiến
    personal_deduction = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('11000000.00'),
        verbose_name="Giảm trừ bản thân (11.000.000 đ)"
    )
    dependent_deduction = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Giảm trừ người phụ thuộc (4.400.000 đ/người)"
    )
    taxable_income = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Thu nhập tính thuế TNCN"
    )
    income_tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Thuế TNCN phải nộp"
    )
    other_deductions = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Các khoản giảm trừ khác"
    )

    # Lương thực lĩnh
    net_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Lương thực lĩnh (Net)"
    )
    status = models.CharField(
        max_length=20,
        choices=[('UNPAID', 'Chưa chi'), ('PAID', 'Đã chi trả')],
        default='UNPAID',
        verbose_name="Trạng thái chi"
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời điểm chi")
    cash_ledger_item = models.ForeignKey(
        'finance.CashLedger',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_items',
        verbose_name="Bút toán chi tương ứng"
    )
    notes = models.TextField(blank=True, verbose_name="Ghi chú phiếu lương")

    class Meta:
        verbose_name = "Phiếu lương nhân viên"
        verbose_name_plural = "Phiếu lương nhân viên"
        ordering = ['period', 'employee']
        unique_together = ['period', 'employee']

    def __str__(self):
        return f"{self.period.code} - {self.employee.full_name}: {self.net_salary:,.0f} đ"
