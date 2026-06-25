# iPhone Shortcuts

After Render deploys, use your Render URL.

Dashboard:

```text
https://YOUR-RENDER-URL/?password=YOUR_DASHBOARD_PASSWORD
```

API settings:

```text
https://YOUR-RENDER-URL/settings?password=YOUR_DASHBOARD_PASSWORD
```

Shortcut webhook URLs:

```text
POST https://YOUR-RENDER-URL/api/run/morning?password=YOUR_DASHBOARD_PASSWORD
POST https://YOUR-RENDER-URL/api/run/midday?password=YOUR_DASHBOARD_PASSWORD
POST https://YOUR-RENDER-URL/api/run/evening?password=YOUR_DASHBOARD_PASSWORD
POST https://YOUR-RENDER-URL/api/run/check_email?password=YOUR_DASHBOARD_PASSWORD
POST https://YOUR-RENDER-URL/api/run/draft_facebook_post?password=YOUR_DASHBOARD_PASSWORD
```

In iPhone Shortcuts:

1. Add URL action.
2. Paste webhook URL.
3. Add Get Contents of URL.
4. Set method to POST.
5. Save shortcut.

Your iPhone is the remote. Render is the engine.
