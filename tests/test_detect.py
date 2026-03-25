"""Tests for the pothole detector (mocked YOLO)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from divot.detect.detector import Detection, DetectionResult, PotholeDetector


class TestDetection:
    def test_area(self):
        d = Detection(x1=10, y1=20, x2=110, y2=70, confidence=0.9)
        assert d.area == 100 * 50

    def test_centre(self):
        d = Detection(x1=0, y1=0, x2=100, y2=100, confidence=0.5)
        assert d.centre == (50, 50)


class TestDetectionResult:
    def test_count(self):
        r = DetectionResult(
            image_path="test.jpg",
            detections=[
                Detection(0, 0, 10, 10, 0.9),
                Detection(20, 20, 30, 30, 0.8),
            ],
        )
        assert r.count == 2


class TestPotholeDetector:
    def test_annotate(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        det = Detection(10, 10, 50, 50, 0.85)
        result = DetectionResult(image_path="test.jpg", detections=[det])

        detector = PotholeDetector()
        annotated = detector.annotate(img, result)

        # Annotated image should differ from blank
        assert not np.array_equal(img, annotated)
        assert annotated.shape == img.shape
