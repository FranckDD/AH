#!/bin/bash
# Sauvegarde horaire : UN snapshot restic (tags hourly,db,files) = export de la base (verifie)
# + uploads, product_photos, consents, lus au meme moment. Une restauration "latest" redonne donc
# une base et des fichiers de la meme heure (pas de ligne qui pointe vers un fichier absent).
# Cout : restic reconnait les fichiers inchanges par date/taille (snapshot precedent) et
# deduplique : sans nouveaute, quelques Ko ecrits, quelques secondes.
# Retention : KEEP_HOURLY derniers (sans prune). Reussite : ecrit $STATUS_DIR/last_success_hourly.
. "$(dirname "$0")/lib.sh"
job_start hourly
check_keep
require_repo
backup_set hourly
forget_hourly
refresh_pull_copy
mark_success
