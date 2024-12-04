# Arbitrex
A platform for backtesting and analyzing trading strategies built on Backtrader.

## Starting the Django server

```bash
python manage.py runserver
```

## Starting Celery

```bash
celery -A arbitrex worker --loglevel=info
```

## Setting up the .env file

```bash
cp .env.example .env
```

## Roadmap (notes from an impromptu meeting)
- Add backtrader docs to message context (strategy editor page)
- Add confirmation strategy option to backtest
  - I'll need to implement a strategy type that can indicate which strategys are "confirmation" strategies, and which are "instigators"
 
- Add "overwrite code" functionality to each backtest result for a given strategy (roll back to a specific version of the strategy.)
- Add "strategy check" logic to run a fast backtest against the strategy before its saved (catch errors before starting a backtest?)
- Add live paper trading
