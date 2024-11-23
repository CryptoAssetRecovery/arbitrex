# backtesting/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from strategies.models import Strategy
from .models import BacktestResult
from .tasks import run_backtest
from .forms import BacktestForm

@login_required
def dashboard(request):
    form = BacktestForm()
    if request.method == 'POST':
        if 'strategy_id' in request.POST:
            strategy_id = request.POST['strategy_id']
            strategy = get_object_or_404(Strategy, id=strategy_id, user=request.user)
        else:   
            form = BacktestForm(request.POST)
            if form.is_valid():
                strategy = form.cleaned_data['strategy']
        backtest = BacktestResult.objects.create(
            user=request.user,
            strategy=strategy,
            status='PENDING',
            parameters={},
        )
        run_backtest.delay(backtest.id)
        return redirect('backtesting:backtest_result', backtest_id=backtest.id)
    return render(request, 'backtesting/index.html', {'form': form})

@login_required
def backtest_result(request, backtest_id):
    backtest = get_object_or_404(BacktestResult, id=backtest_id, user=request.user)
    return render(request, 'backtesting/backtest_result.html', {'backtest': backtest})