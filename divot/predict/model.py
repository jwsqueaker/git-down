"""Gradient-boosted regression model for forecasting IRI degradation.

Given a road section's current IRI, traffic counts, climate, pavement age, and
maintenance history, the model predicts IRI at a future horizon (default 6 months).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

DEFAULT_FEATURES = [
    "current_iri",
    "aadt",
    "freeze_thaw_cycles",
    "pavement_age_years",
    "last_repair_years",
    "precipitation_mm",
    "heavy_vehicle_pct",
]


class DegradationModel:
    """LightGBM regressor that predicts future IRI for road sections.

    Parameters
    ----------
    features : list[str] | None
        Feature columns. Defaults to :data:`DEFAULT_FEATURES`.
    horizon_months : int
        Prediction horizon.
    **lgb_params
        Extra params forwarded to :class:`lightgbm.LGBMRegressor`.
    """

    def __init__(
        self,
        features: list[str] | None = None,
        horizon_months: int = 6,
        n_estimators: int = 500,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        **lgb_params: Any,
    ) -> None:
        self.features = features or DEFAULT_FEATURES
        self.horizon_months = horizon_months
        self._model = lgb.LGBMRegressor(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            **lgb_params,
        )
        self._is_fitted = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train(
        self,
        data: pd.DataFrame,
        target_col: str = "future_iri",
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> dict[str, float]:
        """Train the model and return evaluation metrics on a hold-out set.

        Parameters
        ----------
        data : DataFrame
            Must contain :attr:`features` columns and *target_col*.
        target_col : str
            Column with the ground-truth future IRI.
        """
        X = data[self.features]
        y = data[target_col]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        self._model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
        )
        self._is_fitted = True

        preds = self._model.predict(X_test)
        metrics = {
            "mae": mean_absolute_error(y_test, preds),
            "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
            "r2": r2_score(y_test, preds),
        }
        logger.info("Training metrics: %s", metrics)
        return metrics

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict future IRI for each row."""
        if not self._is_fitted:
            raise RuntimeError("Model has not been trained yet. Call train() or load() first.")
        return self._model.predict(data[self.features])

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------
    def feature_importance(self) -> pd.Series:
        """Return feature importances as a sorted Series."""
        imp = self._model.feature_importances_
        return pd.Series(imp, index=self.features).sort_values(ascending=False)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: str | Path) -> None:
        """Serialise the trained model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self._model, "features": self.features}, path)
        logger.info("Model saved to %s", path)

    def load(self, path: str | Path) -> None:
        """Load a previously saved model."""
        blob = joblib.load(path)
        self._model = blob["model"]
        self.features = blob["features"]
        self._is_fitted = True
        logger.info("Model loaded from %s", path)
