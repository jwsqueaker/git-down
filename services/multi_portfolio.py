"""Multi-Portfolio Management Service - Manage multiple funds/accounts."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, date
from dataclasses import dataclass, field
from models.portfolio import Position, PortfolioSnapshot


@dataclass
class Fund:
    """Represents a managed fund or account."""
    name: str
    fund_id: str
    positions: List[Position]
    benchmark: str = '^GSPC'
    inception_date: Optional[date] = None
    strategy: str = 'Long Only'
    currency: str = 'USD'
    management_fee: float = 0.0
    performance_fee: float = 0.0
    high_water_mark: float = 0.0
    aum: float = 0.0
    cash: float = 0.0
    metadata: Dict = field(default_factory=dict)


class MultiPortfolioManager:
    """Manage and compare multiple portfolios/funds."""

    def __init__(self):
        self.funds: Dict[str, Fund] = {}

    def add_fund(self, fund: Fund) -> None:
        """Add a fund to the manager."""
        self.funds[fund.fund_id] = fund

    def remove_fund(self, fund_id: str) -> bool:
        """Remove a fund from the manager."""
        if fund_id in self.funds:
            del self.funds[fund_id]
            return True
        return False

    def get_fund(self, fund_id: str) -> Optional[Fund]:
        """Get a fund by ID."""
        return self.funds.get(fund_id)

    def list_funds(self) -> List[Dict]:
        """List all managed funds with summary info."""
        summaries = []
        for fund_id, fund in self.funds.items():
            total_value = sum(p.current_value for p in fund.positions) + fund.cash
            total_cost = sum(p.cost_basis for p in fund.positions) + fund.cash

            summaries.append({
                'fund_id': fund_id,
                'name': fund.name,
                'strategy': fund.strategy,
                'benchmark': fund.benchmark,
                'n_positions': len(fund.positions),
                'total_value': total_value,
                'total_cost': total_cost,
                'total_return_pct': (total_value / total_cost - 1) * 100 if total_cost > 0 else 0,
                'currency': fund.currency,
                'inception_date': fund.inception_date,
            })

        return summaries

    def get_aggregate_view(self) -> Dict:
        """Get aggregate view across all funds."""
        total_aum = 0
        total_cost = 0
        all_positions = {}
        sector_exposure = {}

        for fund_id, fund in self.funds.items():
            for pos in fund.positions:
                total_aum += pos.current_value
                total_cost += pos.cost_basis

                if pos.symbol in all_positions:
                    all_positions[pos.symbol]['value'] += pos.current_value
                    all_positions[pos.symbol]['cost'] += pos.cost_basis
                    all_positions[pos.symbol]['funds'].append(fund.name)
                else:
                    all_positions[pos.symbol] = {
                        'value': pos.current_value,
                        'cost': pos.cost_basis,
                        'asset_class': pos.asset_class,
                        'funds': [fund.name],
                    }

            total_aum += fund.cash
            total_cost += fund.cash

        # Calculate aggregate weights
        for symbol, info in all_positions.items():
            info['weight'] = info['value'] / total_aum if total_aum > 0 else 0
            ac = info.get('asset_class', 'Other')
            sector_exposure[ac] = sector_exposure.get(ac, 0) + info['value']

        # Concentration analysis
        position_weights = sorted(
            [(s, i['weight']) for s, i in all_positions.items()],
            key=lambda x: x[1], reverse=True
        )
        top_10_concentration = sum(w for _, w in position_weights[:10])

        # HHI (Herfindahl-Hirschman Index)
        hhi = sum(w ** 2 for _, w in position_weights) * 10000

        return {
            'total_aum': total_aum,
            'total_cost_basis': total_cost,
            'total_return_pct': (total_aum / total_cost - 1) * 100 if total_cost > 0 else 0,
            'n_funds': len(self.funds),
            'n_unique_positions': len(all_positions),
            'positions': all_positions,
            'sector_exposure': sector_exposure,
            'top_10_concentration': top_10_concentration,
            'hhi': hhi,
            'diversification': 'Well Diversified' if hhi < 1500 else ('Moderate' if hhi < 2500 else 'Concentrated'),
        }

    def compare_funds(self, fund_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Compare performance metrics across funds.
        """
        if fund_ids is None:
            fund_ids = list(self.funds.keys())

        comparison = []
        for fund_id in fund_ids:
            fund = self.funds.get(fund_id)
            if not fund:
                continue

            total_value = sum(p.current_value for p in fund.positions) + fund.cash
            total_cost = sum(p.cost_basis for p in fund.positions) + fund.cash
            total_return = (total_value / total_cost - 1) if total_cost > 0 else 0

            n_pos = len(fund.positions)
            weights = [p.current_value / total_value for p in fund.positions] if total_value > 0 else []
            hhi = sum(w ** 2 for w in weights) * 10000 if weights else 0

            position_returns = [(p.current_value / p.cost_basis - 1) for p in fund.positions if p.cost_basis > 0]
            avg_pos_return = np.mean(position_returns) if position_returns else 0
            best_pos = max(fund.positions, key=lambda p: p.unrealized_gain_loss_pct) if fund.positions else None
            worst_pos = min(fund.positions, key=lambda p: p.unrealized_gain_loss_pct) if fund.positions else None

            comparison.append({
                'Fund': fund.name,
                'Strategy': fund.strategy,
                'AUM': total_value,
                'Positions': n_pos,
                'Return (%)': round(total_return * 100, 2),
                'Avg Position Return (%)': round(avg_pos_return * 100, 2),
                'Best Position': best_pos.symbol if best_pos else 'N/A',
                'Worst Position': worst_pos.symbol if worst_pos else 'N/A',
                'Concentration (HHI)': round(hhi, 0),
                'Benchmark': fund.benchmark,
            })

        return pd.DataFrame(comparison)

    def find_overlap(self, fund_id_1: str, fund_id_2: str) -> Dict:
        """Find position overlap between two funds."""
        fund1 = self.funds.get(fund_id_1)
        fund2 = self.funds.get(fund_id_2)

        if not fund1 or not fund2:
            return {'error': 'Fund not found'}

        symbols1 = {p.symbol for p in fund1.positions}
        symbols2 = {p.symbol for p in fund2.positions}

        common = symbols1 & symbols2
        only_1 = symbols1 - symbols2
        only_2 = symbols2 - symbols1

        total_1 = sum(p.current_value for p in fund1.positions)
        total_2 = sum(p.current_value for p in fund2.positions)

        overlap_weight_1 = sum(
            p.current_value / total_1 for p in fund1.positions if p.symbol in common
        ) if total_1 > 0 else 0

        overlap_weight_2 = sum(
            p.current_value / total_2 for p in fund2.positions if p.symbol in common
        ) if total_2 > 0 else 0

        return {
            'fund_1': fund1.name,
            'fund_2': fund2.name,
            'common_positions': list(common),
            'n_common': len(common),
            'only_in_fund_1': list(only_1),
            'only_in_fund_2': list(only_2),
            'overlap_weight_fund_1': overlap_weight_1 * 100,
            'overlap_weight_fund_2': overlap_weight_2 * 100,
            'jaccard_similarity': len(common) / len(symbols1 | symbols2) * 100 if symbols1 | symbols2 else 0,
        }

    def calculate_firm_level_exposure(self) -> Dict:
        """Calculate firm-wide risk exposure across all funds."""
        aggregate = self.get_aggregate_view()

        # Cross-fund concentration risk
        position_fund_count = {}
        for fund in self.funds.values():
            for pos in fund.positions:
                if pos.symbol not in position_fund_count:
                    position_fund_count[pos.symbol] = 0
                position_fund_count[pos.symbol] += 1

        widespread_positions = {
            s: c for s, c in position_fund_count.items()
            if c > len(self.funds) * 0.5
        }

        # Fund-level AUM distribution
        fund_aums = {}
        total_aum = 0
        for fund_id, fund in self.funds.items():
            aum = sum(p.current_value for p in fund.positions) + fund.cash
            fund_aums[fund.name] = aum
            total_aum += aum

        # Largest fund concentration
        max_fund_pct = max(fund_aums.values()) / total_aum * 100 if total_aum > 0 else 0

        return {
            'total_firm_aum': total_aum,
            'n_funds': len(self.funds),
            'n_unique_positions': aggregate['n_unique_positions'],
            'fund_aum_distribution': fund_aums,
            'largest_fund_pct': max_fund_pct,
            'widespread_positions': widespread_positions,
            'aggregate_concentration': aggregate['top_10_concentration'] * 100,
            'aggregate_hhi': aggregate['hhi'],
            'sector_exposure': aggregate['sector_exposure'],
        }

    def generate_multi_portfolio_report(self) -> Dict:
        """Generate comprehensive multi-portfolio report."""
        return {
            'fund_list': self.list_funds(),
            'comparison': self.compare_funds().to_dict('records'),
            'aggregate': self.get_aggregate_view(),
            'firm_exposure': self.calculate_firm_level_exposure(),
        }
