"""Tests for the predictive degradation model."""

import numpy as np
import pandas as pd
import pytest

from divot.predict import DegradationModel


def _make_training_data(n: int = 500) -> pd.DataFrame:
    """Generate synthetic road section data."""
    rng = np.random.RandomState(42)
    df = pd.DataFrame({
        "current_iri": rng.uniform(1, 8, n),
        "aadt": rng.uniform(500, 50_000, n),
        "freeze_thaw_cycles": rng.uniform(0, 100, n),
        "pavement_age_years": rng.uniform(0, 30, n),
        "last_repair_years": rng.uniform(0, 15, n),
        "precipitation_mm": rng.uniform(200, 2000, n),
        "heavy_vehicle_pct": rng.uniform(0.02, 0.30, n),
    })
    # Simple synthetic target: IRI grows with age and traffic
    df["future_iri"] = (
        df["current_iri"]
        + 0.1 * df["pavement_age_years"]
        + 0.00001 * df["aadt"]
        + 0.02 * df["freeze_thaw_cycles"]
        + rng.normal(0, 0.3, n)
    )
    return df


class TestDegradationModel:
    def test_train_and_predict(self):
        data = _make_training_data()
        model = DegradationModel(n_estimators=50)
        metrics = model.train(data)

        assert "mae" in metrics
        assert "rmse" in metrics
        assert "r2" in metrics
        assert metrics["r2"] > 0.5  # should learn the pattern

        preds = model.predict(data.head(10))
        assert len(preds) == 10
        assert all(np.isfinite(preds))

    def test_predict_before_train_raises(self):
        model = DegradationModel()
        with pytest.raises(RuntimeError, match="not been trained"):
            model.predict(pd.DataFrame({"current_iri": [3.0]}))

    def test_feature_importance(self):
        data = _make_training_data()
        model = DegradationModel(n_estimators=50)
        model.train(data)
        imp = model.feature_importance()
        assert len(imp) == len(model.features)
        assert imp.sum() > 0

    def test_save_and_load(self, tmp_path):
        data = _make_training_data()
        model = DegradationModel(n_estimators=50)
        model.train(data)

        path = tmp_path / "model.joblib"
        model.save(path)
        assert path.exists()

        model2 = DegradationModel()
        model2.load(path)
        preds = model2.predict(data.head(5))
        assert len(preds) == 5
