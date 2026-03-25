"""Tests for the FastAPI endpoints."""

import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from divot.api.app import create_app
from divot.detect.detector import Detection, DetectionResult


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    # Provide a mocked detector so we don't need real YOLO weights
    mock_detector = MagicMock()
    mock_detector.detect_image.return_value = DetectionResult(
        image_path="<upload>",
        detections=[Detection(10, 20, 100, 80, 0.92)],
    )
    app = create_app(detector=mock_detector)
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestDetectEndpoint:
    def test_detect_returns_detections(self, client):
        # Create a tiny PNG in memory
        import cv2

        img = np.zeros((64, 64, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".png", img)
        resp = client.post("/detect", files={"image": ("test.png", io.BytesIO(buf.tobytes()))})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["detections"][0]["confidence"] == pytest.approx(0.92)
