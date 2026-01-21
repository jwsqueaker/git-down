"""Dividend income tracking and analysis."""
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models.portfolio import Position


class DividendTracker:
    """Track and analyze dividend income."""

    def __init__(self, positions: List[Position]):
        """
        Initialize dividend tracker.

        Args:
            positions: List of portfolio positions
        """
        self.positions = positions

    def fetch_dividend_data(self, years_back: int = 5) -> pd.DataFrame:
        """
        Fetch historical dividend data for all positions.

        Args:
            years_back: Years of history to fetch

        Returns:
            DataFrame with dividend history
        """
        start_date = datetime.now() - timedelta(days=365 * years_back)

        all_dividends = []

        for position in self.positions:
            try:
                ticker = yf.Ticker(position.symbol)
                divs = ticker.dividends

                if divs.empty:
                    continue

                # Filter to relevant date range
                divs = divs[divs.index >= start_date]

                for date, amount in divs.items():
                    all_dividends.append({
                        'symbol': position.symbol,
                        'date': date,
                        'dividend_per_share': amount,
                        'shares_owned': position.shares,
                        'total_dividend': amount * position.shares
                    })

            except Exception as e:
                print(f"Error fetching dividends for {position.symbol}: {e}")
                continue

        return pd.DataFrame(all_dividends)

    def calculate_annual_dividend_income(
        self,
        dividend_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Calculate annual dividend income by year.

        Args:
            dividend_df: Dividend DataFrame (fetched if not provided)

        Returns:
            DataFrame with annual dividend income
        """
        if dividend_df is None:
            dividend_df = self.fetch_dividend_data()

        if dividend_df.empty:
            return pd.DataFrame()

        dividend_df['year'] = pd.to_datetime(dividend_df['date']).dt.year

        annual = dividend_df.groupby('year').agg({
            'total_dividend': 'sum'
        }).reset_index()

        annual.columns = ['year', 'total_annual_dividends']

        return annual

    def calculate_dividend_yield_on_cost(self) -> pd.DataFrame:
        """
        Calculate yield on cost for each position.

        Returns:
            DataFrame with yield on cost analysis
        """
        results = []

        for position in self.positions:
            try:
                ticker = yf.Ticker(position.symbol)
                info = ticker.info

                # Current dividend yield
                dividend_yield = info.get('dividendYield', 0)
                if dividend_yield is None:
                    dividend_yield = 0

                # Annual dividend per share
                annual_dividend = info.get('dividendRate', 0)
                if annual_dividend is None or annual_dividend == 0:
                    # Try to calculate from trailing dividends
                    divs = ticker.dividends
                    if not divs.empty:
                        # Last 12 months
                        recent_divs = divs[divs.index >= datetime.now() - timedelta(days=365)]
                        annual_dividend = recent_divs.sum()
                    else:
                        annual_dividend = 0

                # Yield on cost = annual dividend / purchase price
                if position.purchase_price > 0:
                    yield_on_cost = (annual_dividend / position.purchase_price)
                else:
                    yield_on_cost = 0

                # Total annual income from this position
                annual_income = annual_dividend * position.shares

                results.append({
                    'symbol': position.symbol,
                    'shares': position.shares,
                    'purchase_price': position.purchase_price,
                    'current_price': position.current_price,
                    'annual_dividend_per_share': annual_dividend,
                    'current_yield': dividend_yield,
                    'yield_on_cost': yield_on_cost,
                    'annual_income': annual_income,
                    'purchase_date': position.purchase_date
                })

            except Exception as e:
                print(f"Error calculating yield for {position.symbol}: {e}")
                continue

        return pd.DataFrame(results)

    def project_future_dividends(
        self,
        years_ahead: int = 10,
        dividend_growth_rate: float = 0.05
    ) -> pd.DataFrame:
        """
        Project future dividend income.

        Args:
            years_ahead: Years to project
            dividend_growth_rate: Annual dividend growth rate

        Returns:
            DataFrame with projected dividends
        """
        yield_df = self.calculate_dividend_yield_on_cost()

        if yield_df.empty:
            return pd.DataFrame()

        current_annual_income = yield_df['annual_income'].sum()

        projections = []

        for year in range(1, years_ahead + 1):
            projected_income = current_annual_income * (1 + dividend_growth_rate) ** year

            projections.append({
                'year': datetime.now().year + year,
                'projected_annual_dividends': projected_income
            })

        return pd.DataFrame(projections)

    def identify_dividend_growth_stocks(self) -> pd.DataFrame:
        """
        Identify positions with consistent dividend growth.

        Returns:
            DataFrame with dividend growth analysis
        """
        results = []

        for position in self.positions:
            try:
                ticker = yf.Ticker(position.symbol)
                divs = ticker.dividends

                if len(divs) < 8:  # Need at least 2 years of quarterly dividends
                    continue

                # Get last 5 years
                recent_divs = divs[divs.index >= datetime.now() - timedelta(days=365*5)]

                # Calculate annual totals
                annual_divs = recent_divs.groupby(recent_divs.index.year).sum()

                if len(annual_divs) < 3:
                    continue

                # Calculate growth rate
                years = len(annual_divs) - 1
                if years > 0:
                    cagr = (annual_divs.iloc[-1] / annual_divs.iloc[0]) ** (1/years) - 1
                else:
                    cagr = 0

                # Check for consistency (no cuts)
                has_cuts = (annual_divs.diff() < 0).any()

                results.append({
                    'symbol': position.symbol,
                    'dividend_cagr': cagr,
                    'years_of_data': years + 1,
                    'has_dividend_cuts': has_cuts,
                    'latest_annual_dividend': annual_divs.iloc[-1],
                    'dividend_aristocrat': cagr > 0 and not has_cuts and years >= 4
                })

            except Exception as e:
                print(f"Error analyzing {position.symbol}: {e}")
                continue

        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values('dividend_cagr', ascending=False)

        return df

    def calculate_dividend_coverage_ratio(self) -> pd.DataFrame:
        """
        Calculate dividend payout ratios (dividend coverage).

        Returns:
            DataFrame with payout ratio analysis
        """
        results = []

        for position in self.positions:
            try:
                ticker = yf.Ticker(position.symbol)
                info = ticker.info

                # Dividend rate
                dividend_rate = info.get('dividendRate', 0)
                if dividend_rate is None:
                    dividend_rate = 0

                # Earnings per share
                eps = info.get('trailingEps', 0)
                if eps is None or eps == 0:
                    payout_ratio = None
                else:
                    payout_ratio = dividend_rate / eps

                # Free cash flow per share (if available)
                fcf = info.get('freeCashflow', 0)
                shares_outstanding = info.get('sharesOutstanding', 1)

                if fcf and shares_outstanding:
                    fcf_per_share = fcf / shares_outstanding
                    fcf_payout_ratio = dividend_rate / fcf_per_share if fcf_per_share > 0 else None
                else:
                    fcf_payout_ratio = None

                # Sustainability assessment
                if payout_ratio is not None:
                    if payout_ratio < 0:
                        sustainability = 'Unsustainable (negative earnings)'
                    elif payout_ratio > 1.0:
                        sustainability = 'At Risk (payout > earnings)'
                    elif payout_ratio > 0.8:
                        sustainability = 'Moderate Risk'
                    else:
                        sustainability = 'Sustainable'
                else:
                    sustainability = 'Unknown'

                results.append({
                    'symbol': position.symbol,
                    'dividend_rate': dividend_rate,
                    'eps': eps,
                    'payout_ratio': payout_ratio,
                    'fcf_payout_ratio': fcf_payout_ratio,
                    'sustainability': sustainability
                })

            except Exception as e:
                print(f"Error for {position.symbol}: {e}")
                continue

        return pd.DataFrame(results)


def calculate_drip_impact(
    initial_shares: float,
    initial_price: float,
    annual_dividend: float,
    years: int,
    dividend_growth_rate: float = 0.05,
    price_growth_rate: float = 0.08
) -> Dict:
    """
    Calculate impact of dividend reinvestment (DRIP).

    Args:
        initial_shares: Starting shares
        initial_price: Starting price
        annual_dividend: Annual dividend per share
        years: Years to project
        dividend_growth_rate: Annual dividend growth
        price_growth_rate: Annual price growth

    Returns:
        Dictionary with DRIP analysis
    """
    shares = initial_shares
    price = initial_price
    dividend = annual_dividend

    shares_history = [shares]
    value_history = [shares * price]

    for year in range(years):
        # Dividends paid
        div_income = shares * dividend

        # Reinvest dividends
        new_shares = div_income / price
        shares += new_shares

        # Grow dividend and price
        dividend *= (1 + dividend_growth_rate)
        price *= (1 + price_growth_rate)

        shares_history.append(shares)
        value_history.append(shares * price)

    # Calculate without DRIP for comparison
    no_drip_value = initial_shares * price

    return {
        'final_shares': shares,
        'final_value_with_drip': value_history[-1],
        'final_value_without_drip': no_drip_value,
        'drip_advantage': value_history[-1] - no_drip_value,
        'drip_advantage_pct': (value_history[-1] / no_drip_value - 1) * 100,
        'shares_history': shares_history,
        'value_history': value_history
    }
