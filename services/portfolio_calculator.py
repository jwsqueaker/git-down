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
        Calculate historical portfolio values - SIMPLIFIED for accuracy.

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

        # Calculate daily portfolio value
        daily_values = []
        daily_cost_basis = []

        for date in prices_df.index:
            date_as_date = date.date()

            # Calculate portfolio value on this date
            total_value = 0
            total_cost = 0

            for position in self.positions:
                # Only include position if it's been purchased by this date
                if date_as_date >= position.purchase_date and position.symbol in prices_df.columns:
                    price = prices_df.loc[date, position.symbol]
                    if pd.notna(price):
                        total_value += price * position.shares
                        total_cost += position.cost_basis

            daily_values.append(total_value)
            daily_cost_basis.append(total_cost)

        # Create DataFrame
        result = pd.DataFrame({
            'value': daily_values,
            'cost_basis': daily_cost_basis
        }, index=prices_df.index)

        # Remove days with zero portfolio value
        result = result[result['value'] > 0]

        # Calculate simple daily returns
        result['returns'] = result['value'].pct_change()

        # Note: This is simple pct_change and doesn't adjust for cash flows
        # If positions were added during the period, returns will include that effect
        # For cash-flow adjusted returns, use calculate_time_weighted_return()

        return result

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

    def calculate_multi_period_returns(self) -> Dict[str, Dict]:
        """
        Calculate returns for multiple standard periods.

        Returns:
            Dictionary with period names as keys and metrics as values
        """
        periods = {
            '1 Year': 365,
            '2 Year': 365 * 2,
            '3 Year': 365 * 3,
            '4 Year': 365 * 4,
            '5 Year': 365 * 5,
            '8 Year': 365 * 8,
            '10 Year': 365 * 10
        }

        results = {}
        end_date = datetime.now().strftime('%Y-%m-%d')

        # Get inception date
        if self.positions:
            inception_date = min(p.purchase_date for p in self.positions)
        else:
            return results

        for period_name, days in periods.items():
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            # Don't calculate if period is before inception
            if datetime.strptime(start_date, '%Y-%m-%d').date() < inception_date:
                continue

            try:
                hist_data = self.calculate_historical_values(start_date, end_date)

                if not hist_data.empty and len(hist_data) > 1:
                    start_value = hist_data['value'].iloc[0]
                    end_value = hist_data['value'].iloc[-1]

                    # Calculate total return
                    total_return = (end_value / start_value - 1) * 100

                    # Calculate annualized return
                    actual_days = (hist_data.index[-1] - hist_data.index[0]).days
                    years = actual_days / 365.25
                    if years > 0:
                        annualized_return = ((end_value / start_value) ** (1 / years) - 1) * 100
                    else:
                        annualized_return = total_return

                    results[period_name] = {
                        'total_return': total_return,
                        'annualized_return': annualized_return,
                        'start_value': start_value,
                        'end_value': end_value,
                        'start_date': hist_data.index[0].strftime('%Y-%m-%d'),
                        'end_date': hist_data.index[-1].strftime('%Y-%m-%d'),
                        'days': actual_days
                    }
            except Exception as e:
                print(f"Error calculating {period_name} return: {e}")
                continue

        # Add "Since Inception"
        try:
            start_date = inception_date.strftime('%Y-%m-%d')
            hist_data = self.calculate_historical_values(start_date, end_date)

            if not hist_data.empty and len(hist_data) > 1:
                start_value = hist_data['value'].iloc[0]
                end_value = hist_data['value'].iloc[-1]

                total_return = (end_value / start_value - 1) * 100

                actual_days = (hist_data.index[-1] - hist_data.index[0]).days
                years = actual_days / 365.25
                if years > 0:
                    annualized_return = ((end_value / start_value) ** (1 / years) - 1) * 100
                else:
                    annualized_return = total_return

                results['Since Inception'] = {
                    'total_return': total_return,
                    'annualized_return': annualized_return,
                    'start_value': start_value,
                    'end_value': end_value,
                    'start_date': hist_data.index[0].strftime('%Y-%m-%d'),
                    'end_date': hist_data.index[-1].strftime('%Y-%m-%d'),
                    'days': actual_days
                }
        except Exception as e:
            print(f"Error calculating inception return: {e}")

        return results

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
