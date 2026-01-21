"""Monte Carlo simulation for portfolio projections."""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class MonteCarloSimulator:
    """Monte Carlo simulation for portfolio performance projections."""

    def __init__(
        self,
        initial_value: float,
        expected_return: float,
        volatility: float,
        years: int = 30,
        simulations: int = 10000,
        annual_contribution: float = 0.0,
        contribution_growth: float = 0.0,
        random_seed: Optional[int] = None
    ):
        """
        Initialize Monte Carlo simulator.

        Args:
            initial_value: Starting portfolio value
            expected_return: Annual expected return (e.g., 0.08 for 8%)
            volatility: Annual volatility/standard deviation (e.g., 0.15 for 15%)
            years: Number of years to simulate
            simulations: Number of simulation runs
            annual_contribution: Annual additional contribution
            contribution_growth: Annual growth rate of contributions
            random_seed: Random seed for reproducibility
        """
        self.initial_value = initial_value
        self.expected_return = expected_return
        self.volatility = volatility
        self.years = years
        self.simulations = simulations
        self.annual_contribution = annual_contribution
        self.contribution_growth = contribution_growth

        if random_seed is not None:
            np.random.seed(random_seed)

        # Results storage
        self.simulation_results = None
        self.final_values = None
        self.percentiles = None

    def run_simulation(
        self,
        distribution: str = 'lognormal',
        rebalance_frequency: str = 'annual'
    ) -> pd.DataFrame:
        """
        Run Monte Carlo simulation.

        Args:
            distribution: 'lognormal' or 'normal'
            rebalance_frequency: 'annual', 'monthly', 'daily'

        Returns:
            DataFrame with simulation results
        """
        # Determine time steps
        if rebalance_frequency == 'daily':
            periods_per_year = 252
        elif rebalance_frequency == 'monthly':
            periods_per_year = 12
        else:  # annual
            periods_per_year = 1

        total_periods = self.years * periods_per_year

        # Adjust return and volatility for time period
        period_return = self.expected_return / periods_per_year
        period_volatility = self.volatility / np.sqrt(periods_per_year)

        # Initialize results array
        results = np.zeros((self.simulations, total_periods + 1))
        results[:, 0] = self.initial_value

        # Run simulations
        for sim in range(self.simulations):
            portfolio_value = self.initial_value

            for period in range(total_periods):
                # Generate random return
                if distribution == 'lognormal':
                    # Log-normal distribution (more realistic for stocks)
                    random_return = np.random.lognormal(
                        mean=period_return - 0.5 * period_volatility**2,
                        sigma=period_volatility
                    ) - 1
                else:
                    # Normal distribution
                    random_return = np.random.normal(
                        period_return,
                        period_volatility
                    )

                # Apply return
                portfolio_value *= (1 + random_return)

                # Add contributions (at period boundaries matching frequency)
                if period > 0 and period % periods_per_year == 0:
                    year = period // periods_per_year
                    contribution = self.annual_contribution * \
                        (1 + self.contribution_growth) ** (year - 1)
                    portfolio_value += contribution

                results[sim, period + 1] = portfolio_value

        # Store results
        self.simulation_results = results
        self.final_values = results[:, -1]

        # Calculate percentiles
        self._calculate_percentiles()

        return self._create_results_dataframe(periods_per_year)

    def _calculate_percentiles(self):
        """Calculate percentile statistics for each time period."""
        percentile_levels = [5, 10, 25, 50, 75, 90, 95]
        self.percentiles = {}

        for level in percentile_levels:
            self.percentiles[f'p{level}'] = np.percentile(
                self.simulation_results,
                level,
                axis=0
            )

    def _create_results_dataframe(self, periods_per_year: int) -> pd.DataFrame:
        """Create DataFrame with simulation results."""
        periods = self.simulation_results.shape[1]

        # Create time index
        if periods_per_year == 252:
            freq = 'D'
        elif periods_per_year == 12:
            freq = 'M'
        else:
            freq = 'Y'

        # Create date range
        start_date = datetime.now()
        date_range = pd.date_range(
            start=start_date,
            periods=periods,
            freq=freq
        )

        # Create DataFrame with percentiles
        df = pd.DataFrame({
            'date': date_range,
            'median': self.percentiles['p50'],
            'mean': np.mean(self.simulation_results, axis=0),
            'p5': self.percentiles['p5'],
            'p10': self.percentiles['p10'],
            'p25': self.percentiles['p25'],
            'p75': self.percentiles['p75'],
            'p90': self.percentiles['p90'],
            'p95': self.percentiles['p95'],
        })

        return df

    def get_probability_of_goal(self, goal_amount: float) -> float:
        """
        Calculate probability of reaching a goal amount.

        Args:
            goal_amount: Target portfolio value

        Returns:
            Probability (0 to 1) of reaching goal
        """
        if self.final_values is None:
            raise ValueError("Run simulation first")

        successful = np.sum(self.final_values >= goal_amount)
        return successful / self.simulations

    def get_probability_of_loss(self) -> float:
        """
        Calculate probability of losing money.

        Returns:
            Probability (0 to 1) of ending below initial value
        """
        if self.final_values is None:
            raise ValueError("Run simulation first")

        losses = np.sum(self.final_values < self.initial_value)
        return losses / self.simulations

    def get_statistics(self) -> Dict[str, float]:
        """
        Get summary statistics of simulation results.

        Returns:
            Dictionary of statistics
        """
        if self.final_values is None:
            raise ValueError("Run simulation first")

        return {
            'mean': np.mean(self.final_values),
            'median': np.median(self.final_values),
            'std': np.std(self.final_values),
            'min': np.min(self.final_values),
            'max': np.max(self.final_values),
            'p5': np.percentile(self.final_values, 5),
            'p10': np.percentile(self.final_values, 10),
            'p25': np.percentile(self.final_values, 25),
            'p75': np.percentile(self.final_values, 75),
            'p90': np.percentile(self.final_values, 90),
            'p95': np.percentile(self.final_values, 95),
            'probability_of_loss': self.get_probability_of_loss()
        }

    def calculate_retirement_probability(
        self,
        years_in_retirement: int,
        annual_withdrawal: float,
        withdrawal_growth: float = 0.03
    ) -> Dict[str, float]:
        """
        Calculate probability of portfolio surviving retirement.

        Args:
            years_in_retirement: How many years of withdrawals
            annual_withdrawal: Annual withdrawal amount
            withdrawal_growth: Annual increase in withdrawals (inflation)

        Returns:
            Dictionary with survival probability and statistics
        """
        if self.simulation_results is None:
            raise ValueError("Run simulation first")

        # Get final values from accumulation phase
        starting_values = self.final_values.copy()

        # Simulate retirement phase
        survived = 0

        for sim_value in starting_values:
            portfolio = sim_value

            for year in range(years_in_retirement):
                # Withdraw at beginning of year
                withdrawal = annual_withdrawal * (1 + withdrawal_growth) ** year
                portfolio -= withdrawal

                # Check if depleted
                if portfolio <= 0:
                    break

                # Apply return for the year
                random_return = np.random.lognormal(
                    mean=self.expected_return - 0.5 * self.volatility**2,
                    sigma=self.volatility
                ) - 1

                portfolio *= (1 + random_return)

            # Check if portfolio survived
            if portfolio > 0:
                survived += 1

        survival_rate = survived / self.simulations

        return {
            'survival_rate': survival_rate,
            'failure_rate': 1 - survival_rate,
            'years_in_retirement': years_in_retirement,
            'total_withdrawals': annual_withdrawal * years_in_retirement
        }

    def get_safe_withdrawal_rate(
        self,
        years_in_retirement: int = 30,
        success_rate: float = 0.95,
        max_iterations: int = 50
    ) -> float:
        """
        Calculate safe withdrawal rate using binary search.

        Args:
            years_in_retirement: Retirement duration
            success_rate: Desired probability of success (e.g., 0.95)
            max_iterations: Maximum search iterations

        Returns:
            Safe withdrawal rate as percentage of final value
        """
        if self.final_values is None:
            raise ValueError("Run simulation first")

        # Binary search for safe withdrawal rate
        low, high = 0.0, 0.15  # Search between 0% and 15%

        for _ in range(max_iterations):
            mid = (low + high) / 2
            median_final = np.median(self.final_values)
            annual_withdrawal = median_final * mid

            result = self.calculate_retirement_probability(
                years_in_retirement,
                annual_withdrawal,
                withdrawal_growth=0.03
            )

            if result['survival_rate'] < success_rate:
                high = mid
            else:
                low = mid

            if abs(high - low) < 0.001:  # Converged
                break

        return (low + high) / 2

    def get_all_paths(self) -> pd.DataFrame:
        """
        Get all simulation paths.

        Returns:
            DataFrame with all simulation paths
        """
        if self.simulation_results is None:
            raise ValueError("Run simulation first")

        return pd.DataFrame(self.simulation_results.T)

    def get_sample_paths(self, n_samples: int = 100) -> pd.DataFrame:
        """
        Get sample of simulation paths for visualization.

        Args:
            n_samples: Number of sample paths to return

        Returns:
            DataFrame with sample paths
        """
        if self.simulation_results is None:
            raise ValueError("Run simulation first")

        # Randomly sample paths
        sample_indices = np.random.choice(
            self.simulations,
            size=min(n_samples, self.simulations),
            replace=False
        )

        return pd.DataFrame(self.simulation_results[sample_indices].T)


def estimate_parameters_from_returns(
    returns: pd.Series,
    periods_per_year: int = 252
) -> Tuple[float, float]:
    """
    Estimate expected return and volatility from historical returns.

    Args:
        returns: Series of historical returns
        periods_per_year: Trading periods per year (252 for daily, 12 for monthly)

    Returns:
        Tuple of (expected_return, volatility)
    """
    # Annualized expected return
    expected_return = returns.mean() * periods_per_year

    # Annualized volatility
    volatility = returns.std() * np.sqrt(periods_per_year)

    return expected_return, volatility


def run_quick_simulation(
    initial_value: float,
    years: int,
    historical_returns: Optional[pd.Series] = None,
    expected_return: float = 0.08,
    volatility: float = 0.15,
    simulations: int = 10000
) -> Dict:
    """
    Quick wrapper to run simulation with sensible defaults.

    Args:
        initial_value: Starting portfolio value
        years: Years to simulate
        historical_returns: Optional historical returns to estimate parameters
        expected_return: Annual expected return (used if no historical data)
        volatility: Annual volatility (used if no historical data)
        simulations: Number of simulations

    Returns:
        Dictionary with results and statistics
    """
    # Estimate parameters from historical data if provided
    if historical_returns is not None:
        expected_return, volatility = estimate_parameters_from_returns(
            historical_returns
        )

    # Run simulation
    simulator = MonteCarloSimulator(
        initial_value=initial_value,
        expected_return=expected_return,
        volatility=volatility,
        years=years,
        simulations=simulations
    )

    results_df = simulator.run_simulation()
    statistics = simulator.get_statistics()

    return {
        'results': results_df,
        'statistics': statistics,
        'simulator': simulator
    }
