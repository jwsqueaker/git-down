"""FastAPI application that exposes detection, IRI, and prediction endpoints."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

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


# ------------------------------------------------------------------
# App factory
# ------------------------------------------------------------------
def create_app(
    detector: PotholeDetector | None = None,
    iri_engine: QuarterCarIRI | None = None,
    predict_model: DegradationModel | None = None,
) -> FastAPI:
    app = FastAPI(title="Divot API", version="0.1.0")

    _detector = detector or PotholeDetector()
    _iri = iri_engine or QuarterCarIRI()
    _predict = predict_model  # may be None if no model loaded

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

    return app
