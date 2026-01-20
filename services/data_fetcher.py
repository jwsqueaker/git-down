"""Market data and macro indicators fetcher."""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from fredapi import Fred
from config.settings import FRED_API_KEY, BENCHMARKS, MACRO_INDICATORS


class MarketDataFetcher:
    """Fetch market data using yfinance."""

    @staticmethod
    def get_price_data(symbol: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch historical price data for a symbol.

        Args:
            symbol: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_current_price(symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Current price or None if error
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d')
            if not data.empty:
                return data['Close'].iloc[-1]
            return None
        except Exception as e:
            print(f"Error fetching current price for {symbol}: {e}")
            return None

    @staticmethod
    def get_multiple_prices(symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols.

        Args:
            symbols: List of ticker symbols

        Returns:
            Dictionary mapping symbol to current price
        """
        prices = {}
        for symbol in symbols:
            price = MarketDataFetcher.get_current_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices

    @staticmethod
    def get_returns(symbol: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.Series:
        """
        Calculate returns for a symbol.

        Args:
            symbol: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Series of daily returns
        """
        df = MarketDataFetcher.get_price_data(symbol, start_date, end_date)
        if df.empty:
            return pd.Series()

        returns = df['Close'].pct_change().dropna()
        return returns

    @staticmethod
    def get_benchmark_data(benchmark_name: str = 'S&P 500',
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get benchmark index data.

        Args:
            benchmark_name: Name of benchmark (e.g., 'S&P 500', 'Nasdaq')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with benchmark data
        """
        symbol = BENCHMARKS.get(benchmark_name)
        if symbol is None:
            print(f"Unknown benchmark: {benchmark_name}")
            return pd.DataFrame()

        return MarketDataFetcher.get_price_data(symbol, start_date, end_date)

    @staticmethod
    def get_ticker_info(symbol: str) -> Dict:
        """
        Get detailed information about a ticker.

        Args:
            symbol: Ticker symbol

        Returns:
            Dictionary with ticker information
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'name': info.get('longName', symbol),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', None),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', None),
                '52w_high': info.get('fiftyTwoWeekHigh', None),
                '52w_low': info.get('fiftyTwoWeekLow', None)
            }
        except Exception as e:
            print(f"Error fetching info for {symbol}: {e}")
            return {'name': symbol}


class MacroDataFetcher:
    """Fetch macro economic indicators using FRED API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize macro data fetcher.

        Args:
            api_key: FRED API key (defaults to config)
        """
        self.api_key = api_key or FRED_API_KEY
        if not self.api_key:
            print("Warning: FRED API key not set. Macro indicators will not be available.")
            self.fred = None
        else:
            try:
                self.fred = Fred(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing FRED API: {e}")
                self.fred = None

    def get_indicator(self, indicator_name: str,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> pd.Series:
        """
        Fetch a specific macro indicator.

        Args:
            indicator_name: Name of indicator (e.g., 'GDP Growth', 'CPI (Inflation)')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Series with indicator data
        """
        if self.fred is None:
            return pd.Series()

        series_id = MACRO_INDICATORS.get(indicator_name)
        if series_id is None:
            print(f"Unknown indicator: {indicator_name}")
            return pd.Series()

        try:
            data = self.fred.get_series(series_id, start_date, end_date)
            data.name = indicator_name
            return data
        except Exception as e:
            print(f"Error fetching {indicator_name}: {e}")
            return pd.Series()

    def get_all_indicators(self, start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch all configured macro indicators.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with all indicators
        """
        if self.fred is None:
            return pd.DataFrame()

        all_data = {}
        for name in MACRO_INDICATORS.keys():
            series = self.get_indicator(name, start_date, end_date)
            if not series.empty:
                all_data[name] = series

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        return df

    def get_latest_values(self) -> Dict[str, float]:
        """
        Get the most recent value for each indicator.

        Returns:
            Dictionary mapping indicator name to latest value
        """
        if self.fred is None:
            return {}

        latest = {}
        for name in MACRO_INDICATORS.keys():
            series = self.get_indicator(name)
            if not series.empty:
                latest[name] = series.iloc[-1]

        return latest

    def get_yoy_change(self, indicator_name: str) -> Optional[float]:
        """
        Get year-over-year change for an indicator.

        Args:
            indicator_name: Name of indicator

        Returns:
            YoY percentage change or None
        """
        if self.fred is None:
            return None

        # Get last 2 years of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)

        series = self.get_indicator(
            indicator_name,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        if len(series) < 2:
            return None

        # Get values approximately 1 year apart
        current = series.iloc[-1]
        year_ago_idx = max(0, len(series) - 13)  # Approximately 12 months ago
        year_ago = series.iloc[year_ago_idx]

        if year_ago == 0:
            return None

        return ((current - year_ago) / year_ago) * 100


class CorrelationAnalyzer:
    """Analyze correlations between portfolio and various data sources."""

    @staticmethod
    def calculate_correlation_matrix(returns_dict: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Calculate correlation matrix from multiple return series.

        Args:
            returns_dict: Dictionary mapping name to returns series

        Returns:
            Correlation matrix as DataFrame
        """
        # Align all series by date
        df = pd.DataFrame(returns_dict)
        correlation = df.corr()
        return correlation

    @staticmethod
    def calculate_rolling_correlation(series1: pd.Series, series2: pd.Series,
                                     window: int = 60) -> pd.Series:
        """
        Calculate rolling correlation between two series.

        Args:
            series1: First series
            series2: Second series
            window: Rolling window size

        Returns:
            Series of rolling correlations
        """
        # Align series
        combined = pd.DataFrame({'s1': series1, 's2': series2}).dropna()

        if len(combined) < window:
            return pd.Series()

        rolling_corr = combined['s1'].rolling(window).corr(combined['s2'])
        return rolling_corr

    @staticmethod
    def portfolio_benchmark_correlation(portfolio_returns: pd.Series,
                                       benchmark_name: str = 'S&P 500',
                                       start_date: Optional[str] = None) -> float:
        """
        Calculate correlation between portfolio and benchmark.

        Args:
            portfolio_returns: Portfolio returns series
            benchmark_name: Benchmark name
            start_date: Optional start date

        Returns:
            Correlation coefficient
        """
        benchmark_returns = MarketDataFetcher.get_returns(
            BENCHMARKS.get(benchmark_name, '^GSPC'),
            start_date=start_date
        )

        if benchmark_returns.empty:
            return 0.0

        # Align dates
        combined = pd.DataFrame({
            'portfolio': portfolio_returns,
            'benchmark': benchmark_returns
        }).dropna()

        if len(combined) < 2:
            return 0.0

        return combined['portfolio'].corr(combined['benchmark'])
