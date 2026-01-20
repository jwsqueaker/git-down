"""Utility helper functions."""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a decimal as percentage.

    Args:
        value: Decimal value (e.g., 0.075 for 7.5%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def format_currency(value: float, decimals: int = 2) -> str:
    """
    Format a value as USD currency.

    Args:
        value: Dollar amount
        decimals: Number of decimal places

    Returns:
        Formatted currency string
    """
    return f"${value:,.{decimals}f}"


def format_number(value: float, decimals: int = 2) -> str:
    """
    Format a number with thousand separators.

    Args:
        value: Number to format
        decimals: Number of decimal places

    Returns:
        Formatted number string
    """
    return f"{value:,.{decimals}f}"


def get_date_range(period: str) -> Tuple[str, str]:
    """
    Get start and end dates for a period.

    Args:
        period: Period name ('1M', '3M', '6M', '1Y', '3Y', '5Y', 'YTD', 'MAX')

    Returns:
        Tuple of (start_date, end_date) as strings
    """
    end_date = datetime.now()
    end_str = end_date.strftime('%Y-%m-%d')

    period_map = {
        '1M': timedelta(days=30),
        '3M': timedelta(days=90),
        '6M': timedelta(days=180),
        '1Y': timedelta(days=365),
        '3Y': timedelta(days=365 * 3),
        '5Y': timedelta(days=365 * 5),
        '10Y': timedelta(days=365 * 10)
    }

    if period == 'YTD':
        start_date = datetime(end_date.year, 1, 1)
    elif period == 'MAX':
        start_date = datetime(2000, 1, 1)
    else:
        delta = period_map.get(period, timedelta(days=365))
        start_date = end_date - delta

    start_str = start_date.strftime('%Y-%m-%d')
    return start_str, end_str


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """
    Calculate Compound Annual Growth Rate.

    Args:
        start_value: Starting value
        end_value: Ending value
        years: Number of years

    Returns:
        CAGR as decimal
    """
    if start_value <= 0 or years <= 0:
        return 0.0

    return (end_value / start_value) ** (1 / years) - 1


def annualize_return(total_return: float, days: int) -> float:
    """
    Annualize a total return.

    Args:
        total_return: Total return as decimal
        days: Number of days

    Returns:
        Annualized return as decimal
    """
    if days <= 0:
        return 0.0

    years = days / 365.25
    return (1 + total_return) ** (1 / years) - 1


def calculate_drawdown_series(cumulative_returns: pd.Series) -> pd.Series:
    """
    Calculate drawdown series from cumulative returns.

    Args:
        cumulative_returns: Series of cumulative returns

    Returns:
        Series of drawdowns
    """
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    return drawdown


def resample_returns(returns: pd.Series, freq: str = 'M') -> pd.Series:
    """
    Resample returns to a different frequency.

    Args:
        returns: Daily returns series
        freq: Target frequency ('W' for weekly, 'M' for monthly, 'Q' for quarterly)

    Returns:
        Resampled returns series
    """
    # Convert to price index
    price_index = (1 + returns).cumprod()

    # Resample to target frequency (take last value)
    resampled_price = price_index.resample(freq).last()

    # Calculate returns from resampled prices
    resampled_returns = resampled_price.pct_change().dropna()

    return resampled_returns


def align_series(*series: pd.Series) -> Tuple[pd.Series, ...]:
    """
    Align multiple time series by their common dates.

    Args:
        *series: Variable number of pandas Series

    Returns:
        Tuple of aligned Series
    """
    df = pd.DataFrame({i: s for i, s in enumerate(series)})
    df = df.dropna()

    return tuple(df[i] for i in range(len(series)))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero

    Returns:
        Result of division or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def get_color_for_value(value: float, reverse: bool = False) -> str:
    """
    Get color based on positive/negative value.

    Args:
        value: Numeric value
        reverse: If True, negative is green and positive is red

    Returns:
        Color name or hex code
    """
    if value > 0:
        return 'red' if reverse else 'green'
    elif value < 0:
        return 'green' if reverse else 'red'
    else:
        return 'gray'
