#!/usr/bin/env bash
# Rollt den Stand des Repos aus:
#   scripts/check_status.py  -> hetzner:/opt/check_status.py   (Cron alle 5 Min.)
#   public/* (ohne status.json) -> Hostinger status.vanityontour.de
# status.json und zahlen.json erzeugen die Server selbst – nie aus dem Repo kopieren,
# das committete status.json ist nur ein Platzhalter.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Arbeitsverzeichnis nicht sauber – erst committen." >&2
  exit 1
fi
python3 -I -m py_compile scripts/check_status.py
rm -rf scripts/__pycache__

HOSTINGER="u982551092@82.198.228.98"
REMOTE_DIR="/home/u982551092/domains/status.vanityontour.de/public_html"
KEY="/root/.ssh/hostinger_ed25519"

scp -q scripts/check_status.py hetzner:/opt/check_status.py
echo "check_status.py -> hetzner:/opt"

tar -C public --exclude=status.json --exclude=zahlen.json -czf - . | ssh hetzner \
  "ssh -p 65002 -i $KEY -o BatchMode=yes $HOSTINGER 'tar -C $REMOTE_DIR -xzf -'"
echo "public/ -> status.vanityontour.de"

# Sofort einmal prüfen, damit status.json zur neuen Seite passt
ssh hetzner /opt/run_status_check.sh >/dev/null
echo "Statusprüfung gelaufen. Deployt: $(git rev-parse --short HEAD)"
