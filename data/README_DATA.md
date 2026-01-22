# Data Directory

This directory contains data files needed for the pothole detection pipeline.

## LA City Boundary

**Required:** `la_city_boundary.geojson`

### How to Obtain:

1. Visit the LA Open Data Portal: https://data.lacity.org/
2. Search for "City Boundary" or navigate to: https://geohub.lacity.org/datasets/lahub::city-boundary/explore
3. Click "Download" and select "GeoJSON"
4. Save the file as `la_city_boundary.geojson` in this directory

Alternatively, you can use this direct download approach:

```bash
# From the project root directory
curl -o data/la_city_boundary.geojson "https://opendata.arcgis.com/api/v3/datasets/09f503229d37414a8e67a7b6ceb9ec43_7/downloads/data?format=geojson&spatialRefId=4326"
```

## Hotspots

The `hotspots/` directory contains GeoJSON files defining high-priority areas for SkySat tasking.

- Each GeoJSON should contain one or more polygon features
- Polygons should be in WGS84 (EPSG:4326) coordinates
- Add custom properties to describe the hotspot (name, priority, etc.)

See `hotspots/example_hotspot.geojson` for an example.

## Models

The `models/` directory is for storing trained model weights:

- Place your trained U-Net weights as `models/unet_potholes.pth`
- If no weights are provided, the system will use randomly initialized weights (for testing pipeline only)

### Model Training

This repository does not include model training code. To train a pothole detection model:

1. Collect labeled training data (imagery + pothole masks)
2. Train a U-Net model using the architecture in `pothole/model_unet.py`
3. Save the trained weights using `torch.save(model.state_dict(), 'unet_potholes.pth')`
4. Place the weights file in `models/` directory

**Expected Input Format:**
- Input: 3-channel RGB imagery (normalized 0-1)
- Output: Single-channel binary mask (1 = pothole, 0 = background)
- Tile size: 512x512 (configurable)

## Weekly Basemap Data

Downloaded Planet basemap imagery will be stored in:

```
data/weekly_la_basemap/
  YYYY-MM-DD/          # Date-stamped directories
    quad_id_1.tif
    quad_id_2.tif
    ...
  la_weekly_YYYY-MM-DD.vrt   # Virtual raster mosaic
  la_weekly_latest.vrt       # Symlink to most recent VRT
```

This directory is created automatically by `scripts/planet_weekly_basemap_la.py`.
