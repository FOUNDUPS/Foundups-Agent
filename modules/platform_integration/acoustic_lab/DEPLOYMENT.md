# [U+1F310] WINDSURF PROTOCOL - Acoustic Lab Production Deployment Guide

**WSP Framework Compliant Infrastructure Setup**

## Overview

This guide provides step-by-step instructions for deploying the Acoustic Lab educational platform to production on Ubuntu VPS or Google Cloud. The deployment follows WSP 49 (Module Structure), WSP 71 (Secrets Management), and WSP 85 (Root Directory Protection) protocols.

## Prerequisites

### System Requirements
- **Ubuntu VPS**: 20.04 LTS or 22.04 LTS (2GB RAM minimum, 4GB recommended)
- **Google Cloud**: Compute Engine VM with Ubuntu image
- **Domain Name**: Registered domain pointing to VPS IP
- **SSH Access**: Root or sudo access to the server

### DNS Configuration
```bash
# Add A record for your domain
acoustic-lab.edu A [YOUR_VPS_IP]

# Optional: Add www redirect
www.acoustic-lab.edu CNAME acoustic-lab.edu
```

## Quick Deployment (Automated)

### Option 1: One-Command Deployment

```bash
# Clone repository and run deployment
git clone https://github.com/your-org/Foundups-Agent.git
cd Foundups-Agent/modules/platform_integration/acoustic_lab/scripts

# Set environment variables
export DOMAIN_NAME="acoustic-lab.edu"
export GIT_REPO="https://github.com/your-org/Foundups-Agent.git"
export BRANCH="main"

# Run automated deployment
sudo bash deploy.sh
```

### Option 2: Manual Step-by-Step

If you prefer manual control or need customization:

## Manual Deployment Steps

### Step 1: Server Provisioning

#### Ubuntu VPS (Digital Ocean/Linode/Vultr)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3.11 python3.11-pip python3.11-venv \
    nginx git ufw certbot python3-certbot-nginx \
    postgresql postgresql-contrib redis-server \
    build-essential software-properties-common \
    curl wget htop vim unattended-upgrades \
    libsndfile1 ffmpeg libasound2-dev portaudio19-dev
```

#### Google Cloud Platform
```bash
# Create VM instance
gcloud compute instances create acoustic-lab \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --tags=http-server,https-server

# Configure firewall
gcloud compute firewall-rules create allow-http \
    --allow tcp:80 \
    --target-tags http-server

gcloud compute firewall-rules create allow-https \
    --allow tcp:443 \
    --target-tags https-server
```

### Step 2: Application User Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash acoustic
sudo usermod -a -G www-data acoustic

# Create application directories
sudo mkdir -p /var/www/acoustic-lab
sudo mkdir -p /var/log/acoustic-lab
sudo mkdir -p /var/run/acoustic-lab
sudo mkdir -p /var/cache/acoustic-lab
sudo mkdir -p /var/lib/acoustic-lab

# Set ownership
sudo chown -R acoustic:acoustic /var/www/acoustic-lab
sudo chown -R acoustic:acoustic /var/log/acoustic-lab
sudo chown -R acoustic:acoustic /var/run/acoustic-lab
sudo chown -R acoustic:acoustic /var/cache/acoustic-lab
sudo chown -R acoustic:acoustic /var/lib/acoustic-lab
```

### Step 3: Database Setup

```bash
# Start PostgreSQL and Redis
sudo systemctl enable postgresql redis-server
sudo systemctl start postgresql redis-server

# Create database and user
sudo -u postgres createuser --createdb acoustic
sudo -u postgres createdb -O acoustic acoustic_lab_prod

# Configure Redis
sudo sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
sudo systemctl restart redis-server
```

### Step 4: Application Deployment

```bash
# Clone repository
sudo -u acoustic git clone -b main https://github.com/your-org/Foundups-Agent.git /var/www/acoustic-lab

# Navigate to module directory
cd /var/www/acoustic-lab/modules/platform_integration/acoustic_lab

# Create Python virtual environment
sudo -u acoustic bash -c "cd /var/www/acoustic-lab && python3.11 -m venv venv"
sudo -u acoustic bash -c "cd /var/www/acoustic-lab && source venv/bin/activate && pip install --upgrade pip setuptools wheel"

# Install dependencies
sudo -u acoustic bash -c "cd /var/www/acoustic-lab && source venv/bin/activate && pip install -r modules/platform_integration/acoustic_lab/requirements.txt"
```

### Gunicorn factory and qualification boundary

The checked-in config uses Gunicorn's recognized `wsgi_app` setting to call
`modules.platform_integration.acoustic_lab.src.web_app:create_app()`. The systemd
service retains its config-only command; no positional application argument or
environment-provided application binding is required:

```bash
# From the repository root, after the documented account/path provisioning:
venv/bin/gunicorn --config modules/platform_integration/acoustic_lab/scripts/gunicorn.conf.py
```

Gunicorn 22.0.0 is the security-update target. Strict request-framing defaults,
sync workers, preloading, foreground execution and production timeout settings
remain unchanged. The module requirements must be selected explicitly after the
inner deployment shell enters the repository root. Neither this source repair
nor a test fixture runs `deploy.sh`, provisions the acoustic account, starts
systemd/nginx, or certifies a VPS deployment.

The dedicated Linux test selection loads this exact config with fixture-only
numeric runner UID/GID, temporary paths, one worker and an OS-assigned loopback
port. These replacements occur before Gunicorn validates the config; CLI user
overrides are too late if the production account is absent. The application
binding is not replaced. Parser rejection controls and actual `/` and `/health`
requests require a separate foreground master/worker cleanup receipt. This
candidate still requires hosted Linux execution; Windows source checks do not
establish Gunicorn execution. The four broader application-test failures and
the separate FFmpeg timeout-child defect remain outside this repair.

### Step 5: Environment Configuration

```bash
# Create production .env file
cat > /var/www/acoustic-lab/.env << 'EOF'
# Acoustic Lab Production Environment Configuration
# WSP 71 Compliant - No secrets in repository

# Application Settings
NODE_ENV=production
FLASK_ENV=production
SECRET_KEY=your-secure-random-key-here

# Database Configuration
DATABASE_URL=postgresql://acoustic@localhost/acoustic_lab_prod

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Ethereum Configuration (Phase 1 - Simulated)
ETHEREUM_TESTNET_URL=https://sepolia.infura.io/v3/YOUR_INFURA_KEY

# Acoustic Lab Settings
ACOUSTIC_LAB_DOMAIN=acoustic-lab.edu
ACOUSTIC_LAB_UPLOAD_LIMIT=16MB
ACOUSTIC_LAB_SESSION_TIMEOUT=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/acoustic-lab/acoustic_lab.log

# Performance
MAX_WORKERS=4
WORKER_TIMEOUT=30
KEEP_ALIVE=10

# Security
ALLOWED_HOSTS=acoustic-lab.edu,localhost,127.0.0.1
CORS_ORIGINS=https://acoustic-lab.edu

# Educational Settings
GEO_RESTRICT_TO_UTAH=true
SYNTHETIC_AUDIO_ONLY=true
PROOF_OF_EXISTENCE_ENABLED=true
EOF

# Secure the .env file
sudo chown acoustic:acoustic /var/www/acoustic-lab/.env
sudo chmod 600 /var/www/acoustic-lab/.env
```

### Step 6: Service Configuration

```bash
# Copy systemd service file
sudo cp /var/www/acoustic-lab/modules/platform_integration/acoustic_lab/scripts/acoustic-lab.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable acoustic-lab
```

### Step 7: Nginx Configuration

```bash
# Copy nginx configuration
sudo cp /var/www/acoustic-lab/modules/platform_integration/acoustic_lab/scripts/nginx.conf /etc/nginx/sites-available/acoustic-lab

# Update configuration with your domain
sudo sed -i 's/acoustic-lab.edu/your-domain.com/g' /etc/nginx/sites-available/acoustic-lab

# Enable site
sudo ln -sf /etc/nginx/sites-available/acoustic-lab /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t
```

### Step 8: Security Configuration

```bash
# Configure firewall
sudo ufw --force enable
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw allow 80
sudo ufw allow 443

# Configure automatic security updates
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

# SSH hardening (optional but recommended)
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### Step 9: SSL Certificate

```bash
# Install Let's Encrypt certificate
sudo certbot --nginx -d acoustic-lab.edu --non-interactive --agree-tos --email admin@acoustic-lab.edu

# Test certificate renewal
sudo certbot renew --dry-run
```

### Step 10: Service Startup

```bash
# Start all services
sudo systemctl start acoustic-lab
sudo systemctl start nginx
sudo systemctl start postgresql
sudo systemctl start redis-server

# Verify services are running
sudo systemctl status acoustic-lab
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server
```

### Step 11: Final Testing

```bash
# Test health endpoint
curl -f https://acoustic-lab.edu/health

# Check logs
sudo journalctl -u acoustic-lab -f

# Test application in browser
# https://acoustic-lab.edu
```

## Configuration Files

### Environment Variables (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `NODE_ENV` | Environment mode | `production` |
| `SECRET_KEY` | Flask secret key | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user@localhost/db` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `ACOUSTIC_LAB_DOMAIN` | Domain name | `acoustic-lab.edu` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Systemd Service Configuration

- **User**: `acoustic`
- **Working Directory**: `/var/www/acoustic-lab`
- **Environment**: Production with `.env` file
- **Security**: Hardened with various restrictions
- **Resources**: 1GB memory limit, 75% CPU quota

### Nginx Configuration

- **Reverse Proxy**: Forwards to Gunicorn on port 8000
- **SSL/TLS**: Automatic HTTPS with Let's Encrypt
- **Security Headers**: XSS protection, content type options
- **Rate Limiting**: Basic protection against abuse
- **Static Files**: Optimized caching for assets

## Monitoring & Maintenance

### Service Monitoring

```bash
# Check service status
sudo systemctl status acoustic-lab

# View application logs
sudo journalctl -u acoustic-lab -f

# View nginx logs
sudo tail -f /var/log/nginx/acoustic-lab_access.log
sudo tail -f /var/log/nginx/acoustic-lab_error.log
```

### Performance Monitoring

```bash
# System resource usage
htop

# Database connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Redis info
redis-cli info
```

### Backup Strategy

```bash
# Database backup
sudo -u postgres pg_dump acoustic_lab_prod > acoustic_lab_$(date +%Y%m%d).sql

# Application backup
tar -czf acoustic_lab_backup_$(date +%Y%m%d).tar.gz /var/www/acoustic-lab

# Configuration backup
cp /etc/nginx/sites-available/acoustic-lab nginx_backup.conf
cp /etc/systemd/system/acoustic-lab.service systemd_backup.service
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status and logs
sudo systemctl status acoustic-lab
sudo journalctl -u acoustic-lab --no-pager -n 50

# Check Python environment
sudo -u acoustic bash -c "cd /var/www/acoustic-lab && source venv/bin/activate && python -c 'import sys; print(sys.path)'"
```

#### Nginx Configuration Errors
```bash
# Test configuration
sudo nginx -t

# Check syntax
sudo nginx -c /etc/nginx/nginx.conf

# Reload configuration
sudo systemctl reload nginx
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Force renewal
sudo certbot certonly --standalone -d acoustic-lab.edu
```

### Performance Tuning

#### Gunicorn Optimization
```ini
# gunicorn.conf.py adjustments
workers = multiprocessing.cpu_count() * 2 + 1  # Increase for high traffic
worker_connections = 1000  # Increase for concurrent connections
max_requests = 1000  # Restart workers periodically
```

#### Database Optimization
```sql
-- PostgreSQL performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
```

## Scaling Considerations

### Horizontal Scaling (Load Balancer)
```nginx
# nginx upstream configuration
upstream acoustic_lab_cluster {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    location / {
        proxy_pass http://acoustic_lab_cluster;
    }
}
```

### Vertical Scaling
- **CPU**: Increase core count for audio processing
- **Memory**: 2-4GB for concurrent users
- **Storage**: 50GB+ for logs and future data
- **Network**: Consider CDN for static assets

## Security Checklist

- [ ] SSH key authentication only
- [ ] Firewall configured (UFW)
- [ ] SSL/TLS certificates installed
- [ ] Automatic security updates enabled
- [ ] Secrets in environment variables
- [ ] File permissions restricted
- [ ] Service running as non-root user
- [ ] Database access restricted
- [ ] Logs monitored and rotated

## WSP Compliance Verification

### WSP 49: Module Structure
- [x] Proper directory hierarchy
- [x] Documentation in appropriate locations
- [x] Scripts in dedicated directories

### WSP 71: Secrets Management
- [x] No secrets in repository
- [x] Environment variable configuration
- [x] Secure file permissions

### WSP 85: Root Directory Protection
- [x] Application in `/var/www`
- [x] No inappropriate files in root
- [x] Proper service user isolation

## Support & Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Check service status and logs
2. **Monthly**: Update system packages and dependencies
3. **Quarterly**: Review security settings and certificates

### Emergency Contacts
- **System Admin**: [admin@acoustic-lab.edu]
- **Technical Support**: [support@acoustic-lab.edu]
- **Security Issues**: [security@acoustic-lab.edu]

---

**[GRADUATE] Acoustic Lab Production Deployment Guide**
**WSP Protocol Compliant Infrastructure Setup**
**Ready for Educational Acoustic Triangulation & Audio Analysis Teaching**
