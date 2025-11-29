# Blacklight Production Deployment Guide

Complete guide for deploying Blacklight application on a Virtual Machine using **Deployment Option 1: All-in-One Docker Compose**.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial VM Setup](#initial-vm-setup)
3. [Configuration](#configuration)
4. [Deployment](#deployment)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)
9. [Backup and Restore](#backup-and-restore)

---

## Prerequisites

### Hardware Requirements

**Minimum:**
- 4 vCPUs
- 8 GB RAM
- 50 GB SSD Storage
- Public IP address

**Recommended:**
- 8 vCPUs
- 16 GB RAM
- 100 GB SSD Storage
- Public IP address with DNS configured

### External Services

Before deployment, ensure you have:

1. **Google Gemini API Key**
   - Sign up at: https://makersuite.google.com/app/apikey
   - Required for AI resume parsing and job matching

2. **Google Cloud Storage**
   - Create a GCS bucket for file uploads
   - Download service account credentials JSON
   - Required for resume and document storage

3. **SMTP Credentials**
   - Gmail, SendGrid, or other SMTP service
   - Required for email notifications

4. **Inngest Account** (Optional)
   - Sign up at: https://www.inngest.com/
   - For production background job processing
   - Can use dev mode without account

---

## Initial VM Setup

### Step 1: Provision VM

Choose your cloud provider and create a VM:

**Google Cloud Platform:**
```bash
gcloud compute instances create blacklight-vm \
  --machine-type=n1-standard-4 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --tags=http-server,https-server
```

**AWS EC2:**
```bash
aws ec2 run-instances \
  --image-id ami-xxxxxxxx \
  --instance-type t3.xlarge \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxx \
  --block-device-mappings DeviceName=/dev/sda1,Ebs={VolumeSize=100}
```

**DigitalOcean:**
- Create Droplet: Ubuntu 22.04 LTS
- Size: 8 GB RAM / 4 vCPUs / 100 GB SSD
- Add tags: `blacklight`, `production`

### Step 2: SSH into VM

```bash
ssh your-user@VM-IP-ADDRESS
```

### Step 3: Run Setup Script

```bash
# Update system
sudo apt-get update

# Clone repository
cd /opt
sudo git clone https://github.com/your-org/blacklight.git blacklight
cd blacklight

# Run VM setup script (installs Docker, configures firewall, etc.)
sudo bash setup-vm.sh
```

The setup script will:
- ✅ Install Docker and Docker Compose
- ✅ Configure firewall (UFW) for ports 22, 80, 443
- ✅ Optimize system settings for production
- ✅ Create application directories
- ✅ Generate self-signed SSL certificate
- ✅ Enable Docker service

**Important:** Log out and log back in after setup for Docker group to take effect:
```bash
exit
ssh your-user@VM-IP-ADDRESS
```

---

## Configuration

### Step 1: Configure Environment Variables

```bash
cd /opt/blacklight

# Copy environment template
cp .env.production.example .env.production

# Edit configuration
vim .env.production
```

**Required Configuration:**

```bash
# Security - CHANGE THESE!
SECRET_KEY=<generate-strong-random-key>
POSTGRES_PASSWORD=<strong-password>

# Google Gemini AI
GEMINI_API_KEY=<your-gemini-api-key>
GOOGLE_API_KEY=<your-google-api-key>

# Google Cloud Storage
GCS_BUCKET_NAME=<your-bucket-name>
GCS_PROJECT_ID=<your-project-id>

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<your-email@gmail.com>
SMTP_PASSWORD=<your-app-password>
SMTP_FROM_EMAIL=<your-email@gmail.com>

# Domain / URLs (update after you have a domain)
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
CORS_ORIGINS=https://your-domain.com
FRONTEND_BASE_URL=https://your-domain.com
```

**Generate Strong Secret Key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2: Upload GCS Credentials

```bash
# Upload your service account JSON to the server
# On your local machine:
scp /path/to/gcs-credentials.json your-user@VM-IP:/opt/blacklight/server/gcs-credentials.json

# On the VM, verify it exists:
ls -la /opt/blacklight/server/gcs-credentials.json
```

### Step 3: SSL Certificate (Optional but Recommended)

**Option A: Let's Encrypt (Recommended for Production)**

If you have a domain name configured:

```bash
# Stop nginx if running
sudo docker compose -f docker-compose.production.yml down nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Certificates will be at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem

# Update nginx/nginx.conf to use these paths
# Then deploy normally
```

**Option B: Self-Signed Certificate (Already Created)**

The setup script already created a self-signed certificate at `nginx/ssl/`. This works but browsers will show a warning.

---

## Deployment

### Deploy the Application

```bash
cd /opt/blacklight

# Run deployment script
bash deploy.sh
```

The deployment script will:
1. ✅ Check prerequisites (Docker, environment files)
2. ✅ Validate configuration
3. ✅ Build Docker images (10-15 minutes on first run)
4. ✅ Start database and wait for it to be ready
5. ✅ Run database migrations
6. ✅ Start all services (nginx, backend, frontends, redis)
7. ✅ Perform health checks
8. ✅ Display access URLs and status

**Expected Output:**
```
✅ Deployment Complete!
📊 Container Status:
NAME                     STATUS         PORTS
blacklight-nginx         Up (healthy)   80/tcp, 443/tcp
blacklight-backend       Up (healthy)   
blacklight-portal        Up (healthy)
blacklight-centrald      Up (healthy)
blacklight-postgres      Up (healthy)   5432/tcp
blacklight-redis         Up (healthy)   6379/tcp
```

---

## Post-Deployment Verification

### 1. Check Services Status

```bash
# View running containers
docker compose -f docker-compose.production.yml ps

# View logs
docker compose -f docker-compose.production.yml logs -f
```

### 2. Test Endpoints

```bash
# Health check
curl http://localhost/health
# Expected: healthy

# Backend API
curl http://localhost/api/health
# Expected: {"status":"healthy",...}

# Portal frontend
curl -I http://localhost/portal
# Expected: HTTP/1.1 200 OK

# CentralD frontend
curl -I http://localhost/centrald
# Expected: HTTP/1.1 200 OK
```

### 3. Access Web Interfaces

Open in your browser:
- **Portal**: `http://VM-IP/portal` or `https://your-domain.com/portal`
- **CentralD**: `http://VM-IP/centrald` or `https://your-domain.com/centrald`
- **API Docs**: `http://VM-IP/api` or `https://your-domain.com/api`

### 4. Test AI Features

1. Upload a resume via Portal
2. Verify AI parsing works (check backend logs)
3. Test job matching functionality

### 5. Test Email Notifications

1. Create a candidate invitation
2. Check logs for email sending
3. Verify email delivery

---

## Monitoring and Maintenance

### View Logs

```bash
# All services
docker compose -f docker-compose.production.yml logs -f

# Specific service
docker compose -f docker-compose.production.yml logs -f backend
docker compose -f docker-compose.production.yml logs -f portal
docker compose -f docker-compose.production.yml logs -f nginx
```

### Monitor Resources

```bash
# Container stats
docker stats

# System resources
htop

# Disk usage
df -h
```

### Management Commands

```bash
# Restart services
docker compose -f docker-compose.production.yml restart

# Restart specific service
docker compose -f docker-compose.production.yml restart backend

# Stop all services
docker compose -f docker-compose.production.yml down

# Stop and remove volumes (WARNING: deletes data)
docker compose -f docker-compose.production.yml down -v
```

### Database Management (Optional)

Start pgAdmin for database management:

```bash
# Start with tools profile
docker compose -f docker-compose.production.yml --profile tools up -d

# Access pgAdmin at: http://VM-IP:5050
# Login: admin@blacklight.com / password from .env.production
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose -f docker-compose.production.yml logs service-name

# Check container status
docker compose -f docker-compose.production.yml ps

# Rebuild specific service
docker compose -f docker-compose.production.yml build --no-cache service-name
docker compose -f docker-compose.production.yml up -d service-name
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker compose -f docker-compose.production.yml logs postgres

# Test connection
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -d blacklight

# Reset database (WARNING: deletes all data)
docker compose -f docker-compose.production.yml down postgres
docker volume rm blacklight_postgres_data
bash deploy.sh
```

### Port Already in Use

```bash
# Find process using port 80
sudo lsof -i :80

# Kill process
sudo kill -9 <PID>
```

### Out of Disk Space

```bash
# Clean Docker system
docker system prune -a --volumes

# Check disk usage
df -h
du -sh /var/lib/docker
```

### SSL Certificate Issues

```bash
# Verify certificate
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Test SSL connection
openssl s_client -connect localhost:443
```

---

## Security Best Practices

### 1. SSH Hardening

```bash
# Disable password authentication
sudo vim /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd

# Use SSH keys only
ssh-copy-id your-user@VM-IP
```

### 2. Firewall Configuration

```bash
# Check firewall status
sudo ufw status

# Allow specific IP only
sudo ufw allow from YOUR-IP to any port 22
```

### 3. Regular Updates

```bash
# Update system packages weekly
sudo apt-get update && sudo apt-get upgrade -y

# Update Docker images
cd /opt/blacklight
docker compose -f docker-compose.production.yml pull
bash deploy.sh
```

### 4. Secrets Management

- Never commit `.env.production` to git
- Use environment variables for sensitive data
- Rotate passwords regularly
- Use strong, unique passwords

### 5. Install Fail2Ban

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Backup and Restore

### Automated Backups

```bash
# Run backup manually
bash backup.sh

# Schedule daily backups at 2 AM
crontab -e
# Add: 0 2 * * * cd /opt/blacklight && bash backup.sh >> /var/log/blacklight-backup.log 2>&1
```

Backups are stored in `/backups/blacklight/` and optionally uploaded to Google Cloud Storage.

### Restore from Backup

```bash
# 1. Stop application
docker compose -f docker-compose.production.yml down

# 2. Start database only
docker compose -f docker-compose.production.yml up -d postgres
sleep 10

# 3. Restore database
gunzip -c /backups/blacklight/blacklight_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.production.yml exec -T postgres \
  psql -U postgres -d blacklight

# 4. Restore uploads (if applicable)
docker compose -f docker-compose.production.yml exec -T backend \
  tar xzf - < /backups/blacklight/blacklight_backup_YYYYMMDD_HHMMSS_uploads.tar.gz

# 5. Restart application
docker compose -f docker-compose.production.yml up -d
```

---

## Updating the Application

```bash
cd /opt/blacklight

# Pull latest code
git pull origin main

# Rebuild and redeploy
bash deploy.sh
```

---

## Scaling Considerations

### Horizontal Scaling

For high-traffic scenarios, consider:
- Load balancer in front of multiple VMs
- External managed PostgreSQL (Cloud SQL, RDS)
- External Redis (Memoria Store, ElastiCache)
- CDN for static assets

### Vertical Scaling

Upgrade VM resources as needed:
- CPU: 8-16 vCPUs for high concurrency
- RAM: 32 GB+ for large datasets
- Disk: SSD with 200+ IOPS

---

## Support

For issues or questions:
1. Check logs: `docker compose -f docker-compose.production.yml logs`
2. Review troubleshooting section above
3. Check backend README: `server/README.md`
4. Contact development team

---

## Quick Reference

**Common Commands:**
```bash
# Deploy
bash deploy.sh

# View logs
docker compose -f docker-compose.production.yml logs -f

# Restart
docker compose -f docker-compose.production.yml restart

# Stop
docker compose -f docker-compose.production.yml down

# Backup
bash backup.sh

# Check status
docker compose -f docker-compose.production.yml ps
```

**Access URLs:**
- Portal: `https://your-domain.com/portal`
- CentralD: `https://your-domain.com/centrald`
- API: `https://your-domain.com/api`
- Health: `https://your-domain.com/health`
- pgAdmin: `http://VM-IP:5050`
- Redis UI: `http://VM-IP:8081`
