"""Cross-reference pothole detections against municipal 311 / open-data records.

This proves the city had prior knowledge of the defect — a key element for
successful damage claims in most jurisdictions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class City(str, Enum):
    LOS_ANGELES = "los_angeles"
    CHICAGO = "chicago"
    NYC = "nyc"
    PHILADELPHIA = "philadelphia"
    HOUSTON = "houston"


@dataclass
class CityRecord:
    """A single 311 / open-data record about a known road defect."""

    record_id: str
    city: City
    lat: float
    lon: float
    reported_date: datetime
    status: str  # e.g. "open", "in_progress", "closed"
    description: str = ""
    source: str = "311"

    @property
    def age_days(self) -> int:
        return (datetime.utcnow() - self.reported_date).days


# Mapping of city → publicly available dataset URLs (illustrative)
_DATA_SOURCES: dict[City, str] = {
    City.LOS_ANGELES: "https://data.lacity.org/resource/pothole-311.json",
    City.CHICAGO: "https://data.cityofchicago.org/resource/pothole-311.json",
    City.NYC: "https://data.cityofnewyork.us/resource/pothole-311.json",
    City.PHILADELPHIA: "https://phl.carto.com/api/v2/sql?q=SELECT+*+FROM+pothole_311",
    City.HOUSTON: "https://data.houstontx.gov/resource/pothole-311.json",
}


class CityDataLookup:
    """Look up municipal pothole records near a given GPS coordinate.

    Parameters
    ----------
    city : City
        Which city's open-data portal to query.
    radius_m : float
        Search radius in metres.
    """

    def __init__(self, city: City, radius_m: float = 50.0) -> None:
        self.city = city
        self.radius_m = radius_m
        self._cache: pd.DataFrame | None = None

    def _haversine_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in metres."""
        import math

        R = 6_371_000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def load_records(self, records: list[dict[str, Any]]) -> None:
        """Load records from a list of dicts (e.g. from a JSON API response)."""
        self._cache = pd.DataFrame(records)
        logger.info("Loaded %d 311 records for %s", len(self._cache), self.city.value)

    def load_csv(self, path: str) -> None:
        """Load records from a local CSV export."""
        self._cache = pd.read_csv(path, parse_dates=["reported_date"])
        logger.info("Loaded %d records from %s", len(self._cache), path)

    def lookup(self, lat: float, lon: float) -> list[CityRecord]:
        """Find 311 records within *radius_m* of the given coordinate."""
        if self._cache is None or self._cache.empty:
            return []

        results: list[CityRecord] = []
        for _, row in self._cache.iterrows():
            dist = self._haversine_m(lat, lon, row["lat"], row["lon"])
            if dist <= self.radius_m:
                results.append(
                    CityRecord(
                        record_id=str(row.get("record_id", "")),
                        city=self.city,
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                        reported_date=pd.Timestamp(row["reported_date"]).to_pydatetime(),
                        status=str(row.get("status", "unknown")),
                        description=str(row.get("description", "")),
                    )
                )
        return results

    def city_knew(self, lat: float, lon: float) -> bool:
        """Return True if the city had at least one prior record near this location."""
        return len(self.lookup(lat, lon)) > 0
