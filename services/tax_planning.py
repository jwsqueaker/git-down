"""Tax planning and optimization tools."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from models.portfolio import Position


class TaxPlanner:
    """Tax planning and optimization calculator."""

    def __init__(self, positions: List[Position], tax_brackets: Optional[Dict] = None):
        """
        Initialize tax planner.

        Args:
            positions: List of portfolio positions
            tax_brackets: Custom tax brackets (uses 2024 federal if not provided)
        """
        self.positions = positions
        self.tax_brackets = tax_brackets or self._default_tax_brackets()

    def _default_tax_brackets(self) -> Dict:
        """2024 Federal tax brackets (single filer)."""
        return {
            'ordinary': [
                (11600, 0.10),
                (47150, 0.12),
                (100525, 0.22),
                (191950, 0.24),
                (243725, 0.32),
                (609350, 0.35),
                (float('inf'), 0.37)
            ],
            'long_term_capital_gains': [
                (47025, 0.00),
                (518900, 0.15),
                (float('inf'), 0.20)
            ],
            'short_term_capital_gains': 'ordinary'  # Taxed as ordinary income
        }

    def calculate_unrealized_gains(self) -> pd.DataFrame:
        """
        Calculate unrealized gains/losses for all positions.

        Returns:
            DataFrame with gain/loss details
        """
        results = []

        for position in self.positions:
            if position.current_price is None:
                continue

            cost_basis = position.shares * position.purchase_price
            current_value = position.shares * position.current_price
            gain_loss = current_value - cost_basis
            gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0

            # Determine holding period
            holding_days = (datetime.now().date() - position.purchase_date).days
            is_long_term = holding_days > 365

            results.append({
                'symbol': position.symbol,
                'shares': position.shares,
                'cost_basis': cost_basis,
                'current_value': current_value,
                'unrealized_gain_loss': gain_loss,
                'gain_loss_pct': gain_loss_pct,
                'holding_days': holding_days,
                'is_long_term': is_long_term,
                'purchase_date': position.purchase_date
            })

        return pd.DataFrame(results)

    def identify_tax_loss_harvest_opportunities(
        self,
        min_loss_threshold: float = 1000.0
    ) -> pd.DataFrame:
        """
        Identify tax-loss harvesting opportunities.

        Args:
            min_loss_threshold: Minimum loss to consider (default $1,000)

        Returns:
            DataFrame with tax-loss harvesting candidates
        """
        gains_df = self.calculate_unrealized_gains()

        # Filter for losses above threshold
        harvest_candidates = gains_df[
            gains_df['unrealized_gain_loss'] < -min_loss_threshold
        ].copy()

        if harvest_candidates.empty:
            return harvest_candidates

        # Calculate tax benefit
        harvest_candidates['estimated_tax_benefit'] = harvest_candidates.apply(
            lambda row: self._calculate_tax_on_gain(
                row['unrealized_gain_loss'],
                row['is_long_term']
            ),
            axis=1
        )

        # Sort by tax benefit (most negative = biggest benefit)
        harvest_candidates = harvest_candidates.sort_values(
            'estimated_tax_benefit'
        )

        return harvest_candidates[[
            'symbol', 'unrealized_gain_loss', 'gain_loss_pct',
            'holding_days', 'is_long_term', 'estimated_tax_benefit'
        ]]

    def calculate_tax_on_gain(
        self,
        gain: float,
        holding_period_days: int,
        income: float = 100000.0
    ) -> float:
        """
        Calculate tax on a capital gain.

        Args:
            gain: Capital gain amount
            holding_period_days: Days held
            income: Annual ordinary income for tax bracket determination

        Returns:
            Tax owed
        """
        is_long_term = holding_period_days > 365
        return self._calculate_tax_on_gain(gain, is_long_term, income)

    def _calculate_tax_on_gain(
        self,
        gain: float,
        is_long_term: bool,
        income: float = 100000.0
    ) -> float:
        """Internal method to calculate tax."""
        if gain <= 0:
            # Tax benefit from losses (can offset other gains)
            # Simplified: assume max benefit at marginal rate
            return gain * 0.24  # Typical marginal rate

        if is_long_term:
            brackets = self.tax_brackets['long_term_capital_gains']
        else:
            brackets = self.tax_brackets['ordinary']

        tax = 0
        remaining = gain

        for threshold, rate in brackets:
            if income + remaining <= threshold:
                tax += remaining * rate
                break
            else:
                taxable_in_bracket = threshold - income
                tax += taxable_in_bracket * rate
                remaining -= taxable_in_bracket
                income = threshold

        return tax

    def estimate_annual_tax_impact(
        self,
        realized_gains: float = 0.0,
        realized_losses: float = 0.0,
        dividend_income: float = 0.0,
        ordinary_income: float = 100000.0
    ) -> Dict:
        """
        Estimate annual tax impact from portfolio.

        Args:
            realized_gains: Realized capital gains for the year
            realized_losses: Realized capital losses for the year
            dividend_income: Total dividend income
            ordinary_income: Salary and other ordinary income

        Returns:
            Dictionary with tax estimates
        """
        # Net capital gains/losses
        net_capital_gain_loss = realized_gains - realized_losses

        # Capital loss limitation ($3,000 per year)
        if net_capital_gain_loss < 0:
            deductible_loss = min(abs(net_capital_gain_loss), 3000)
            carryforward_loss = max(abs(net_capital_gain_loss) - 3000, 0)
        else:
            deductible_loss = 0
            carryforward_loss = 0

        # Calculate tax on net gains (if positive)
        if net_capital_gain_loss > 0:
            capital_gains_tax = self._calculate_tax_on_gain(
                net_capital_gain_loss,
                is_long_term=True,  # Assume long-term for this estimate
                income=ordinary_income
            )
        else:
            capital_gains_tax = 0

        # Tax benefit from deductible losses
        if deductible_loss > 0:
            # Reduces ordinary income
            tax_benefit = deductible_loss * self._get_marginal_rate(ordinary_income)
        else:
            tax_benefit = 0

        # Dividend tax (qualified dividends taxed at capital gains rates)
        dividend_tax = self._calculate_tax_on_gain(
            dividend_income,
            is_long_term=True,
            income=ordinary_income
        )

        total_investment_tax = capital_gains_tax + dividend_tax - tax_benefit

        return {
            'realized_gains': realized_gains,
            'realized_losses': realized_losses,
            'net_capital_gain_loss': net_capital_gain_loss,
            'dividend_income': dividend_income,
            'deductible_loss': deductible_loss,
            'carryforward_loss': carryforward_loss,
            'capital_gains_tax': capital_gains_tax,
            'dividend_tax': dividend_tax,
            'tax_benefit_from_losses': tax_benefit,
            'total_investment_tax': total_investment_tax,
            'effective_rate': (total_investment_tax / (realized_gains + dividend_income) * 100)
                if (realized_gains + dividend_income) > 0 else 0
        }

    def _get_marginal_rate(self, income: float) -> float:
        """Get marginal tax rate for given income."""
        brackets = self.tax_brackets['ordinary']

        for threshold, rate in brackets:
            if income <= threshold:
                return rate

        return brackets[-1][1]  # Highest bracket

    def calculate_wash_sale_risk(
        self,
        symbol: str,
        sale_date: datetime,
        days_window: int = 30
    ) -> Dict:
        """
        Check for wash sale risk.

        Args:
            symbol: Stock symbol
            sale_date: Date of sale
            days_window: Days before/after to check (default 30)

        Returns:
            Dictionary with wash sale risk assessment
        """
        # Check if same security was purchased within 30 days before or after
        purchase_dates = [
            p.purchase_date for p in self.positions
            if p.symbol == symbol
        ]

        at_risk = False
        risk_dates = []

        for purchase_date in purchase_dates:
            days_diff = abs((sale_date.date() - purchase_date).days)

            if days_diff <= days_window:
                at_risk = True
                risk_dates.append(purchase_date)

        return {
            'symbol': symbol,
            'at_risk': at_risk,
            'risk_dates': risk_dates,
            'recommendation': 'Wait to repurchase' if at_risk else 'No wash sale risk'
        }

    def optimize_withdrawal_order(
        self,
        target_amount: float,
        ordinary_income: float = 100000.0
    ) -> List[Dict]:
        """
        Optimize order of selling positions for tax efficiency.

        Args:
            target_amount: Amount needed from sales
            ordinary_income: Annual ordinary income

        Returns:
            List of positions to sell in optimal order
        """
        gains_df = self.calculate_unrealized_gains()

        # Score each position (lower score = better to sell)
        def calculate_sell_score(row):
            # Prefer long-term over short-term
            lt_bonus = -1000 if row['is_long_term'] else 1000

            # Prefer smaller gains (or bigger losses)
            gain_penalty = row['unrealized_gain_loss']

            # Combined score
            return gain_penalty + lt_bonus

        gains_df['sell_score'] = gains_df.apply(calculate_sell_score, axis=1)
        gains_df = gains_df.sort_values('sell_score')

        # Build withdrawal plan
        withdrawal_plan = []
        remaining = target_amount
        cumulative_tax = 0

        for _, row in gains_df.iterrows():
            if remaining <= 0:
                break

            sell_amount = min(remaining, row['current_value'])
            proportion = sell_amount / row['current_value']

            gain_from_sale = row['unrealized_gain_loss'] * proportion
            tax_on_sale = self._calculate_tax_on_gain(
                gain_from_sale,
                row['is_long_term'],
                ordinary_income
            )

            withdrawal_plan.append({
                'symbol': row['symbol'],
                'sell_value': sell_amount,
                'shares_to_sell': row['shares'] * proportion,
                'realized_gain_loss': gain_from_sale,
                'estimated_tax': tax_on_sale,
                'is_long_term': row['is_long_term']
            })

            remaining -= sell_amount
            cumulative_tax += tax_on_sale

        return withdrawal_plan

    def compare_tax_scenarios(
        self,
        scenario_1: Dict,
        scenario_2: Dict
    ) -> Dict:
        """
        Compare two tax scenarios.

        Args:
            scenario_1: First scenario with realized_gains, realized_losses, dividend_income
            scenario_2: Second scenario

        Returns:
            Comparison results
        """
        result_1 = self.estimate_annual_tax_impact(**scenario_1)
        result_2 = self.estimate_annual_tax_impact(**scenario_2)

        difference = result_1['total_investment_tax'] - result_2['total_investment_tax']

        return {
            'scenario_1': result_1,
            'scenario_2': result_2,
            'tax_difference': difference,
            'better_scenario': 1 if result_1['total_investment_tax'] < result_2['total_investment_tax'] else 2
        }


def calculate_qualified_dividend_income(
    dividends: pd.DataFrame,
    holding_period_days: pd.Series
) -> Tuple[float, float]:
    """
    Separate qualified from non-qualified dividends.

    Args:
        dividends: DataFrame with dividend amounts
        holding_period_days: Series with holding periods

    Returns:
        Tuple of (qualified_dividends, non_qualified_dividends)
    """
    # Simplified: dividends qualified if held > 60 days during 121-day period
    qualified_mask = holding_period_days > 60

    qualified = dividends[qualified_mask].sum() if not dividends.empty else 0
    non_qualified = dividends[~qualified_mask].sum() if not dividends.empty else 0

    return qualified, non_qualified
