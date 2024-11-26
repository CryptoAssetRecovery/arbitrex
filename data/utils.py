import pandas as pd
import datetime

from .binance_ocl import get_binance_ohlc_history

def get_historical_data(timeframe, asset='BTC', start_date=None, end_date=None):
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
    data = get_binance_ohlc_history(
        asset=asset,
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

def parse_row(row):
    """
    Convert a DataFrame row into a dictionary suitable for OCLPrice creation.
    
    Args:
        row: A pandas Series representing OHLCV data
        
    Returns:
        dict: A dictionary with properly formatted OHLCV data
    """
    if isinstance(row, pd.Series):
        return {
            'date': row['Date'],
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': float(row['Volume'])
        }
    elif isinstance(row, dict):
        return {
            'date': row['Date'],
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'volume': float(row['Volume'])
        }
    elif isinstance(row, str):
        try:
            date, open_price, high, low, close, volume, _ = row.split(',')
            return {
                'date': pd.to_datetime(date.strip()),
                'open': float(open_price.strip()),
                'high': float(high.strip()),
                'low': float(low.strip()),
                'close': float(close.strip()),
                'volume': float(volume.strip())
            }
        except (ValueError, IndexError) as e:
            raise ValueError(f"Unable to parse row: {row}. Error: {str(e)}")
    else:
        raise ValueError(f"Unsupported row type: {type(row)}")