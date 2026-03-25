# DIVOT

**Every pothole has a paper trail.**

Divot is a civic pothole platform that auto-detects road defects, tracks
municipal awareness, and helps drivers file damage claims — backed by evidence.

## How it works

1. **Detect** — dashcam + accelerometer auto-detect potholes in real time
2. **City Knew** — cross-references 311/open-data records to prove the city
   was on notice
3. **File** — generates a pre-filled claim with GPS evidence, photos, and the
   city's own acknowledgement records
4. **Recover** — tracks claim status and pending reimbursement

## Dashboard

```
┌──────────────────────────────────────────────────┐
│  0 DETECTED   0 CITY KNEW   0 FILED   $0 PENDING│
│  0 claims →   This week →   ▶ Demo →             │
│                                                   │
│  ⚙ 7-DAY   📣 Report a pothole                   │
│                                                   │
│  Protected · Auto-detecting · alerts on           │
└──────────────────────────────────────────────────┘
```

## Supported cities

| City | 311 data | Claim portal |
|---|---|---|
| Los Angeles | ✅ | ✅ |
| Chicago | ✅ | ✅ |
| New York City | ✅ | ✅ |
| Philadelphia | ✅ | ✅ |
| Houston | ✅ | ✅ |

## Features

| Module | What it does |
|---|---|
| `divot.detect` | YOLOv8-based pothole detector — dashcam frames or uploaded images |
| `divot.iri` | Quarter-car IRI from accelerometer + GPS traces |
| `divot.predict` | Gradient-boosted model forecasting IRI degradation 6-12 months ahead |
| `divot.claims` | Claim generation, 311 cross-referencing, and status tracking |
| `divot.api` | FastAPI service wrapping all modules behind a REST API |
| `divot.viz` | Folium / Plotly helpers for defect maps and IRI heat-maps |

## Quick start

```bash
# Install
pip install -e ".[dev]"

# Detect potholes in an image
divot detect --input photo.jpg --output results/

# Compute IRI from a drive log
divot iri --accel data/accel.csv --gps data/gps.csv

# Train the predictive model
divot train --data data/road_sections.parquet --out models/

# Launch the API
divot serve --port 8000
```

## Project layout

```
divot/
  detect/       # pothole detection (YOLOv8)
  iri/          # IRI computation (quarter-car model)
  predict/      # predictive degradation model
  claims/       # claim filing, 311 lookup, status tracking
  api/          # FastAPI service
  viz/          # mapping & visualisation helpers
data/           # sample datasets
models/         # saved model weights / artefacts
tests/          # pytest suite
```

## Configuration

Copy `config/default.yaml` and override:

```yaml
detect:
  model: yolov8m
  confidence: 0.45
  device: cpu

claims:
  default_city: los_angeles
  auto_311_lookup: true
```

## License

MIT
