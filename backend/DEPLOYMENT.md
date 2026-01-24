# TMS Deployment Guide

## Pre-Deployment Checklist

### 1. Server Requirements
- [ ] Ubuntu 22.04 LTS (or similar Linux distribution)
- [ ] Python 3.10+
- [ ] PostgreSQL 14+
- [ ] Nginx (reverse proxy)
- [ ] SSL certificate (Let's Encrypt recommended)
- [ ] Minimum 2GB RAM, 2 CPU cores

### 2. Environment Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx certbot python3-certbot-nginx

# Create application user
sudo useradd -m -s /bin/bash tms
sudo mkdir -p /var/www/tms
sudo chown tms:tms /var/www/tms

# Create log directory
sudo mkdir -p /var/log/tms
sudo chown tms:tms /var/log/tms
```

### 3. Database Setup

```bash
# Login to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE tms_production;
CREATE USER tms_user WITH PASSWORD 'your-strong-password';
ALTER ROLE tms_user SET client_encoding TO 'utf8';
ALTER ROLE tms_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tms_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE tms_production TO tms_user;
\q
```

### 4. Application Deployment

```bash
# Switch to application user
sudo su - tms
cd /var/www/tms

# Clone repository
git clone https://github.com/your-org/tms-app.git .

# Create virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy and configure environment
cp .env.production .env
# Edit .env with production values
nano .env

# Run migrations
python manage.py migrate --settings=tms_project.settings.production

# Collect static files
python manage.py collectstatic --noinput --settings=tms_project.settings.production

# Create superuser
python manage.py createsuperuser --settings=tms_project.settings.production
```

### 5. Gunicorn Configuration

Create `/var/www/tms/backend/gunicorn.conf.py`:

```python
import multiprocessing

# Bind to Unix socket for Nginx
bind = "unix:/var/www/tms/backend/tms.sock"

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads = 2
timeout = 120

# Logging
accesslog = "/var/log/tms/gunicorn_access.log"
errorlog = "/var/log/tms/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "tms"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

### 6. Systemd Service

Create `/etc/systemd/system/tms.service`:

```ini
[Unit]
Description=TMS Django Application
After=network.target postgresql.service

[Service]
User=tms
Group=tms
WorkingDirectory=/var/www/tms/backend
Environment="DJANGO_SETTINGS_MODULE=tms_project.settings.production"
ExecStart=/var/www/tms/backend/venv/bin/gunicorn --config gunicorn.conf.py tms_project.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable tms
sudo systemctl start tms
sudo systemctl status tms
```

### 7. Nginx Configuration

Create `/etc/nginx/sites-available/tms`:

```nginx
upstream tms_backend {
    server unix:/var/www/tms/backend/tms.sock fail_timeout=0;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/tms_access.log;
    error_log /var/log/nginx/tms_error.log;

    # Max upload size
    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias /var/www/tms/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/tms/backend/media/;
        expires 7d;
    }

    # API endpoints
    location / {
        proxy_pass http://tms_backend;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/tms /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d api.yourdomain.com
```

### 8. Frontend Deployment

```bash
# Build frontend for production
cd /var/www/tms/frontend
npm install
npm run build -- --configuration=production

# Deploy to web server or CDN
# Option 1: Serve via Nginx
# Option 2: Deploy to Vercel/Netlify
# Option 3: Deploy to S3 + CloudFront
```

## Post-Deployment Verification

### Security Checks
- [ ] HTTPS is enforced (HTTP redirects to HTTPS)
- [ ] HSTS header is present
- [ ] CSP headers are configured
- [ ] Debug mode is OFF
- [ ] Secret key is unique and secure
- [ ] Database password is strong
- [ ] Admin panel is accessible only to authorized users

### Functional Checks
- [ ] Login/logout works
- [ ] API documentation accessible at `/api/docs/`
- [ ] Travel request creation works
- [ ] Approval workflow functions correctly
- [ ] Email notifications are sent
- [ ] File uploads work
- [ ] Reports can be exported

### Performance Checks
- [ ] Static files are cached (check response headers)
- [ ] Database queries are optimized
- [ ] Gunicorn workers are sufficient

## Maintenance Commands

```bash
# View logs
sudo journalctl -u tms -f
tail -f /var/log/tms/django.log

# Restart application
sudo systemctl restart tms

# Run migrations after updates
source /var/www/tms/backend/venv/bin/activate
python manage.py migrate --settings=tms_project.settings.production

# Collect static files after updates
python manage.py collectstatic --noinput --settings=tms_project.settings.production

# Create database backup
pg_dump -U tms_user tms_production > backup_$(date +%Y%m%d).sql
```

## Rollback Procedure

```bash
# Stop service
sudo systemctl stop tms

# Restore previous version
cd /var/www/tms
git checkout <previous-commit-hash>

# Restore database if needed
psql -U tms_user tms_production < backup_YYYYMMDD.sql

# Restart service
sudo systemctl start tms
```

## Monitoring Recommendations

1. **Application Monitoring**: Set up Sentry for error tracking
2. **Server Monitoring**: Use Prometheus + Grafana or similar
3. **Uptime Monitoring**: Use UptimeRobot or similar
4. **Log Aggregation**: Consider ELK stack or CloudWatch

## Support

For issues, check:
1. Application logs: `/var/log/tms/django.log`
2. Gunicorn logs: `/var/log/tms/gunicorn_error.log`
3. Nginx logs: `/var/log/nginx/tms_error.log`
4. System logs: `journalctl -u tms`
