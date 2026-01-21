"""CSV upload and processing utilities."""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from models.portfolio import Position
import io


class CSVHandler:
    """Handle CSV uploads for portfolio and LTCMA data."""

    @staticmethod
    def parse_portfolio_csv(file_content: bytes) -> List[Position]:
        """
        Parse portfolio CSV file into Position objects.

        Expected columns: symbol, shares, purchase_date, purchase_price
        Optional columns: asset_class, description

        Args:
            file_content: CSV file content as bytes

        Returns:
            List of Position objects
        """
        try:
            df = pd.read_csv(io.BytesIO(file_content))

            # Validate required columns
            required_cols = ['symbol', 'shares', 'purchase_date', 'purchase_price']
            missing = [col for col in required_cols if col not in df.columns]

            if missing:
                raise ValueError(f"Missing required columns: {', '.join(missing)}")

            positions = []
            for _, row in df.iterrows():
                # Parse date
                purchase_date = pd.to_datetime(row['purchase_date']).date()

                # Get optional fields
                asset_class = str(row['asset_class']).strip() if 'asset_class' in df.columns and pd.notna(row.get('asset_class')) else None
                description = str(row['description']).strip() if 'description' in df.columns and pd.notna(row.get('description')) else None

                position = Position(
                    symbol=str(row['symbol']).upper().strip(),
                    shares=float(row['shares']),
                    purchase_date=purchase_date,
                    purchase_price=float(row['purchase_price']),
                    asset_class=asset_class,
                    description=description
                )
                positions.append(position)

            return positions

        except Exception as e:
            raise ValueError(f"Error parsing portfolio CSV: {e}")

    @staticmethod
    def parse_ltcma_csv(file_content: bytes) -> pd.DataFrame:
        """
        Parse LTCMA CSV file.

        Expected columns: asset_class, expected_return, volatility, [optional correlation columns]

        Args:
            file_content: CSV file content as bytes

        Returns:
            DataFrame with LTCMA data
        """
        try:
            df = pd.read_csv(io.BytesIO(file_content))

            # Validate required columns
            required_cols = ['asset_class', 'expected_return', 'volatility']
            missing = [col for col in required_cols if col not in df.columns]

            if missing:
                raise ValueError(f"Missing required columns: {', '.join(missing)}")

            # Convert percentages if needed (assumes returns/vol are in percentage form like 7.5)
            df['expected_return'] = df['expected_return'].apply(
                lambda x: x / 100 if x > 1 else x
            )
            df['volatility'] = df['volatility'].apply(
                lambda x: x / 100 if x > 1 else x
            )

            return df

        except Exception as e:
            raise ValueError(f"Error parsing LTCMA CSV: {e}")

    @staticmethod
    def create_portfolio_template() -> str:
        """
        Create a CSV template for portfolio upload.

        Returns:
            CSV string template
        """
        template = """asset_class,description,symbol,shares,purchase_date,purchase_price
U.S. Large Cap Equity,Apple Inc.,AAPL,100,2023-01-15,150.25
U.S. Large Cap Equity,Microsoft Corporation,MSFT,50,2023-02-20,275.50
U.S. Large Cap Equity,Alphabet Inc.,GOOGL,25,2023-03-10,105.75
U.S. Large Cap Equity,SPDR S&P 500 ETF Trust,SPY,200,2023-01-05,385.50
U.S. Government Bonds,iShares 20+ Year Treasury Bond ETF,TLT,50,2023-02-01,95.30
"""
        return template

    @staticmethod
    def create_ltcma_template() -> str:
        """
        Create a CSV template for LTCMA data upload.

        Returns:
            CSV string template
        """
        template = """asset_class,expected_return,volatility
U.S. Large Cap,7.5,17.0
U.S. Small Cap,8.0,23.0
International Developed,7.0,18.0
Emerging Markets,8.5,25.0
U.S. Investment Grade Bonds,4.5,5.5
U.S. High Yield Bonds,6.0,12.0
Commodities,5.5,18.0
Real Estate,7.0,20.0
Cash,3.5,1.0
"""
        return template

    @staticmethod
    def validate_portfolio_data(positions: List[Position]) -> Dict[str, List[str]]:
        """
        Validate portfolio data and return any warnings/errors.

        Args:
            positions: List of Position objects

        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []

        if not positions:
            errors.append("No positions found in file")
            return {'errors': errors, 'warnings': warnings}

        # Check for duplicates
        symbols = [p.symbol for p in positions]
        duplicates = [s for s in set(symbols) if symbols.count(s) > 1]
        if duplicates:
            warnings.append(f"Duplicate symbols found: {', '.join(duplicates)}")

        # Check for negative shares or prices
        for pos in positions:
            if pos.shares <= 0:
                errors.append(f"{pos.symbol}: Invalid shares ({pos.shares})")
            if pos.purchase_price <= 0:
                errors.append(f"{pos.symbol}: Invalid purchase price ({pos.purchase_price})")

        # Check for future dates
        today = datetime.now().date()
        for pos in positions:
            if pos.purchase_date > today:
                warnings.append(f"{pos.symbol}: Purchase date is in the future")

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def export_portfolio_to_csv(positions: List[Position]) -> str:
        """
        Export portfolio positions to CSV string.

        Args:
            positions: List of Position objects

        Returns:
            CSV string
        """
        data = []
        for pos in positions:
            data.append({
                'asset_class': pos.asset_class or '',
                'description': pos.description or '',
                'symbol': pos.symbol,
                'shares': pos.shares,
                'purchase_date': pos.purchase_date.strftime('%Y-%m-%d'),
                'purchase_price': pos.purchase_price,
                'current_price': pos.current_price,
                'current_value': pos.current_value,
                'gain_loss': pos.unrealized_gain_loss,
                'return_pct': pos.unrealized_gain_loss_pct
            })

        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    @staticmethod
    def export_metrics_to_csv(metrics_dict: Dict) -> str:
        """
        Export metrics to CSV string.

        Args:
            metrics_dict: Dictionary of metrics

        Returns:
            CSV string
        """
        # Convert dict to DataFrame
        df = pd.DataFrame([metrics_dict]).T
        df.columns = ['Value']
        df.index.name = 'Metric'
        return df.to_csv()
