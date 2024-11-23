# dashboard/signals.py

import logging

logger = logging.getLogger(__name__)

from django.db.models.signals import post_save
from django.dispatch import receiver
from backtesting.models import BacktestResult
from dashboard.models import BestPerformingAlgo

@receiver(post_save, sender=BacktestResult)
def update_best_performing_algo(sender, instance, **kwargs):
    logger.debug(f"Signal triggered for BacktestResult ID: {instance.id}")
    if instance.status == 'COMPLETED':
        logger.debug(f"BacktestResult ID {instance.id} is COMPLETED.")
        strategy = instance.strategy
        # Fetch the current best performing strategy
        best_algo = BestPerformingAlgo.objects.order_by('-created_at').first()
        
        logger.debug(f"Current Best Algo Sharpe Ratio: {best_algo.algo_sharpe_ratio if best_algo else 'None'}")
        logger.debug(f"Instance Sharpe Ratio: {instance.algo_sharpe_ratio}")

        # Determine if the current instance is better
        if not best_algo or (instance.algo_sharpe_ratio and instance.algo_sharpe_ratio > best_algo.algo_sharpe_ratio):
            BestPerformingAlgo.objects.update_or_create(
                strategy=strategy,
                defaults={
                    'backtest_result': instance,
                    'algo_return': instance.algo_return,
                    'algo_win_rate': instance.algo_win_rate,
                    'algo_sharpe_ratio': instance.algo_sharpe_ratio,
                }
            )
            logger.debug(f"BestPerformingAlgo updated/created for strategy ID: {strategy.id}")
    else:
        logger.debug(f"BacktestResult ID {instance.id} status is not COMPLETED.")