BACKTRADER_DOCS = """
# Strategy

A `Cerebro` instance is the pumping heart and controlling brain of `backtrader`. A `Strategy` is the same for the platform user.

The _Strategy’s_ expressed lifecycle in methods

Note

A strategy can be interrupted during _birth_ by raising a `StrategySkipError` exception from the module `backtrader.errors`

This will avoid going through the strategy during a backtesting. See the section `Exceptions`

1. Conception: `__init__`
    
    This is obviously invoked during instantiation: `indicators` will be created here and other needed attribute. Example:
    
    `def __init__(self):     self.sma = btind.SimpleMovingAverage(period=15)`
    
2. Birth: `start`
    
    The world (`cerebro`) tells the strategy is time to start kicking. A default empty method exists.
    
3. Childhood: `prenext`
    
    `indicators` declared during conception will have put constraints on how long the strategy needs to mature: this is called the `minimum period`. Above `__init__` created a _SimpleMovingAverage_ with a `period=15`.
    
    As long as the system has seen less than `15` bars, `prenext` will be called (the default implementation is a no-op)
    
4. Adulthood: `next`
    
    Once the system has seen `15` bars and the `SimpleMovingAverage` has a buffer large enough to start producing values, the strategy is mature enough to really execute.
    
    There is a `nextstart` method which is called exactly _once_, to mark the switch from `prenext` to `next`. The default implementation of `nextstart` is to simply call `next`
    
5. Reproduction: `None`
    
    Ok, strategies do not really reproduce. But in a sense they do, because the system will instantiate them several times if _optimizing_ (with different parameters)
    
6. Death: `stop`
    
    The system tells the strategy the time to come to a reset and put things in order has come. A default empty method exists.
    

In most cases and for regular usage patterns this will look like:

`class MyStrategy(bt.Strategy):      def __init__(self):         self.sma = btind.SimpleMovingAverage(period=15)      def next(self):         if self.sma > self.data.close:             # Do something             pass          elif self.sma < self.data.close:             # Do something else             pass`

In this snippet:

- During `__init__` an attribute is assigned an indicator
    
- The default empty `start` method is not overriden
    
- `prenext` and `nexstart` are not overriden
    
- In `next` the value of the indicator is compared against the closing price to do something
    
- The default empty `stop` method is not overriden
    

Strategies, like a trader in the real world, will get notified when events take place. Actually once per `next` cycle in the backtesting process. The strategy will:

- be notified through `notify_order(order)` of any status change in an order
    
- be notified through `notify_trade(trade)` of any opening/updating/closing trade
    
- be notified through `notify_cashvalue(cash, value)` of the current cash and portfolio in the broker
    
- be notified through `notify_fund(cash, value, fundvalue, shares)` of the current cash and portfolio in the broker and tradking of fundvalue and shares
    
- Events (implementation specific) via `notify_store(msg, *args, **kwargs)`
    
    See Cerebro for an explanation on the _store_ notifications. These will delivered to the strategy even if they have also been delivered to a `cerebro` instance (with an overriden `notify_store` method or via a _callback_)
    

And _Strategies_ also like traders have the chance to operate in the market during the `next` method to try to achieve profit with

- the `buy` method to go long or reduce/close a short position
    
- the `sell` method to go short or reduce/close a long position
    
- the `close` method to obviously close an existing position
    
- the `cancel` method to cancel a not yet executed order
    

## How to Buy/Sell/Close

The `Buy` and `Sell` methods generate orders. When invoked they return an `Order` (or subclass) instance that can be used as a reference. This order has a unique `ref` identifier that can be used for comparison

Note

Subclasses of `Order` for speficic broker implementations may carry additional _unique identifiers_ provided by the broker.

To create the order use the following parameters:

- `data` (default: `None`)
    
    For which data the order has to be created. If `None` then the first data in the system, `self.datas[0] or self.data0` (aka `self.data`) will be used
    
- `size` (default: `None`)
    
    Size to use (positive) of units of data to use for the order.
    
    If `None` the `sizer` instance retrieved via `getsizer` will be used to determine the size.
    
- `price` (default: `None`)
    
    Price to use (live brokers may place restrictions on the actual format if it does not comply to minimum tick size requirements)
    
    `None` is valid for `Market` and `Close` orders (the market determines the price)
    
    For `Limit`, `Stop` and `StopLimit` orders this value determines the trigger point (in the case of `Limit` the trigger is obviously at which price the order should be matched)
    
- `plimit` (default: `None`)
    
    Only applicable to `StopLimit` orders. This is the price at which to set the implicit _Limit_ order, once the _Stop_ has been triggered (for which `price` has been used)
    
- `exectype` (default: `None`)
    
    Possible values:
    
    - `Order.Market` or `None`. A market order will be executed with the next available price. In backtesting it will be the opening price of the next bar
        
    - `Order.Limit`. An order which can only be executed at the given `price` or better
        
    - `Order.Stop`. An order which is triggered at `price` and executed like an `Order.Market` order
        
    - `Order.StopLimit`. An order which is triggered at `price` and executed as an implicit _Limit_ order with price given by `pricelimit`
        
- `valid` (default: `None`)
    
    Possible values:
    
    - `None`: this generates an order that will not expire (aka _Good til cancel_) and remain in the market until matched or canceled. In reality brokers tend to impose a temporal limit, but this is usually so far away in time to consider it as not expiring
        
    - `datetime.datetime` or `datetime.date` instance: the date will be used to generate an order valid until the given datetime (aka _good til date_)
        
    - `Order.DAY` or `0` or `timedelta()`: a day valid until the _End of the Session_ (aka _day_ order) will be generated
        
    - `numeric value`: This is assumed to be a value corresponding to a datetime in `matplotlib` coding (the one used by `backtrader`) and will used to generate an order valid until that time (_good til date_)
        
- `tradeid` (default: `0`)
    
    This is an internal value applied by `backtrader` to keep track of overlapping trades on the same asset. This `tradeid` is sent back to the _strategy_ when notifying changes to the status of the orders.
    
- `**kwargs`: additional broker implementations may support extra parameters. `backtrader` will pass the _kwargs_ down to the created order objects
    
    Example: if the 4 order execution types directly supported by `backtrader` are not enough, in the case of for example _Interactive Brokers_ the following could be passed as _kwargs_:
    
    `orderType='LIT', lmtPrice=10.0, auxPrice=9.8`
    
    This would override the settings created by `backtrader` and generate a `LIMIT IF TOUCHED` order with a _touched_ price of 9.8 and a _limit_ price of 10.0.
    

## Information Bits:

- A Strategy has a _length_ which is always equal to that of the main data (`datas[0]`) and can of course be gotten with `len(self)`
    
    `next` can be called without changes in _length_ if data is being replayed or a live feed is being passed and new ticks for the same point in time (length) are arriving
    

## Member Attributes:

- `env`: the cerebro entity in which this Strategy lives
    
- `datas`: array of data feeds which have been passed to cerebro
    
    - `data/data0` is an alias for datas[0]
        
    - `dataX` is an alias for datas[X]
        
    
    _data feeds_ can also be accessed by name (see the reference) if one has been assigned to it
    
- `dnames`: an alternative to reach the data feeds by name (either with `[name]` or with `.name` notation)
    
    For example if resampling a data like this:
    
    `... data0 = bt.feeds.YahooFinanceData(datname='YHOO', fromdate=..., name='days') cerebro.adddata(data0) cerebro.resampledata(data0, timeframe=bt.TimeFrame.Weeks, name='weeks') ...`
    
    Later in the strategy one can create indicators on each like this:
    
    `... smadays = bt.ind.SMA(self.dnames.days, period=30)  # or self.dnames['days'] smaweeks = bt.ind.SMA(self.dnames.weeks, period=10)  # or self.dnames['weeks'] ...`
    
- `broker`: reference to the broker associated to this strategy (received from cerebro)
    
- `stats`: list/named tuple-like sequence holding the Observers created by cerebro for this strategy
    
- `analyzers`: list/named tuple-like sequence holding the Analyzers created by cerebro for this strategy
    
- `position`: actually a property which gives the current position for `data0`.
    
    Methods to retrieve all possitions are available (see the reference)
    

## Member Attributes (meant for statistics/observers/analyzers):

- `_orderspending`: list of orders which will be notified to the strategy before `next` is called
    
- `_tradespending`: list of trades which will be notified to the strategy before `next` is called
    
- `_orders`: list of order which have been already notified. An order can be several times in the list with different statuses and different execution bits. The list is menat to keep the history.
    
- `_trades`: list of order which have been already notified. A trade can be several times in the list just like an order.
    

Note

Bear in mind that `prenext`, `nextstart` and `next` can be called several times for the same point in time (ticks updating prices for the daily bar, when a daily timeframe is in use)

## Reference: Strategy

#### class backtrader.Strategy(*args, **kwargs)

Base class to be subclassed for user defined strategies.

#### next()

This method will be called for all remaining data points when the minimum period for all datas/indicators have been meet.

#### nextstart()

This method will be called once, exactly when the minimum period for all datas/indicators have been meet. The default behavior is to call next

#### prenext()

This method will be called before the minimum period of all datas/indicators have been meet for the strategy to start executing

#### start()

Called right before the backtesting is about to be started.

#### stop()

Called right before the backtesting is about to be stopped

#### notify_order(order)

Receives an order whenever there has been a change in one

#### notify_trade(trade)

Receives a trade whenever there has been a change in one

#### notify_cashvalue(cash, value)

Receives the current fund value, value status of the strategy’s broker

#### notify_fund(cash, value, fundvalue, shares)

Receives the current cash, value, fundvalue and fund shares

#### notify_store(msg, *args, **kwargs)

Receives a notification from a store provider

#### buy(data=None, size=None, price=None, plimit=None, exectype=None, valid=None, tradeid=0, oco=None, trailamount=None, trailpercent=None, parent=None, transmit=True, **kwargs)

Create a buy (long) order and send it to the broker

- `data` (default: `None`)
    
    For which data the order has to be created. If `None` then the first data in the system, `self.datas[0] or self.data0` (aka `self.data`) will be used
    
- `size` (default: `None`)
    
    Size to use (positive) of units of data to use for the order.
    
    If `None` the `sizer` instance retrieved via `getsizer` will be used to determine the size.
    
- `price` (default: `None`)
    
    Price to use (live brokers may place restrictions on the actual format if it does not comply to minimum tick size requirements)
    
    `None` is valid for `Market` and `Close` orders (the market determines the price)
    
    For `Limit`, `Stop` and `StopLimit` orders this value determines the trigger point (in the case of `Limit` the trigger is obviously at which price the order should be matched)
    
- `plimit` (default: `None`)
    
    Only applicable to `StopLimit` orders. This is the price at which to set the implicit _Limit_ order, once the _Stop_ has been triggered (for which `price` has been used)
    
- `trailamount` (default: `None`)
    
    If the order type is StopTrail or StopTrailLimit, this is an absolute amount which determines the distance to the price (below for a Sell order and above for a buy order) to keep the trailing stop
    
- `trailpercent` (default: `None`)
    
    If the order type is StopTrail or StopTrailLimit, this is a percentage amount which determines the distance to the price (below for a Sell order and above for a buy order) to keep the trailing stop (if `trailamount` is also specified it will be used)
    
- `exectype` (default: `None`)
    
    Possible values:
    
    - `Order.Market` or `None`. A market order will be executed with the next available price. In backtesting it will be the opening price of the next bar
        
    - `Order.Limit`. An order which can only be executed at the given `price` or better
        
    - `Order.Stop`. An order which is triggered at `price` and executed like an `Order.Market` order
        
    - `Order.StopLimit`. An order which is triggered at `price` and executed as an implicit _Limit_ order with price given by `pricelimit`
        
    - `Order.Close`. An order which can only be executed with the closing price of the session (usually during a closing auction)
        
    - `Order.StopTrail`. An order which is triggered at `price` minus `trailamount` (or `trailpercent`) and which is updated if the price moves away from the stop
        
    - `Order.StopTrailLimit`. An order which is triggered at `price` minus `trailamount` (or `trailpercent`) and which is updated if the price moves away from the stop
        
- `valid` (default: `None`)
    
    Possible values:
    
    - `None`: this generates an order that will not expire (aka _Good till cancel_) and remain in the market until matched or canceled. In reality brokers tend to impose a temporal limit, but this is usually so far away in time to consider it as not expiring
        
    - `datetime.datetime` or `datetime.date` instance: the date will be used to generate an order valid until the given datetime (aka _good till date_)
        
    - `Order.DAY` or `0` or `timedelta()`: a day valid until the _End of the Session_ (aka _day_ order) will be generated
        
    - `numeric value`: This is assumed to be a value corresponding to a datetime in `matplotlib` coding (the one used by `backtrader`) and will used to generate an order valid until that time (_good till date_)
        
- `tradeid` (default: `0`)
    
    This is an internal value applied by `backtrader` to keep track of overlapping trades on the same asset. This `tradeid` is sent back to the _strategy_ when notifying changes to the status of the orders.
    
- `oco` (default: `None`)
    
    Another `order` instance. This order will become part of an OCO (Order Cancel Others) group. The execution of one of the orders, immediately cancels all others in the same group
    
- `parent` (default: `None`)
    
    Controls the relationship of a group of orders, for example a buy which is bracketed by a high-side limit sell and a low side stop sell. The high/low side orders remain inactive until the parent order has been either executed (they become active) or is canceled/expires (the children are also canceled) bracket orders have the same size
    
- `transmit` (default: `True`)
    
    Indicates if the order has to be **transmitted**, ie: not only placed in the broker but also issued. This is meant for example to control bracket orders, in which one disables the transmission for the parent and 1st set of children and activates it for the last children, which triggers the full placement of all bracket orders.
    
- `**kwargs`: additional broker implementations may support extra parameters. `backtrader` will pass the _kwargs_ down to the created order objects
    
    Example: if the 4 order execution types directly supported by `backtrader` are not enough, in the case of for example _Interactive Brokers_ the following could be passed as _kwargs_:
    
    `orderType='LIT', lmtPrice=10.0, auxPrice=9.8`
    
    This would override the settings created by `backtrader` and generate a `LIMIT IF TOUCHED` order with a _touched_ price of 9.8 and a _limit_ price of 10.0.
    
- **Returns**
    
    - the submitted order

#### sell(data=None, size=None, price=None, plimit=None, exectype=None, valid=None, tradeid=0, oco=None, trailamount=None, trailpercent=None, parent=None, transmit=True, **kwargs)

To create a selll (short) order and send it to the broker

See the documentation for `buy` for an explanation of the parameters

Returns: the submitted order

#### close(data=None, size=None, **kwargs)

Counters a long/short position closing it

See the documentation for `buy` for an explanation of the parameters

Note

- `size`: automatically calculated from the existing position if not provided (default: `None`) by the caller

Returns: the submitted order

#### cancel(order)

Cancels the order in the broker

#### buy_bracket(data=None, size=None, price=None, plimit=None, exectype=2, valid=None, tradeid=0, trailamount=None, trailpercent=None, oargs={}, stopprice=None, stopexec=3, stopargs={}, limitprice=None, limitexec=2, limitargs={}, **kwargs)

Create a bracket order group (low side - buy order - high side). The default behavior is as follows:

- Issue a **buy** order with execution `Limit`
    
- Issue a _low side_ bracket **sell** order with execution `Stop`
    
- Issue a _high side_ bracket **sell** order with execution `Limit`.
    

See below for the different parameters

- `data` (default: `None`)
    
    For which data the order has to be created. If `None` then the first data in the system, `self.datas[0] or self.data0` (aka `self.data`) will be used
    
- `size` (default: `None`)
    
    Size to use (positive) of units of data to use for the order.
    
    If `None` the `sizer` instance retrieved via `getsizer` will be used to determine the size.
    
    Note
    
    The same size is applied to all 3 orders of the bracket
    
- `price` (default: `None`)
    
    Price to use (live brokers may place restrictions on the actual format if it does not comply to minimum tick size requirements)
    
    `None` is valid for `Market` and `Close` orders (the market determines the price)
    
    For `Limit`, `Stop` and `StopLimit` orders this value determines the trigger point (in the case of `Limit` the trigger is obviously at which price the order should be matched)
    
- `plimit` (default: `None`)
    
    Only applicable to `StopLimit` orders. This is the price at which to set the implicit _Limit_ order, once the _Stop_ has been triggered (for which `price` has been used)
    
- `trailamount` (default: `None`)
    
    If the order type is StopTrail or StopTrailLimit, this is an absolute amount which determines the distance to the price (below for a Sell order and above for a buy order) to keep the trailing stop
    
- `trailpercent` (default: `None`)
    
    If the order type is StopTrail or StopTrailLimit, this is a percentage amount which determines the distance to the price (below for a Sell order and above for a buy order) to keep the trailing stop (if `trailamount` is also specified it will be used)
    
- `exectype` (default: `bt.Order.Limit`)
    
    Possible values: (see the documentation for the method `buy`
    
- `valid` (default: `None`)
    
    Possible values: (see the documentation for the method `buy`
    
- `tradeid` (default: `0`)
    
    Possible values: (see the documentation for the method `buy`
    
- `oargs` (default: `{}`)
    
    Specific keyword arguments (in a `dict`) to pass to the main side order. Arguments from the default `**kwargs` will be applied on top of this.
    
- `**kwargs`: additional broker implementations may support extra parameters. `backtrader` will pass the _kwargs_ down to the created order objects
    
    Possible values: (see the documentation for the method `buy`
    
    Note
    
    This `kwargs` will be applied to the 3 orders of a bracket. See below for specific keyword arguments for the low and high side orders
    
- `stopprice` (default: `None`)
    
    Specific price for the _low side_ stop order
    
- `stopexec` (default: `bt.Order.Stop`)
    
    Specific execution type for the _low side_ order
    
- `stopargs` (default: `{}`)
    
    Specific keyword arguments (in a `dict`) to pass to the low side order. Arguments from the default `**kwargs` will be applied on top of this.
    
- `limitprice` (default: `None`)
    
    Specific price for the _high side_ stop order
    
- `stopexec` (default: `bt.Order.Limit`)
    
    Specific execution type for the _high side_ order
    
- `limitargs` (default: `{}`)
    
    Specific keyword arguments (in a `dict`) to pass to the high side order. Arguments from the default `**kwargs` will be applied on top of this.
    

High/Low Side orders can be suppressed by using:

- `limitexec=None` to suppress the _high side_
    
- `stopexec=None` to suppress the _low side_
    
- **Returns**
    
    - A list containing the 3 orders [order, stop side, limit side]
        
    - If high/low orders have been suppressed the return value will still contain 3 orders, but those suppressed will have a value of `None`
        

#### sell_bracket(data=None, size=None, price=None, plimit=None, exectype=2, valid=None, tradeid=0, trailamount=None, trailpercent=None, oargs={}, stopprice=None, stopexec=3, stopargs={}, limitprice=None, limitexec=2, limitargs={}, **kwargs)

Create a bracket order group (low side - buy order - high side). The default behavior is as follows:

- Issue a **sell** order with execution `Limit`
    
- Issue a _high side_ bracket **buy** order with execution `Stop`
    
- Issue a _low side_ bracket **buy** order with execution `Limit`.
    

See `bracket_buy` for the meaning of the parameters

High/Low Side orders can be suppressed by using:

- `stopexec=None` to suppress the _high side_
    
- `limitexec=None` to suppress the _low side_
    
- **Returns**
    
    - A list containing the 3 orders [order, stop side, limit side]
        
    - If high/low orders have been suppressed the return value will still contain 3 orders, but those suppressed will have a value of `None`
        

#### order_target_size(data=None, target=0, **kwargs)

Place an order to rebalance a position to have final size of `target`

The current `position` size is taken into account as the start point to achieve `target`

- If `target` > `pos.size` -> buy `target - pos.size`
    
- If `target` < `pos.size` -> sell `pos.size - target`
    

It returns either:

- The generated order

or

- `None` if no order has been issued (`target == position.size`)

#### order_target_value(data=None, target=0.0, price=None, **kwargs)

Place an order to rebalance a position to have final value of `target`

The current `value` is taken into account as the start point to achieve `target`

- If no `target` then close postion on data
    
- If `target` > `value` then buy on data
    
- If `target` < `value` then sell on data
    

It returns either:

- The generated order

or

- `None` if no order has been issued

#### order_target_percent(data=None, target=0.0, **kwargs)

Place an order to rebalance a position to have final value of `target` percentage of current portfolio `value`

`target` is expressed in decimal: `0.05` -> `5%`

It uses `order_target_value` to execute the order.

_Example_

- `target=0.05` and portfolio value is `100`
    
- The `value` to be reached is `0.05 * 100 = 5`
    
- `5` is passed as the `target` value to `order_target_value`
    

The current `value` is taken into account as the start point to achieve `target`

The `position.size` is used to determine if a position is `long` / `short`

- If `target` > `value`
    
    - buy if `pos.size >= 0` (Increase a long position)
    - sell if `pos.size < 0` (Increase a short position)
- If `target` < `value`
    
    - sell if `pos.size >= 0` (Decrease a long position)
    - buy if `pos.size < 0` (Decrease a short position)

It returns either:

- The generated order

or

- `None` if no order has been issued (`target == position.size`)

#### getsizer()

Returns the sizer which is in used if automatic statke calculation is used

Also available as `sizer`

#### setsizer(sizer)

Replace the default (fixed stake) sizer

#### getsizing(data=None, isbuy=True)

Return the stake calculated by the sizer instance for the current situation

#### getposition(data=None, broker=None)

Returns the current position for a given data in a given broker.

If both are None, the main data and the default broker will be used

A property `position` is also available

#### getpositionbyname(name=None, broker=None)

Returns the current position for a given name in a given broker.

If both are None, the main data and the default broker will be used

A property `positionbyname` is also available

#### getpositionsbyname(broker=None)

Returns the current by name positions directly from the broker

If the given `broker` is None, the default broker will be used

A property `positionsbyname` is also available

#### getdatanames()

Returns a list of the existing data names

#### getdatabyname(name)

Returns a given data by name using the environment (cerebro)

#### add_timer(when, offset=datetime.timedelta(0), repeat=datetime.timedelta(0), weekdays=[], weekcarry=False, monthdays=[], monthcarry=True, allow=None, tzdata=None, cheat=False, *args, **kwargs)

Note

Can be called during `__init__` or `start`

Schedules a timer to invoke either a specified callback or the `notify_timer` of one or more strategies.

- **Parameters**
    
    **when** (_-_) – can be
    
    - `datetime.time` instance (see below `tzdata`)
        
    - `bt.timer.SESSION_START` to reference a session start
        
    - `bt.timer.SESSION_END` to reference a session end
        
    - `offset` which must be a `datetime.timedelta` instance
        
    
    Used to offset the value `when`. It has a meaningful use in combination with `SESSION_START` and `SESSION_END`, to indicated things like a timer being called `15 minutes` after the session start.
    
    - `repeat` which must be a `datetime.timedelta` instance
        
        Indicates if after a 1st call, further calls will be scheduled within the same session at the scheduled `repeat` delta
        
        Once the timer goes over the end of the session it is reset to the original value for `when`
        
    - `weekdays`: a **sorted** iterable with integers indicating on which days (iso codes, Monday is 1, Sunday is 7) the timers can be actually invoked
        
        If not specified, the timer will be active on all days
        
    - `weekcarry` (default: `False`). If `True` and the weekday was not seen (ex: trading holiday), the timer will be executed on the next day (even if in a new week)
        
    - `monthdays`: a **sorted** iterable with integers indicating on which days of the month a timer has to be executed. For example always on day _15_ of the month
        
        If not specified, the timer will be active on all days
        
    - `monthcarry` (default: `True`). If the day was not seen (weekend, trading holiday), the timer will be executed on the next available day.
        
    - `allow` (default: `None`). A callback which receives a datetime.date` instance and returns `True` if the date is allowed for timers or else returns `False`
        
    - `tzdata` which can be either `None` (default), a `pytz` instance or a `data feed` instance.
        
        `None`: `when` is interpreted at face value (which translates to handling it as if it where UTC even if it’s not)
        
        `pytz` instance: `when` will be interpreted as being specified in the local time specified by the timezone instance.
        
        `data feed` instance: `when` will be interpreted as being specified in the local time specified by the `tz` parameter of the data feed instance.
        
        Note
        
        If `when` is either `SESSION_START` or `SESSION_END` and `tzdata` is `None`, the 1st _data feed_ in the system (aka `self.data0`) will be used as the reference to find out the session times.
        
    - `cheat` (default `False`) if `True` the timer will be called before the broker has a chance to evaluate the orders. This opens the chance to issue orders based on opening price for example right before the session starts
        
    - `*args`: any extra args will be passed to `notify_timer`
        
    - `**kwargs`: any extra kwargs will be passed to `notify_timer`
        

Return Value:

- The created timer

#### notify_timer(timer, when, *args, **kwargs)

Receives a timer notification where `timer` is the timer which was returned by `add_timer`, and `when` is the calling time. `args` and `kwargs` are any additional arguments passed to `add_timer`

The actual `when` time can be later, but the system may have not be able to call the timer before. This value is the timer value and no the system time.

-----
# Sizers

- Smart Staking

A _Strategy_ offers methods to trade, namely: `buy`, `sell` and `close`. Let’s see the signature of `buy`:

`def buy(self, data=None,         size=None, price=None, plimit=None,         exectype=None, valid=None, tradeid=0, **kwargs):`

Notice that `size` has a default value of `None` if the caller does not specify it. This is where _Sizers_ play an important role:

- `size=None` requests that the _Strategy_ asks its _Sizer_ for the actual stake

This obviously implies that _Strategies_ have a _Sizer_: Yes, indeed!. The background machinery adds a default sizer to a _Strategy_ if the user has not added one. The default _Sizer_ added to a _strategy_ is `SizerFix`. The initial lines of the definition:

`class SizerFix(SizerBase):     params = (('stake', 1),)`

It is easy to guess that this _Sizer_ simply _buys/sells_ using a `stake` of `1` units (be it shares, contracts, …)

## Using _Sizers_

### From _Cerebro_

_Sizers_ can be added via _Cerebro_ with 2 different methods:

- `addsizer(sizercls, *args, **kwargs)`
    
    Adds a _Sizer_ that will be applied to any strategy added to _cerebro_. This is, so to to say, the default _Sizer_. Example:
    
    `cerebro = bt.Cerebro() cerebro.addsizer(bt.sizers.SizerFix, stake=20)  # default sizer for strategies`
    
- `addsizer_byidx(idx, sizercls, *args, **kwargs)`
    
    The _Sizer_ will only be added to the _Strategy_ referenced by `idx`
    
    This `idx` can be gotten as return value from `addstrategy`. As in:
    
    `cerebro = bt.Cerebro() cerebro.addsizer(bt.sizers.SizerFix, stake=20)  # default sizer for strategies  idx = cerebro.addstrategy(MyStrategy, myparam=myvalue) cerebro.addsizer_byidx(idx, bt.sizers.SizerFix, stake=5)  cerebro.addstrategy(MyOtherStrategy)`
    
    In this example:
    
    - A default _Sizer_ has been added to the system. This one applies to all strategies which don’t have a specific _Sizer_ assigned
        
    - For _MyStrategy_ and after collecting its insertion _idx_, a specific sizer (changing the `stake` param) is added
        
    - A 2nd strategy, _MyOtherStrategy_, is added to the system. No specific _Sizer_ is added for it
        
    - This means that:
        
        - _MyStrategy_ will finally have an internal specific _Sizer_
            
        - _MyOtherStrategy_ will get the default sizer
            

Note

_default_ doesn’t mean that that the strategies share a single _Sizer_ instance. Each _strategy_ receives a different instance of the _default_ sizer

To share a single instance, the sizer to be shared should be a singleton class. How to define one is outside of the scope of _backtrader_

### From _Strategy_

The _Strategy_ class offers an API: `setsizer` and `getsizer` (and a _property_ `sizer`) to manage the _Sizer_. The signatures:

- `def setsizer(self, sizer)`: it takes an already instantiated _Sizer_
    
- `def getsizer(self)`: returns the current _Sizer_ instance
    
- `sizer` it is the property which can be directly _get/set_
    

In this scenario the _Sizer_ can be for example:

- Passed to the strategy as a parameter
    
- Be set during `__init__` using the property `sizer` or `setsizer` as in:
    
    `class MyStrategy(bt.Strategy):     params = (('sizer', None),)      def __init__(self):         if self.p.sizer is not None:             self.sizer = self.p.sizer`
    
    This would for example allow to create a _Sizer_ at the same level as the _cerebro_ calls are happening and pass it as a parameter to all strategies that go in the system, which effectevily allows sharing a _Sizer_
    

## _Sizer_ Development

Doing it is easy:

1. Subclass from `backtrader.Sizer`
    
    This gives you access to `self.strategy` and `self.broker` although it shouldn’t be needed in most cases. Things that can be accessed with the `broker`
    
    - data’s position with `self.strategy.getposition(data)`
        
    - complete portfolio value through `self.broker.getvalue()`
        
        Notice this could of course also be done with `self.strategy.broker.getvalue()`
        
    
    Some of the other things are already below as arguments
    
2. Override the method `_getsizing(self, comminfo, cash, data, isbuy)`
    
    - `comminfo`: The CommissionInfo instance that contains information about the commission for the data and allows calculation of position value, operation cost, commision for the operation
        
    - `cash`: current available cash in the _broker_
        
    - `data`: target of the operation
        
    - `isbuy`: will be `True` for _buy_ operations and `False` for _sell_ operations
        
    
    This method returns the desired `size` for the _buy/sell_ operation
    
    The returned sign is not relevant, ie: if the operation is a _sell_ operation (`isbuy` will be `False`) the method may return `5` or `-5`. Only the absolute value will be used by the _sell_ operation.
    
    `Sizer` has already gone to the `broker` and requested the _commission information_ for the given _data_, the actual _cash_ level and provides a direct reference to the _data_ which is the target of the operation
    

Let’s go for the definition of the `FixedSize` sizer:

`import backtrader as bt  class FixedSize(bt.Sizer):     params = (('stake', 1),)      def _getsizing(self, comminfo, cash, data, isbuy):         return self.params.stake`

This is pretty simple in that the _Sizer_ makes no calculations and the parameters are just there.

But the mechanism should allow the construction of complex _sizing_ (aka _positioning_) systems to manage the stakes when entering/exiting the market.

Another example: **A position rerverser**:

`class FixedRerverser(bt.FixedSize):      def _getsizing(self, comminfo, cash, data, isbuy):         position = self.broker.getposition(data)         size = self.p.stake * (1 + (position.size != 0))         return size`

This one builds on the existing `FixedSize` to inherit the `params` and overrides `_getsizing` to:

- Get the `position` of the _data_ via the attribute `broker`
    
- Use `position.size` to decide if to double the fixed stake
    
- Return the calculated value
    

This would remove the burden from the _Strategy_ to decide if a position has to be reversed or opened, the _Sizer_ is in control and can at any time be replaced without affecting the logic.

## Practical _Sizer_ Applicability

Wihtout considering complex sizing algorithms, two different sizers can be used to _turn a strategy from Long-Only to Long-Short_. Simply by changing the _Sizer_ in the _cerebro_ execution, the strategy will change behavior. A very simple `close` crosses `SMA` algorithm:

`class CloseSMA(bt.Strategy):     params = (('period', 15),)      def __init__(self):         sma = bt.indicators.SMA(self.data, period=self.p.period)         self.crossover = bt.indicators.CrossOver(self.data, sma)      def next(self):         if self.crossover > 0:             self.buy()          elif self.crossover < 0:             self.sell()`

Notice how the strategy doesn’t consider the current _position_ (by looking at `self.position`) to decide whether a _buy_ or _sell_ has to actually be done. Only the _signal_ from the `CrossOver` is considered. The _Sizers_ will be in charge of everything.

This sizer will take care of only returning a _non-zero_ size when selling if a position is already open:

`class LongOnly(bt.Sizer):     params = (('stake', 1),)      def _getsizing(self, comminfo, cash, data, isbuy):       if isbuy:           return self.p.stake        # Sell situation       position = self.broker.getposition(data)       if not position.size:           return 0  # do not sell if nothing is open        return self.p.stake`

Putting it all together (and assuming _backtrader_ has already been imported and a _data_ has been added to the system):

`... cerebro.addstrategy(CloseSMA) cerebro.addsizer(LongOnly) ... cerebro.run() ...`

The chart (from the sample included in the sources to test this).

[![image](https://www.backtrader.com/docu/sizers/sizer-long-only.png)](https://www.backtrader.com/docu/sizers/sizer-long-only.png)

The _Long-Short_ version simply changes the _Sizer_ to be the `FixedReverser` shown above:

`... cerebro.addstrategy(CloseSMA) cerebro.addsizer(FixedReverser) ... cerebro.run() ...`

The output chart.

[![image](https://www.backtrader.com/docu/sizers/sizer-fixedreverser.png)](https://www.backtrader.com/docu/sizers/sizer-fixedreverser.png)

Notice the differences:

- The number of _trades_ has duplicated
    
- The cash level never goes back to be the _value_ because the strategy is _always_ in the market
    

Both approaches are anyhow negative, but this is only an example.

## _bt.Sizer_ Reference

#### class backtrader.Sizer()

This is the base class for _Sizers_. Any _sizer_ should subclass this and override the `_getsizing` method

Member Attribs:

- `strategy`: will be set by the strategy in which the sizer is working
    
    Gives access to the entire api of the strategy, for example if the actual data position would be needed in `_getsizing`:
    
    `position = self.strategy.getposition(data)`
    
- `broker`: will be set by the strategy in which the sizer is working
    
    Gives access to information some complex sizers may need like portfolio value, ..
    

#### _getsizing(comminfo, cash, data, isbuy)

This method has to be overriden by subclasses of Sizer to provide the sizing functionality

Params:

``* `comminfo`: The CommissionInfo instance that contains   information about the commission for the data and allows   calculation of position value, operation cost, commision for the   operation  * `cash`: current available cash in the *broker*  * `data`: target of the operation  * `isbuy`: will be `True` for *buy* operations and `False`   for *sell* operations``

The method has to return the actual size (an int) to be executed. If `0` is returned nothing will be executed.

The absolute value of the returned value will be used

-----
## Indicators:
### Absolute Strength Histogram:
- The indicator will work with the raw priced passed to it in a data feed. If the user wants to run the indicator on an average price it can pass it, instead of passing the raw price.
- The 0.5 multiplier in the `RSI` mode, will be a parameter
- The moving average won't be selected with any kind of _integer_. In _backtrader_ one can pass the actual desired moving average as a parameter.
- The smoothing moving average, unless specified as a parameter, will be the same as the moving average already in use in the indicator
- The `pointsize` will not be used unless the user specifies a value for it as a parameter.

And here the implementation
```
class ASH(bt.Indicator):
    alias = ('AbsoluteStrengthOscilator',)

    lines = ('ash', 'bulls', 'bears',)  # output lines

    # customize the plotting of the *ash* line
    plotlines = dict(ash=dict(_method='bar', alpha=0.33, width=0.66))

    RSI, STOCH = range(0, 2)  # enum values for the parameter mode

    params = dict(
        period=9,
        smoothing=2,
        mode=RSI,
        rsifactor=0.5,
        movav=bt.ind.WMA,  # WeightedMovingAverage
        smoothav=None,  # use movav if not specified
        pointsize=None,  # use only if specified
    )

    def __init__(self):
        # Start calcs according to selected mode
        if self.p.mode == self.RSI:
            p0p1 = self.data - self.data(-1)  # used twice below
            half_abs_p0p1 = self.p.rsifactor * abs(p0p1)  # used twice below

            bulls = half_abs_p0p1 + p0p1
            bears = half_abs_p0p1 - p0p1
        else:
            bulls = self.data - bt.ind.Lowest(self.data, period=self.p.period)
            bears = bt.ind.Highest(self.data, period=self.p.period) - self.data

        avbulls = self.p.movav(bulls, period=self.p.period)
        avbears = self.p.movav(bears, period=self.p.period)

        # choose smoothing average and smooth the already averaged values
        smoothav = self.p.smoothav or self.p.movav  # choose smoothav
        smoothbulls = smoothav(avbulls, period=self.p.smoothing)
        smoothbears = smoothav(avbears, period=self.p.smoothing)

        if self.p.pointsize:  # apply only if it makes sense
            smoothbulls /= self.p.pointsize
            smoothbears /= self.p.pointsize

        # Assign the final values to the output lines
        self.l.bulls = smoothbulls
        self.l.bears = smoothbears
        self.l.ash = smoothbulls - smoothbears
```

### Connors RSI:
Google provides two references for the Connors RSI indicator:
• [Nirvana Systems - Connors RSI](https://www.nirvanasystems.com/ultimate-indicator-connors-rsi/)
• [TradingView - Connors RSI](https://www.tradingview.com/wiki/Connors_RSI_(CRSI))
Both agree on the formula but differ in terminology. The Connors RSI is calculated as:
`CRSI(3, 2, 100) = [RSI(3) + RSI(Streak, 2) + PercentRank(100)] / 3`
  
  **Note:**
TradingView incorrectly suggests using ROC (“Rate of Change”) instead of PctRank (“Percentage Rank”).

**Definition of** Streak **(or** UpDown **in TradingView):**
• Consecutive days the price closes higher/lower than the previous day.
• Resets to 0 if the price remains unchanged.
• Positive for upward streaks, negative for downward streaks.

With the correct formula, PercentRank, and a clear definition of Streak, implementing Connors RSI should be straightforward.
```
class Streak(bt.ind.PeriodN):
    '''
    Keeps a counter of the current upwards/downwards/neutral streak
    '''
    lines = ('streak',)
    params = dict(period=2)  # need prev/cur days (2) for comparisons

    curstreak = 0

    def next(self):
        d0, d1 = self.data[0], self.data[-1]

        if d0 > d1:
            self.l.streak[0] = self.curstreak = max(1, self.curstreak + 1)
        elif d0 < d1:
            self.l.streak[0] = self.curstreak = min(-1, self.curstreak - 1)
        else:
            self.l.streak[0] = self.curstreak = 0


class ConnorsRSI(bt.Indicator):
    '''
    Calculates the ConnorsRSI as:
        - (RSI(per_rsi) + RSI(Streak, per_streak) + PctRank(per_rank)) / 3
    '''
    lines = ('crsi',)
    params = dict(prsi=3, pstreak=2, prank=100)

    def __init__(self):
        # Calculate the components
        rsi = bt.ind.RSI(self.data, period=self.p.prsi)

        streak = Streak(self.data)
        rsi_streak = bt.ind.RSI(streak, period=self.p.pstreak)

        prank = bt.ind.PercentRank(self.data, period=self.p.prank)

        # Apply the formula
        self.l.crsi = (rsi + rsi_streak + prank) / 3.0
```

### Donchian Channels:
```
class DonchianChannels(bt.Indicator):
    '''
    Params Note:
      - `lookback` (default: -1)
        If `-1`, the bars to consider will start 1 bar in the past and the
        current high/low may break through the channel.
        If `0`, the current prices will be considered for the Donchian
        Channel. This means that the price will **NEVER** break through the
        upper/lower channel bands.
    '''

    alias = ('DCH', 'DonchianChannel',)

    lines = ('dcm', 'dch', 'dcl',)  # dc middle, dc high, dc low
    params = dict(
        period=20,
        lookback=-1,  # consider current bar or not
    )

    plotinfo = dict(subplot=False)  # plot along with data
    plotlines = dict(
        dcm=dict(ls='--'),  # dashed line
        dch=dict(_samecolor=True),  # use same color as prev line (dcm)
        dcl=dict(_samecolor=True),  # use same color as prev line (dch)
    )

    def __init__(self):
        hi, lo = self.data.high, self.data.low
        if self.p.lookback:  # move backwards as needed
            hi, lo = hi(self.p.lookback), lo(self.p.lookback)

        self.l.dch = bt.ind.Highest(hi, period=self.p.period)
        self.l.dcl = bt.ind.Lowest(lo, period=self.p.period)
        self.l.dcm = (self.l.dch + self.l.dcl) / 2.0  # avg of the above
```

### Money Flow Indicator:
```
class MFI(bt.Indicator):
    lines = ('mfi',)
    params = dict(period=14)

    alias = ('MoneyFlowIndicator',)

    def __init__(self):
        tprice = (self.data.close + self.data.low + self.data.high) / 3.0
        mfraw = tprice * self.data.volume

        flowpos = bt.ind.SumN(mfraw * (tprice > tprice(-1)), period=self.p.period)
        flowneg = bt.ind.SumN(mfraw * (tprice < tprice(-1)), period=self.p.period)

        mfiratio = bt.ind.DivByZero(flowpos, flowneg, zero=100.0)
        self.l.mfi = 100.0 - 100.0 / (1.0 + mfiratio)
```

### Stochastic (Generic):
_backtrader_ already includes a `Stochastic` indicator (including a variant which displays the three calculated lines and not just the usual two `%k` and `%d` lines)

But such indicator assumes that the data source for the calculations has `high`, `low` and `close` components. This is so because the original definition uses those components.

If one wants to use different components, a first approach could be creating a data feed which stores the different components in the `high`, `low` and `close` lines of the data feed.

But a much more straightforward approach is to have a _Generic_ `Stochastic` indicator which takes three (3) data components and uses them as if they were the `high`, `low` and `close` components.

The code below does that and adds a nice touch by allowing customization of the moving average for the 2nd smoothing.
```
class Stochastic_Generic(bt.Indicator):
    '''
    This generic indicator doesn't assume the data feed has the components
    ``high``, ``low`` and ``close``. It needs three data sources passed to it,
    which whill considered in that order. (following the OHLC standard naming)
    '''
    lines = ('k', 'd', 'dslow',)
    params = dict(
        pk=14,
        pd=3,
        pdslow=3,
        movav=bt.ind.SMA,
        slowav=None,
    )

    def __init__(self):
        # Get highest from period k from 1st data
        highest = bt.ind.Highest(self.data0, period=self.p.pk)
        # Get lowest from period k from 2nd data
        lowest = bt.ind.Lowest(self.data1, period=self.p.pk)

        # Apply the formula to get raw K
        kraw = 100.0 * (self.data2 - lowest) / (highest - lowest)

        # The standard k in the indicator is a smoothed versin of K
        self.l.k = k = self.p.movav(kraw, period=self.p.pd)

        # Smooth k => d
        slowav = self.p.slowav or self.p.movav  # chose slowav
        self.l.d = slowav(k, period=self.p.pdslow)
```

### StochRSI:
_Stockcharts_ and _Investopedia_ have literature on this indicator.
- [StockCharts - StochRSI (ChartSchool)](https://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:stochrsi)
- [Investopedia - Stochastic RSI - StochRSI Definition](https://www.investopedia.com/terms/s/stochrsi.asp)

With the formula being:
`StochRSI = (RSI - min(RSI, period)) / (max(RSI, period) - min(RSI, period))`

In theory the period to calculate the `RSI` is the same that will later be applied to find out the minimum and maximum values of the `RSI`. That means that if the chosen period is `14` (de-facto standard) for the `RSI`, the total look-back period for the indicator will be `28`

**Note:**
The actual look-back period will be a bit longer, because a 14-period `RSI` has a longer effective look-back period of `15`, as the comparison of the closing prices of the 1st two periods is needed to kick-start the calculations

In any case, _backtrader_ does calculate all the needed look-back and warm-up periods automatically.

Considering that the following are built-in indicators in _backtrader_:
- `RSI`
- `Lowest` (aka `MaxN`)
- `Highest` (aka `MinN`)

developing the `StochRSI` according to the formula seen above is straightforward.
```
class StochRSI(bt.Indicator):
    lines = ('stochrsi',)
    params = dict(
        period=14,  # to apply to RSI
        pperiod=None,  # if passed apply to HighestN/LowestN, else "period"
    )

    def __init__(self):
        rsi = bt.ind.RSI(self.data, period=self.p.period)

        pperiod = self.p.pperiod or self.p.period
        maxrsi = bt.ind.Highest(rsi, period=pperiod)
        minrsi = bt.ind.Lowest(rsi, period=pperiod)

        self.l.stochrsi = (rsi - minrsi) / (maxrsi - minrsi)
```
-----
# TA-Lib Indicators

Even if _backtrader_ offers an already high number of built-in indicators and developing an indicator is mostly a matter of defining the inputs, outputs and writing the formula in a natural manner, some people want to use _TA-LIB_. Some of the reasons:

- Indicator _X_ is in the library and not in _backtrader_ (the author would gladly accept a request)
    
- _TA-LIB_ behavior is well known and people trust good old things
    

In order to satisfy each and every taste, _TA-LIB_ integration is offered.

## Requirements

- [Python wrapper for TA-Lib](https://github.com/mrjbq7/ta-lib)
    
- Any dependencies needed by it (for example _numpy_)
    

The installation details are on the _GitHub_ repository

## Using _ta-lib_

As easy as using any of the indicators already built-in in _backtrader_. Example of a _Simple Moving Average_. First the _backtrader_ one:

`import backtrader as bt  class MyStrategy(bt.Strategy):     params = (('period', 20),)      def __init__(self):         self.sma = bt.indicators.SMA(self.data, period=self.p.period)         ...  ...`

Now the _ta-lib_ example:

`import backtrader as bt  class MyStrategy(bt.Strategy):     params = (('period', 20),)      def __init__(self):         self.sma = bt.talib.SMA(self.data, timeperiod=self.p.period)         ...  ...`

Et voilá! Of course the _params_ for the _ta-lib_ indicators are defined by the library itself and not by _backtrader_. In this case the _SMA_ in _ta-lib_ takes a parameter named `timeperiod` to defined the size of the operating window.

For indicators that require more than one input, for example the _Stochastic_:

`import backtrader as bt  class MyStrategy(bt.Strategy):     params = (('period', 20),)      def __init__(self):         self.stoc = bt.talib.STOCH(self.data.high, self.data.low, self.data.close,                                    fastk_period=14, slowk_period=3, slowd_period=3)          ...  ...`

Notice how `high`, `low` and `close` have been individually passed. One could always pass `open` instead of `low` (or any other data series) and experiment.

The _ta-lib_ indicator documentation is automatically parsed and added to the _backtrader_ docs. You may also check the _ta-lib_ source code/docs. Or adittionally do:

`print(bt.talib.SMA.__doc__)`

Which in this case outputs:

`SMA([input_arrays], [timeperiod=30])  Simple Moving Average (Overlap Studies)  Inputs:     price: (any ndarray) Parameters:     timeperiod: 30 Outputs:     real`

Which offers some information:

- Which _Input_ is to be expected (_DISREGARD the ``ndarray`` comment_ because backtrader manages the conversions in the background)
    
- Which _parameters_ and which default values
    
- Which output _lines_ the indicator actually offers
    

### Moving Averages and MA_Type

To select a specific _moving average_ for indicators like `bt.talib.STOCH`, the standard _ta-lib_ `MA_Type` is accesible with `backtrader.talib.MA_Type`. For example:

`import backtrader as bt print('SMA:', bt.talib.MA_Type.SMA) print('T3:', bt.talib.MA_Type.T3)`

## Plotting ta-lib indicators

Just as with regular usage, there is nothing special to do to plot the _ta-lib_ indicators.

Note

Indicators which output a _CANDLE_ (all those looking for a candlestick pattern) deliver a binary output: either 0 or 100. In order to avoid adding a `subplot` to the chart, there is an automated plotting translation to plot them over the _data_ at the point in time in which the pattern was recognized.

## Examples and comparisons

The following are plots comparing the outputs of some _ta-lib_ indicators against the equivalent built-in indicators in _backtrader_. To consider:

- The _ta-lib_ indicators get a `TA_` prefix on the plot. This is specifically done by the sample to help the user spot which is which
    
- _Moving Averages_ (if both deliver the same result) will be plotted _ON_ top of the other existing _Moving Average_. The two indicators cannot be seen separately and the test is a pass if that’s the case.
    
- All samples include a `CDLDOJI` indicator as a reference
    

### KAMA (Kaufman Moving Average)

This is the 1st example because it is the only (from all indicators which the sample directly compare) that has a difference:

- The initial values of the the samples are not the same
    
- At some point in time, the values converge and both _KAMA_ implementations have the same behavior.
    

After having analyzed the _ta-lib_ source code:

- The implementation in _ta-lib_ makes a non-industry standard choice for the 1st values of the _KAMA_.
    
    The choice can be seen in the source code quoting from the source code): _The yesterday price is used here as the previous KAMA._
    

_backtrader_ does the usual choice which is the same as for example the one from _Stockcharts_:

- [KAMA at StockCharts](http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:kaufman_s_adaptive_moving_average)
    
    _Since we need an initial value to start the calculation, the first KAMA is just a simple moving average_
    

Hence the difference. Furthermore:

- The _ta-lib_ `KAMA` implementation doesn’t allow specifying the `fast` and `slow` periods for the adjustment of the _scalable constant_ defined by _Kaufman_.

Sample execution:

`$ ./talibtest.py --plot --ind kama`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-kama.png)](https://www.backtrader.com/docu/talib/ta-lib-kama.png)

### SMA

`$ ./talibtest.py --plot --ind sma`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-sma.png)](https://www.backtrader.com/docu/talib/ta-lib-sma.png)

### EMA

`$ ./talibtest.py --plot --ind ema`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-ema.png)](https://www.backtrader.com/docu/talib/ta-lib-ema.png)

### Stochastic

`$ ./talibtest.py --plot --ind stoc`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-stoc.png)](https://www.backtrader.com/docu/talib/ta-lib-stoc.png)

### RSI

`$ ./talibtest.py --plot --ind rsi`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-rsi.png)](https://www.backtrader.com/docu/talib/ta-lib-rsi.png)

### MACD

`$ ./talibtest.py --plot --ind macd`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-macd.png)](https://www.backtrader.com/docu/talib/ta-lib-macd.png)

### Bollinger Bands

`$ ./talibtest.py --plot --ind bollinger`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-bollinger.png)](https://www.backtrader.com/docu/talib/ta-lib-bollinger.png)

### AROON

Note that _ta-lib_ chooses to put the _down_ line first and the colours are inverted when compared with the _backtrader_ built-in indicator.

`$ ./talibtest.py --plot --ind aroon`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-aroon.png)](https://www.backtrader.com/docu/talib/ta-lib-aroon.png)

### Ultimate Oscillator

`$ ./talibtest.py --plot --ind ultimate`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-ultimate.png)](https://www.backtrader.com/docu/talib/ta-lib-ultimate.png)

### Trix

`$ ./talibtest.py --plot --ind trix`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-trix.png)](https://www.backtrader.com/docu/talib/ta-lib-trix.png)

### ADXR

Here _backtrader_ offers both the `ADX` and `ADXR` lines.

`$ ./talibtest.py --plot --ind adxr`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-adxr.png)](https://www.backtrader.com/docu/talib/ta-lib-adxr.png)

### DEMA

`$ ./talibtest.py --plot --ind dema`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-dema.png)](https://www.backtrader.com/docu/talib/ta-lib-dema.png)

### TEMA

`$ ./talibtest.py --plot --ind tema`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-tema.png)](https://www.backtrader.com/docu/talib/ta-lib-tema.png)

### PPO

Here _backtrader_ offers not only the `ppo` line, but a more traditional `macd` approach.

`$ ./talibtest.py --plot --ind ppo`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-ppo.png)](https://www.backtrader.com/docu/talib/ta-lib-ppo.png)

### WilliamsR

`$ ./talibtest.py --plot --ind williamsr`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-williamsr.png)](https://www.backtrader.com/docu/talib/ta-lib-williamsr.png)

### ROC

All indicators show have exactly the same shape, but how to track _momentum_ or _rate of change_ has several definitions

`$ ./talibtest.py --plot --ind roc`

Output

[![image](https://www.backtrader.com/docu/talib/ta-lib-roc.png)](https://www.backtrader.com/docu/talib/ta-lib-roc.png)

## Sample Usage

`$ ./talibtest.py --help usage: talibtest.py [-h] [--data0 DATA0] [--fromdate FROMDATE]                     [--todate TODATE]                     [--ind {sma,ema,stoc,rsi,macd,bollinger,aroon,ultimate,trix,kama,adxr,dema,tema,ppo,williamsr,roc}]                     [--no-doji] [--use-next] [--plot [kwargs]]  Sample for ta-lib  optional arguments:   -h, --help            show this help message and exit   --data0 DATA0         Data to be read in (default:                         ../../datas/yhoo-1996-2015.txt)   --fromdate FROMDATE   Starting date in YYYY-MM-DD format (default:                         2005-01-01)   --todate TODATE       Ending date in YYYY-MM-DD format (default: 2006-12-31)   --ind {sma,ema,stoc,rsi,macd,bollinger,aroon,ultimate,trix,kama,adxr,dema,tema,ppo,williamsr,roc}                         Which indicator pair to show together (default: sma)   --no-doji             Remove Doji CandleStick pattern checker (default:                         False)   --use-next            Use next (step by step) instead of once (batch)                         (default: False)   --plot [kwargs], -p [kwargs]                         Plot the read data applying any kwargs passed For                         example (escape the quotes if needed): --plot                         style="candle" (to plot candles) (default: None)`

## Sample Code

`from __future__ import (absolute_import, division, print_function,                         unicode_literals)  import argparse import datetime  import backtrader as bt  class TALibStrategy(bt.Strategy):     params = (('ind', 'sma'), ('doji', True),)      INDS = ['sma', 'ema', 'stoc', 'rsi', 'macd', 'bollinger', 'aroon',             'ultimate', 'trix', 'kama', 'adxr', 'dema', 'ppo', 'tema',             'roc', 'williamsr']      def __init__(self):         if self.p.doji:             bt.talib.CDLDOJI(self.data.open, self.data.high,                              self.data.low, self.data.close)          if self.p.ind == 'sma':             bt.talib.SMA(self.data.close, timeperiod=25, plotname='TA_SMA')             bt.indicators.SMA(self.data, period=25)         elif self.p.ind == 'ema':             bt.talib.EMA(timeperiod=25, plotname='TA_SMA')             bt.indicators.EMA(period=25)         elif self.p.ind == 'stoc':             bt.talib.STOCH(self.data.high, self.data.low, self.data.close,                            fastk_period=14, slowk_period=3, slowd_period=3,                            plotname='TA_STOCH')              bt.indicators.Stochastic(self.data)          elif self.p.ind == 'macd':             bt.talib.MACD(self.data, plotname='TA_MACD')             bt.indicators.MACD(self.data)             bt.indicators.MACDHisto(self.data)         elif self.p.ind == 'bollinger':             bt.talib.BBANDS(self.data, timeperiod=25,                             plotname='TA_BBANDS')             bt.indicators.BollingerBands(self.data, period=25)          elif self.p.ind == 'rsi':             bt.talib.RSI(self.data, plotname='TA_RSI')             bt.indicators.RSI(self.data)          elif self.p.ind == 'aroon':             bt.talib.AROON(self.data.high, self.data.low, plotname='TA_AROON')             bt.indicators.AroonIndicator(self.data)          elif self.p.ind == 'ultimate':             bt.talib.ULTOSC(self.data.high, self.data.low, self.data.close,                             plotname='TA_ULTOSC')             bt.indicators.UltimateOscillator(self.data)          elif self.p.ind == 'trix':             bt.talib.TRIX(self.data, timeperiod=25,  plotname='TA_TRIX')             bt.indicators.Trix(self.data, period=25)          elif self.p.ind == 'adxr':             bt.talib.ADXR(self.data.high, self.data.low, self.data.close,                           plotname='TA_ADXR')             bt.indicators.ADXR(self.data)          elif self.p.ind == 'kama':             bt.talib.KAMA(self.data, timeperiod=25, plotname='TA_KAMA')             bt.indicators.KAMA(self.data, period=25)          elif self.p.ind == 'dema':             bt.talib.DEMA(self.data, timeperiod=25, plotname='TA_DEMA')             bt.indicators.DEMA(self.data, period=25)          elif self.p.ind == 'ppo':             bt.talib.PPO(self.data, plotname='TA_PPO')             bt.indicators.PPO(self.data, _movav=bt.indicators.SMA)          elif self.p.ind == 'tema':             bt.talib.TEMA(self.data, timeperiod=25, plotname='TA_TEMA')             bt.indicators.TEMA(self.data, period=25)          elif self.p.ind == 'roc':             bt.talib.ROC(self.data, timeperiod=12, plotname='TA_ROC')             bt.talib.ROCP(self.data, timeperiod=12, plotname='TA_ROCP')             bt.talib.ROCR(self.data, timeperiod=12, plotname='TA_ROCR')             bt.talib.ROCR100(self.data, timeperiod=12, plotname='TA_ROCR100')             bt.indicators.ROC(self.data, period=12)             bt.indicators.Momentum(self.data, period=12)             bt.indicators.MomentumOscillator(self.data, period=12)          elif self.p.ind == 'williamsr':             bt.talib.WILLR(self.data.high, self.data.low, self.data.close,                            plotname='TA_WILLR')             bt.indicators.WilliamsR(self.data)  def runstrat(args=None):     args = parse_args(args)      cerebro = bt.Cerebro()      dkwargs = dict()     if args.fromdate:         fromdate = datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')         dkwargs['fromdate'] = fromdate      if args.todate:         todate = datetime.datetime.strptime(args.todate, '%Y-%m-%d')         dkwargs['todate'] = todate      data0 = bt.feeds.YahooFinanceCSVData(dataname=args.data0, **dkwargs)     cerebro.adddata(data0)      cerebro.addstrategy(TALibStrategy, ind=args.ind, doji=not args.no_doji)      cerebro.run(runcone=not args.use_next, stdstats=False)     if args.plot:         pkwargs = dict(style='candle')         if args.plot is not True:  # evals to True but is not True             npkwargs = eval('dict(' + args.plot + ')')  # args were passed             pkwargs.update(npkwargs)          cerebro.plot(**pkwargs)  def parse_args(pargs=None):      parser = argparse.ArgumentParser(         formatter_class=argparse.ArgumentDefaultsHelpFormatter,         description='Sample for sizer')      parser.add_argument('--data0', required=False,                         default='../../datas/yhoo-1996-2015.txt',                         help='Data to be read in')      parser.add_argument('--fromdate', required=False,                         default='2005-01-01',                         help='Starting date in YYYY-MM-DD format')      parser.add_argument('--todate', required=False,                         default='2006-12-31',                         help='Ending date in YYYY-MM-DD format')      parser.add_argument('--ind', required=False, action='store',                         default=TALibStrategy.INDS[0],                         choices=TALibStrategy.INDS,                         help=('Which indicator pair to show together'))      parser.add_argument('--no-doji', required=False, action='store_true',                         help=('Remove Doji CandleStick pattern checker'))      parser.add_argument('--use-next', required=False, action='store_true',                         help=('Use next (step by step) '                               'instead of once (batch)'))      # Plot options     parser.add_argument('--plot', '-p', nargs='?', required=False,                         metavar='kwargs', const=True,                         help=('Plot the read data applying any kwargs passed\n'                               '\n'                               'For example (escape the quotes if needed):\n'                               '\n'                               '  --plot style="candle" (to plot candles)\n'))      if pargs is not None:         return parser.parse_args(pargs)      return parser.parse_args()  if __name__ == '__main__':     runstrat()`
"""