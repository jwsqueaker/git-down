"""Client Reporting Service - Generate institutional-grade reports."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, date
import json
import io


class ClientReportGenerator:
    """Generate institutional client reports and fact sheets."""

    def __init__(self):
        self.report_sections = []

    def generate_executive_summary(
        self,
        portfolio_value: float,
        total_return: float,
        benchmark_return: float,
        period: str = 'QTD',
        inception_date: Optional[date] = None
    ) -> Dict:
        """Generate executive summary for client report."""
        active_return = total_return - benchmark_return

        if inception_date:
            days = (datetime.now().date() - inception_date).days
            years = days / 365.25
        else:
            years = 1

        return {
            'report_date': datetime.now().strftime('%B %d, %Y'),
            'period': period,
            'portfolio_value': portfolio_value,
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'active_return': active_return,
            'outperformed': active_return > 0,
            'years_since_inception': round(years, 1),
            'inception_date': inception_date.strftime('%B %d, %Y') if inception_date else 'N/A',
        }

    def generate_performance_table(
        self,
        returns_data: Dict[str, Dict[str, float]]
    ) -> pd.DataFrame:
        """
        Generate standardized performance table.

        Args:
            returns_data: {
                'Portfolio': {'MTD': 0.02, 'QTD': 0.05, ...},
                'Benchmark': {'MTD': 0.01, 'QTD': 0.04, ...}
            }
        """
        periods = ['MTD', 'QTD', 'YTD', '1Y', '3Y', '5Y', '10Y', 'SI']
        rows = []

        for name, returns in returns_data.items():
            row = {'Name': name}
            for period in periods:
                val = returns.get(period)
                row[period] = f"{val*100:.2f}%" if val is not None else 'N/A'
            rows.append(row)

        # Add active return row if portfolio and benchmark present
        if 'Portfolio' in returns_data and 'Benchmark' in returns_data:
            active_row = {'Name': 'Active Return'}
            for period in periods:
                p_val = returns_data['Portfolio'].get(period)
                b_val = returns_data['Benchmark'].get(period)
                if p_val is not None and b_val is not None:
                    active = p_val - b_val
                    active_row[period] = f"{active*100:+.2f}%"
                else:
                    active_row[period] = 'N/A'
            rows.append(active_row)

        return pd.DataFrame(rows)

    def generate_risk_statistics_table(
        self,
        risk_metrics: Dict[str, float],
        benchmark_metrics: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """Generate risk statistics comparison table."""
        metrics_display = {
            'annualized_return': ('Annualized Return', '{:.2%}'),
            'annualized_volatility': ('Annualized Volatility', '{:.2%}'),
            'sharpe_ratio': ('Sharpe Ratio', '{:.2f}'),
            'sortino_ratio': ('Sortino Ratio', '{:.2f}'),
            'max_drawdown': ('Maximum Drawdown', '{:.2%}'),
            'calmar_ratio': ('Calmar Ratio', '{:.2f}'),
            'beta': ('Beta', '{:.2f}'),
            'alpha': ('Alpha (Annualized)', '{:.2%}'),
            'information_ratio': ('Information Ratio', '{:.2f}'),
            'tracking_error': ('Tracking Error', '{:.2%}'),
            'up_capture': ('Up Capture Ratio', '{:.1f}%'),
            'down_capture': ('Down Capture Ratio', '{:.1f}%'),
        }

        rows = []
        for key, (label, fmt) in metrics_display.items():
            row = {'Metric': label}
            val = risk_metrics.get(key)
            row['Portfolio'] = fmt.format(val) if val is not None else 'N/A'

            if benchmark_metrics:
                b_val = benchmark_metrics.get(key)
                row['Benchmark'] = fmt.format(b_val) if b_val is not None else 'N/A'

            rows.append(row)

        return pd.DataFrame(rows)

    def generate_holdings_summary(
        self,
        positions: List[Dict],
        total_value: float
    ) -> pd.DataFrame:
        """Generate top holdings summary for client report."""
        sorted_positions = sorted(positions, key=lambda x: x.get('value', 0), reverse=True)

        rows = []
        for i, pos in enumerate(sorted_positions[:20]):
            rows.append({
                'Rank': i + 1,
                'Security': pos.get('description', pos.get('symbol', 'Unknown')),
                'Ticker': pos.get('symbol', ''),
                'Sector': pos.get('asset_class', 'N/A'),
                'Weight (%)': f"{pos.get('value', 0) / total_value * 100:.2f}" if total_value > 0 else '0.00',
                'Value': f"${pos.get('value', 0):,.0f}",
                'Return (%)': f"{pos.get('return_pct', 0):.2f}",
            })

        top_n_weight = sum(
            pos.get('value', 0) / total_value for pos in sorted_positions[:10]
        ) * 100 if total_value > 0 else 0

        df = pd.DataFrame(rows)
        return df

    def generate_allocation_summary(
        self,
        allocations: Dict[str, float],
        target_allocations: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """Generate asset allocation summary with drift analysis."""
        rows = []
        for asset_class, weight in sorted(allocations.items(), key=lambda x: x[1], reverse=True):
            row = {
                'Asset Class': asset_class,
                'Current (%)': f"{weight:.1f}",
            }
            if target_allocations:
                target = target_allocations.get(asset_class, 0)
                row['Target (%)'] = f"{target:.1f}"
                row['Drift (%)'] = f"{weight - target:+.1f}"
            rows.append(row)

        return pd.DataFrame(rows)

    def generate_commentary(
        self,
        portfolio_return: float,
        benchmark_return: float,
        top_contributors: List[Dict],
        bottom_contributors: List[Dict],
        market_context: Optional[str] = None
    ) -> str:
        """Generate performance commentary text."""
        active = portfolio_return - benchmark_return
        direction = "outperformed" if active > 0 else "underperformed"

        commentary = f"**Performance Overview**\n\n"
        commentary += f"The portfolio returned {portfolio_return*100:.2f}% during the period, "
        commentary += f"which {direction} the benchmark return of {benchmark_return*100:.2f}% "
        commentary += f"by {abs(active)*100:.2f}%.\n\n"

        if top_contributors:
            commentary += "**Top Contributors:**\n"
            for contrib in top_contributors[:3]:
                name = contrib.get('symbol', contrib.get('name', 'Unknown'))
                ret = contrib.get('contribution', 0)
                commentary += f"- {name}: contributed {ret*100:+.2f}% to portfolio return\n"
            commentary += "\n"

        if bottom_contributors:
            commentary += "**Bottom Contributors:**\n"
            for contrib in bottom_contributors[:3]:
                name = contrib.get('symbol', contrib.get('name', 'Unknown'))
                ret = contrib.get('contribution', 0)
                commentary += f"- {name}: detracted {abs(ret)*100:.2f}% from portfolio return\n"
            commentary += "\n"

        if market_context:
            commentary += f"**Market Context:**\n{market_context}\n"

        return commentary

    def generate_fee_disclosure(
        self,
        portfolio_value: float,
        management_fee_pct: float = 0.0075,
        performance_fee_pct: float = 0.0,
        gross_return: float = 0.0,
        hurdle_rate: float = 0.0
    ) -> Dict:
        """Generate fee calculation and disclosure."""
        management_fee = portfolio_value * management_fee_pct
        performance_fee = 0

        if performance_fee_pct > 0 and gross_return > hurdle_rate:
            excess_return = gross_return - hurdle_rate
            performance_fee = portfolio_value * excess_return * performance_fee_pct

        total_fees = management_fee + performance_fee
        net_return = gross_return - total_fees / portfolio_value if portfolio_value > 0 else gross_return

        return {
            'portfolio_value': portfolio_value,
            'gross_return_pct': gross_return * 100,
            'management_fee_pct': management_fee_pct * 100,
            'management_fee_dollar': management_fee,
            'performance_fee_pct': performance_fee_pct * 100,
            'performance_fee_dollar': performance_fee,
            'total_fees_dollar': total_fees,
            'total_fees_pct': total_fees / portfolio_value * 100 if portfolio_value > 0 else 0,
            'net_return_pct': net_return * 100,
            'fee_drag_pct': (gross_return - net_return) * 100,
        }

    def generate_full_report(
        self,
        portfolio_data: Dict,
        benchmark_data: Optional[Dict] = None,
        risk_data: Optional[Dict] = None,
        attribution_data: Optional[Dict] = None
    ) -> Dict:
        """Assemble a complete client report from component data."""
        report = {
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'sections': {},
        }

        # Executive Summary
        if portfolio_data:
            report['sections']['executive_summary'] = self.generate_executive_summary(
                portfolio_value=portfolio_data.get('total_value', 0),
                total_return=portfolio_data.get('total_return', 0),
                benchmark_return=benchmark_data.get('total_return', 0) if benchmark_data else 0,
            )

        # Performance Table
        if portfolio_data.get('period_returns'):
            perf_data = {'Portfolio': portfolio_data['period_returns']}
            if benchmark_data and benchmark_data.get('period_returns'):
                perf_data['Benchmark'] = benchmark_data['period_returns']
            report['sections']['performance_table'] = self.generate_performance_table(perf_data).to_dict('records')

        # Risk Statistics
        if risk_data:
            report['sections']['risk_statistics'] = self.generate_risk_statistics_table(risk_data).to_dict('records')

        # Holdings
        if portfolio_data.get('positions'):
            report['sections']['holdings'] = self.generate_holdings_summary(
                portfolio_data['positions'],
                portfolio_data.get('total_value', 0)
            ).to_dict('records')

        # Attribution
        if attribution_data:
            report['sections']['attribution'] = attribution_data

        # Commentary
        if portfolio_data.get('top_contributors') or portfolio_data.get('bottom_contributors'):
            report['sections']['commentary'] = self.generate_commentary(
                portfolio_data.get('total_return', 0),
                benchmark_data.get('total_return', 0) if benchmark_data else 0,
                portfolio_data.get('top_contributors', []),
                portfolio_data.get('bottom_contributors', []),
            )

        return report

    def export_report_data(self, report: Dict, format: str = 'json') -> str:
        """Export report data in specified format."""
        if format == 'json':
            return json.dumps(report, indent=2, default=str)
        elif format == 'csv':
            output = io.StringIO()
            for section_name, section_data in report.get('sections', {}).items():
                if isinstance(section_data, list) and section_data:
                    output.write(f"\n=== {section_name.upper()} ===\n")
                    df = pd.DataFrame(section_data)
                    df.to_csv(output, index=False)
                elif isinstance(section_data, dict):
                    output.write(f"\n=== {section_name.upper()} ===\n")
                    for key, val in section_data.items():
                        output.write(f"{key},{val}\n")
            return output.getvalue()
        else:
            return json.dumps(report, indent=2, default=str)
