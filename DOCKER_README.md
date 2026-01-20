# Docker Deployment Guide

This guide covers deploying the Portfolio Dashboard using Docker.

## Quick Start (Recommended)

### Option 1: Automated Script (Easiest)

```bash
./docker-quickstart.sh
```

This script will:
- ✅ Check Docker installation
- ✅ Verify environment configuration
- ✅ Build the Docker image
- ✅ Create data directories
- ✅ Start the container
- ✅ Open browser automatically

### Option 2: Docker Compose (Best for Production)

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

### Option 3: Manual Docker Commands

```bash
# Build image
docker build -t portfolio-dashboard .

# Run container
docker run -d \
  --name portfolio-dashboard \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -e FRED_API_KEY=your_key_here \
  portfolio-dashboard

# Access at http://localhost:8501
```

## Prerequisites

### Install Docker

**macOS:**
```bash
# Download Docker Desktop
# https://www.docker.com/products/docker-desktop
```

**Windows:**
```bash
# Download Docker Desktop
# https://www.docker.com/products/docker-desktop
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add:

```env
FRED_API_KEY=your_api_key_here
```

Get a free FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html

## Usage

### Start the Dashboard

**Method 1: Quick Start Script**
```bash
./docker-quickstart.sh
```

**Method 2: Docker Compose**
```bash
docker-compose up -d
```

**Method 3: Direct Docker**
```bash
docker run -d \
  --name portfolio-dashboard \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -e FRED_API_KEY=${FRED_API_KEY} \
  portfolio-dashboard
```

### Access the Dashboard

Open your browser to: **http://localhost:8501**

### View Logs

```bash
# Docker Compose
docker-compose logs -f

# Direct Docker
docker logs -f portfolio-dashboard
```

### Stop the Dashboard

```bash
# Docker Compose
docker-compose down

# Direct Docker
docker stop portfolio-dashboard
```

### Restart the Dashboard

```bash
# Docker Compose
docker-compose restart

# Direct Docker
docker restart portfolio-dashboard
```

## Data Persistence

Your portfolio data is stored in the `./data` directory and persists between container restarts.

**Backup your data:**
```bash
# Backup
tar -czf portfolio-backup-$(date +%Y%m%d).tar.gz data/

# Restore
tar -xzf portfolio-backup-YYYYMMDD.tar.gz
```

## Advanced Usage

### Custom Port

Run on a different port (e.g., 9000):

```bash
docker run -d \
  --name portfolio-dashboard \
  -p 9000:8501 \
  -v $(pwd)/data:/app/data \
  -e FRED_API_KEY=${FRED_API_KEY} \
  portfolio-dashboard
```

Access at: http://localhost:9000

### Mount Custom Data

```bash
docker run -d \
  --name portfolio-dashboard \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v /path/to/my/portfolios:/app/uploads \
  -e FRED_API_KEY=${FRED_API_KEY} \
  portfolio-dashboard
```

### View Container Stats

```bash
docker stats portfolio-dashboard
```

### Execute Commands Inside Container

```bash
# Open shell in container
docker exec -it portfolio-dashboard /bin/bash

# Run Python in container
docker exec -it portfolio-dashboard python -c "import yfinance; print('OK')"
```

## Troubleshooting

### Container won't start

**Check logs:**
```bash
docker logs portfolio-dashboard
```

**Common issues:**
- Port 8501 already in use
- Invalid environment variables
- Insufficient memory

**Solutions:**
```bash
# Check what's using port 8501
sudo lsof -i :8501

# Or use different port
docker run -p 8502:8501 ...

# Check Docker resources
docker info
```

### Port already in use

```bash
# Find what's using the port
sudo lsof -i :8501

# Kill the process
kill -9 <PID>

# Or use a different port
docker run -p 8502:8501 ...
```

### Permission denied

```bash
# On Linux, add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
# Or use newgrp
newgrp docker
```

### Container keeps restarting

```bash
# Check logs
docker logs portfolio-dashboard

# Run without auto-restart to see error
docker run -it --rm \
  -p 8501:8501 \
  -e FRED_API_KEY=${FRED_API_KEY} \
  portfolio-dashboard
```

### Cannot connect to Docker daemon

```bash
# Start Docker service (Linux)
sudo systemctl start docker

# Start Docker Desktop (macOS/Windows)
# Open Docker Desktop application
```

### Out of disk space

```bash
# Clean up unused images
docker system prune -a

# Remove old images
docker image prune -a

# Check disk usage
docker system df
```

## Updates

### Update to latest code

```bash
# Pull latest code
git pull origin claude/portfolio-dashboard-macro-0F39Q

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Or with direct Docker
docker stop portfolio-dashboard
docker rm portfolio-dashboard
docker build -t portfolio-dashboard .
./docker-quickstart.sh
```

### Update dependencies only

```bash
# Rebuild image
docker-compose build --no-cache

# Restart
docker-compose up -d
```

## Production Deployment

### With Nginx Reverse Proxy

See `deployment/nginx.conf` for configuration.

```bash
# Start with Nginx profile
docker-compose --profile with-nginx up -d
```

### Enable HTTPS/SSL

1. Get SSL certificates (Let's Encrypt):
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com
```

2. Copy certificates to deployment/ssl/
3. Update nginx.conf with certificate paths
4. Restart:
```bash
docker-compose --profile with-nginx up -d
```

### Resource Limits

Limit memory and CPU:

```bash
docker run -d \
  --name portfolio-dashboard \
  -p 8501:8501 \
  --memory="1g" \
  --cpus="1.0" \
  -v $(pwd)/data:/app/data \
  -e FRED_API_KEY=${FRED_API_KEY} \
  portfolio-dashboard
```

Or in docker-compose.yml:
```yaml
services:
  portfolio-dashboard:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Health Monitoring

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' portfolio-dashboard

# View health check logs
docker inspect --format='{{json .State.Health}}' portfolio-dashboard | jq
```

### Auto-restart on failure

Already configured with `--restart unless-stopped` in docker-compose.yml.

## Security Best Practices

### Don't expose database files

The `.gitignore` already excludes `data/` directory.

### Use secrets for API keys

Never commit `.env` file:
```bash
# Verify .env is gitignored
git check-ignore .env
```

### Limit container privileges

```bash
docker run -d \
  --name portfolio-dashboard \
  --security-opt=no-new-privileges:true \
  --cap-drop=ALL \
  -p 8501:8501 \
  portfolio-dashboard
```

### Use read-only filesystem where possible

```bash
docker run -d \
  --name portfolio-dashboard \
  --read-only \
  --tmpfs /tmp \
  -v $(pwd)/data:/app/data \
  portfolio-dashboard
```

## Container Maintenance

### Scheduled backups

Create a cron job:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/git-down && tar -czf backups/portfolio-$(date +\%Y\%m\%d).tar.gz data/
```

### Log rotation

Docker handles log rotation automatically, but you can configure:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Add to `/etc/docker/daemon.json` and restart Docker.

### Monitoring

Use Docker stats:
```bash
# Real-time stats
docker stats portfolio-dashboard

# Or with docker-compose
docker-compose stats
```

## Multi-Platform Build

Build for different architectures:

```bash
# Build for ARM (Raspberry Pi, Apple Silicon)
docker buildx build --platform linux/arm64 -t portfolio-dashboard:arm64 .

# Build for AMD64 (Intel/AMD)
docker buildx build --platform linux/amd64 -t portfolio-dashboard:amd64 .

# Build for both
docker buildx build --platform linux/amd64,linux/arm64 -t portfolio-dashboard:latest .
```

## Docker Hub Deployment

Push to Docker Hub:

```bash
# Tag image
docker tag portfolio-dashboard yourusername/portfolio-dashboard:latest

# Login
docker login

# Push
docker push yourusername/portfolio-dashboard:latest

# Pull on another machine
docker pull yourusername/portfolio-dashboard:latest
```

## FAQ

**Q: How much disk space does it need?**
A: ~1-2 GB for the image, plus your data.

**Q: Can I run multiple instances?**
A: Yes, use different ports and container names.

**Q: Does it work on ARM (M1 Mac, Raspberry Pi)?**
A: Yes, Python and dependencies are platform-independent.

**Q: How do I upgrade Python version?**
A: Edit `Dockerfile` and change `FROM python:3.10-slim` to desired version.

**Q: Can I use PostgreSQL instead of SQLite?**
A: Yes, set `DATABASE_URL` environment variable to PostgreSQL connection string.

## Support

For Docker-specific issues:
- Docker documentation: https://docs.docker.com
- Docker Compose: https://docs.docker.com/compose

For application issues:
- See main README.md
- Check TROUBLESHOOTING.md
- Open GitHub issue

## Quick Reference

```bash
# Build
docker build -t portfolio-dashboard .

# Run
docker run -d --name portfolio-dashboard -p 8501:8501 portfolio-dashboard

# Logs
docker logs -f portfolio-dashboard

# Stop
docker stop portfolio-dashboard

# Start
docker start portfolio-dashboard

# Remove
docker rm portfolio-dashboard

# Shell access
docker exec -it portfolio-dashboard /bin/bash

# Stats
docker stats portfolio-dashboard

# Inspect
docker inspect portfolio-dashboard

# Clean up
docker system prune -a
```

---

**Ready to deploy?** Run `./docker-quickstart.sh` and you'll be up in minutes!
