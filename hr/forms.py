from django import forms
from hr.models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['code', 'full_name', 'department', 'position', 'phone', 'email', 'status', 'join_date', 'user']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: NV001'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ và tên'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Chuyên viên tư vấn'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 0987654321'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'VD: employee@g14.vn'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'join_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
        }

