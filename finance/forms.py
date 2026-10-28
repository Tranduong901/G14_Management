from django import forms
from decimal import Decimal
from finance.models import CashLedger, Payable, PayablePayment, LedgerType, PaymentMethod

class PayablePaymentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1000', 'min': '1000'}),
        label="Số tiền thanh toán (VNĐ)"
    )
    payment_method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Hình thức thanh toán"
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú chứng từ ủy nhiệm chi / chuyển khoản...'}),
        required=False,
        label="Ghi chú chi tiền"
    )

class OtherLedgerForm(forms.Form):
    transaction_type = forms.ChoiceField(
        choices=LedgerType.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Loại giao dịch"
    )
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1000', 'min': '1000'}),
        label="Số tiền (VNĐ)"
    )
    payment_method = forms.ChoiceField(
        choices=PaymentMethod.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Hình thức thanh toán"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghi rõ lý do thu hoặc chi (bắt buộc theo BR17)...'}),
        label="Lý do thu / chi"
    )

class ReversalForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ghi rõ lý do lập bút toán đảo điều chỉnh (bắt buộc)...'}),
        label="Lý do lập bút toán đảo"
    )

