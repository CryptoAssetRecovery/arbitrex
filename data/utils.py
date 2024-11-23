import yfinance as yf
import pandas as pd

def get_historical_data(start_date='2023-01-01', end_date='2024-11-20'):
    data = yf.download('BTC-USD', start=start_date, end=end_date)
    return data