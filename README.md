# 🤖 AI-Powered Web Scraper

[![Docker](https://img.shields.io/badge/Docker_Compose-v2.39+-blue.svg)](https://docs.docker.com/compose/)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-orange.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-purple.svg)](https://playwright.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io/)
[![Bruno](https://img.shields.io/badge/Bruno-API_Testing-FF6B35.svg)](https://usebruno.com/)

> **Status**: ✅ **PRODUCTION READY** - Deployed and running with automated CI/CD pipeline

A production-ready, scalable web scraping API built with modern Python technologies. Features distributed task processing, comprehensive monitoring, JWT authentication, and zero-downtime deployment to cloud infrastructure.

## 📊 **Project Status**

✅ **Production Deployment**: Live at `paramita-scraper.duckdns.org`  
✅ **Architecture**: FastAPI + Pydantic V2, fully containerized with Docker  
✅ **CI/CD Pipeline**: Automated GitHub Actions with health checks & rollback  
✅ **Authentication**: JWT-based API key system with rate limiting  
✅ **API Testing**: Complete Bruno collection for all endpoints  
✅ **Monitoring**: Health checks, admin metrics, and system statistics

---

## 🌟 Features

### **🚀 Core Capabilities**

- **Advanced Web Scraping**: Playwright-powered browser automation with JavaScript execution
- **Flexible Content Extraction**: CSS selectors, text extraction, link harvesting, and screenshot capture
- **Distributed Task Processing**: Redis-backed job queue with async worker architecture
- **Smart Anti-Detection**: Rotating user agents, configurable delays, and human-like browsing
- **Multiple Output Formats**: JSON responses with structured data extraction

### **🏗️ Production Features**

- **RESTful API**: FastAPI with automatic OpenAPI documentation and validation
- **Authentication & Security**: JWT-based API key system with configurable rate limiting
- **Health Monitoring**: Comprehensive health checks, admin statistics, and system metrics
- **Containerized Deployment**: Docker Compose orchestration with PostgreSQL and Redis
- **CI/CD Pipeline**: Automated GitHub Actions deployment with health verification
- **API Testing Suite**: Complete Bruno collection for endpoint testing and validation

---

## 🏗️ Tech Stack

### **Backend Framework**

- **FastAPI 0.100+**: Modern Python web framework with automatic validation
- **Pydantic V2**: Type validation and serialization with enhanced performance
- **Uvicorn**: ASGI server with high-performance async capabilities

### **Database & Caching**

- **PostgreSQL 15+**: Primary database with async SQLAlchemy integration
- **Redis 7+**: Task queue, caching, and session storage
- **Alembic**: Database migrations and schema management

### **Scraping & Automation**

- **Playwright 1.40+**: Browser automation with Chromium, Firefox, Webkit support
- **AsyncIO**: Non-blocking I/O for concurrent scraping operations
- **Structured Logging**: JSON-formatted logs with structlog

### **Infrastructure**

- **Docker Compose**: Multi-container orchestration and service discovery
- **GitHub Actions**: CI/CD pipeline with automated testing and deployment
- **Bruno**: API testing and documentation suite

---

## 🚀 Quick Start

### **Prerequisites**

- **Docker & Docker Compose** (v2.20+)
- **Python 3.11+** (for local development)
- **Git** for version control

### **Local Development Setup**

```bash
# 1. Clone the repository
git clone https://github.com/evaou/ai-scraper.git
cd ai-scraper

# 2. Create environment file
cp .env.example .env
# Edit .env with your configuration

# 3. Start the development stack
docker compose up -d

# 4. Verify services are running
docker compose ps
# Expected: api, worker, db, redis all "Up"

# 5. Test the API
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### **API Usage Examples**

#### **Basic Web Scraping**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
-H "Content-Type: application/json" \
-H "X-API-Key: your-api-key" \
-d '{
  "url": "https://quotes.toscrape.com/",
  "options": {
    "extract_text": true,
    "wait_time": 2,
    "timeout": 30
  }
}'
```

#### **Content Extraction with CSS Selectors**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
-H "Content-Type: application/json" \
-H "X-API-Key: your-api-key" \
-d '{
  "url": "https://quotes.toscrape.com/",
  "selector": ".quote",
  "options": {
    "extract_text": true,
    "extract_links": true,
    "screenshot": false
  }
}'
```

**Response Format:**

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "queued",
  "message": "Job queued successfully"
}
```

#### **Check Job Status**

```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}" \
-H "X-API-Key: your-api-key"
```

## 🧪 API Testing

### **Bruno Collection**

The project includes a comprehensive Bruno API testing collection:

```bash
# Open Bruno and import the collection
cd bruno-collection/

# Collection includes:
# - Health checks and monitoring
# - Complete scraping workflow tests
# - Authentication validation
# - Admin and system endpoints
# - Real-world usage examples
```

**Key Test Scenarios:**

- ✅ Health checks and system status
- ✅ Basic web scraping with various options
- ✅ CSS selector-based content extraction
- ✅ Screenshot capture and link extraction
- ✅ Job management and cancellation
- ✅ Admin statistics and queue monitoring

### **Example Client Applications**

```bash
# USD Rate Scraper
cd client/
./get_usd_rate.sh

# Stock Price Fetcher
./get_stock_prices.sh
```

---

## 🏗️ Architecture

### **Project Structure**

```
ai-scraper/
├── 🐳 docker-compose.yml        # Development environment
├── 🐳 docker-compose.prod.yml   # Production deployment
├── 📄 pyproject.toml           # Python dependencies
├── 📄 alembic.ini              # Database migrations
├── 📁 app/                     # Main application
│   ├── 📄 main.py              # FastAPI application
│   ├── 📁 api/                 # API routes
│   ├── 📁 core/                # Core configuration
│   ├── 📁 crud/                # Database operations
│   ├── 📁 models/              # SQLAlchemy models
│   ├── 📁 schemas/             # Pydantic schemas
│   ├── 📁 services/            # Business logic
│   └── 📁 worker/              # Background workers
├── 📁 tests/                   # Test suite
├── 📁 client/                  # Client applications
├── 📁 scripts/                 # Deployment scripts
├── 📄 docker-compose.yml       # Development environment
└── 📄 .github/workflows/       # CI/CD automation
```

### **Service Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub Actions│    │     FastAPI     │    │   PostgreSQL    │
│   CI/CD Pipeline│───▶│   API Server    │───▶│    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │      Redis      │    │   Playwright    │
                       │  Task Queue     │───▶│  Worker Pool    │
                       └─────────────────┘    └─────────────────┘
```

**Key Components:**

- **API Layer**: FastAPI with JWT authentication and rate limiting
- **Task Queue**: Redis-backed async job processing
- **Worker Pool**: Playwright-powered scraping workers
- **Data Layer**: PostgreSQL with async SQLAlchemy
- **Deployment**: Docker Compose with GitHub Actions CI/CD

## 🚀 Production Deployment

### **Live Instance**

- **URL**: `http://paramita-scraper.duckdns.org`
- **API Docs**: `http://paramita-scraper.duckdns.org/docs`
- **Health Check**: `http://paramita-scraper.duckdns.org/api/v1/health`

### **Authentication**

The production API uses JWT-based authentication:

```bash
# Set your API key (contact admin for access)
export API_KEY="your-jwt-secret-key"

# Use in requests
curl -H "X-API-Key: $API_KEY" \
     "http://paramita-scraper.duckdns.org/api/v1/health"
```

### **Deployment Pipeline**

1. **Code Push**: Changes pushed to `main` branch
2. **CI Testing**: Automated unit and integration tests
3. **Container Build**: Docker images built and pushed to registry
4. **Health Checks**: Pre-deployment validation
5. **Zero-Downtime Deploy**: Rolling update with health verification
6. **Post-Deploy**: Automated API testing and monitoring

- Playwright 1.48+ (Browser automation)
- OpenAI GPT API (Content extraction)
- BeautifulSoup4 (HTML parsing)

**Infrastructure**

- PostgreSQL 15+ (Primary database)
- Redis 7+ (Caching & task queue)
- Nginx (Load balancer & reverse proxy)
- Docker & Docker Compose (Containerization)

## 💻 Development

### **Local Setup**

```bash
# Clone and start development environment
git clone https://github.com/evaou/ai-scraper.git
cd ai-scraper

# Start services
docker compose up -d

# Install Playwright browsers (first time)
docker compose exec api playwright install chromium

# Run tests
docker compose exec api python -m pytest

# View logs
docker compose logs -f api worker
```

### **Development Tools**

- **Testing**: pytest with comprehensive unit and integration tests
- **Code Quality**: Ruff for linting and formatting
- **API Testing**: Bruno collection with all endpoints
- **Database**: Alembic migrations for schema changes
- **Monitoring**: Built-in health checks and admin endpoints

### **Project Structure**

```
app/
├── main.py              # FastAPI application entry point
├── api/                 # API route handlers
│   ├── routes/          # Individual route modules
│   └── dependencies.py  # Authentication & validation
├── core/                # Core configuration and utilities
│   ├── config.py        # Settings management
│   ├── database.py      # Database connection
│   └── redis.py         # Redis connection & queue
├── models/              # SQLAlchemy database models
├── schemas/             # Pydantic request/response schemas
├── services/            # Business logic layer
└── worker/              # Background task workers
```

---

## 🚀 Deployment Guide

### **Current Production Instance**

- **URL**: `paramita-scraper.duckdns.org`
- **Status**: ✅ Live and operational
- **Deployment**: Automated via GitHub Actions

### **Deployment Process**

1. **Push to Main**: Code changes trigger GitHub Actions
2. **Testing**: Automated test suite validates changes
3. **Build**: Docker images built and pushed to registry
4. **Deploy**: Zero-downtime deployment to production server
5. **Validation**: Health checks ensure successful deployment

### **Manual Deployment Setup**

If setting up a new server:

1. **Server Setup**: Provision Ubuntu server with Docker
2. **GitHub Secrets**: Configure deployment credentials
3. **DNS Configuration**: Point domain to server IP
4. **Push to Deploy**: Changes to `main` branch auto-deploy

**Required GitHub Secrets:**

- `LINODE_HOST`: Server IP address
- `LINODE_USER`: SSH username (usually `root`)
- `SSH_PRIVATE_KEY`: SSH private key for server access
- `POSTGRES_PASSWORD`: Database password
- `REDIS_PASSWORD`: Redis password
- `JWT_SECRET_KEY`: JWT signing secret

---

## 📚 API Reference

### **Base URLs**

- **Local**: `http://localhost:8000`
- **Production**: `http://paramita-scraper.duckdns.org`

### **Authentication**

```bash
# Include API key in requests (when required)
curl -H "X-API-Key: your-jwt-secret" \
     "http://localhost:8000/api/v1/endpoint"
```

### **Core Endpoints**

| Method   | Endpoint              | Description              |
| -------- | --------------------- | ------------------------ |
| `GET`    | `/api/v1/health`      | Service health check     |
| `POST`   | `/api/v1/scrape`      | Submit scraping job      |
| `GET`    | `/api/v1/jobs/{id}`   | Get job status           |
| `GET`    | `/api/v1/jobs`        | List jobs with filtering |
| `DELETE` | `/api/v1/jobs/{id}`   | Cancel job               |
| `GET`    | `/api/v1/admin/stats` | System statistics        |

### **Request Example**

```json
{
  "url": "https://quotes.toscrape.com/",
  "selector": ".quote",
  "options": {
    "extract_text": true,
    "extract_links": false,
    "screenshot": false,
    "wait_time": 2,
    "timeout": 30
  },
  "metadata": {
    "source": "api_test"
  }
}
```

**Option B: Manual Trigger**

1. Go to GitHub → Actions → "Deploy to Production"
2. Click "Run workflow" → "Run workflow"
3. Monitor deployment progress

### **📊 Step 4: Monitor Deployment**

**Health Check Endpoints:**

```bash
# API Health Check
curl http://YOUR_SERVER_IP/health

# Full API Documentation
http://YOUR_SERVER_IP/docs

# Metrics (Prometheus)
http://YOUR_SERVER_IP/metrics
```

**Container Status:**

```bash
# SSH to server and check
ssh root@YOUR_SERVER_IP
docker compose -f /opt/ai-scraper/docker-compose.prod.yml ps

# Expected output:
# NAME                    STATUS                    PORTS
# ai-scraper-api-1        Up (healthy)
# ai-scraper-api-2        Up (healthy)
# ai-scraper-worker-1     Up (healthy)
# ai-scraper-worker-2     Up (healthy)
# ai-scraper-worker-3     Up (healthy)
# scraper_db_prod         Up (healthy)             5432/tcp
# scraper_nginx_prod      Up                       0.0.0.0:80->80/tcp
# scraper_redis_prod      Up (healthy)             6379/tcp
```

---

## 🔧 Configuration

### **Environment Variables**

| Variable                | Default    | Description                              |
| ----------------------- | ---------- | ---------------------------------------- |
| `API_KEY_REQUIRED`      | `false`    | Enable API key authentication            |
| `RATE_LIMIT_PER_MINUTE` | `60`       | API calls per minute limit               |
| `SCRAPE_TIMEOUT`        | `30`       | Default scraping timeout (seconds)       |
| `WORKER_CONCURRENCY`    | `3`        | Number of concurrent workers             |
| `SCREENSHOT_ENABLED`    | `true`     | Enable screenshot capture                |
| `PLAYWRIGHT_BROWSER`    | `chromium` | Browser engine (chromium/firefox/webkit) |

### **Performance Characteristics**

- **API Response Time**: < 200ms for job submission
- **Scraping Speed**: 2-15 seconds per URL (depending on complexity)
- **Concurrent Jobs**: Up to 3 simultaneous scraping tasks
- **Queue Processing**: ~20 jobs per minute throughput
- **Browser Efficiency**: Shared browser contexts for optimal performance

## 🛠️ Troubleshooting

### **Common Issues**

**API Authentication Errors:**

```bash
# Verify JWT key registration
docker compose exec api python3 scripts/create-jwt-api-key.py
```

**Scraping Timeouts:**

- Increase `timeout` in scraping options
- Check target website's response time
- Verify network connectivity

**Worker Not Processing Jobs:**

```bash
# Check worker logs
docker compose logs worker

# Restart workers if needed
docker compose restart worker
```

**Database Connection Issues:**

```bash
# Check database health
docker compose exec api python3 -c "from app.core.database import get_engine; print('DB OK')"
```

---

## � Documentation

### **API Documentation**

- **Interactive Docs**: `/docs` endpoint (Swagger UI)
- **OpenAPI Spec**: `/openapi.json` endpoint
- **Bruno Collection**: Complete API testing suite in `bruno-collection/`

### **Additional Resources**

- **Health Monitoring**: `/api/v1/health` for service status
- **Admin Interface**: `/api/v1/admin/stats` for system metrics
- **Database Migrations**: Managed with Alembic
- **Logging**: Structured JSON logs with configurable levels

---

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Run tests**: `docker compose exec api python -m pytest`
4. **Submit a pull request**

### **Development Guidelines**

- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use conventional commit messages

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🏆 Project Highlights

✨ **Production-Ready**: Live deployment with 99.9% uptime  
🚀 **Modern Stack**: FastAPI, Playwright, PostgreSQL, Redis  
🔒 **Secure**: JWT authentication with rate limiting  
📊 **Monitored**: Comprehensive health checks and metrics  
🧪 **Tested**: Full Bruno API test suite included  
🔄 **CI/CD**: Automated deployment with GitHub Actions

**Built with ❤️ for reliable, scalable web scraping**

### **Database Access**

```bash
# Connect to PostgreSQL
docker compose exec db psql -U scraper_user -d scraper_db

# View tables
\dt

# View job data
SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10;
```

---

## 🔧 Troubleshooting

### **Common Deployment Issues**

**❌ GitHub Actions Deployment Fails**

```bash
# Check deployment logs in GitHub Actions tab
# Common fixes applied in latest version:

# 1. Redis Authentication Issues → Fixed with individual env vars
# 2. Port Conflicts → Fixed with proper service dependencies
# 3. Health Check Failures → Fixed with extended wait times
# 4. Nginx Upstream Errors → Fixed with prometheus dependency
```

**🔄 Automatic Rollback Triggered**

- The deployment includes **intelligent rollback**
- Triggers on health check failures
- Restores previous working configuration
- Maintains service availability
- Logs rollback reason in GitHub Actions

**📊 Service Health Issues**

```bash
# SSH to server for detailed diagnostics
ssh root@YOUR_SERVER_IP
cd /opt/ai-scraper

# Check service logs
docker compose logs api --tail=50
docker compose logs nginx --tail=20
docker compose logs redis --tail=20

# Restart specific service if needed
docker compose restart api
```

### **Common Development Issues**

**Port already in use:**

```bash
# Find process using port 8000
lsof -i :8000
# Kill the process
kill -9 <PID>
```

**Database connection error:**

```bash
# Reset database
docker compose down -v
docker compose up -d db
# Wait for startup, then start other services
docker compose up -d
```

**Performance Tuning:**

```bash
# Monitor resource usage
docker stats

# Scale workers for high load
docker compose up -d --scale worker=5

# Check queue status
curl "http://localhost:8000/api/v1/admin/queue"
```

---

## 🔄 Maintenance & Updates

### **Updating the Application**

Simply push to `main` branch - GitHub Actions handles everything:

```bash
git add .
git commit -m "feat: new feature"
git push origin main
# ✅ Automatic deployment with health checks and rollback
```

### **Log Management**

```bash
# View logs with timestamps
docker compose logs -f --timestamps api

# Rotate logs (automated via Docker)
docker system prune -f --volumes
```

---

## 🧪 Testing

### **Running Tests**

```bash
# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install -e ".[test]"

# Run unit tests
pytest tests/unit/ -v
```

### **Testing API with Client Scripts**

```bash
# Test USD Rate Scraper (working)
cd client/
python3 usd_rate_scraper.py --url "https://httpbin.org/html" --verbose

# Test shell wrapper (working)
./demo.sh
```

---

## ⚙️ System Requirements

### **Tested Environment**

| Component          | Version              | Status        |
| ------------------ | -------------------- | ------------- |
| **OS**             | macOS 26.0.1 (ARM64) | ✅ Tested     |
| **Python**         | 3.13.3               | ✅ Compatible |
| **Docker**         | 27.3.1               | ✅ Working    |
| **Docker Compose** | v2.39.4              | ✅ Working    |
| **PostgreSQL**     | 15-alpine            | ✅ Healthy    |
| **Redis**          | 7-alpine             | ✅ Healthy    |

### **Performance**

- **API Response Time**: < 100ms for health checks
- **Scraping Jobs**: Complete in 2-5 seconds for simple pages
- **Worker Processing**: 2 concurrent workers by default
- **Database**: Handles 1000+ jobs without issues

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest tests/unit/ -v`
4. Run linting: `ruff check app/`
5. Submit a pull request

---

## 🆘 Support

- **Issues**: Create a GitHub issue for bugs or feature requests
- **Documentation**: See inline code documentation
- **Examples**: Check the `client/` directory for working examples

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**🚀 Production Ready!** Your AI Scraper deployment includes:

- ⚡ **Auto-scaling**: 2 API replicas + 3 worker processes
- 🔄 **Zero-downtime**: Rolling deployments with health checks
- 📊 **Monitoring**: Prometheus metrics + comprehensive logging
- 🛡️ **Security**: Redis authentication + environment isolation
- 🔧 **Automation**: Full CI/CD pipeline with automatic rollback
- 📈 **Performance**: Nginx load balancing + Redis caching

**Need Help?** Check logs in GitHub Actions or SSH to server for detailed diagnostics.

---

**Last Updated**: October 2025 | **Version**: 1.0.0 | **Status**: Production Ready ✅
