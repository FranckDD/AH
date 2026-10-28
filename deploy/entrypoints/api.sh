#!/bin/sh
# API FastAPI : gunicorn + UvicornWorker sur le port 8000.
#
# FORWARDED_ALLOW_IPS : adresses dont l'en-tete X-Forwarded-For est cru, donc
# celles du proxy (Caddy). Par defaut 127.0.0.1 = personne (sur). Le compose le
# regle de preference sur le sous-reseau du conteneur Caddy (pas '*' : avec '*',
# uvicorn prend l'adresse la plus a gauche de X-Forwarded-For, falsifiable si le
# port 8000 est atteignable autrement que par Caddy).
# Valeur reelle de client : request.client.host et slowapi.get_remote_address.
set -eu
exec gunicorn \
  -k uvicorn.workers.UvicornWorker \
  --workers "${WEB_CONCURRENCY:-2}" \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --graceful-timeout 30 \
  --worker-tmp-dir /dev/shm \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --access-logfile - \
  api_backend.backend_app.main:app
