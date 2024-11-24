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
