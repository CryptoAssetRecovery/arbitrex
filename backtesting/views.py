# backtesting/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from strategies.models import Strategy
from .models import BacktestResult
from .tasks import run_backtest
from .forms import BacktestForm

@login_required
def dashboard(request):
    if request.method == 'POST':
        form = BacktestForm(request.POST)
        if form.is_valid():
            strategy = form.cleaned_data['strategy']
            timeframe = form.cleaned_data['timeframe']
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            leverage = form.cleaned_data.get('leverage')
            commission = form.cleaned_data.get('commission')
            slippage = form.cleaned_data.get('slippage')
            parameters = form.cleaned_data.get('parameters') or {}
            backtest = BacktestResult.objects.create(
                user=request.user,
                strategy=strategy,
                status='PENDING',
                parameters=parameters,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                leverage=leverage,
                commission=commission,
                slippage=slippage,
            )
            run_backtest.delay(backtest.id)
            return redirect('backtesting:backtest_result', backtest_id=backtest.id)
        else:
            messages.error(request, f"Form is not valid: {form.errors}")
    else:
        form = BacktestForm()
    return render(request, 'backtesting/index.html', {'form': form})

@login_required
def backtest_result(request, backtest_id):
    backtest = get_object_or_404(BacktestResult, id=backtest_id, user=request.user)
    return render(request, 'backtesting/backtest_result.html', {'backtest': backtest})