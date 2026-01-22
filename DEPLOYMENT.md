# Deployment Guide

This guide covers deploying the LA Pothole Detection app to Streamlit Cloud.

## Streamlit Cloud Deployment

### Prerequisites

1. GitHub account
2. Streamlit Cloud account (free at https://streamlit.io/cloud)
3. Planet API key

### Step 1: Prepare Repository

The repository is already configured with:
- `.streamlit/config.toml` - Streamlit configuration
- `packages.txt` - System dependencies (GDAL)
- `requirements.txt` - Python dependencies
- `.gitignore` - Excludes secrets and data files

### Step 2: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit https://share.streamlit.io/
   - Sign in with GitHub

2. **Create New App**
   - Click "New app"
   - Select repository: `jwsqueaker/git-down`
   - Select branch: `main` (or your feature branch)
   - Main file path: `streamlit_app.py`
   - Click "Deploy"

3. **Configure Secrets**
   - After deployment starts, click "⚙️ Settings" → "Secrets"
   - Add your credentials in TOML format:

```toml
PL_API_KEY = "your_planet_api_key_here"
PL_SERIES_NAME = "PlanetScope Weekly Basemap"

# Optional: AWS credentials
AWS_BUCKET = "your-bucket-name"
AWS_PREFIX = "pothole-data/"
AWS_REGION = "us-west-2"
```

4. **Save and Reboot**
   - Click "Save"
   - The app will automatically reboot with the new secrets

### Step 3: Test Deployment

1. Wait for the app to finish deploying (2-5 minutes)
2. Access your app at: `https://<app-name>.streamlit.app/`
3. Test the interface (upload functionality will work, Planet API requires valid credentials)

### Important Notes

#### File Uploads Only Mode

The deployed app supports:
- ✅ Upload GeoTIFF files for detection
- ✅ Interactive map visualization
- ✅ GeoJSON export
- ❌ Planet API fetching (requires paid Planet subscription and valid API key)

#### Planet API Integration

To enable Planet basemap fetching:
1. Obtain a Planet API key (requires subscription)
2. Add credentials to Streamlit Cloud secrets
3. Configure PL_SERIES_NAME to match your available series

#### Data Persistence

⚠️ **Important:** Streamlit Cloud apps are stateless. Downloaded data will be lost when:
- App is redeployed
- App goes to sleep (after inactivity)
- Container is restarted

For production use, consider:
- Using S3 or cloud storage for persistence
- Running on a dedicated server
- Implementing a database for results

#### Resource Limits

Streamlit Cloud free tier:
- 1 GB RAM
- 1 CPU core
- Limited compute hours

For large imagery:
- Reduce tile_size in settings
- Process smaller areas
- Use lower resolution imagery
- Consider paid Streamlit Cloud plans

### Step 4: Custom Domain (Optional)

Streamlit Cloud supports custom domains on paid plans:
1. Upgrade to paid plan
2. Settings → Custom domain
3. Follow DNS configuration instructions

## Alternative Deployment Options

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Install GDAL
RUN apt-get update && \
    apt-get install -y gdal-bin libgdal-dev python3-gdal && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py"]
```

Build and run:
```bash
docker build -t pothole-app .
docker run -p 8501:8501 \
  -e PL_API_KEY=$PL_API_KEY \
  -e PL_SERIES_NAME="$PL_SERIES_NAME" \
  pothole-app
```

### AWS EC2 / Google Cloud / Azure

1. Launch a VM instance
2. Install dependencies:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip gdal-bin libgdal-dev
```

3. Clone repository and install:
```bash
git clone https://github.com/jwsqueaker/git-down.git
cd git-down
pip3 install -r requirements.txt
```

4. Set environment variables:
```bash
export PL_API_KEY="your_key"
export PL_SERIES_NAME="your_series"
```

5. Run with nohup or systemd:
```bash
nohup streamlit run streamlit_app.py --server.port 8501 &
```

### Heroku Deployment

Create `Procfile`:
```
web: streamlit run streamlit_app.py --server.port=$PORT
```

Create `Aptfile`:
```
gdal-bin
libgdal-dev
```

Deploy:
```bash
heroku create your-app-name
heroku buildpacks:add --index 1 heroku-community/apt
heroku buildpacks:add --index 2 heroku/python
git push heroku main
heroku config:set PL_API_KEY=your_key
heroku config:set PL_SERIES_NAME=your_series
```

## Monitoring and Maintenance

### Streamlit Cloud Dashboard

- View logs in real-time
- Monitor resource usage
- Check deployment status
- Manage secrets

### Troubleshooting

**GDAL Import Errors:**
- Ensure `packages.txt` is in root directory
- Check Streamlit Cloud build logs

**Memory Errors:**
- Reduce tile_size (try 256 or 384)
- Process smaller imagery
- Upgrade to paid tier for more RAM

**Planet API Errors:**
- Verify API key is correct in secrets
- Check series name matches exactly
- Ensure Planet subscription is active

**Slow Performance:**
- Use GPU-enabled hosting for faster inference
- Reduce image size before upload
- Consider batch processing offline

## Security Best Practices

1. **Never commit secrets** - Use `.gitignore` to exclude `.streamlit/secrets.toml`
2. **Use Streamlit secrets** - Configure in cloud settings, not in code
3. **Validate user uploads** - The app validates GeoTIFF format
4. **Limit file sizes** - Configure max upload size in settings
5. **Monitor usage** - Check Planet API usage to avoid overages

## Support

- Streamlit Cloud Docs: https://docs.streamlit.io/streamlit-community-cloud
- Planet API Docs: https://developers.planet.com/
- Issues: Open on GitHub repository

## Next Steps

After deployment:
1. Test with sample GeoTIFF files
2. Configure Planet API credentials if available
3. Customize detection parameters
4. Share app URL with stakeholders
5. Monitor usage and performance
