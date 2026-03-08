"""Liquidity Analysis Service - Trading volume, market impact, and liquidity risk."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import yfinance as yf


class LiquidityAnalyzer:
    """Institutional liquidity analysis and market impact estimation."""

    # Liquidity tiers
    LIQUIDITY_TIERS = {
        'Highly Liquid': {'min_adv': 50_000_000, 'max_spread_bps': 5, 'color': '#2ecc71'},
        'Liquid': {'min_adv': 10_000_000, 'max_spread_bps': 20, 'color': '#3498db'},
        'Moderately Liquid': {'min_adv': 1_000_000, 'max_spread_bps': 50, 'color': '#f39c12'},
        'Illiquid': {'min_adv': 100_000, 'max_spread_bps': 200, 'color': '#e74c3c'},
        'Highly Illiquid': {'min_adv': 0, 'max_spread_bps': float('inf'), 'color': '#8e44ad'},
    }

    def __init__(self, trading_days: int = 252):
        self.trading_days = trading_days

    def analyze_position_liquidity(
        self,
        symbol: str,
        position_value: float,
        lookback_days: int = 90
    ) -> Dict:
        """
        Analyze liquidity for a single position.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 30)

        try:
            data = yf.download(symbol, start=start_date.strftime('%Y-%m-%d'),
                               end=end_date.strftime('%Y-%m-%d'), progress=False)
        except Exception:
            return {'symbol': symbol, 'error': 'Unable to fetch data'}

        if data.empty:
            return {'symbol': symbol, 'error': 'No data available'}

        if isinstance(data.columns, pd.MultiIndex):
            volume = data[('Volume', symbol)]
            close = data[('Close', symbol)]
            high = data[('High', symbol)]
            low = data[('Low', symbol)]
        else:
            volume = data['Volume']
            close = data['Close']
            high = data['High']
            low = data['Low']

        avg_volume = volume.tail(lookback_days).mean()
        avg_price = close.tail(lookback_days).mean()
        adv = avg_volume * avg_price  # Average Daily Value traded

        # Bid-ask spread proxy using high-low spread
        spread_pct = ((high - low) / close).tail(lookback_days).mean()
        spread_bps = spread_pct * 10000

        # Days to liquidate (assuming 10% of ADV per day)
        participation_rate = 0.10
        days_to_liquidate = position_value / (adv * participation_rate) if adv > 0 else float('inf')

        # Amihud illiquidity ratio
        returns = close.pct_change().dropna()
        dollar_volume = volume * close
        amihud = (returns.abs() / dollar_volume).tail(lookback_days).mean()

        # Volume volatility
        volume_vol = volume.tail(lookback_days).std() / avg_volume if avg_volume > 0 else 0

        # Classify liquidity tier
        tier = 'Highly Illiquid'
        for tier_name, criteria in self.LIQUIDITY_TIERS.items():
            if adv >= criteria['min_adv'] and spread_bps <= criteria['max_spread_bps']:
                tier = tier_name
                break

        # Market impact estimate (square-root model)
        market_impact = self._estimate_market_impact(
            position_value, adv, spread_bps / 10000, avg_price
        )

        return {
            'symbol': symbol,
            'position_value': position_value,
            'avg_daily_volume': avg_volume,
            'avg_daily_value': adv,
            'avg_price': avg_price,
            'spread_bps': spread_bps,
            'days_to_liquidate_10pct': days_to_liquidate,
            'days_to_liquidate_25pct': position_value / (adv * 0.25) if adv > 0 else float('inf'),
            'amihud_illiquidity': amihud,
            'volume_volatility': volume_vol,
            'liquidity_tier': tier,
            'market_impact': market_impact,
            'pct_of_adv': position_value / adv * 100 if adv > 0 else float('inf'),
        }

    def _estimate_market_impact(
        self,
        trade_value: float,
        adv: float,
        spread: float,
        price: float,
        volatility: float = 0.02
    ) -> Dict:
        """
        Estimate market impact using the square-root model.

        Market Impact = spread/2 + sigma * sqrt(Q/V)

        Where:
        - sigma = daily volatility
        - Q = trade size in shares
        - V = average daily volume
        """
        if adv <= 0 or price <= 0:
            return {'total_cost_pct': 0, 'total_cost_dollar': 0}

        participation = trade_value / adv

        # Half spread cost
        half_spread = spread / 2

        # Temporary impact (square root model)
        temp_impact = volatility * np.sqrt(participation)

        # Permanent impact (typically ~1/3 of temporary)
        perm_impact = temp_impact / 3

        total_impact = half_spread + temp_impact + perm_impact
        total_cost = total_impact * trade_value

        return {
            'half_spread_cost_pct': half_spread * 100,
            'temporary_impact_pct': temp_impact * 100,
            'permanent_impact_pct': perm_impact * 100,
            'total_cost_pct': total_impact * 100,
            'total_cost_dollar': total_cost,
            'participation_rate': participation * 100,
        }

    def analyze_portfolio_liquidity(
        self,
        positions: Dict[str, float],
        lookback_days: int = 90
    ) -> Dict:
        """
        Analyze liquidity across entire portfolio.

        Args:
            positions: {symbol: position_value}
            lookback_days: Historical lookback period
        """
        total_value = sum(positions.values())
        position_analysis = {}
        tier_distribution = {}
        total_liquidation_cost = 0
        max_days_to_liquidate = 0

        for symbol, value in positions.items():
            analysis = self.analyze_position_liquidity(symbol, value, lookback_days)
            position_analysis[symbol] = analysis

            if 'error' not in analysis:
                tier = analysis['liquidity_tier']
                tier_distribution[tier] = tier_distribution.get(tier, 0) + value / total_value

                if 'market_impact' in analysis:
                    total_liquidation_cost += analysis['market_impact'].get('total_cost_dollar', 0)

                dtl = analysis.get('days_to_liquidate_10pct', 0)
                if dtl != float('inf'):
                    max_days_to_liquidate = max(max_days_to_liquidate, dtl)

        # Portfolio liquidity score (0-100)
        liquid_weight = tier_distribution.get('Highly Liquid', 0) + tier_distribution.get('Liquid', 0)
        mod_liquid_weight = tier_distribution.get('Moderately Liquid', 0)
        illiquid_weight = tier_distribution.get('Illiquid', 0) + tier_distribution.get('Highly Illiquid', 0)
        liquidity_score = liquid_weight * 100 + mod_liquid_weight * 60 + illiquid_weight * 20

        # Liquidity-at-Risk: What % can be liquidated in 1, 5, 10 days
        lar = self._calculate_liquidity_at_risk(position_analysis, total_value)

        return {
            'position_analysis': position_analysis,
            'tier_distribution': tier_distribution,
            'total_portfolio_value': total_value,
            'total_liquidation_cost': total_liquidation_cost,
            'liquidation_cost_pct': total_liquidation_cost / total_value * 100 if total_value > 0 else 0,
            'max_days_to_full_liquidation': max_days_to_liquidate,
            'liquidity_score': min(100, max(0, liquidity_score)),
            'liquidity_at_risk': lar,
        }

    def _calculate_liquidity_at_risk(
        self,
        position_analysis: Dict,
        total_value: float
    ) -> Dict:
        """Calculate what percentage can be liquidated within N days."""
        horizons = [1, 3, 5, 10, 20]
        lar = {}

        for days in horizons:
            liquidatable = 0
            for symbol, analysis in position_analysis.items():
                if 'error' in analysis:
                    continue
                adv = analysis.get('avg_daily_value', 0)
                pos_value = analysis.get('position_value', 0)
                max_liquidatable = min(pos_value, adv * 0.10 * days)
                liquidatable += max_liquidatable

            lar[f'{days}_day'] = {
                'liquidatable_value': min(liquidatable, total_value),
                'pct_of_portfolio': min(100, liquidatable / total_value * 100) if total_value > 0 else 0,
            }

        return lar

    def calculate_redemption_risk(
        self,
        portfolio_positions: Dict[str, float],
        redemption_amount: float,
        urgency: str = 'normal'
    ) -> Dict:
        """
        Assess the impact of a redemption/withdrawal on the portfolio.

        Args:
            portfolio_positions: {symbol: value}
            redemption_amount: Amount to redeem
            urgency: 'urgent' (1 day), 'normal' (5 days), 'planned' (20 days)
        """
        days_map = {'urgent': 1, 'normal': 5, 'planned': 20}
        available_days = days_map.get(urgency, 5)
        total_value = sum(portfolio_positions.values())

        if redemption_amount > total_value:
            return {'error': 'Redemption exceeds portfolio value'}

        redemption_pct = redemption_amount / total_value

        # Pro-rata liquidation plan
        liquidation_plan = {}
        total_impact = 0

        for symbol, value in portfolio_positions.items():
            sell_amount = value * redemption_pct
            analysis = self.analyze_position_liquidity(symbol, sell_amount, lookback_days=60)

            if 'error' not in analysis:
                impact = analysis.get('market_impact', {}).get('total_cost_dollar', 0)
                dtl = analysis.get('days_to_liquidate_10pct', float('inf'))
                feasible = dtl <= available_days

                liquidation_plan[symbol] = {
                    'sell_amount': sell_amount,
                    'market_impact': impact,
                    'days_needed': dtl,
                    'feasible': feasible,
                }
                total_impact += impact

        feasible_count = sum(1 for v in liquidation_plan.values() if v.get('feasible', False))
        total_positions = len(liquidation_plan)

        return {
            'redemption_amount': redemption_amount,
            'redemption_pct': redemption_pct * 100,
            'urgency': urgency,
            'available_days': available_days,
            'liquidation_plan': liquidation_plan,
            'total_market_impact': total_impact,
            'impact_pct': total_impact / redemption_amount * 100 if redemption_amount > 0 else 0,
            'feasible_positions': feasible_count,
            'total_positions': total_positions,
            'is_feasible': feasible_count == total_positions,
        }

    def generate_liquidity_report(
        self,
        positions: Dict[str, float]
    ) -> Dict:
        """Generate comprehensive liquidity analysis report."""
        return self.analyze_portfolio_liquidity(positions)
