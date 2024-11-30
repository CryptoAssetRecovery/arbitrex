# backtesting/analyzers.py

import backtrader as bt

class PortfolioValueAnalyzer(bt.Analyzer):
    """Tracks portfolio value over time."""
    def __init__(self):
        self.values = []

    def next(self):
        dt = self.datas[0].datetime.datetime(0)
        value = self.strategy.broker.getvalue()
        self.values.append({
            'time': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio_value': value
        })

    def get_analysis(self):
        return self.values

class TradeListAnalyzer(bt.Analyzer):
    """Captures detailed trade information."""
    def __init__(self):
        self.trades = []

    def notify_trade(self, trade):
        if trade.isclosed:
            trade_details = {
                'datetime': self.strategy.datas[0].datetime.datetime(0),
                'type': 'buy' if trade.size > 0 else 'sell',
                'price': trade.price,
                'size': trade.size,
                'portfolio_value': self.strategy.broker.getvalue()
            }
            self.trades.append(trade_details)

    def get_analysis(self):
        return {'trades': self.trades}

class OrderListAnalyzer(bt.Analyzer):
    """Captures detailed order execution information."""
    def __init__(self):
        self.orders = []

    def notify_order(self, order):
        if order.status in [order.Completed]:
            try:
                # Get the current datetime from the strategy
                dt = self.strategy.datetime.datetime()
                
                order_details = {
                    'datetime': dt,  # Using strategy's current datetime
                    'type': 'buy' if order.isbuy() else 'sell',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'portfolio_value': self.strategy.broker.getvalue()
                }
                self.orders.append(order_details)
                print(f"Order Executed: {order_details}")  # Debug statement
            except Exception as e:
                print(f"Error in OrderListAnalyzer.notify_order: {str(e)}")
                print(f"Order status: {order.status}")
                print(f"Order info: {order}")

    def get_analysis(self):
        return {'orders': self.orders}