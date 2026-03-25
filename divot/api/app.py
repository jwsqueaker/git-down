"""FastAPI application that exposes detection, IRI, prediction, and claims endpoints."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from divot.claims.tracker import ClaimTracker, ClaimStatus, Evidence
from divot.detect import PotholeDetector
from divot.iri import QuarterCarIRI
from divot.predict import DegradationModel


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------
class DetectionOut(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    label: str


class DetectResponse(BaseModel):
    count: int
    detections: list[DetectionOut]


class IRISegmentOut(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    length_m: float
    iri: float


class PredictRequest(BaseModel):
    current_iri: float
    aadt: float
    freeze_thaw_cycles: float
    pavement_age_years: float
    last_repair_years: float
    precipitation_mm: float = 800.0
    heavy_vehicle_pct: float = 0.10


class PredictResponse(BaseModel):
    predicted_iri: float
    horizon_months: int


class ClaimCreate(BaseModel):
    lat: float
    lon: float
    damage_amount_usd: float = 0.0


class ClaimOut(BaseModel):
    id: str
    lat: float
    lon: float
    status: str
    city_records: list[str]
    damage_amount_usd: float


class DashboardSummary(BaseModel):
    detected: int
    city_knew: int
    filed: int
    pending_usd: float
    total_claims: int


# ------------------------------------------------------------------
# App factory
# ------------------------------------------------------------------
def create_app(
    detector: PotholeDetector | None = None,
    iri_engine: QuarterCarIRI | None = None,
    predict_model: DegradationModel | None = None,
) -> FastAPI:
    app = FastAPI(title="Divot API", version="0.1.0")

    # Serve static frontend
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    _detector = detector or PotholeDetector()
    _iri = iri_engine or QuarterCarIRI()
    _predict = predict_model  # may be None if no model loaded
    _claims = ClaimTracker()

    @app.get("/")
    def index():
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/detect", response_model=DetectResponse)
    async def detect(image: UploadFile = File(...)):
        contents = await image.read()
        arr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        result = _detector.detect_image(img)
        return DetectResponse(
            count=result.count,
            detections=[
                DetectionOut(
                    x1=d.x1, y1=d.y1, x2=d.x2, y2=d.y2,
                    confidence=d.confidence, label=d.label,
                )
                for d in result.detections
            ],
        )

    @app.post("/iri", response_model=list[IRISegmentOut])
    async def compute_iri(
        accel: UploadFile = File(...),
        gps: UploadFile = File(...),
    ):
        accel_df = pd.read_csv(io.BytesIO(await accel.read()))
        gps_df = pd.read_csv(io.BytesIO(await gps.read()))
        segments = _iri.compute(accel_df, gps_df)
        return [
            IRISegmentOut(
                start_lat=s.start_lat, start_lon=s.start_lon,
                end_lat=s.end_lat, end_lon=s.end_lon,
                length_m=s.length_m, iri=s.iri,
            )
            for s in segments
        ]

    @app.post("/predict", response_model=PredictResponse)
    def predict(req: PredictRequest):
        if _predict is None:
            return {"error": "No model loaded"}
        row = pd.DataFrame([req.model_dump()])
        pred = _predict.predict(row)[0]
        return PredictResponse(
            predicted_iri=float(pred),
            horizon_months=_predict.horizon_months,
        )

    # ------------------------------------------------------------------
    # Claims endpoints
    # ------------------------------------------------------------------
    @app.get("/dashboard", response_model=DashboardSummary)
    def dashboard():
        return DashboardSummary(**_claims.summary())

    @app.post("/claims", response_model=ClaimOut)
    def create_claim(req: ClaimCreate):
        claim = _claims.create(lat=req.lat, lon=req.lon)
        if req.damage_amount_usd:
            claim.file(req.damage_amount_usd)
        return ClaimOut(
            id=claim.id,
            lat=claim.lat,
            lon=claim.lon,
            status=claim.status.value,
            city_records=claim.city_records,
            damage_amount_usd=claim.damage_amount_usd,
        )

    @app.get("/claims", response_model=list[ClaimOut])
    def list_claims():
        return [
            ClaimOut(
                id=c.id, lat=c.lat, lon=c.lon,
                status=c.status.value,
                city_records=c.city_records,
                damage_amount_usd=c.damage_amount_usd,
            )
            for c in _claims.all()
        ]

    @app.post("/report")
    async def report_pothole(
        lat: float,
        lon: float,
        image: UploadFile = File(None),
    ):
        """Quick-report endpoint: detect + create claim in one call."""
        evidence: list[Evidence] = []
        if image:
            contents = await image.read()
            arr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            result = _detector.detect_image(img)
            if result.count > 0:
                evidence.append(Evidence(kind="photo", path_or_url=image.filename or "upload"))

        claim = _claims.create(lat=lat, lon=lon, evidence=evidence)
        return {
            "claim_id": claim.id,
            "status": claim.status.value,
            "evidence_count": len(evidence),
        }

    return app
