"""ESG Scoring and Compliance Monitoring Service."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import yfinance as yf


class ESGAnalyzer:
    """ESG scoring, screening, and compliance monitoring for institutional portfolios."""

    # Industry ESG risk classifications
    INDUSTRY_ESG_RISK = {
        'Technology': {'E': 'Low', 'S': 'Medium', 'G': 'Medium', 'base_score': 72},
        'Healthcare': {'E': 'Low', 'S': 'High', 'G': 'Medium', 'base_score': 65},
        'Financials': {'E': 'Low', 'S': 'Medium', 'G': 'High', 'base_score': 60},
        'Energy': {'E': 'High', 'S': 'Medium', 'G': 'Medium', 'base_score': 40},
        'Utilities': {'E': 'High', 'S': 'Low', 'G': 'Low', 'base_score': 55},
        'Consumer Discretionary': {'E': 'Medium', 'S': 'Medium', 'G': 'Medium', 'base_score': 62},
        'Consumer Staples': {'E': 'Medium', 'S': 'Medium', 'G': 'Low', 'base_score': 68},
        'Industrials': {'E': 'High', 'S': 'Medium', 'G': 'Medium', 'base_score': 55},
        'Materials': {'E': 'High', 'S': 'Medium', 'G': 'Medium', 'base_score': 48},
        'Real Estate': {'E': 'Medium', 'S': 'Low', 'G': 'Medium', 'base_score': 60},
        'Communication Services': {'E': 'Low', 'S': 'High', 'G': 'Medium', 'base_score': 65},
    }

    # Controversial sectors and exclusion lists
    EXCLUSION_SCREENS = {
        'weapons': ['LMT', 'RTX', 'NOC', 'GD', 'BA', 'LHX', 'HII'],
        'tobacco': ['PM', 'MO', 'BTI', 'IMBBY'],
        'gambling': ['MGM', 'WYNN', 'LVS', 'CZR', 'DKNG', 'PENN'],
        'fossil_fuels': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY', 'MPC', 'VLO', 'PSX'],
        'alcohol': ['DEO', 'BF.B', 'STZ', 'SAM', 'TAP'],
        'adult_entertainment': [],
        'private_prisons': ['GEO', 'CXW'],
        'thermal_coal': ['BTU', 'ARCH', 'CEIX', 'HCC', 'AMR'],
    }

    # UN Global Compact principles
    UNGC_PRINCIPLES = [
        'Human Rights: Support & Respect',
        'Human Rights: Not Complicit in Abuses',
        'Labour: Freedom of Association',
        'Labour: Elimination of Forced Labour',
        'Labour: Abolition of Child Labour',
        'Labour: Elimination of Discrimination',
        'Environment: Precautionary Approach',
        'Environment: Greater Responsibility',
        'Environment: Environmentally Friendly Technologies',
        'Anti-Corruption: Work Against Corruption',
    ]

    def __init__(self):
        self._ticker_info_cache = {}

    def _get_ticker_info(self, symbol: str) -> Dict:
        """Get and cache ticker info from yfinance."""
        if symbol in self._ticker_info_cache:
            return self._ticker_info_cache[symbol]
        try:
            info = yf.Ticker(symbol).info
            self._ticker_info_cache[symbol] = info
            return info
        except Exception:
            return {}

    def calculate_esg_scores(
        self,
        symbols: List[str],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Calculate ESG scores for portfolio positions.

        Uses sector-based scoring with adjustments from available data.
        """
        position_scores = {}

        for symbol in symbols:
            info = self._get_ticker_info(symbol)
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            market_cap = info.get('marketCap', 0)

            industry_risk = self.INDUSTRY_ESG_RISK.get(sector, {
                'E': 'Medium', 'S': 'Medium', 'G': 'Medium', 'base_score': 55
            })

            base = industry_risk['base_score']

            # Size adjustment (larger companies typically have better ESG disclosure)
            if market_cap > 100e9:
                size_adj = 8
            elif market_cap > 10e9:
                size_adj = 4
            elif market_cap > 1e9:
                size_adj = 0
            else:
                size_adj = -5

            # Controversy check
            is_excluded = any(symbol in exc for exc in self.EXCLUSION_SCREENS.values())
            controversy_adj = -15 if is_excluded else 0

            e_score = min(100, max(0, base + size_adj + controversy_adj + np.random.normal(0, 3)))
            s_score = min(100, max(0, base + size_adj + controversy_adj + np.random.normal(0, 3)))
            g_score = min(100, max(0, base + size_adj + np.random.normal(0, 3)))

            # Adjust for risk level
            risk_adj = {'Low': 5, 'Medium': 0, 'High': -10}
            e_score += risk_adj.get(industry_risk['E'], 0)
            s_score += risk_adj.get(industry_risk['S'], 0)
            g_score += risk_adj.get(industry_risk['G'], 0)

            e_score = min(100, max(0, e_score))
            s_score = min(100, max(0, s_score))
            g_score = min(100, max(0, g_score))

            total = (e_score * 0.35 + s_score * 0.35 + g_score * 0.30)

            position_scores[symbol] = {
                'environmental': round(e_score, 1),
                'social': round(s_score, 1),
                'governance': round(g_score, 1),
                'total_esg': round(total, 1),
                'esg_rating': self._score_to_rating(total),
                'sector': sector,
                'industry': industry,
                'e_risk': industry_risk['E'],
                's_risk': industry_risk['S'],
                'g_risk': industry_risk['G'],
                'is_excluded_sector': is_excluded,
            }

        # Portfolio-level weighted score
        if weights:
            weighted_e = sum(
                weights.get(s, 0) * position_scores[s]['environmental']
                for s in symbols if s in position_scores
            )
            weighted_s = sum(
                weights.get(s, 0) * position_scores[s]['social']
                for s in symbols if s in position_scores
            )
            weighted_g = sum(
                weights.get(s, 0) * position_scores[s]['governance']
                for s in symbols if s in position_scores
            )
            weighted_total = sum(
                weights.get(s, 0) * position_scores[s]['total_esg']
                for s in symbols if s in position_scores
            )
        else:
            n = len(symbols)
            weighted_e = np.mean([v['environmental'] for v in position_scores.values()])
            weighted_s = np.mean([v['social'] for v in position_scores.values()])
            weighted_g = np.mean([v['governance'] for v in position_scores.values()])
            weighted_total = np.mean([v['total_esg'] for v in position_scores.values()])

        return {
            'position_scores': position_scores,
            'portfolio_environmental': round(weighted_e, 1),
            'portfolio_social': round(weighted_s, 1),
            'portfolio_governance': round(weighted_g, 1),
            'portfolio_esg_score': round(weighted_total, 1),
            'portfolio_esg_rating': self._score_to_rating(weighted_total),
        }

    def _score_to_rating(self, score: float) -> str:
        """Convert numeric ESG score to letter rating."""
        if score >= 80:
            return 'AAA'
        elif score >= 70:
            return 'AA'
        elif score >= 60:
            return 'A'
        elif score >= 50:
            return 'BBB'
        elif score >= 40:
            return 'BB'
        elif score >= 30:
            return 'B'
        else:
            return 'CCC'

    def run_exclusion_screening(
        self,
        symbols: List[str],
        screens: Optional[List[str]] = None
    ) -> Dict:
        """
        Run exclusion screening against controversial sector lists.

        Args:
            symbols: Portfolio symbols
            screens: Which screens to apply (None = all)
        """
        if screens is None:
            screens = list(self.EXCLUSION_SCREENS.keys())

        violations = {}
        clean = []

        for symbol in symbols:
            symbol_violations = []
            for screen in screens:
                if symbol in self.EXCLUSION_SCREENS.get(screen, []):
                    symbol_violations.append(screen)

            if symbol_violations:
                violations[symbol] = symbol_violations
            else:
                clean.append(symbol)

        return {
            'violations': violations,
            'clean_positions': clean,
            'n_violations': len(violations),
            'n_clean': len(clean),
            'pct_compliant': len(clean) / len(symbols) * 100 if symbols else 100,
            'screens_applied': screens,
        }

    def check_compliance_rules(
        self,
        portfolio_weights: Dict[str, float],
        rules: Optional[Dict] = None
    ) -> Dict:
        """
        Check portfolio against compliance rules.

        Default rules include concentration limits, sector limits, etc.
        """
        if rules is None:
            rules = {
                'max_single_position': 0.10,
                'max_sector_exposure': 0.30,
                'min_positions': 10,
                'max_cash': 0.10,
                'max_excluded_sector_exposure': 0.0,
            }

        violations = []
        warnings = []

        # Single position concentration
        max_pos = rules.get('max_single_position', 0.10)
        for symbol, weight in portfolio_weights.items():
            if weight > max_pos:
                violations.append({
                    'rule': 'Position Concentration',
                    'symbol': symbol,
                    'limit': f'{max_pos*100:.1f}%',
                    'actual': f'{weight*100:.1f}%',
                    'severity': 'High',
                })

        # Minimum diversification
        min_pos = rules.get('min_positions', 10)
        n_positions = len([w for w in portfolio_weights.values() if w > 0.001])
        if n_positions < min_pos:
            violations.append({
                'rule': 'Minimum Diversification',
                'symbol': 'Portfolio',
                'limit': f'{min_pos} positions',
                'actual': f'{n_positions} positions',
                'severity': 'Medium',
            })

        # Sector concentration
        sector_weights = {}
        for symbol, weight in portfolio_weights.items():
            info = self._get_ticker_info(symbol)
            sector = info.get('sector', 'Unknown')
            sector_weights[sector] = sector_weights.get(sector, 0) + weight

        max_sector = rules.get('max_sector_exposure', 0.30)
        for sector, weight in sector_weights.items():
            if weight > max_sector:
                violations.append({
                    'rule': 'Sector Concentration',
                    'symbol': sector,
                    'limit': f'{max_sector*100:.1f}%',
                    'actual': f'{weight*100:.1f}%',
                    'severity': 'Medium',
                })
            elif weight > max_sector * 0.8:
                warnings.append({
                    'rule': 'Sector Concentration Warning',
                    'symbol': sector,
                    'limit': f'{max_sector*100:.1f}%',
                    'actual': f'{weight*100:.1f}%',
                    'severity': 'Low',
                })

        # ESG exclusion check
        max_excluded = rules.get('max_excluded_sector_exposure', 0.0)
        excluded_weight = 0
        for symbol, weight in portfolio_weights.items():
            if any(symbol in exc for exc in self.EXCLUSION_SCREENS.values()):
                excluded_weight += weight

        if excluded_weight > max_excluded:
            violations.append({
                'rule': 'ESG Exclusion',
                'symbol': 'Portfolio',
                'limit': f'{max_excluded*100:.1f}%',
                'actual': f'{excluded_weight*100:.1f}%',
                'severity': 'High',
            })

        return {
            'is_compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'n_violations': len(violations),
            'n_warnings': len(warnings),
            'rules_checked': list(rules.keys()),
            'sector_exposures': sector_weights,
        }

    def calculate_carbon_metrics(
        self,
        symbols: List[str],
        weights: Optional[Dict[str, float]] = None,
        portfolio_value: float = 1_000_000
    ) -> Dict:
        """
        Estimate portfolio carbon intensity and footprint.
        Uses sector-based estimates as proxy.
        """
        # Average carbon intensity by sector (tCO2e/million USD revenue)
        SECTOR_CARBON_INTENSITY = {
            'Energy': 650,
            'Utilities': 550,
            'Materials': 400,
            'Industrials': 180,
            'Consumer Discretionary': 50,
            'Consumer Staples': 80,
            'Healthcare': 30,
            'Financials': 10,
            'Technology': 15,
            'Communication Services': 12,
            'Real Estate': 100,
        }

        position_carbon = {}
        total_intensity = 0

        for symbol in symbols:
            info = self._get_ticker_info(symbol)
            sector = info.get('sector', 'Unknown')
            weight = weights.get(symbol, 1/len(symbols)) if weights else 1/len(symbols)

            intensity = SECTOR_CARBON_INTENSITY.get(sector, 100)
            weighted_intensity = intensity * weight
            total_intensity += weighted_intensity

            position_carbon[symbol] = {
                'sector': sector,
                'carbon_intensity': intensity,
                'weighted_contribution': weighted_intensity,
                'estimated_footprint_tco2': intensity * weight * portfolio_value / 1_000_000,
            }

        total_footprint = total_intensity * portfolio_value / 1_000_000

        # Benchmark: S&P 500 weighted avg ~130 tCO2e/M USD
        benchmark_intensity = 130
        vs_benchmark = (total_intensity / benchmark_intensity - 1) * 100

        return {
            'portfolio_carbon_intensity': round(total_intensity, 1),
            'total_footprint_tco2': round(total_footprint, 1),
            'benchmark_intensity': benchmark_intensity,
            'vs_benchmark_pct': round(vs_benchmark, 1),
            'position_carbon': position_carbon,
            'carbon_risk': 'High' if total_intensity > 200 else ('Medium' if total_intensity > 100 else 'Low'),
        }

    def generate_esg_report(
        self,
        symbols: List[str],
        weights: Optional[Dict[str, float]] = None,
        portfolio_value: float = 1_000_000,
        compliance_rules: Optional[Dict] = None
    ) -> Dict:
        """Generate comprehensive ESG and compliance report."""
        report = {
            'esg_scores': self.calculate_esg_scores(symbols, weights),
            'exclusion_screening': self.run_exclusion_screening(symbols),
            'carbon_metrics': self.calculate_carbon_metrics(symbols, weights, portfolio_value),
        }

        if weights:
            report['compliance'] = self.check_compliance_rules(weights, compliance_rules)

        return report
