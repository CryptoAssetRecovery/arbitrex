# strategies/views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from backtesting.models import BacktestResult
from .utils import chat_with_openai, chat_with_anthropic
from .models import Strategy
from .forms import StrategyForm

from dotenv import load_dotenv
import openai
import anthropic
import os
import json

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
anthropic.api_key = os.getenv("ANTHROPIC_API_KEY")


MODEL_MAP = settings.MODEL_MAP

# Create a reverse mapping from model to provider for easy lookup
MODEL_TO_PROVIDER = {model: provider for provider, models in MODEL_MAP.items() for model in models}

@csrf_protect
@require_POST
def chat_with_ai(request):
    try:
        # Get the chat messages and LLM model
        messages = request.POST.get('message_history')
        llm_model = request.POST.get('llm_model')

        # Get the strategy code
        code = request.POST.get('code')        

        # Get the backtest parameters
        include_last_backtest_logs = request.POST.get('include_last_backtest_logs')
        last_backtest_id = request.POST.get('last_backtest_id')

        # Validate model
        if llm_model not in MODEL_TO_PROVIDER:
            return JsonResponse({
                'success': False,
                'error': f"Invalid model selected: {llm_model}"
            }, status=400)
        
        # Get the LLM provider
        llm_provider = MODEL_TO_PROVIDER[llm_model]

        # Convert messages to a list of dictionaries
        messages = json.loads(messages)

        # Get the backtesting code
        with open('backtesting/tasks.py', 'r') as file:
            backtesting_code = file.read()

        # Add the user's code to the most recent user message
        system_messages = [
            {"role": "system", "content": f"Here is the current trading strategy code:\n\n```python\n{code}\n```Only assist the user with the custom backtrader code - do not provide any other information pertaining to the main, or other parts of the code."},
            {"role": "system", "content": f"Here is the current backtesting code. The user **cannot** modify the backtesting code. Make sure that the strategy code is compatible with the backtesting code:\n\n```python\n{backtesting_code}\n```"}
        ]

        # Append the backtest results if the user checked the checkbox
        if include_last_backtest_logs:
            last_backtest = BacktestResult.objects.filter(id=last_backtest_id).first()
            if last_backtest:
                backtest_log = last_backtest.log[-1000:] if len(last_backtest.log) > 1000 else last_backtest.log
                print(backtest_log)
                system_messages.append({"role": "system", "content": f"Here is the backtest results from backtest {last_backtest.id}:\n\n```python\n{backtest_log}\n```"})

        # Add the system messages to the list
        messages = system_messages + messages

        # Call the appropriate chat function based on provider
        if llm_provider == "openai":
            response_content = chat_with_openai(messages, model=llm_model)
        elif llm_provider == "anthropic":
            response_content = chat_with_anthropic(messages, model=llm_model)
        else:
            return JsonResponse({
                'success': False,
                'error': f"Unsupported provider: {llm_provider}"
            }, status=400)

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

        best_backtest = BacktestResult.objects.filter(strategy=self.object, algo_sharpe_ratio__isnull=False).order_by('-algo_sharpe_ratio').first()

        best_sharpe_ratio = best_backtest.algo_sharpe_ratio if best_backtest else None
        best_win_rate = best_backtest.algo_win_rate if best_backtest else None
        best_return = best_backtest.algo_return if best_backtest else None

        print(best_sharpe_ratio)
        print(best_win_rate)
        print(best_return)
        print(best_backtest)

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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['last_backtest'] = BacktestResult.objects.filter(strategy=self.object).order_by('-created_at').first() if BacktestResult.objects.filter(strategy=self.object).exists() else None
        return context

class StrategyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Strategy
    template_name = 'strategies/strategy_confirm_delete.html'
    success_url = reverse_lazy('strategy_list')

    def test_func(self):
        strategy = self.get_object()
        return self.request.user == strategy.user