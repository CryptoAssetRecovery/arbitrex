import unittest
from unittest import mock
from unittest.mock import patch
import pandas as pd
import datetime

from django.test import TestCase
from django.utils import timezone

from .utils import get_historical_data, parse_row
from .binance_ocl import get_binance_ohlc_history


class GetHistoricalDataTest(TestCase):
    @patch('data.utils.get_binance_ohlc_history')
    def test_get_historical_data_valid_timeframe(self, mock_get_binance_ohlc_history):
        # Mock data returned from Binance
        mock_data = pd.DataFrame({
            'time': [
                datetime.datetime(2023, 10, 1, 0, 0),
                datetime.datetime(2023, 10, 1, 0, 5)
            ],
            'open': [100.0, 101.0],
            'high': [110.0, 111.0],
            'low': [90.0, 91.0],
            'close': [105.0, 106.0],
            'volume': [1000.0, 1100.0]
        })
        mock_get_binance_ohlc_history.return_value = mock_data

        timeframe = '5m'
        asset = 'BTC'
        start_date = datetime.datetime(2023, 10, 1, 0, 0)
        end_date = datetime.datetime(2023, 10, 1, 0, 10)

        result = get_historical_data(timeframe, asset, start_date, end_date)

        # Assertions
        self.assertIsInstance(result, pd.DataFrame)
        self.assertListEqual(list(result.columns), ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj_Close'])
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['Date'], datetime.datetime(2023, 10, 1, 0, 0))
        self.assertEqual(result.iloc[0]['Adj_Close'], 105.0)

    def test_get_historical_data_invalid_timeframe(self):
        timeframe = '10m'  # Invalid timeframe
        asset = 'BTC'
        with self.assertRaises(ValueError) as context:
            get_historical_data(timeframe)
        self.assertIn('Invalid timeframe', str(context.exception))

    @patch('data.utils.get_binance_ohlc_history')
    def test_get_historical_data_no_data_returned(self, mock_get_binance_ohlc_history):
        mock_get_binance_ohlc_history.return_value = None
        with self.assertRaises(ValueError) as context:
            get_historical_data('5m')
        self.assertIn('No data returned from Binance', str(context.exception))

    @patch('data.utils.get_binance_ohlc_history')
    def test_get_historical_data_default_dates_timeframe_1d(self, mock_get_binance_ohlc_history):
        # Mock data
        mock_data = pd.DataFrame({
            'time': [timezone.now() - datetime.timedelta(days=700)],
            'open': [100.0],
            'high': [110.0],
            'low': [90.0],
            'close': [105.0],
            'volume': [1000.0]
        })
        mock_get_binance_ohlc_history.return_value = mock_data

        result = get_historical_data('1d')  # Defaults applied

        # Assertions
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)

    def test_parse_row_with_series(self):
        row = pd.Series({
            'Date': datetime.datetime(2023, 10, 1, 0, 0),
            'Open': 100.0,
            'High': 110.0,
            'Low': 90.0,
            'Close': 105.0,
            'Volume': 1000.0
        })
        expected_output = {
            'date': datetime.datetime(2023, 10, 1, 0, 0),
            'open': 100.0,
            'high': 110.0,
            'low': 90.0,
            'close': 105.0,
            'volume': 1000.0
        }
        result = parse_row(row)
        self.assertDictEqual(result, expected_output)

    def test_parse_row_with_dict(self):
        row = {
            'Date': datetime.datetime(2023, 10, 1, 0, 0),
            'Open': 101.0,
            'High': 111.0,
            'Low': 91.0,
            'Close': 106.0,
            'Volume': 1100.0
        }
        expected_output = {
            'date': datetime.datetime(2023, 10, 1, 0, 0),
            'open': 101.0,
            'high': 111.0,
            'low': 91.0,
            'close': 106.0,
            'volume': 1100.0
        }
        result = parse_row(row)
        self.assertDictEqual(result, expected_output)

    def test_parse_row_with_string(self):
        row = "2023-10-01 00:00:00, 102.0, 112.0, 92.0, 107.0, 1200.0, extra"
        expected_output = {
            'date': pd.to_datetime('2023-10-01 00:00:00'),
            'open': 102.0,
            'high': 112.0,
            'low': 92.0,
            'close': 107.0,
            'volume': 1200.0
        }
        result = parse_row(row)
        self.assertDictEqual(result, expected_output)

    def test_parse_row_with_invalid_string(self):
        row = "Invalid,row,data"
        with self.assertRaises(ValueError) as context:
            parse_row(row)
        self.assertIn('Unable to parse row', str(context.exception))

    def test_parse_row_with_unsupported_type(self):
        row = 12345
        with self.assertRaises(ValueError) as context:
            parse_row(row)
        self.assertIn('Unsupported row type', str(context.exception))


class GetHistoricalDataTimezoneHandlingTest(TestCase):
    @patch('data.utils.get_binance_ohlc_history')
    def test_timezone_aware_datetimes(self, mock_get_binance_ohlc_history):
        # Mock data returned from Binance with timezone-aware datetimes
        mock_data = pd.DataFrame({
            'time': [
                datetime.datetime(2023, 10, 1, 0, 0, tzinfo=datetime.timezone.utc),
                datetime.datetime(2023, 10, 1, 0, 5, tzinfo=datetime.timezone.utc)
            ],
            'open': [100.0, 101.0],
            'high': [110.0, 111.0],
            'low': [90.0, 91.0],
            'close': [105.0, 106.0],
            'volume': [1000.0, 1100.0]
        })
        mock_get_binance_ohlc_history.return_value = mock_data

        timeframe = '5m'
        asset = 'BTC'
        start_date = datetime.datetime(2023, 10, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2023, 10, 1, 0, 10, tzinfo=datetime.timezone.utc)

        result = get_historical_data(timeframe, asset, start_date, end_date)

        # Assertions to ensure timezone-naive after processing
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIsNone(result['Date'].iloc[0].tzinfo)
        self.assertIsNone(result['Date'].iloc[1].tzinfo)
