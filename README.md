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
- TODO: Add "overwrite code" functionality to each backtest result for a given strategy (roll back to a specific version of the strategy.)
- TODO: Add live paper trading
