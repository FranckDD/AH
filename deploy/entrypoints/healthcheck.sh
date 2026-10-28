#!/bin/sh
# Sonde de l'API (healthcheck compose du service "api").
# /health repond HTTP 200 meme si la base est injoignable : le corps JSON
# {"success": true|false, "status": "ok"|"error", "database": ...} fait foi.
# Code 0 seulement si success est true.
exec python -c "
import json, sys, urllib.request
try:
    body = json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=8))
    sys.exit(0 if body.get('success') is True else 1)
except Exception:
    sys.exit(1)
"
