import unittest
from unittest.mock import patch, MagicMock
import datetime
import pandas as pd
import backtrader as bt
from backtesting.tasks import (
    get_ocl_historical_data,
    load_strategies_and_inject_log,
    run_cerebro_with_data_and_strategy,
    extract_results_and_save,
    update_best_algos,
    run_backtest
)

class TestTasks(unittest.TestCase):

    @patch('data.models.OCLPrice')
    @patch('data.models.OCLDataImport')
    def test_get_ocl_historical_data_success(self, mock_data_import, mock_price):
        mock_data_import_obj = MagicMock()
        mock_data_import.objects.get.return_value = mock_data_import_obj
        
        mock_price.objects.filter.return_value.order_by.return_value.values.return_value = [
            {'date': datetime.datetime(2020,1,1), 'open':1, 'high':2, 'low':0.5, 'close':1.5, 'volume':1000}
        ]

        df = get_ocl_historical_data(123)
        self.assertIsNotNone(df)
        self.assertIn('Date', df.columns)
        self.assertIn('Open', df.columns)
        self.assertEqual(df.iloc[0]['Open'], 1)

    @patch('data.models.OCLPrice')
    @patch('data.models.OCLDataImport')
    def test_get_ocl_historical_data_no_data(self, mock_data_import, mock_price):
        mock_data_import_obj = MagicMock()
        mock_data_import.objects.get.return_value = mock_data_import_obj
        mock_price.objects.filter.return_value.order_by.return_value.values.return_value = []

        with self.assertRaises(ValueError) as context:
            get_ocl_historical_data(123)
        self.assertIn("No price data found", str(context.exception))

    def test_load_strategies_and_inject_log_success(self):
        strategy_code = """
import backtrader as bt
class MyTestStrategy(bt.Strategy):
    def __init__(self):
        pass
"""
        def mock_capture_log(strategy, txt, dt=None):
            pass

        UserStrategy = load_strategies_and_inject_log(strategy_code, mock_capture_log)
        self.assertTrue(hasattr(UserStrategy, 'log'))

    def test_load_strategies_and_inject_log_no_strategy(self):
        strategy_code = "x = 5"
        def mock_capture_log(strategy, txt, dt=None):
            pass

        with self.assertRaises(ValueError):
            load_strategies_and_inject_log(strategy_code, mock_capture_log)

    @patch('backtesting.tasks.bt.Cerebro')
    def test_run_cerebro_with_data_and_strategy(self, mock_cerebro_class):
        mock_cerebro = MagicMock()
        mock_cerebro_class.return_value = mock_cerebro

        df = pd.DataFrame([{
            'Date': datetime.datetime(2020,1,1),
            'Open':1, 'High':2, 'Low':0.5, 'Close':1.5, 'Volume':1000, 'Adj_Close':1.5
        }])

        class MockStrategy:
            pass

        cerebro, results, initial_cash = run_cerebro_with_data_and_strategy([df], MockStrategy, commission=0.1)
        mock_cerebro.addstrategy.assert_called_once()
        mock_cerebro.adddata.assert_called()
        mock_cerebro.run.assert_called_once()
        self.assertEqual(initial_cash, 10000)

    @patch('backtesting.tasks.BestPerformingAlgo')
    @patch('backtesting.tasks.BestReturnAlgo')
    @patch('backtesting.tasks.MostWinningAlgo')
    def test_extract_results_and_save_no_trades(self, mock_most_winning, mock_best_return, mock_best_perf):
        # Make queries return None so no comparison occurs
        mock_best_perf.objects.order_by.return_value.first.return_value = None
        mock_best_return.objects.order_by.return_value.first.return_value = None
        mock_most_winning.objects.order_by.return_value.first.return_value = None

        backtest = MagicMock()
        backtest.parameters = {}
        # Make backtest.strategy a valid mock strategy model
        mock_strategy_model = MagicMock()
        mock_strategy_model.pk = 1
        type(mock_strategy_model).__name__ = 'Strategy'
        backtest.strategy = mock_strategy_model

        mock_cerebro = MagicMock()
        mock_cerebro.broker.getvalue.return_value = 10000

        mock_strategy = MagicMock()
        mock_results = [mock_strategy]

        mock_strategy.analyzers.sharpe_ratio.get_analysis.return_value = {}
        mock_strategy.analyzers.trade_analyzer.get_analysis.return_value = {'total': {'total': 0}, 'won': {'total': 0}}
        mock_strategy.analyzers.trade_list.get_analysis.return_value = {'trades': []}
        mock_strategy.analyzers.order_list.get_analysis.return_value = {'orders': []}
        mock_strategy.analyzers.portfolio_value.get_analysis.return_value = {'portfolio': []}

        strategy_logs = ["2020-01-01 Something happened"]
        backtest = extract_results_and_save(backtest, mock_cerebro, mock_results, strategy_logs)
        self.assertEqual(backtest.status, 'COMPLETED')
        self.assertIn("No trades were executed", backtest.log)
        self.assertEqual(backtest.algo_return, 0.0)
        self.assertEqual(backtest.algo_sharpe_ratio, 0.0)
        self.assertEqual(backtest.algo_win_rate, 0.0)

    @patch('backtesting.tasks.BestPerformingAlgo')
    @patch('backtesting.tasks.BestReturnAlgo')
    @patch('backtesting.tasks.MostWinningAlgo')
    def test_extract_results_and_save_with_trades(self, mock_most_winning, mock_best_return, mock_best_perf):
        # All queries return None initially
        mock_best_perf.objects.order_by.return_value.first.return_value = None
        mock_best_return.objects.order_by.return_value.first.return_value = None
        mock_most_winning.objects.order_by.return_value.first.return_value = None

        backtest = MagicMock()
        backtest.parameters = {}

        # Valid mock Strategy model instance
        mock_strategy_model = MagicMock()
        mock_strategy_model.pk = 1
        type(mock_strategy_model).__name__ = 'Strategy'
        backtest.strategy = mock_strategy_model

        mock_cerebro = MagicMock()
        mock_cerebro.broker.getvalue.return_value = 11000

        mock_strategy = MagicMock()
        mock_results = [mock_strategy]

        mock_strategy.analyzers.sharpe_ratio.get_analysis.return_value = {'sharperatio': 1.5}
        mock_strategy.analyzers.trade_analyzer.get_analysis.return_value = {'total': {'total': 2}, 'won': {'total': 1}}
        mock_strategy.analyzers.trade_list.get_analysis.return_value = {
            'trades': [{'datetime': datetime.datetime(2020,1,1), 'type':'BUY', 'price':1.5, 'size':10, 'portfolio_value':10000}]
        }
        mock_strategy.analyzers.order_list.get_analysis.return_value = {
            'orders': [{'datetime': datetime.datetime(2020,1,1), 'type':'BUY', 'price':1.5, 'size':10, 'portfolio_value':10000}]
        }
        mock_strategy.analyzers.portfolio_value.get_analysis.return_value = {'portfolio': [10000, 11000]}

        strategy_logs = ["2020-01-01 Buy executed"]
        backtest = extract_results_and_save(backtest, mock_cerebro, mock_results, strategy_logs)

        self.assertEqual(backtest.status, 'COMPLETED')
        self.assertIn("Performance Summary", backtest.log)
        self.assertNotEqual(backtest.algo_return, 0.0)
        self.assertEqual(backtest.algo_sharpe_ratio, 1.5)
        self.assertEqual(backtest.algo_win_rate, 50.0)

        # Ensure create is called since previous bests were None
        mock_best_perf.objects.create.assert_called_once()
        mock_best_return.objects.create.assert_called_once()
        mock_most_winning.objects.create.assert_called_once()

    @patch('backtesting.tasks.BestPerformingAlgo')
    @patch('backtesting.tasks.BestReturnAlgo')
    @patch('backtesting.tasks.MostWinningAlgo')
    @patch('backtesting.tasks.get_ocl_historical_data')
    @patch('backtesting.tasks.load_strategies_and_inject_log')
    @patch('backtesting.tasks.run_cerebro_with_data_and_strategy')
    @patch('backtesting.tasks.BacktestResult')
    def test_run_backtest_success(self, mock_backtest_result, mock_run_cerebro, mock_load_strategy, mock_get_data,
                                  mock_most_winning, mock_best_return, mock_best_perf):
        # Return None for queries
        mock_best_perf.objects.order_by.return_value.first.return_value = None
        mock_best_return.objects.order_by.return_value.first.return_value = None
        mock_most_winning.objects.order_by.return_value.first.return_value = None

        backtest_instance = MagicMock()
        backtest_instance.id = 1
        mock_ocl_import = MagicMock()
        mock_ocl_import.id = 123
        backtest_instance.ocl_data_import = mock_ocl_import

        # Valid Strategy instance
        strategy_model = MagicMock()
        strategy_model.pk = 1
        type(strategy_model).__name__ = 'Strategy'
        backtest_instance.strategy = strategy_model
        backtest_instance.strategy.code = "class MyTestStrategy(bt.Strategy):\n    pass"
        backtest_instance.status = 'RUNNING'
        mock_backtest_result.objects.get.return_value = backtest_instance

        # Mock data
        mock_get_data.return_value = pd.DataFrame([{
            'Date': datetime.datetime(2020,1,1),
            'Open':1, 'High':2, 'Low':0.5, 'Close':1.5, 'Volume':1000, 'Adj_Close':1.5
        }])

        class MockUserStrategy:
            pass
        mock_load_strategy.return_value = MockUserStrategy

        # Mock run_cerebro results
        mock_cerebro = MagicMock()
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.analyzers.sharpe_ratio.get_analysis.return_value = {'sharperatio': 1.2}
        mock_strategy_instance.analyzers.trade_analyzer.get_analysis.return_value = {'total': {'total': 1}, 'won': {'total': 1}}
        mock_strategy_instance.analyzers.trade_list.get_analysis.return_value = {
            'trades': [{'datetime': datetime.datetime(2020,1,1), 'type':'BUY', 'price':1.5, 'size':10, 'portfolio_value':10000}]
        }
        mock_strategy_instance.analyzers.order_list.get_analysis.return_value = {
            'orders': [{'datetime': datetime.datetime(2020,1,1), 'type':'BUY', 'price':1.5, 'size':10, 'portfolio_value':10000}]
        }
        mock_strategy_instance.analyzers.portfolio_value.get_analysis.return_value = {'portfolio': [10000, 11200]}
        mock_cerebro.broker.getvalue.return_value = 11200
        mock_run_cerebro.return_value = (mock_cerebro, [mock_strategy_instance], 10000)

        run_backtest(backtest_instance.id)

        self.assertEqual(backtest_instance.status, 'COMPLETED')
        mock_best_perf.objects.create.assert_called_once()
        mock_best_return.objects.create.assert_called_once()
        mock_most_winning.objects.create.assert_called_once()

    @patch('backtesting.tasks.BacktestResult')
    def test_run_backtest_failure(self, mock_backtest_result):
        backtest_instance = MagicMock()
        backtest_instance.id = 1
        backtest_instance.ocl_data_import = None
        strategy_model = MagicMock()
        strategy_model.pk = 1
        type(strategy_model).__name__ = 'Strategy'
        backtest_instance.strategy = strategy_model
        backtest_instance.strategy.code = "class MyTestStrategy(bt.Strategy):\n    pass"
        mock_backtest_result.objects.get.return_value = backtest_instance

        run_backtest(backtest_instance.id)

        self.assertEqual(backtest_instance.status, 'FAILED')
        self.assertIn("No OCL data import ID found for this backtest", backtest_instance.log)


if __name__ == '__main__':
    unittest.main()
