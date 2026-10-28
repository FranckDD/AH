#!/bin/bash
# Rafraichit a la demande la copie coherente du depot ($RESTIC_REPOSITORY/.pull) lue par le PC de
# l'admin (pull_backups.ps1), sous le verrou partage "repo" : attend la fin d'un hourly/nightly/
# offsite en cours. hourly.sh et nightly.sh le font deja a chaque execution ; ce script sert a
# forcer un rafraichissement juste avant une copie manuelle :
#   docker compose ... exec backup /opt/backup/pull_prepare.sh
# Affiche le chemin et le manifeste. Aucune ecriture dans le depot lui-meme.
. "$(dirname "$0")/lib.sh"
job_start pull_prepare
refresh_pull_copy
[ -s "$RESTIC_REPOSITORY/$PULL_DIR_NAME/PULL_MANIFEST.json" ] || die "copie pour le PC absente apres rafraichissement"
echo "$RESTIC_REPOSITORY/$PULL_DIR_NAME : $(cat "$RESTIC_REPOSITORY/$PULL_DIR_NAME/PULL_MANIFEST.json")"
