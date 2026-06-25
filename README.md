# AstroBuild&Co. Beast Agent

Cloud-hosted AI business operations dashboard for AstroBuild&Co., LLC.

This repo contains the FastAPI mobile dashboard, approval queue, iPhone webhook endpoints, scheduled routines, API settings page, and scaffolded agents for email triage, RFQ/quote drafting, Facebook post drafting, follow-ups, job packets, compliance tracking, and daily planning.

## Start command for Render

```bash
uvicorn dashboard.main:app --host 0.0.0.0 --port $PORT
```

## Build command

```bash
pip install -r requirements.txt
```

## Dashboard

After deployment:

```text
https://YOUR-RENDER-URL/?password=YOUR_DASHBOARD_PASSWORD
```

## API settings page

```text
https://YOUR-RENDER-URL/settings?password=YOUR_DASHBOARD_PASSWORD
```

Enter OpenAI, Spectrum email, and Meta/Facebook keys inside your own dashboard, not in chat.

## Safety rule

The agent can read, classify, summarize, calculate, draft, organize, and recommend.

It must never send emails, publish Facebook posts, submit quotes, delete emails, modify records, spend money, or change account settings without explicit Ashton approval.
