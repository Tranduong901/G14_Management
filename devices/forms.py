from django import forms
from devices.models import ProductItem, WarrantyReturn, ItemStatus, WarrantyAction, WarrantyStatus

class ProductItemForm(forms.ModelForm):
    class Meta:
        model = ProductItem
        fields = ['serial_number', 'product', 'status', 'warranty_months', 'warranty_start_date', 'warranty_end_date']
        widgets = {
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 356789123456789'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'warranty_months': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'warranty_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'warranty_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class WarrantyReturnForm(forms.ModelForm):
    class Meta:
        model = WarrantyReturn
        fields = ['item', 'customer', 'issue_description', 'action_type', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'issue_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mô tả chi tiết triệu chứng lỗi của máy...'}),
            'action_type': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú thêm...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only sold items can be selected for warranty
        self.fields['item'].queryset = ProductItem.objects.filter(status=ItemStatus.SOLD)

class WarrantyResolveForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (WarrantyStatus.COMPLETED, 'Hoàn tất xử lý'),
            (WarrantyStatus.REJECTED, 'Từ chối bảo hành (Hết hạn hoặc lỗi người dùng)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Kết luận xử lý"
    )
    replacement_item = forms.ModelChoiceField(
        queryset=ProductItem.objects.filter(status=ItemStatus.IN_STOCK),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Thiết bị đổi mới (Nếu áp dụng Đổi 1-1)",
        help_text="Chỉ hiển thị các thiết bị đang có sẵn trong kho."
    )
    resolution_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Nội dung kiểm tra kỹ thuật / linh kiện thay thế...'}),
        required=False,
        label="Ghi chú kết quả xử lý"
    )

