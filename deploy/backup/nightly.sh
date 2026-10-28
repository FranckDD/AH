#!/bin/bash
# Sauvegarde complete de la nuit, EN PLUS des sauvegardes horaires : meme contenu (un snapshot
# nightly,db,files = export de la base + uploads, product_photos, consents) mais conservee
# longtemps : KEEP_DAILY / KEEP_WEEKLY / KEEP_MONTHLY. Le nettoyage physique (prune) a lieu le
# jour BACKUP_PRUNE_DAY (1=lundi ... 7=dimanche, defaut 7) ou si PRUNE=1.
. "$(dirname "$0")/lib.sh"
job_start nightly
check_keep
require_repo
backup_set nightly
forget_hourly
if [ "${PRUNE:-0}" = "1" ] || [ "$(date +%u)" = "${BACKUP_PRUNE_DAY:-7}" ]; then
  log "retention + prune"
  forget_nightly --prune
else
  forget_nightly
fi
refresh_pull_copy
mark_success
