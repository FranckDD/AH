#!/bin/bash
# Fonctions communes des scripts de sauvegarde (a "sourcer", jamais a lancer).
# Contrat avec la tache 10 (alertes) : dans $STATUS_DIR (volume backup_status) chaque tache
#   <job> in hourly|nightly|offsite|verify ecrit
#     last_success_<job>   : horodatage Unix (secondes) de la derniere reussite
#     last_failure_<job>   : horodatage Unix du dernier echec (supprime a la reussite suivante)
#     last_error_<job>     : message de l'echec (supprime a la reussite suivante)
#   et offsite ecrit aussi offsite_stats.json {ts, files, dirs, bytes}.
# Tout echec : code de sortie non nul + une ligne "BACKUP-ECHEC job=... : message" sur stderr.
set -Eeuo pipefail
umask 077

STATUS_DIR="${STATUS_DIR:-/var/lib/ah2-status}"
STAGE_ROOT="${STAGE_ROOT:-/var/tmp/ah2-stage}"
LOCK_DIR="${LOCK_DIR:-/var/tmp}"
BACKUP_HOST="${BACKUP_HOST:-ah2}"
BACKUP_DATA_DIRS="${BACKUP_DATA_DIRS:-/data/uploads /data/product_photos /data/consents}"
BACKUP_MIN_DUMP_BYTES="${BACKUP_MIN_DUMP_BYTES:-20000}"
KEEP_HOURLY="${KEEP_HOURLY:-48}"
KEEP_DAILY="${KEEP_DAILY:-14}"
KEEP_WEEKLY="${KEEP_WEEKLY:-8}"
KEEP_MONTHLY="${KEEP_MONTHLY:-6}"
export RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-/backups/repo}"
export RESTIC_CACHE_DIR="${RESTIC_CACHE_DIR:-/var/cache/restic}"
# Le dump est pose dans un dossier au chemin FIXE (il fait partie du snapshot, avec les fichiers) ;
# restore.sh et verify.sh le retrouvent a ce chemin. Ne pas le changer sans migration du depot.
DUMP_SNAP_DIR="/var/tmp/ah2-dump"
DUMP_SNAP_FILE="$DUMP_SNAP_DIR/ah2.dump"
PULL_DIR_NAME=".pull"   # copie "figee" du depot, lue par le PC de l'admin (voir refresh_pull_copy)

# restic attend (au plus RESTIC_RETRY_LOCK) qu'un verrou exclusif (forget/prune d'un autre processus)
# se libere au lieu d'echouer. Un verrou perime (crash) se leve avec "restic unlock" (fait par
# require_repo : ne retire que les verrous perimes, jamais un verrou vivant).
restic() { command restic --retry-lock "${RESTIC_RETRY_LOCK:-30m}" "$@"; }

# Definition jq : ts = secondes Unix d'une date RFC3339 de restic, AVEC decalage horaire
# ("2026-10-28T02:30:00.123+01:00" ou "...Z"). Ne jamais faire .[0:19]+"Z" (heure locale lue comme UTC).
JQ_DEFS='def ts: sub("[.][0-9]+";"") | capture("^(?<d>[0-9T:-]{19})(?<z>Z|[+-][0-9]{2}:[0-9]{2})$")
  | (.d + "Z" | fromdateiso8601) - (if .z == "Z" then 0 else ((if .z[0:1] == "-" then -1 else 1 end) * ((.z[1:3] | tonumber) * 3600 + (.z[4:6] | tonumber) * 60)) end);'

JOB="backup"
ERRMSG=""
STAGE=""

log() { printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$JOB" "$*"; }
die() { ERRMSG="$*"; log "ERREUR: $*" >&2; exit 1; }

atomic_write() { # atomic_write fichier contenu  (lisible par les autres conteneurs : 0644)
  local f="$1" tmp
  tmp="$(mktemp "$f.XXXXXX")"
  printf '%s\n' "$2" > "$tmp"
  chmod 0644 "$tmp"
  mv -f "$tmp" "$f"
}

mark_success() {
  atomic_write "$STATUS_DIR/last_success_$JOB" "$(date +%s)"
  rm -f "$STATUS_DIR/last_failure_$JOB" "$STATUS_DIR/last_error_$JOB"
  log "OK"
}

job_exit() {
  local rc="$1"
  trap - EXIT ERR
  [ -n "$STAGE" ] && rm -rf "$STAGE"
  [ -n "${DUMP_OWNED:-}" ] && rm -rf "$DUMP_SNAP_DIR"
  if [ "$rc" -ne 0 ]; then
    local msg="${ERRMSG:-echec inattendu (voir le journal ci-dessus)}"
    { mkdir -p "$STATUS_DIR" \
      && atomic_write "$STATUS_DIR/last_failure_$JOB" "$(date +%s)" \
      && atomic_write "$STATUS_DIR/last_error_$JOB" "$msg"; } 2>/dev/null || true
    echo "BACKUP-ECHEC job=$JOB : $msg" >&2
  fi
  exit "$rc"
}

# job_start <nom> [nom_du_verrou] : verrou, dossier temporaire, piege de sortie.
job_start() {
  JOB="$1"
  local lock="${2:-repo}"
  mkdir -p "$STATUS_DIR" "$STAGE_ROOT"
  STAGE="$STAGE_ROOT/$JOB.$$"
  mkdir -p "$STAGE"
  trap 'ERRMSG="${ERRMSG:-echec de : $BASH_COMMAND (ligne $LINENO)}"' ERR
  trap 'job_exit $?' EXIT
  # Un seul travail a la fois par verrou : hourly, nightly, verify ET offsite partagent "repo" (un
  # chevauchement ATTEND son tour, il n'echoue pas). Verrou local au conteneur ; restic pose en plus
  # ses propres verrous dans le depot (--retry-lock) pour les processus d'un autre conteneur.
  exec 9>"$LOCK_DIR/ah2-backup-$lock.lock"
  flock -w "${BACKUP_LOCK_WAIT:-3600}" 9 || die "verrou '$lock' occupe depuis plus de ${BACKUP_LOCK_WAIT:-3600} s"
  load_password
}

# Mot de passe du depot : RESTIC_PASSWORD, ou RESTIC_PASSWORD_FILE (lu une fois, jamais affiche).
load_password() {
  # Fichier secret par defaut (monte en lecture seule par le compose) : fonctionne aussi pour
  # "docker compose exec", qui n'herite pas de l'environnement exporte par l'entrypoint.
  if [ -z "${RESTIC_PASSWORD:-}" ] && [ -z "${RESTIC_PASSWORD_FILE:-}" ] && [ -f /run/secrets/restic_password ]; then
    RESTIC_PASSWORD_FILE=/run/secrets/restic_password
  fi
  if [ -z "${RESTIC_PASSWORD:-}" ] && [ -n "${RESTIC_PASSWORD_FILE:-}" ]; then
    [ -r "$RESTIC_PASSWORD_FILE" ] || die "RESTIC_PASSWORD_FILE illisible"
    RESTIC_PASSWORD="$(head -n1 "$RESTIC_PASSWORD_FILE" | tr -d '\r\n')"
  fi
  unset RESTIC_PASSWORD_FILE
  [ -n "${RESTIC_PASSWORD:-}" ] || die "RESTIC_PASSWORD manquant (ni RESTIC_PASSWORD_FILE, ni /run/secrets/restic_password)"
  export RESTIC_PASSWORD
}

check_keep() {
  local v
  for v in KEEP_HOURLY KEEP_DAILY KEEP_WEEKLY KEEP_MONTHLY; do
    [[ "${!v}" =~ ^[1-9][0-9]*$ ]] || die "$v doit etre un entier >= 1 (valeur : '${!v}')"
  done
}

# Le depot doit exister et s'ouvrir avec le mot de passe fourni ; jamais d'init ici
# (un mauvais mot de passe ne doit JAMAIS conduire a creer un second depot).
require_repo() { # require_repo [depot]
  local repo="${1:-$RESTIC_REPOSITORY}" out
  if ! out="$(RESTIC_REPOSITORY="$repo" restic cat config 2>&1 >/dev/null)"; then
    case "$out" in
      *"wrong password"*|*"no key found"*) die "mot de passe du depot restic incorrect ($repo) : rien n'a ete ecrit" ;;
      *) die "depot restic inaccessible ($repo) : $(printf '%s' "$out" | tail -n 2 | tr '\n' ' ')" ;;
    esac
  fi
  RESTIC_REPOSITORY="$repo" restic unlock >/dev/null 2>&1 || true
}

# dump_db <fichier> : pg_dump au format personnalise, SANS compression interne (-Z 0 : restic
# compresse et deduplique bien mieux un flux stable d'une heure a l'autre). Echoue bruyamment si
# le fichier est vide, trop court ou illisible (relecture complete par pg_restore).
dump_db() {
  local out="$1" size
  : "${PGHOST:=db}"
  [ -n "${PGUSER:-}" ] && [ -n "${PGDATABASE:-}" ] && [ -n "${PGPASSWORD:-}" ]     || die "PGUSER, PGDATABASE ou PGPASSWORD manquant (POSTGRES_USER/DB/PASSWORD de deploy/.env)"
  export PGHOST PGUSER PGDATABASE PGPASSWORD
  rm -f "$out"
  log "pg_dump de $PGDATABASE sur $PGHOST"
  "${PG_DUMP_BIN:-pg_dump}" --format=custom --compress=0 --no-password --file="$out" \
    || die "pg_dump a echoue"
  [ -f "$out" ] || die "pg_dump n'a produit aucun fichier"
  size="$(wc -c < "$out" | tr -d ' ')"
  [ "$size" -ge "$BACKUP_MIN_DUMP_BYTES" ] \
    || die "export trop court ($size octets < $BACKUP_MIN_DUMP_BYTES) : sauvegarde annulee"
  pg_restore --file=/dev/null "$out" 2>"$STAGE/pgrestore.err" \
    || die "export illisible ou tronque (pg_restore : $(tail -n 1 "$STAGE/pgrestore.err"))"
  log "export valide : $size octets"
}

# BACKUP_FAKE_TIME (reserve aux essais) date le snapshot : BACKUP_FAKE_TIME="2026-01-01_02:30:00" (ou avec une espace)
# Code de sortie 3 de restic = snapshot ECRIT mais certains fichiers illisibles/disparus pendant la
# lecture (un fichier temporaire supprime par l'application) : ce n'est pas une perte de sauvegarde,
# on le journalise et on continue. Tout autre code != 0 = echec.
restic_backup() {
  local extra=() rc=0
  [ -n "${BACKUP_FAKE_TIME:-}" ] && extra=(--time "${BACKUP_FAKE_TIME//_/ }")
  restic backup --host "$BACKUP_HOST" "${extra[@]}" "$@" || rc=$?
  if [ "$rc" -eq 3 ]; then
    log "ATTENTION: restic code 3 : snapshot ecrit, mais des fichiers n'ont pas pu etre lus (disparus pendant la sauvegarde ?)" >&2
    rc=0
  fi
  return "$rc"
}

# backup_set <tag-de-frequence> : UN SEUL snapshot restic (tags <freq>,db,files) qui contient
#   - l'export de la base ($DUMP_SNAP_DIR/ah2.dump, verifie avant d'etre envoye)
#   - les trois volumes de fichiers (uploads, product_photos, consents)
# lus au meme moment : une restauration "latest" redonne une base et des fichiers de la MEME heure.
# restic deduplique : si rien n'a change, seuls quelques Ko sont ecrits (les fichiers deja connus
# sont reconnus par date/taille grace au snapshot precedent).
backup_set() {
  local freq="$1" d dirs=()
  for d in $BACKUP_DATA_DIRS; do
    [ -d "$d" ] || die "dossier de donnees absent : $d (volume non monte ?)"
    dirs+=("$d")
  done
  DUMP_OWNED=1
  rm -rf "$DUMP_SNAP_DIR"; mkdir -p "$DUMP_SNAP_DIR"
  dump_db "$DUMP_SNAP_FILE"
  log "snapshot unique base + fichiers (tags $freq,db,files) : $DUMP_SNAP_DIR ${dirs[*]}"
  restic_backup --tag "$freq" --tag db --tag files "$DUMP_SNAP_DIR" "${dirs[@]}"
  rm -rf "$DUMP_SNAP_DIR"
}

# refresh_pull_copy : copie INSTANTANEE et COHERENTE du depot dans $RESTIC_REPOSITORY/.pull, pour le
# PC de l'admin. Appelee en fin de hourly/nightly, donc SOUS le verrou "repo" : aucun travail
# n'ecrit pendant la copie. Les fichiers d'un depot restic ne sont jamais modifies apres ecriture
# (seulement ajoutes ou supprimes) : des liens physiques (cp -al) suffisent, sans dupliquer les
# donnees (cout : quelques centaines de ms, aucun octet). Le PC copie ce dossier : meme si le
# depot vivant change ou est elague pendant sa copie, ce qu'il lit ne bouge pas. PULL_MANIFEST.json
# (nombre de fichiers, date) lui permet de detecter une copie tronquee sans le mot de passe.
# Un echec ici ne fait PAS echouer la sauvegarde (journalise, et la copie PC refusera une copie perimee).
refresh_pull_copy() {
  local repo="$RESTIC_REPOSITORY" new old e n
  case "$repo" in /*) ;; *) return 0 ;; esac
  new="$repo/$PULL_DIR_NAME.new"; old="$repo/$PULL_DIR_NAME.old"
  rm -rf "$new" "$old"
  if ! { mkdir "$new" && for e in config keys snapshots index data; do cp -al "$repo/$e" "$new/$e"; done; } 2>"$STAGE/pull.err"; then
    log "ATTENTION: copie pour le PC non rafraichie : $(tail -n 1 "$STAGE/pull.err")" >&2
    rm -rf "$new"; return 0
  fi
  n="$(find "$new" -type f | wc -l | tr -d ' ')"
  echo "{\"ts\":$(date +%s),\"files\":$n}" > "$new/PULL_MANIFEST.json"
  [ -e "$repo/$PULL_DIR_NAME" ] && mv "$repo/$PULL_DIR_NAME" "$old"
  mv "$new" "$repo/$PULL_DIR_NAME"
  rm -rf "$old"
  log "copie pour le PC rafraichie : $n fichiers (liens physiques, $PULL_DIR_NAME)"
}

# retry <commande...> : jusqu'a BACKUP_RETRY_TRIES essais (defaut 3), BACKUP_RETRY_DELAY s entre deux
# (defaut 60). Pour les operations IDEMPOTENTES sur le reseau (copy, forget, prune) : une coupure
# SFTP passagere ne fait pas perdre l'envoi d'une semaine.
retry() {
  local tries="${BACKUP_RETRY_TRIES:-3}" delay="${BACKUP_RETRY_DELAY:-60}" i=1 rc=0
  while :; do
    rc=0; "$@" || rc=$?
    [ "$rc" -eq 0 ] && return 0
    if [ "$i" -ge "$tries" ]; then return "$rc"; fi
    log "essai $i/$tries echoue (code $rc) : nouvel essai dans ${delay} s" >&2
    sleep "$delay"; i=$((i+1))
  done
}

forget_hourly() { # sans --prune : instantane
  restic forget --tag hourly --group-by tags --keep-last "$KEEP_HOURLY" \
    "$@"
}
forget_nightly() {
  restic forget --tag nightly --group-by tags --keep-daily "$KEEP_DAILY" \
    --keep-weekly "$KEEP_WEEKLY" --keep-monthly "$KEEP_MONTHLY" "$@"
}

# offsite_setup : prepare OFF (depot distant), OPTS (options restic -o sftp.command=...),
# SSH_BASE (commande ssh) et OFFPW (mot de passe du depot distant) d'apres l'environnement.
# OFFSITE_REPOSITORY (essais) remplace la configuration SFTP.
OPTS=(); SSH_BASE=(); OFF=""; OFFPW=""
offsite_setup() {
  OFFPW="${RESTIC_OFFSITE_PASSWORD:-$RESTIC_PASSWORD}"
  if [ -n "${OFFSITE_REPOSITORY:-}" ]; then
    OFF="$OFFSITE_REPOSITORY"
    return 0
  fi
  [ -n "${BACKUP_SFTP_HOST:-}" ] && [ -n "${BACKUP_SFTP_USER:-}" ] && [ -n "${BACKUP_SFTP_PATH:-}" ]     || die "envoi hors serveur non configure (BACKUP_SFTP_HOST, BACKUP_SFTP_USER, BACKUP_SFTP_PATH dans deploy/.env)"
  local key="${BACKUP_SFTP_KEY:-/home/backup/.ssh/id_sftp}" kh="${BACKUP_SFTP_KNOWN_HOSTS:-/home/backup/.ssh/known_hosts}"
  [ -s "$key" ] || die "cle privee SFTP absente ou vide ($key) : fichier deploy/secrets/backup_sftp_key non monte ?"
  [ -s "$kh" ] || die "known_hosts absent ou vide ($kh) : l'empreinte du serveur Hostinger doit etre epinglee"
  SSH_BASE=(ssh -p "${BACKUP_SFTP_PORT:-22}" -i "$key" -o IdentitiesOnly=yes -o BatchMode=yes
            -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$kh"
            -o ServerAliveInterval=30 -o ServerAliveCountMax=6 "${BACKUP_SFTP_USER}@${BACKUP_SFTP_HOST}")
  OFF="sftp:${BACKUP_SFTP_USER}@${BACKUP_SFTP_HOST}:${BACKUP_SFTP_PATH}"
  OPTS=(-o "sftp.command=${SSH_BASE[*]} -s sftp")
}
