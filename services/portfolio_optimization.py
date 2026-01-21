"""Portfolio optimization using Modern Portfolio Theory."""
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Optional


class PortfolioOptimizer:
    """Calculate efficient frontier and optimal portfolios."""

    def __init__(self, returns: pd.DataFrame, risk_free_rate: float = 0.03):
        """
        Initialize optimizer.

        Args:
            returns: DataFrame with historical returns (columns = assets)
            risk_free_rate: Annual risk-free rate
        """
        self.returns = returns
        self.risk_free_rate = risk_free_rate
        self.mean_returns = returns.mean() * 252  # Annualized
        self.cov_matrix = returns.cov() * 252  # Annualized

    def calculate_portfolio_performance(
        self,
        weights: np.ndarray
    ) -> Tuple[float, float]:
        """
        Calculate portfolio return and risk.

        Args:
            weights: Portfolio weights

        Returns:
            Tuple of (return, volatility)
        """
        portfolio_return = np.sum(self.mean_returns * weights)
        portfolio_std = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))

        return portfolio_return, portfolio_std

    def calculate_sharpe_ratio(self, weights: np.ndarray) -> float:
        """Calculate Sharpe ratio for given weights."""
        port_return, port_std = self.calculate_portfolio_performance(weights)
        return (port_return - self.risk_free_rate) / port_std

    def find_max_sharpe_portfolio(self) -> Dict:
        """Find maximum Sharpe ratio portfolio."""
        num_assets = len(self.mean_returns)

        # Constraints
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))

        # Initial guess
        init_guess = num_assets * [1. / num_assets]

        # Optimize (minimize negative Sharpe)
        result = minimize(
            lambda w: -self.calculate_sharpe_ratio(w),
            init_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        opt_weights = result.x
        opt_return, opt_vol = self.calculate_portfolio_performance(opt_weights)
        opt_sharpe = self.calculate_sharpe_ratio(opt_weights)

        return {
            'weights': dict(zip(self.returns.columns, opt_weights)),
            'expected_return': opt_return,
            'volatility': opt_vol,
            'sharpe_ratio': opt_sharpe
        }

    def find_min_volatility_portfolio(self) -> Dict:
        """Find minimum volatility portfolio."""
        num_assets = len(self.mean_returns)

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))
        init_guess = num_assets * [1. / num_assets]

        result = minimize(
            lambda w: self.calculate_portfolio_performance(w)[1],
            init_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        opt_weights = result.x
        opt_return, opt_vol = self.calculate_portfolio_performance(opt_weights)

        return {
            'weights': dict(zip(self.returns.columns, opt_weights)),
            'expected_return': opt_return,
            'volatility': opt_vol,
            'sharpe_ratio': self.calculate_sharpe_ratio(opt_weights)
        }

    def generate_efficient_frontier(
        self,
        num_portfolios: int = 50
    ) -> pd.DataFrame:
        """
        Generate efficient frontier.

        Args:
            num_portfolios: Number of points on frontier

        Returns:
            DataFrame with efficient frontier portfolios
        """
        # Find min and max return portfolios
        min_vol_port = self.find_min_volatility_portfolio()
        max_sharpe_port = self.find_max_sharpe_portfolio()

        # Target returns
        target_returns = np.linspace(
            min_vol_port['expected_return'],
            max_sharpe_port['expected_return'],
            num_portfolios
        )

        frontier = []

        for target_return in target_returns:
            # Optimize for minimum volatility at target return
            constraints = (
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: self.calculate_portfolio_performance(x)[0] - target_return}
            )

            bounds = tuple((0, 1) for _ in range(len(self.mean_returns)))
            init_guess = len(self.mean_returns) * [1. / len(self.mean_returns)]

            result = minimize(
                lambda w: self.calculate_portfolio_performance(w)[1],
                init_guess,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                weights = result.x
                ret, vol = self.calculate_portfolio_performance(weights)
                sharpe = self.calculate_sharpe_ratio(weights)

                frontier.append({
                    'return': ret,
                    'volatility': vol,
                    'sharpe_ratio': sharpe
                })

        return pd.DataFrame(frontier)

    def suggest_portfolio_for_risk_level(
        self,
        target_volatility: float
    ) -> Dict:
        """
        Suggest portfolio for target risk level.

        Args:
            target_volatility: Target annual volatility (e.g., 0.15 for 15%)

        Returns:
            Portfolio weights and characteristics
        """
        num_assets = len(self.mean_returns)

        # Maximize return subject to volatility constraint
        constraints = (
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'ineq', 'fun': lambda x: target_volatility - self.calculate_portfolio_performance(x)[1]}
        )

        bounds = tuple((0, 1) for _ in range(num_assets))
        init_guess = num_assets * [1. / num_assets]

        result = minimize(
            lambda w: -self.calculate_portfolio_performance(w)[0],
            init_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        opt_weights = result.x
        opt_return, opt_vol = self.calculate_portfolio_performance(opt_weights)

        return {
            'weights': dict(zip(self.returns.columns, opt_weights)),
            'expected_return': opt_return,
            'volatility': opt_vol,
            'sharpe_ratio': self.calculate_sharpe_ratio(opt_weights)
        }
