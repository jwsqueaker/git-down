"""Tests for the claims module."""

from datetime import datetime

import pytest

from divot.claims.city_data import City, CityDataLookup, CityRecord
from divot.claims.tracker import Claim, ClaimStatus, ClaimTracker, Evidence


class TestClaimTracker:
    def test_create_and_summary(self):
        tracker = ClaimTracker()
        c1 = tracker.create(lat=34.05, lon=-118.25)
        assert c1.status == ClaimStatus.DETECTED

        summary = tracker.summary()
        assert summary["detected"] == 1
        assert summary["total_claims"] == 1

    def test_claim_lifecycle(self):
        tracker = ClaimTracker()
        claim = tracker.create(lat=41.88, lon=-87.63)

        # City knew
        claim.mark_city_knew(["SR-12345"])
        assert claim.status == ClaimStatus.CITY_KNEW
        assert tracker.summary()["city_knew"] == 1

        # File
        claim.file(damage_amount=450.0)
        assert claim.status == ClaimStatus.FILED
        assert claim.filed_at is not None
        assert tracker.summary()["pending_usd"] == 450.0

        # Resolve
        claim.resolve(approved=True)
        assert claim.status == ClaimStatus.APPROVED

    def test_evidence_attachment(self):
        claim = Claim(lat=40.71, lon=-74.01)
        claim.evidence.append(
            Evidence(kind="photo", path_or_url="/tmp/pothole.jpg")
        )
        assert len(claim.evidence) == 1


class TestCityDataLookup:
    def test_lookup_within_radius(self):
        lookup = CityDataLookup(city=City.CHICAGO, radius_m=100)
        lookup.load_records([
            {
                "record_id": "CHI-001",
                "lat": 41.8800,
                "lon": -87.6300,
                "reported_date": "2024-06-01",
                "status": "open",
                "description": "Large pothole on Main St",
            }
        ])

        # Very close — should match
        results = lookup.lookup(41.8801, -87.6301)
        assert len(results) == 1
        assert results[0].record_id == "CHI-001"

    def test_lookup_outside_radius(self):
        lookup = CityDataLookup(city=City.NYC, radius_m=50)
        lookup.load_records([
            {
                "record_id": "NYC-001",
                "lat": 40.7128,
                "lon": -74.0060,
                "reported_date": "2024-06-01",
                "status": "open",
            }
        ])

        # Far away — should not match
        results = lookup.lookup(41.0, -74.0)
        assert len(results) == 0

    def test_city_knew(self):
        lookup = CityDataLookup(city=City.LOS_ANGELES, radius_m=100)
        lookup.load_records([
            {
                "record_id": "LA-100",
                "lat": 34.0522,
                "lon": -118.2437,
                "reported_date": "2024-01-15",
                "status": "open",
            }
        ])
        assert lookup.city_knew(34.0523, -118.2438) is True
        assert lookup.city_knew(35.0, -118.0) is False
