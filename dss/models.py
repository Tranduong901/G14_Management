from django.db import models
from accounts.models import BaseModel

class ForecastResult(BaseModel):
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='forecast_results',
        verbose_name="Sản phẩm"
    )
    forecast_period = models.CharField(
        max_length=20,
        verbose_name="Kỳ dự báo (VD: 2026-11)"
    )
    method = models.CharField(
        max_length=50,
        default='SMA_3M',
        verbose_name="Phương pháp dự báo"
    )
    forecasted_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Số lượng dự báo"
    )
    actual_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Số lượng bán thực tế"
    )
    error_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Độ lệch dự báo (%) (TC28)"
    )
    calculated_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm tính toán")

    class Meta:
        verbose_name = "Kết quả dự báo nhu cầu"
        verbose_name_plural = "Dữ liệu dự báo nhu cầu (DSS)"
        ordering = ['-forecast_period', 'product__code']

    def __str__(self):
        return f"{self.product.name} ({self.forecast_period}): Dự báo {self.forecasted_quantity}"

