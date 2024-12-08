# backtesting/tasks.py

import matplotlib
matplotlib.use('Agg')

from celery import shared_task
from django.core.files.base import ContentFile

from .models import BacktestResult
from dashboard.models import BestPerformingAlgo, MostWinningAlgo, BestReturnAlgo
from .analyzers import PortfolioValueAnalyzer, TradeListAnalyzer, OrderListAnalyzer
from strategies.utils import load_strategies_and_inject_log

import backtrader as bt
import matplotlib.pyplot as plt
from io import BytesIO
import pandas as pd
import datetime
import json
import traceback


def get_ocl_historical_data(data_import_id):
    """
    Fetch historical data from OCLDataImport and format it to match expected output.
    """
    from data.models import OCLDataImport, OCLPrice

    data_import = OCLDataImport.objects.get(id=data_import_id)
    prices = OCLPrice.objects.filter(data_import=data_import).order_by('date').values(
        'date', 'open', 'high', 'low', 'close', 'volume'
    )

    if not prices:
        raise ValueError(f"No price data found for import {data_import_id}")

    df = pd.DataFrame(list(prices))
    df = df.rename(columns={
        'date': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    })
    df['Adj_Close'] = df['Close']
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj_Close']]
    if pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)

    return df

def run_cerebro_with_data_and_strategy(dataframes, UserStrategy, commission=0.0):
    """
    Configure and run Cerebro with given dataframes and the user strategy.
    Supports multiple data feeds if dataframes is a list of DataFrames.
    """
    cerebro = bt.Cerebro()
    cerebro.addstrategy(UserStrategy)

    # Set commission as a percentage
    cerebro.broker.setcommission(
        commission=(commission / 100),
        commtype=bt.CommInfoBase.COMM_PERC
    )

    initial_cash = 10_000
    cerebro.broker.set_cash(initial_cash)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

    # Add one or multiple data feeds
    for df in dataframes:
        data_feed = bt.feeds.PandasData(
            dataname=df,
            datetime='Date',
            open='Open',
            high='High',
            low='Low',
            close='Close',
            volume='Volume',
            openinterest=-1
        )
        cerebro.adddata(data_feed)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    cerebro.addanalyzer(PortfolioValueAnalyzer, _name='portfolio_value')
    cerebro.addanalyzer(TradeListAnalyzer, _name='trade_list')
    cerebro.addanalyzer(OrderListAnalyzer, _name='order_list')

    results = cerebro.run()
    return cerebro, results, initial_cash


def extract_results_and_save(backtest, cerebro, results, strategy_logs):
    """
    Extract analyzer results, trades, orders, plots, and save everything to BacktestResult.
    """
    first_strategy = results[0]
    final_value = cerebro.broker.getvalue()

    # Extract Sharpe ratio
    sharpe_ratio = first_strategy.analyzers.sharpe_ratio.get_analysis().get('sharperatio', 0.0)

    # Trade Analyzer
    trade_analyzer = first_strategy.analyzers.trade_analyzer.get_analysis()
    total_trades = trade_analyzer.get('total', {}).get('total', 0)
    won_trades = trade_analyzer.get('won', {}).get('total', 0)
    win_rate = (won_trades / total_trades) * 100 if total_trades > 0 else 0.0

    # Trades
    trade_list = first_strategy.analyzers.trade_list.get_analysis().get('trades', [])
    trade_data = [{
        "time": t['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
        "type": t['type'],
        "price": t['price'],
        "size": t['size'],
        "portfolio_value": t['portfolio_value']
    } for t in trade_list]

    # Orders
    order_list = first_strategy.analyzers.order_list.get_analysis().get('orders', [])
    order_data = [{
        "time": o['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
        "type": o['type'],
        "price": o['price'],
        "size": o['size'],
        "portfolio_value": o['portfolio_value']
    } for o in order_list]

    initial_cash = 10_000
    if total_trades == 0:
        sharpe_ratio = 0.0
        win_rate = 0.0
        performance_summary = "No trades were executed in this backtest."
    else:
        performance_summary = (
            f"Performance Summary\n"
            f"===================\n"
            f"Initial Portfolio Value: ${initial_cash:,.2f}\n"
            f"Final Portfolio Value:   ${final_value:.2f}\n"
            f"Profit/Loss:             ${final_value - initial_cash:.2f}\n"
            f"Return:                  {((final_value - initial_cash) / initial_cash) * 100:.2f}%\n"
            f"Sharpe Ratio:            {sharpe_ratio:.2f}\n"
            f"Win Rate:                {win_rate:.2f}%\n"
            f"Number of Trades:        {total_trades}"
        )

    # Save trades and orders
    backtest.trade_data = trade_data
    backtest.order_data = order_data

    # Portfolio values
    backtest.portfolio_values = first_strategy.analyzers.portfolio_value.get_analysis()
    backtest.portfolio_values_json = json.dumps(backtest.portfolio_values)
    backtest.trade_data_json = json.dumps(trade_data)

    # Generate plot
    figs = cerebro.plot(style='candlestick', iplot=False)
    if figs and len(figs) > 0 and len(figs[0]) > 0:
        fig = figs[0][0]
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
        plt.close(fig)
        buf.seek(0)
        image_file = ContentFile(buf.getvalue(), f'backtest_{backtest.id}.png')
        backtest.result_file.save(f'backtest_{backtest.id}.png', image_file, save=False)
        buf.close()

    backtest.status = 'COMPLETED'
    backtest.completed_at = datetime.datetime.utcnow()
    backtest.parameters = json.dumps(backtest.parameters) if isinstance(backtest.parameters, dict) else backtest.parameters
    backtest.log = "\n".join([
        "Strategy Logs:",
        "==============",
        *strategy_logs,
        "",
        performance_summary
    ])

    backtest.algo_return = ((final_value - initial_cash) / initial_cash) * 100 if total_trades > 0 else 0.0
    backtest.algo_sharpe_ratio = sharpe_ratio
    backtest.algo_win_rate = win_rate
    backtest.save()

    # Update leaderboards
    update_best_algos(backtest)

    return backtest


def update_best_algos(backtest):
    """
    Update BestPerformingAlgo, BestReturnAlgo, MostWinningAlgo records if this backtest outperforms them.
    """
    # BestPerformingAlgo
    best_performance = BestPerformingAlgo.objects.order_by('-algo_sharpe_ratio').first()
    if best_performance is None or backtest.algo_sharpe_ratio > best_performance.algo_sharpe_ratio:
        BestPerformingAlgo.objects.create(
            strategy=backtest.strategy,
            backtest_result=backtest,
            algo_return=backtest.algo_return,
            algo_sharpe_ratio=backtest.algo_sharpe_ratio,
            algo_win_rate=backtest.algo_win_rate
        )

    # BestReturnAlgo
    best_return = BestReturnAlgo.objects.order_by('-algo_return').first()
    if best_return is None or backtest.algo_return > best_return.algo_return:
        BestReturnAlgo.objects.create(
            strategy=backtest.strategy,
            backtest_result=backtest,
            algo_return=backtest.algo_return,
            algo_win_rate=backtest.algo_win_rate,
            algo_sharpe_ratio=backtest.algo_sharpe_ratio
        )

    # MostWinningAlgo
    most_winning = MostWinningAlgo.objects.order_by('-algo_win_rate').first()
    if most_winning is None or backtest.algo_win_rate > most_winning.algo_win_rate:
        MostWinningAlgo.objects.create(
            strategy=backtest.strategy,
            backtest_result=backtest,
            algo_return=backtest.algo_return,
            algo_win_rate=backtest.algo_win_rate,
            algo_sharpe_ratio=backtest.algo_sharpe_ratio
        )


@shared_task
def run_backtest(backtest_id):
    """
    Executes the backtest asynchronously and updates the BacktestResult accordingly.
    """
    # Logging storage
    strategy_logs = []

    def capture_log(strategy, txt, dt=None):
        dt = dt or strategy.datas[0].datetime.date(0)
        log_entry = f'{dt.isoformat()} {txt}'
        strategy_logs.append(log_entry)

    backtest = BacktestResult.objects.get(id=backtest_id)
    backtest.status = 'RUNNING'
    backtest.save()

    try:
        # Load data
        if not backtest.ocl_data_import:
            raise ValueError("No OCL data import ID found for this backtest.")
        data_df = get_ocl_historical_data(backtest.ocl_data_import.id)

        # Load user strategy if it hasn't been loaded yet
        if not backtest.strategy_code:
            backtest.strategy_code = backtest.strategy.code
            backtest.save()
        UserStrategy = load_strategies_and_inject_log(backtest.strategy_code, capture_log)

        # Run Cerebro
        cerebro, results, initial_cash = run_cerebro_with_data_and_strategy(
            dataframes=[data_df],
            UserStrategy=UserStrategy,
            commission=backtest.commission
        )

        # Extract results and save
        backtest = extract_results_and_save(backtest, cerebro, results, strategy_logs)

        # Also store OCL data for reference
        ocl_data = data_df.copy()
        ocl_data['Date'] = ocl_data['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        backtest.ocl_data = ocl_data.to_dict(orient='records')
        backtest.save()

    except Exception as e:
        backtest.status = 'FAILED'
        backtest.log = f"{str(e)}\n{traceback.format_exc()}"
        backtest.save()
    finally:
        plt.close('all')
