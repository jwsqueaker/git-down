"""YOLOv8-based pothole detector."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single pothole detection."""

    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    label: str = "pothole"

    @property
    def area(self) -> int:
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @property
    def centre(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)


@dataclass
class DetectionResult:
    """Result for a single image."""

    image_path: str
    detections: list[Detection] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.detections)


class PotholeDetector:
    """Detect potholes in images or video frames using YOLOv8.

    Parameters
    ----------
    model_name : str
        Ultralytics model identifier (e.g. ``"yolov8m"``).
    confidence : float
        Minimum detection confidence.
    device : str
        Torch device string (``"cpu"``, ``"cuda:0"``, etc.).
    img_size : int
        Inference image size.
    """

    CLASS_NAMES = {0: "pothole"}

    def __init__(
        self,
        model_name: str = "yolov8m",
        confidence: float = 0.45,
        device: str = "cpu",
        img_size: int = 640,
        weights_path: str | Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.confidence = confidence
        self.device = device
        self.img_size = img_size
        self._model = None
        self._weights_path = Path(weights_path) if weights_path else None

    # ------------------------------------------------------------------
    # Lazy-load the YOLO model so importing the module stays fast.
    # ------------------------------------------------------------------
    @property
    def model(self):
        if self._model is None:
            from ultralytics import YOLO

            src = str(self._weights_path) if self._weights_path else f"{self.model_name}.pt"
            self._model = YOLO(src)
            logger.info("Loaded YOLO model %s on %s", src, self.device)
        return self._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def detect_image(self, image: np.ndarray | str | Path) -> DetectionResult:
        """Run detection on a single image (path or BGR ndarray)."""
        if isinstance(image, (str, Path)):
            path = str(image)
            image = cv2.imread(path)
            if image is None:
                raise FileNotFoundError(f"Cannot read image: {path}")
        else:
            path = "<ndarray>"

        results = self.model.predict(
            source=image,
            conf=self.confidence,
            imgsz=self.img_size,
            device=self.device,
            verbose=False,
        )

        detections: list[Detection] = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                detections.append(
                    Detection(
                        x1=int(x1),
                        y1=int(y1),
                        x2=int(x2),
                        y2=int(y2),
                        confidence=float(box.conf[0]),
                    )
                )
        return DetectionResult(image_path=path, detections=detections)

    def detect_batch(
        self, images: Sequence[np.ndarray | str | Path]
    ) -> list[DetectionResult]:
        """Run detection on multiple images."""
        return [self.detect_image(img) for img in images]

    def annotate(self, image: np.ndarray, result: DetectionResult) -> np.ndarray:
        """Draw bounding boxes on *image* and return the annotated copy."""
        out = image.copy()
        for d in result.detections:
            cv2.rectangle(out, (d.x1, d.y1), (d.x2, d.y2), (0, 0, 255), 2)
            label = f"{d.label} {d.confidence:.2f}"
            cv2.putText(
                out, label, (d.x1, d.y1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
            )
        return out
