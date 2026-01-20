# Deployment Guide

This guide covers deploying the Portfolio Dashboard to various platforms.

## Deployment Options

1. **Streamlit Cloud** (Recommended - Free & Easy)
2. **Docker** (Containerized deployment)
3. **Heroku** (Cloud platform)
4. **AWS/GCP/Azure** (Enterprise solutions)
5. **Local Server** (Self-hosted)

---

## 1. Streamlit Cloud (Recommended)

**Best for:** Personal use, small teams, quick deployment

### Prerequisites
- GitHub account
- Streamlit account (free at https://streamlit.io/cloud)

### Steps

1. **Push your code to GitHub** (already done!)

2. **Sign up for Streamlit Cloud**:
   - Go to https://streamlit.io/cloud
   - Sign in with GitHub

3. **Deploy your app**:
   - Click "New app"
   - Select your repository: `jwsqueaker/git-down`
   - Branch: `claude/portfolio-dashboard-macro-0F39Q`
   - Main file: `app.py`
   - Click "Deploy"

4. **Configure secrets**:
   - In Streamlit Cloud dashboard, go to app settings
   - Click "Secrets"
   - Add your FRED API key:
     ```toml
     FRED_API_KEY = "your_api_key_here"
     ```

5. **Access your app**:
   - You'll get a URL like: `https://your-app.streamlit.app`
   - Share this with anyone!

### Limitations
- Free tier: Limited resources
- Apps sleep after inactivity (wake on visit)
- Public by default (can make private with paid plan)

---

## 2. Docker Deployment

**Best for:** Consistent environments, self-hosting, portability

### Dockerfile

Already created! See `Dockerfile` in the repository.

### Build and Run

```bash
# Build the image
docker build -t portfolio-dashboard .

# Run the container
docker run -p 8501:8501 \
  -e FRED_API_KEY=your_key_here \
  portfolio-dashboard
```

Access at: `http://localhost:8501`

### Docker Compose

For easier management:

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down

# View logs
docker-compose logs -f
```

### Persistent Data

To keep your portfolio data between restarts:

```bash
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -e FRED_API_KEY=your_key_here \
  portfolio-dashboard
```

---

## 3. Heroku Deployment

**Best for:** Simple cloud deployment with add-ons

### Prerequisites
- Heroku account (free tier available)
- Heroku CLI installed

### Files Needed

Already created:
- `Procfile` - Tells Heroku how to run the app
- `setup.sh` - Setup script for Streamlit
- `requirements.txt` - Python dependencies

### Deployment Steps

```bash
# Login to Heroku
heroku login

# Create a new app
heroku create portfolio-dashboard-app

# Set environment variables
heroku config:set FRED_API_KEY=your_key_here

# Deploy
git push heroku claude/portfolio-dashboard-macro-0F39Q:main

# Open the app
heroku open
```

### Custom Domain

```bash
heroku domains:add www.yourportfolio.com
```

Then configure DNS with your domain provider.

---

## 4. AWS Deployment

### Option A: AWS EC2

**Best for:** Full control, scalability

```bash
# Launch EC2 instance (Ubuntu)
# SSH into instance

# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv

# Clone repository
git clone https://github.com/jwsqueaker/git-down.git
cd git-down
git checkout claude/portfolio-dashboard-macro-0F39Q

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
echo "FRED_API_KEY=your_key" > .env

# Run with nohup
nohup streamlit run app.py --server.port 8501 &

# Or use systemd for production (see systemd section below)
```

Configure security group to allow port 8501.

### Option B: AWS Lightsail

Simpler than EC2:
1. Create Lightsail instance
2. Use the same EC2 setup steps above
3. Map static IP
4. Open firewall port 8501

### Option C: AWS ECS (Container)

Deploy the Docker image to ECS:
1. Push image to ECR
2. Create ECS task definition
3. Create ECS service
4. Use Application Load Balancer

---

## 5. Google Cloud Platform (GCP)

### Cloud Run (Recommended)

**Best for:** Serverless, auto-scaling, pay-per-use

```bash
# Install gcloud CLI
# Login: gcloud auth login

# Build and deploy
gcloud run deploy portfolio-dashboard \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FRED_API_KEY=your_key

# Get URL
gcloud run services describe portfolio-dashboard --region us-central1
```

### Compute Engine (VM)

Similar to AWS EC2 - use the same setup steps.

---

## 6. Azure Deployment

### Azure App Service

```bash
# Install Azure CLI
# Login: az login

# Create resource group
az group create --name portfolio-rg --location eastus

# Create app service plan
az appservice plan create \
  --name portfolio-plan \
  --resource-group portfolio-rg \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --resource-group portfolio-rg \
  --plan portfolio-plan \
  --name portfolio-dashboard-app \
  --runtime "PYTHON|3.10"

# Set environment variables
az webapp config appsettings set \
  --resource-group portfolio-rg \
  --name portfolio-dashboard-app \
  --settings FRED_API_KEY=your_key

# Deploy
az webapp up \
  --resource-group portfolio-rg \
  --name portfolio-dashboard-app
```

---

## 7. Local Server (Production Setup)

**Best for:** Internal use, on-premises hosting

### Using systemd (Linux)

1. **Create systemd service file**:

```bash
sudo nano /etc/systemd/system/portfolio-dashboard.service
```

Add (see `deployment/portfolio-dashboard.service`).

2. **Enable and start**:

```bash
sudo systemctl daemon-reload
sudo systemctl enable portfolio-dashboard
sudo systemctl start portfolio-dashboard
sudo systemctl status portfolio-dashboard
```

### Using Nginx Reverse Proxy

```bash
# Install Nginx
sudo apt install nginx

# Configure (see deployment/nginx.conf)
sudo nano /etc/nginx/sites-available/portfolio

# Enable site
sudo ln -s /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d portfolio.yourdomain.com
```

---

## Environment Variables

All deployments need these environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `FRED_API_KEY` | No* | FRED API key for macro indicators |
| `DATABASE_URL` | No | SQLite URL (defaults to local file) |
| `RISK_FREE_RATE` | No | Annual risk-free rate (defaults to 0.045) |

*FRED_API_KEY is technically optional but highly recommended for full functionality.

---

## Security Considerations

### Production Checklist

- [ ] Use HTTPS (SSL/TLS certificates)
- [ ] Set strong authentication if needed
- [ ] Secure environment variables (don't commit .env)
- [ ] Regular security updates
- [ ] Backup database regularly
- [ ] Monitor for unusual activity
- [ ] Rate limit API requests
- [ ] Use firewall rules

### Authentication

Streamlit doesn't have built-in auth. Options:

1. **Streamlit Cloud** - Has authentication in paid plans
2. **Nginx Basic Auth** - Simple password protection
3. **OAuth** - Use streamlit-authenticator library
4. **VPN** - Restrict access to VPN users

---

## Monitoring & Maintenance

### Health Checks

Add to `app.py`:
```python
# Health check endpoint
if st.experimental_get_query_params().get('health'):
    st.write("OK")
    st.stop()
```

### Logging

```bash
# View Streamlit logs
tail -f ~/.streamlit/logs/*.log

# Docker logs
docker logs -f container_name

# Systemd logs
sudo journalctl -u portfolio-dashboard -f
```

### Backups

Backup the SQLite database:
```bash
# Local backup
cp portfolio.db portfolio.db.backup

# Automated daily backups
0 2 * * * cp /path/to/portfolio.db /backups/portfolio-$(date +\%Y\%m\%d).db
```

---

## Performance Optimization

### Caching

Already implemented in the code with `@st.cache_data`.

### Database Optimization

For large portfolios:
```bash
# Vacuum database
sqlite3 portfolio.db "VACUUM;"

# Analyze for optimization
sqlite3 portfolio.db "ANALYZE;"
```

### Resource Limits

**Memory:**
- Minimum: 512 MB
- Recommended: 1-2 GB
- Heavy use: 4 GB+

**CPU:**
- Minimum: 1 core
- Recommended: 2 cores

---

## Scaling

### Horizontal Scaling

For multiple users:
1. Use managed database (PostgreSQL instead of SQLite)
2. Deploy multiple app instances
3. Use load balancer
4. Implement session management

### Vertical Scaling

For single-user performance:
1. Increase RAM
2. Use SSD storage
3. Add CPU cores
4. Optimize queries

---

## Troubleshooting Deployment

### App won't start

Check:
- Python version (needs 3.8+)
- All dependencies installed
- Environment variables set
- Port not already in use
- Sufficient memory/disk

### Slow performance

Solutions:
- Enable caching
- Reduce data range
- Use CDN for static files
- Increase server resources
- Optimize database queries

### Data not persisting

Ensure:
- Database directory is writable
- Using persistent volume (Docker)
- Database file isn't in /tmp
- Regular backups enabled

---

## Cost Estimates

### Free Options
- **Streamlit Cloud**: Free tier available
- **Heroku**: Free tier (limited hours)
- **AWS Free Tier**: 1 year free (limited)

### Paid Options
- **Streamlit Cloud Pro**: ~$20/month
- **Heroku Hobby**: ~$7/month
- **AWS EC2 t3.small**: ~$15/month
- **GCP Cloud Run**: Pay-per-use (~$5-20/month)
- **Digital Ocean**: $5-10/month

---

## Recommended Setup by Use Case

### Personal Use
→ **Streamlit Cloud (Free)** or **Local Docker**

### Small Team (< 10 users)
→ **Streamlit Cloud Pro** or **Heroku**

### Company Internal Tool
→ **AWS EC2 + Nginx + SSL** or **GCP Cloud Run**

### SaaS Product
→ **Kubernetes + PostgreSQL + Redis** (advanced setup)

---

## Quick Deploy Commands

### Streamlit Cloud (Web UI)
```
1. Visit share.streamlit.io
2. Connect GitHub
3. Select repository and branch
4. Deploy!
```

### Docker
```bash
docker build -t portfolio . && docker run -p 8501:8501 portfolio
```

### Heroku
```bash
heroku create && git push heroku main && heroku open
```

### AWS (EC2)
```bash
ssh -i key.pem ubuntu@instance
# Then run setup commands
```

---

## Support

For deployment issues:
- Streamlit docs: https://docs.streamlit.io/streamlit-community-cloud
- Docker docs: https://docs.docker.com
- Platform-specific documentation

---

**Ready to deploy?** Choose the option that best fits your needs and follow the steps above!
