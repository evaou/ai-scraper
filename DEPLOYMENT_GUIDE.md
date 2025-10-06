# 🚀 AI Scraper - Complete Deployment Guide

> **Automated CI/CD deployment to Linode via GitHub Actions with Docker Compose V2**

## 📋 Quick Start Checklist

- [ ] Create Linode server ($5/month)
- [ ] Run server setup script
- [ ] Configure 8 GitHub secrets
- [ ] Push to main branch → Deploy! 🎉

---

## 🖥️ Step 1: Create & Configure Linode Server

### 1.1 Create Linode Instance
1. **Go to [Linode Cloud Manager](https://cloud.linode.com)**
2. **Create a new Linode:**
   - **Distribution:** Ubuntu 22.04 LTS
   - **Plan:** Nanode 1GB ($5/month) minimum
   - **Region:** Choose closest to your users
   - **Set root password**

### 1.2 Automated Server Setup
```bash
# SSH to your server
ssh root@YOUR_SERVER_IP

# Download and run setup script
wget https://raw.githubusercontent.com/evaou/ai-scraper/main/linode-setup.sh
chmod +x linode-setup.sh
./linode-setup.sh

# Validate setup
wget https://raw.githubusercontent.com/evaou/ai-scraper/main/validate-deployment.sh
chmod +x validate-deployment.sh
./validate-deployment.sh
```

### 1.3 Add SSH Key for GitHub Actions
```bash
# On your Linode server
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINAyLXMQfx5k/+DgaQrcfDVqosS3sTBbatsngjXHHZez github-actions-ai-scraper" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

---

## 🔐 Step 2: Configure GitHub Secrets

**Go to:** GitHub Repository → **Settings** → **Secrets and variables** → **Actions**

### Required Secrets (8 total):

| Secret Name | Value | Example |
|-------------|-------|---------|
| `LINODE_HOST` | Your Linode server IP | `192.168.1.100` |
| `LINODE_USER` | SSH username | `root` |
| `SSH_PRIVATE_KEY` | Private key content | See below ⬇️ |
| `POSTGRES_DB` | Database name | `scraper_prod` |
| `POSTGRES_USER` | Database username | `scraper_user` |
| `POSTGRES_PASSWORD` | Database password | Generate with script |
| `REDIS_PASSWORD` | Redis password | Generate with script |
| `JWT_SECRET_KEY` | JWT signing secret | Generate with script |

### Generate Secure Passwords
```bash
# Run locally to generate passwords
./generate-secrets.sh
```

### SSH Private Key Value
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACDQMi1zEH8eZP/g4GkK3Hw1aqLEt7EwW2rbJ4I1xx2XswAAAKDYHi652B4u
uQAAAAtzc2gtZWQyNTUxOQAAACDQMi1zEH8eZP/g4GkK3Hw1aqLEt7EwW2rbJ4I1xx2Xsw
AAAEB3GGRDw8BmMn4Fz1Fm5BYL64Yi6CMRfqkfiD2BEPETAdAyLXMQfx5k/+DgaQrcfDVq
osS3sTBbatsngjXHHZezAAAAGWdpdGh1Yi1hY3Rpb25zLWFpLXNjcmFwZXIBAgME
-----END OPENSSH PRIVATE KEY-----
```

---

## 🚀 Step 3: Deploy

### Option A: Automatic Deploy (Recommended)
```bash
git add .
git commit -m "🚀 Deploy to production"
git push origin main
```

### Option B: Manual Trigger
1. Go to **GitHub** → **Actions** tab
2. Click **"Deploy to Linode"** workflow  
3. Click **"Run workflow"** → **"Run workflow"**

---

## 📊 Step 4: Monitor Deployment

### 4.1 GitHub Actions Progress
- **Test Job** (~5-8 min): PostgreSQL + Redis + pytest
- **Build & Push** (~3-5 min): Docker images to GHCR
- **Deploy** (~2-3 min): Deploy to Linode server
- **Total Time**: ~10-15 minutes

### 4.2 Check Server Status
```bash
ssh root@YOUR_SERVER_IP
cd /opt/ai-scraper
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

### 4.3 Verify Deployment Success
```bash
# Test API endpoints
curl http://YOUR_SERVER_IP/api/v1/health/live
curl http://YOUR_SERVER_IP:8000/api/v1/docs
```

**✅ Success indicators:**
- All GitHub Actions jobs complete ✅
- Services show "Up" status in docker compose ps ✅  
- Health check returns 200 ✅
- API docs accessible ✅

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### 🔑 SSH Connection Fails
```bash
# Test connection locally
ssh -i ~/.ssh/github_actions_ai_scraper -v root@YOUR_SERVER_IP
```

#### 🐳 Docker Issues  
```bash
# Check Docker status
docker info
docker compose version

# Restart Docker if needed
sudo systemctl restart docker
```

#### 📊 Service Health Check Fails
```bash
# Check individual service logs
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs worker
docker compose -f docker-compose.prod.yml logs db
```

#### 🔄 Need to Rollback?
The deployment has **automatic rollback** built-in. Check GitHub Actions logs for rollback details.

---

## 🌐 Step 5: Domain & SSL (Optional)

### 5.1 Point Domain to Server
**DNS Configuration:**
- **A Record:** `@` → `YOUR_SERVER_IP` 
- **A Record:** `api` → `YOUR_SERVER_IP` (subdomain)

### 5.2 Add SSL Certificate  
```bash
# On your server
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com
```

---

## 📚 Post-Deployment

### Your API Endpoints:
- **🏥 Health:** `http://YOUR_SERVER_IP/api/v1/health/live`
- **📖 Docs:** `http://YOUR_SERVER_IP:8000/api/v1/docs`  
- **📊 Admin:** `http://YOUR_SERVER_IP:8000/api/v1/admin/stats`
- **🔍 Metrics:** `http://YOUR_SERVER_IP:8000/api/v1/admin/metrics`

### Recommended Next Steps:
1. **🔐 Set up API authentication** (if needed)
2. **📈 Configure monitoring** and alerts
3. **💾 Set up automated backups** 
4. **🔒 Enable HTTPS** with domain + SSL
5. **📊 Monitor performance** via `/admin/stats`

---

## ⚡ Technology Stack

- **🐳 Docker Compose V2** - Modern container orchestration
- **🔄 GitHub Actions** - CI/CD pipeline  
- **🐧 Ubuntu 22.04** - Server OS
- **☁️ Linode** - Cloud hosting ($5/month)
- **📦 GitHub Container Registry** - Docker image storage
- **🔒 SSH Keys** - Secure deployment authentication

---

## 🎯 Architecture Overview

```
GitHub Push → Actions → Test → Build → Deploy → Health Check
                ↓          ↓       ↓         ↓
            PostgreSQL  Docker   Linode   API Live
            Redis       Images   Server   ✅ Success
```

---

**🎉 Congratulations!** Your AI Scraper is now **production-ready** and automatically deployed! 

The system will now automatically deploy every time you push to the main branch. The deployment includes automatic rollback, health monitoring, and production-grade Docker Compose V2 orchestration.

---

*Need help? Check GitHub Actions logs or create an issue in the repository.*