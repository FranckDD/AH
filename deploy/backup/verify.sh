#!/bin/bash
# Controle d'integrite : structure du depot + lecture de donnees par echantillon (restic check),
# puis relecture COMPLETE du dernier export de base (pg_restore). Ecrit last_success_verify.
# BACKUP_CHECK_SUBSET (defaut 5%) : part des donnees relues ; 100% pour un controle total.
. "$(dirname "$0")/lib.sh"
job_start verify
require_repo
log "restic check (sous-ensemble ${BACKUP_CHECK_SUBSET:-5%})"
restic check --read-data-subset="${BACKUP_CHECK_SUBSET:-5%}"
id="$(restic snapshots --tag db --json | jq -r "$JQ_DEFS"' sort_by(.time | ts) | last | .id // empty')"
[ -n "$id" ] || die "aucun export de base dans le depot"
# Les dates de restic portent un decalage horaire (+01:00) : ts les convertit correctement.
age="$(restic snapshots --tag db --json | jq -r "$JQ_DEFS"' sort_by(.time | ts) | last | now - (.time | ts) | floor')"
log "dernier export : snapshot $id, age ${age} s"
restic dump "$id" "$DUMP_SNAP_FILE" > "$STAGE/ah2.dump"
size="$(wc -c < "$STAGE/ah2.dump" | tr -d ' ')"
[ "$size" -ge "$BACKUP_MIN_DUMP_BYTES" ] || die "dernier export trop court ($size octets)"
pg_restore --file=/dev/null "$STAGE/ah2.dump" 2>"$STAGE/err" \
  || die "dernier export illisible (pg_restore : $(tail -n 1 "$STAGE/err"))"
log "dernier export relu en entier : $(pg_restore --list "$STAGE/ah2.dump" | grep -c ' TABLE DATA ') entrees de donnees de tables (TABLE DATA)"
# Un export de plus de 3 h alors que l'horaire tourne chaque heure = probleme (alerte).
[ "$age" -le "${BACKUP_MAX_DUMP_AGE_S:-10800}" ] || die "le dernier export a ${age} s (> ${BACKUP_MAX_DUMP_AGE_S:-10800} s) : l'export horaire ne tourne plus"
mark_success
