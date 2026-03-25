"""Tests for the IRI quarter-car module."""

import numpy as np
import pandas as pd
import pytest

from divot.iri import QuarterCarIRI


def _make_accel_gps(n_samples: int = 10_000, fs: int = 100):
    """Generate synthetic accelerometer + GPS data for a ~2.2 km drive at 80 km/h."""
    t = np.arange(n_samples) / fs
    timestamps = pd.date_range("2024-01-01", periods=n_samples, freq=f"{1_000_000 // fs}us")

    # Synthetic vertical accel: mild roughness
    np.random.seed(42)
    az = np.random.normal(0, 0.5, n_samples)
    az += 0.3 * np.sin(2 * np.pi * 5 * t)  # 5 Hz bump component

    accel = pd.DataFrame({
        "timestamp": timestamps,
        "ax": np.zeros(n_samples),
        "ay": np.zeros(n_samples),
        "az": az,
    })

    # GPS — straight line heading east
    speed = 22.22  # m/s
    lat_start, lon_start = 40.0, -74.0
    metres_per_deg_lat = 111_320
    metres_per_deg_lon = 111_320 * np.cos(np.radians(lat_start))

    gps_rate = 10  # Hz
    gps_n = n_samples // (fs // gps_rate)
    gps_ts = timestamps[:: fs // gps_rate][:gps_n]
    dists = np.arange(gps_n) * speed / gps_rate
    lons = lon_start + dists / metres_per_deg_lon

    gps = pd.DataFrame({
        "timestamp": gps_ts,
        "lat": np.full(gps_n, lat_start),
        "lon": lons,
        "speed_mps": np.full(gps_n, speed),
    })

    return accel, gps


class TestQuarterCarIRI:
    def test_basic_computation(self):
        accel, gps = _make_accel_gps()
        engine = QuarterCarIRI(segment_length_m=100)
        segments = engine.compute(accel, gps)

        assert len(segments) > 0
        for seg in segments:
            assert seg.iri >= 0
            assert seg.length_m >= 90  # allow slight tolerance

    def test_smooth_road_low_iri(self):
        """A perfectly smooth road should yield near-zero IRI."""
        n = 10_000
        fs = 100
        timestamps = pd.date_range("2024-01-01", periods=n, freq="10ms")

        accel = pd.DataFrame({
            "timestamp": timestamps,
            "ax": np.zeros(n),
            "ay": np.zeros(n),
            "az": np.zeros(n),  # no vertical acceleration
        })

        gps_n = n // 10
        gps = pd.DataFrame({
            "timestamp": timestamps[::10][:gps_n],
            "lat": np.full(gps_n, 40.0),
            "lon": np.linspace(-74.0, -73.98, gps_n),
            "speed_mps": np.full(gps_n, 22.22),
        })

        engine = QuarterCarIRI(segment_length_m=100)
        segments = engine.compute(accel, gps)
        if segments:
            assert segments[0].iri < 1.0  # should be very low

    def test_empty_data(self):
        accel = pd.DataFrame(columns=["timestamp", "ax", "ay", "az"])
        gps = pd.DataFrame(columns=["timestamp", "lat", "lon", "speed_mps"])
        engine = QuarterCarIRI()
        segments = engine.compute(accel, gps)
        assert segments == []
