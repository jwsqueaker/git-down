"""Factor Analysis Service - Fama-French and multi-factor risk models."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
import yfinance as yf


class FactorAnalysis:
    """Multi-factor risk model analysis for institutional portfolios."""

    # Standard Fama-French factors
    FACTOR_DESCRIPTIONS = {
        'MKT': 'Market Risk Premium (Rm - Rf)',
        'SMB': 'Small Minus Big (Size Factor)',
        'HML': 'High Minus Low (Value Factor)',
        'RMW': 'Robust Minus Weak (Profitability)',
        'CMA': 'Conservative Minus Aggressive (Investment)',
        'MOM': 'Momentum Factor (Winners - Losers)',
    }

    # Proxy ETFs for factor construction
    FACTOR_PROXIES = {
        'MKT': {'long': 'SPY', 'short': None},
        'SMB': {'long': 'IWM', 'short': 'SPY'},
        'HML': {'long': 'IWD', 'short': 'IWF'},
        'RMW': {'long': 'QUAL', 'short': None},
        'CMA': {'long': 'VLUE', 'short': None},
        'MOM': {'long': 'MTUM', 'short': None},
    }

    def __init__(self, risk_free_rate: float = 0.045):
        self.risk_free_rate = risk_free_rate
        self._factor_returns = None

    def construct_factor_returns(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Construct factor return series from ETF proxies.

        Returns DataFrame with columns for each factor's daily returns.
        """
        all_prices = {}
        tickers = set()
        for factor, proxies in self.FACTOR_PROXIES.items():
            tickers.add(proxies['long'])
            if proxies['short']:
                tickers.add(proxies['short'])

        for ticker in tickers:
            try:
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                if not data.empty:
                    if isinstance(data.columns, pd.MultiIndex):
                        all_prices[ticker] = data[('Close', ticker)]
                    else:
                        all_prices[ticker] = data['Close']
            except Exception:
                continue

        if not all_prices:
            return pd.DataFrame()

        prices_df = pd.DataFrame(all_prices).dropna()
        returns_df = prices_df.pct_change().dropna()

        daily_rf = self.risk_free_rate / 252
        factor_returns = {}

        for factor, proxies in self.FACTOR_PROXIES.items():
            long_ticker = proxies['long']
            short_ticker = proxies['short']

            if long_ticker not in returns_df.columns:
                continue

            if factor == 'MKT':
                factor_returns[factor] = returns_df[long_ticker] - daily_rf
            elif short_ticker and short_ticker in returns_df.columns:
                factor_returns[factor] = returns_df[long_ticker] - returns_df[short_ticker]
            else:
                factor_returns[factor] = returns_df[long_ticker] - daily_rf

        self._factor_returns = pd.DataFrame(factor_returns)
        return self._factor_returns

    def run_factor_regression(
        self,
        portfolio_returns: pd.Series,
        factors: Optional[List[str]] = None,
        model: str = 'ff5'
    ) -> Dict:
        """
        Run multi-factor regression on portfolio returns.

        Args:
            portfolio_returns: Daily portfolio returns series
            factors: Specific factors to use (None = use model default)
            model: 'capm', 'ff3', 'ff5', 'ff5_mom', or 'custom'

        Returns:
            Dictionary with regression results including alpha, betas, R-squared, etc.
        """
        if self._factor_returns is None or self._factor_returns.empty:
            end_date = portfolio_returns.index[-1].strftime('%Y-%m-%d')
            start_date = portfolio_returns.index[0].strftime('%Y-%m-%d')
            self.construct_factor_returns(start_date, end_date)

        if self._factor_returns is None or self._factor_returns.empty:
            return {'error': 'Unable to construct factor returns'}

        model_factors = {
            'capm': ['MKT'],
            'ff3': ['MKT', 'SMB', 'HML'],
            'ff5': ['MKT', 'SMB', 'HML', 'RMW', 'CMA'],
            'ff5_mom': ['MKT', 'SMB', 'HML', 'RMW', 'CMA', 'MOM'],
        }

        if factors is None:
            factors = model_factors.get(model, ['MKT', 'SMB', 'HML'])

        available_factors = [f for f in factors if f in self._factor_returns.columns]
        if not available_factors:
            return {'error': 'No matching factors available'}

        aligned = pd.DataFrame({
            'portfolio': portfolio_returns,
            **{f: self._factor_returns[f] for f in available_factors}
        }).dropna()

        if len(aligned) < 30:
            return {'error': f'Insufficient data points ({len(aligned)}). Need at least 30.'}

        daily_rf = self.risk_free_rate / 252
        y = aligned['portfolio'] - daily_rf
        X = aligned[available_factors]
        X_with_const = np.column_stack([np.ones(len(X)), X.values])

        result = np.linalg.lstsq(X_with_const, y.values, rcond=None)
        coefficients = result[0]

        alpha = coefficients[0]
        betas = dict(zip(available_factors, coefficients[1:]))

        y_pred = X_with_const @ coefficients
        residuals = y.values - y_pred
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y.values - np.mean(y.values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        n = len(y)
        p = len(available_factors)
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - p - 1) if n > p + 1 else r_squared

        mse = ss_res / (n - p - 1) if n > p + 1 else 0
        se_coefficients = np.sqrt(np.diag(mse * np.linalg.pinv(X_with_const.T @ X_with_const)))

        t_stats = coefficients / se_coefficients if np.all(se_coefficients > 0) else np.zeros_like(coefficients)
        p_values = [2 * (1 - stats.t.cdf(abs(t), n - p - 1)) for t in t_stats]

        annualized_alpha = alpha * 252
        tracking_error = np.std(residuals) * np.sqrt(252)

        factor_contributions = {}
        for i, factor in enumerate(available_factors):
            factor_mean = aligned[factor].mean() * 252
            factor_contributions[factor] = betas[factor] * factor_mean

        return {
            'model': model,
            'factors_used': available_factors,
            'alpha_daily': alpha,
            'alpha_annualized': annualized_alpha,
            'alpha_t_stat': t_stats[0],
            'alpha_p_value': p_values[0],
            'betas': betas,
            'beta_t_stats': dict(zip(available_factors, t_stats[1:])),
            'beta_p_values': dict(zip(available_factors, p_values[1:])),
            'r_squared': r_squared,
            'adj_r_squared': adj_r_squared,
            'tracking_error': tracking_error,
            'information_ratio': annualized_alpha / tracking_error if tracking_error > 0 else 0,
            'factor_contributions': factor_contributions,
            'residual_volatility': np.std(residuals) * np.sqrt(252),
            'n_observations': n,
        }

    def rolling_factor_exposure(
        self,
        portfolio_returns: pd.Series,
        window: int = 60,
        factors: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Calculate rolling factor exposures over time.

        Returns DataFrame with rolling betas for each factor.
        """
        if self._factor_returns is None or self._factor_returns.empty:
            end_date = portfolio_returns.index[-1].strftime('%Y-%m-%d')
            start_date = portfolio_returns.index[0].strftime('%Y-%m-%d')
            self.construct_factor_returns(start_date, end_date)

        if self._factor_returns is None or self._factor_returns.empty:
            return pd.DataFrame()

        if factors is None:
            factors = [f for f in ['MKT', 'SMB', 'HML'] if f in self._factor_returns.columns]

        aligned = pd.DataFrame({
            'portfolio': portfolio_returns,
            **{f: self._factor_returns[f] for f in factors}
        }).dropna()

        if len(aligned) < window:
            return pd.DataFrame()

        daily_rf = self.risk_free_rate / 252
        rolling_betas = {f: [] for f in factors}
        rolling_alpha = []
        dates = []

        for i in range(window, len(aligned)):
            window_data = aligned.iloc[i - window:i]
            y = window_data['portfolio'] - daily_rf
            X = window_data[factors].values
            X_with_const = np.column_stack([np.ones(len(X)), X])

            try:
                result = np.linalg.lstsq(X_with_const, y.values, rcond=None)
                coeffs = result[0]
                rolling_alpha.append(coeffs[0] * 252)
                for j, factor in enumerate(factors):
                    rolling_betas[factor].append(coeffs[j + 1])
                dates.append(aligned.index[i])
            except Exception:
                continue

        result_df = pd.DataFrame({'Alpha (Ann.)': rolling_alpha, **rolling_betas}, index=dates)
        return result_df

    def factor_risk_decomposition(
        self,
        portfolio_returns: pd.Series,
        factors: Optional[List[str]] = None
    ) -> Dict:
        """
        Decompose portfolio risk into systematic (factor) and idiosyncratic components.
        """
        regression = self.run_factor_regression(portfolio_returns, factors)
        if 'error' in regression:
            return regression

        total_variance = portfolio_returns.var() * 252
        residual_variance = regression['residual_volatility'] ** 2
        systematic_variance = total_variance - residual_variance

        factor_variances = {}
        if self._factor_returns is not None:
            for factor in regression['factors_used']:
                if factor in self._factor_returns.columns:
                    beta = regression['betas'][factor]
                    factor_var = self._factor_returns[factor].var() * 252
                    factor_variances[factor] = (beta ** 2) * factor_var

        return {
            'total_risk': np.sqrt(total_variance),
            'systematic_risk': np.sqrt(max(systematic_variance, 0)),
            'idiosyncratic_risk': regression['residual_volatility'],
            'systematic_pct': systematic_variance / total_variance * 100 if total_variance > 0 else 0,
            'idiosyncratic_pct': residual_variance / total_variance * 100 if total_variance > 0 else 0,
            'factor_risk_contributions': factor_variances,
            'r_squared': regression['r_squared'],
        }

    def style_analysis(
        self,
        portfolio_returns: pd.Series,
        style_benchmarks: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Returns-based style analysis (RBSA) using constrained regression.
        Decomposes portfolio returns into style benchmark exposures.
        """
        if style_benchmarks is None:
            style_benchmarks = {
                'Large Growth': 'IWF',
                'Large Value': 'IWD',
                'Small Growth': 'IWO',
                'Small Value': 'IWN',
                'International': 'EFA',
                'Emerging Markets': 'EEM',
                'Bonds': 'AGG',
            }

        benchmark_returns = {}
        start = portfolio_returns.index[0].strftime('%Y-%m-%d')
        end = portfolio_returns.index[-1].strftime('%Y-%m-%d')

        for name, ticker in style_benchmarks.items():
            try:
                data = yf.download(ticker, start=start, end=end, progress=False)
                if not data.empty:
                    if isinstance(data.columns, pd.MultiIndex):
                        benchmark_returns[name] = data[('Close', ticker)].pct_change().dropna()
                    else:
                        benchmark_returns[name] = data['Close'].pct_change().dropna()
            except Exception:
                continue

        if not benchmark_returns:
            return {'error': 'Unable to fetch benchmark data'}

        bench_df = pd.DataFrame(benchmark_returns)
        aligned = pd.DataFrame({'portfolio': portfolio_returns}).join(bench_df, how='inner').dropna()

        if len(aligned) < 30:
            return {'error': 'Insufficient data for style analysis'}

        y = aligned['portfolio'].values
        X = aligned.drop(columns=['portfolio']).values
        style_names = list(aligned.columns[1:])

        from scipy.optimize import minimize

        def objective(weights):
            predicted = X @ weights
            return np.sum((y - predicted) ** 2)

        n_styles = len(style_names)
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
        ]
        bounds = [(0.0, 1.0)] * n_styles
        x0 = np.ones(n_styles) / n_styles

        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        weights = dict(zip(style_names, result.x))
        y_pred = X @ result.x
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            'style_weights': weights,
            'r_squared': r_squared,
            'selection_return': (y.mean() - y_pred.mean()) * 252,
            'style_benchmarks_used': list(style_benchmarks.keys()),
        }

    def generate_factor_report(self, portfolio_returns: pd.Series) -> Dict:
        """Generate comprehensive factor analysis report."""
        results = {}

        for model in ['capm', 'ff3', 'ff5']:
            results[model] = self.run_factor_regression(portfolio_returns, model=model)

        results['risk_decomposition'] = self.factor_risk_decomposition(portfolio_returns)
        results['style_analysis'] = self.style_analysis(portfolio_returns)

        return results
