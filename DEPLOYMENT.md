# AI Scraper - Production Deployment

Automated CI/CD deployment to Linode via GitHub Actions.

## Setup

### 1. Add GitHub Secrets

**Settings → Secrets and variables → Actions:**

| Secret | Value | Example |
|--------|-------|----------|
| `LINODE_HOST` | Your server IP | `192.168.1.100` |
| `LINODE_USER` | SSH username | `root` |
| `SSH_PRIVATE_KEY` | SSH private key content | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `POSTGRES_PASSWORD` | Database password | `secure_db_pass_123` |
| `REDIS_PASSWORD` | Redis password | `secure_redis_pass_456` |
| `JWT_SECRET_KEY` | JWT signing secret | `super_long_random_secret_key_here` |
| `DOMAIN_NAME` | Your domain (optional) | `api.yourdomain.com` |

### 2. Deploy

```bash
git push origin main
```

✨ **That's it!** GitHub Actions will automatically:
- Run tests
- Build Docker images  
- Deploy to your Linode server
- Run health checks

## Monitor

- **GitHub Actions**: Repository → Actions tab
- **Health Check**: `http://your-domain/health`
- **API Docs**: `http://your-domain/api/v1/docs`
- **Server Logs**: `ssh root@your-server && docker compose -f /opt/ai-scraper/docker-compose.prod.yml logs -f`

## Troubleshooting

**Deployment fails?**
```bash
# Check GitHub Actions logs first
# Then SSH to server and check:
ssh root@your-server
cd /opt/ai-scraper
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs
```

**Need to rollback?**
```bash
ssh root@your-server
cd /opt/ai-scraper
./scripts/deploy.sh  # Has automatic rollback on failure
```
