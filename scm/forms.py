from django import forms
from django.forms import inlineformset_factory
from scm.models import PurchaseRequest, PurchaseRequestDetail
from catalog.models import Product, Supplier

class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú mục đích nhập hàng (kế hoạch kinh doanh, bổ sung tồn kho)...'}),
        }

class PurchaseRequestDetailForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequestDetail
        fields = ['product', 'suggested_supplier', 'requested_quantity', 'estimated_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'suggested_supplier': forms.Select(attrs={'class': 'form-select supplier-select'}),
            'requested_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'estimated_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1000'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(status='ACTIVE')
        self.fields['suggested_supplier'].queryset = Supplier.objects.all()

PurchaseRequestDetailFormSet = inlineformset_factory(
    PurchaseRequest,
    PurchaseRequestDetail,
    form=PurchaseRequestDetailForm,
    extra=1,
    can_delete=True
)

class RequestRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Nhập lý do từ chối phê duyệt đề nghị này (bắt buộc)...'}),
        label="Lý do từ chối"
    )

