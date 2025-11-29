# 🚀 Blacklight VM Deployment - Quick Start

Ready-to-deploy configuration for Blacklight application on a Virtual Machine.

## 📦 What's Included

This repository contains everything needed for production VM deployment:

- **`docker-compose.production.yml`** - Complete multi-service orchestration
- **`nginx/nginx.conf`** - Reverse proxy with SSL, security headers, caching
- **`.env.production.example`** - Environment configuration template
- **`setup-vm.sh`** - Automated VM initialization script
- **`deploy.sh`** - One-command deployment script
- **`backup.sh`** - Database and file backup automation
- **`DEPLOYMENT.md`** - Comprehensive deployment guide

## ⚡ Quick Deploy (3 Steps)

### 1️⃣ Setup VM

```bash
# SSH into your fresh Ubuntu VM
ssh your-user@VM-IP

# Clone and setup
cd /opt
sudo git clone <your-repo> blacklight
cd blacklight
sudo bash setup-vm.sh

# Log out and back in
exit && ssh your-user@VM-IP
```

### 2️⃣ Configure

```bash
cd /opt/blacklight

# Copy and edit environment
cp .env.production.example .env.production
vim .env.production  # Fill in your credentials

# Upload GCS credentials
# (On your local machine):
# scp gcs-credentials.json your-user@VM-IP:/opt/blacklight/server/
```

### 3️⃣ Deploy

```bash
cd /opt/blacklight
bash deploy.sh
```

🎉 **That's it!** Your application is now running!

## 🌐 Access Your Application

- **Portal**: `https://your-vm-ip/portal`
- **CentralD**: `https://your-vm-ip/centrald`
- **API**: `https://your-vm-ip/api`
- **Health Check**: `https://your-vm-ip/health`

## 📋 Requirements

**Hardware (Minimum):**
- 4 vCPUs
- 8 GB RAM
- 50 GB SSD

**External Services:**
- Google Gemini API Key
- Google Cloud Storage bucket + credentials
- SMTP credentials (Gmail, SendGrid, etc.)

## 🔧 Management Commands

```bash
# View logs
docker compose -f docker-compose.production.yml logs -f

# Restart services
docker compose -f docker-compose.production.yml restart

# Stop services
docker compose -f docker-compose.production.yml down

# Backup database
bash backup.sh
```

## 📚 Documentation

For detailed instructions, troubleshooting, and advanced configuration, see:

**[📖 DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide

## 🔐 Security Checklist

- [ ] Change `SECRET_KEY` in `.env.production`
- [ ] Change `POSTGRES_PASSWORD` in `.env.production`
- [ ] Update `ALLOWED_HOSTS` to your domain
- [ ] Update `CORS_ORIGINS` to your domain
- [ ] Setup Let's Encrypt SSL for production
- [ ] Configure SSH key authentication
- [ ] Setup automated backups (cron)

## 🆘 Support

**Common Issues:**

```bash
# Check if all services are running
docker compose -f docker-compose.production.yml ps

# View specific service logs
docker compose -f docker-compose.production.yml logs backend

# Rebuild and redeploy
bash deploy.sh
```

For more help, see the [Troubleshooting section](./DEPLOYMENT.md#troubleshooting) in DEPLOYMENT.md.

---

**Architecture:** Flask Backend + React Frontends (Portal & CentralD) + PostgreSQL (pgvector) + Redis + Nginx

**Deployment Model:** All-in-One Docker Compose on single VM
