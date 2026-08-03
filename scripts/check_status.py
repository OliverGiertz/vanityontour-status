#!/usr/bin/env python3
"""
VanityOnTour Status Checker
Runs via GitHub Actions every 5 minutes, writes public/status.json
"""

import json
import ssl
import socket
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# hetzner, von dem aus geprüft wird, hat zwar eine globale IPv6-Adresse und eine
# Default-Route, aber keine funktionierende IPv6-Konnektivität — jede Verbindung
# zu einem AAAA-Record läuft erst in einen ~20s-Timeout, bevor Python auf IPv4
# zurückfällt. Das verfälscht die gemessenen Antwortzeiten massiv (20s statt
# 150ms) und zog den Lauf über das Cron-Intervall hinaus. Bis IPv6 auf hetzner
# repariert ist, wird hier ausschließlich über IPv4 geprüft — das entspricht
# ohnehin dem, was dieser Messpunkt tatsächlich erreichen kann.
_getaddrinfo_orig = socket.getaddrinfo


def _getaddrinfo_ipv4_only(*args, **kwargs):
    return [ai for ai in _getaddrinfo_orig(*args, **kwargs) if ai[0] == socket.AF_INET]


socket.getaddrinfo = _getaddrinfo_ipv4_only

OUTPUT_FILE = "public/status.json"

# Seit der VPN-Absicherung (Phase 2) antworten die Admin-Oberflächen auf ihren
# öffentlichen Domains nur noch mit 403. Der Checker läuft per Cron auf hetzner,
# das selbst WireGuard-Peer 10.10.0.14 ist — diese Dienste werden deshalb über
# "check_url" intern geprüft. "url" bleibt die öffentliche Adresse: die Statusseite
# zeigt daraus nur den Hostnamen an, interne Adressen gehören nicht ins status.json.
WEBSITES = [
    {"name": "VanityOnTour",         "url": "https://vanityontour.de",                        "group": "websites", "expect": [200, 301, 302]},
    {"name": "News Portal",           "url": "https://news.vanityontour.de",                   "group": "websites", "expect": [200, 301, 302]},
    {"name": "Wiki",                  "url": "https://wiki.vanityontour.de",                   "group": "websites", "expect": [200, 301, 302]},
    {"name": "StaySense",             "url": "https://staysense.vanityontour.de",              "group": "websites", "expect": [200, 301, 302]},
    {"name": "StaySense Landing",     "url": "https://landing.staysense.vanityontour.de",     "group": "websites", "expect": [200, 301, 302]},
    {"name": "VanityCast Landing",    "url": "https://vanitycast.vanityontour.de",             "group": "websites", "expect": [200, 301, 302]},
    {"name": "Kurzlinks",             "url": "https://go.vanityontour.de",                     "group": "websites", "expect": [200, 301, 302]},
    {"name": "N8N Automation",        "url": "https://n8n.vanityontour.de",                    "group": "tools",    "expect": [200, 301, 302], "check_url": "http://10.10.0.13:5678"},
    {"name": "Nginx Proxy Manager",   "url": "https://nginx.vanityontour.de",                  "group": "tools",    "expect": [200, 301, 302], "check_url": "http://10.10.0.13:81"},
    {"name": "Nginx Proxy Mgr (VoT)", "url": "https://ng.vanityontour.de",                     "group": "tools",    "expect": [200, 301, 302], "check_url": "http://10.10.0.12:81"},
    # Root liefert öffentlich zwar 302, aber /dashboard ist gesperrt — die echte
    # öffentliche Status-Page beweist dagegen, dass Kuma wirklich antwortet.
    {"name": "Uptime Kuma",           "url": "https://server.vanityontour.de",                 "group": "tools",    "expect": [200],           "check_url": "https://server.vanityontour.de/status/vanity"},
    {"name": "Statistiken",           "url": "https://stats.vanityontour.de",                  "group": "tools",    "expect": [200, 301, 302], "check_url": "http://127.0.0.1:3000"},
    {"name": "App Backend",           "url": "https://app.vanityontour.de",                    "group": "tools",    "expect": [200, 301, 302]},
    # Grafana und CloudPanel laufen auf hetzner selbst — localhost statt 10.10.0.14,
    # damit die Prüfung auch bei liegendem Tunnel noch stimmt.
    {"name": "CloudPanel",            "url": "https://cp.blog.vanityontour.de",                "group": "tools",    "expect": [200, 301, 302], "check_url": "https://127.0.0.1:8443"},
    # Dienste auf dem Hostinger VPS (Traefik). Forgejo und Postiz haben bewusst
    # noch öffentliche Logins und werden deshalb ganz normal von außen geprüft.
    {"name": "Forgejo",               "url": "https://git.giertz.biz",                         "group": "tools",    "expect": [200, 301, 302]},
    {"name": "Postiz",                "url": "https://social.vanityontour.de",                 "group": "tools",    "expect": [200, 301, 302, 307]},
    # Achtung, schwaches Signal: Traefik beantwortet die BasicAuth vor dem Proxy.
    # Die 401 belegt also nur, dass Traefik läuft und der Auth-Schutz noch greift —
    # nicht, dass der Container dahinter lebt. Dass Shlink selbst antwortet, zeigt
    # der Health-Endpunkt weiter unten. Eine 200 hier hiesse: Schutz ist weg.
    {"name": "Shlink Admin",          "url": "https://shlink.vanityontour.de",                 "group": "tools",    "expect": [401]},
    {"name": "RSS News API",          "url": "https://news.vanityontour.de/health",            "group": "apis",     "expect": [200]},
    {"name": "StaySense API",         "url": "https://staysense.vanityontour.de/api/health",   "group": "apis",     "expect": [200]},
    {"name": "Shlink API",            "url": "https://go.vanityontour.de/rest/health",         "group": "apis",     "expect": [200]},
]

SSL_DOMAINS = [
    "vanityontour.de",
    "news.vanityontour.de",
    "wiki.vanityontour.de",
    "n8n.vanityontour.de",
    "staysense.vanityontour.de",
    "server.vanityontour.de",
    "vanitycast.vanityontour.de",
    "go.vanityontour.de",
    "git.giertz.biz",
]

APP_STORE_COUNTRY = "de"
APP_STORE_IDS = [
    "6742772476",  # Vanity Expense Logbook
    "6781152682",  # VanityCast
]


def check_http(url: str, expected: list[int]) -> dict:
    start = time.time()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "VoT-StatusChecker/1.0"},
        )
        handler = urllib.request.HTTPSHandler(context=ctx)
        opener = urllib.request.build_opener(handler)
        opener.addheaders = [("User-Agent", "VoT-StatusChecker/1.0")]
        with opener.open(req, timeout=10) as resp:
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        return {"status": "down", "status_code": None, "response_time_ms": None, "error": str(e)[:80]}
    ms = round((time.time() - start) * 1000)
    up = code in expected
    # 4xx/5xx server errors count as down, not just degraded
    status = "up" if up else ("down" if code >= 400 else "degraded")
    return {"status": status, "status_code": code, "response_time_ms": ms, "error": None}


def check_ssl(domain: str) -> dict:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        expires_str = cert.get("notAfter", "")
        expires_dt = datetime.strptime(expires_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days = (expires_dt - datetime.now(timezone.utc)).days
        return {"valid": True, "expires_in_days": days, "expires_at": expires_dt.strftime("%Y-%m-%d")}
    except Exception as e:
        return {"valid": False, "expires_in_days": None, "expires_at": None, "error": str(e)[:60]}


def fetch_app_store(app_id: str) -> dict:
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={APP_STORE_COUNTRY}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data.get("results"):
            return {"id": app_id, "error": "No results"}
        r = data["results"][0]
        release_raw = r.get("currentVersionReleaseDate", "")
        release_fmt = release_raw[:10] if release_raw else None
        return {
            "id": app_id,
            "name": r.get("trackName"),
            "version": r.get("version"),
            "rating": r.get("averageUserRating"),
            "rating_count": r.get("userRatingCount"),
            "rating_current_version": r.get("averageUserRatingForCurrentVersion"),
            "rating_count_current_version": r.get("userRatingCountForCurrentVersion"),
            "price": r.get("formattedPrice"),
            "category": r.get("primaryGenreName"),
            "last_update": release_fmt,
            "min_ios": r.get("minimumOsVersion"),
            "store_url": r.get("trackViewUrl", "").split("?")[0],
            "icon_url": r.get("artworkUrl100", "").replace("100x100bb", "200x200bb"),
            "seller": r.get("sellerName"),
            "error": None,
        }
    except Exception as e:
        return {"id": app_id, "error": str(e)[:80]}


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{now}] Checking {len(WEBSITES)} services...")

    results = []
    for site in WEBSITES:
        target = site.get("check_url", site["url"])
        r = check_http(target, site["expect"])
        # check_url beschreibt die interne Netztopologie und wird nicht veröffentlicht
        public = {k: v for k, v in site.items() if k != "check_url"}
        results.append({**public, **r})
        sym = "✓" if r["status"] == "up" else "✗"
        via = "  via " + target if "check_url" in site else ""
        print(f"  {sym} {site['name']:30s} {r['status']:8s} {r.get('status_code') or '---'} {r.get('response_time_ms') or '---'}ms{via}")

    print("Checking SSL certificates...")
    ssl_results = {}
    for domain in SSL_DOMAINS:
        ssl_results[domain] = check_ssl(domain)
        d = ssl_results[domain]
        print(f"  {domain}: {d.get('expires_in_days', '?')} days")

    print("Fetching App Store data...")
    apps = [fetch_app_store(app_id) for app_id in APP_STORE_IDS]
    for a in apps:
        if a.get("error"):
            print(f"  {a.get('id')}: FEHLER {a['error']}")
        else:
            print(f"  {a.get('name')} v{a.get('version', '?')} ⭐{a.get('rating') or '—'}")

    # Overall status
    downs = [r for r in results if r["status"] == "down"]
    degraded = [r for r in results if r["status"] == "degraded"]
    if downs:
        overall = "degraded" if len(downs) <= 2 else "down"
    elif degraded:
        overall = "degraded"
    else:
        overall = "up"

    output = {
        "generated_at": now,
        "overall": overall,
        "services": results,
        "ssl": ssl_results,
        # "app" bleibt als Einzelfeld erhalten, weil index.html nur manuell auf
        # Hostinger aktualisiert wird — eine ältere Seite würde sonst leer laufen.
        "app": apps[0] if apps else {"error": "keine App konfiguriert"},
        "apps": apps,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Written to {OUTPUT_FILE} — overall: {overall}")


if __name__ == "__main__":
    main()
