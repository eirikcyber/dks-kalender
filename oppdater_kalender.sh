#!/usr/bin/env zsh
# Generer DKS-kalender og push til GitHub Pages.
# Køyrast av launchd kvar natt.

set -e

REPO="$HOME/dks-kalender"
PYTHON="$HOME/.dks_venv/bin/python3"
# Fallback til system-python viss venv ikkje finst
if [[ ! -x "$PYTHON" ]]; then
    PYTHON="$(command -v python3)"
fi

cd "$REPO"
"$PYTHON" dks_kalender_feed.py

git add docs/dks_asker.ics
if git diff --cached --quiet; then
    echo "Ingen endringar." >&2
    exit 0
fi

git commit -m "Oppdater DKS-kalender $(date -u +%Y-%m-%d)"
git push
