# Deploy to Render

Use repo:

```text
ASTROBUILDNCO/tradingbotai
```

Render settings:

```text
Build command: pip install -r requirements.txt
Start command: uvicorn dashboard.main:app --host 0.0.0.0 --port $PORT
```

Required Render environment variables:

```text
DASHBOARD_PASSWORD=choose_a_private_password
CONFIG_ENCRYPTION_KEY=optional_but_recommended
TIMEZONE=America/New_York
APPROVAL_REQUIRED=true
```

After deploy:

```text
https://YOUR-RENDER-URL/?password=YOUR_DASHBOARD_PASSWORD
https://YOUR-RENDER-URL/settings?password=YOUR_DASHBOARD_PASSWORD
```

Put OpenAI/Spectrum/Meta keys into the settings page, not chat.
