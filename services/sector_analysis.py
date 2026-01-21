"""Sector and geographic exposure analysis."""
import pandas as pd
import yfinance as yf
from typing import Dict, List
from models.portfolio import Position


class SectorAnalyzer:
    """Analyze sector and geographic exposures."""

    def __init__(self, positions: List[Position]):
        self.positions = positions

    def get_sector_exposure(self) -> pd.DataFrame:
        """Get sector breakdown of portfolio."""
        sector_data = []

        for position in self.positions:
            try:
                ticker = yf.Ticker(position.symbol)
                info = ticker.info

                sector = info.get('sector', 'Unknown')
                industry = info.get('industry', 'Unknown')

                value = position.shares * (position.current_price or position.purchase_price)

                sector_data.append({
                    'symbol': position.symbol,
                    'sector': sector,
                    'industry': industry,
                    'value': value,
                    'shares': position.shares
                })
            except:
                continue

        df = pd.DataFrame(sector_data)
        if df.empty:
            return df

        total_value = df['value'].sum()

        sector_summary = df.groupby('sector').agg({
            'value': 'sum',
            'symbol': 'count'
        }).reset_index()

        sector_summary.columns = ['sector', 'value', 'num_positions']
        sector_summary['weight'] = sector_summary['value'] / total_value

        return sector_summary.sort_values('weight', ascending=False)

    def get_geographic_exposure(self) -> pd.DataFrame:
        """Get geographic exposure."""
        geo_data = []

        for position in self.positions:
            try:
                ticker = yf.Ticker(position.symbol)
                info = ticker.info

                country = info.get('country', 'Unknown')
                value = position.shares * (position.current_price or position.purchase_price)

                geo_data.append({
                    'symbol': position.symbol,
                    'country': country,
                    'value': value
                })
            except:
                continue

        df = pd.DataFrame(geo_data)
        if df.empty:
            return df

        total_value = df['value'].sum()

        geo_summary = df.groupby('country').agg({
            'value': 'sum',
            'symbol': 'count'
        }).reset_index()

        geo_summary.columns = ['country', 'value', 'num_positions']
        geo_summary['weight'] = geo_summary['value'] / total_value

        return geo_summary.sort_values('weight', ascending=False)

    def check_concentration_risk(self, threshold: float = 0.15) -> Dict:
        """Check for concentration risk."""
        sector_exposure = self.get_sector_exposure()

        if sector_exposure.empty:
            return {'has_risk': False, 'concentrated_sectors': []}

        concentrated = sector_exposure[sector_exposure['weight'] > threshold]

        return {
            'has_risk': len(concentrated) > 0,
            'concentrated_sectors': concentrated.to_dict('records'),
            'max_sector_weight': sector_exposure['weight'].max(),
            'herfindahl_index': (sector_exposure['weight'] ** 2).sum()
        }
