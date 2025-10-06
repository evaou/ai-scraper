# 🚀 Complete Linode Deployment Setup Guide

## Step 1: Create & Configure Your Linode Server

### 1.1 Create Linode Instance
1. Go to [Linode Cloud Manager](https://cloud.linode.com)
2. Create a new Linode:
   - **Distribution:** Ubuntu 22.04 LTS
   - **Region:** Choose closest to your users
   - **Linode Plan:** Nanode 1GB ($5/month) or higher
   - **Root Password:** Set a strong password
   - **SSH Keys:** Add your public key (optional but recommended)

### 1.2 Set Up Server
1. SSH to your server: `ssh root@YOUR_SERVER_IP`
2. Copy and run the setup script:

```bash
# Copy the linode-setup.sh script to your server and run:
chmod +x linode-setup.sh
./linode-setup.sh
```

### 1.3 Add SSH Key for GitHub Actions
```bash
# On your Linode server:
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINAyLXMQfx5k/+DgaQrcfDVqosS3sTBbatsngjXHHZez github-actions-ai-scraper" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## Step 2: Configure GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### 2.1 Server Connection Secrets

| Secret Name | Value | Example |
|-------------|-------|---------|
| `LINODE_HOST` | Your Linode server IP | `192.168.1.100` |
| `LINODE_USER` | SSH username | `root` |
| `SSH_PRIVATE_KEY` | Private key content | Copy entire private key below ⬇️ |

**SSH_PRIVATE_KEY value:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACDQMi1zEH8eZP/g4GkK3Hw1aqLEt7EwW2rbJ4I1xx2XswAAAKDYHi652B4u
uQAAAAtzc2gtZWQyNTUxOQAAACDQMi1zEH8eZP/g4GkK3Hw1aqLEt7EwW2rbJ4I1xx2Xsw
AAAEB3GGRDw8BmMn4Fz1Fm5BYL64Yi6CMRfqkfiD2BEPETAdAyLXMQfx5k/+DgaQrcfDVq
osS3sTBbatsngjXHHZezAAAAGWdpdGh1Yi1hY3Rpb25zLWFpLXNjcmFwZXIBAgME
-----END OPENSSH PRIVATE KEY-----
```

### 2.2 Application Secrets

Generate strong passwords:
```bash
# Generate secure passwords (run locally)
openssl rand -base64 16  # For database password
openssl rand -base64 16  # For Redis password  
openssl rand -base64 32  # For JWT secret
```

| Secret Name | Value | Example |
|-------------|-------|---------|
| `POSTGRES_DB` | Database name | `scraper_prod` |
| `POSTGRES_USER` | Database username | `scraper_user` |
| `POSTGRES_PASSWORD` | Database password | `generated_password_123` |
| `REDIS_PASSWORD` | Redis password | `generated_redis_pass_456` |
| `JWT_SECRET_KEY` | JWT signing secret | `super_long_random_jwt_secret_key` |

## Step 3: Trigger Deployment

### 3.1 Test SSH Connection First
```bash
# Test SSH connection locally:
ssh -i ~/.ssh/github_actions_ai_scraper root@YOUR_SERVER_IP
```

### 3.2 Trigger Deployment
Once all secrets are configured, deploy by:

**Option A: Push to main branch**
```bash
git add .
git commit -m "🚀 Trigger deployment to Linode"
git push origin main
```

**Option B: Manual trigger**
1. Go to GitHub → Your repo → **Actions**
2. Click "Deploy to Linode" workflow
3. Click "Run workflow" → "Run workflow"

## Step 4: Monitor Deployment

### 4.1 Watch GitHub Actions
- Go to **Actions** tab in your GitHub repo
- Click on the running workflow
- Monitor each job: Test → Build & Push → Deploy

### 4.2 Check Server Status
```bash
# SSH to your server and check:
ssh root@YOUR_SERVER_IP
cd /opt/ai-scraper
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### 4.3 Verify Deployment
```bash
# Test the API:
curl http://YOUR_SERVER_IP/api/v1/health/live
curl http://YOUR_SERVER_IP:8000/api/v1/health/live
```

## Step 5: Set Up Domain (Optional)

### 5.1 Configure DNS
Point your domain to your Linode server IP:
- **A Record:** `@` → `YOUR_SERVER_IP`
- **A Record:** `api` → `YOUR_SERVER_IP` (optional subdomain)

### 5.2 Configure SSL (Optional)
```bash
# On your server:
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 🎯 Expected Results

### Successful Deployment Flow:
1. ✅ **Test Job** - Runs tests with PostgreSQL/Redis
2. ✅ **Build & Push** - Builds Docker images 
3. ✅ **Deploy** - Deploys to your Linode server
4. ✅ **Health Check** - Verifies deployment success

### After Deployment:
- **API Available:** `http://YOUR_SERVER_IP:8000/api/v1/docs`
- **Health Check:** `http://YOUR_SERVER_IP/api/v1/health/live`
- **Admin Stats:** `http://YOUR_SERVER_IP:8000/api/v1/admin/stats`

## 🚨 Troubleshooting

### Common Issues:

#### 1. SSH Connection Fails
```bash
# Test SSH key:
ssh -i ~/.ssh/github_actions_ai_scraper -v root@YOUR_SERVER_IP
```

#### 2. Docker Login Fails
- Check `GITHUB_TOKEN` secret exists (should be automatic)
- Verify GitHub Container Registry permissions

#### 3. Service Health Check Fails
```bash
# Check logs:
docker-compose -f docker-compose.prod.yml logs api
docker-compose -f docker-compose.prod.yml logs worker
```

#### 4. Deployment Rollback
The workflow has automatic rollback - check Actions logs for details.

## 🎉 Success Indicators

When deployment is successful, you'll see:
- ✅ All GitHub Actions jobs complete
- ✅ Services running: `docker-compose ps` shows "Up" status
- ✅ Health check returns 200: `curl http://YOUR_SERVER_IP/api/v1/health/live`
- ✅ API docs accessible: `http://YOUR_SERVER_IP:8000/api/v1/docs`

## 📝 Next Steps After Deployment

1. **Set up monitoring** - Check `/api/v1/admin/stats` endpoint
2. **Configure backups** - Set up database and data backups
3. **Domain & SSL** - Point your domain and add HTTPS
4. **API Keys** - Set up API authentication if needed
5. **Monitoring** - Set up uptime monitoring

Your AI Scraper is now live and ready for production use! 🚀