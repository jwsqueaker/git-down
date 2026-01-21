"""Portfolio rebalancing assistant."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from models.portfolio import Position


class RebalancingAssistant:
    """Calculate rebalancing needs and generate trade recommendations."""

    def __init__(
        self,
        positions: List[Position],
        target_allocation: Dict[str, float],
        tolerance: float = 0.05
    ):
        """
        Initialize rebalancing assistant.

        Args:
            positions: Current portfolio positions
            target_allocation: Target allocation by symbol {symbol: weight}
            tolerance: Rebalancing tolerance (default 5%)
        """
        self.positions = positions
        self.target_allocation = target_allocation
        self.tolerance = tolerance

    def calculate_current_allocation(self) -> Dict[str, float]:
        """
        Calculate current portfolio allocation.

        Returns:
            Dictionary of current weights by symbol
        """
        total_value = sum(
            p.shares * (p.current_price or p.purchase_price)
            for p in self.positions
        )

        if total_value == 0:
            return {}

        allocation = {}
        for p in self.positions:
            value = p.shares * (p.current_price or p.purchase_price)
            allocation[p.symbol] = value / total_value

        return allocation

    def calculate_drift(self) -> pd.DataFrame:
        """
        Calculate allocation drift from targets.

        Returns:
            DataFrame with drift analysis
        """
        current = self.calculate_current_allocation()

        drift_data = []

        # All symbols (current + target)
        all_symbols = set(list(current.keys()) + list(self.target_allocation.keys()))

        for symbol in all_symbols:
            current_weight = current.get(symbol, 0.0)
            target_weight = self.target_allocation.get(symbol, 0.0)
            drift = current_weight - target_weight
            drift_pct = (drift / target_weight * 100) if target_weight > 0 else 0

            needs_rebalancing = abs(drift) > self.tolerance

            drift_data.append({
                'symbol': symbol,
                'current_weight': current_weight,
                'target_weight': target_weight,
                'drift': drift,
                'drift_pct': drift_pct,
                'needs_rebalancing': needs_rebalancing,
                'action': self._determine_action(drift)
            })

        df = pd.DataFrame(drift_data)
        return df.sort_values('drift', ascending=False)

    def _determine_action(self, drift: float) -> str:
        """Determine rebalancing action based on drift."""
        if abs(drift) <= self.tolerance:
            return 'Hold'
        elif drift > 0:
            return 'Sell'
        else:
            return 'Buy'

    def generate_rebalancing_trades(
        self,
        total_portfolio_value: Optional[float] = None,
        additional_contribution: float = 0.0
    ) -> List[Dict]:
        """
        Generate specific trade recommendations to rebalance.

        Args:
            total_portfolio_value: Current total value (calculated if not provided)
            additional_contribution: Additional cash to invest

        Returns:
            List of trade recommendations
        """
        if total_portfolio_value is None:
            total_portfolio_value = sum(
                p.shares * (p.current_price or p.purchase_price)
                for p in self.positions
            )

        # New total including contribution
        new_total_value = total_portfolio_value + additional_contribution

        current_allocation = self.calculate_current_allocation()

        trades = []

        for symbol, target_weight in self.target_allocation.items():
            target_value = new_total_value * target_weight
            current_value = total_portfolio_value * current_allocation.get(symbol, 0.0)

            trade_value = target_value - current_value

            if abs(trade_value) < 100:  # Ignore tiny trades
                continue

            # Find current position
            position = next((p for p in self.positions if p.symbol == symbol), None)
            current_price = position.current_price if position else None

            if current_price and current_price > 0:
                shares_to_trade = trade_value / current_price

                trades.append({
                    'symbol': symbol,
                    'action': 'Buy' if trade_value > 0 else 'Sell',
                    'shares': abs(shares_to_trade),
                    'value': abs(trade_value),
                    'current_price': current_price,
                    'current_value': current_value,
                    'target_value': target_value
                })

        return sorted(trades, key=lambda x: abs(x['value']), reverse=True)

    def calculate_rebalancing_frequency_recommendation(
        self,
        historical_returns: pd.DataFrame,
        rebalancing_frequencies: List[str] = ['monthly', 'quarterly', 'semiannual', 'annual']
    ) -> Dict:
        """
        Analyze optimal rebalancing frequency based on historical data.

        Args:
            historical_returns: DataFrame with historical returns
            rebalancing_frequencies: Frequencies to test

        Returns:
            Dictionary with frequency analysis
        """
        # Simplified analysis
        results = {}

        for freq in rebalancing_frequencies:
            # Estimate turnover and costs
            if freq == 'monthly':
                annual_rebalances = 12
            elif freq == 'quarterly':
                annual_rebalances = 4
            elif freq == 'semiannual':
                annual_rebalances = 2
            else:  # annual
                annual_rebalances = 1

            # Estimated trading costs (simplified)
            estimated_cost = annual_rebalances * 0.001 * len(self.target_allocation)  # 0.1% per rebalance

            results[freq] = {
                'annual_rebalances': annual_rebalances,
                'estimated_annual_cost_pct': estimated_cost * 100,
                'recommendation_score': 1 / (annual_rebalances * 0.5)  # Favor less frequent
            }

        # Find best option
        best = max(results.items(), key=lambda x: x[1]['recommendation_score'])

        return {
            'analysis': results,
            'recommended_frequency': best[0],
            'reason': f"Balances rebalancing benefit vs. trading costs"
        }

    def tax_aware_rebalancing(
        self,
        positions_with_gains: pd.DataFrame,
        target_trades: List[Dict]
    ) -> List[Dict]:
        """
        Adjust rebalancing trades to minimize tax impact.

        Args:
            positions_with_gains: DataFrame with unrealized gains info
            target_trades: Original trade recommendations

        Returns:
            Tax-optimized trade list
        """
        optimized_trades = []

        for trade in target_trades:
            symbol = trade['symbol']

            # Find position info
            position_info = positions_with_gains[
                positions_with_gains['symbol'] == symbol
            ]

            if position_info.empty or trade['action'] == 'Buy':
                # No tax impact for buys or new positions
                optimized_trades.append(trade)
                continue

            # Check for tax impact on sells
            if trade['action'] == 'Sell':
                unrealized_gain = position_info['unrealized_gain_loss'].iloc[0]

                # If selling at a loss, prioritize
                if unrealized_gain < 0:
                    trade['priority'] = 'High'
                    trade['note'] = 'Tax-loss harvesting opportunity'
                # If short-term gain, deprioritize
                elif not position_info['is_long_term'].iloc[0]:
                    trade['priority'] = 'Low'
                    trade['note'] = 'Short-term gain - consider waiting'
                else:
                    trade['priority'] = 'Medium'
                    trade['note'] = 'Long-term gain'

                optimized_trades.append(trade)

        return sorted(optimized_trades, key=lambda x: {'High': 3, 'Medium': 2, 'Low': 1}.get(x.get('priority', 'Medium'), 2), reverse=True)

    def calculate_portfolio_turnover(
        self,
        trades: List[Dict],
        total_portfolio_value: float
    ) -> float:
        """
        Calculate portfolio turnover from trades.

        Args:
            trades: List of trades
            total_portfolio_value: Total portfolio value

        Returns:
            Turnover rate (as decimal)
        """
        total_traded = sum(trade['value'] for trade in trades)
        turnover = total_traded / total_portfolio_value if total_portfolio_value > 0 else 0

        return turnover


def suggest_target_allocation(
    risk_tolerance: str,
    age: int,
    years_to_retirement: int
) -> Dict[str, float]:
    """
    Suggest target allocation based on investor profile.

    Args:
        risk_tolerance: 'conservative', 'moderate', or 'aggressive'
        age: Investor age
        years_to_retirement: Years until retirement

    Returns:
        Suggested allocation dictionary
    """
    # Rule of thumb: stocks = 110 - age (for moderate risk)
    base_stock_pct = max(20, min(90, 110 - age))

    # Adjust for risk tolerance
    if risk_tolerance == 'conservative':
        stock_pct = base_stock_pct * 0.7
    elif risk_tolerance == 'aggressive':
        stock_pct = base_stock_pct * 1.2
    else:  # moderate
        stock_pct = base_stock_pct

    # Cap between 20-90%
    stock_pct = max(20, min(90, stock_pct))
    bond_pct = 100 - stock_pct

    return {
        'stocks': stock_pct / 100,
        'bonds': bond_pct / 100,
        'suggested_stocks_etf': 'VTI or SPY',
        'suggested_bonds_etf': 'BND or AGG'
    }
