#!/bin/sh
# Point d'entree unique de l'image ah2-api : run.sh api|worker|scheduler
set -eu
dir="$(dirname "$0")"
cmd="${1:-}"
case "$cmd" in
  api|worker|scheduler|alerts)
    shift
    exec "$dir/$cmd.sh" "$@"
    ;;
  *)
    echo "run.sh: commande inconnue '$cmd' (attendu : api, worker, scheduler ou alerts)" >&2
    exit 64
    ;;
esac
