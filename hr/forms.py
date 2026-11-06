from django import forms
from hr.models import (
    Employee,
    LaborContract,
    WorkShift,
    AttendanceRecord,
    LeaveRequest,
    PayrollPeriod,
)

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'code', 'full_name', 'department', 'position', 'branch',
            'phone', 'email', 'status', 'join_date', 'user',
            'gender', 'dob', 'address',
            'id_card_number', 'id_card_date', 'id_card_place',
            'tax_code', 'social_insurance_code',
            'bank_account_number', 'bank_name', 'dependents_count'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: NV001'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ và tên'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Chuyên viên tư vấn'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 0987654321'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'VD: employee@g14.vn'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'join_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Địa chỉ thường trú / tạm trú'}),
            'id_card_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số CCCD'}),
            'id_card_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'id_card_place': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nơi cấp CCCD'}),
            'tax_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mã số thuế'}),
            'social_insurance_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mã sổ BHXH'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số tài khoản'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Vietcombank - CN Hà Nội'}),
            'dependents_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

class LaborContractForm(forms.ModelForm):
    class Meta:
        model = LaborContract
        fields = [
            'employee', 'contract_type', 'start_date', 'end_date',
            'base_salary', 'allowance', 'insurance_salary',
            'position', 'branch', 'is_active', 'notes'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'contract_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '100000'}),
            'allowance': forms.NumberInput(attrs={'class': 'form-control', 'step': '50000'}),
            'insurance_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '100000'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class WorkShiftForm(forms.ModelForm):
    class Meta:
        model = WorkShift
        fields = ['code', 'name', 'start_time', 'end_time', 'standard_work_units', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'standard_work_units': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AttendanceManualEntryForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['employee', 'date', 'shift', 'work_units', 'check_in', 'check_out', 'status', 'ot_hours', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'shift': forms.Select(attrs={'class': 'form-select'}),
            'work_units': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'ot_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ghi chú'}),
        }

class AttendanceEditForm(forms.Form):
    work_units = forms.DecimalField(
        max_digits=4, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
        label="Ngày công"
    )
    status = forms.ChoiceField(
        choices=AttendanceRecord._meta.get_field('status').choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Trạng thái"
    )
    check_in = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Giờ vào"
    )
    check_out = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Giờ ra"
    )
    ot_hours = forms.DecimalField(
        max_digits=4, decimal_places=2, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        label="Giờ làm thêm (OT)"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Ghi chú"
    )
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Bắt buộc nhập lý do chỉnh sửa chấm công...'}),
        label="Lý do chỉnh sửa chấm công (Bắt buộc)"
    )

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'days_count', 'reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'days_count': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0.5'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Nhập lý do xin nghỉ phép...'}),
        }

class PayrollPeriodForm(forms.ModelForm):
    class Meta:
        model = PayrollPeriod
        fields = ['month', 'year', 'standard_work_days', 'notes']
        widgets = {
            'month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2050}),
            'standard_work_days': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú bảng lương'}),
        }
