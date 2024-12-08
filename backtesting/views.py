# backtesting/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import BacktestResult
from .tasks import run_backtest
from .forms import BacktestForm
from .utils import update_strategy_params_in_code
from strategies.models import Strategy
from strategies.utils import load_strategies_and_inject_log

@login_required
def dashboard(request):
    if request.method == 'POST':
        form = BacktestForm(request.POST)
        if form.is_valid():
            strategy = form.cleaned_data['strategy']
            parameters = form.cleaned_data.get('parameters') or {}
            print(parameters)
            backtest = BacktestResult.objects.create(
                user=request.user,
                strategy=strategy,
                status='PENDING',
                parameters=parameters,
                commission=form.cleaned_data.get('commission'),
                slippage=form.cleaned_data.get('slippage'),
                ocl_data_import=form.cleaned_data.get('ocl_data_import')
            )

            original_code = strategy.code
            updated_code = update_strategy_params_in_code(original_code, parameters)

            backtest.strategy_code = updated_code
            backtest.save()

            run_backtest.delay(backtest.id)
            return redirect('backtesting:backtest_result', backtest_id=backtest.id)
        else:
            messages.error(request, f"Form is not valid: {form.errors}")
    else:
        form = BacktestForm()
    return render(request, 'backtesting/index.html', {'form': form})

@login_required
def strategy_parameters(request, strategy_id):
    strategy = get_object_or_404(Strategy, id=strategy_id)
    if not strategy:
        return JsonResponse({"error": "Strategy not found"}, status=404)
    
    def capture_log():
        pass

    strategy_class = load_strategies_and_inject_log(strategy.code, capture_log)
    
    # Return a warning if the strategy has no parameters
    if not hasattr(strategy_class, 'params'):
        return JsonResponse({"warning": "This strategy has no parameters"}, safe=False)
    
    # Convert params to a serializable dictionary
    params_dict = dict(strategy_class.params._getpairs())
    
    return JsonResponse({"parameters": params_dict}, safe=False)

@login_required
def backtest_chart_data(request, backtest_id):
    backtest = get_object_or_404(BacktestResult, id=backtest_id, user=request.user)
    
    return JsonResponse({
        "priceData": backtest.ocl_data,
        "portfolioValues": backtest.portfolio_values,
        "tradeData": backtest.trade_data,
        "orderData": backtest.order_data
    }, safe=False)

@login_required
def backtest_result(request, backtest_id):
    backtest = get_object_or_404(BacktestResult, id=backtest_id, user=request.user)
    return render(request, 'backtesting/backtest_result.html', {'backtest': backtest})

@login_required
def backtest_status(request, backtest_id):
    backtest = get_object_or_404(BacktestResult, id=backtest_id, user=request.user)
    return JsonResponse({
        "status": backtest.status,
    })