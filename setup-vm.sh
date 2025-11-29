#!/bin/bash

# =============================================================================
# Blacklight VM Setup Script
# =============================================================================
# This script prepares a fresh Ubuntu/Debian VM for Blacklight deployment
# Run with: sudo bash setup-vm.sh
# =============================================================================

set -e  # Exit on error

echo "========================================="
echo "Blacklight VM Setup Script"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Get the regular user (not root)
REGULAR_USER=${SUDO_USER:-$USER}
echo "🔍 Detected user: $REGULAR_USER"
echo ""

# =============================================================================
# 1. Update System
# =============================================================================
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    git \
    vim \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx
echo "✅ System updated"
echo ""

# =============================================================================
# 2. Install Docker
# =============================================================================
echo "🐳 Installing Docker..."

# Remove old versions
apt-get remove -y docker docker-engine docker.io containerd runc || true

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
usermod -aG docker $REGULAR_USER

echo "✅ Docker installed"
docker --version
docker compose version
echo ""

# =============================================================================
# 3. Configure Firewall
# =============================================================================
echo "🔥 Configuring firewall (UFW)..."

# Reset UFW to defaults
ufw --force reset

# Allow SSH (important!)
ufw allow 22/tcp comment 'SSH'

# Allow HTTP and HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Enable UFW
ufw --force enable

echo "✅ Firewall configured"
ufw status
echo ""

# =============================================================================
# 4. Optimize System for Production
# =============================================================================
echo "⚙️  Optimizing system settings..."

# Increase file descriptor limits
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
EOF

# Optimize kernel parameters for Docker and PostgreSQL
cat >> /etc/sysctl.conf << 'EOF'

# Docker & Network optimization
net.core.somaxconn=1024
net.ipv4.tcp_max_syn_backlog=2048
net.ipv4.ip_local_port_range=1024 65535
net.ipv4.tcp_tw_reuse=1
net.ipv4.tcp_fin_timeout=30

# PostgreSQL optimization
vm.swappiness=10
vm.overcommit_memory=2
vm.overcommit_ratio=80
kernel.shmmax=4294967296
kernel.shmall=1048576
EOF

# Apply sysctl settings
sysctl -p

echo "✅ System optimized"
echo ""

# =============================================================================
# 5. Create Application Directory
# =============================================================================
echo "📁 Creating application directories..."

APP_DIR="/opt/blacklight"
mkdir -p $APP_DIR
chown -R $REGULAR_USER:$REGULAR_USER $APP_DIR

# Create backup directory
mkdir -p /backups/blacklight
chown -R $REGULAR_USER:$REGULAR_USER /backups/blacklight

echo "✅ Directories created at $APP_DIR"
echo ""

# =============================================================================
# 6. Setup SSL (Self-Signed Certificate for now)
# =============================================================================
echo "🔐 Setting up self-signed SSL certificate..."
echo "NOTE: Replace with Let's Encrypt certificate after domain is configured"
echo ""

SSL_DIR="$APP_DIR/nginx/ssl"
mkdir -p $SSL_DIR

# Generate self-signed certificate (valid for 365 days)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout $SSL_DIR/key.pem \
    -out $SSL_DIR/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Blacklight/OU=IT/CN=localhost"

chown -R $REGULAR_USER:$REGULAR_USER $SSL_DIR
chmod 600 $SSL_DIR/key.pem
chmod 644 $SSL_DIR/cert.pem

echo "✅ Self-signed SSL certificate created"
echo ""

# =============================================================================
# 7. Enable Docker Service
# =============================================================================
echo "🚀 Enabling Docker service..."
systemctl enable docker
systemctl start docker
echo "✅ Docker service enabled and started"
echo ""

# =============================================================================
# Setup Complete
# =============================================================================
echo "========================================="
echo "✅ VM Setup Complete!"
echo "========================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Log out and log back in for docker group to take effect:"
echo "   exit"
echo ""
echo "2. Clone your Blacklight repository to $APP_DIR:"
echo "   cd $APP_DIR"
echo "   git clone <your-repo-url> ."
echo ""
echo "3. Copy and configure environment file:"
echo "   cp .env.production.example .env.production"
echo "   vim .env.production  # Fill in your credentials"
echo ""
echo "4. Copy your GCS credentials:"
echo "   # Upload your gcs-credentials.json to server/gcs-credentials.json"
echo ""
echo "5. (OPTIONAL) Setup Let's Encrypt SSL for your domain:"
echo "   sudo certbot certonly --standalone -d your-domain.com"
echo "   # Then update nginx/nginx.conf to use:"
echo "   # /etc/letsencrypt/live/your-domain.com/fullchain.pem"
echo "   # /etc/letsencrypt/live/your-domain.com/privkey.pem"
echo ""
echo "6. Deploy the application:"
echo "   bash deploy.sh"
echo ""
echo "📝 Important Notes:"
echo "- Firewall is configured to allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)"
echo "- Self-signed SSL certificate created (replace with real certificate)"
echo "- Application directory: $APP_DIR"
echo "- Backup directory: /backups/blacklight"
echo ""
echo "🔒 Security Reminders:"
echo "- Change default passwords in .env.production"
echo "- Setup SSH key authentication and disable password login"
echo "- Configure fail2ban for additional security"
echo "- Regularly update the system: sudo apt-get update && sudo apt-get upgrade"
echo ""
