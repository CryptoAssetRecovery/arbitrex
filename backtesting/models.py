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
    parameters = models.JSONField(default=dict, blank=True)
    
    algo_return = models.FloatField(blank=True, null=True)
    algo_win_rate = models.FloatField(blank=True, null=True)
    algo_sharpe_ratio = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Backtest {self.id} - {self.strategy.name} - {self.status}"