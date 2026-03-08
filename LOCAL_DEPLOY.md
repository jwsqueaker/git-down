# Local Deployment Guide

Run the LA Pothole Detection app on your own computer in 3 easy steps.

## 🚀 Quick Start (Recommended)

### Option 1: One-Command Launch (Any Platform)

```bash
python3 launch.py
```

That's it! The script will:
- ✅ Check for dependencies
- ✅ Install missing packages
- ✅ Create configuration files
- ✅ Launch the Streamlit app
- ✅ Open in your browser automatically

### Option 2: Platform-Specific Scripts

**macOS / Linux:**
```bash
./run_local.sh
```

**Windows:**
```cmd
run_local.bat
```

## 📋 Prerequisites

### Required Software

1. **Python 3.9 or later**
   - Check: `python3 --version`
   - Download: https://www.python.org/downloads/

2. **GDAL** (for geospatial processing)

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install gdal-bin libgdal-dev python3-gdal
   ```

   **macOS:**
   ```bash
   brew install gdal
   ```

   **Windows:**
   - Download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
   - Install matching your Python version
   - Or use: `pip install GDAL-3.x.x-cpXX-win_amd64.whl`

## 📥 Step-by-Step Installation

### 1. Get the Code

**If using GitHub (private repo):**
```bash
git clone https://github.com/jwsqueaker/git-down.git
cd git-down
```

**If you have the code locally already:**
```bash
cd /path/to/git-down
```

### 2. Set Up Python Environment

**Create virtual environment:**
```bash
python3 -m venv venv
```

**Activate it:**

- **macOS/Linux:** `source venv/bin/activate`
- **Windows:** `venv\Scripts\activate`

**Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the App

```bash
streamlit run streamlit_app.py
```

The app will open at: **http://localhost:8501**

## ⚙️ Configuration (Optional)

### For Planet API Access

Create `.env` file in the project root:

```env
PL_API_KEY=your_planet_api_key_here
PL_SERIES_NAME=PlanetScope Weekly Basemap
```

Or use `.streamlit/secrets.toml`:

```toml
PL_API_KEY = "your_planet_api_key_here"
PL_SERIES_NAME = "PlanetScope Weekly Basemap"
```

### For AWS S3 Delivery (Optional)

Add to `.env`:
```env
AWS_BUCKET=your-bucket-name
AWS_PREFIX=pothole-data/
AWS_REGION=us-west-2
```

## 🧪 Test Without Planet API

You can test the full pipeline without Planet API:

1. **Upload a sample GeoTIFF**
   - Any satellite or drone imagery
   - Must be in GeoTIFF format (.tif)

2. **Adjust detection parameters**
   - Tile Size: 512 (default)
   - Threshold: 0.5 (default)
   - Min Area: 1.0

3. **Run detection**
   - Results will show (random without trained model)
   - Full pipeline works: upload → detect → visualize → export

4. **Download results**
   - Export as GeoJSON
   - View on interactive map

## 🎯 Using the App

### Upload Tab

1. **Select input method:**
   - Upload GeoTIFF file
   - Or use latest Planet basemap (if configured)

2. **Preview the imagery**
   - Thumbnail preview loads automatically

3. **Click "Run Detection"**
   - Processing takes 30 seconds to 5 minutes
   - Depends on image size and hardware

### Results Tab

1. **View statistics:**
   - Total potholes detected
   - Total area (m²)
   - Average confidence

2. **Interactive map:**
   - Zoom and pan
   - Click polygons for details
   - Red = detected potholes

3. **Download results:**
   - Click "Download GeoJSON"
   - Import into QGIS, ArcGIS, etc.

## 🔧 Troubleshooting

### "Module not found" errors

**Solution:**
```bash
pip install -r requirements.txt
```

Make sure virtual environment is activated!

### GDAL import errors

**Solution:**

1. Install GDAL system package first (see Prerequisites)
2. Then install Python GDAL:
   ```bash
   pip install gdal==$(gdal-config --version)
   ```

### "streamlit: command not found"

**Solution:**
```bash
# Make sure you're in virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Then install streamlit
pip install streamlit
```

### Port 8501 already in use

**Solution:**
```bash
# Use a different port
streamlit run streamlit_app.py --server.port 8502
```

### Out of memory errors

**Solution:**

Reduce parameters in sidebar:
- Tile Size: 256 (from 512)
- Use smaller input images
- Close other applications

### App won't start

**Check Python version:**
```bash
python3 --version  # Should be 3.9 or later
```

**Check dependencies:**
```bash
pip list | grep streamlit
pip list | grep rasterio
```

**Reinstall everything:**
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🌐 Access From Other Devices

By default, Streamlit only accepts connections from localhost.

### Allow Network Access

```bash
streamlit run streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port 8501
```

Then access from other devices at:
```
http://YOUR_IP:8501
```

Find your IP:
- **macOS/Linux:** `ifconfig | grep inet`
- **Windows:** `ipconfig`

⚠️ **Security Warning:** Only do this on trusted networks!

## 🐳 Docker Deployment (Advanced)

### Build Docker Image

```bash
docker build -t pothole-detection .
```

### Run Container

```bash
docker run -p 8501:8501 \
  -e PL_API_KEY="your_key" \
  -e PL_SERIES_NAME="your_series" \
  pothole-detection
```

Access at: http://localhost:8501

## 📊 Performance Tips

### For Faster Processing

1. **Use GPU if available**
   - Install PyTorch with CUDA support
   - Speeds up inference 5-10x

2. **Reduce tile size**
   - Smaller tiles = less memory
   - But more tiles = more overhead
   - 512 is optimal for most cases

3. **Use VRT files**
   - For large multi-file imagery
   - Avoids loading entire dataset into memory

4. **Process smaller AOIs**
   - Clip to specific neighborhoods
   - Process in batches

## 🔒 Running Privately

This local deployment is completely private:
- ✅ No data leaves your computer
- ✅ No external services called (except Planet API if configured)
- ✅ Results stay local
- ✅ Full control over your data

## 📝 Next Steps

After successful deployment:

1. **Add model weights** (if you have them)
   - Place in `models/unet_potholes.pth`
   - Restart the app

2. **Configure Planet API** (optional)
   - Add credentials to `.env`
   - Test with "Fetch Latest Basemap" button

3. **Process your imagery**
   - Upload GeoTIFFs
   - Adjust parameters
   - Export results

4. **Integrate with GIS**
   - Import GeoJSON into QGIS
   - Overlay on base maps
   - Analysis and reporting

## 💡 Tips

- **Save your settings:** Streamlit remembers your last parameters
- **Batch processing:** Process multiple files by re-uploading
- **Export often:** Download GeoJSON after each run
- **Monitor memory:** Watch task manager with large files
- **Keep logs:** Check terminal for detailed processing info

## 🆘 Getting Help

If issues persist:

1. Check the error message in terminal
2. Review Streamlit logs
3. Verify all prerequisites installed
4. Try the minimal example (see below)

### Minimal Test

```python
import streamlit as st
st.write("Hello! Streamlit works!")
```

Save as `test.py` and run:
```bash
streamlit run test.py
```

If this works, the issue is with dependencies, not Streamlit.

---

**Ready to detect potholes? Run `python3 launch.py` and get started!** 🚀
