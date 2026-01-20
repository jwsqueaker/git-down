# Portfolio Dashboard - Usage Guide

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your FRED API key
```

### 2. Get FRED API Key (Free)

1. Visit https://fred.stlouisfed.org/
2. Create a free account
3. Go to https://fred.stlouisfed.org/docs/api/api_key.html
4. Request an API key
5. Add it to your `.env` file: `FRED_API_KEY=your_key_here`

### 3. Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Features Guide

### Portfolio Upload

1. **Prepare Your Portfolio CSV**:
   - Download the template from the sidebar
   - Fill in your positions with these columns:
     - `symbol`: Stock ticker (e.g., AAPL, MSFT, SPY)
     - `shares`: Number of shares you own
     - `purchase_date`: When you bought it (YYYY-MM-DD format)
     - `purchase_price`: Price per share when purchased

2. **Upload**:
   - Click "Browse files" in the sidebar
   - Select your CSV file
   - The dashboard will automatically load and analyze your portfolio

### Overview Tab

- **Total Value**: Current market value of your portfolio
- **Total Return**: Overall gain/loss percentage
- **Holdings Table**: Detailed view of each position
- **Asset Allocation**: Pie chart showing portfolio composition

### Performance Tab

Key metrics include:

- **Annualized Return**: Your average yearly return
- **Sharpe Ratio**: Risk-adjusted return (higher is better, >1 is good)
- **Sortino Ratio**: Like Sharpe but focuses on downside risk
- **Max Drawdown**: Largest peak-to-trough decline
- **Calmar Ratio**: Return relative to max drawdown
- **Volatility**: Standard deviation of returns

**Historical Chart**: Compare your portfolio against S&P 500

### Benchmark Comparison Tab

- Select different benchmarks (S&P 500, Nasdaq, etc.)
- View comparative performance metrics
- **Beta**: Portfolio sensitivity to market movements
  - Beta = 1: Moves with the market
  - Beta > 1: More volatile than market
  - Beta < 1: Less volatile than market
- **Alpha**: Excess return over what Beta predicts (positive is good)
- **Tracking Error**: How much you deviate from the benchmark
- **Information Ratio**: Risk-adjusted excess return

### Macro Indicators Tab

Monitor economic conditions:

- **GDP Growth**: Economic expansion/contraction
- **CPI (Inflation)**: Cost of living changes
- **Unemployment Rate**: Job market health
- **Fed Funds Rate**: Central bank policy rate
- **10Y Treasury Yield**: Long-term interest rates

Each indicator shows:
- Current value
- Year-over-year change
- Historical trend chart

### Correlations Tab

Understand relationships between your holdings:

- **Correlation Matrix**: How positions move together
  - +1: Perfect positive correlation
  - 0: No correlation
  - -1: Perfect negative correlation (good for diversification)

Use this to identify:
- Diversification opportunities
- Concentrated risks
- Hedging positions

### LTCMA Tab

Upload JP Morgan's Long-Term Capital Market Assumptions:

1. **Download LTCMA Template**: Get the CSV format
2. **Add Data**: Fill in asset class expectations
   - Expected returns
   - Volatility
   - (Optional) Correlation data
3. **Upload**: Use the LTCMA uploader in sidebar

View:
- Expected returns by asset class
- Risk-return scatter plot
- Compare your portfolio to forward-looking expectations

## Understanding Risk Metrics

### Sharpe Ratio
- Measures return per unit of risk
- Formula: (Return - Risk-Free Rate) / Volatility
- **Interpretation**:
  - < 1: Not great
  - 1-2: Good
  - 2-3: Very good
  - > 3: Excellent

### Sortino Ratio
- Like Sharpe, but only penalizes downside volatility
- Better measure if you don't mind upside volatility
- Generally higher than Sharpe ratio

### Treynor Ratio
- Return per unit of systematic risk (Beta)
- Useful for well-diversified portfolios

### Information Ratio
- Risk-adjusted excess return vs. benchmark
- > 0.5 is good, > 1.0 is excellent

### Calmar Ratio
- Return relative to maximum drawdown
- Higher is better
- > 1 is considered good

### Maximum Drawdown
- Worst peak-to-trough decline
- Shows worst historical loss
- Important for risk tolerance

## Tips for Best Results

### Data Quality
- Ensure all symbols are valid tickers
- Use purchase dates in YYYY-MM-DD format
- Double-check purchase prices
- For ETFs/funds, use their ticker symbols

### Analysis Periods
- **1M-6M**: Short-term momentum
- **1Y**: Recent performance
- **3Y**: Medium-term trends
- **5Y+**: Long-term performance (recommended)

### Benchmark Selection
- **S&P 500**: For large-cap US equity portfolios
- **Nasdaq**: For tech-heavy portfolios
- **Russell 2000**: For small-cap focused portfolios
- **Dow Jones**: For blue-chip portfolios

### Interpreting Results

**Good Signs**:
- Sharpe ratio > 1
- Positive alpha
- Low correlation within portfolio (good diversification)
- Outperformance vs. benchmark

**Warning Signs**:
- Max drawdown > 30%
- High correlation with single sector
- Negative alpha over long periods
- Very high volatility relative to returns

## Troubleshooting

### "No positions found"
- Check CSV format matches template
- Ensure all required columns are present
- Verify column names are exact (case-sensitive)

### "Error fetching data"
- Check internet connection
- Verify symbols are valid
- Some symbols may not have historical data

### "Unable to fetch macro indicators"
- Verify FRED_API_KEY in .env file
- Check API key is valid
- Ensure you haven't exceeded rate limits

### Prices not updating
- Click "Load from Database" to refresh
- Re-upload portfolio CSV
- Check that market is open (prices update during trading hours)

## Advanced Features

### Export Data
- Download your analysis as CSV
- Use exported data in Excel/Sheets
- Share metrics with advisors

### Multiple Portfolios
- Save different portfolio CSVs
- Compare performance across portfolios
- Track multiple strategies

### Custom Benchmarks
- Use any ticker as benchmark
- Compare to sector ETFs
- Analyze against custom indices

## Support

For issues or questions:
- Check the README.md for setup instructions
- Review this guide for feature explanations
- Verify your data format matches templates
- Check FRED API key configuration

## Example Workflow

1. **Morning**: Upload portfolio, check overnight changes
2. **Check Performance**: Review metrics for your holding period
3. **Monitor Macro**: See if economic indicators suggest changes
4. **Analyze Correlations**: Identify diversification opportunities
5. **Compare Benchmarks**: Validate your strategy is working
6. **Review LTCMA**: Compare to long-term expectations
7. **Make Decisions**: Use insights for portfolio adjustments

Remember: This is an analytical tool. Always do your own research and consider consulting a financial advisor for investment decisions.
