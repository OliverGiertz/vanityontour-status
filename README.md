# VanityOnTour Status Page

Automated status dashboard for all VanityOnTour services, hosted on Hostinger at `status.vanityontour.de`.

## What it monitors

- **Websites**: vanityontour.de, news, wiki, staysense, landing
- **Tools**: N8N, Nginx Proxy Manager, Uptime Kuma, Stats, App Backend, CloudPanel
- **APIs**: RSS News API, StaySense API
- **iOS App**: Vanity Expense Logbook (version, rating, last update)
- **SSL**: Certificate expiry for all main domains

## How it works

GitHub Actions runs every 5 minutes:
1. `scripts/check_status.py` checks all services and writes `public/status.json`
2. Commits the updated `status.json` to the repo
3. Deploys `public/` to Hostinger via FTP

## Setup: GitHub Secrets required

Go to **Settings → Secrets → Actions** and add:

| Secret | Value |
|--------|-------|
| `FTP_SERVER` | FTP hostname from Hostinger hPanel |
| `FTP_USERNAME` | `u982551092` |
| `FTP_PASSWORD` | FTP password from Hostinger hPanel |

## Local test

```bash
python3 scripts/check_status.py
# → writes public/status.json
```
