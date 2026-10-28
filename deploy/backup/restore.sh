#!/bin/bash
# Restauration depuis le depot restic.
#
#   restore.sh [--from-offsite] [--apply-to-stack] [--force] <snapshot|latest> <dossier_cible>
#
# Sans --apply-to-stack : restaure dans <dossier_cible> et NE TOUCHE A RIEN d'autre.
#     <cible>/db/ah2.dump                     export de la base (verifie par pg_restore)
#     <cible>/files/data/{uploads,product_photos,consents}   fichiers deposes
#   "latest" = le snapshot le plus recent etiquete db (horaire OU nocturne). Il contient l'export
#   ET les fichiers pris au meme moment : base et fichiers sont de la meme heure. (Anciens depots :
#   si ce snapshot ne contient pas de fichiers, le dernier snapshot "files" est utilise.)
#   Un identifiant restaure ce seul snapshot.
#
# Avec --apply-to-stack : en plus, RECREE la base depuis l'export (pg_restore --clean --if-exists
#   --no-owner, en une seule transaction : tout ou rien) et restaure les fichiers DIRECTEMENT dans
#   les volumes montes sous $APPLY_ROOT (defaut /apply : /apply/data/uploads, .../product_photos,
#   .../consents), proprietaire 10001. Doit etre lance en root. Les autres services (api, worker,
#   scheduler, powersync) doivent etre ARRETES ; --force coupe les connexions restantes.
#   AVANT d'ecraser une base non vide, un export de securite de la base ACTUELLE est ecrit dans
#   <dossier_cible>/safety/ (refus de continuer s'il echoue). Monter <dossier_cible> sur le disque
#   de l'hote pour le conserver. Commande complete : docs/exploitation/sauvegardes.md.
# --from-offsite : lit le depot Hostinger (SFTP, memes variables BACKUP_SFTP_*) au lieu du depot local
#   (serveur perdu, depot local perdu aussi).
# Depot : RESTIC_REPOSITORY (defaut /backups/repo) et RESTIC_PASSWORD(_FILE).
. "$(dirname "$0")/lib.sh"
JOB=restore
APPLY=0; FORCE=0; FROM_OFFSITE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --apply-to-stack) APPLY=1 ;;
    --force) FORCE=1 ;;
    --from-offsite) FROM_OFFSITE=1 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    --) shift; break ;;
    -*) echo "Option inconnue : $1" >&2; exit 64 ;;
    *) break ;;
  esac
  shift
done
[ $# -eq 2 ] || { sed -n '2,6p' "$0" >&2; exit 64; }
SNAP="$1"; TARGET="$2"
APPLY_ROOT="${APPLY_ROOT:-/apply}"

STAGE="$(mktemp -d "${STAGE_ROOT}/restore.XXXXXX" 2>/dev/null || mktemp -d)"
trap 'rm -rf "$STAGE"; ' EXIT
load_password
if [ "$FROM_OFFSITE" = 1 ]; then
  offsite_setup
  export RESTIC_REPOSITORY="$OFF" RESTIC_PASSWORD="$OFFPW"
  # toutes les commandes restic suivantes visent le depot distant
  restic() { command restic --retry-lock "${RESTIC_RETRY_LOCK:-30m}" "${OPTS[@]}" "$@"; }
  log "lecture du depot distant : $OFF"
fi
require_repo

latest_id() { restic snapshots --tag "$1" --json | jq -r "$JQ_DEFS"' sort_by(.time | ts) | last | .id // empty'; }

DB_ID=""; FILES_ID=""
if [ "$SNAP" = latest ]; then
  DB_ID="$(latest_id db)"
  [ -n "$DB_ID" ] || die "aucun export de base dans le depot"
  tags="$(restic snapshots --json "$DB_ID" | jq -r '.[0].tags | join(",")')"
  case ",$tags," in
    *,files,*) FILES_ID="$DB_ID" ;;          # snapshot unique : base et fichiers du meme instant
    *) FILES_ID="$(latest_id files)" ;;      # ancien format (export seul) : dernier snapshot de fichiers
  esac
else
  tags="$(restic snapshots --json "$SNAP" | jq -r '.[0].tags | join(",")')" || die "snapshot introuvable : $SNAP"
  case ",$tags," in *,db,*) DB_ID="$SNAP" ;; esac
  case ",$tags," in *,files,*) FILES_ID="$SNAP" ;; esac
  [ -n "$DB_ID$FILES_ID" ] || die "snapshot $SNAP sans etiquette db ni files (etiquettes : $tags)"
fi

mkdir -p "$TARGET"
if [ -n "$DB_ID" ]; then
  log "restauration de l'export de base (snapshot $DB_ID)"
  rm -rf "$TARGET/db.tmp"
  restic restore "$DB_ID" --target "$TARGET/db.tmp" --include "$DUMP_SNAP_DIR"
  mkdir -p "$TARGET/db"
  mv -f "$TARGET/db.tmp$DUMP_SNAP_FILE" "$TARGET/db/ah2.dump" || die "export absent du snapshot $DB_ID (format inconnu)"
  rm -rf "$TARGET/db.tmp"
  DUMP="$TARGET/db/ah2.dump"
  [ -s "$DUMP" ] || die "export restaure vide : $DUMP"
  pg_restore --file=/dev/null "$DUMP" || die "export restaure illisible : $DUMP"
  log "export de base restaure et verifie : $DUMP ($(wc -c < "$DUMP" | tr -d ' ') octets)"
fi

if [ -n "$FILES_ID" ] && [ "$APPLY" = 0 ]; then
  log "restauration des fichiers (snapshot $FILES_ID) dans $TARGET/files"
  restic restore "$FILES_ID" --target "$TARGET/files" --include /data
fi

if [ "$APPLY" = 1 ]; then
  [ "$(id -u)" = 0 ] || die "--apply-to-stack doit etre lance en root (--user 0) pour donner les fichiers a l'uid 10001"
  if [ -n "$DB_ID" ]; then
    : "${PGHOST:=db}" "${PGUSER:?PGUSER manquant}" "${PGDATABASE:?PGDATABASE manquant}" "${PGPASSWORD:?PGPASSWORD manquant}"
    export PGHOST PGUSER PGDATABASE PGPASSWORD
    psql -X -At -c 'select 1' >/dev/null || die "base injoignable ($PGHOST)"
    others="$(psql -X -At -c "select count(*) from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()")"
    if [ "$others" != 0 ]; then
      [ "$FORCE" = 1 ] || die "$others connexion(s) ouverte(s) sur la base : arreter api, worker, scheduler et powersync (docker compose stop ...) ou relancer avec --force"
      log "--force : fermeture de $others connexion(s)"
      psql -X -At -c "select pg_terminate_backend(pid) from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()" >/dev/null
      sleep 2
    fi
    ntab="$(psql -X -At -c "select count(*) from information_schema.tables where table_schema='public'")"
    if [ "$ntab" != 0 ]; then
      SAFE="$TARGET/safety/avant-restauration-$(date +%Y%m%d-%H%M%S).dump"
      mkdir -p "$TARGET/safety"
      log "base NON vide ($ntab tables) : export de securite de l'etat actuel -> $SAFE"
      pg_dump --format=custom --no-password --file="$SAFE" || die "export de securite impossible : restauration annulee, rien n'a ete modifie"
      pg_restore --file=/dev/null "$SAFE" || die "export de securite illisible : restauration annulee, rien n'a ete modifie"
      log "export de securite verifie ($(wc -c < "$SAFE" | tr -d ' ') octets). A conserver jusqu'a verification du resultat."
    else
      log "base vide : pas d'export de securite necessaire"
    fi
    log "pg_restore --clean --if-exists --no-owner (une transaction) vers $PGDATABASE@$PGHOST"
    pg_restore --clean --if-exists --no-owner --single-transaction --exit-on-error -d "$PGDATABASE" "$DUMP" \
      || die "pg_restore a echoue : la base n'a pas ete modifiee (transaction annulee)"
    log "base recreee. alembic_version = $(psql -X -At -c 'select version_num from public.alembic_version' | tr '\n' ' ')"
  fi
  if [ -n "$FILES_ID" ]; then
    for v in uploads product_photos consents; do
      [ -d "$APPLY_ROOT/data/$v" ] || die "volume non monte : $APPLY_ROOT/data/$v (voir la commande dans docs/exploitation/sauvegardes.md)"
    done
    log "restauration des fichiers (snapshot $FILES_ID) dans $APPLY_ROOT/data/*"
    restic restore "$FILES_ID" --target "$APPLY_ROOT" --include /data
    chown -R 10001:10001 "$APPLY_ROOT/data/uploads" "$APPLY_ROOT/data/product_photos" "$APPLY_ROOT/data/consents"
    log "proprietaire des fichiers : uid 10001"
  else
    log "ATTENTION: aucun snapshot de fichiers restaure (snapshot de base seule)"
  fi
fi
log "TERMINE"
