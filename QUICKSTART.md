# Quick Start - Deploy in 5 Minutes

## Option 1: Deploy to Streamlit Cloud (Recommended)

### Step 1: Create Main Branch (One-time setup)

Since the code is on a feature branch, you'll want to merge it to `main` first:

1. **Go to GitHub**: https://github.com/jwsqueaker/git-down

2. **Create Pull Request**:
   - Click "Pull requests" → "New pull request"
   - Base: `main` (create if doesn't exist)
   - Compare: `claude/build-from-conversation-vjhRB`
   - Click "Create pull request"
   - Review changes
   - Click "Merge pull request"

   Or use this direct link:
   https://github.com/jwsqueaker/git-down/pull/new/claude/build-from-conversation-vjhRB

3. **Set main as default branch**:
   - Go to Settings → Branches
   - Set `main` as default branch

### Step 2: Deploy to Streamlit Cloud

1. **Sign up for Streamlit Cloud** (free)
   - Go to https://share.streamlit.io/
   - Click "Sign in with GitHub"
   - Authorize Streamlit Cloud to access your repositories

2. **Create New App**
   - Click "New app" button
   - Repository: `jwsqueaker/git-down`
   - Branch: `main` (or `claude/build-from-conversation-vjhRB`)
   - Main file path: `streamlit_app.py`
   - Click "Deploy!"

3. **Wait for Deployment** (2-5 minutes)
   - Streamlit will install dependencies from `requirements.txt` and `packages.txt`
   - Watch the build logs for any errors
   - The app URL will be: `https://git-down-<random>.streamlit.app/`

4. **Configure Secrets** (Optional - only needed for Planet API)
   - Click "⚙️" (Settings) → "Secrets"
   - Add your Planet credentials:

   ```toml
   PL_API_KEY = "your_planet_api_key_here"
   PL_SERIES_NAME = "PlanetScope Weekly Basemap"
   ```

   - Click "Save"
   - App will automatically restart

5. **Done!** 🎉
   - Your app is now live at the Streamlit Cloud URL
   - Share the URL with others
   - Upload GeoTIFF files to test pothole detection

## Option 2: Run Locally (For Development)

### Quick Local Setup

```bash
# Clone the repository
git clone https://github.com/jwsqueaker/git-down.git
cd git-down

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y gdal-bin libgdal-dev

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

Access at: http://localhost:8501

## What You Can Do Without Planet API

Even without Planet API credentials, you can:

✅ Upload your own GeoTIFF files
✅ Run pothole detection (with random weights for testing)
✅ Visualize results on interactive map
✅ Export detections as GeoJSON
✅ Test the full pipeline

## What You Need Planet API For

With Planet API credentials:

🛰️ Fetch weekly satellite imagery for Los Angeles
🛰️ Submit SkySat tasking for hotspots
🛰️ Automate weekly monitoring

## Testing the App

### Sample GeoTIFF Files

You can test with:
- Any GeoTIFF file from satellite imagery
- Aerial photography in GeoTIFF format
- Drone imagery (best results)
- Sample files from:
  - USGS Earth Explorer
  - Copernicus Open Access Hub
  - Your own drone flights

### Expected Behavior

**Without trained weights:**
- Detection will run but results will be random (model not trained)
- This is expected! It's for testing the pipeline
- You can see the full workflow: upload → detect → visualize → export

**With trained weights:**
- Place `unet_potholes.pth` in `models/` directory
- Detection will produce meaningful results
- Adjust threshold and min_area for best results

## Troubleshooting

**App won't deploy:**
- Check build logs for errors
- Ensure `requirements.txt` and `packages.txt` are in root directory
- Try deploying again (sometimes temporary issues)

**GDAL import errors:**
- Make sure `packages.txt` contains GDAL dependencies
- Wait for full build completion
- Check Python version is 3.9+

**Out of memory:**
- Reduce tile_size to 256 or 384
- Use smaller GeoTIFF files
- Consider upgrading to Streamlit Cloud paid tier

**Planet API not working:**
- Verify PL_API_KEY is set correctly in Secrets
- Check PL_SERIES_NAME matches your series exactly
- Ensure Planet subscription is active

## Next Steps

After deployment:

1. **Test with sample data** - Upload a small GeoTIFF
2. **Adjust parameters** - Tune threshold and tile size
3. **Add model weights** - Train or obtain pothole detection weights
4. **Configure Planet API** - For automated imagery fetching
5. **Share your app** - Send the URL to stakeholders

## Getting Help

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions
- Read [README.md](README.md) for full documentation
- Check Streamlit docs: https://docs.streamlit.io/
- Open an issue on GitHub for problems

## Pro Tips

💡 **Pin your app** - Star it in Streamlit Cloud to prevent sleep
💡 **Custom domain** - Available on paid Streamlit plans
💡 **Monitor usage** - Check analytics in Streamlit Cloud dashboard
💡 **Version control** - App auto-updates when you push to GitHub
💡 **Share privately** - Configure access settings in Streamlit Cloud

---

**Ready to deploy? Go to https://share.streamlit.io/ and get started!** 🚀
