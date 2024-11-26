# backtesting/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import datetime

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
    trade_data = backtest.trade_data
    ocl_data = backtest.ocl_data_import.get_price_data()

    # Format the ocl_data
    ocl_data = ocl_data.to_dict(orient='records')

    # Transform priceData
    price_data = []
    for entry in ocl_data:
        # Parse the 'Date' string into a datetime object
        try:
            dt = datetime.datetime.strptime(entry['Date'], "%Y-%m-%d %H:%M:%S")
            timestamp = int(dt.timestamp())
        except ValueError as e:
            # Handle incorrect date formats
            continue  # Skip this entry or handle as needed

        price_data.append({
            "time": timestamp,
            "open": entry["Open"],
            "high": entry["High"],
            "low": entry["Low"],
            "close": entry["Close"],
        })

    # Transform tradeData
    trade_data_transformed = []
    for trade in trade_data:
        # Parse the 'time' string into a datetime object
        try:
            dt = datetime.datetime.strptime(trade["time"], "%Y-%m-%d %H:%M:%S")
            timestamp = int(dt.timestamp())
        except ValueError as e:
            # Handle incorrect date formats
            continue  # Skip this trade or handle as needed

        trade_data_transformed.append({
            "time": timestamp,
            "type": trade["type"],
            "price": trade["price"],
        })

    # print("Trade Data:", trade_data_transformed[0])
    # print("Price Data:", price_data[0])

    return JsonResponse({
        "tradeData": trade_data_transformed,
        "priceData": price_data
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