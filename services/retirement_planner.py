"""Retirement planning and goal achievement calculator."""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from services.monte_carlo import MonteCarloSimulator


class RetirementPlanner:
    """Calculate retirement readiness and goal achievement probability."""

    def __init__(
        self,
        current_age: int,
        retirement_age: int,
        life_expectancy: int,
        current_portfolio_value: float,
        annual_contribution: float,
        contribution_growth_rate: float = 0.03,
        expected_return: float = 0.08,
        volatility: float = 0.15,
        simulations: int = 10000
    ):
        """
        Initialize retirement planner.

        Args:
            current_age: Current age in years
            retirement_age: Target retirement age
            life_expectancy: Expected age at death
            current_portfolio_value: Current portfolio value
            annual_contribution: Annual savings/contributions
            contribution_growth_rate: Annual increase in contributions
            expected_return: Expected annual return during accumulation
            volatility: Annual volatility of returns
            simulations: Number of Monte Carlo simulations
        """
        self.current_age = current_age
        self.retirement_age = retirement_age
        self.life_expectancy = life_expectancy
        self.current_portfolio_value = current_portfolio_value
        self.annual_contribution = annual_contribution
        self.contribution_growth_rate = contribution_growth_rate
        self.expected_return = expected_return
        self.volatility = volatility
        self.simulations = simulations

        # Calculated values
        self.years_to_retirement = retirement_age - current_age
        self.years_in_retirement = life_expectancy - retirement_age

        # Results
        self.accumulation_results = None
        self.retirement_values = None

    def calculate_retirement_readiness(
        self,
        desired_annual_income: float,
        income_replacement_ratio: Optional[float] = None,
        social_security_annual: float = 0.0,
        pension_annual: float = 0.0,
        healthcare_annual: float = 0.0,
        other_expenses_annual: float = 0.0,
        inflation_rate: float = 0.03,
        retirement_return: float = 0.06,
        retirement_volatility: float = 0.10
    ) -> Dict:
        """
        Calculate probability of meeting retirement goals.

        Args:
            desired_annual_income: Target annual retirement income (today's dollars)
            income_replacement_ratio: Optional ratio of pre-retirement income (e.g., 0.8 for 80%)
            social_security_annual: Expected annual Social Security benefits
            pension_annual: Expected annual pension income
            healthcare_annual: Expected annual healthcare costs
            other_expenses_annual: Other annual retirement expenses
            inflation_rate: Expected inflation rate
            retirement_return: Expected return during retirement (typically lower)
            retirement_volatility: Volatility during retirement (typically lower)

        Returns:
            Dictionary with retirement readiness analysis
        """
        # Accumulation phase - save until retirement
        accumulation_simulator = MonteCarloSimulator(
            initial_value=self.current_portfolio_value,
            expected_return=self.expected_return,
            volatility=self.volatility,
            years=self.years_to_retirement,
            simulations=self.simulations,
            annual_contribution=self.annual_contribution,
            contribution_growth=self.contribution_growth_rate
        )

        accumulation_results = accumulation_simulator.run_simulation()
        self.accumulation_results = accumulation_results
        retirement_portfolio_values = accumulation_simulator.final_values

        # Calculate required income
        if income_replacement_ratio is not None:
            # Estimate current income from contributions
            estimated_current_income = self.annual_contribution / 0.15  # Assume 15% savings rate
            desired_annual_income = estimated_current_income * income_replacement_ratio

        # Calculate net income needed from portfolio
        other_income = social_security_annual + pension_annual
        net_income_needed = desired_annual_income + healthcare_annual + other_expenses_annual - other_income

        # Retirement phase - simulate withdrawals
        successful_scenarios = 0
        final_balances = []

        for starting_value in retirement_portfolio_values:
            portfolio = starting_value
            survived = True

            for year in range(self.years_in_retirement):
                # Inflation-adjusted withdrawal
                withdrawal = net_income_needed * (1 + inflation_rate) ** year

                # Withdraw at beginning of year
                portfolio -= withdrawal

                if portfolio <= 0:
                    survived = False
                    break

                # Apply return for the year
                random_return = np.random.lognormal(
                    mean=retirement_return - 0.5 * retirement_volatility**2,
                    sigma=retirement_volatility
                ) - 1

                portfolio *= (1 + random_return)

            if survived and portfolio > 0:
                successful_scenarios += 1

            final_balances.append(portfolio if survived else 0)

        # Calculate success rate
        success_rate = successful_scenarios / self.simulations

        # Calculate shortfall/surplus
        median_retirement_value = np.median(retirement_portfolio_values)

        # Rule of thumb: 4% withdrawal rate
        sustainable_income_4pct = median_retirement_value * 0.04

        # Calculate actual sustainable withdrawal rate
        if median_retirement_value > 0:
            withdrawal_rate = net_income_needed / median_retirement_value
        else:
            withdrawal_rate = 0

        # Determine readiness level
        if success_rate >= 0.90:
            readiness_level = "Excellent"
            readiness_color = "green"
        elif success_rate >= 0.75:
            readiness_level = "Good"
            readiness_color = "blue"
        elif success_rate >= 0.60:
            readiness_level = "Fair"
            readiness_color = "orange"
        else:
            readiness_level = "Needs Improvement"
            readiness_color = "red"

        # Calculate required portfolio value for 90% success
        required_value_90pct = net_income_needed / 0.04  # Using 4% rule

        # Calculate shortfall
        shortfall = max(0, required_value_90pct - median_retirement_value)

        return {
            'success_rate': success_rate,
            'readiness_level': readiness_level,
            'readiness_color': readiness_color,
            'median_retirement_value': median_retirement_value,
            'mean_retirement_value': np.mean(retirement_portfolio_values),
            'p10_retirement_value': np.percentile(retirement_portfolio_values, 10),
            'p90_retirement_value': np.percentile(retirement_portfolio_values, 90),
            'desired_annual_income': desired_annual_income,
            'net_income_needed': net_income_needed,
            'sustainable_income_4pct': sustainable_income_4pct,
            'withdrawal_rate': withdrawal_rate,
            'required_value_90pct': required_value_90pct,
            'shortfall': shortfall,
            'surplus': max(0, median_retirement_value - required_value_90pct),
            'years_to_retirement': self.years_to_retirement,
            'years_in_retirement': self.years_in_retirement,
            'total_contributions': self._calculate_total_contributions(),
            'successful_scenarios': successful_scenarios,
            'failed_scenarios': self.simulations - successful_scenarios,
            'median_final_balance': np.median(final_balances),
            'retirement_portfolio_values': retirement_portfolio_values
        }

    def _calculate_total_contributions(self) -> float:
        """Calculate total contributions over accumulation period."""
        total = 0
        for year in range(self.years_to_retirement):
            contribution = self.annual_contribution * (1 + self.contribution_growth_rate) ** year
            total += contribution
        return total

    def calculate_required_savings(
        self,
        desired_annual_income: float,
        success_rate_target: float = 0.90,
        max_iterations: int = 50
    ) -> Dict:
        """
        Calculate required annual savings to meet retirement goal.

        Args:
            desired_annual_income: Target retirement income
            success_rate_target: Desired probability of success (e.g., 0.90)
            max_iterations: Maximum search iterations

        Returns:
            Dictionary with required savings analysis
        """
        # Binary search for required savings
        low, high = 0.0, desired_annual_income * 2

        for _ in range(max_iterations):
            mid = (low + high) / 2

            # Test this savings rate
            test_planner = RetirementPlanner(
                current_age=self.current_age,
                retirement_age=self.retirement_age,
                life_expectancy=self.life_expectancy,
                current_portfolio_value=self.current_portfolio_value,
                annual_contribution=mid,
                contribution_growth_rate=self.contribution_growth_rate,
                expected_return=self.expected_return,
                volatility=self.volatility,
                simulations=5000  # Use fewer for speed
            )

            result = test_planner.calculate_retirement_readiness(
                desired_annual_income=desired_annual_income
            )

            if result['success_rate'] < success_rate_target:
                low = mid
            else:
                high = mid

            if abs(high - low) < 100:  # Converged to within $100
                break

        required_annual_savings = (low + high) / 2
        increase_needed = required_annual_savings - self.annual_contribution

        return {
            'required_annual_savings': required_annual_savings,
            'current_annual_savings': self.annual_contribution,
            'increase_needed': increase_needed,
            'increase_percentage': (increase_needed / self.annual_contribution * 100) if self.annual_contribution > 0 else 0,
            'monthly_increase_needed': increase_needed / 12
        }

    def retirement_age_scenarios(
        self,
        desired_annual_income: float,
        ages_to_test: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Compare retirement outcomes at different retirement ages.

        Args:
            desired_annual_income: Target retirement income
            ages_to_test: List of retirement ages to test (default: current+5 to current+15)

        Returns:
            DataFrame with comparison across retirement ages
        """
        if ages_to_test is None:
            min_age = max(self.current_age + 5, 60)
            max_age = min(self.current_age + 20, 75)
            ages_to_test = list(range(min_age, max_age + 1, 5))

        results = []

        for retirement_age in ages_to_test:
            if retirement_age <= self.current_age:
                continue

            planner = RetirementPlanner(
                current_age=self.current_age,
                retirement_age=retirement_age,
                life_expectancy=self.life_expectancy,
                current_portfolio_value=self.current_portfolio_value,
                annual_contribution=self.annual_contribution,
                contribution_growth_rate=self.contribution_growth_rate,
                expected_return=self.expected_return,
                volatility=self.volatility,
                simulations=self.simulations
            )

            analysis = planner.calculate_retirement_readiness(
                desired_annual_income=desired_annual_income
            )

            results.append({
                'retirement_age': retirement_age,
                'years_to_retirement': retirement_age - self.current_age,
                'success_rate': analysis['success_rate'],
                'median_portfolio_value': analysis['median_retirement_value'],
                'withdrawal_rate': analysis['withdrawal_rate'],
                'readiness_level': analysis['readiness_level']
            })

        return pd.DataFrame(results)

    def income_scenarios(
        self,
        income_levels: Optional[List[float]] = None
    ) -> pd.DataFrame:
        """
        Compare success rates at different income levels.

        Args:
            income_levels: List of annual income amounts to test

        Returns:
            DataFrame with comparison across income levels
        """
        if income_levels is None:
            # Default: test income from 50% to 150% of 4% rule
            base_income = self.current_portfolio_value * 0.04
            income_levels = [
                base_income * 0.5,
                base_income * 0.75,
                base_income,
                base_income * 1.25,
                base_income * 1.5
            ]

        results = []

        for income in income_levels:
            analysis = self.calculate_retirement_readiness(
                desired_annual_income=income
            )

            results.append({
                'annual_income': income,
                'success_rate': analysis['success_rate'],
                'withdrawal_rate': analysis['withdrawal_rate'],
                'readiness_level': analysis['readiness_level']
            })

        return pd.DataFrame(results)

    def get_retirement_timeline(self) -> Dict[str, pd.DataFrame]:
        """
        Get detailed timeline for accumulation and retirement phases.

        Returns:
            Dictionary with 'accumulation' and 'retirement' DataFrames
        """
        timeline = {
            'accumulation': None,
            'retirement': None
        }

        if self.accumulation_results is not None:
            timeline['accumulation'] = self.accumulation_results

        return timeline

    def calculate_social_security_estimate(
        self,
        average_indexed_monthly_earnings: float,
        full_retirement_age: int = 67
    ) -> Dict:
        """
        Estimate Social Security benefits (simplified calculator).

        Args:
            average_indexed_monthly_earnings: Average indexed monthly earnings
            full_retirement_age: Full retirement age for Social Security

        Returns:
            Dictionary with benefit estimates
        """
        # Simplified PIA (Primary Insurance Amount) calculation
        # 2024 bend points: $1,174 and $7,078
        aime = average_indexed_monthly_earnings

        if aime <= 1174:
            pia = aime * 0.90
        elif aime <= 7078:
            pia = (1174 * 0.90) + ((aime - 1174) * 0.32)
        else:
            pia = (1174 * 0.90) + ((7078 - 1174) * 0.32) + ((aime - 7078) * 0.15)

        # Adjustment for claiming age
        age_difference = self.retirement_age - full_retirement_age

        if age_difference < 0:
            # Early claiming reduces benefits (5/9 of 1% per month for first 36 months, then 5/12 of 1%)
            months_early = abs(age_difference * 12)
            if months_early <= 36:
                reduction = months_early * (5/9) * 0.01
            else:
                reduction = (36 * (5/9) * 0.01) + ((months_early - 36) * (5/12) * 0.01)
            adjusted_benefit = pia * (1 - reduction)
        elif age_difference > 0:
            # Delayed claiming increases benefits (2/3 of 1% per month)
            months_late = age_difference * 12
            increase = months_late * (2/3) * 0.01
            adjusted_benefit = pia * (1 + increase)
        else:
            adjusted_benefit = pia

        return {
            'monthly_benefit': adjusted_benefit,
            'annual_benefit': adjusted_benefit * 12,
            'claiming_age': self.retirement_age,
            'full_retirement_age': full_retirement_age,
            'adjustment_factor': adjusted_benefit / pia if pia > 0 else 1.0
        }


def calculate_retirement_number(
    desired_annual_income: float,
    withdrawal_rate: float = 0.04,
    other_income: float = 0.0
) -> float:
    """
    Calculate required portfolio value for retirement (the "retirement number").

    Args:
        desired_annual_income: Target annual retirement income
        withdrawal_rate: Safe withdrawal rate (default 4%)
        other_income: Other guaranteed income (Social Security, pension, etc.)

    Returns:
        Required portfolio value
    """
    income_from_portfolio = desired_annual_income - other_income
    return income_from_portfolio / withdrawal_rate


def calculate_savings_rate_needed(
    current_portfolio: float,
    target_portfolio: float,
    years: int,
    expected_return: float = 0.08
) -> float:
    """
    Calculate required annual savings to reach target.

    Args:
        current_portfolio: Current portfolio value
        target_portfolio: Target portfolio value
        years: Years until retirement
        expected_return: Expected annual return

    Returns:
        Required annual savings amount
    """
    # Future value of current portfolio
    fv_current = current_portfolio * (1 + expected_return) ** years

    # Shortfall to make up with contributions
    shortfall = target_portfolio - fv_current

    if shortfall <= 0:
        return 0.0

    # Calculate required annual payment using FV of annuity formula
    # FV = PMT * (((1 + r)^n - 1) / r)
    # PMT = FV / (((1 + r)^n - 1) / r)

    denominator = ((1 + expected_return) ** years - 1) / expected_return
    required_savings = shortfall / denominator

    return required_savings
