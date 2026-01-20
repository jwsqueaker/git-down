"""Portfolio data models and structures."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class Position:
    """Individual portfolio position."""
    symbol: str
    shares: float
    purchase_date: date
    purchase_price: float
    current_price: Optional[float] = None

    @property
    def cost_basis(self) -> float:
        """Total cost basis."""
        return self.shares * self.purchase_price

    @property
    def current_value(self) -> float:
        """Current market value."""
        if self.current_price is None:
            return self.cost_basis
        return self.shares * self.current_price

    @property
    def unrealized_gain_loss(self) -> float:
        """Unrealized gain/loss."""
        return self.current_value - self.cost_basis

    @property
    def unrealized_gain_loss_pct(self) -> float:
        """Unrealized gain/loss percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_gain_loss / self.cost_basis) * 100


@dataclass
class PortfolioSnapshot:
    """Portfolio snapshot at a point in time."""
    date: date
    positions: List[Position]
    cash: float = 0.0

    @property
    def total_value(self) -> float:
        """Total portfolio value."""
        return sum(p.current_value for p in self.positions) + self.cash

    @property
    def total_cost_basis(self) -> float:
        """Total cost basis."""
        return sum(p.cost_basis for p in self.positions) + self.cash

    @property
    def total_gain_loss(self) -> float:
        """Total unrealized gain/loss."""
        return self.total_value - self.total_cost_basis

    @property
    def total_return_pct(self) -> float:
        """Total return percentage."""
        if self.total_cost_basis == 0:
            return 0.0
        return (self.total_gain_loss / self.total_cost_basis) * 100

    def get_allocation(self) -> Dict[str, float]:
        """Get asset allocation by symbol."""
        total = self.total_value
        if total == 0:
            return {}

        allocation = {}
        for position in self.positions:
            allocation[position.symbol] = (position.current_value / total) * 100

        if self.cash > 0:
            allocation['CASH'] = (self.cash / total) * 100

        return allocation

    def to_dataframe(self) -> pd.DataFrame:
        """Convert positions to DataFrame."""
        data = []
        for p in self.positions:
            data.append({
                'Symbol': p.symbol,
                'Shares': p.shares,
                'Purchase Date': p.purchase_date,
                'Purchase Price': p.purchase_price,
                'Current Price': p.current_price or 0,
                'Cost Basis': p.cost_basis,
                'Current Value': p.current_value,
                'Gain/Loss': p.unrealized_gain_loss,
                'Return %': p.unrealized_gain_loss_pct
            })
        return pd.DataFrame(data)


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics."""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    beta: Optional[float] = None
    alpha: Optional[float] = None
    treynor_ratio: Optional[float] = None
    information_ratio: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'Total Return (%)': round(self.total_return * 100, 2),
            'Annualized Return (%)': round(self.annualized_return * 100, 2),
            'Volatility (%)': round(self.volatility * 100, 2),
            'Sharpe Ratio': round(self.sharpe_ratio, 2),
            'Sortino Ratio': round(self.sortino_ratio, 2),
            'Max Drawdown (%)': round(self.max_drawdown * 100, 2),
            'Calmar Ratio': round(self.calmar_ratio, 2),
            'Beta': round(self.beta, 2) if self.beta else None,
            'Alpha (%)': round(self.alpha * 100, 2) if self.alpha else None,
            'Treynor Ratio': round(self.treynor_ratio, 2) if self.treynor_ratio else None,
            'Information Ratio': round(self.information_ratio, 2) if self.information_ratio else None
        }
