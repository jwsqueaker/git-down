# Frequently Asked Questions (FAQ)

## General Questions

### What is this dashboard for?

This is a comprehensive portfolio analysis tool that helps you:
- Track your investment portfolio performance
- Calculate risk-adjusted return metrics (Sharpe, Sortino, etc.)
- Compare against market benchmarks (S&P 500, Nasdaq, etc.)
- Monitor macro economic indicators
- Analyze correlations and diversification
- Compare against JP Morgan LTCMA expectations

### Is this free to use?

Yes! The dashboard is completely free and open-source. The data sources are also free:
- Yahoo Finance (via yfinance) - no API key needed
- FRED API - free with registration
- Your portfolio data is stored locally

### Do I need programming knowledge?

No. Just upload a CSV file with your portfolio positions and the dashboard does the rest. Basic Excel/Sheets knowledge is helpful for preparing the CSV file.

### Is my data secure?

Yes. All data is stored locally on your computer in a SQLite database. No data is sent to external servers except when fetching market prices and economic indicators from public APIs.

## Setup & Installation

### What do I need to get started?

1. Python 3.8 or higher
2. The dependencies (install with `pip install -r requirements.txt`)
3. A FRED API key (free, optional but recommended)
4. Your portfolio data in CSV format

### How do I get a FRED API key?

1. Visit https://fred.stlouisfed.org/
2. Create a free account
3. Go to https://fred.stlouisfed.org/docs/api/api_key.html
4. Click "Request API Key"
5. Copy the key and add it to your `.env` file

### Do I need a FRED API key?

It's optional but highly recommended. Without it, you won't be able to view macro economic indicators. All other features will work fine.

### The installation is failing. What should I do?

1. Verify Python version: `python --version` (needs 3.8+)
2. Update pip: `pip install --upgrade pip`
3. Install dependencies one by one to identify the problem
4. Check the INSTALLATION.md for platform-specific issues
5. Consider using a virtual environment

## Portfolio Upload

### What format should my portfolio CSV be in?

Required columns:
- `symbol`: Ticker symbol (e.g., AAPL, MSFT)
- `shares`: Number of shares you own
- `purchase_date`: When you bought it (YYYY-MM-DD)
- `purchase_price`: Price per share when purchased

Example:
```csv
symbol,shares,purchase_date,purchase_price
AAPL,100,2020-01-15,75.00
MSFT,50,2020-03-20,160.00
SPY,25,2021-06-10,420.00
```

### Where can I find ticker symbols?

- Use Yahoo Finance: https://finance.yahoo.com/
- Search for your stock and the ticker is shown prominently
- For ETFs, use their standard ticker (e.g., SPY, QQQ, VOO)

### Can I include mutual funds?

Yes, if they have a ticker symbol. Most mutual funds traded on exchanges have tickers. For private mutual funds without tickers, you may need to use a proxy ETF.

### Can I track cryptocurrency?

Yes! Use the crypto ticker from Yahoo Finance:
- Bitcoin: BTC-USD
- Ethereum: ETH-USD
- Others: Check Yahoo Finance for the correct format

### Can I track multiple portfolios?

Currently, the dashboard shows one portfolio at a time. To track multiple:
1. Create separate CSV files for each portfolio
2. Upload them individually to compare
3. Or combine all positions into one CSV

### What if I don't remember my purchase date/price?

Use your brokerage statements to find:
- Purchase confirmations
- Transaction history
- Cost basis reports

If truly unavailable, you can estimate, but metrics will be less accurate.

## Features & Functionality

### What metrics are available?

**Return Metrics:**
- Total Return
- Annualized Return

**Risk Metrics:**
- Volatility (Standard Deviation)
- Maximum Drawdown
- VaR (Value at Risk)
- CVaR (Conditional VaR)

**Risk-Adjusted Metrics:**
- Sharpe Ratio
- Sortino Ratio
- Treynor Ratio
- Information Ratio
- Calmar Ratio

**Benchmark-Relative:**
- Alpha
- Beta
- Tracking Error
- Correlation

### What's a good Sharpe Ratio?

- < 1: Not great - not being rewarded enough for risk
- 1-2: Good - acceptable risk-adjusted returns
- 2-3: Very good - excellent risk-adjusted performance
- > 3: Exceptional - outstanding performance

### What does Beta mean?

Beta measures how much your portfolio moves with the market:
- Beta = 1: Moves exactly with the market
- Beta > 1: More volatile than the market (amplifies gains and losses)
- Beta < 1: Less volatile than the market (more stable)
- Beta < 0: Moves opposite to the market (rare)

### What is Alpha?

Alpha is your excess return beyond what your Beta would predict:
- Positive Alpha: Outperforming expectations (good!)
- Zero Alpha: Performing as expected given your risk
- Negative Alpha: Underperforming (bad)

### How often is data updated?

- **Market prices**: Fetched in real-time when you load/refresh the dashboard
- **Macro indicators**: FRED data updates on the indicator's schedule (daily to monthly)
- **Portfolio metrics**: Calculated in real-time based on current prices

### Which benchmarks can I compare against?

Built-in benchmarks:
- S&P 500 (^GSPC)
- Nasdaq (^IXIC)
- Dow Jones (^DJI)
- Russell 2000 (^RUT)

You can also use any ticker as a benchmark.

## LTCMA Data

### What is LTCMA?

LTCMA = Long-Term Capital Market Assumptions. JP Morgan publishes annual forward-looking return expectations for various asset classes (stocks, bonds, real estate, etc.) over 10-15 year horizons.

### Where do I get LTCMA data?

1. JP Morgan publishes LTCMA reports annually
2. Download from JP Morgan Asset Management website
3. Extract the data for asset classes
4. Format as CSV using the template in the dashboard

### Is LTCMA data required?

No, it's completely optional. The LTCMA tab is for advanced users who want to compare their portfolio against institutional forward-looking expectations.

### What can I do with LTCMA data?

- See expected returns by asset class
- Compare your portfolio allocation to professional forecasts
- Identify potential over/underweight positions
- Understand risk-return tradeoffs across asset classes

## Troubleshooting

### The dashboard is slow

**Solutions:**
- Reduce the time period for analysis
- Use fewer positions
- Close unnecessary browser tabs
- Ensure good internet connection for data fetching

### I get "No data found" for a symbol

**Possible causes:**
- Invalid ticker symbol - verify on Yahoo Finance
- Stock is delisted or no longer traded
- Ticker format is wrong (check for -USD suffix for crypto)

**Solutions:**
- Verify the ticker on finance.yahoo.com
- For international stocks, use the correct exchange suffix (e.g., AAPL.L for London)

### Macro indicators aren't showing

**Check:**
1. FRED_API_KEY is in your .env file
2. The key is valid (test at https://fred.stlouisfed.org/)
3. You haven't exceeded rate limits (5000 requests/day)
4. Your internet connection is working

### Prices seem wrong

**Possible causes:**
- Stock had a split - yfinance should adjust automatically
- Ticker symbol changed - update your portfolio
- Data issue with Yahoo Finance - try again later

### The correlation matrix is empty

**Requirements:**
- At least 2 positions in portfolio
- Sufficient historical data overlap
- Valid ticker symbols

If still empty, try extending the analysis period (use 1Y or 3Y instead of 1M).

## Advanced Usage

### Can I export my data?

The dashboard shows all data in tables that can be copied. For programmatic export, you can:
- Access the SQLite database directly
- Modify the code to add export buttons
- Use pandas to export DataFrames to CSV

### Can I customize the risk-free rate?

Currently it's set to 4.5% in the code. You can modify `config/settings.py` to change it:
```python
RISK_FREE_RATE = 0.045  # Change this value
```

### Can I add custom benchmarks?

Yes! Edit `config/settings.py` and add to the BENCHMARKS dictionary:
```python
BENCHMARKS = {
    'S&P 500': '^GSPC',
    'My Custom Index': 'TICKER_HERE'
}
```

### Can I add more macro indicators?

Yes! Find the FRED series ID and add to `config/settings.py`:
```python
MACRO_INDICATORS = {
    'Your Indicator Name': 'FRED_SERIES_ID'
}
```

Browse available series at https://fred.stlouisfed.org/

### Can I run this on a server?

Yes! Streamlit can be deployed to:
- Streamlit Cloud (free tier available)
- Heroku
- AWS/GCP/Azure
- Any server with Python

See Streamlit deployment docs: https://docs.streamlit.io/streamlit-community-cloud/get-started

### Can I schedule automated reports?

The current version is interactive. For automated reports, you could:
- Modify the code to save charts/metrics as files
- Set up a cron job to run the analysis
- Email results using Python's smtplib

This would require custom development.

## Best Practices

### How far back should I analyze?

- **1M-3M**: Recent trends, short-term momentum
- **1Y**: Annual performance, tax planning
- **3Y**: Medium-term strategy evaluation
- **5Y+**: Long-term investing (recommended for retirement accounts)

### How often should I check my portfolio?

Depends on your strategy:
- **Day traders**: Multiple times daily
- **Active investors**: Daily or weekly
- **Long-term investors**: Monthly or quarterly
- **Retirement accounts**: Quarterly or annually

Over-checking can lead to emotional decisions!

### What's a well-diversified portfolio?

Look for:
- Low correlations between positions (< 0.7)
- Multiple sectors represented
- Mix of asset classes (stocks, bonds, etc.)
- Beta around 0.8-1.0 for balanced risk

The correlation matrix helps identify diversification.

### Should I worry about drawdown?

Maximum drawdown shows your worst historical loss. Consider:
- Can you emotionally handle this loss again?
- Is it within your risk tolerance?
- 20-30% is normal for stock portfolios
- > 50% suggests very high risk

## Data Privacy & Security

### Is my portfolio data shared anywhere?

No. Your portfolio data stays on your computer. The only external connections are:
- Yahoo Finance (to get stock prices)
- FRED API (to get macro data)

These services don't receive your portfolio positions.

### What data does Yahoo Finance see?

Only the ticker symbols you're requesting prices for. Not your shares, purchase prices, or total value.

### Can I use this offline?

Partially. You can view uploaded data, but you need internet to:
- Fetch current prices
- Get historical data
- Update macro indicators

### Where is my data stored?

In a SQLite database file called `portfolio.db` in the project directory. You can back it up by copying this file.

## Contributing & Support

### Can I contribute to the project?

Yes! This is open-source. You can:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

### I found a bug. What should I do?

1. Check if it's already reported
2. Create a detailed bug report including:
   - What you were doing
   - Error messages
   - Your Python version
   - Steps to reproduce

### Can I request features?

Yes! Open an issue describing:
- The feature you want
- Why it would be useful
- How it should work

## Legal & Disclaimer

### Is this financial advice?

**NO.** This is an analytical tool only. It does not provide:
- Investment recommendations
- Buy/sell advice
- Financial planning
- Tax guidance

Always consult a qualified financial advisor for investment decisions.

### Can I use this for professional purposes?

The tool is provided as-is without warranty. For professional use:
- Verify all calculations independently
- Understand the limitations
- Don't rely solely on automated metrics
- Consider professional-grade tools for client management

### What's the license?

Check the LICENSE file in the repository. Generally MIT or similar permissive license allowing free use with attribution.
