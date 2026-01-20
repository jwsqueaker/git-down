# Deployment Files

This directory contains configuration files for deploying the Portfolio Dashboard to various platforms.

## Files Overview

### Docker Deployment
- `deploy-docker.sh` - Automated Docker deployment script
- See `../Dockerfile` and `../docker-compose.yml` in root

### Nginx Configuration
- `nginx.conf` - Nginx reverse proxy configuration with SSL support
- Use with Docker Compose or standalone server deployment

### Systemd Service
- `portfolio-dashboard.service` - systemd service file for Linux servers
- Enables automatic startup and process management

## Quick Start

### Docker (Easiest)
```bash
# From project root
chmod +x deployment/deploy-docker.sh
./deployment/deploy-docker.sh
```

### Streamlit Cloud (No Config Needed)
1. Push to GitHub
2. Connect at share.streamlit.io
3. Add FRED_API_KEY in secrets
4. Deploy!

### Linux Server with systemd
```bash
# Install to /opt
sudo cp -r . /opt/portfolio-dashboard
cd /opt/portfolio-dashboard

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Install service
sudo cp deployment/portfolio-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable portfolio-dashboard
sudo systemctl start portfolio-dashboard
sudo systemctl status portfolio-dashboard
```

### With Nginx Reverse Proxy
```bash
# After setting up the app, configure Nginx
sudo cp deployment/nginx.conf /etc/nginx/sites-available/portfolio
sudo ln -s /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL with Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

## Environment Variables

All deployments need:
- `FRED_API_KEY` - Your FRED API key (optional but recommended)

Optional:
- `DATABASE_URL` - Database connection string
- `RISK_FREE_RATE` - Annual risk-free rate for calculations

## Platform-Specific Notes

### Streamlit Cloud
- Secrets go in dashboard settings, not .env file
- Use `.streamlit/secrets.toml.example` as template
- Free tier has resource limits

### Docker
- Data persists in `./data` directory
- Expose port 8501 or use Nginx
- Use docker-compose for easier management

### Heroku
- Uses `Procfile` in root directory
- Set config vars: `heroku config:set FRED_API_KEY=...`
- Free tier sleeps after inactivity

### AWS/GCP/Azure
- Use systemd service for process management
- Configure security groups/firewall
- Setup SSL certificates
- Consider using managed databases

## Security Checklist

Before deploying to production:

- [ ] Set strong passwords/keys
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall rules
- [ ] Set up monitoring
- [ ] Enable automatic backups
- [ ] Review Nginx security headers
- [ ] Restrict database permissions
- [ ] Use environment variables (not hardcoded secrets)

## Monitoring

### Docker Logs
```bash
docker-compose logs -f portfolio-dashboard
```

### Systemd Logs
```bash
sudo journalctl -u portfolio-dashboard -f
```

### Nginx Logs
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8501
sudo lsof -i :8501
# Or
sudo netstat -tulpn | grep 8501

# Kill process or change port
```

### Permission Denied
```bash
# Fix ownership
sudo chown -R www-data:www-data /opt/portfolio-dashboard

# Or run as your user (edit service file)
```

### Database Locked
```bash
# Stop all instances
sudo systemctl stop portfolio-dashboard
docker-compose down

# Remove lock file
rm portfolio.db-journal

# Restart
```

## Updates

To update deployed application:

### Docker
```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Systemd
```bash
cd /opt/portfolio-dashboard
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart portfolio-dashboard
```

### Streamlit Cloud
- Push to GitHub
- Streamlit Cloud auto-deploys

## Support

For deployment help:
- Check main DEPLOYMENT.md
- Review platform documentation
- Open GitHub issue
