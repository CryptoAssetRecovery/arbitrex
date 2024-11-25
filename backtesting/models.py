# backtesting/models.py

from django.db import models
from accounts.models import CustomUser
from strategies.models import Strategy

class BacktestResult(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='backtests')
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='backtests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    result_file = models.FileField(upload_to='backtest_results/', blank=True, null=True)
    log = models.TextField(blank=True, null=True)
    parameters = models.JSONField(default=dict, blank=True, null=True)

    timeframe = models.CharField(
        max_length=3,
        choices=[
            ('1h', '1 Hour'),
            ('4h', '4 Hours'),
            ('1d', '1 Day'),
        ],
        default='4h'
    )

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    commission = models.FloatField(blank=True, null=True)
    slippage = models.FloatField(blank=True, null=True)
    leverage = models.FloatField(blank=True, null=True)
    
    algo_return = models.FloatField(blank=True, null=True)
    algo_win_rate = models.FloatField(blank=True, null=True)
    algo_sharpe_ratio = models.FloatField(blank=True, null=True)

    # Snapshot fields
    strategy_name = models.CharField(max_length=100)
    strategy_description = models.TextField(blank=True, null=True)
    strategy_code = models.TextField()

    # Charting data
    trade_data = models.JSONField(blank=True, null=True)
    ocl_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Backtest {self.id} - {self.strategy_name} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.strategy_name or not self.strategy_code:
            self.strategy_name = self.strategy.name
            self.strategy_description = self.strategy.description
            self.strategy_code = self.strategy.code
                
        super().save(*args, **kwargs)