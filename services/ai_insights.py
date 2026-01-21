"""AI-powered insights and anomaly detection."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class AIInsights:
    """Generate AI-powered insights from portfolio data."""

    def __init__(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series):
        """
        Initialize AI insights generator.

        Args:
            portfolio_returns: Portfolio returns series
            benchmark_returns: Benchmark returns series
        """
        self.portfolio_returns = portfolio_returns
        self.benchmark_returns = benchmark_returns

    def detect_anomalies(self, threshold_std: float = 3.0) -> pd.DataFrame:
        """
        Detect anomalous returns.

        Args:
            threshold_std: Standard deviations for anomaly threshold

        Returns:
            DataFrame with anomalies
        """
        mean = self.portfolio_returns.mean()
        std = self.portfolio_returns.std()

        # Identify outliers
        anomalies = self.portfolio_returns[
            np.abs(self.portfolio_returns - mean) > threshold_std * std
        ]

        if anomalies.empty:
            return pd.DataFrame()

        anomaly_df = pd.DataFrame({
            'date': anomalies.index,
            'return': anomalies.values,
            'z_score': (anomalies.values - mean) / std,
            'type': ['Extreme Loss' if r < mean else 'Extreme Gain' for r in anomalies.values]
        })

        return anomaly_df.sort_values('date', ascending=False)

    def identify_trends(self, window: int = 20) -> Dict:
        """
        Identify current trends.

        Args:
            window: Rolling window for trend calculation

        Returns:
            Dictionary with trend analysis
        """
        # Calculate rolling statistics
        rolling_mean = self.portfolio_returns.rolling(window).mean()
        recent_trend = rolling_mean.iloc[-window:].mean()

        # Momentum
        recent_returns = self.portfolio_returns.iloc[-window:]
        positive_days = (recent_returns > 0).sum()
        momentum = positive_days / window

        # Volatility trend
        rolling_vol = self.portfolio_returns.rolling(window).std()
        vol_trend = 'Increasing' if rolling_vol.iloc[-1] > rolling_vol.iloc[-window] else 'Decreasing'

        return {
            'recent_trend': 'Uptrend' if recent_trend > 0 else 'Downtrend',
            'trend_strength': abs(recent_trend),
            'momentum_score': momentum,
            'volatility_trend': vol_trend,
            'current_volatility': rolling_vol.iloc[-1]
        }

    def generate_performance_insights(self) -> List[str]:
        """Generate natural language insights about performance."""
        insights = []

        # Compare to benchmark
        portfolio_total = (1 + self.portfolio_returns).prod() - 1
        benchmark_total = (1 + self.benchmark_returns).prod() - 1

        if portfolio_total > benchmark_total:
            outperformance = (portfolio_total - benchmark_total) * 100
            insights.append(
                f"Your portfolio has outperformed the benchmark by {outperformance:.2f}% over this period."
            )
        else:
            underperformance = (benchmark_total - portfolio_total) * 100
            insights.append(
                f"Your portfolio has underperformed the benchmark by {underperformance:.2f}% over this period."
            )

        # Volatility analysis
        port_vol = self.portfolio_returns.std() * np.sqrt(252) * 100
        bench_vol = self.benchmark_returns.std() * np.sqrt(252) * 100

        if port_vol > bench_vol * 1.2:
            insights.append(
                f"Your portfolio is significantly more volatile ({port_vol:.1f}%) than the benchmark ({bench_vol:.1f}%)."
            )
        elif port_vol < bench_vol * 0.8:
            insights.append(
                f"Your portfolio is less volatile ({port_vol:.1f}%) than the benchmark ({bench_vol:.1f}%), indicating lower risk."
            )

        # Downside analysis
        negative_returns = self.portfolio_returns[self.portfolio_returns < 0]
        if len(negative_returns) > 0:
            avg_loss = negative_returns.mean() * 100
            loss_frequency = len(negative_returns) / len(self.portfolio_returns) * 100
            insights.append(
                f"On down days, your average loss is {abs(avg_loss):.2f}%, occurring {loss_frequency:.1f}% of the time."
            )

        # Winning streak
        streaks = self._calculate_streaks()
        if streaks['max_winning_streak'] > 10:
            insights.append(
                f"Your longest winning streak was {streaks['max_winning_streak']} consecutive positive days."
            )

        return insights

    def _calculate_streaks(self) -> Dict:
        """Calculate winning and losing streaks."""
        positive = (self.portfolio_returns > 0).astype(int)

        max_win_streak = 0
        max_loss_streak = 0
        current_streak = 0
        last_value = None

        for val in positive:
            if val == last_value:
                current_streak += 1
            else:
                if last_value == 1:
                    max_win_streak = max(max_win_streak, current_streak)
                elif last_value == 0:
                    max_loss_streak = max(max_loss_streak, current_streak)
                current_streak = 1
                last_value = val

        return {
            'max_winning_streak': max_win_streak,
            'max_losing_streak': max_loss_streak
        }

    def suggest_actions(self) -> List[Dict]:
        """Suggest actionable items based on analysis."""
        suggestions = []

        # Check for high volatility
        vol = self.portfolio_returns.std() * np.sqrt(252)
        if vol > 0.25:
            suggestions.append({
                'priority': 'High',
                'action': 'Consider Rebalancing',
                'reason': 'Portfolio volatility is high (>25%)',
                'suggestion': 'Review allocation and consider adding lower-risk assets'
            })

        # Check for drawdown
        cumulative = (1 + self.portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        if max_drawdown < -0.20:
            suggestions.append({
                'priority': 'Medium',
                'action': 'Review Risk Tolerance',
                'reason': f'Portfolio experienced {abs(max_drawdown)*100:.1f}% drawdown',
                'suggestion': 'Ensure this level of decline is acceptable for your goals'
            })

        # Check for drift from benchmark
        correlation = self.portfolio_returns.corr(self.benchmark_returns)
        if correlation < 0.7:
            suggestions.append({
                'priority': 'Low',
                'action': 'Benchmark Alignment',
                'reason': 'Low correlation with benchmark',
                'suggestion': 'Portfolio may be taking different risks than intended'
            })

        return suggestions


def calculate_portfolio_health_score(
    returns: pd.Series,
    target_return: float = 0.08,
    target_volatility: float = 0.15,
    max_drawdown_tolerance: float = 0.20
) -> Dict:
    """
    Calculate overall portfolio health score.

    Args:
        returns: Portfolio returns
        target_return: Target annual return
        target_volatility: Target annual volatility
        max_drawdown_tolerance: Maximum acceptable drawdown

    Returns:
        Dictionary with health score and components
    """
    # Calculate metrics
    annual_return = returns.mean() * 252
    annual_vol = returns.std() * np.sqrt(252)

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = abs(drawdown.min())

    # Score components (0-100 each)
    return_score = min(100, (annual_return / target_return) * 100) if target_return > 0 else 50
    vol_score = max(0, 100 - abs(annual_vol - target_volatility) / target_volatility * 100)
    dd_score = max(0, 100 - (max_dd / max_drawdown_tolerance) * 100)

    # Overall score (weighted average)
    overall_score = (
        return_score * 0.4 +
        vol_score * 0.3 +
        dd_score * 0.3
    )

    # Rating
    if overall_score >= 85:
        rating = 'Excellent'
    elif overall_score >= 70:
        rating = 'Good'
    elif overall_score >= 55:
        rating = 'Fair'
    else:
        rating = 'Needs Improvement'

    return {
        'overall_score': overall_score,
        'rating': rating,
        'return_score': return_score,
        'volatility_score': vol_score,
        'drawdown_score': dd_score,
        'metrics': {
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'max_drawdown': max_dd
        }
    }
