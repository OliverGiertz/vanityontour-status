# VanityOnTour – Status & Zahlen

Öffentliche Seite unter `status.vanityontour.de`, gehostet auf Hostinger. Seit
09.10.2026 zeigt sie neben dem Live-Status auch Kennzahlen („In Zahlen") und die
30-Tage-Verfügbarkeit je Dienst.

## Grundsatz: öffentlich ist nur, was öffentlich sein soll

`status.json` und `zahlen.json` sind für jeden abrufbar. Deshalb stehen hier
**nur öffentliche Dienste** – keine Admin-Oberflächen, keine Server, kein VPN.
Die internen Dienste (n8n, Nginx Proxy Manager, Grafana, CloudPanel, Kuma-Admin,
Postiz, Shlink-Admin, Forgejo, Wiki) werden intern über Uptime Kuma und das
Grafana-Dashboard „VoT Betrieb (intern)" überwacht (nur per VPN). Bis 09.10.2026
standen sie auch hier – das ist bewusst entfernt.

## Was die Seite zeigt

- **In Zahlen** (`zahlen.json`): Besucher und Seitenaufrufe (Umami, gezählt seit
  09.10.2026), Beiträge im Blog, Fediverse-Follower, Mastodon-Beiträge,
  Kurzlink-Klicks, Verfügbarkeit 30 Tage, Seitenaufrufe pro Tag
- **Websites**: vanityontour.de, News, StaySense, StaySense Landing,
  VanityCast Landing, Kurzlinks (`go.`)
- **Schnittstellen**: RSS News API, StaySense API, Shlink API
- **iOS Apps**: Vanity Expense Logbook und VanityCast (Version, Bewertung, letztes Update)
- je Dienst: Status, Verfügbarkeit 30 Tage (Uptime Kuma), Antwortzeit, Zertifikat

## Wie die Daten entstehen

| Datei | Erzeugt von | Wo | Takt |
|---|---|---|---|
| `status.json` | `scripts/check_status.py` (dieses Repo) | Cron auf hetzner, `/opt/run_status_check.sh` | 5 Min. |
| `zahlen.json` | `publish_public.py` im Repo `oliver/vot-metrics-exporter` | systemd-Timer `vot-public.timer` auf hetzner | 5 Min. |

Beide Dateien werden per SCP (Port 65002, Schlüssel `/root/.ssh/hostinger_ed25519`
auf hetzner) nach Hostinger geschoben. `zahlen.json` arbeitet mit einer
**Positivliste**: Nur ausdrücklich genannte Kennzahlen und Dienste kommen hinein,
auch wenn Prometheus mehr kennt.

Das committete `public/status.json` ist nur ein Platzhalter – der Live-Stand steht
ausschließlich auf Hostinger.

## Deploy

```bash
./deploy.sh
```

Verweigert bei uncommitteten Änderungen, kopiert `scripts/check_status.py` nach
`hetzner:/opt/`, packt `public/` (ohne die beiden JSON-Dateien) nach Hostinger
und führt die Statusprüfung einmal aus. Nie einzelne Dateien von Hand kopieren –
genau so sind Repo und Server früher auseinandergelaufen.

## Lokal testen

```bash
python3 scripts/check_status.py      # schreibt public/status.json
cd public && python3 -m http.server   # Seite mit lokalen Daten ansehen
```

Für `zahlen.json` die Live-Datei holen:
`curl -s https://status.vanityontour.de/zahlen.json -o public/zahlen.json`
(nicht committen).
