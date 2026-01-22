# LA Pothole Detection System

End-to-end pipeline for detecting potholes from satellite imagery using deep learning. This system integrates with Planet Labs to fetch weekly imagery of Los Angeles and runs automated pothole detection using a U-Net segmentation model.

## Features

- **Weekly Planet Basemap Integration**: Automatically fetch PlanetScope weekly basemaps for Los Angeles
- **SkySat Tasking**: Submit tasking requests for high-resolution imagery of hotspot areas
- **Deep Learning Detection**: U-Net-based segmentation for pothole detection
- **Geospatial Processing**: Full georeferencing, vectorization, and area calculations
- **Interactive Visualization**: Streamlit app with map-based results display
- **Export Capabilities**: GeoJSON output compatible with GIS tools
- **Cloud Deployment**: Ready for Streamlit Cloud deployment

## 🚀 Quick Deploy

**Deploy to Streamlit Cloud:**

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Deploy from your fork (`streamlit_app.py`)
4. Add secrets (PL_API_KEY, PL_SERIES_NAME) in Settings
5. Done! Start uploading GeoTIFFs to detect potholes

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## Architecture

```
pothole-app/
├── pothole/              # Core detection module
│   ├── model_unet.py     # U-Net architecture
│   ├── infer.py          # Inference pipeline
│   ├── tiling.py         # Image tiling utilities
│   ├── vectorize.py      # Raster-to-vector conversion
│   └── geo.py            # Geospatial utilities
├── scripts/              # Data acquisition scripts
│   ├── planet_list_series.py           # List available Planet basemap series
│   ├── planet_weekly_basemap_la.py     # Fetch weekly LA basemap
│   └── task_skysat_hotspots_weekly.py  # Submit SkySat tasking orders
├── data/                 # Data directory
│   ├── la_city_boundary.geojson   # LA City boundary (download required)
│   ├── hotspots/                  # Hotspot polygons for SkySat tasking
│   └── weekly_la_basemap/         # Downloaded basemap imagery
├── models/               # Model weights directory
├── streamlit_app.py      # Interactive web application
└── requirements.txt      # Python dependencies
```

## Prerequisites

- **Python**: 3.9 or later
- **GDAL**: Required for rasterio (install system package first)
- **Planet API Key**: Required for imagery access
- **Optional**: CUDA-capable GPU for faster inference

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3-dev gdal-bin libgdal-dev
```

**macOS:**
```bash
brew install gdal
```

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd pothole-app
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required
PL_API_KEY=your_planet_api_key_here
PL_SERIES_NAME=your_basemap_series_name

# Optional (for S3 delivery)
AWS_BUCKET=your-bucket-name
AWS_PREFIX=pothole-data/
AWS_REGION=us-west-2
```

Or export directly:

```bash
export PL_API_KEY="your_planet_api_key"
export PL_SERIES_NAME="PlanetScope Weekly Basemap"
```

### 5. Download LA City Boundary

```bash
# Option 1: Download manually from LA Open Data Portal
# Visit: https://geohub.lacity.org/datasets/city-boundary
# Save as: data/la_city_boundary.geojson

# Option 2: Use curl (if direct link available)
curl -o data/la_city_boundary.geojson \
  "https://opendata.arcgis.com/api/v3/datasets/09f503229d37414a8e67a7b6ceb9ec43_7/downloads/data?format=geojson&spatialRefId=4326"
```

### 6. (Optional) Add Model Weights

If you have trained model weights:

```bash
cp /path/to/your/weights.pth models/unet_potholes.pth
```

**Note:** The system will work without weights (using random initialization) for testing the pipeline, but results won't be meaningful.

## Usage

### Quick Start Guide

**Complete workflow in 5 steps:**

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Set environment variables
export PL_API_KEY="your_api_key"
export PL_SERIES_NAME="PlanetScope Weekly Basemap"

# 3. List available basemap series (find your series name)
python scripts/planet_list_series.py

# 4. Fetch latest weekly basemap for LA
python scripts/planet_weekly_basemap_la.py

# 5. Run Streamlit app
streamlit run streamlit_app.py
```

### Script Details

#### 1. List Available Planet Basemap Series

Discover what basemap series are available to your account:

```bash
python scripts/planet_list_series.py
```

**Output:**
```
Available Basemap Series:
  - PlanetScope Weekly Basemap (global_monthly_2023_01_mosaic)
  - California Monthly Basemap (california_monthly_mosaic)
  ...
```

Set the `PL_SERIES_NAME` environment variable to the exact name you want to use.

#### 2. Fetch Weekly Planet Basemap

Download the latest mosaic from your chosen series:

```bash
python scripts/planet_weekly_basemap_la.py \
  --api-key $PL_API_KEY \
  --series-name "$PL_SERIES_NAME" \
  --aoi data/la_city_boundary.geojson \
  --output-dir data/weekly_la_basemap \
  --delivery local
```

**Options:**
- `--api-key`: Planet API key (or use PL_API_KEY env var)
- `--series-name`: Exact basemap series name (or use PL_SERIES_NAME env var)
- `--aoi`: Path to LA boundary GeoJSON (default: data/la_city_boundary.geojson)
- `--output-dir`: Output directory for downloaded quads (default: data/weekly_la_basemap)
- `--delivery`: Delivery method - 'local' or 's3' (default: local)

**Output:**
```
data/weekly_la_basemap/
  2024-01-15/           # Date-stamped directory
    quad_1.tif
    quad_2.tif
    ...
  la_weekly_2024-01-15.vrt    # Virtual raster
  la_weekly_latest.vrt        # Symlink to latest
```

#### 3. Submit SkySat Tasking (Optional)

Create tasking orders for high-priority hotspot areas:

```bash
python scripts/task_skysat_hotspots_weekly.py \
  --api-key $PL_API_KEY \
  --hotspots-dir data/hotspots \
  --cloud-threshold 0.1 \
  --off-nadir-angle-max 20 \
  --acquisitions 1 \
  --dry-run
```

**Options:**
- `--hotspots-dir`: Directory with hotspot GeoJSON files (default: data/hotspots)
- `--start-time`: Start of tasking window (ISO 8601, default: now)
- `--end-time`: End of tasking window (ISO 8601, default: +7 days)
- `--cloud-threshold`: Max cloud cover (0.0-1.0, default: 0.1)
- `--off-nadir-angle-max`: Max off-nadir angle in degrees (default: 20)
- `--acquisitions`: Number of acquisitions requested (default: 1)
- `--dry-run`: Print orders without submitting

Remove `--dry-run` to actually submit orders.

#### 4. Run Detection (Command Line)

Run detection programmatically:

```python
from pothole import PotholeDetector

detector = PotholeDetector(
    model_path="models/unet_potholes.pth",  # Optional
    tile_size=512,
    overlap=64,
    threshold=0.5,
    min_area=1.0,
)

geojson = detector.process_geotiff(
    "data/weekly_la_basemap/la_weekly_latest.vrt",
    output_geojson_path="output/potholes_detected.geojson",
)

print(f"Detected {len(geojson['features'])} potholes")
```

#### 5. Run Streamlit App

Launch the interactive web application:

```bash
streamlit run streamlit_app.py
```

**The app provides:**
- Upload custom GeoTIFF or use latest Planet basemap
- Configure detection parameters (tile size, threshold, etc.)
- Run detection with progress tracking
- Interactive map visualization
- Download results as GeoJSON
- Statistics and data table view

Access at: http://localhost:8501

## Model Training

This repository includes the U-Net architecture but not training code. To train a model:

### Data Format

- **Input Images**: RGB GeoTIFF tiles (512x512 recommended)
- **Ground Truth**: Binary masks (1 = pothole, 0 = background)
- **Format**: GeoTIFF or PNG with matching filenames

### Training Steps

1. Prepare a dataset of labeled potholes
2. Use the U-Net architecture from `pothole/model_unet.py`
3. Train with standard segmentation loss (BCE, Dice, etc.)
4. Save weights: `torch.save(model.state_dict(), 'unet_potholes.pth')`
5. Place in `models/` directory

### Expected Performance

**Note:** PlanetScope imagery (3-4m resolution) is NOT sufficient for detecting small potholes. This pipeline is designed to be modular and work with:

- **High-resolution aerial imagery** (10-30 cm GSD)
- **Drone imagery** (2-10 cm GSD)
- **SkySat imagery** (50 cm GSD) - marginal for potholes

The weekly basemap provides citywide context but should be supplemented with targeted high-resolution tasking.

## Configuration

### Detection Parameters

Adjust in Streamlit sidebar or when creating `PotholeDetector`:

- **tile_size**: Size of processing tiles (default: 512)
  - Larger = fewer tiles, more memory
  - Smaller = more tiles, less memory

- **overlap**: Overlap between tiles (default: 64)
  - Prevents edge artifacts
  - Larger overlap = better blending, slower processing

- **threshold**: Probability threshold for detection (default: 0.5)
  - Lower = more detections (higher recall, more false positives)
  - Higher = fewer detections (higher precision, lower recall)

- **min_area**: Minimum area filter in CRS units² (default: 1.0)
  - Filters out tiny detections
  - Adjust based on CRS (projected vs geographic)

### GeoJSON Output Properties

Each detected pothole feature includes:

```json
{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "properties": {
    "confidence": 0.87,           // Mean probability
    "area_crs_units": 12.5,       // Area in source CRS
    "area_m2": 11.8,              // Area in square meters
    "source_file": "la_weekly_latest.vrt"
  }
}
```

## Troubleshooting

### GDAL Issues

```bash
# If rasterio fails to install
export GDAL_VERSION=$(gdal-config --version)
pip install gdal==$GDAL_VERSION

# Or use conda
conda install -c conda-forge gdal rasterio
```

### Planet API Authentication

```bash
# Test API key
planet auth init --email your@email.com

# Or use key directly
export PL_API_KEY="your_key_here"
python scripts/planet_list_series.py
```

### Memory Issues

If processing large imagery:

- Reduce `tile_size` (e.g., 256 or 384)
- Process smaller AOIs
- Use VRT files instead of loading full rasters

### Model Not Found Warning

This is expected if you don't have trained weights. The system will use random initialization for testing the pipeline. Results will not be meaningful but you can verify the full workflow.

## Architecture Notes

### Why U-Net?

- Proven architecture for semantic segmentation
- Efficient for small objects
- Skip connections preserve spatial detail
- Widely supported and easy to train

### Tiling Strategy

Large satellite imagery is processed in overlapping tiles:

1. Image divided into 512x512 tiles with 64px overlap
2. Each tile processed independently
3. Predictions blended using weighted averaging
4. Prevents edge artifacts and handles arbitrary image sizes

### Vectorization

Binary masks converted to polygons:

1. Morphological cleanup (opening/closing) removes noise
2. Rasterio's `shapes()` extracts connected components
3. Polygons filtered by area threshold
4. Geometries simplified to reduce vertex count
5. Georeferencing preserved throughout

## Performance Considerations

### Inference Speed

- **CPU**: ~2-5 tiles/second (depends on hardware)
- **GPU**: ~20-50 tiles/second (NVIDIA GPU recommended)

For a typical LA citywide basemap (~50-100 quads):
- Expect 30-60 minutes on CPU
- Expect 5-15 minutes on GPU

### Storage

- Weekly basemap: ~5-20 GB per week (depends on cloud cover, area)
- VRT files: Minimal (<1 MB)
- Detection outputs: <10 MB per week

## Limitations

1. **Resolution**: PlanetScope (~3-4m) too coarse for small potholes
2. **Model**: Requires training on labeled data
3. **Weather**: Cloud cover may prevent weekly captures
4. **Coverage**: Basemaps may not cover entire city
5. **Accuracy**: Depends on training data quality

## Roadmap

- [ ] Implement S3 delivery mode for Planet Orders API
- [ ] Add model training code and example dataset
- [ ] Support change detection (compare weekly results)
- [ ] Integration with city work order systems
- [ ] Mobile app for field verification
- [ ] Temporal tracking of pothole repairs

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[Specify your license here]

## Acknowledgments

- Planet Labs for satellite imagery access
- Los Angeles Open Data Portal for city boundary data
- U-Net architecture from Ronneberger et al.

## Support

For issues and questions:
- Open an issue on GitHub
- Check documentation in `data/README_DATA.md`
- Review Planet API docs: https://developers.planet.com/

## Citation

If you use this code in research:

```bibtex
@software{la_pothole_detection,
  title={LA Pothole Detection System},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/pothole-app}
}
```
