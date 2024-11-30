# backtesting/tasks.py

import matplotlib

matplotlib.use('module://backend_interagg')

from celery import shared_task
from django.core.files.base import ContentFile

from .models import BacktestResult
from dashboard.models import (
    BestPerformingAlgo, 
    MostWinningAlgo, 
    BestReturnAlgo
)
from .analyzers import (
    PortfolioValueAnalyzer, 
    TradeListAnalyzer, 
    OrderListAnalyzer
)

import backtrader as bt
import matplotlib.pyplot as plt
from pathlib import Path
from io import BytesIO
import pandas as pd
import datetime
import json

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
    """
    Executes the backtest asynchronously and updates the BacktestResult instance accordingly.
    
    Args:
        backtest_id: ID of the BacktestResult object to update
    """

    # Use Agg backend for matplotlib
    matplotlib.use('Agg')

    try:
        backtest = BacktestResult.objects.get(id=backtest_id)
        backtest.status = 'RUNNING'
        backtest.save()

        commission = backtest.commission

        if backtest.ocl_data_import:
            data = get_ocl_historical_data(backtest.ocl_data_import.id)
            print(f"Data shape: {data.shape}")
        else:
            raise ValueError("No OCL data import ID found for this backtest.")
        
        # Clean and prepare data
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
        initial_cash = 10_000
        cerebro.broker.set_cash(initial_cash)

        # Add sizer
        cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

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

        # Initialize storage for trade data
        trade_data = []  # Initialize trade_data as an empty list

        # Initialize storage for order data
        order_data = []

        # Add all analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        cerebro.addanalyzer(PortfolioValueAnalyzer, _name='portfolio_value')
        cerebro.addanalyzer(TradeListAnalyzer, _name='trade_list')
        cerebro.addanalyzer(OrderListAnalyzer, _name='order_list') 

        # Run backtest with analyzers
        print("Running backtest")
        results = cerebro.run()
        print("Backtest completed")
        first_strategy = results[0]

        # Process trade data
        trade_list = first_strategy.analyzers.trade_list.get_analysis()
        trades = trade_list.get('trades', [])
        
        # Process order data
        order_list = first_strategy.analyzers.order_list.get_analysis()
        orders = order_list.get('orders', [])

        # Populate trade_data
        for trade in trades:
            trade_entry = {
                "time": trade['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                "type": trade['type'],
                "price": trade['price'],
                "size": trade['size'],
                "portfolio_value": trade['portfolio_value']
            }
            trade_data.append(trade_entry)

        # Populate order_data
        for order in orders:
            order_entry = {
                "time": order['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                "type": order['type'],
                "price": order['price'],
                "size": order['size'],
                "portfolio_value": order['portfolio_value']
            }
            order_data.append(order_entry)

        # Save both trade and order data
        backtest.trade_data = trade_data
        backtest.order_data = order_data
        backtest.save()

        # Retrieve analyzers' results
        sharpe_ratio = first_strategy.analyzers.sharpe_ratio.get_analysis().get('sharperatio', 0.0)

        # Trade Analyzer for Win Rate
        trade_analyzer = first_strategy.analyzers.trade_analyzer.get_analysis()
        total_trades = trade_analyzer.total.total if hasattr(trade_analyzer, 'total') and trade_analyzer.total.total else 0
        won_trades = trade_analyzer.won.total if hasattr(trade_analyzer, 'won') and trade_analyzer.won.total else 0
        win_rate = (won_trades / total_trades) * 100 if total_trades > 0 else 0.0

        # Handle case with no trades
        if total_trades == 0:
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

        # Retrieve trade transactions from the custom TradeListAnalyzer
        trade_list_analyzer = first_strategy.analyzers.trade_list.get_analysis()
        trades = trade_list_analyzer.get('trades', [])

        # Populate trade_data
        for trade in trades:
            trade_entry = {
                "time": trade['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                "type": trade['type'],
                "price": trade['price'],
                "size": trade['size'],
                "portfolio_value": trade['portfolio_value']
            }
            trade_data.append(trade_entry)

        # Retrieve order executions from the OrderListAnalyzer
        order_list_analyzer = first_strategy.analyzers.order_list.get_analysis()
        orders = order_list_analyzer.get('orders', [])

        # Populate order_data (all executed orders)
        for order in orders:
            order_entry = {
                "time": order['datetime'].strftime('%Y-%m-%d %H:%M:%S'),
                "type": order['type'],
                "price": order['price'],
                "size": order['size'],
                "portfolio_value": order['portfolio_value']
            }
            order_data.append(order_entry)

        # Save the trade data and order data to BacktestResult
        backtest.trade_data = trade_data
        backtest.order_data = order_data
        backtest.portfolio_values = first_strategy.analyzers.portfolio_value.get_analysis()
        backtest.save()

        # Save portfolio values as JSON
        backtest.portfolio_values_json = json.dumps(backtest.portfolio_values)

        # Save trade data
        backtest.trade_data = trade_data  # Now trade_data is defined
        backtest.trade_data_json = json.dumps(trade_data)
        
        # Create trades directory if it doesn't exist
        trades_dir = Path('media/trades')
        trades_dir.mkdir(parents=True, exist_ok=True)
        
        # Save backtest result
        final_value = cerebro.broker.getvalue()

        # Generate plots with interactive mode explicitly disabled
        figs = cerebro.plot(style='candlestick', iplot=False)

        # Handle the figure saving with explicit non-interactive settings
        if figs and len(figs) > 0 and len(figs[0]) > 0:
            fig = figs[0][0]
            buf = BytesIO()
            fig.savefig(buf, 
                       format='png',
                       bbox_inches='tight',
                       dpi=300,
                       backend='Agg')
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
        backtest.parameters = json.dumps(backtest.parameters)  # Assuming parameters is a dict
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
            BestPerformingAlgo.objects.create(
                strategy=backtest.strategy,
                backtest_result=backtest,
                algo_return=backtest.algo_return,
                algo_sharpe_ratio=backtest.algo_sharpe_ratio,
                algo_win_rate=backtest.algo_win_rate
            )

        # Check if this is the best return algo
        best_return = BestReturnAlgo.objects.order_by('-algo_return').first()
        if best_return is None or backtest.algo_return > best_return.algo_return:
            BestReturnAlgo.objects.create(
                strategy=backtest.strategy,
                backtest_result=backtest,
                algo_return=backtest.algo_return,
                algo_win_rate=backtest.algo_win_rate,
                algo_sharpe_ratio=backtest.algo_sharpe_ratio
            )

        # Check if this is the most winning algo
        most_winning = MostWinningAlgo.objects.order_by('-algo_win_rate').first()
        if most_winning is None or backtest.algo_win_rate > most_winning.algo_win_rate:
            MostWinningAlgo.objects.create(
                strategy=backtest.strategy,
                backtest_result=backtest,
                algo_return=backtest.algo_return,
                algo_win_rate=backtest.algo_win_rate,
                algo_sharpe_ratio=backtest.algo_sharpe_ratio
            )

        # Optionally, include portfolio_values from analyzer
        ocl_data = data.copy()
        ocl_data['Date'] = ocl_data['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        ocl_data = ocl_data.to_dict(orient='records')

        # Save the trade data and ocl data
        backtest.trade_data = trade_data
        backtest.ocl_data = ocl_data
        backtest.save()

    except Exception as e:
        import traceback
        backtest.status = 'FAILED'
        backtest.log = f"{str(e)}\n{traceback.format_exc()}"
        backtest.save()
    finally:
        # Ensure we clean up any remaining figures
        plt.close('all')