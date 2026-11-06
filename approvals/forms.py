from django import forms
from approvals.models import ApprovalWorkflowConfig, ApprovalStepConfig
from accounts.models import Role

class ApprovalWorkflowConfigForm(forms.ModelForm):
    class Meta:
        model = ApprovalWorkflowConfig
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ApprovalStepConfigForm(forms.ModelForm):
    class Meta:
        model = ApprovalStepConfig
        fields = ['step_number', 'name', 'approver_role', 'specific_approver', 'is_final_step']
        widgets = {
            'step_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'approver_role': forms.Select(attrs={'class': 'form-select'}),
            'specific_approver': forms.Select(attrs={'class': 'form-select'}),
            'is_final_step': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ApprovalDecisionForm(forms.Form):
    action = forms.ChoiceField(
        choices=[('APPROVE', 'Đồng ý phê duyệt'), ('REJECT', 'Từ chối phê duyệt')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Nhập ý kiến phê duyệt hoặc bắt buộc nhập lý do nếu từ chối...'
        }),
        label="Ý kiến / Lý do"
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        comment = cleaned_data.get('comment', '').strip()
        if action == 'REJECT' and not comment:
            self.add_error('comment', 'Vui lòng nhập lý do từ chối phê duyệt.')
        return cleaned_data
