# dashboard/views.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from backtesting.models import BacktestResult
from dashboard.models import BestPerformingAlgo

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['backtests'] = BacktestResult.objects.filter(user=self.request.user).order_by('-created_at')
        context['best_performances'] = BestPerformingAlgo.objects.order_by('-algo_sharpe_ratio').first()
        return context
