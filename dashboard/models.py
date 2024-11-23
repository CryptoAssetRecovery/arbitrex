# dashboard/models.py

from django.db import models
from django.utils import timezone

from backtesting.models import BacktestResult
from strategies.models import Strategy

class BestPerformingAlgo(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name='best_performances')
    backtest_result = models.ForeignKey(BacktestResult, on_delete=models.CASCADE, related_name='best_performances', default=None, null=True, blank=True)

    algo_return = models.FloatField()
    algo_win_rate = models.FloatField()
    algo_sharpe_ratio = models.FloatField()

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Best Algo for {self.strategy.name} - Sharpe Ratio: {self.algo_sharpe_ratio}"