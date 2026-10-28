#!/bin/sh
# Worker Celery (file par defaut "celery"). Application : celery_app.py a la racine.
set -eu
exec celery -A celery_app worker --loglevel=info -Q celery --concurrency="${CELERY_CONCURRENCY:-2}"
