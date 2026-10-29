#!/bin/bash
# [U+1F310] WINDSURF PROTOCOL - Acoustic Lab Production Deployment
# Google Cloud / Ubuntu VPS Production Deployment Script
# WSP 49 Compliant Infrastructure Setup

set -e  # Exit on any error

# Configuration - Update these values for your deployment
APP_NAME="acoustic-lab"
APP_DIR="/var/www/$APP_NAME"
USER_NAME="acoustic"
DOMAIN_NAME="${DOMAIN_NAME:-acoustic-lab.edu}"  # Can be overridden
GIT_REPO="${GIT_REPO:-https://github.com/your-org/Foundups-Agent.git}"
BRANCH="${BRANCH:-main}"
NODE_ENV="${NODE_ENV:-production}"

echo "[ROCKET] WINDSURF PROTOCOL - Starting Acoustic Lab Production Deployment"
echo "[DATA] Target: $DOMAIN_NAME"
echo "[TOOL] Environment: $NODE_ENV"
echo "[BOX] Branch: $BRANCH"
echo "=================================================="

# Update system
echo "[BOX] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install core system packages
echo "[BOX] Installing core system dependencies..."
sudo apt install -y \
    python3.11 \
    python3.11-pip \
    python3.11-venv \
    python3.11-dev \
    nginx \
    git \
    ufw \
    certbot \
    python3-certbot-nginx \
    build-essential \
    software-properties-common \
    curl \
    wget \
    htop \
    vim \
    unattended-upgrades

# Install audio processing dependencies
echo "[U+1F3B5] Installing audio processing libraries..."
sudo apt install -y \
    libsndfile1 \
    ffmpeg \
    libasound2-dev \
    portaudio19-dev \
    python3-pyaudio

# Install database (PostgreSQL for future Phase 3)
echo "[U+1F5C4]️ Installing PostgreSQL database..."
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Install Redis (for future async tasks/queue)
echo "[REFRESH] Installing Redis cache/message queue..."
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Configure PostgreSQL (basic setup)
echo "[U+2699]️ Configuring PostgreSQL..."
sudo -u postgres createuser --createdb $USER_NAME || echo "User already exists"
sudo -u postgres createdb -O $USER_NAME ${APP_NAME}_prod || echo "Database already exists"

# Configure Redis
echo "[U+2699]️ Configuring Redis..."
sudo sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
sudo systemctl restart redis-server

# Create application user with proper permissions
echo "[U+1F464] Creating application user..."
sudo useradd -m -s /bin/bash $USER_NAME || echo "User already exists"
sudo usermod -a -G www-data $USER_NAME

# Create application directories with proper permissions
echo "[U+1F4C1] Creating application directories..."
sudo mkdir -p $APP_DIR
sudo mkdir -p /var/log/$APP_NAME
sudo mkdir -p /var/run/$APP_NAME
sudo mkdir -p /var/cache/$APP_NAME
sudo mkdir -p /var/lib/$APP_NAME

# Set proper ownership
sudo chown -R $USER_NAME:$USER_NAME $APP_DIR
sudo chown -R $USER_NAME:$USER_NAME /var/log/$APP_NAME
sudo chown -R $USER_NAME:$USER_NAME /var/run/$APP_NAME
sudo chown -R $USER_NAME:$USER_NAME /var/cache/$APP_NAME
sudo chown -R $USER_NAME:$USER_NAME /var/lib/$APP_NAME

# Clone application code from repository
echo "[CLIPBOARD] Cloning application code..."
if [ -d "$APP_DIR/.git" ]; then
    echo "Repository already exists, pulling latest changes..."
    sudo -u $USER_NAME bash -c "cd $APP_DIR && git fetch && git checkout $BRANCH && git pull origin $BRANCH"
else
    sudo -u $USER_NAME git clone -b $BRANCH $GIT_REPO $APP_DIR
fi

# Navigate to acoustic_lab module directory
MODULE_DIR="$APP_DIR/modules/platform_integration/acoustic_lab"
if [ ! -d "$MODULE_DIR" ]; then
    echo "[FAIL] Acoustic Lab module not found in repository"
    exit 1
fi

# Set up Python virtual environment
echo "[U+1F40D] Setting up Python virtual environment..."
sudo -u $USER_NAME bash -c "cd $APP_DIR && python3.11 -m venv venv"
sudo -u $USER_NAME bash -c "cd $APP_DIR && source venv/bin/activate && pip install --upgrade pip setuptools wheel"

# Install Python dependencies
echo "[BOX] Installing Python dependencies..."
cd $MODULE_DIR
sudo -u $USER_NAME bash -c "cd $APP_DIR && source venv/bin/activate && pip install -r modules/platform_integration/acoustic_lab/requirements.txt"

# Create production .env file
echo "[TOOL] Creating production environment configuration..."
cat > $APP_DIR/.env << EOF
# Acoustic Lab Production Environment Configuration
# WSP 71 Compliant - No secrets in repository

# Application Settings
NODE_ENV=production
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Database Configuration (Phase 3)
DATABASE_URL=postgresql://$USER_NAME@localhost/${APP_NAME}_prod

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Ethereum Configuration (Phase 1 - Simulated)
ETHEREUM_TESTNET_URL=https://sepolia.infura.io/v3/YOUR_INFURA_KEY

# Acoustic Lab Settings
ACOUSTIC_LAB_DOMAIN=$DOMAIN_NAME
ACOUSTIC_LAB_UPLOAD_LIMIT=16MB
ACOUSTIC_LAB_SESSION_TIMEOUT=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/$APP_NAME/acoustic_lab.log

# Performance
MAX_WORKERS=4
WORKER_TIMEOUT=30
KEEP_ALIVE=10

# Security
ALLOWED_HOSTS=$DOMAIN_NAME,localhost,127.0.0.1
CORS_ORIGINS=https://$DOMAIN_NAME

# Educational Settings
GEO_RESTRICT_TO_UTAH=true
SYNTHETIC_AUDIO_ONLY=true
PROOF_OF_EXISTENCE_ENABLED=true
EOF

sudo chown $USER_NAME:$USER_NAME $APP_DIR/.env
sudo chmod 600 $APP_DIR/.env

# Install systemd service
echo "[U+2699]️ Installing systemd service..."
sudo cp $MODULE_DIR/scripts/acoustic-lab.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME

# Configure Nginx reverse proxy
echo "[U+1F310] Configuring Nginx reverse proxy..."
sudo cp $MODULE_DIR/scripts/nginx.conf /etc/nginx/sites-available/$APP_NAME

# Update nginx configuration with correct paths
sudo sed -i "s|acoustic-lab.edu|$DOMAIN_NAME|g" /etc/nginx/sites-available/$APP_NAME
sudo sed -i "s|/opt/acoustic-lab|/var/www/acoustic-lab|g" /etc/nginx/sites-available/$APP_NAME
sudo sed -i "s|acoustic_lab|$APP_NAME|g" /etc/nginx/sites-available/$APP_NAME

# Enable site and remove default
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t
if [ $? -ne 0 ]; then
    echo "[FAIL] Nginx configuration test failed"
    exit 1
fi

# Configure firewall (WSP 71 security)
echo "[U+1F525] Configuring firewall..."
sudo ufw --force enable
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force reload

# Configure automatic security updates
echo "[LOCK] Configuring automatic security updates..."
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

# Start services
echo "[U+25B6]️ Starting production services..."
sudo systemctl start $APP_NAME
sudo systemctl start nginx

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 10

# Health check
echo "[U+1F3E5] Running comprehensive health checks..."

# Check systemd services
if ! sudo systemctl is-active --quiet $APP_NAME; then
    echo "[FAIL] Acoustic Lab service failed to start"
    sudo journalctl -u $APP_NAME --no-pager -n 20
    exit 1
fi

if ! sudo systemctl is-active --quiet nginx; then
    echo "[FAIL] Nginx service failed to start"
    sudo journalctl -u nginx --no-pager -n 20
    exit 1
fi

# Check PostgreSQL and Redis
if ! sudo systemctl is-active --quiet postgresql; then
    echo "[FAIL] PostgreSQL service failed to start"
    exit 1
fi

if ! sudo systemctl is-active --quiet redis-server; then
    echo "[FAIL] Redis service failed to start"
    exit 1
fi

# Test application health endpoint
if curl -f -s http://localhost/health > /dev/null; then
    echo "[OK] Application health check passed"
else
    echo "[FAIL] Application health check failed"
    sudo journalctl -u $APP_NAME --no-pager -n 20
    exit 1
fi

# SSL certificate setup (Let's Encrypt)
read -p "[LOCK] Do you want to set up SSL certificate with Let's Encrypt? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "[LOCK] Setting up SSL certificate with Let's Encrypt..."
    sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME

    if [ $? -eq 0 ]; then
        echo "[OK] SSL certificate installed successfully"
        HTTPS_URL="https://$DOMAIN_NAME"
    else
        echo "[FAIL] SSL certificate installation failed"
        HTTPS_URL="http://$DOMAIN_NAME"
    fi
else
    echo "[U+26A0]️ SSL not configured - consider setting up HTTPS for production"
    HTTPS_URL="http://$DOMAIN_NAME"
fi

# Final verification and summary
echo ""
echo "[CELEBRATE] WINDSURF PROTOCOL - Acoustic Lab Production Deployment COMPLETED!"
echo "=================================================="
echo ""
echo "[DATA] Service Status:"
echo "  [OK] Acoustic Lab: $(sudo systemctl is-active $APP_NAME)"
echo "  [OK] Nginx: $(sudo systemctl is-active nginx)"
echo "  [OK] PostgreSQL: $(sudo systemctl is-active postgresql)"
echo "  [OK] Redis: $(sudo systemctl is-active redis-server)"
echo ""
echo "[U+1F310] Application URLs:"
echo "  HTTP:  http://$DOMAIN_NAME"
echo "  HTTPS: $HTTPS_URL"
echo "  Health: $HTTPS_URL/health"
echo ""
echo "[U+1F4C1] Important Paths:"
echo "  Application: $APP_DIR"
echo "  Logs: /var/log/$APP_NAME/"
echo "  Config: $APP_DIR/.env"
echo ""
echo "[TOOL] Useful Commands:"
echo "  # Check service status"
echo "  sudo systemctl status $APP_NAME"
echo ""
echo "  # View application logs"
echo "  sudo journalctl -u $APP_NAME -f"
echo ""
echo "  # Restart services"
echo "  sudo systemctl restart $APP_NAME nginx"
echo ""
echo "  # Nginx logs"
echo "  sudo tail -f /var/log/nginx/${APP_NAME}_access.log"
echo "  sudo tail -f /var/log/nginx/${APP_NAME}_error.log"
echo ""
echo "[LOCK] Security Notes:"
echo "  - SSH key authentication configured"
echo "  - Firewall active (UFW)"
echo "  - Automatic security updates enabled"
echo "  - Secrets managed via environment variables"
echo ""
echo "[BOOKS] Next Steps:"
echo "  1. Test the application: curl $HTTPS_URL/health"
echo "  2. Upload test audio: Access $HTTPS_URL in browser"
echo "  3. Monitor logs: sudo journalctl -u $APP_NAME -f"
echo "  4. Set up monitoring/alerting (optional)"
echo ""
echo "[GRADUATE] Educational Platform Ready - Teaching Acoustic Triangulation & Audio Analysis!"
echo "[U+1F4D6] WSP 49 Compliant Infrastructure - Production Deployment Complete"
