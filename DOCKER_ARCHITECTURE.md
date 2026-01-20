# Portfolio Dashboard - Docker Architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Host Machine                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Docker Container: portfolio-dashboard        │  │
│  │                                                      │  │
│  │  ┌────────────────────────────────────────────┐     │  │
│  │  │      Streamlit Application (Port 8501)     │     │  │
│  │  │                                            │     │  │
│  │  │  ┌──────────────────────────────────┐     │     │  │
│  │  │  │      app.py (Main Dashboard)     │     │     │  │
│  │  │  └──────────────────────────────────┘     │     │  │
│  │  │                                            │     │  │
│  │  │  ┌──────────────────────────────────┐     │     │  │
│  │  │  │    Services Layer                │     │     │  │
│  │  │  │  • Data Fetcher (yfinance/FRED)  │     │     │  │
│  │  │  │  • Portfolio Calculator          │     │     │  │
│  │  │  │  • Risk Metrics                  │     │     │  │
│  │  │  └──────────────────────────────────┘     │     │  │
│  │  │                                            │     │  │
│  │  │  ┌──────────────────────────────────┐     │     │  │
│  │  │  │    Models Layer                  │     │     │  │
│  │  │  │  • Database Schema               │     │     │  │
│  │  │  │  • Portfolio Models              │     │     │  │
│  │  │  └──────────────────────────────────┘     │     │  │
│  │  │                                            │     │  │
│  │  │  ┌──────────────────────────────────┐     │     │  │
│  │  │  │    SQLite Database               │     │     │  │
│  │  │  │    /app/data/portfolio.db        │◄────┼─────┼──┐
│  │  │  └──────────────────────────────────┘     │     │  │
│  │  └────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                │                            │
│                                │ Port Mapping               │
│                                │ 8501:8501                  │
│                                ▼                            │
│         http://localhost:8501                              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Persistent Volume Mounts                  │  │
│  │                                                      │  │
│  │  ./data/          ──►  /app/data/                   │  │
│  │  (Host)                (Container)                  │  │
│  │                                                      │  │
│  │  ./sample_data/   ──►  /app/sample_data/           │  │
│  │  (Host)                (Container)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Environment Variables                     │  │
│  │                                                      │  │
│  │  FRED_API_KEY         (from .env file)              │  │
│  │  DATABASE_URL         (SQLite connection)           │  │
│  │  RISK_FREE_RATE       (default: 0.045)              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ External API Calls
                           ▼
        ┌──────────────────────────────────┐
        │    External Data Sources         │
        │                                  │
        │  • Yahoo Finance (yfinance)      │
        │    - Stock prices                │
        │    - Historical data             │
        │                                  │
        │  • FRED API                      │
        │    - Macro indicators            │
        │    - Economic data               │
        └──────────────────────────────────┘
```

## Component Breakdown

### Container Layer

**Base Image:** `python:3.10-slim`
- Minimal Debian-based Python image
- Optimized for size (~150 MB base)
- Security-focused with minimal attack surface

**Application Code:**
- Streamlit web framework
- Portfolio analysis engine
- Risk metrics calculator
- Data fetching services

**Runtime Configuration:**
- Port: 8501 (Streamlit default)
- Health checks every 30 seconds
- Auto-restart on failure
- Read/write access to data volume

### Volume Mounts

**./data/ → /app/data/**
- SQLite database (portfolio.db)
- Cached market data
- User uploads
- Persistent across container restarts

**./sample_data/ → /app/sample_data/**
- Example portfolio CSV
- LTCMA sample data
- Read-only

### Network Flow

```
User Browser
    ↓
http://localhost:8501
    ↓
Docker Port Mapping (8501:8501)
    ↓
Streamlit App in Container
    ↓ (if needed)
External APIs (Yahoo Finance, FRED)
```

## Deployment Modes

### Mode 1: Basic Docker

```bash
docker run -d \
  --name portfolio-dashboard \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -e FRED_API_KEY=abc123 \
  portfolio-dashboard
```

**Architecture:**
```
[Container] ──► Port 8501 ──► Host:8501 ──► Browser
     │
     └─► Volume: ./data/
```

### Mode 2: Docker Compose

```bash
docker-compose up -d
```

**Architecture:**
```
docker-compose.yml
    │
    ├─► portfolio-dashboard (service)
    │   ├─► Image: portfolio-dashboard
    │   ├─► Port: 8501:8501
    │   ├─► Volume: ./data
    │   ├─► Environment: .env
    │   └─► Restart: unless-stopped
    │
    └─► (optional) nginx (service)
        ├─► Image: nginx:alpine
        ├─► Port: 80:80, 443:443
        ├─► SSL certificates
        └─► Reverse proxy to dashboard
```

### Mode 3: With Nginx Reverse Proxy

```bash
docker-compose --profile with-nginx up -d
```

**Architecture:**
```
Browser
    ↓
https://portfolio.yourdomain.com (443)
    ↓
Nginx Container
    ├─► SSL Termination
    ├─► Security Headers
    └─► Reverse Proxy
        ↓
Portfolio Dashboard Container (8501)
    ↓
Database (./data/portfolio.db)
```

## Data Flow

### Portfolio Upload Flow

```
1. User uploads CSV via browser
   ↓
2. Streamlit receives file
   ↓
3. CSV Handler parses data
   ↓
4. Validation checks
   ↓
5. Save to SQLite database
   ↓
6. Fetch current prices (yfinance)
   ↓
7. Calculate metrics
   ↓
8. Display in dashboard
```

### Metrics Calculation Flow

```
1. Load positions from database
   ↓
2. Fetch historical prices (yfinance)
   ↓
3. Calculate returns
   ↓
4. Compute risk metrics
   │  ├─► Sharpe Ratio
   │  ├─► Sortino Ratio
   │  ├─► Max Drawdown
   │  └─► Others
   ↓
5. Compare to benchmarks
   ↓
6. Generate visualizations
   ↓
7. Display results
```

### Macro Indicators Flow

```
1. User selects indicators
   ↓
2. Fetch from FRED API
   │  (requires API key)
   ↓
3. Cache in database
   ↓
4. Calculate YoY changes
   ↓
5. Create time series charts
   ↓
6. Display trends
```

## Resource Requirements

### Minimum Specs

```
CPU:     1 core
Memory:  512 MB
Disk:    1 GB
Network: Internet connection
```

### Recommended Specs

```
CPU:     2 cores
Memory:  1-2 GB
Disk:    2 GB
Network: Broadband
```

### Resource Usage

```
Idle State:
  CPU:    5-10%
  Memory: 200-300 MB
  Disk:   500 MB

Active Use (calculating metrics):
  CPU:    50-80%
  Memory: 400-800 MB
  Disk:   500-700 MB
```

## Security Architecture

### Container Isolation

```
Host OS
  └─► Docker Engine
      └─► Container (isolated)
          ├─► Own filesystem (except volumes)
          ├─► Own network namespace
          ├─► Limited privileges
          └─► No access to host data
```

### Data Protection

```
.env file (host)
  └─► Environment variables
      └─► Container process only
          └─► Not in image
          └─► Not in logs
```

### Network Security

```
Container Network:
  • Internal: 172.17.0.0/16 (default)
  • Exposed: Port 8501 only
  • Outbound: HTTPS to APIs
  • No incoming except port 8501
```

## Scaling Options

### Vertical Scaling

Increase container resources:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

### Horizontal Scaling

Multiple instances with load balancer:
```
Load Balancer (Nginx/Traefik)
    │
    ├─► Dashboard Instance 1 (port 8501)
    ├─► Dashboard Instance 2 (port 8502)
    └─► Dashboard Instance 3 (port 8503)
```

**Note:** Requires shared database (PostgreSQL instead of SQLite).

## Monitoring Architecture

### Health Checks

```
Docker Health Check
    │
    └─► curl http://localhost:8501/_stcore/health
         │
         ├─► Success (200) → Container healthy
         └─► Failure → Auto-restart
```

### Logging

```
Container Logs
    │
    ├─► Streamlit app logs
    ├─► Python errors
    ├─► HTTP requests
    └─► Docker captures all
         │
         └─► docker logs portfolio-dashboard
```

### Metrics Collection

```
docker stats portfolio-dashboard
    │
    ├─► CPU usage
    ├─► Memory usage
    ├─► Network I/O
    └─► Disk I/O
```

## Backup Strategy

### Database Backup

```
Host: ./data/portfolio.db
    │
    ├─► Automatic (Docker volume)
    └─► Manual backup
        │
        └─► tar -czf backup.tar.gz ./data/
```

### Full Container Backup

```
1. Commit container to image
   docker commit portfolio-dashboard portfolio-backup

2. Save image to file
   docker save portfolio-backup > backup.tar

3. Restore later
   docker load < backup.tar
```

## Update Workflow

```
1. Pull latest code
   git pull

2. Stop container
   docker-compose down

3. Rebuild image
   docker-compose build

4. Start new container
   docker-compose up -d

5. Verify health
   docker-compose logs -f
```

## Troubleshooting Flow

```
Issue Detected
    │
    ├─► Check container status
    │   docker ps -a
    │
    ├─► Check logs
    │   docker logs portfolio-dashboard
    │
    ├─► Check health
    │   docker inspect --format='{{.State.Health.Status}}'
    │
    ├─► Check resources
    │   docker stats
    │
    └─► Check configuration
        docker inspect portfolio-dashboard
```

## Quick Reference Commands

```bash
# Build
docker build -t portfolio-dashboard .

# Run
docker run -d --name portfolio-dashboard -p 8501:8501 portfolio-dashboard

# Logs (live)
docker logs -f portfolio-dashboard

# Shell access
docker exec -it portfolio-dashboard /bin/bash

# Stats
docker stats portfolio-dashboard

# Health
docker inspect --format='{{.State.Health.Status}}' portfolio-dashboard

# Restart
docker restart portfolio-dashboard

# Stop & Remove
docker stop portfolio-dashboard && docker rm portfolio-dashboard

# Complete cleanup
docker system prune -a
```

---

**This architecture provides:**
- ✅ Isolation and security
- ✅ Easy deployment and updates
- ✅ Data persistence
- ✅ Health monitoring
- ✅ Scalability options
- ✅ Production-ready setup
