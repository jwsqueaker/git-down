"""Configuration settings for the portfolio dashboard."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///portfolio_dashboard.db')

# API Keys
FRED_API_KEY = os.getenv('FRED_API_KEY', '')

# Risk-Free Rate
RISK_FREE_RATE_SYMBOL = os.getenv('RISK_FREE_RATE_SYMBOL', '^TNX')

# Benchmarks
BENCHMARKS = {
    'S&P 500': '^GSPC',
    'Nasdaq': '^IXIC',
    'Dow Jones': '^DJI',
    'Russell 2000': '^RUT',
    'VIX': '^VIX',
    '10Y Treasury': '^TNX'
}

# Macro Indicators (FRED)
MACRO_INDICATORS = {
    'GDP Growth': 'A191RL1Q225SBEA',
    'CPI (Inflation)': 'CPIAUCSL',
    'Unemployment Rate': 'UNRATE',
    'Fed Funds Rate': 'DFF',
    '10Y Treasury Yield': 'DGS10',
    'PCE Inflation': 'PCEPI',
    'Consumer Sentiment': 'UMCSENT',
    'Industrial Production': 'INDPRO'
}

# Trading days per year
TRADING_DAYS_PER_YEAR = 252

# Risk-free rate default (annual %)
DEFAULT_RISK_FREE_RATE = 4.5
