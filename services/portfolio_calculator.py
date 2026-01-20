"""Portfolio calculation and analytics engine."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from models.portfolio import Position, PortfolioSnapshot, PerformanceMetrics
from services.data_fetcher import MarketDataFetcher, CorrelationAnalyzer
from services.risk_metrics import RiskMetricsCalculator
from config.settings import TRADING_DAYS_PER_YEAR


class PortfolioCalculator:
    """Calculate portfolio metrics and performance."""

    def __init__(self, positions: List[Position]):
        """
        Initialize portfolio calculator.

        Args:
            positions: List of portfolio positions
        """
        self.positions = positions
        self.market_data = MarketDataFetcher()

    def update_current_prices(self):
        """Fetch and update current prices for all positions."""
        symbols = [p.symbol for p in self.positions]
        prices = self.market_data.get_multiple_prices(symbols)

        for position in self.positions:
            if position.symbol in prices:
                position.current_price = prices[position.symbol]

    def get_snapshot(self, as_of_date: Optional[datetime] = None) -> PortfolioSnapshot:
        """
        Get portfolio snapshot.

        Args:
            as_of_date: Date for snapshot (defaults to today)

        Returns:
            PortfolioSnapshot object
        """
        if as_of_date is None:
            as_of_date = datetime.now().date()

        # Update prices if needed
        if any(p.current_price is None for p in self.positions):
            self.update_current_prices()

        snapshot = PortfolioSnapshot(
            date=as_of_date,
            positions=self.positions.copy()
        )

        return snapshot

    def calculate_historical_values(self, start_date: str,
                                    end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Calculate historical portfolio values.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today

        Returns:
            DataFrame with historical values and returns
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Get historical prices for all positions
        all_prices = {}
        for position in self.positions:
            prices = self.market_data.get_price_data(
                position.symbol,
                start_date,
                end_date
            )
            if not prices.empty:
                all_prices[position.symbol] = prices['Close']

        if not all_prices:
            return pd.DataFrame()

        # Create DataFrame of prices
        prices_df = pd.DataFrame(all_prices)

        # Calculate position values (shares * price)
        values_df = pd.DataFrame()
        for position in self.positions:
            if position.symbol in prices_df.columns:
                # Only include prices after purchase date
                mask = prices_df.index.date >= position.purchase_date
                values = prices_df[position.symbol].copy()
                values[~mask] = np.nan
                values_df[position.symbol] = values * position.shares

        # Calculate total portfolio value
        portfolio_value = values_df.sum(axis=1)

        # Calculate returns
        portfolio_returns = portfolio_value.pct_change()

        # Create result DataFrame
        result = pd.DataFrame({
            'value': portfolio_value,
            'returns': portfolio_returns
        })

        return result.dropna()

    def calculate_returns(self, start_date: str,
                         end_date: Optional[str] = None) -> pd.Series:
        """
        Calculate portfolio returns.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Series of daily returns
        """
        hist_data = self.calculate_historical_values(start_date, end_date)
        if hist_data.empty:
            return pd.Series()

        return hist_data['returns'].dropna()

    def calculate_performance_metrics(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        benchmark: str = 'S&P 500',
        risk_free_rate: Optional[float] = None
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            benchmark: Benchmark name for comparison
            risk_free_rate: Annual risk-free rate (decimal)

        Returns:
            PerformanceMetrics object
        """
        # Get portfolio returns
        returns = self.calculate_returns(start_date, end_date)

        if returns.empty:
            # Return zero metrics if no data
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                calmar_ratio=0.0
            )

        # Get benchmark returns
        benchmark_returns = self.market_data.get_returns(
            symbol=benchmark,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate risk metrics
        calculator = RiskMetricsCalculator(
            returns,
            risk_free_rate=risk_free_rate if risk_free_rate else 0.045
        )

        # Get all metrics
        if not benchmark_returns.empty:
            metrics_dict = calculator.all_metrics(
                benchmark_returns=benchmark_returns,
                periods_per_year=TRADING_DAYS_PER_YEAR
            )
        else:
            metrics_dict = calculator.all_metrics(
                periods_per_year=TRADING_DAYS_PER_YEAR
            )

        # Create PerformanceMetrics object
        return PerformanceMetrics(
            total_return=metrics_dict.get('total_return', 0.0),
            annualized_return=metrics_dict.get('annualized_return', 0.0),
            volatility=metrics_dict.get('volatility', 0.0),
            sharpe_ratio=metrics_dict.get('sharpe_ratio', 0.0),
            sortino_ratio=metrics_dict.get('sortino_ratio', 0.0),
            max_drawdown=metrics_dict.get('max_drawdown', 0.0),
            calmar_ratio=metrics_dict.get('calmar_ratio', 0.0),
            beta=metrics_dict.get('beta'),
            alpha=metrics_dict.get('alpha'),
            treynor_ratio=metrics_dict.get('treynor_ratio'),
            information_ratio=metrics_dict.get('information_ratio')
        )

    def compare_to_benchmark(
        self,
        benchmark: str = 'S&P 500',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Compare portfolio performance to benchmark.

        Args:
            benchmark: Benchmark name
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with comparison metrics
        """
        # Get portfolio returns
        portfolio_returns = self.calculate_returns(start_date, end_date)

        # Get benchmark returns
        benchmark_returns = self.market_data.get_returns(
            benchmark,
            start_date,
            end_date
        )

        if portfolio_returns.empty or benchmark_returns.empty:
            return {}

        # Calculate metrics for both
        port_calc = RiskMetricsCalculator(portfolio_returns)
        bench_calc = RiskMetricsCalculator(benchmark_returns)

        # Calculate correlation
        corr_analyzer = CorrelationAnalyzer()
        correlation = corr_analyzer.portfolio_benchmark_correlation(
            portfolio_returns,
            benchmark,
            start_date
        )

        comparison = {
            'portfolio_return': port_calc.annualized_return(),
            'benchmark_return': bench_calc.annualized_return(),
            'portfolio_volatility': port_calc.volatility(),
            'benchmark_volatility': bench_calc.volatility(),
            'portfolio_sharpe': port_calc.sharpe_ratio(),
            'benchmark_sharpe': bench_calc.sharpe_ratio(),
            'beta': port_calc.calculate_beta(benchmark_returns),
            'alpha': port_calc.calculate_alpha(benchmark_returns),
            'correlation': correlation,
            'tracking_error': (portfolio_returns - benchmark_returns).std() * np.sqrt(TRADING_DAYS_PER_YEAR),
            'information_ratio': port_calc.information_ratio(benchmark_returns)
        }

        return comparison

    def analyze_contributions(self, start_date: str,
                            end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Analyze position-level contributions to portfolio return.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with position contributions
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        contributions = []

        for position in self.positions:
            # Get price data
            prices = self.market_data.get_price_data(
                position.symbol,
                start_date,
                end_date
            )

            if prices.empty:
                continue

            # Filter to post-purchase
            prices = prices[prices.index.date >= position.purchase_date]

            if len(prices) < 2:
                continue

            # Calculate return
            start_price = prices['Close'].iloc[0]
            end_price = prices['Close'].iloc[-1]
            position_return = (end_price - start_price) / start_price

            # Calculate contribution (weighted by initial allocation)
            initial_value = position.shares * start_price
            contribution = position_return * initial_value

            contributions.append({
                'symbol': position.symbol,
                'initial_value': initial_value,
                'return': position_return,
                'contribution': contribution
            })

        df = pd.DataFrame(contributions)

        if not df.empty:
            total_initial = df['initial_value'].sum()
            df['weight'] = df['initial_value'] / total_initial
            df['weighted_contribution'] = df['contribution'] / total_initial

        return df

    def get_correlation_matrix(self, start_date: str,
                               end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Calculate correlation matrix of portfolio positions.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Correlation matrix DataFrame
        """
        returns_dict = {}

        for position in self.positions:
            returns = self.market_data.get_returns(
                position.symbol,
                start_date,
                end_date
            )
            if not returns.empty:
                returns_dict[position.symbol] = returns

        if not returns_dict:
            return pd.DataFrame()

        analyzer = CorrelationAnalyzer()
        return analyzer.calculate_correlation_matrix(returns_dict)
