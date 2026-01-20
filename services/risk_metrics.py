"""Risk-adjusted return metrics calculations."""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from config.settings import TRADING_DAYS_PER_YEAR, DEFAULT_RISK_FREE_RATE


class RiskMetricsCalculator:
    """Calculate various risk-adjusted performance metrics."""

    def __init__(self, returns: pd.Series, risk_free_rate: float = DEFAULT_RISK_FREE_RATE / 100):
        """
        Initialize risk metrics calculator.

        Args:
            returns: Series of returns (daily, weekly, or monthly)
            risk_free_rate: Annual risk-free rate (as decimal, e.g., 0.045 for 4.5%)
        """
        self.returns = returns.dropna()
        self.risk_free_rate = risk_free_rate

    def annualized_return(self, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate annualized return.

        Args:
            periods_per_year: Number of periods per year (252 for daily, 12 for monthly)

        Returns:
            Annualized return as decimal
        """
        if len(self.returns) == 0:
            return 0.0

        total_return = (1 + self.returns).prod() - 1
        n_periods = len(self.returns)
        years = n_periods / periods_per_year

        if years == 0:
            return 0.0

        return (1 + total_return) ** (1 / years) - 1

    def volatility(self, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate annualized volatility (standard deviation).

        Args:
            periods_per_year: Number of periods per year

        Returns:
            Annualized volatility as decimal
        """
        if len(self.returns) < 2:
            return 0.0

        return self.returns.std() * np.sqrt(periods_per_year)

    def sharpe_ratio(self, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate Sharpe ratio.

        Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility

        Args:
            periods_per_year: Number of periods per year

        Returns:
            Sharpe ratio
        """
        ann_return = self.annualized_return(periods_per_year)
        vol = self.volatility(periods_per_year)

        if vol == 0:
            return 0.0

        return (ann_return - self.risk_free_rate) / vol

    def sortino_ratio(self, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate Sortino ratio.

        Sortino Ratio = (Portfolio Return - Risk-Free Rate) / Downside Deviation
        Only considers downside volatility (negative returns).

        Args:
            periods_per_year: Number of periods per year

        Returns:
            Sortino ratio
        """
        ann_return = self.annualized_return(periods_per_year)
        downside_returns = self.returns[self.returns < 0]

        if len(downside_returns) == 0:
            return np.inf if ann_return > self.risk_free_rate else 0.0

        downside_std = downside_returns.std() * np.sqrt(periods_per_year)

        if downside_std == 0:
            return 0.0

        return (ann_return - self.risk_free_rate) / downside_std

    def max_drawdown(self) -> float:
        """
        Calculate maximum drawdown.

        Max Drawdown = (Trough Value - Peak Value) / Peak Value

        Returns:
            Maximum drawdown as decimal (negative value)
        """
        if len(self.returns) == 0:
            return 0.0

        cumulative = (1 + self.returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        return drawdown.min()

    def calmar_ratio(self, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate Calmar ratio.

        Calmar Ratio = Annualized Return / Absolute Max Drawdown

        Args:
            periods_per_year: Number of periods per year

        Returns:
            Calmar ratio
        """
        ann_return = self.annualized_return(periods_per_year)
        max_dd = abs(self.max_drawdown())

        if max_dd == 0:
            return 0.0

        return ann_return / max_dd

    def calculate_beta(self, benchmark_returns: pd.Series) -> float:
        """
        Calculate beta relative to a benchmark.

        Beta = Covariance(Portfolio, Benchmark) / Variance(Benchmark)

        Args:
            benchmark_returns: Benchmark returns series

        Returns:
            Beta
        """
        # Align returns
        combined = pd.DataFrame({
            'portfolio': self.returns,
            'benchmark': benchmark_returns
        }).dropna()

        if len(combined) < 2:
            return 1.0

        covariance = combined['portfolio'].cov(combined['benchmark'])
        benchmark_variance = combined['benchmark'].var()

        if benchmark_variance == 0:
            return 1.0

        return covariance / benchmark_variance

    def calculate_alpha(self, benchmark_returns: pd.Series,
                       periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate Jensen's alpha.

        Alpha = Portfolio Return - (Risk-Free Rate + Beta * (Benchmark Return - Risk-Free Rate))

        Args:
            benchmark_returns: Benchmark returns series
            periods_per_year: Number of periods per year

        Returns:
            Alpha (annualized)
        """
        portfolio_return = self.annualized_return(periods_per_year)
        benchmark_calc = RiskMetricsCalculator(benchmark_returns, self.risk_free_rate)
        benchmark_return = benchmark_calc.annualized_return(periods_per_year)
        beta = self.calculate_beta(benchmark_returns)

        alpha = portfolio_return - (self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate))

        return alpha

    def treynor_ratio(self, benchmark_returns: pd.Series,
                     periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate Treynor ratio.

        Treynor Ratio = (Portfolio Return - Risk-Free Rate) / Beta

        Args:
            benchmark_returns: Benchmark returns series
            periods_per_year: Number of periods per year

        Returns:
            Treynor ratio
        """
        ann_return = self.annualized_return(periods_per_year)
        beta = self.calculate_beta(benchmark_returns)

        if beta == 0:
            return 0.0

        return (ann_return - self.risk_free_rate) / beta

    def information_ratio(self, benchmark_returns: pd.Series,
                         periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
        """
        Calculate information ratio.

        Information Ratio = (Portfolio Return - Benchmark Return) / Tracking Error
        Measures excess return per unit of tracking error.

        Args:
            benchmark_returns: Benchmark returns series
            periods_per_year: Number of periods per year

        Returns:
            Information ratio
        """
        # Align returns
        combined = pd.DataFrame({
            'portfolio': self.returns,
            'benchmark': benchmark_returns
        }).dropna()

        if len(combined) < 2:
            return 0.0

        # Calculate excess returns
        excess_returns = combined['portfolio'] - combined['benchmark']

        # Annualized excess return
        ann_excess = excess_returns.mean() * periods_per_year

        # Tracking error (annualized)
        tracking_error = excess_returns.std() * np.sqrt(periods_per_year)

        if tracking_error == 0:
            return 0.0

        return ann_excess / tracking_error

    def value_at_risk(self, confidence_level: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR).

        Args:
            confidence_level: Confidence level (e.g., 0.95 for 95%)

        Returns:
            VaR as decimal (negative value represents potential loss)
        """
        if len(self.returns) == 0:
            return 0.0

        return np.percentile(self.returns, (1 - confidence_level) * 100)

    def conditional_var(self, confidence_level: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.

        CVaR is the expected loss given that we're in the worst (1 - confidence_level) of cases.

        Args:
            confidence_level: Confidence level (e.g., 0.95 for 95%)

        Returns:
            CVaR as decimal (negative value represents expected loss in tail)
        """
        if len(self.returns) == 0:
            return 0.0

        var = self.value_at_risk(confidence_level)
        return self.returns[self.returns <= var].mean()

    def all_metrics(self, benchmark_returns: Optional[pd.Series] = None,
                   periods_per_year: int = TRADING_DAYS_PER_YEAR) -> dict:
        """
        Calculate all available metrics.

        Args:
            benchmark_returns: Optional benchmark returns for relative metrics
            periods_per_year: Number of periods per year

        Returns:
            Dictionary of all metrics
        """
        metrics = {
            'total_return': (1 + self.returns).prod() - 1,
            'annualized_return': self.annualized_return(periods_per_year),
            'volatility': self.volatility(periods_per_year),
            'sharpe_ratio': self.sharpe_ratio(periods_per_year),
            'sortino_ratio': self.sortino_ratio(periods_per_year),
            'max_drawdown': self.max_drawdown(),
            'calmar_ratio': self.calmar_ratio(periods_per_year),
            'var_95': self.value_at_risk(0.95),
            'cvar_95': self.conditional_var(0.95)
        }

        if benchmark_returns is not None:
            metrics.update({
                'beta': self.calculate_beta(benchmark_returns),
                'alpha': self.calculate_alpha(benchmark_returns, periods_per_year),
                'treynor_ratio': self.treynor_ratio(benchmark_returns, periods_per_year),
                'information_ratio': self.information_ratio(benchmark_returns, periods_per_year)
            })

        return metrics
