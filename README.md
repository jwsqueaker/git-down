# Portfolio Analysis & Tracking Dashboard

A comprehensive portfolio analysis dashboard with macro economic indicators, risk-adjusted performance metrics, and correlation analysis.

## Features

### Portfolio Analysis
- **Performance Metrics**: Total return, annualized return, volatility
- **Risk-Adjusted Returns**:
  - Sharpe Ratio
  - Sortino Ratio
  - Treynor Ratio
  - Information Ratio
  - Calmar Ratio
  - Maximum Drawdown
- **Asset Allocation**: Visual breakdown of portfolio holdings
- **Historical Performance**: Time-series analysis with interactive charts

### Macro Economic Indicators
- GDP Growth
- Inflation (CPI)
- Unemployment Rate
- Interest Rates (10-Year Treasury)
- Fed Funds Rate
- VIX (Market Volatility Index)

### Benchmark Comparison
- Compare portfolio against major indices (S&P 500, Nasdaq, etc.)
- Relative performance analysis
- Beta and correlation metrics

### LTCMA Analysis
- Upload JP Morgan Long-Term Capital Market Assumptions
- Correlation analysis between portfolio and asset class assumptions
- Forward-looking return expectations

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your FRED API key
   ```

3. **Get FRED API Key** (Free):
   - Visit: https://fred.stlouisfed.org/docs/api/api_key.html
   - Sign up and get your API key
   - Add to `.env` file

## Usage

### Run the Dashboard:
```bash
streamlit run app.py
```

### Upload Portfolio:
1. Prepare CSV with columns: `symbol`, `shares`, `purchase_date`, `purchase_price`
2. Use the upload feature in the dashboard sidebar
3. View real-time portfolio analysis

### Upload LTCMA Data:
1. Download JP Morgan LTCMA data
2. Format as CSV with columns: `asset_class`, `expected_return`, `volatility`, `correlation_data`
3. Upload through the dashboard

## Data Sources

- **Market Data**: Yahoo Finance (via yfinance)
- **Macro Indicators**: FRED (Federal Reserve Economic Data)
- **Portfolio Positions**: CSV upload
- **LTCMA Data**: Manual CSV upload

## Project Structure

```
portfolio-dashboard/
├── app.py                      # Main Streamlit application
├── config/
│   └── settings.py             # Configuration and environment variables
├── models/
│   ├── database.py             # Database models and schema
│   └── portfolio.py            # Portfolio data models
├── services/
│   ├── data_fetcher.py         # Market data and macro indicators
│   ├── portfolio_calculator.py # Portfolio metrics and analytics
│   └── risk_metrics.py         # Risk-adjusted return calculations
├── utils/
│   ├── csv_handler.py          # CSV upload and processing
│   └── helpers.py              # Utility functions
└── requirements.txt
```

## License

MIT
