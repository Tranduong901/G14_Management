from django import forms
from crm.models import Lead, Opportunity, CrmActivity, OpportunityStage

class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name', 'phone', 'email', 'company', 'source', 'status', 'assigned_to', 'branch', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Họ và tên khách tiềm năng'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại liên hệ'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Công ty / Đơn vị'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Nhu cầu thiết bị, ngân sách dự kiến...'}),
        }

class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ['name', 'lead', 'customer', 'stage', 'probability', 'expected_revenue', 'expected_close_date', 'assigned_to', 'branch', 'loss_reason', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Dự án cấp 20 iPhone 15 Pro Max cho Công ty X'}),
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'probability': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'expected_revenue': forms.NumberInput(attrs={'class': 'form-control', 'step': '100000'}),
            'expected_close_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'loss_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lý do nếu thất bại (Lost)'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class CrmActivityForm(forms.ModelForm):
    class Meta:
        model = CrmActivity
        fields = ['activity_type', 'subject', 'lead', 'opportunity', 'due_date', 'status', 'assigned_to', 'result']
        widgets = {
            'activity_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Gọi điện tư vấn báo giá iPad Pro'}),
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'opportunity': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'result': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú nội dung trao đổi, kết quả cuộc hẹn...'}),
        }
