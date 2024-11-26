import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def get_binance_ohlc_history(asset='BTC', interval='1h', start_date=None, end_date=None):
    """
    Fetch historical BTC/USD OHLC data from Binance US
    
    asset: Asset to fetch data for (optional)
    interval: Time interval - options:
        '1m', '3m', '5m', '15m', '30m'  # minutes
        '1h', '2h', '4h', '6h', '8h', '12h'  # hours
        '1d', '3d'  # days
        '1w', '1M'  # weeks, months
    start_date: datetime object for start of data (optional)
    end_date: datetime object for end of data (optional)
    """
    
    endpoint = "https://api.binance.us/api/v3/klines"
    all_data = []

    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=365)  # Default to 1 year

    # Convert dates to milliseconds timestamps
    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)
    current_start = start_ts
    
    while current_start < end_ts:
        params = {
            'symbol': f'{asset}USDT',
            'interval': interval,
            'startTime': current_start,
            'endTime': end_ts,
            'limit': 1000
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            # Process timestamps for logging
            batch_start = datetime.fromtimestamp(data[0][0] / 1000)
            batch_end = datetime.fromtimestamp(data[-1][0] / 1000)
            # print(f"Fetched from {batch_start} to {batch_end}")
            
            all_data.extend(data)
            
            # Update start time for next batch
            # Add 1 to avoid duplicate candle
            current_start = int(data[-1][0]) + 1
            
            # Respect rate limits
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            # print(f"Error fetching data: {e}")
            time.sleep(5)  # Wait longer on error
            continue
    
    if not all_data:
        return None
        
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close',
        'volume', 'close_time', 'quote_volume', 'trades',
        'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Convert price and volume columns to float
    price_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume',
                 'taker_buy_volume', 'taker_buy_quote_volume']
    df[price_cols] = df[price_cols].astype(float)
    
    # Clean up the dataframe
    df = df.drop(['close_time', 'ignore'], axis=1)
    df = df.rename(columns={'timestamp': 'time'})
    
    # print(f"\nFinal dataset:")
    # print(f"Start: {df['time'].min()}")
    # print(f"End: {df['time'].max()}")
    # print(f"Total periods: {len(df)}")
    
    return df