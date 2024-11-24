# backtesting/tasks.py

from celery import shared_task
from django.core.files.base import ContentFile

from .binance_ocl import get_btc_ohlc_history
from .models import BacktestResult
from dashboard.models import BestPerformingAlgo
from io import BytesIO
import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt

import datetime

def get_historical_data(timeframe, start_date=None, end_date=None):
    # Map backtesting timeframes to Binance intervals
    timeframe_mapping = {
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d'
    }
    
    if timeframe not in timeframe_mapping:
        raise ValueError(f"Invalid timeframe: {timeframe}")
        
    # Convert dates to datetime objects if they're date objects
    if isinstance(start_date, datetime.date) and not isinstance(start_date, datetime.datetime):
        start_date = datetime.datetime.combine(start_date, datetime.time.min)
    if isinstance(end_date, datetime.date) and not isinstance(end_date, datetime.datetime):
        end_date = datetime.datetime.combine(end_date, datetime.time.max)
    
    # Convert string dates to datetime if they're strings
    if isinstance(end_date, str):
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    
    if end_date is None:
        end_date = datetime.datetime.now()
    if start_date is None:
        if timeframe == '1d':
            start_date = end_date - datetime.timedelta(days=700)
        elif timeframe in ['5m', '15m', '30m']:
            start_date = end_date - datetime.timedelta(days=100)
        else:
            start_date = end_date - datetime.timedelta(days=30)
    
    # Ensure dates are timezone-naive datetime objects
    if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
    if hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)

    # Get data from Binance
    data = get_btc_ohlc_history(
        interval=timeframe_mapping[timeframe],
        start_date=start_date,
        end_date=end_date
    )
    
    if data is None:
        raise ValueError("No data returned from Binance")
    
    # Rename columns to match expected format
    data = data.rename(columns={
        'time': 'Date',
        'volume': 'Volume'
    })
    
    # Add Adj_Close column (in crypto it's the same as Close)
    data['Adj_Close'] = data['close']
    
    # Select and reorder columns to match expected format
    data = data[['Date', 'open', 'high', 'low', 'close', 'Volume', 'Adj_Close']]
    
    # Rename remaining columns to match expected format
    data = data.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close'
    })
    
    # Set index to Date
    data.set_index('Date', inplace=True)
    
    # Handle timezone if present
    if pd.api.types.is_datetime64_any_dtype(data.index):
        data.index = pd.to_datetime(data.index).tz_localize(None)
    
    # Reset index to match expected format
    data.reset_index(inplace=True)
    
    return data


@shared_task
def run_backtest(backtest_id):
    print(f"Running backtest {backtest_id}")

    backtest = BacktestResult.objects.get(id=backtest_id)
    backtest.status = 'RUNNING'
    backtest.save()

    try:
        timeframe = backtest.timeframe
        start_date = backtest.start_date
        end_date = backtest.end_date

        commission = backtest.commission

        data = get_historical_data(timeframe, start_date, end_date)
        print("Data Columns after processing:", data.columns)

        # Dynamically create a Strategy class from user code
        strategy_code = backtest.strategy.code
        exec_globals = {}
        exec(strategy_code, exec_globals)
        UserStrategy = None
        for obj in exec_globals.values():
            if isinstance(obj, type) and issubclass(obj, bt.Strategy):
                UserStrategy = obj
                break

        if not UserStrategy:
            raise ValueError("Strategy class not defined or does not inherit from backtrader.Strategy.")

        # Initialize Cerebro engine
        cerebro = bt.Cerebro()
        
        # Add strategy with logging enabled
        cerebro.addstrategy(UserStrategy)
        
        # Set commission - using a percentage commission
        cerebro.broker.setcommission(
            commission=(commission / 100),
            commtype=bt.CommInfoBase.COMM_PERC  # Specify commission type as percentage
        )
        
        # Set cash
        initial_cash = 10000
        cerebro.broker.set_cash(initial_cash)
        
        # Add sizer
        cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

        # Add analyzers for Sharpe Ratio and Trade Analysis
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', timeframe=bt.TimeFrame.Days, compression=1)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')

        # Configure the data feed for Backtrader
        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime='Date',
            open='Open',
            high='High',
            low='Low',
            close='Close',
            volume='Volume',
            openinterest=-1
        )
        cerebro.adddata(data_feed)

        # Print initial portfolio value
        print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')

        # Run backtest with analyzers
        results = cerebro.run()
        
        # Extract analyzers' results
        first_strategy = results[0]
        
        # Sharpe Ratio
        sharpe_ratio = first_strategy.analyzers.sharpe_ratio.get_analysis().get('sharperatio', 0.0)

        # Trade Analyzer for Win Rate
        trade_analyzer = first_strategy.analyzers.trade_analyzer.get_analysis()
        total_trades = trade_analyzer.total.total if 'total' in trade_analyzer and trade_analyzer.total.total else 0
        won_trades = trade_analyzer.won.total if 'won' in trade_analyzer and trade_analyzer.won.total else 0
        win_rate = (won_trades / total_trades) * 100 if total_trades > 0 else 0.0

        # Print final portfolio value
        final_value = cerebro.broker.getvalue()
        print(f'Final Portfolio Value: {final_value:.2f}')
        print(f'Profit/Loss: {final_value - initial_cash:.2f}')
        print(f'Sharpe Ratio: {sharpe_ratio:.2f}')
        print(f'Win Rate: {win_rate:.2f}%')

        # Generate plots
        figs = cerebro.plot(style='candlestick')
        
        # Backtrader returns a list of figures, we'll save the first one
        fig = figs[0][0]
        
        # Save the figure to bytes
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        image_file = ContentFile(buf.getvalue(), f'backtest_{backtest.id}.png')
        backtest.result_file.save(f'backtest_{backtest.id}.png', image_file, save=False)
        
        # Close the figure to free memory
        plt.close(fig)

        # Update backtest result
        backtest.status = 'COMPLETED'
        backtest.completed_at = datetime.datetime.utcnow()
        backtest.parameters = {}  # Populate if you have parameters
        return_string = (
            f"Performance Summary\n"
            f"===================\n"
            f"Initial Portfolio Value: ${initial_cash:,.2f}\n"
            f"Final Portfolio Value:   ${final_value:,.2f}\n"
            f"Profit/Loss:             ${final_value - initial_cash:,.2f}\n"
            f"Return:                  {((final_value - initial_cash) / initial_cash) * 100:.2f}%\n"
            f"Sharpe Ratio:            {sharpe_ratio:.2f}\n"
            f"Win Rate:                {win_rate:.2f}%"
        )
        backtest.log = return_string

        # Save calculated metrics
        backtest.algo_return = ((final_value - initial_cash) / initial_cash) * 100  # Percentage return
        backtest.algo_sharpe_ratio = sharpe_ratio
        backtest.algo_win_rate = win_rate
        backtest.save()

        # Check if this is the best performing algo
        best_performance = BestPerformingAlgo.objects.order_by('-algo_sharpe_ratio').first()
        if best_performance is None or backtest.algo_sharpe_ratio > best_performance.algo_sharpe_ratio:
            best_performance = BestPerformingAlgo.objects.create(strategy=backtest.strategy, backtest_result=backtest, algo_return=backtest.algo_return, algo_sharpe_ratio=backtest.algo_sharpe_ratio, algo_win_rate=backtest.algo_win_rate)

    except Exception as e:
        import traceback
        backtest.status = 'FAILED'
        backtest.log = f"{str(e)}\n{traceback.format_exc()}"
        backtest.save()