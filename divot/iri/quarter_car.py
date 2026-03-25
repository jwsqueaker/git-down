"""Quarter-car model for International Roughness Index computation.

The IRI is the reference simulation of a quarter-car travelling at 80 km/h over
a measured profile.  This module takes vertical acceleration + GPS data recorded
in a vehicle, double-integrates to recover the road profile, then runs the
quarter-car simulation to produce IRI per segment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import signal
from scipy.integrate import cumulative_trapezoid

logger = logging.getLogger(__name__)


@dataclass
class IRISegment:
    """IRI value for one road segment."""

    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    length_m: float
    iri: float  # m/km


class QuarterCarIRI:
    """Compute IRI from accelerometer + GPS traces.

    Parameters match the World Bank quarter-car reference (Golden Car):
        m_s  = 250 kg   (sprung mass — body)
        m_u  = 40 kg    (unsprung mass — axle)
        k_s  = 63000 N/m  (suspension spring)
        c_s  = 6000 N·s/m (suspension damper)
        k_t  = 150000 N/m (tyre spring)
        speed = 80 km/h (22.22 m/s)
    """

    def __init__(
        self,
        m_s: float = 250,
        m_u: float = 40,
        k_s: float = 63000,
        c_s: float = 6000,
        k_t: float = 150000,
        speed_mps: float = 22.22,
        sample_rate_hz: int = 100,
        segment_length_m: float = 100,
    ) -> None:
        self.m_s = m_s
        self.m_u = m_u
        self.k_s = k_s
        self.c_s = c_s
        self.k_t = k_t
        self.speed = speed_mps
        self.fs = sample_rate_hz
        self.segment_length = segment_length_m

        # Build state-space model: x = [z_s, dz_s, z_u, dz_u]
        A = np.array([
            [0, 1, 0, 0],
            [-k_s / m_s, -c_s / m_s, k_s / m_s, c_s / m_s],
            [0, 0, 0, 1],
            [k_s / m_u, c_s / m_u, -(k_s + k_t) / m_u, -c_s / m_u],
        ])
        B = np.array([[0], [0], [0], [k_t / m_u]])
        C = np.array([[1, 0, 0, 0]])  # sprung-mass displacement
        D = np.array([[0]])
        self._sys = signal.StateSpace(A, B, C, D)

    # ------------------------------------------------------------------
    # Profile recovery
    # ------------------------------------------------------------------
    @staticmethod
    def _profile_from_accel(az: np.ndarray, fs: int) -> np.ndarray:
        """Double-integrate vertical acceleration to get road profile estimate.

        A 4th-order high-pass Butterworth at 0.5 Hz removes drift.
        """
        dt = 1.0 / fs
        vel = cumulative_trapezoid(az, dx=dt, initial=0)
        disp = cumulative_trapezoid(vel, dx=dt, initial=0)

        # High-pass to remove drift
        sos = signal.butter(4, 0.5, btype="high", fs=fs, output="sos")
        return signal.sosfiltfilt(sos, disp)

    # ------------------------------------------------------------------
    # Quarter-car simulation
    # ------------------------------------------------------------------
    def _simulate(self, profile: np.ndarray) -> float:
        """Run the quarter-car model and return IRI (m/km)."""
        dx = self.speed / self.fs
        length_m = len(profile) * dx
        if length_m < 1:
            return 0.0

        t = np.arange(len(profile)) / self.fs
        _, y, _ = signal.lsim(self._sys, profile, t)

        # IRI = (1/L) * integral |dz_s/dt - dz_u/dt| dx
        # Simplified: slope = cumulative rectified velocity of sprung mass
        sprung_vel = np.gradient(y.flatten(), t)
        iri = np.mean(np.abs(sprung_vel)) / self.speed * 1000  # m/km
        return float(iri)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute(
        self,
        accel: pd.DataFrame,
        gps: pd.DataFrame,
    ) -> list[IRISegment]:
        """Compute per-segment IRI from accelerometer and GPS dataframes.

        Parameters
        ----------
        accel : DataFrame
            Columns: ``timestamp, ax, ay, az`` (m/s^2, ≥100 Hz).
        gps : DataFrame
            Columns: ``timestamp, lat, lon, speed_mps``.

        Returns
        -------
        list[IRISegment]
        """
        accel = accel.sort_values("timestamp").reset_index(drop=True)
        gps = gps.sort_values("timestamp").reset_index(drop=True)

        az = accel["az"].values
        profile = self._profile_from_accel(az, self.fs)

        # Merge GPS by nearest timestamp to get positions
        gps["timestamp"] = pd.to_datetime(gps["timestamp"])
        accel["timestamp"] = pd.to_datetime(accel["timestamp"])
        merged = pd.merge_asof(accel, gps, on="timestamp", direction="nearest")

        # Compute cumulative distance from speed
        dt = 1.0 / self.fs
        dists = np.cumsum(merged["speed_mps"].fillna(self.speed).values * dt)

        segments: list[IRISegment] = []
        seg_start = 0
        for i in range(1, len(dists)):
            if dists[i] - dists[seg_start] >= self.segment_length:
                seg_profile = profile[seg_start:i]
                iri_val = self._simulate(seg_profile)
                segments.append(
                    IRISegment(
                        start_lat=float(merged["lat"].iloc[seg_start]),
                        start_lon=float(merged["lon"].iloc[seg_start]),
                        end_lat=float(merged["lat"].iloc[i]),
                        end_lon=float(merged["lon"].iloc[i]),
                        length_m=float(dists[i] - dists[seg_start]),
                        iri=iri_val,
                    )
                )
                seg_start = i

        logger.info("Computed IRI for %d segments", len(segments))
        return segments

    def compute_from_csvs(
        self,
        accel_path: str,
        gps_path: str,
    ) -> list[IRISegment]:
        """Convenience wrapper that reads CSVs then calls :meth:`compute`."""
        accel = pd.read_csv(accel_path)
        gps = pd.read_csv(gps_path)
        return self.compute(accel, gps)
