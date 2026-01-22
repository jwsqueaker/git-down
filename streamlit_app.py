"""
Streamlit app for pothole detection visualization.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import streamlit as st
import numpy as np
import rasterio
from rasterio.plot import reshape_as_image
import leafmap.foliumap as leafmap
import geopandas as gpd
from PIL import Image

# Page config must be first Streamlit command
st.set_page_config(
    page_title="LA Pothole Detection",
    page_icon="🛣️",
    layout="wide",
)

# Add pothole module to path and import
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pothole import PotholeDetector
except ImportError as e:
    st.error(f"❌ Error importing pothole module: {e}")
    st.error("Please ensure all dependencies are installed from requirements.txt")
    st.stop()

# Initialize session state
if "geojson" not in st.session_state:
    st.session_state.geojson = None
if "latest_tif" not in st.session_state:
    st.session_state.latest_tif = None


def load_and_display_image(tif_path: str, max_size: int = 800):
    """Load and display a preview of the GeoTIFF."""
    try:
        with rasterio.open(tif_path) as src:
            # Read at lower resolution for preview
            out_shape = (
                src.count,
                min(src.height, max_size),
                min(src.width, max_size),
            )

            data = src.read(out_shape=out_shape)

            # Convert to RGB for display
            if data.shape[0] >= 3:
                rgb = data[:3, :, :]
                rgb = reshape_as_image(rgb)

                # Normalize to 0-255
                if rgb.max() > 255:
                    rgb = (rgb / rgb.max() * 255).astype(np.uint8)

                return Image.fromarray(rgb)

    except Exception as e:
        st.error(f"Error loading image preview: {e}")
        return None


def run_detection(
    tif_path: str,
    model_path: str,
    tile_size: int,
    overlap: int,
    threshold: float,
    min_area: float,
):
    """Run pothole detection on a GeoTIFF."""
    try:
        # Create detector
        detector = PotholeDetector(
            model_path=model_path if model_path else None,
            tile_size=tile_size,
            overlap=overlap,
            threshold=threshold,
            min_area=min_area,
        )

        # Process
        with st.spinner("Processing imagery..."):
            progress_bar = st.progress(0)
            progress_bar.progress(10)

            # Get metadata
            with rasterio.open(tif_path) as src:
                metadata = {
                    "source_file": os.path.basename(tif_path),
                    "crs": str(src.crs),
                }

            progress_bar.progress(20)

            # Run detection
            geojson = detector.process_geotiff(
                tif_path,
                metadata=metadata,
            )

            progress_bar.progress(100)

        return geojson

    except Exception as e:
        st.error(f"Error during detection: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None


def display_results_on_map(geojson: dict):
    """Display detection results on an interactive map."""
    if not geojson or not geojson.get("features"):
        st.warning("No potholes detected")
        return

    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson["features"])

    # Set CRS if available
    if "crs" in geojson and geojson["crs"]:
        crs_name = geojson["crs"].get("properties", {}).get("name", "")
        if crs_name:
            try:
                gdf.set_crs(crs_name, inplace=True)
            except:
                pass

    # Ensure WGS84 for display
    if gdf.crs and gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    # Create map
    m = leafmap.Map()

    # Add polygons
    style = {
        "color": "red",
        "fillColor": "red",
        "fillOpacity": 0.3,
        "weight": 2,
    }

    m.add_gdf(gdf, layer_name="Potholes", style=style)

    # Zoom to layer
    if len(gdf) > 0:
        bounds = gdf.total_bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Display map
    m.to_streamlit(height=600)


def fetch_latest_planet_basemap():
    """Run the Planet basemap fetcher script."""
    import subprocess

    # Try to get credentials from Streamlit secrets first, then environment variables
    try:
        api_key = st.secrets["PL_API_KEY"]
    except (KeyError, FileNotFoundError):
        api_key = os.getenv("PL_API_KEY")

    try:
        series_name = st.secrets["PL_SERIES_NAME"]
    except (KeyError, FileNotFoundError):
        series_name = os.getenv("PL_SERIES_NAME")

    if not api_key:
        st.error("PL_API_KEY not set. Configure in Streamlit Cloud secrets or set as environment variable")
        return False

    if not series_name:
        st.error("PL_SERIES_NAME not set. Configure in Streamlit Cloud secrets or set as environment variable")
        return False

    script_path = Path(__file__).parent / "scripts" / "planet_weekly_basemap_la.py"

    if not script_path.exists():
        st.error(f"Script not found: {script_path}")
        return False

    try:
        with st.spinner("Fetching latest Planet basemap..."):
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                st.success("Planet basemap fetched successfully!")
                st.text(result.stdout)

                # Check for VRT file
                vrt_path = Path("data/weekly_la_basemap") / "la_weekly_latest.vrt"
                if vrt_path.exists():
                    st.session_state.latest_tif = str(vrt_path)
                    return True
                else:
                    st.warning("VRT file not found, but script completed")
                    return False
            else:
                st.error(f"Script failed with code {result.returncode}")
                st.text(result.stderr)
                return False

    except subprocess.TimeoutExpired:
        st.error("Script timed out after 10 minutes")
        return False
    except Exception as e:
        st.error(f"Error running script: {e}")
        return False


# Main UI
st.title("🛣️ LA Pothole Detection")
st.markdown("Detect potholes in satellite imagery using deep learning")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    # Planet basemap section
    st.subheader("Planet Basemap")

    if st.button("Fetch Latest Planet Basemap"):
        if fetch_latest_planet_basemap():
            st.rerun()

    if st.session_state.latest_tif:
        st.info(f"Latest: {Path(st.session_state.latest_tif).parent.name}")

    st.markdown("---")

    # Model settings
    st.subheader("Model Settings")

    model_path = st.text_input(
        "Model Weights Path",
        value="models/unet_potholes.pth",
        help="Path to pretrained U-Net weights (optional)",
    )

    # Check if model exists
    if model_path and not os.path.exists(model_path):
        st.warning("⚠️ Model file not found. Using random weights.")

    st.markdown("---")

    # Inference settings
    st.subheader("Inference Settings")

    tile_size = st.slider("Tile Size", 128, 1024, 512, 128)
    overlap = st.slider("Tile Overlap", 0, 256, 64, 32)
    threshold = st.slider("Detection Threshold", 0.0, 1.0, 0.5, 0.05)
    min_area = st.number_input("Min Area (CRS units²)", 0.1, 100.0, 1.0, 0.1)

    st.markdown("---")

    # About
    st.subheader("ℹ️ About")
    st.markdown("""
    This tool detects potholes in satellite imagery using a U-Net segmentation model.

    **Note:** PlanetScope resolution (~3-4m) may not be sufficient for small potholes.
    Consider using higher resolution imagery for better results.
    """)

# Main area
tab1, tab2 = st.tabs(["📤 Upload & Detect", "📊 Results"])

with tab1:
    st.header("Input Imagery")

    # Input method selection
    input_method = st.radio(
        "Select input method:",
        ["Upload GeoTIFF", "Use Latest Planet Basemap"],
    )

    selected_file = None

    if input_method == "Upload GeoTIFF":
        uploaded_file = st.file_uploader(
            "Upload a GeoTIFF file",
            type=["tif", "tiff"],
        )

        if uploaded_file:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as tmp:
                tmp.write(uploaded_file.read())
                selected_file = tmp.name

            st.success(f"Uploaded: {uploaded_file.name}")

    else:  # Use latest Planet basemap
        if st.session_state.latest_tif and os.path.exists(st.session_state.latest_tif):
            selected_file = st.session_state.latest_tif
            st.success(f"Using: {selected_file}")
        else:
            st.warning("No Planet basemap available. Fetch one from the sidebar.")

    # Show preview
    if selected_file:
        st.subheader("Image Preview")
        preview = load_and_display_image(selected_file)
        if preview:
            st.image(preview, caption="Input Image (preview)", use_container_width=True)

    # Run detection button
    if st.button("🔍 Run Detection", type="primary", disabled=selected_file is None):
        if selected_file:
            geojson = run_detection(
                selected_file,
                model_path,
                tile_size,
                overlap,
                threshold,
                min_area,
            )

            if geojson:
                st.session_state.geojson = geojson
                st.success(f"✅ Detection complete! Found {len(geojson['features'])} potholes")
                st.balloons()

with tab2:
    st.header("Detection Results")

    if st.session_state.geojson:
        geojson = st.session_state.geojson

        # Stats
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Potholes", len(geojson["features"]))

        with col2:
            if geojson["features"]:
                areas = [f["properties"].get("area_m2", 0) for f in geojson["features"]]
                total_area = sum(areas)
                st.metric("Total Area (m²)", f"{total_area:.1f}")
            else:
                st.metric("Total Area (m²)", "0")

        with col3:
            if geojson["features"]:
                confidences = [f["properties"].get("confidence", 0) for f in geojson["features"]]
                avg_conf = np.mean([c for c in confidences if c > 0])
                st.metric("Avg Confidence", f"{avg_conf:.2f}")
            else:
                st.metric("Avg Confidence", "N/A")

        # Map
        st.subheader("Map View")
        display_results_on_map(geojson)

        # Download button
        st.subheader("Export Results")

        geojson_str = json.dumps(geojson, indent=2)

        st.download_button(
            label="📥 Download GeoJSON",
            data=geojson_str,
            file_name="potholes_detected.geojson",
            mime="application/geo+json",
        )

        # Show data table
        if st.checkbox("Show Data Table"):
            gdf = gpd.GeoDataFrame.from_features(geojson["features"])
            st.dataframe(gdf.drop(columns=["geometry"]))

    else:
        st.info("👈 Run detection in the 'Upload & Detect' tab to see results here")
