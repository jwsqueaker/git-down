"""Claim lifecycle management — create, track, and summarise pothole damage claims."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ClaimStatus(str, Enum):
    DETECTED = "detected"
    CITY_KNEW = "city_knew"
    FILED = "filed"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    PAID = "paid"


@dataclass
class Evidence:
    """A piece of evidence attached to a claim."""

    kind: str  # "photo", "accel_log", "gps_trace", "311_record"
    path_or_url: str
    captured_at: datetime = field(default_factory=datetime.utcnow)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Claim:
    """A single pothole damage claim."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    lat: float = 0.0
    lon: float = 0.0
    detected_at: datetime = field(default_factory=datetime.utcnow)
    status: ClaimStatus = ClaimStatus.DETECTED
    city_records: list[str] = field(default_factory=list)  # matched 311 IDs
    evidence: list[Evidence] = field(default_factory=list)
    damage_amount_usd: float = 0.0
    filed_at: datetime | None = None
    resolved_at: datetime | None = None
    notes: str = ""

    def mark_city_knew(self, record_ids: list[str]) -> None:
        self.city_records = record_ids
        self.status = ClaimStatus.CITY_KNEW

    def file(self, damage_amount: float) -> None:
        self.damage_amount_usd = damage_amount
        self.status = ClaimStatus.FILED
        self.filed_at = datetime.utcnow()

    def mark_pending(self) -> None:
        self.status = ClaimStatus.PENDING

    def resolve(self, approved: bool) -> None:
        self.status = ClaimStatus.APPROVED if approved else ClaimStatus.DENIED
        self.resolved_at = datetime.utcnow()


class ClaimTracker:
    """In-memory claim store with summary statistics for the dashboard."""

    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}

    def create(self, lat: float, lon: float, evidence: list[Evidence] | None = None) -> Claim:
        claim = Claim(lat=lat, lon=lon, evidence=evidence or [])
        self._claims[claim.id] = claim
        logger.info("Created claim %s at (%.5f, %.5f)", claim.id, lat, lon)
        return claim

    def get(self, claim_id: str) -> Claim | None:
        return self._claims.get(claim_id)

    def all(self) -> list[Claim]:
        return list(self._claims.values())

    # ------------------------------------------------------------------
    # Dashboard summary
    # ------------------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        """Return counts matching the dashboard widgets."""
        claims = list(self._claims.values())
        return {
            "detected": sum(1 for c in claims if c.status == ClaimStatus.DETECTED),
            "city_knew": sum(1 for c in claims if c.status == ClaimStatus.CITY_KNEW),
            "filed": sum(
                1 for c in claims if c.status in {ClaimStatus.FILED, ClaimStatus.PENDING}
            ),
            "pending_usd": sum(
                c.damage_amount_usd
                for c in claims
                if c.status in {ClaimStatus.FILED, ClaimStatus.PENDING}
            ),
            "total_claims": len(claims),
        }
