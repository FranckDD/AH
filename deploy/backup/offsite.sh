#!/bin/bash
# Envoi HEBDOMADAIRE du depot local vers Hostinger (SFTP), par "restic copy" (incremental,
# deja chiffre, depot distant au meme format). Choisi pour limiter le NOMBRE DE FICHIERS
# chez Hostinger (limite 600 000, dont 60 000 deja pris) : paquets de BACKUP_OFFSITE_PACK_SIZE Mo,
# seuls les exports de nuit des BACKUP_OFFSITE_WINDOW_DAYS derniers jours + le dernier export
# horaire sont copies, retention distante reglee par OFFSITE_KEEP_* puis prune + regroupement
# des petits paquets. Voir docs/exploitation/sauvegardes.md (mesures).
#
# Variables : BACKUP_SFTP_HOST, BACKUP_SFTP_USER, BACKUP_SFTP_PATH, BACKUP_SFTP_PORT (22),
# cle privee /home/backup/.ssh/id_sftp et known_hosts /home/backup/.ssh/known_hosts (copies par
# entrypoint.sh depuis /run/secrets/). OFFSITE_REPOSITORY (essais) remplace tout cela par un
# depot local ou un autre depot restic. RESTIC_OFFSITE_PASSWORD (defaut RESTIC_PASSWORD).
#
# Verrou : meme verrou "repo" que hourly/nightly/verify (un chevauchement ATTEND, jusqu'a
# BACKUP_LOCK_WAIT = 1 h par defaut ; restic pose en plus ses verrous avec --retry-lock). Pendant
# qu'il envoie, un hourly/nightly attend donc sa fin : un envoi hebdomadaire normal dure quelques
# minutes. Coupures SFTP passageres : chaque operation reseau est reessayee (BACKUP_RETRY_TRIES=3,
# BACKUP_RETRY_DELAY=60 s).
# Marqueur last_success_offsite : ecrit SEULEMENT quand copie + retention distante + prune sont
# termines. Fenetre : les nuits des BACKUP_OFFSITE_WINDOW_DAYS (21) derniers jours sont copiees
# (plus que 2 semaines de pannes ne creent donc pas de trou) ; l'alerte (tache 10) se declenche
# apres 8 jours sans succes.
. "$(dirname "$0")/lib.sh"
job_start offsite repo
check_keep
require_repo

LOCAL="$RESTIC_REPOSITORY"
PACK="${BACKUP_OFFSITE_PACK_SIZE:-32}"
WINDOW_DAYS="${BACKUP_OFFSITE_WINDOW_DAYS:-21}"
OFF_KEEP_HOURLY="${OFFSITE_KEEP_HOURLY:-2}"
offsite_setup
ro() { # restic sur le depot DISTANT
  RESTIC_REPOSITORY="$OFF" RESTIC_PASSWORD="$OFFPW" RESTIC_PACK_SIZE="$PACK" restic "${OPTS[@]}" "$@"
}
rc_copy() { # restic copy : source = depot local
  ro copy --from-repo "$LOCAL" "$@"
}
export RESTIC_FROM_PASSWORD="$RESTIC_PASSWORD"

log "depot distant : ${OFF}"
tries="${BACKUP_RETRY_TRIES:-3}"; n=1
while :; do
  if out="$(ro cat config 2>&1 >/dev/null)"; then break; fi
  case "$out" in
    *"wrong password"*|*"no key found"*) die "mot de passe du depot DISTANT incorrect : rien n'a ete ecrit" ;;
    # erreur de TRANSPORT (hote, cle, empreinte, session sftp) : jamais une raison de creer un depot
    *"unable to start the sftp"*|*"Could not resolve"*|*"Permission denied"*|*"Connection "*|*"Host key verification"*|*"timed out"*)
      [ "$n" -lt "$tries" ] || die "depot distant inaccessible (reseau, cle ou empreinte) : $(printf '%s' "$out" | tail -n 2 | tr -s '[:space:]' ' ')"
      log "depot distant injoignable (essai $n/$tries) : $(printf '%s' "$out" | tail -n 1) ; nouvel essai dans ${BACKUP_RETRY_DELAY:-60} s"
      sleep "${BACKUP_RETRY_DELAY:-60}"; n=$((n+1)) ;;
    *"Is there a repository"*)
      log "depot distant absent : initialisation (memes parametres de decoupage que le depot local)"
      retry ro init --from-repo "$LOCAL" --copy-chunker-params || die "initialisation du depot distant impossible"
      break ;;
    *)
      [ "$n" -lt "$tries" ] || die "depot distant inaccessible : $(printf '%s' "$out" | tr -s '[:space:]' ' ' | tail -c 300)"
      log "depot distant injoignable (essai $n/$tries) : $(printf '%s' "$out" | tail -n 1) ; nouvel essai dans ${BACKUP_RETRY_DELAY:-60} s"
      sleep "${BACKUP_RETRY_DELAY:-60}"; n=$((n+1)) ;;
  esac
done
ro unlock >/dev/null 2>&1 || true

# Snapshots a envoyer : nuits recentes + dernier export horaire.
ids="$( { restic snapshots --tag nightly --json \
            | jq -r --argjson w $((WINDOW_DAYS * 86400)) --argjson n "${BACKUP_FAKE_NOW:-$(date +%s)}" \
                "$JQ_DEFS"' .[] | select(($n - (.time | ts)) < $w) | .id'
          restic snapshots --tag hourly --json | jq -r "$JQ_DEFS"' sort_by(.time | ts) | last | .id // empty'
        } | sort -u )"
[ -n "$ids" ] || die "aucun snapshot local a envoyer"
log "snapshots a envoyer : $(printf '%s' "$ids" | wc -l) (deja presents : ignores par restic)"
# shellcheck disable=SC2086
retry rc_copy $ids

log "retention distante (nuits : ${KEEP_DAILY}j/${KEEP_WEEKLY}s/${KEEP_MONTHLY}m ; horaires : ${OFF_KEEP_HOURLY})"
retry ro forget --tag nightly --group-by tags --keep-daily "$KEEP_DAILY" --keep-weekly "$KEEP_WEEKLY" \
  --keep-monthly "$KEEP_MONTHLY"
retry ro forget --tag hourly --group-by tags --keep-last "$OFF_KEEP_HOURLY"
retry ro prune --repack-smaller-than "${PACK}m" --max-unused 10%

nsnap="$(retry ro snapshots --json | jq 'length')"

# Mesure du depot distant : fichiers, dossiers, octets.
files=-1; dirs=-1; bytes=-1
if [ -n "${OFFSITE_REPOSITORY:-}" ]; then
  case "$OFF" in /*) files="$(find "$OFF" -type f | wc -l)"; dirs="$(find "$OFF" -type d | wc -l)"
                     bytes=$(( $(du -sk "$OFF" | cut -f1) * 1024 )) ;; esac
else
  # shell distant (Hostinger l'autorise) ; si indisponible, la mesure est "inconnue" sans echec.
  if m="$("${SSH_BASE[@]}" "p='${BACKUP_SFTP_PATH}'; find \"\$p\" -type f | wc -l; find \"\$p\" -type d | wc -l; du -sk \"\$p\" | cut -f1" 2>/dev/null)"; then
    f1="$(printf '%s\n' "$m" | sed -n 1p | tr -d ' ')"; d1="$(printf '%s\n' "$m" | sed -n 2p | tr -d ' ')"; k1="$(printf '%s\n' "$m" | sed -n 3p | tr -d ' ')"
    # une mesure illisible reste "inconnue" (-1) : elle ne fait jamais echouer un envoi reussi
    if [[ "$f1" =~ ^[0-9]+$ && "$d1" =~ ^[0-9]+$ && "$k1" =~ ^[0-9]+$ ]]; then files="$f1"; dirs="$d1"; bytes=$(( k1 * 1024 )); fi
  fi
fi
log "depot distant : snapshots=$nsnap fichiers=$files dossiers=$dirs octets=$bytes (limite Hostinger : 600000 fichiers en tout)"
atomic_write "$STATUS_DIR/offsite_stats.json" \
  "$(jq -nc --argjson ts "$(date +%s)" --argjson f "$files" --argjson d "$dirs" --argjson b "$bytes" --argjson s "$nsnap" \
        '{ts:$ts, files:$f, dirs:$d, bytes:$b, snapshots:$s}')"
mark_success
