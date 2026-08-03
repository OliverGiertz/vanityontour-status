# VanityOnTour Status Page

Automated status dashboard for all VanityOnTour services, hosted on Hostinger at `status.vanityontour.de`.

## What it monitors

- **Websites**: vanityontour.de, news, wiki, staysense, landing
- **Tools**: N8N, Nginx Proxy Manager, Uptime Kuma, Stats, App Backend, CloudPanel
- **APIs**: RSS News API, StaySense API
- **iOS App**: Vanity Expense Logbook (version, rating, last update)
- **SSL**: Certificate expiry for all main domains

## How it works

Ein Cron auf **hetzner** (`88.99.209.207`) läuft alle 5 Minuten:

```
*/5 * * * * /opt/run_status_check.sh >> /var/log/status_check.log 2>&1
```

1. `/opt/check_status.py` prüft alle Dienste und schreibt `/opt/public/status.json`
2. `run_status_check.sh` kopiert die Datei per SCP (Port 65002) nach
   `/home/u982551092/domains/status.vanityontour.de/public_html/status.json`

Die statischen Dateien unter `public/` (HTML, CSS, Icons) liegen unverändert auf
Hostinger; nur `status.json` wird zyklisch überschrieben.

> Der frühere Weg über GitHub Actions + FTP-Deploy wird **nicht** mehr benutzt.
> Das committete `public/status.json` ist deshalb nur ein Platzhalter — der
> Live-Stand steht ausschließlich auf Hostinger.

### Deployment einer Skript-Änderung

`scripts/check_status.py` wird **nicht** automatisch ausgerollt. Nach einer
Änderung:

```bash
scp scripts/check_status.py hetzner:/opt/check_status.py
ssh hetzner '/opt/run_status_check.sh'   # einmal testweise ausführen
```

## Dienste hinter dem Management-VPN

Seit der VPN-Absicherung antworten die Admin-Oberflächen öffentlich nur noch mit
`403`. Weil der Checker auf hetzner läuft und hetzner WireGuard-Peer
`10.10.0.14` ist, werden diese Dienste über das Feld `check_url` intern geprüft:

| Dienst | Anzeige (`url`) | Prüfung (`check_url`) |
|---|---|---|
| N8N Automation | `n8n.vanityontour.de` | `http://10.10.0.13:5678` |
| Nginx Proxy Manager | `nginx.vanityontour.de` | `http://10.10.0.13:81` |
| Nginx Proxy Mgr (VoT) | `ng.vanityontour.de` | `http://10.10.0.12:81` |
| Statistiken (Grafana) | `stats.vanityontour.de` | `http://127.0.0.1:3000` |
| CloudPanel | `cp.blog.vanityontour.de` | `https://127.0.0.1:8443` |
| Uptime Kuma | `server.vanityontour.de` | `…/status/vanity` (öffentlich) |

`check_url` wird vor dem Schreiben aus `status.json` entfernt — die interne
Netztopologie gehört nicht auf eine öffentliche Seite. Die Statusseite zeigt
weiterhin nur den Hostnamen aus `url` an.

## Local test

```bash
python3 scripts/check_status.py
# → writes public/status.json
```

Achtung: Lokal (ohne VPN-Route zu `10.10.0.0/24`) melden die intern geprüften
Dienste zwangsläufig „down". Aussagekräftig ist der Lauf nur auf hetzner.
