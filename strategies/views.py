# strategies/views.py

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.core.cache import cache
import uuid

from backtesting.models import BacktestResult
from .utils import chat_with_openai, chat_with_anthropic, load_strategies_and_inject_log
from .models import Strategy
from .forms import StrategyForm
from .backtrader_docks import BACKTRADER_DOCS

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
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    session_key = f"chat_lock_{request.user.id}"
    
    # Try to acquire a lock with a timeout
    if not cache.add(session_key, request_id, timeout=30):  # 30 seconds timeout
        return JsonResponse({
            'success': False,
            'error': "Another chat request is in progress. Please wait."
        }, status=429)  # 429 Too Many Requests

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

        # Load the backtesting code
        with open('backtesting/tasks.py', 'r') as file:
            backtesting_code = file.read()

        # Define static system messages
        static_system_messages = [
            {"role": "system", "content": f"<SYSTEM_MESSAGE>Docs for the backtrader library and some examples:\n\n{BACKTRADER_DOCS}</SYSTEM_MESSAGE>"},
            {"role": "system", "content": f"<SYSTEM_MESSAGE>Current backtesting code. The user **cannot** modify the backtesting code. Make sure that the strategy code is compatible with the backtesting code:\n\n```python\n{backtesting_code}\n```</SYSTEM_MESSAGE>"}
        ]

        # Check if static system messages are already present
        static_present = all(
            any(
                msg.get('content') == system_msg.get('content') 
                for msg in messages 
            ) 
            for system_msg in static_system_messages
        )

        if not static_present:
            # Prepend static system messages once
            messages = static_system_messages + messages

        # Define dynamic system message with the current strategy code
        dynamic_system_message = {
            "role": "system",
            "content": f"<SYSTEM_MESSAGE>Current trading strategy code:\n\n```python\n{code}\n```\nOnly assist the user with the custom backtrader code - do not provide any other information pertaining to the main, or other parts of the code.</SYSTEM_MESSAGE>"
        }

        # Prepend dynamic system message every time
        messages = [dynamic_system_message] + messages

        # Append the backtest results if the user checked the checkbox
        if include_last_backtest_logs and last_backtest_id != 'null':
            last_backtest = BacktestResult.objects.filter(id=int(last_backtest_id)).first()
            if last_backtest:
                backtest_log = last_backtest.log[-1000:] if len(last_backtest.log) > 1000 else last_backtest.log
                # Find the last user message
                for i in range(len(messages)-1, -1, -1):
                    if messages[i].get('role') == 'user':
                        # Insert backtest results before the last user message
                        messages.insert(i, {"role": "system", "content": f"<SYSTEM_MESSAGE>Here is the backtest results from backtest {last_backtest.id}:\n\n```python\n{backtest_log}\n```</SYSTEM_MESSAGE>"})
                        break

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
    finally:
        # Release the lock if we still own it
        if cache.get(session_key) == request_id:
            cache.delete(session_key)

class StrategyListView(LoginRequiredMixin, ListView):
    model = Strategy
    template_name = 'strategies/strategy_list.html'
    context_object_name = 'strategies'

    def get_queryset(self):
        #return Strategy.objects.filter(user=self.request.user).order_by('-created_at')
        return Strategy.objects.all().order_by('-created_at') # Temporary for ease of use - TODO: add "publish" feature

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
        # Add a check for the parameters field
        def capture_log():
            pass
        
        strategy_class = load_strategies_and_inject_log(form.instance.code, capture_log)
        if not hasattr(strategy_class, 'params'):
            messages.warning(self.request, "Warning: This strategy has no parameters.")
        
        form.instance.user = self.request.user
        messages.success(self.request, 'Strategy created successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        # Add all form errors to messages
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(self.request, error)
                else:
                    messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

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
    
    def form_valid(self, form):
        # Add a check for the parameters field
        def capture_log():
            pass
        
        strategy_class = load_strategies_and_inject_log(form.instance.code, capture_log)
        if not hasattr(strategy_class, 'params'):
            print("No params")
            messages.warning(self.request, "Warning: This strategy has no parameters.")
        else:
            params = strategy_class.params._getpairs()
            if not params:
                messages.warning(self.request, "Warning: This strategy has no parameters defined.")
            else:
                messages.success(self.request, 'Strategy updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Add all form errors to messages
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(self.request, error)
                else:
                    messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

class StrategyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Strategy
    template_name = 'strategies/strategy_confirm_delete.html'
    success_url = reverse_lazy('strategy_list')

    def test_func(self):
        strategy = self.get_object()
        return self.request.user == strategy.user