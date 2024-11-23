# backtesting/tasks.py

import os
import datetime
from celery import shared_task
from django.conf import settings
from .models import BacktestResult
from strategies.models import Strategy
import backtrader as bt
import matplotlib.pyplot as plt
from io import BytesIO
from django.core.files.base import ContentFile
import numpy as np

import yfinance as yf
import pandas as pd

def get_historical_data():
    # Calculate dates within Yahoo Finance's limitations
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=700)
    
    print(f"Fetching data from {start_date} to {end_date}")
    
    # Download historical data for BTC-USD with 1h intervals
    data = yf.download('BTC-USD', 
                      start=start_date, 
                      end=end_date,
                      interval='1h')

    # Debug: Print original columns
    print("Original Columns:", data.columns)

    # Check if columns are MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        # Extract the first level of the MultiIndex
        data.columns = data.columns.get_level_values(0)
        print("Flattened Columns:", data.columns)
    else:
        print("Columns are already single-level.")

    data.reset_index(inplace=True)
    
    # Rename 'Datetime' to 'Date' if needed
    if 'Datetime' in data.columns:
        data.rename(columns={'Datetime': 'Date'}, inplace=True)

    # Set index and resample
    data.set_index('Date', inplace=True)
    data = data.resample('4H').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum',
        'Adj Close': 'last'
    })
    data.reset_index(inplace=True)

    # Rename 'Adj Close' to 'Adj_Close'
    data.rename(columns={'Adj Close': 'Adj_Close'}, inplace=True)
    print("Renamed Columns:", data.columns)

    # Handle timezone if present
    if pd.api.types.is_datetime64_any_dtype(data['Date']):
        data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)

    # Check for missing values and handle them
    if data.isnull().values.any():
        print("Data contains missing values. Filling missing data.")
        data.fillna(method='ffill', inplace=True)
        data.fillna(method='bfill', inplace=True)  # In case forward fill doesn't work

    # Define required columns
    required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj_Close']

    # Verify that all required columns are present
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise KeyError(f"Missing columns in data: {missing_columns}")

    # Select only the necessary columns
    data = data[required_columns]

    # Debug: Print first few rows to verify
    print("Data Sample:\n", data.head())

    return data


@shared_task
def run_backtest(backtest_id):
    print(f"Running backtest {backtest_id}")

    backtest = BacktestResult.objects.get(id=backtest_id)
    backtest.status = 'RUNNING'
    backtest.save()

    try:
        data = get_historical_data()
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
        
        # Set commission - using a more realistic crypto commission
        cerebro.broker.setcommission(commission=0.001)  # 0.1% commission
        
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

    except Exception as e:
        import traceback
        backtest.status = 'FAILED'
        backtest.log = f"{str(e)}\n{traceback.format_exc()}"
        backtest.save()