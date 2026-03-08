"""Risk Management Service - VaR, CVaR, stress testing, and risk budgeting."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from scipy import stats
from scipy.optimize import minimize


class RiskManager:
    """Institutional-grade risk management and stress testing."""

    # Historical stress scenarios
    HISTORICAL_SCENARIOS = {
        'COVID-19 Crash (2020)': {
            'description': 'Pandemic-driven market crash, Feb-Mar 2020',
            'equity_shock': -0.34,
            'bond_shock': 0.05,
            'credit_spread_change': 3.5,
            'vix_level': 82.69,
            'duration_weeks': 5,
        },
        'GFC (2008-2009)': {
            'description': 'Global Financial Crisis',
            'equity_shock': -0.57,
            'bond_shock': 0.15,
            'credit_spread_change': 6.0,
            'vix_level': 80.86,
            'duration_weeks': 72,
        },
        'Dot-Com Bust (2000-2002)': {
            'description': 'Technology bubble burst',
            'equity_shock': -0.49,
            'bond_shock': 0.20,
            'credit_spread_change': 2.5,
            'vix_level': 45.08,
            'duration_weeks': 130,
        },
        'Black Monday (1987)': {
            'description': 'Single-day 22% market crash',
            'equity_shock': -0.22,
            'bond_shock': 0.03,
            'credit_spread_change': 1.0,
            'vix_level': 150.0,
            'duration_weeks': 1,
        },
        'Rising Rates (2022)': {
            'description': 'Fed aggressive rate hikes, inflation surge',
            'equity_shock': -0.25,
            'bond_shock': -0.13,
            'credit_spread_change': 1.5,
            'vix_level': 36.45,
            'duration_weeks': 40,
        },
        'Euro Debt Crisis (2011)': {
            'description': 'European sovereign debt crisis',
            'equity_shock': -0.19,
            'bond_shock': 0.08,
            'credit_spread_change': 2.0,
            'vix_level': 48.0,
            'duration_weeks': 20,
        },
        'Flash Crash (2010)': {
            'description': 'May 2010 flash crash',
            'equity_shock': -0.07,
            'bond_shock': 0.02,
            'credit_spread_change': 0.5,
            'vix_level': 40.0,
            'duration_weeks': 1,
        },
        'Rate Shock (+300bps)': {
            'description': 'Hypothetical sudden rate increase',
            'equity_shock': -0.15,
            'bond_shock': -0.20,
            'credit_spread_change': 2.0,
            'vix_level': 40.0,
            'duration_weeks': 12,
        },
    }

    def __init__(self, confidence_level: float = 0.95, trading_days: int = 252):
        self.confidence_level = confidence_level
        self.trading_days = trading_days

    def calculate_var(
        self,
        returns: pd.Series,
        method: str = 'historical',
        horizon: int = 1,
        portfolio_value: float = 1_000_000,
        confidence: Optional[float] = None
    ) -> Dict:
        """
        Calculate Value at Risk using multiple methods.

        Args:
            returns: Daily returns series
            method: 'historical', 'parametric', 'cornish_fisher', or 'all'
            horizon: Holding period in days
            portfolio_value: Current portfolio value
            confidence: Override default confidence level

        Returns:
            Dictionary with VaR results
        """
        conf = confidence or self.confidence_level
        alpha = 1 - conf
        clean_returns = returns.dropna()

        results = {}

        if method in ('historical', 'all'):
            var_pct = np.percentile(clean_returns, alpha * 100)
            results['historical'] = {
                'var_pct': var_pct * np.sqrt(horizon),
                'var_dollar': abs(var_pct * np.sqrt(horizon) * portfolio_value),
                'method': 'Historical Simulation',
            }

        if method in ('parametric', 'all'):
            mu = clean_returns.mean()
            sigma = clean_returns.std()
            z_score = stats.norm.ppf(alpha)
            var_pct = mu + z_score * sigma
            results['parametric'] = {
                'var_pct': var_pct * np.sqrt(horizon),
                'var_dollar': abs(var_pct * np.sqrt(horizon) * portfolio_value),
                'method': 'Parametric (Normal)',
            }

        if method in ('cornish_fisher', 'all'):
            mu = clean_returns.mean()
            sigma = clean_returns.std()
            skew = clean_returns.skew()
            kurt = clean_returns.kurtosis()
            z = stats.norm.ppf(alpha)
            z_cf = (z + (z**2 - 1) * skew / 6
                    + (z**3 - 3*z) * kurt / 24
                    - (2*z**3 - 5*z) * skew**2 / 36)
            var_pct = mu + z_cf * sigma
            results['cornish_fisher'] = {
                'var_pct': var_pct * np.sqrt(horizon),
                'var_dollar': abs(var_pct * np.sqrt(horizon) * portfolio_value),
                'method': 'Cornish-Fisher (Fat Tails)',
            }

        if method != 'all':
            return results.get(method, results)

        return results

    def calculate_cvar(
        self,
        returns: pd.Series,
        method: str = 'historical',
        horizon: int = 1,
        portfolio_value: float = 1_000_000,
        confidence: Optional[float] = None
    ) -> Dict:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).
        """
        conf = confidence or self.confidence_level
        alpha = 1 - conf
        clean_returns = returns.dropna()

        results = {}

        if method in ('historical', 'all'):
            var_threshold = np.percentile(clean_returns, alpha * 100)
            tail_returns = clean_returns[clean_returns <= var_threshold]
            cvar_pct = tail_returns.mean() if len(tail_returns) > 0 else var_threshold
            results['historical'] = {
                'cvar_pct': cvar_pct * np.sqrt(horizon),
                'cvar_dollar': abs(cvar_pct * np.sqrt(horizon) * portfolio_value),
                'var_pct': var_threshold * np.sqrt(horizon),
                'n_tail_observations': len(tail_returns),
                'method': 'Historical ES',
            }

        if method in ('parametric', 'all'):
            mu = clean_returns.mean()
            sigma = clean_returns.std()
            z = stats.norm.ppf(alpha)
            es_z = stats.norm.pdf(z) / alpha
            cvar_pct = mu - sigma * es_z
            results['parametric'] = {
                'cvar_pct': cvar_pct * np.sqrt(horizon),
                'cvar_dollar': abs(cvar_pct * np.sqrt(horizon) * portfolio_value),
                'method': 'Parametric ES',
            }

        if method != 'all':
            return results.get(method, results)

        return results

    def calculate_component_var(
        self,
        position_returns: pd.DataFrame,
        weights: np.ndarray,
        portfolio_value: float = 1_000_000,
        confidence: Optional[float] = None
    ) -> Dict:
        """
        Calculate Component VaR - each position's contribution to total VaR.
        """
        conf = confidence or self.confidence_level
        clean_returns = position_returns.dropna()

        cov_matrix = clean_returns.cov() * self.trading_days
        port_variance = weights @ cov_matrix.values @ weights
        port_vol = np.sqrt(port_variance)
        z = stats.norm.ppf(1 - conf)
        total_var = abs(z * port_vol * portfolio_value)

        marginal_var = (cov_matrix.values @ weights) / port_vol
        component_var = weights * marginal_var
        component_var_dollar = component_var * abs(z) * portfolio_value

        pct_contribution = component_var / port_vol * 100

        return {
            'total_var': total_var,
            'total_var_pct': abs(z * port_vol),
            'component_var': dict(zip(clean_returns.columns, component_var_dollar)),
            'pct_contribution': dict(zip(clean_returns.columns, pct_contribution)),
            'marginal_var': dict(zip(clean_returns.columns, marginal_var * abs(z) * portfolio_value)),
        }

    def run_stress_test(
        self,
        portfolio_value: float,
        position_weights: Dict[str, float],
        asset_classes: Optional[Dict[str, str]] = None,
        scenarios: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Run stress tests against historical and hypothetical scenarios.

        Args:
            portfolio_value: Total portfolio value
            position_weights: Dict of {symbol: weight}
            asset_classes: Dict of {symbol: asset_class} (equity, bond, etc.)
            scenarios: Custom scenarios (uses HISTORICAL_SCENARIOS if None)

        Returns:
            DataFrame with scenario impacts
        """
        if scenarios is None:
            scenarios = self.HISTORICAL_SCENARIOS

        if asset_classes is None:
            asset_classes = {s: 'equity' for s in position_weights}

        results = []
        for scenario_name, params in scenarios.items():
            total_impact = 0
            position_impacts = {}

            for symbol, weight in position_weights.items():
                ac = asset_classes.get(symbol, 'equity').lower()
                position_value = portfolio_value * weight

                if ac in ('equity', 'stock', 'u.s. large cap equity', 'u.s. small cap equity',
                          'international equity', 'emerging markets equity'):
                    shock = params['equity_shock']
                elif ac in ('bond', 'fixed income', 'u.s. aggregate bonds', 'u.s. treasury'):
                    shock = params['bond_shock']
                else:
                    shock = params['equity_shock'] * 0.7

                impact = position_value * shock
                total_impact += impact
                position_impacts[symbol] = impact

            results.append({
                'Scenario': scenario_name,
                'Description': params['description'],
                'Portfolio Impact ($)': total_impact,
                'Portfolio Impact (%)': total_impact / portfolio_value * 100 if portfolio_value > 0 else 0,
                'Worst Position': min(position_impacts, key=position_impacts.get) if position_impacts else 'N/A',
                'VIX Level': params['vix_level'],
                'Duration (Weeks)': params['duration_weeks'],
            })

        return pd.DataFrame(results).sort_values('Portfolio Impact ($)')

    def run_custom_stress_test(
        self,
        returns: pd.Series,
        equity_shock: float,
        bond_shock: float = 0.0,
        portfolio_value: float = 1_000_000
    ) -> Dict:
        """Run a custom hypothetical stress test."""
        clean_returns = returns.dropna()
        beta = 1.0

        if len(clean_returns) > 30:
            try:
                import yfinance as yf
                spy = yf.download('SPY', start=clean_returns.index[0].strftime('%Y-%m-%d'),
                                  end=clean_returns.index[-1].strftime('%Y-%m-%d'), progress=False)
                if not spy.empty:
                    if isinstance(spy.columns, pd.MultiIndex):
                        spy_ret = spy[('Close', 'SPY')].pct_change().dropna()
                    else:
                        spy_ret = spy['Close'].pct_change().dropna()
                    aligned = pd.DataFrame({'port': clean_returns, 'spy': spy_ret}).dropna()
                    if len(aligned) > 10:
                        cov = np.cov(aligned['port'], aligned['spy'])
                        beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 1.0
            except Exception:
                pass

        estimated_impact = equity_shock * beta
        stressed_value = portfolio_value * (1 + estimated_impact)

        return {
            'equity_shock': equity_shock,
            'bond_shock': bond_shock,
            'portfolio_beta': beta,
            'estimated_impact_pct': estimated_impact * 100,
            'estimated_impact_dollar': estimated_impact * portfolio_value,
            'stressed_portfolio_value': stressed_value,
            'loss_dollar': portfolio_value - stressed_value,
        }

    def calculate_risk_budget(
        self,
        position_returns: pd.DataFrame,
        weights: np.ndarray,
        risk_budgets: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Analyze risk budgeting - how risk is allocated across positions.

        Args:
            position_returns: DataFrame of position returns
            weights: Current position weights
            risk_budgets: Target risk allocations (equal if None)
        """
        clean_returns = position_returns.dropna()
        cov_matrix = clean_returns.cov() * self.trading_days
        port_variance = weights @ cov_matrix.values @ weights
        port_vol = np.sqrt(port_variance)

        marginal_risk = (cov_matrix.values @ weights) / port_vol
        risk_contribution = weights * marginal_risk
        risk_pct = risk_contribution / port_vol * 100

        if risk_budgets is None:
            n = len(weights)
            risk_budgets = {col: 100 / n for col in clean_returns.columns}

        tracking = {}
        for i, col in enumerate(clean_returns.columns):
            target = risk_budgets.get(col, 100 / len(weights))
            actual = risk_pct[i]
            tracking[col] = {
                'weight': weights[i] * 100,
                'risk_contribution_pct': actual,
                'target_risk_budget': target,
                'deviation': actual - target,
                'risk_per_unit_weight': actual / (weights[i] * 100) if weights[i] > 0 else 0,
            }

        return {
            'portfolio_volatility': port_vol,
            'position_risk': tracking,
            'total_risk_pct': sum(risk_pct),
            'concentration_index': np.sum(risk_pct ** 2) / 10000,
        }

    def calculate_risk_parity_weights(
        self,
        position_returns: pd.DataFrame
    ) -> Dict:
        """
        Calculate risk parity weights (equal risk contribution).
        """
        clean_returns = position_returns.dropna()
        cov_matrix = clean_returns.cov().values * self.trading_days
        n = len(clean_returns.columns)

        def risk_budget_objective(weights):
            port_vol = np.sqrt(weights @ cov_matrix @ weights)
            marginal_risk = cov_matrix @ weights / port_vol
            risk_contrib = weights * marginal_risk
            target = port_vol / n
            return np.sum((risk_contrib - target) ** 2)

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = [(0.01, 0.5)] * n
        x0 = np.ones(n) / n

        result = minimize(risk_budget_objective, x0, method='SLSQP',
                          bounds=bounds, constraints=constraints)

        rp_weights = result.x
        port_vol = np.sqrt(rp_weights @ cov_matrix @ rp_weights)
        marginal_risk = cov_matrix @ rp_weights / port_vol
        risk_contrib = rp_weights * marginal_risk

        return {
            'weights': dict(zip(clean_returns.columns, rp_weights)),
            'risk_contributions': dict(zip(clean_returns.columns, risk_contrib / port_vol * 100)),
            'portfolio_volatility': port_vol,
            'optimization_success': result.success,
        }

    def calculate_drawdown_analysis(self, returns: pd.Series) -> Dict:
        """Comprehensive drawdown analysis."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdowns = (cumulative - running_max) / running_max

        max_dd = drawdowns.min()
        max_dd_end = drawdowns.idxmin()

        peak_idx = cumulative[:max_dd_end].idxmax()
        recovery_mask = cumulative[max_dd_end:] >= cumulative[peak_idx]
        recovery_date = recovery_mask[recovery_mask].index[0] if recovery_mask.any() else None

        dd_periods = []
        in_drawdown = False
        dd_start = None
        dd_peak_val = None

        for i in range(len(drawdowns)):
            if drawdowns.iloc[i] < -0.01 and not in_drawdown:
                in_drawdown = True
                dd_start = drawdowns.index[i]
                dd_peak_val = cumulative.iloc[i - 1] if i > 0 else cumulative.iloc[0]
            elif drawdowns.iloc[i] >= -0.001 and in_drawdown:
                in_drawdown = False
                dd_trough_idx = drawdowns[dd_start:drawdowns.index[i]].idxmin()
                dd_periods.append({
                    'start': dd_start,
                    'trough': dd_trough_idx,
                    'end': drawdowns.index[i],
                    'depth': drawdowns[dd_trough_idx],
                    'duration_days': (drawdowns.index[i] - dd_start).days,
                })

        dd_periods.sort(key=lambda x: x['depth'])
        top_5 = dd_periods[:5]

        avg_drawdown = drawdowns[drawdowns < 0].mean() if len(drawdowns[drawdowns < 0]) > 0 else 0
        pct_time_in_drawdown = (drawdowns < -0.01).sum() / len(drawdowns) * 100

        return {
            'max_drawdown': max_dd,
            'max_drawdown_peak': peak_idx,
            'max_drawdown_trough': max_dd_end,
            'max_drawdown_recovery': recovery_date,
            'recovery_days': (recovery_date - max_dd_end).days if recovery_date else None,
            'current_drawdown': drawdowns.iloc[-1],
            'average_drawdown': avg_drawdown,
            'pct_time_in_drawdown': pct_time_in_drawdown,
            'top_5_drawdowns': top_5,
            'drawdown_series': drawdowns,
        }

    def calculate_tail_risk_metrics(self, returns: pd.Series) -> Dict:
        """Calculate tail risk statistics."""
        clean = returns.dropna()

        return {
            'skewness': clean.skew(),
            'kurtosis': clean.kurtosis(),
            'excess_kurtosis': clean.kurtosis() - 3,
            'jarque_bera_stat': stats.jarque_bera(clean)[0],
            'jarque_bera_pvalue': stats.jarque_bera(clean)[1],
            'is_normal': stats.jarque_bera(clean)[1] > 0.05,
            'worst_day': clean.min(),
            'worst_week': clean.rolling(5).sum().min() if len(clean) >= 5 else clean.min(),
            'worst_month': clean.rolling(21).sum().min() if len(clean) >= 21 else clean.min(),
            'best_day': clean.max(),
            'pct_negative_days': (clean < 0).sum() / len(clean) * 100,
            'gain_loss_ratio': abs(clean[clean > 0].mean() / clean[clean < 0].mean()) if (clean < 0).any() and (clean > 0).any() else 0,
            'tail_ratio': abs(np.percentile(clean, 95) / np.percentile(clean, 5)) if np.percentile(clean, 5) != 0 else 0,
        }

    def generate_risk_report(
        self,
        returns: pd.Series,
        portfolio_value: float = 1_000_000,
        position_weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """Generate comprehensive risk management report."""
        report = {
            'var': self.calculate_var(returns, method='all', portfolio_value=portfolio_value),
            'cvar': self.calculate_cvar(returns, method='all', portfolio_value=portfolio_value),
            'drawdown': self.calculate_drawdown_analysis(returns),
            'tail_risk': self.calculate_tail_risk_metrics(returns),
        }

        if position_weights:
            report['stress_test'] = self.run_stress_test(
                portfolio_value, position_weights
            )

        return report
