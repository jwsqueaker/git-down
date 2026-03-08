"""Performance Attribution Service - Brinson and factor-based attribution."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import yfinance as yf


class PerformanceAttribution:
    """Institutional-grade performance attribution analysis."""

    def __init__(self, trading_days: int = 252):
        self.trading_days = trading_days

    def brinson_attribution(
        self,
        portfolio_weights: Dict[str, float],
        benchmark_weights: Dict[str, float],
        portfolio_returns: Dict[str, float],
        benchmark_returns: Dict[str, float],
        sectors: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Brinson-Fachler performance attribution.

        Decomposes active return into:
        - Allocation Effect: Over/underweight in outperforming sectors
        - Selection Effect: Picking better securities within sectors
        - Interaction Effect: Cross-effect of allocation and selection

        Args:
            portfolio_weights: {sector/symbol: weight}
            benchmark_weights: {sector/symbol: weight}
            portfolio_returns: {sector/symbol: return}
            benchmark_returns: {sector/symbol: return}
            sectors: Optional {symbol: sector} mapping for position-level analysis
        """
        if sectors:
            portfolio_weights, portfolio_returns = self._aggregate_to_sectors(
                portfolio_weights, portfolio_returns, sectors)
            benchmark_weights, benchmark_returns = self._aggregate_to_sectors(
                benchmark_weights, benchmark_returns, sectors)

        all_sectors = set(list(portfolio_weights.keys()) + list(benchmark_weights.keys()))

        total_port_return = sum(
            portfolio_weights.get(s, 0) * portfolio_returns.get(s, 0)
            for s in all_sectors
        )
        total_bench_return = sum(
            benchmark_weights.get(s, 0) * benchmark_returns.get(s, 0)
            for s in all_sectors
        )

        attribution = {}
        total_allocation = 0
        total_selection = 0
        total_interaction = 0

        for sector in all_sectors:
            wp = portfolio_weights.get(sector, 0)
            wb = benchmark_weights.get(sector, 0)
            rp = portfolio_returns.get(sector, 0)
            rb = benchmark_returns.get(sector, 0)

            allocation = (wp - wb) * (rb - total_bench_return)
            selection = wb * (rp - rb)
            interaction = (wp - wb) * (rp - rb)

            attribution[sector] = {
                'portfolio_weight': wp,
                'benchmark_weight': wb,
                'active_weight': wp - wb,
                'portfolio_return': rp,
                'benchmark_return': rb,
                'allocation_effect': allocation,
                'selection_effect': selection,
                'interaction_effect': interaction,
                'total_effect': allocation + selection + interaction,
            }

            total_allocation += allocation
            total_selection += selection
            total_interaction += interaction

        active_return = total_port_return - total_bench_return

        return {
            'sector_attribution': attribution,
            'total_allocation_effect': total_allocation,
            'total_selection_effect': total_selection,
            'total_interaction_effect': total_interaction,
            'active_return': active_return,
            'portfolio_return': total_port_return,
            'benchmark_return': total_bench_return,
        }

    def _aggregate_to_sectors(
        self,
        weights: Dict[str, float],
        returns: Dict[str, float],
        sectors: Dict[str, str]
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Aggregate position-level data to sector level."""
        sector_weights = {}
        sector_return_contrib = {}

        for symbol, weight in weights.items():
            sector = sectors.get(symbol, 'Other')
            sector_weights[sector] = sector_weights.get(sector, 0) + weight
            ret = returns.get(symbol, 0)
            sector_return_contrib[sector] = sector_return_contrib.get(sector, 0) + weight * ret

        sector_returns = {}
        for sector, w in sector_weights.items():
            sector_returns[sector] = sector_return_contrib[sector] / w if w > 0 else 0

        return sector_weights, sector_returns

    def multi_period_attribution(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        frequency: str = 'M'
    ) -> pd.DataFrame:
        """
        Multi-period performance attribution with geometric linking.

        Args:
            portfolio_returns: Daily portfolio returns
            benchmark_returns: Daily benchmark returns
            frequency: Resampling frequency ('M', 'Q', 'Y')
        """
        port_price = (1 + portfolio_returns).cumprod()
        bench_price = (1 + benchmark_returns).cumprod()

        port_periodic = port_price.resample(frequency).last().pct_change().dropna()
        bench_periodic = bench_price.resample(frequency).last().pct_change().dropna()

        aligned = pd.DataFrame({
            'portfolio': port_periodic,
            'benchmark': bench_periodic,
        }).dropna()

        aligned['active_return'] = aligned['portfolio'] - aligned['benchmark']
        aligned['cumulative_portfolio'] = (1 + aligned['portfolio']).cumprod() - 1
        aligned['cumulative_benchmark'] = (1 + aligned['benchmark']).cumprod() - 1
        aligned['cumulative_active'] = aligned['cumulative_portfolio'] - aligned['cumulative_benchmark']

        return aligned

    def calculate_contribution_analysis(
        self,
        position_returns: pd.DataFrame,
        weights: Dict[str, float],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Calculate each position's contribution to total portfolio return.
        """
        if start_date:
            position_returns = position_returns[position_returns.index >= start_date]
        if end_date:
            position_returns = position_returns[position_returns.index <= end_date]

        clean_returns = position_returns.dropna()
        if clean_returns.empty:
            return {'error': 'No data available'}

        total_returns = {}
        contributions = {}
        portfolio_return = 0

        for col in clean_returns.columns:
            total_ret = (1 + clean_returns[col]).prod() - 1
            total_returns[col] = total_ret
            weight = weights.get(col, 0)
            contrib = weight * total_ret
            contributions[col] = contrib
            portfolio_return += contrib

        pct_contribution = {}
        for col, contrib in contributions.items():
            pct_contribution[col] = (contrib / portfolio_return * 100) if portfolio_return != 0 else 0

        sorted_contrib = sorted(contributions.items(), key=lambda x: x[1], reverse=True)

        return {
            'position_returns': total_returns,
            'position_contributions': contributions,
            'pct_contributions': pct_contribution,
            'portfolio_return': portfolio_return,
            'top_contributors': sorted_contrib[:5],
            'bottom_contributors': sorted_contrib[-5:],
        }

    def calculate_risk_adjusted_attribution(
        self,
        position_returns: pd.DataFrame,
        weights: Dict[str, float],
        risk_free_rate: float = 0.045
    ) -> Dict:
        """
        Risk-adjusted return attribution per position.
        """
        daily_rf = risk_free_rate / self.trading_days
        clean_returns = position_returns.dropna()

        results = {}
        for col in clean_returns.columns:
            ret = clean_returns[col]
            ann_return = ret.mean() * self.trading_days
            ann_vol = ret.std() * np.sqrt(self.trading_days)
            excess_return = ann_return - risk_free_rate

            sharpe = excess_return / ann_vol if ann_vol > 0 else 0

            downside_ret = ret[ret < daily_rf]
            downside_vol = downside_ret.std() * np.sqrt(self.trading_days) if len(downside_ret) > 0 else 0
            sortino = excess_return / downside_vol if downside_vol > 0 else 0

            cumulative = (1 + ret).cumprod()
            running_max = cumulative.expanding().max()
            max_dd = ((cumulative - running_max) / running_max).min()

            calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

            weight = weights.get(col, 0)

            results[col] = {
                'weight': weight,
                'annualized_return': ann_return,
                'annualized_volatility': ann_vol,
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'max_drawdown': max_dd,
                'calmar_ratio': calmar,
                'risk_contribution': weight * ann_vol,
                'return_contribution': weight * ann_return,
                'return_risk_ratio': (weight * ann_return) / (weight * ann_vol) if ann_vol > 0 and weight > 0 else 0,
            }

        return results

    def calculate_batting_average(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        frequency: str = 'M'
    ) -> Dict:
        """
        Calculate batting average - % of periods outperforming benchmark.
        """
        port_price = (1 + portfolio_returns).cumprod()
        bench_price = (1 + benchmark_returns).cumprod()

        port_periodic = port_price.resample(frequency).last().pct_change().dropna()
        bench_periodic = bench_price.resample(frequency).last().pct_change().dropna()

        aligned = pd.DataFrame({'port': port_periodic, 'bench': bench_periodic}).dropna()
        outperform = aligned['port'] > aligned['bench']

        up_market = aligned[aligned['bench'] > 0]
        down_market = aligned[aligned['bench'] <= 0]

        up_capture = (1 + aligned.loc[aligned['bench'] > 0, 'port']).prod() / \
                     (1 + aligned.loc[aligned['bench'] > 0, 'bench']).prod() * 100 if len(up_market) > 0 else 100

        down_capture = (1 + aligned.loc[aligned['bench'] <= 0, 'port']).prod() / \
                       (1 + aligned.loc[aligned['bench'] <= 0, 'bench']).prod() * 100 if len(down_market) > 0 else 100

        freq_label = {'D': 'Daily', 'W': 'Weekly', 'M': 'Monthly', 'Q': 'Quarterly', 'Y': 'Annual'}.get(frequency, frequency)

        return {
            'batting_average': outperform.sum() / len(outperform) * 100 if len(outperform) > 0 else 0,
            'periods_outperformed': int(outperform.sum()),
            'total_periods': len(outperform),
            'frequency': freq_label,
            'up_capture_ratio': up_capture,
            'down_capture_ratio': down_capture,
            'capture_ratio': up_capture / down_capture if down_capture != 0 else float('inf'),
            'avg_outperformance': (aligned['port'] - aligned['bench'])[outperform].mean() if outperform.any() else 0,
            'avg_underperformance': (aligned['port'] - aligned['bench'])[~outperform].mean() if (~outperform).any() else 0,
        }

    def generate_attribution_report(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        position_returns: Optional[pd.DataFrame] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """Generate comprehensive performance attribution report."""
        report = {}

        report['multi_period'] = self.multi_period_attribution(
            portfolio_returns, benchmark_returns, frequency='M'
        )

        for freq in ['M', 'Q']:
            report[f'batting_average_{freq}'] = self.calculate_batting_average(
                portfolio_returns, benchmark_returns, frequency=freq
            )

        if position_returns is not None and weights is not None:
            report['contribution'] = self.calculate_contribution_analysis(
                position_returns, weights
            )
            report['risk_adjusted'] = self.calculate_risk_adjusted_attribution(
                position_returns, weights
            )

        return report
