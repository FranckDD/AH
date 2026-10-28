#!/bin/sh
# Controles d alerte a la demande : run.sh alerts [--dry-run|--test-mail]
set -eu
cd /app
exec python -m deploy.alerts.run_checks "$@"
