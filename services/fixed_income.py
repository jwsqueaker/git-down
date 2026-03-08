"""Fixed Income Analytics Service - Bond analysis and duration management."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from scipy.optimize import brentq


class FixedIncomeAnalytics:
    """Institutional-grade fixed income analytics."""

    def __init__(self):
        self.day_count_conventions = {
            '30/360': self._day_count_30_360,
            'actual/360': self._day_count_actual_360,
            'actual/365': self._day_count_actual_365,
            'actual/actual': self._day_count_actual_actual,
        }

    def calculate_bond_price(
        self,
        face_value: float,
        coupon_rate: float,
        ytm: float,
        years_to_maturity: float,
        frequency: int = 2
    ) -> Dict:
        """
        Calculate bond price and accrued metrics.

        Args:
            face_value: Par value of the bond
            coupon_rate: Annual coupon rate (decimal)
            ytm: Yield to maturity (decimal)
            years_to_maturity: Years until maturity
            frequency: Coupon payments per year (1=annual, 2=semi-annual, 4=quarterly)
        """
        n_periods = int(years_to_maturity * frequency)
        coupon_payment = face_value * coupon_rate / frequency
        period_yield = ytm / frequency

        if period_yield == 0:
            pv_coupons = coupon_payment * n_periods
            pv_face = face_value
        else:
            pv_coupons = coupon_payment * (1 - (1 + period_yield) ** -n_periods) / period_yield
            pv_face = face_value / (1 + period_yield) ** n_periods

        clean_price = pv_coupons + pv_face

        return {
            'clean_price': clean_price,
            'dirty_price': clean_price,
            'pv_coupons': pv_coupons,
            'pv_face': pv_face,
            'coupon_payment': coupon_payment,
            'total_coupons': coupon_payment * n_periods,
            'premium_discount': clean_price - face_value,
            'premium_discount_pct': (clean_price / face_value - 1) * 100,
        }

    def calculate_yield_to_maturity(
        self,
        face_value: float,
        coupon_rate: float,
        market_price: float,
        years_to_maturity: float,
        frequency: int = 2
    ) -> float:
        """Calculate yield to maturity from market price."""
        coupon = face_value * coupon_rate / frequency
        n = int(years_to_maturity * frequency)

        def price_diff(ytm_guess):
            r = ytm_guess / frequency
            if r == 0:
                pv = coupon * n + face_value
            else:
                pv = coupon * (1 - (1 + r) ** -n) / r + face_value / (1 + r) ** n
            return pv - market_price

        try:
            ytm = brentq(price_diff, -0.5, 2.0, xtol=1e-10)
            return ytm
        except Exception:
            return 0.0

    def calculate_duration(
        self,
        face_value: float,
        coupon_rate: float,
        ytm: float,
        years_to_maturity: float,
        frequency: int = 2
    ) -> Dict:
        """
        Calculate Macaulay duration, modified duration, and convexity.
        """
        n_periods = int(years_to_maturity * frequency)
        coupon = face_value * coupon_rate / frequency
        period_yield = ytm / frequency

        bond_price = self.calculate_bond_price(
            face_value, coupon_rate, ytm, years_to_maturity, frequency
        )['clean_price']

        # Macaulay Duration
        weighted_time = 0
        for t in range(1, n_periods + 1):
            pv_cf = coupon / (1 + period_yield) ** t
            weighted_time += t * pv_cf

        pv_face = face_value / (1 + period_yield) ** n_periods
        weighted_time += n_periods * pv_face

        macaulay_duration = (weighted_time / bond_price) / frequency

        # Modified Duration
        modified_duration = macaulay_duration / (1 + period_yield)

        # Dollar Duration (DV01)
        dv01 = modified_duration * bond_price / 10000

        # Convexity
        convexity_sum = 0
        for t in range(1, n_periods + 1):
            pv_cf = coupon / (1 + period_yield) ** t
            convexity_sum += t * (t + 1) * pv_cf

        convexity_sum += n_periods * (n_periods + 1) * pv_face
        convexity = convexity_sum / (bond_price * (1 + period_yield) ** 2 * frequency ** 2)

        return {
            'macaulay_duration': macaulay_duration,
            'modified_duration': modified_duration,
            'effective_duration': modified_duration,
            'dollar_duration': dv01,
            'dv01': dv01,
            'convexity': convexity,
            'dollar_convexity': convexity * bond_price / 100,
        }

    def price_sensitivity(
        self,
        face_value: float,
        coupon_rate: float,
        ytm: float,
        years_to_maturity: float,
        yield_change_bps: float,
        frequency: int = 2
    ) -> Dict:
        """
        Calculate price change for a given yield change using duration & convexity.
        """
        metrics = self.calculate_duration(
            face_value, coupon_rate, ytm, years_to_maturity, frequency
        )
        bond_price = self.calculate_bond_price(
            face_value, coupon_rate, ytm, years_to_maturity, frequency
        )['clean_price']

        dy = yield_change_bps / 10000

        duration_effect = -metrics['modified_duration'] * dy
        convexity_effect = 0.5 * metrics['convexity'] * dy ** 2
        total_pct_change = duration_effect + convexity_effect
        new_price_approx = bond_price * (1 + total_pct_change)

        new_price_exact = self.calculate_bond_price(
            face_value, coupon_rate, ytm + dy, years_to_maturity, frequency
        )['clean_price']

        return {
            'original_price': bond_price,
            'yield_change_bps': yield_change_bps,
            'duration_effect_pct': duration_effect * 100,
            'convexity_effect_pct': convexity_effect * 100,
            'total_change_pct': total_pct_change * 100,
            'approximate_new_price': new_price_approx,
            'exact_new_price': new_price_exact,
            'approximation_error': new_price_approx - new_price_exact,
            'dollar_change': new_price_exact - bond_price,
        }

    def build_yield_curve(
        self,
        maturities: List[float],
        yields: List[float]
    ) -> Dict:
        """
        Build and analyze a yield curve.

        Args:
            maturities: List of maturities in years
            yields: Corresponding yields (decimal)
        """
        sorted_pairs = sorted(zip(maturities, yields))
        maturities = [p[0] for p in sorted_pairs]
        yields_sorted = [p[1] for p in sorted_pairs]

        # Determine curve shape
        if len(maturities) >= 3:
            short_rate = np.mean(yields_sorted[:len(yields_sorted)//3])
            mid_rate = np.mean(yields_sorted[len(yields_sorted)//3:2*len(yields_sorted)//3])
            long_rate = np.mean(yields_sorted[2*len(yields_sorted)//3:])

            if short_rate < mid_rate < long_rate:
                shape = 'Normal (Upward Sloping)'
            elif short_rate > mid_rate > long_rate:
                shape = 'Inverted'
            elif mid_rate > short_rate and mid_rate > long_rate:
                shape = 'Humped'
            else:
                shape = 'Flat'
        else:
            shape = 'Insufficient Data'

        # Calculate spread metrics
        term_spread = yields_sorted[-1] - yields_sorted[0] if len(yields_sorted) >= 2 else 0

        # Forward rates (bootstrap simple forward rates)
        forward_rates = []
        for i in range(1, len(maturities)):
            t1, t2 = maturities[i-1], maturities[i]
            y1, y2 = yields_sorted[i-1], yields_sorted[i]
            if t2 > t1:
                fwd = ((1 + y2) ** t2 / (1 + y1) ** t1) ** (1 / (t2 - t1)) - 1
                forward_rates.append({
                    'from': t1,
                    'to': t2,
                    'forward_rate': fwd,
                })

        return {
            'maturities': maturities,
            'yields': yields_sorted,
            'shape': shape,
            'term_spread': term_spread,
            'term_spread_bps': term_spread * 10000,
            'forward_rates': forward_rates,
            'short_rate': yields_sorted[0] if yields_sorted else 0,
            'long_rate': yields_sorted[-1] if yields_sorted else 0,
        }

    def calculate_portfolio_duration(
        self,
        bonds: List[Dict],
        total_value: Optional[float] = None
    ) -> Dict:
        """
        Calculate weighted average duration for a bond portfolio.

        Args:
            bonds: List of dicts with keys: face_value, coupon_rate, ytm,
                   years_to_maturity, market_value, frequency (optional)
        """
        total_mv = total_value or sum(b.get('market_value', b['face_value']) for b in bonds)

        weighted_duration = 0
        weighted_convexity = 0
        weighted_ytm = 0
        total_dv01 = 0
        bond_details = []

        for bond in bonds:
            freq = bond.get('frequency', 2)
            metrics = self.calculate_duration(
                bond['face_value'], bond['coupon_rate'],
                bond['ytm'], bond['years_to_maturity'], freq
            )

            mv = bond.get('market_value', bond['face_value'])
            weight = mv / total_mv if total_mv > 0 else 0

            weighted_duration += weight * metrics['modified_duration']
            weighted_convexity += weight * metrics['convexity']
            weighted_ytm += weight * bond['ytm']
            total_dv01 += metrics['dv01'] * (mv / 100)

            bond_details.append({
                'face_value': bond['face_value'],
                'coupon_rate': bond['coupon_rate'],
                'ytm': bond['ytm'],
                'years_to_maturity': bond['years_to_maturity'],
                'market_value': mv,
                'weight': weight,
                'modified_duration': metrics['modified_duration'],
                'convexity': metrics['convexity'],
                'dv01': metrics['dv01'],
            })

        return {
            'portfolio_duration': weighted_duration,
            'portfolio_convexity': weighted_convexity,
            'portfolio_ytm': weighted_ytm,
            'total_dv01': total_dv01,
            'total_market_value': total_mv,
            'n_bonds': len(bonds),
            'bond_details': bond_details,
        }

    def calculate_spread_analysis(
        self,
        corporate_yield: float,
        treasury_yield: float,
        swap_rate: Optional[float] = None
    ) -> Dict:
        """Calculate various spread measures."""
        g_spread = corporate_yield - treasury_yield

        results = {
            'g_spread_bps': g_spread * 10000,
            'g_spread_pct': g_spread * 100,
            'corporate_yield': corporate_yield,
            'treasury_yield': treasury_yield,
        }

        if swap_rate is not None:
            i_spread = corporate_yield - swap_rate
            swap_spread = swap_rate - treasury_yield
            results['i_spread_bps'] = i_spread * 10000
            results['swap_spread_bps'] = swap_spread * 10000

        return results

    def key_rate_duration(
        self,
        face_value: float,
        coupon_rate: float,
        ytm: float,
        years_to_maturity: float,
        key_rates: Optional[List[float]] = None,
        frequency: int = 2,
        bump_bps: float = 1.0
    ) -> Dict:
        """
        Calculate key rate durations - sensitivity to specific points on yield curve.
        """
        if key_rates is None:
            key_rates = [0.5, 1, 2, 3, 5, 7, 10, 20, 30]
        key_rates = [kr for kr in key_rates if kr <= years_to_maturity * 1.5]

        base_price = self.calculate_bond_price(
            face_value, coupon_rate, ytm, years_to_maturity, frequency
        )['clean_price']

        bump = bump_bps / 10000
        key_rate_durations = {}

        for kr in key_rates:
            bump_ytm = ytm + bump * max(0, 1 - abs(years_to_maturity - kr) / max(kr, 1))
            bumped_price = self.calculate_bond_price(
                face_value, coupon_rate, bump_ytm, years_to_maturity, frequency
            )['clean_price']
            krd = -(bumped_price - base_price) / (base_price * bump) if base_price > 0 else 0
            key_rate_durations[f'{kr}Y'] = krd

        return {
            'key_rate_durations': key_rate_durations,
            'total_krd': sum(key_rate_durations.values()),
            'base_price': base_price,
        }

    def _day_count_30_360(self, start: date, end: date) -> float:
        d1, m1, y1 = min(start.day, 30), start.month, start.year
        d2, m2, y2 = min(end.day, 30), end.month, end.year
        return (360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)) / 360

    def _day_count_actual_360(self, start: date, end: date) -> float:
        return (end - start).days / 360

    def _day_count_actual_365(self, start: date, end: date) -> float:
        return (end - start).days / 365

    def _day_count_actual_actual(self, start: date, end: date) -> float:
        return (end - start).days / 365.25

    def generate_fixed_income_report(
        self,
        bonds: List[Dict],
        treasury_curve: Optional[Dict] = None
    ) -> Dict:
        """Generate comprehensive fixed income analytics report."""
        report = {
            'portfolio_metrics': self.calculate_portfolio_duration(bonds),
            'individual_bonds': [],
        }

        for bond in bonds:
            freq = bond.get('frequency', 2)
            price = self.calculate_bond_price(
                bond['face_value'], bond['coupon_rate'],
                bond['ytm'], bond['years_to_maturity'], freq
            )
            duration = self.calculate_duration(
                bond['face_value'], bond['coupon_rate'],
                bond['ytm'], bond['years_to_maturity'], freq
            )
            sensitivity = self.price_sensitivity(
                bond['face_value'], bond['coupon_rate'],
                bond['ytm'], bond['years_to_maturity'],
                yield_change_bps=100, frequency=freq
            )

            report['individual_bonds'].append({
                'pricing': price,
                'duration_metrics': duration,
                'sensitivity_100bps': sensitivity,
            })

        if treasury_curve:
            report['yield_curve'] = self.build_yield_curve(
                treasury_curve['maturities'],
                treasury_curve['yields']
            )

        return report
