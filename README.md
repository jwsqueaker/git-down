# Divot

**Pothole detection, IRI mapping, and predictive road-condition modeling.**

Divot turns dashcam video and accelerometer data into actionable road-maintenance
intelligence. It detects potholes in real time, computes International Roughness
Index (IRI) profiles, and forecasts future pavement degradation so crews can
prioritize repairs before failures cascade.

## Features

| Module | What it does |
|---|---|
| `divot.detect` | YOLOv8-based pothole detector — works on dashcam frames or images |
| `divot.iri` | Computes quarter-car IRI from accelerometer + GPS traces |
| `divot.predict` | Gradient-boosted regression model that forecasts IRI 6-12 months ahead |
| `divot.api` | FastAPI service that wraps all three modules behind a REST API |
| `divot.viz` | Folium / Plotly helpers for mapping defects and IRI heat-maps |

## Quick start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Detect potholes in an image
divot detect --input photo.jpg --output results/

# 3. Compute IRI from a drive log
divot iri --accel data/accel.csv --gps data/gps.csv

# 4. Train the predictive model
divot train --data data/road_sections.parquet --out models/

# 5. Launch the API
divot serve --port 8000
```

## Project layout

```
divot/
  detect/       # pothole detection (YOLOv8)
  iri/          # IRI computation (quarter-car model)
  predict/      # predictive degradation model
  api/          # FastAPI service
  viz/          # mapping & visualisation helpers
data/           # sample datasets
models/         # saved model weights / artefacts
tests/          # pytest suite
```

## Data formats

**Accelerometer CSV** — columns: `timestamp, ax, ay, az` (m/s^2, 100 Hz+)

**GPS CSV** — columns: `timestamp, lat, lon, speed_mps`

**Road sections Parquet** — one row per 100 m section with historical IRI,
AADT, climate zone, pavement type, last-repair date, etc.

## Configuration

Copy `config/default.yaml` and override values:

```yaml
detect:
  model: yolov8m          # yolov8n | yolov8s | yolov8m
  confidence: 0.45
  device: cuda:0           # cpu | cuda:N

iri:
  quarter_car:
    speed_mps: 22.22       # 80 km/h reference
    sample_rate_hz: 100

predict:
  horizon_months: 6
  features:
    - current_iri
    - aadt
    - freeze_thaw_cycles
    - pavement_age_years
    - last_repair_years
```

## License

MIT
