"""Goal-based financial planning."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from services.monte_carlo import MonteCarloSimulator


class Goal:
    """Financial goal definition."""

    def __init__(
        self,
        name: str,
        target_amount: float,
        years_until: int,
        priority: int = 1,
        current_saved: float = 0.0
    ):
        """
        Initialize financial goal.

        Args:
            name: Goal name (e.g., "House Down Payment")
            target_amount: Target amount needed
            years_until: Years until goal date
            priority: Priority ranking (1=highest)
            current_saved: Amount already saved for this goal
        """
        self.name = name
        self.target_amount = target_amount
        self.years_until = years_until
        self.priority = priority
        self.current_saved = current_saved


class GoalPlanner:
    """Multi-goal financial planning."""

    def __init__(self, goals: List[Goal], total_savings_rate: float):
        """
        Initialize goal planner.

        Args:
            goals: List of financial goals
            total_savings_rate: Total annual savings available
        """
        self.goals = sorted(goals, key=lambda g: (g.years_until, g.priority))
        self.total_savings_rate = total_savings_rate

    def calculate_required_savings_per_goal(
        self,
        expected_return: float = 0.07
    ) -> pd.DataFrame:
        """
        Calculate required monthly savings for each goal.

        Args:
            expected_return: Expected annual return

        Returns:
            DataFrame with savings requirements
        """
        results = []

        for goal in self.goals:
            # Amount still needed
            needed = goal.target_amount - goal.current_saved

            if needed <= 0:
                monthly_savings = 0
                shortfall = 0
            else:
                # Calculate monthly savings using future value of annuity
                monthly_rate = expected_return / 12
                months = goal.years_until * 12

                if monthly_rate > 0:
                    # FV = PMT * (((1 + r)^n - 1) / r) + PV * (1 + r)^n
                    # Solve for PMT
                    fv_of_current = goal.current_saved * (1 + monthly_rate) ** months
                    remaining_needed = goal.target_amount - fv_of_current

                    if remaining_needed > 0:
                        monthly_savings = remaining_needed / (
                            ((1 + monthly_rate) ** months - 1) / monthly_rate
                        )
                    else:
                        monthly_savings = 0
                else:
                    monthly_savings = needed / months if months > 0 else needed

                shortfall = max(0, monthly_savings * 12 - self.total_savings_rate)

            results.append({
                'goal': goal.name,
                'target_amount': goal.target_amount,
                'current_saved': goal.current_saved,
                'amount_needed': needed,
                'years_until': goal.years_until,
                'monthly_savings_required': monthly_savings,
                'annual_savings_required': monthly_savings * 12,
                'priority': goal.priority,
                'shortfall': shortfall,
                'on_track': shortfall == 0
            })

        return pd.DataFrame(results)

    def allocate_savings_by_priority(self) -> pd.DataFrame:
        """
        Allocate available savings across goals by priority.

        Returns:
            DataFrame with savings allocation
        """
        required_df = self.calculate_required_savings_per_goal()

        allocations = []
        remaining_savings = self.total_savings_rate

        for _, row in required_df.iterrows():
            if remaining_savings <= 0:
                allocated = 0
                funded_pct = 0
            else:
                needed = row['annual_savings_required']
                allocated = min(needed, remaining_savings)
                funded_pct = (allocated / needed * 100) if needed > 0 else 100

                remaining_savings -= allocated

            allocations.append({
                'goal': row['goal'],
                'required_annual': row['annual_savings_required'],
                'allocated_annual': allocated,
                'funded_percentage': funded_pct,
                'priority': row['priority']
            })

        return pd.DataFrame(allocations)

    def run_goal_monte_carlo(
        self,
        goal: Goal,
        monthly_savings: float,
        expected_return: float = 0.07,
        volatility: float = 0.15,
        simulations: int = 10000
    ) -> Dict:
        """
        Run Monte Carlo simulation for goal achievement.

        Args:
            goal: Financial goal
            monthly_savings: Monthly savings amount
            expected_return: Expected annual return
            volatility: Annual volatility
            simulations: Number of simulations

        Returns:
            Dictionary with simulation results
        """
        simulator = MonteCarloSimulator(
            initial_value=goal.current_saved,
            expected_return=expected_return,
            volatility=volatility,
            years=goal.years_until,
            simulations=simulations,
            annual_contribution=monthly_savings * 12
        )

        results = simulator.run_simulation()

        # Calculate probability of reaching goal
        success_rate = simulator.get_probability_of_goal(goal.target_amount)

        return {
            'goal_name': goal.name,
            'target_amount': goal.target_amount,
            'probability_of_success': success_rate,
            'median_final_value': np.median(simulator.final_values),
            'results': results
        }

    def suggest_timeline_adjustment(
        self,
        goal: Goal,
        available_monthly_savings: float,
        expected_return: float = 0.07
    ) -> Dict:
        """
        Suggest timeline adjustment if savings is insufficient.

        Args:
            goal: Financial goal
            available_monthly_savings: Available monthly savings
            expected_return: Expected annual return

        Returns:
            Dictionary with timeline suggestions
        """
        # Calculate how long it would take with available savings
        monthly_rate = expected_return / 12
        needed = goal.target_amount - goal.current_saved

        if available_monthly_savings <= 0:
            return {
                'feasible': False,
                'suggested_years': float('inf')
            }

        if monthly_rate > 0:
            # Solve for n: FV = PMT * (((1 + r)^n - 1) / r) + PV * (1 + r)^n
            # This requires numerical solution, use approximation
            months_needed = int(np.log(1 + (needed * monthly_rate) / available_monthly_savings) / np.log(1 + monthly_rate))
        else:
            months_needed = int(needed / available_monthly_savings) if available_monthly_savings > 0 else 999

        years_needed = months_needed / 12

        return {
            'original_timeline': goal.years_until,
            'suggested_timeline': years_needed,
            'timeline_extension': max(0, years_needed - goal.years_until),
            'feasible': years_needed <= goal.years_until * 1.5  # Within 50% extension
        }


def calculate_education_cost_projection(
    current_annual_cost: float,
    years_until_college: int,
    years_in_college: int = 4,
    inflation_rate: float = 0.05
) -> Dict:
    """
    Project future education costs.

    Args:
        current_annual_cost: Current annual college cost
        years_until_college: Years until child starts college
        years_in_college: Duration of college
        inflation_rate: Education cost inflation rate

    Returns:
        Dictionary with cost projections
    """
    # Project cost at start of college
    first_year_cost = current_annual_cost * (1 + inflation_rate) ** years_until_college

    # Total cost over all years
    total_cost = 0
    year_costs = []

    for year in range(years_in_college):
        year_cost = first_year_cost * (1 + inflation_rate) ** year
        total_cost += year_cost
        year_costs.append(year_cost)

    return {
        'current_annual_cost': current_annual_cost,
        'first_year_cost': first_year_cost,
        'total_cost_needed': total_cost,
        'yearly_costs': year_costs,
        'years_until': years_until_college
    }
