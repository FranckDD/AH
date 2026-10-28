#!/bin/bash
# Point d'entree du conteneur backup.
#  - sans argument (ou "cron") : prepare le depot, genere la planification depuis l'environnement,
#    fait un premier export si le dernier a plus de 30 min, puis lance supercronic.
#  - avec un argument : execute la commande telle quelle (ex. "restore.sh latest /tmp/r"),
#    sans toucher au depot ni lancer la planification.
set -Eeuo pipefail
export PATH="/opt/backup:$PATH"

# --- Secrets SFTP (copies avec les bons droits ; ssh exige 0600) : aussi pour restore.sh --from-offsite
sshdir=/home/backup/.ssh
# Si le fichier n'existe pas sur le serveur au premier "up", Docker cree un DOSSIER a sa place :
# message clair plutot qu'une erreur ssh incomprehensible plus tard.
for sec in backup_sftp_key backup_known_hosts restic_password; do
  if [ -d "/run/secrets/$sec" ]; then
    echo "BACKUP-ECHEC job=entrypoint : /run/secrets/$sec est un DOSSIER, pas un fichier : le fichier source n'existait pas sur le serveur quand Docker a monte le conteneur. Sur l'hote : supprimer ce dossier (sudo rmdir deploy/secrets/$sec), creer le vrai fichier (voir docs/exploitation/sauvegardes.md, section 3) puis relancer le service." >&2
    exit 78
  fi
done
if [ "${1:-cron}" = "cron" ] && [ -n "${BACKUP_SFTP_HOST:-}" ]; then
  for sec in backup_sftp_key backup_known_hosts; do
    [ -s "/run/secrets/$sec" ] || { echo "BACKUP-ECHEC job=entrypoint : /run/secrets/$sec absent ou vide alors que l'envoi hors serveur est configure (BACKUP_SFTP_HOST). Creer le fichier deploy/secrets/$sec (docs/exploitation/sauvegardes.md, section 3) ou vider BACKUP_SFTP_HOST pour desactiver l'envoi." >&2; exit 78; }
  done
fi
if [ -f /run/secrets/backup_sftp_key ] && [ -s /run/secrets/backup_sftp_key ]; then
  install -m 0600 /run/secrets/backup_sftp_key "$sshdir/id_sftp" 2>/dev/null     || echo "ATTENTION: cle SFTP illisible par l'uid $(id -u) (chown 10001 deploy/secrets/backup_sftp_key)" >&2
fi
if [ -f /run/secrets/backup_known_hosts ] && [ -s /run/secrets/backup_known_hosts ]; then
  install -m 0644 /run/secrets/backup_known_hosts "$sshdir/known_hosts" 2>/dev/null || true
fi

if [ "${1:-cron}" != "cron" ]; then exec "$@"; fi

. /opt/backup/lib.sh
JOB=entrypoint
trap 'echo "BACKUP-ECHEC job=entrypoint : ${ERRMSG:-demarrage impossible (ligne $LINENO)}" >&2' ERR

# --- 1. Depot local : doit etre un dossier ecrivable (propre a l'uid 10001)
[ -d "$RESTIC_REPOSITORY" ] || die "dossier du depot absent : $RESTIC_REPOSITORY"
if [ ! -w "$RESTIC_REPOSITORY" ]; then
  die "le dossier du depot n'est pas ecrivable par l'uid $(id -u). Sur l'hote : sudo install -d -o 10001 -g 10001 -m 0700 \$BACKUP_REPO_DIR (voir docs/exploitation/sauvegardes.md)"
fi
load_password
if [ ! -e "$RESTIC_REPOSITORY/config" ]; then
  if [ -n "$(ls -A "$RESTIC_REPOSITORY" 2>/dev/null)" ]; then
    die "$RESTIC_REPOSITORY n'est pas vide mais ne contient pas de depot restic (config absent) : refus d'initialiser"
  fi
  log "depot absent : initialisation (restic init, format stable = v2)"
  restic init
fi
require_repo

[ -s "$sshdir/id_sftp" ] || log "ATTENTION: pas de cle SFTP : l'envoi hebdomadaire hors serveur echouera"

# --- 3. Planification generee depuis les variables
export BACKUP_HOURLY_CRON="${BACKUP_HOURLY_CRON:-7 * * * *}"
export BACKUP_NIGHTLY_CRON="${BACKUP_NIGHTLY_CRON:-30 2 * * *}"
export BACKUP_OFFSITE_CRON="${BACKUP_OFFSITE_CRON:-30 4 * * 0}"
export BACKUP_VERIFY_CRON="${BACKUP_VERIFY_CRON:-15 5 * * 3}"
tpl="$(cat /opt/backup/crontab)"
for v in BACKUP_HOURLY_CRON BACKUP_NIGHTLY_CRON BACKUP_OFFSITE_CRON BACKUP_VERIFY_CRON; do
  val="${!v}"
  [[ "$val" =~ ^[0-9*/,@A-Za-z-]+( [0-9*/,A-Za-z-]+){4}$ || "$val" =~ ^@(hourly|daily|weekly|monthly)$ ]] \
    || die "$v invalide : '$val' (attendu : 5 champs cron, ex. 7 * * * *)"
  tpl="${tpl//@${v}@/$val}"
done
printf '%s\n' "$tpl" > /tmp/ah2-crontab
supercronic -test /tmp/ah2-crontab || die "planification invalide (supercronic -test)"
log "planification :"; grep -v '^#' /tmp/ah2-crontab | sed 's/^/    /'

# --- 4. Etat initial : un export tout de suite si le dernier a plus de 30 min
last="$(cat "$STATUS_DIR/last_success_hourly" 2>/dev/null || echo 0)"
if [ $(( $(date +%s) - last )) -gt 1800 ]; then
  log "dernier export horaire absent ou ancien : export immediat"
  /opt/backup/hourly.sh || log "ATTENTION: l'export initial a echoue (le conteneur reste actif et reessaiera a l'heure prevue)"
fi

trap - ERR
exec supercronic /tmp/ah2-crontab
