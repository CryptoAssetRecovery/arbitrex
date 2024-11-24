# strategies/views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from backtesting.models import BacktestResult
from .models import Strategy
from .forms import StrategyForm

import openai
import os
from dotenv import load_dotenv
import json
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

@csrf_protect
@require_POST
def chat_with_ai(request):
    try:
        messages = request.POST.get('message_history')
        code = request.POST.get('code')

        # Convert messages to a list of dictionaries
        messages = json.loads(messages)

        # Get a copy of the backtesting logic in tasks.py
        with open('backtesting/tasks.py', 'r') as file:
            backtesting_code = file.read()

        # Add the users code to the most recent user message
        system_messages = [{"role": "system", "content": f"Here is the current trading strategy code:\n\n```python\n{code}\n```Only assist the user with the custom backtrader code - do not provide any other information pertaining to the main, or other parts of the code."}]
        system_messages.append({"role": "system", "content": f"Here is the current backtesting code. The user **cannot** modify the backtesting code. Make sure that the strategy code is compatible with the backtesting code:\n\n```python\n{backtesting_code}\n```"})

        # Add the system messages to the list
        messages = system_messages + messages

        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o", 
            messages=messages,
        )

        # Remove the system messages from the response
        response_content = response.choices[0].message.content
        for system_message in system_messages:
            response_content = response_content.replace(system_message["content"], "")
        
        return JsonResponse({
            'success': True,
            'response': response_content
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

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

        best_backtest = BacktestResult.objects.filter(strategy=self.object).order_by('-algo_sharpe_ratio').first()

        best_sharpe_ratio = best_backtest.algo_sharpe_ratio if best_backtest else None
        best_win_rate = best_backtest.algo_win_rate if best_backtest else None
        best_return = best_backtest.algo_return if best_backtest else None

        context['best_sharpe_ratio'] = best_sharpe_ratio
        context['best_win_rate'] = best_win_rate
        context['best_return'] = best_return

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