# AI Scraper API - Bruno Collection

This Bruno collection provides comprehensive testing for the AI Scraper API. It's designed to work with Bruno v2.13.2 and includes all major API endpoints with proper authentication and testing scenarios.

## 🚀 Quick Start

1. **Install Bruno**: Download from [usebruno.com](https://www.usebruno.com/)
2. **Open Collection**: Open the `bruno-collection` folder in Bruno
3. **Select Environment**: Choose either `Local` or `Production` environment
4. **Configure API Key**: Update the `api_key` variable in your chosen environment
5. **Start Testing**: Begin with the Health folder to verify connectivity

## 📁 Collection Structure

### 🏥 Health

Basic health checks and service monitoring endpoints:

- **Health Check**: Overall API health with dependency checks
- **Liveness Probe**: Kubernetes liveness endpoint
- **Readiness Probe**: Kubernetes readiness endpoint

### 🕷️ Scraping

Core scraping functionality:

- **Submit Scraping Job**: Create new scraping tasks
- **Get Job Status**: Check job progress and results
- **List Recent Results**: Browse completed jobs with filtering
- **Cancel Job**: Cancel pending or running jobs

### ⚙️ Admin

System administration and monitoring:

- **Admin Statistics**: Comprehensive system metrics
- **Queue Status**: Job queue and worker information
- **Admin Metrics**: Performance monitoring data
- **Cleanup Old Jobs**: Database maintenance operations

### 📚 Examples

Common use cases and scenarios:

- **Scrape with CSS Selector**: Target specific page elements
- **Scrape with Screenshot**: Full page capture with visual proof
- **Test Authentication**: Verify API key requirements

### 🔧 System

API infrastructure and documentation:

- **API Documentation**: Access Swagger/OpenAPI docs
- **OpenAPI Schema**: Complete API specification
- **Root Endpoint**: Basic service information

## 🔑 Authentication

The API supports API key authentication via the `X-API-Key` header. Authentication behavior depends on the `API_KEY_REQUIRED` configuration:

- **Required**: All endpoints (except health) require a valid API key
- **Optional**: API key provides enhanced features but isn't mandatory

### Setting Your API Key

1. Open Bruno and select your environment (Local/Production)
2. Update the `api_key` variable with your actual API key
3. The key will automatically be included in request headers

## 🌍 Environments

### Local Development

```
base_url: http://localhost:8000
api_base: http://localhost:8000/api/v1
```

### Production

```
base_url: http://yourname.duckdns.org
api_base: http://yourname.duckdns.org/api/v1
```

## 🧪 Testing Workflow

### 1. Basic Connectivity

Start with the **Health** folder to ensure the API is accessible:

```
1. Health Check → Verify overall service health
2. Liveness Probe → Confirm basic availability
3. Readiness Probe → Check all dependencies
```

### 2. Authentication Check

Use **Examples > Test Authentication** to verify authentication setup:

- Without API key: Should return 401/403 if auth is required
- With API key: Should return 202 and process the job

### 3. Core Functionality

Test main features with the **Scraping** folder:

```
1. Submit Scraping Job → Create a test job
2. Get Job Status → Check job progress (use returned job_id)
3. List Recent Results → Browse completed jobs
4. Cancel Job → Test job cancellation (optional)
```

### 4. Administration

Monitor system health with **Admin** endpoints:

- View system statistics and performance metrics
- Check queue status and worker activity
- Test maintenance operations

## 📊 Expected Response Codes

- **200**: Success (GET requests)
- **202**: Accepted (POST scraping jobs)
- **401**: Unauthorized (missing/invalid API key)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found (invalid job ID or endpoint)
- **422**: Validation Error (invalid request data)
- **500**: Internal Server Error (system issues)

## 🔍 Common Use Cases

### Basic Web Scraping

```json
{
  "url": "https://example.com",
  "options": {
    "extract_text": true,
    "wait_time": 2,
    "timeout": 30
  }
}
```

### Content Extraction with CSS Selectors

```json
{
  "url": "https://quotes.toscrape.com/",
  "selector": ".quote",
  "options": {
    "extract_text": true,
    "wait_time": 3
  }
}
```

### Full Page Capture with Screenshot

```json
{
  "url": "https://example.com",
  "options": {
    "screenshot": true,
    "extract_links": true,
    "extract_images": true,
    "viewport_width": 1920,
    "viewport_height": 1080
  }
}
```

## 🐛 Troubleshooting

### Connection Issues

1. Verify the base URL in your environment
2. Check if the API server is running
3. Ensure no firewall blocking the connection

### Authentication Errors

1. Confirm your API key is correctly set in the environment
2. Check if API_KEY_REQUIRED is enabled on the server
3. Verify the API key format and validity

### Job Processing Issues

1. Check job status with "Get Job Status" endpoint
2. Review job parameters for validation errors
3. Monitor admin statistics for system health

## 📝 Notes

- All timestamps are in UTC format
- Job IDs are UUIDs and should be preserved between requests
- Screenshots are base64 encoded in the response
- Rate limiting may apply based on API key configuration
- Queue processing is asynchronous - use job status polling

## 🔗 Additional Resources

- **API Documentation**: Access `/docs` endpoint for interactive Swagger UI
- **OpenAPI Spec**: Download from `/openapi.json` for client generation

---

**Version**: Compatible with AI Scraper API v1.0.0+  
**Bruno Version**: 2.13.2+  
**Last Updated**: October 2025
