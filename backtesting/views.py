# backtesting/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import BacktestResult
from .tasks import run_backtest
from .forms import BacktestForm

@login_required
def dashboard(request):
    if request.method == 'POST':
        form = BacktestForm(request.POST)
        if form.is_valid():
            strategy = form.cleaned_data['strategy']
            commission = form.cleaned_data.get('commission')
            slippage = form.cleaned_data.get('slippage')
            parameters = form.cleaned_data.get('parameters') or {}
            ocl_data_import = form.cleaned_data.get('ocl_data_import')
            backtest = BacktestResult.objects.create(
                user=request.user,
                strategy=strategy,
                status='PENDING',
                parameters=parameters,
                commission=commission,
                slippage=slippage,
                ocl_data_import=ocl_data_import,
            )
            run_backtest.delay(backtest.id)
            return redirect('backtesting:backtest_result', backtest_id=backtest.id)
        else:
            messages.error(request, f"Form is not valid: {form.errors}")
    else:
        form = BacktestForm()
    return render(request, 'backtesting/index.html', {'form': form})

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