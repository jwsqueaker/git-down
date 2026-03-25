"""CLI entry-point for Divot."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Divot — pothole detection, IRI mapping & predictive modeling.")


@app.command()
def detect(
    input: Path = typer.Option(..., help="Image file or directory of images"),
    output: Path = typer.Option(Path("results"), help="Directory for annotated images"),
    confidence: float = typer.Option(0.45, help="Minimum detection confidence"),
    model: str = typer.Option("yolov8m", help="YOLO model name"),
    device: str = typer.Option("cpu", help="Torch device"),
):
    """Detect potholes in images."""
    from divot.detect import PotholeDetector

    import cv2

    output.mkdir(parents=True, exist_ok=True)
    detector = PotholeDetector(model_name=model, confidence=confidence, device=device)

    paths = list(input.glob("*")) if input.is_dir() else [input]
    for p in paths:
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
            continue
        img = cv2.imread(str(p))
        result = detector.detect_image(img)
        typer.echo(f"{p.name}: {result.count} pothole(s)")
        annotated = detector.annotate(img, result)
        cv2.imwrite(str(output / p.name), annotated)


@app.command()
def iri(
    accel: Path = typer.Option(..., help="Accelerometer CSV"),
    gps: Path = typer.Option(..., help="GPS CSV"),
    segment_length: float = typer.Option(100, help="Segment length in metres"),
):
    """Compute IRI from accelerometer + GPS data."""
    from divot.iri import QuarterCarIRI

    engine = QuarterCarIRI(segment_length_m=segment_length)
    segments = engine.compute_from_csvs(str(accel), str(gps))
    for seg in segments:
        typer.echo(
            f"({seg.start_lat:.5f},{seg.start_lon:.5f}) → "
            f"({seg.end_lat:.5f},{seg.end_lon:.5f})  "
            f"IRI={seg.iri:.2f} m/km"
        )


@app.command()
def train(
    data: Path = typer.Option(..., help="Road sections Parquet file"),
    out: Path = typer.Option(Path("models/degradation.joblib"), help="Output model path"),
):
    """Train the predictive degradation model."""
    import pandas as pd

    from divot.predict import DegradationModel

    df = pd.read_parquet(data)
    model = DegradationModel()
    metrics = model.train(df)
    model.save(out)
    typer.echo(f"Trained — MAE={metrics['mae']:.3f}  RMSE={metrics['rmse']:.3f}  R²={metrics['r2']:.3f}")


@app.command()
def serve(
    port: int = typer.Option(8000, help="Port"),
    host: str = typer.Option("0.0.0.0", help="Host"),
    workers: int = typer.Option(2, help="Uvicorn workers"),
):
    """Launch the FastAPI service."""
    import uvicorn

    uvicorn.run("divot.api:create_app", host=host, port=port, workers=workers, factory=True)


if __name__ == "__main__":
    app()
