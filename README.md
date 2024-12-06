# Arbitrex
A platform for backtesting and analyzing trading strategies built on Backtrader.

## Prerequisites

- Docker
- Python 3.10+

## Building the Docker Containers

```bash
sudo docker compose up --build
```
*Note: Remember to migrate the database the first time you run the containers (sudo docker compose exec web python3 manage.py migrate).*

## Setting up the .env file

```bash
cp .env.example .env
```

I hope Im not forgetting anything, Im doing this from memory at like 12 AM lol.

## Roadmap (notes from an impromptu meeting)
- TODO: Complete and fix up the test suite

- TODO: Add parameter options to the backtest configuration page
    - And the backtest results page

- TODO: Add checksum for hyper params in strategy

- TODO: Add automatic hyper parameter optimization

- TODO: Add live paper trading
- TODO: Add statistical arbitrage ability (multiple OCL pairs)
- TODO: Add public flags for strategies + backtest results
- TODO: Add system prompt management + doc importing for strategy editing
- TODO: Find a blockchain analytics API 
- TODO: Explore modular "mini strategies" that can be used to compose more complex strategies