import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import GradientBoostingClassifier
import numpy as np

def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    fast_ema = prices.ewm(span=fast, adjust=False).mean()
    slow_ema = prices.ewm(span=slow, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_bollinger_bands(prices, window=20, num_std=2):
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return upper_band, lower_band

# Download Bitcoin data
print("Downloading Bitcoin historical data...")
btc = yf.Ticker("BTC-USD").history(period="max")
print("Download complete!")

btc.index = pd.to_datetime(btc.index)

# Drop dividend and split columns if they exist
if "Dividends" in btc.columns:
    del btc["Dividends"]
if "Stock Splits" in btc.columns:
    del btc["Stock Splits"]

# Create target variable
btc["Tomorrow"] = btc["Close"].shift(-1)
btc["Target"] = (btc["Tomorrow"] > btc["Close"]).astype(int)

# Simplify the feature set to focus on stronger signals
horizons = [5, 60]  # Reduced horizons to focus on short and medium-term trends
predictors = []

for horizon in horizons:
    rolling_averages = btc.rolling(horizon).mean()
    
    ratio_column = f"Close_Ratio_{horizon}"
    btc[ratio_column] = btc["Close"] / rolling_averages["Close"]
    
    trend_column = f"Trend_{horizon}"
    btc[trend_column] = btc.shift(1).rolling(horizon).sum()["Target"]
    
    predictors += [ratio_column, trend_column]

# Add core technical indicators
btc['RSI'] = calculate_rsi(btc['Close'], window=14)
btc['MACD'], btc['Signal'] = calculate_macd(btc['Close'])

# Add strong trend indicator
btc['Strong_Uptrend'] = (btc['Close'] > btc['Close'].rolling(window=20).mean()) & \
                        (btc['Close'].rolling(window=20).mean() > btc['Close'].rolling(window=50).mean())

predictors += ['RSI', 'MACD', 'Signal', 'Strong_Uptrend']

def predict(train, test, predictors, model):
    model.fit(train[predictors], train["Target"])
    preds = model.predict_proba(test[predictors])[:,1]
    
    # Conservative threshold
    threshold = 0.8  # Only take high conviction trades
    
    # Additional trading rules
    rsi = test['RSI']
    macd = test['MACD']
    signal = test['Signal']
    strong_uptrend = test['Strong_Uptrend']
    
    # Only trade when multiple conditions align
    trading_signal = (preds >= threshold) & \
                     (rsi > 50) & (rsi < 70) & \
                     (macd > signal) & \
                     strong_uptrend
    
    preds = pd.Series(trading_signal.astype(int), index=test.index, name="Predictions")
    combined = pd.concat([test["Target"], preds], axis=1)
    return combined

# Use GradientBoostingClassifier with more conservative parameters
model = GradientBoostingClassifier(
    n_estimators=100,
    learning_rate=0.05,  # Reduced learning rate
    max_depth=3,
    subsample=0.8,  # Add randomness to make it more robust
    random_state=42
)

# Modify backtest function to use larger chunks
def backtest(data, model, predictors, start_date='2022-01-01', training_window=365, step=30):
    """
    Backtest the trading strategy using a rolling window approach.
    
    Parameters:
    - data: DataFrame containing the price data and features
    - model: The machine learning model to use
    - predictors: List of feature columns
    - start_date: Start date for backtesting
    - training_window: Number of days to use for training (default 1 year)
    - step: Number of days to predict forward
    """
    # Convert start_date to datetime and make it timezone-aware
    start_date = pd.to_datetime(start_date).tz_localize(data.index.tz)
    
    # Ensure data is sorted by date
    data = data.sort_index()
    
    # Find the index corresponding to the start date
    start_index = data.index.searchsorted(start_date)
    
    print(f"Starting backtest from {start_date}, index {start_index}")
    
    all_predictions = []
    for i in range(start_index, len(data) - step, step):
        # Define training period
        train_start = i - training_window
        train_end = i
        test_start = i
        test_end = i + step
        
        # Ensure we have enough data for training
        if train_start < 0:
            continue
            
        train = data.iloc[train_start:train_end].copy()
        test = data.iloc[test_start:test_end].copy()
        
        print(f"Training window: {train.index[0]} to {train.index[-1]}")
        print(f"Testing window:  {test.index[0]} to {test.index[-1]}")
        print("-" * 50)
        
        predictions = predict(train, test, predictors, model)
        all_predictions.append(predictions)
    
    if len(all_predictions) == 0:
        raise ValueError(f"No predictions generated. Check your start date and step size.")
    
    return pd.concat(all_predictions)

# Feature selection
X = btc[predictors].dropna()
y = btc['Target'].loc[X.index]

selector = SelectKBest(f_classif, k=10)
X_selected = selector.fit_transform(X, y)
selected_features = X.columns[selector.get_support()].tolist()

print("Selected features:", selected_features)

# Clean data and create model
btc = btc.dropna(subset=btc.columns[btc.columns != "Tomorrow"])

# Implement time series cross-validation
tscv = TimeSeriesSplit(n_splits=5)

# Make predictions
print("Starting backtesting...")
predictions = backtest(
    btc, 
    model, 
    predictors, 
    start_date='2022-01-01', 
    training_window=365,  # 1 year of training data
    step=30  # 30 days forward testing
)

# Calculate returns and create visualizations
def analyze_performance(predictions, price_data):
    predictions['Returns'] = None
    hold_returns = []
    strategy_returns = []
    current_price = None
    
    for idx in predictions.index:
        if current_price is None:
            current_price = price_data.loc[idx, 'Close']
            continue
            
        # Calculate returns
        next_price = price_data.loc[idx, 'Close']
        hold_return = (next_price - current_price) / current_price
        hold_returns.append(hold_return)
        
        # Only take positions when we predict up movement (1)
        if predictions.loc[idx, 'Predictions'] == 1:
            strategy_returns.append(hold_return)
        else:
            strategy_returns.append(0)
            
        current_price = next_price
    
    predictions['Hold_Returns'] = [0] + hold_returns
    predictions['Strategy_Returns'] = [0] + strategy_returns
    
    # Calculate cumulative returns
    predictions['Cum_Hold_Returns'] = (1 + predictions['Hold_Returns']).cumprod()
    predictions['Cum_Strategy_Returns'] = (1 + predictions['Strategy_Returns']).cumprod()
    
    return predictions

# Analyze performance
print("Analyzing trading performance...")
predictions = analyze_performance(predictions, btc)

# Create visualizations
plt.figure(figsize=(15, 10))

# Plot 1: Cumulative Returns Comparison
plt.subplot(2, 1, 1)
plt.plot(predictions.index, predictions['Cum_Hold_Returns'], label='Buy and Hold')
plt.plot(predictions.index, predictions['Cum_Strategy_Returns'], label='Strategy')
plt.title('Cumulative Returns: Strategy vs Buy and Hold')
plt.legend()
plt.yscale('log')

# Plot 2: Monthly Returns Distribution
plt.subplot(2, 1, 2)
monthly_returns = predictions['Strategy_Returns'].resample('ME').sum()
sns.histplot(monthly_returns, bins=50)
plt.title('Distribution of Monthly Strategy Returns')

plt.tight_layout()
plt.savefig('trading_performance.png')
plt.close()

# Generate performance metrics
total_trades = (predictions['Predictions'] == 1).sum()
profitable_trades = ((predictions['Strategy_Returns'] > 0) & (predictions['Predictions'] == 1)).sum()
final_return = predictions['Cum_Strategy_Returns'].iloc[-1] - 1
buy_hold_return = predictions['Cum_Hold_Returns'].iloc[-1] - 1

print("\n=== Performance Report ===")
print(f"Total number of trades: {total_trades}")
print(f"Profitable trades: {profitable_trades} ({profitable_trades/total_trades*100:.1f}%)")
print(f"Strategy total return: {final_return*100:.1f}%")
print(f"Buy & Hold return: {buy_hold_return*100:.1f}%")
print(f"Strategy Sharpe Ratio: {(predictions['Strategy_Returns'].mean() / predictions['Strategy_Returns'].std() * (252**0.5)):.2f}")

# Save predictions with returns data
predictions.to_csv("btc_predictions.csv")
print("\nPredictions and performance data saved to btc_predictions.csv")
print("Performance visualization saved as trading_performance.png")