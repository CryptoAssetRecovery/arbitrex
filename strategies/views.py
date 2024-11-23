# strategies/views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from backtesting.models import BacktestResult
from .models import Strategy
from .forms import StrategyForm
from dashboard.models import BestPerformingAlgo

class StrategyListView(LoginRequiredMixin, ListView):
    model = Strategy
    template_name = 'strategies/strategy_list.html'
    context_object_name = 'strategies'

    def get_queryset(self):
        return Strategy.objects.filter(user=self.request.user).order_by('-created_at')

class StrategyDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Strategy
    template_name = 'strategies/strategy_detail.html'

    def test_func(self):
        strategy = self.get_object()
        return self.request.user == strategy.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['backtests'] = BacktestResult.objects.filter(strategy=self.object).order_by('-created_at')

        best_sharpe_ratio = BacktestResult.objects.filter(strategy=self.object).order_by('-algo_sharpe_ratio').first()
        best_win_rate = BacktestResult.objects.filter(strategy=self.object).order_by('-algo_win_rate').first()
        best_return = BacktestResult.objects.filter(strategy=self.object).order_by('-algo_return').first()

        context['best_sharpe_ratio'] = best_sharpe_ratio.algo_sharpe_ratio
        context['best_win_rate'] = best_win_rate.algo_win_rate
        context['best_return'] = best_return.algo_return

        return context

class StrategyCreateView(LoginRequiredMixin, CreateView):
    model = Strategy
    form_class = StrategyForm
    template_name = 'strategies/strategy_form.html'
    success_url = reverse_lazy('strategy_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class StrategyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Strategy
    form_class = StrategyForm
    template_name = 'strategies/strategy_form.html'
    success_url = reverse_lazy('strategy_list')

    def test_func(self):
        strategy = self.get_object()
        return self.request.user == strategy.user

class StrategyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Strategy
    template_name = 'strategies/strategy_confirm_delete.html'
    success_url = reverse_lazy('strategy_list')

    def test_func(self):
        strategy = self.get_object()
        return self.request.user == strategy.user