# GitHub Actions API Integration

This document explains how to enable AI Scraper API access for GitHub Actions workflows.

## Current Behavior

Both the **USD Rate Email** and **Stock Price Alert** workflows now support optional API access:

### 🔄 Default Mode (No API Key)

- **USD Rate**: Falls back to manual web scraping
- **Stock Price**: Falls back to CSV parsing from Google Sheets
- ✅ **Works out of the box** - no configuration needed

### ⚡ Enhanced Mode (With API Key)

- **USD Rate**: Uses AI Scraper API for faster, more reliable scraping
- **Stock Price**: Uses AI Scraper API for better HTML parsing
- 🚀 **Faster and more robust** - requires API key setup

## Setup Instructions

### ✅ UPDATED: Using JWT_SECRET_KEY

Both workflows now use the existing `JWT_SECRET_KEY` GitHub secret for API authentication. To enable API mode:

### Step 1: Create JWT API Key

Run this command on your production server:

```bash
# SSH to your server
ssh root@your-server-ip

# Navigate to the project
cd /path/to/ai-scraper

# Create API key using JWT_SECRET_KEY
python3 scripts/create-jwt-api-key.py
```

The script will output:

```
✅ GitHub Actions API authentication configured!
🔑 Using JWT_SECRET_KEY as API Key
🏷️  Prefix: dev-sec

🎯 Both workflows will now use API mode successfully:
   - Stock Price Alert workflow
   - USD Rate Email workflow

� No additional GitHub secrets needed - using existing JWT_SECRET_KEY
```

### Step 2: No Additional Setup Needed!

✅ **Already configured!** Both workflows now use `JWT_SECRET_KEY` for API access 3. Click **New repository secret** 4. Name: `AI_SCRAPER_API_KEY` 5. Value: The full API key (e.g., `sk-abc123def456...`) 6. Click **Add secret**

### Step 3: Verify Setup

After adding the secret, both workflows will automatically start using the API for enhanced performance:

- **USD Rate Email**: Next run will use API instead of manual scraping
- **Stock Price Alert**: Next run will use API instead of CSV parsing

## Verification

You can verify API usage by checking the workflow logs:

### With API Key ✅

```
[get_usd_rate] Retrieved rate via AI Scraper API
[get_stock_prices] Retrieved stock data via AI Scraper API
```

### Without API Key (Fallback) ⚠️

```
[get_usd_rate] Retrieved rate via manual fallback
[get_stock_prices] Retrieved stock data via CSV fallback
```

## Benefits of API Mode

| Feature            | Manual/CSV Mode | API Mode      |
| ------------------ | --------------- | ------------- |
| **Speed**          | Slower          | Faster        |
| **Reliability**    | Good            | Better        |
| **Error Handling** | Basic           | Advanced      |
| **Rate Limiting**  | None            | Managed       |
| **Monitoring**     | Limited         | Full tracking |

## Troubleshooting

### API Key Not Working

- Verify the secret name is exactly `AI_SCRAPER_API_KEY`
- Check that the API key was created successfully
- Ensure the AI Scraper API server is running

### Fallback Mode Activated

- This is normal if no API key is configured
- Both modes provide the same functionality
- API mode just offers better performance

### Still Getting 401 Errors

- The production API requires authentication
- Verify your API key is active: check the database `api_keys` table
- Ensure `API_KEY_REQUIRED=true` in production settings

## Advanced Configuration

### Custom Rate Limits

When creating API keys, you can specify custom rate limits:

```python
# In the create-api-key.py script
api_key, raw_key = ApiKey.create_api_key(
    name="GitHub Actions",
    description="API key for workflows",
    rate_limit_per_minute=200,  # Higher limits for workflows
    rate_limit_per_hour=2000,
    rate_limit_per_day=20000,
)
```

### Multiple API Keys

You can create separate keys for different purposes:

```bash
# For USD rate workflow
python3 scripts/create-api-key.py --name "USD Rate Workflow" --description "API key for USD rate email"

# For stock price workflow
python3 scripts/create-api-key.py --name "Stock Price Workflow" --description "API key for stock price alerts"
```

Then use different GitHub secrets: `USD_API_KEY`, `STOCK_API_KEY`, etc.
