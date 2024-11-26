# backtesting/tasks.py

import matplotlib
# Force Agg backend before importing anything else matplotlib-related
matplotlib.use('module://backend_interagg')

# Disable interactive mode right after matplotlib import

from celery import shared_task
from django.core.files.base import ContentFile

from .models import BacktestResult
from dashboard.models import BestPerformingAlgo

import matplotlib.pyplot as plt
from io import BytesIO
import pandas as pd
import backtrader as bt
from pathlib import Path

import datetime
import csv

def get_ocl_historical_data(data_import_id):
    """
    Fetch historical data from OCLDataImport and format it to match get_historical_data output.
    
    Args:
        data_import_id: ID of the OCLDataImport object
        
    Returns:
        pandas.DataFrame with columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj_Close']
    """
    from data.models import OCLDataImport, OCLPrice
    
    try:
        # Get the data import object and its associated prices
        data_import = OCLDataImport.objects.get(id=data_import_id)
        prices = OCLPrice.objects.filter(
            data_import=data_import
        ).order_by('date').values(
            'date', 'open', 'high', 'low', 'close', 'volume'
        )
        
        if not prices:
            raise ValueError(f"No price data found for import {data_import_id}")
            
        # Convert to DataFrame
        df = pd.DataFrame(list(prices))
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        # Add Adj_Close column (in crypto it's the same as Close)
        df['Adj_Close'] = df['Close']
        
        # Ensure columns are in the expected order
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj_Close']]
        
        # Handle timezone if present
        if pd.api.types.is_datetime64_any_dtype(df['Date']):
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
            
        return df
        
    except OCLDataImport.DoesNotExist:
        raise ValueError(f"Data import {data_import_id} not found")


@shared_task
def run_backtest(backtest_id):
    
    # Create a new figure at the start and ensure it's non-interactive
    plt.switch_backend('Agg')
    
    backtest = BacktestResult.objects.get(id=backtest_id)
    backtest.status = 'RUNNING'
    backtest.save()

    try:
        commission = backtest.commission

        if backtest.ocl_data_import:
            data = get_ocl_historical_data(backtest.ocl_data_import.id)
        else:
            raise ValueError("No OCL data import ID found for this backtest.")
        
        ocl_data = data.to_dict(orient='records')

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
        cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')

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

        # Run backtest with analyzers
        results = cerebro.run()
        
        # Extract analyzers' results
        first_strategy = results[0]

        # Save trade data
        transactions = first_strategy.analyzers.transactions.get_analysis()

        # Initialize an empty list to store formatted trade data
        trade_data = []

        # Iterate over each transaction date and its corresponding trades
        for date, trades in transactions.items():
            for trans in trades:
                price = trans[1]  # Price is the second element
                size = trans[4]   # Size is the fifth element
                trade_type = 'buy' if size > 0 else 'sell'

                # Append each trade as a dictionary to the trade_data list
                trade_data.append({
                    "time": date.strftime('%Y-%m-%d %H:%M:%S'),
                    "type": trade_type,
                    "price": price,
                    "size": abs(size)
                })

        # Save the formatted trade data to the backtest object
        backtest.trade_data = trade_data

        # Save the trade data
        transactions = first_strategy.analyzers.transactions.get_analysis()
        
        # Convert datetime keys to strings in transactions
        formatted_transactions = {
            date.strftime('%Y-%m-%d %H:%M:%S'): trades 
            for date, trades in transactions.items()
        }

        # Create trades directory if it doesn't exist
        trades_dir = Path('media/trades')
        trades_dir.mkdir(parents=True, exist_ok=True)
        
        # Sharpe Ratio
        sharpe_ratio = first_strategy.analyzers.sharpe_ratio.get_analysis().get('sharperatio', 0.0)

        # Trade Analyzer for Win Rate
        trade_analyzer = first_strategy.analyzers.trade_analyzer.get_analysis()
        total_trades = trade_analyzer.total.total if 'total' in trade_analyzer and trade_analyzer.total.total else 0
        won_trades = trade_analyzer.won.total if 'won' in trade_analyzer and trade_analyzer.won.total else 0
        win_rate = (won_trades / total_trades) * 100 if total_trades > 0 else 0.0

        # Handle case with no trades
        if total_trades == 0:
            # print("No trades were made during the backtest.")
            sharpe_ratio = 0.0
            win_rate = 0.0
            performance_summary = "No trades were executed in this backtest."
        else:
            performance_summary = (
                f"Performance Summary\n"
                f"===================\n"
                f"Initial Portfolio Value: ${initial_cash:,.2f}\n"
                f"Final Portfolio Value:   ${cerebro.broker.getvalue():.2f}\n"
                f"Profit/Loss:             ${cerebro.broker.getvalue() - initial_cash:.2f}\n"
                f"Return:                  {((cerebro.broker.getvalue() - initial_cash) / initial_cash) * 100:.2f}%\n"
                f"Sharpe Ratio:            {sharpe_ratio:.2f}\n"
                f"Win Rate:                {win_rate:.2f}%"
            )

        # Print final portfolio value
        final_value = cerebro.broker.getvalue()
        # print(f'Final Portfolio Value: {final_value:.2f}')
        # print(f'Profit/Loss: {final_value - initial_cash:.2f}')
        # print(f'Sharpe Ratio: {sharpe_ratio:.2f}')
        # print(f'Win Rate: {win_rate:.2f}%')

        # Generate plots with interactive mode explicitly disabled
        figs = cerebro.plot(style='candlestick', iplot=False)
        
        # Handle the figure saving with explicit non-interactive settings
        if figs and len(figs) > 0 and len(figs[0]) > 0:
            fig = figs[0][0]
            
            # Save the figure with tight layout and high DPI
            buf = BytesIO()
            fig.savefig(buf, 
                       format='png',
                       bbox_inches='tight',
                       dpi=300,
                       backend='Agg')
            
            # Clean up
            plt.close(fig)
            plt.close('all')
            
            # Save the image
            buf.seek(0)
            image_file = ContentFile(buf.getvalue(), f'backtest_{backtest.id}.png')
            backtest.result_file.save(f'backtest_{backtest.id}.png', image_file, save=False)
            
            # Explicitly close the buffer
            buf.close()

        # Update backtest result
        backtest.status = 'COMPLETED'
        backtest.completed_at = datetime.datetime.utcnow()
        backtest.parameters = {}  # Populate if you have parameters
        backtest.log = performance_summary

        if total_trades == 0:
            # Save default metrics when no trades are made
            backtest.algo_return = 0.0
            backtest.algo_sharpe_ratio = 0.0
            backtest.algo_win_rate = 0.0
        else:
            # Save calculated metrics
            backtest.algo_return = ((final_value - initial_cash) / initial_cash) * 100  # Percentage return
            backtest.algo_sharpe_ratio = sharpe_ratio
            backtest.algo_win_rate = win_rate

        backtest.save()

        # Check if this is the best performing algo
        best_performance = BestPerformingAlgo.objects.order_by('-algo_sharpe_ratio').first()
        if best_performance is None or backtest.algo_sharpe_ratio > best_performance.algo_sharpe_ratio:
            best_performance = BestPerformingAlgo.objects.create(
                strategy=backtest.strategy,
                backtest_result=backtest,
                algo_return=backtest.algo_return,
                algo_sharpe_ratio=backtest.algo_sharpe_ratio,
                algo_win_rate=backtest.algo_win_rate
            )
        
        # Convert data to records and ensure timestamps are converted to strings
        ocl_data = data.copy()
        ocl_data['Date'] = ocl_data['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        ocl_data = ocl_data.to_dict(orient='records')

        # Save the trade data and ocl data
        backtest.trade_data = trade_data

        backtest.save()

    except Exception as e:
        import traceback
        backtest.status = 'FAILED'
        backtest.log = f"{str(e)}\n{traceback.format_exc()}"
        backtest.save()
    finally:
        # Ensure we clean up any remaining figures
        plt.close('all')