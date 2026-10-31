#!/usr/bin/env bash
# Essai de sauvegarde / restauration (tache 9) : pile MINIMALE (db + backup) du compose de
# production, projet "ah2backuptest" (ne touche jamais la pile de developpement), depot restic
# LOCAL, serveur SFTP jetable (sshd Alpine, ~10 Mo) pour l'envoi hebdomadaire.
#
#   bash deploy/tests/test_backup_restore.sh [--keep] [--no-build] [--weeks N] [--down]
#
#   --keep       laisse tout en place a la fin (pile, volumes, images)
#   --no-build   reutilise l'image ghcr.io/rehearsal/ah2-backup:local deja construite
#   --weeks N    duree de la simulation de volumetrie (defaut 12 semaines ; 2 suffit pour un essai
#                de non-regression, la simulation est alors ~6 fois plus courte)
#   --down       ne fait QUE nettoyer
#
# Prerequis : docker compose v2, images locales postgres:17.6-bookworm et
# ghcr.io/rehearsal/ah2-api:local (celle de deploy/smoke.sh --build : elle contient init_prod_db.sh),
# acces reseau pour construire (restic, supercronic) la premiere fois. Disque : refuse de
# demarrer sous 3 Go libres.
#
# Ce qui n'est PAS verifie ici (tache 14) : le vrai SFTP Hostinger (port, quotas, droits de
# find/du, limite de fichiers), la reprise de PowerSync apres restauration, le pull du PC admin.
set -uo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'

PROJECT=ah2backuptest
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"

WORK="deploy/.backup-test-work"   # relatif a la racine (docker.exe ne comprend pas /c/...)
ENVF="$WORK/test.env"
OVR="$WORK/override.yml"
COMPOSE_FILE="deploy/docker-compose.prod.yml"
IMG="ghcr.io/rehearsal/ah2-backup:local"
API_IMG="ghcr.io/rehearsal/ah2-api:local"
SSHD_IMG="ah2backuptest-sshd:local"
SSHD="${PROJECT}-sshd"
NET="${PROJECT}_ah2"
KEEP=0; BUILD=1; WEEKS=12; ONLY_DOWN=0; ONLY_PULL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --keep) KEEP=1 ;; --no-build) BUILD=0 ;; --down) ONLY_DOWN=1 ;; --only-pull) ONLY_PULL=1 ;;
    --weeks) shift; WEEKS="$1" ;;
    -h|--help) sed -n '2,19p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Option inconnue : $1" >&2; exit 64 ;;
  esac
  shift
done

free_gb() { df -P -k /c 2>/dev/null | awk 'NR==2{printf "%.1f", $4/1048576}'; }
disk_guard() {
  local g; g="$(free_gb)"
  if awk -v g="${g:-0}" 'BEGIN{exit !(g < 3)}'; then echo "ARRET: seulement ${g} Go libres sur C: (< 3 Go)" >&2; exit 70; fi
}

# gen_env ecrit un .env jetable ; les valeurs sont fausses et ne servent qu'ici.
gen_env() {
  local hex; hex() { openssl rand -hex 24; }
  mkdir -p "$WORK"
  cat > "$ENVF" <<EOF
DOMAIN=localhost
GHCR_OWNER=rehearsal
IMAGE_TAG=local
POSTGRES_USER=ah2
POSTGRES_DB=AH2
POSTGRES_PASSWORD=$(hex)
POWERSYNC_REPL_PASSWORD=$(hex)
REDIS_PASSWORD=$(hex)
JWT_SECRET=$(openssl rand -base64 32)
JWT_ALGORITHM=HS256
PS_PORT=8080
PS_ADMIN_TOKEN=$(openssl rand -base64 32)
PG_STORAGE_USER=powersync
PG_STORAGE_DB=powersync_storage
PG_STORAGE_PASSWORD=$(hex)
ACME_EMAIL=backuptest@example.test
RESTIC_PASSWORD=test-$(hex)
BACKUP_HOURLY_CRON="0 0 1 1 *"
BACKUP_NIGHTLY_CRON="5 0 1 1 *"
BACKUP_OFFSITE_CRON="10 0 1 1 *"
BACKUP_VERIFY_CRON="15 0 1 1 *"
BACKUP_SFTP_HOST=sshd
BACKUP_SFTP_USER=hostinger
BACKUP_SFTP_PATH=backups/ah2
BACKUP_SFTP_PORT=2222
BACKUP_SFTP_KEY_FILE=./.backup-test-work/sftp_key
BACKUP_KNOWN_HOSTS_FILE=./.backup-test-work/known_hosts
EOF
  # Les trois volumes de fichiers et le statut sont ceux du compose de production ; seul le
  # depot (dossier hote en production) devient un volume nomme pour l'essai.
  cat > "$OVR" <<'EOF'
services:
  backup:
    volumes: !override
      - bk_repo:/backups/repo
      - uploads:/data/uploads:ro
      - product_photos:/data/product_photos:ro
      - consents:/data/consents:ro
      - backup_status:/var/lib/ah2-status
      - ${BACKUP_SFTP_KEY_FILE}:/run/secrets/backup_sftp_key:ro
      - ${BACKUP_KNOWN_HOSTS_FILE}:/run/secrets/backup_known_hosts:ro
volumes:
  bk_repo:
EOF
}

C() { docker compose -p "$PROJECT" --env-file "$ENVF" -f "$COMPOSE_FILE" -f "$OVR" "$@"; }

cleanup() {
  docker rm -f "$SSHD" >/dev/null 2>&1 || true
  if [ -f "$ENVF" ]; then C down -v --remove-orphans >/dev/null 2>&1 || true; fi
  for v in rootvol cronvol safety; do docker volume rm -f "${PROJECT}_$v" >/dev/null 2>&1 || true; done
  rm -rf "$WORK" "${PULLT:-/nonexistent-pullt}"
  if [ "$KEEP" = 0 ]; then
    docker rmi -f "$SSHD_IMG" "$IMG" >/dev/null 2>&1 || true
  fi
}

if [ "$ONLY_DOWN" = 1 ]; then
  [ -f "$ENVF" ] || gen_env
  KEEP=0; cleanup; echo "Pile $PROJECT supprimee (volumes, sshd, images)."; exit 0
fi
[ "$ONLY_PULL" = 1 ] || disk_guard
rm -rf "$WORK"; gen_env
[ "$KEEP" = 1 ] || [ "$ONLY_PULL" = 1 ] || trap cleanup EXIT
# shellcheck disable=SC1090
set -a; . "$ENVF"; set +a

NPASS=0; NFAIL=0; FAILED=()
pass() { NPASS=$((NPASS+1)); echo "PASS  $1  [$2]"; }
fail() { NFAIL=$((NFAIL+1)); FAILED+=("$1"); echo "FAIL  $1  [$2]"; }
eqs() { # comme eq, mais n'affiche que l'empreinte des valeurs (listes longues)
  if [ "$2" = "$3" ]; then pass "$1" "identique, md5=$(printf '%s' "$3" | md5sum | cut -c1-12), $(printf '%s
' "$3" | wc -l | tr -d ' ') lignes"
  else fail "$1" "difference : $(diff <(printf '%s
' "$2") <(printf '%s
' "$3") | head -6 | tr '
' '|')"; fi
}
eq() { if [ "$2" = "$3" ]; then pass "$1" "obtenu=$3"; else fail "$1" "attendu=$2 obtenu=$3"; fi; }
ne() { if [ "$2" != "$3" ]; then pass "$1" "$3"; else fail "$1" "doit differer de $2"; fi; }
info() { echo "INFO  $1  [$2]"; }
section() { echo; echo "=== $* ==="; }
need() { "$@" || { echo "ARRET: echec de : $*" >&2; exit 1; }; }

# --- aides ---------------------------------------------------------------------------------
BK() { C exec -T backup "$@"; }                      # dans le conteneur backup (uid 10001)
bkenv() { # bkenv "A=1 B=2" commande... : avec variables supplementaires
  local envs=() kv; for kv in $1; do envs+=(-e "$kv"); done; shift
  C exec -T "${envs[@]}" backup "$@"
}
psqld() { C exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -X -At -v ON_ERROR_STOP=1 "$@"; }
COUNT_SQL="select table_name||'='||(xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by table_name"
counts() { psqld -c "$COUNT_SQL" | tr -d '\r'; }
nonzero_counts() { grep -v '=0$'; }
nsnap() { BK sh -c "restic snapshots --tag $1 --json | jq length" | tr -d '\r\n'; }
repo_sig() { BK sh -c "find ${1:-/backups/repo} | sort | md5sum" | tr -d '\r\n '; }
statusval() { BK sh -c "cat /var/lib/ah2-status/$1 2>/dev/null || echo none" | tr -d '\r\n'; }
cid() { C ps -q "$1" | tr -d '\r\n'; }
wait_healthy() { # wait_healthy service secondes
  local i=0 st; while [ "$i" -lt "$2" ]; do
    st="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$(cid "$1")" 2>/dev/null | tr -d '\r\n')"
    [ "$st" = healthy ] && return 0
    [ "$(docker inspect --format '{{.RestartCount}}' "$(cid "$1")" 2>/dev/null | tr -d '
')" -ge 2 ] 2>/dev/null && return 1   # boucle de redemarrage
    sleep 3; i=$((i+3)); done; return 1
}
# Conteneur d'aide root avec les trois volumes de fichiers en ecriture sous /data/<nom>
VOLS() { echo "-v ${PROJECT}_uploads:/data/uploads -v ${PROJECT}_product_photos:/data/product_photos -v ${PROJECT}_consents:/data/consents"; }
vr() { # vr "script" : root, volumes en ecriture, pas de reseau
  # shellcheck disable=SC2046
  docker run --rm --user 0 --entrypoint bash $(VOLS) "$IMG" -c "$1"
}
MANIFEST='cd /data && find uploads product_photos consents -type f | sort | while IFS= read -r f; do sha256sum "$f"; done'

# --- P. pull_backups.ps1 : syntaxe (analyseur PowerShell) et comportement (scp factice) -------
# Le script est lance par Windows PowerShell 5.1 (celui de la tache planifiee). "scp" est un vrai
# programme natif factice (scp.cmd -> PowerShell) qui ecrit sur stderr et sort avec un code :
# c'est exactement le cas qui cassait avec $ErrorActionPreference='Stop' + 2>&1.
pull_tests() {
  local PSF_WIN W
  PSF_WIN="$(cygpath -w "$ROOT/deploy/backup/pull_backups.ps1" 2>/dev/null || echo "$ROOT/deploy/backup/pull_backups.ps1")"
  PULLT="$(mktemp -d)"; W="$(cygpath -w "$PULLT" 2>/dev/null || echo "$PULLT")"
  local PERR
  PERR="$("$PS51" -NoProfile -Command "\$e=\$null;\$t=\$null;[void][System.Management.Automation.Language.Parser]::ParseFile('$PSF_WIN',[ref]\$t,[ref]\$e); \$e | ForEach-Object { \$_.Message + ' ligne ' + \$_.Extent.StartLineNumber }" 2>&1)"
  if [ -z "$PERR" ]; then pass "pull_backups.ps1 : analyse syntaxique PowerShell sans erreur" "Parser::ParseFile"; else fail "pull_backups.ps1 : syntaxe" "$PERR"; return; fi
  mkdir -p "$PULLT/remote/.pull"; echo k > "$PULLT/key"
  cat > "$PULLT/fake_scp.ps1" <<'PSEOF'
$a = @($args)
$dest = $a[$a.Count - 1]; $src = $a[$a.Count - 2]
$mode = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'mode.txt') -Raw).Trim()
if ($mode -eq 'fail') { [Console]::Error.WriteLine('ssh: connect to host ah2 port 22: Connection refused'); exit 255 }
if ($mode -eq 'flaky') {
  $c = Join-Path $PSScriptRoot 'count.txt'
  if (-not (Test-Path $c)) { Set-Content $c 'x'; [Console]::Error.WriteLine('Connection reset by peer'); exit 1 }
}
$p = ($src -replace '^[^:]+:', '') -replace '/\*$', ''
$local = Join-Path (Join-Path $PSScriptRoot 'remote') (($p -replace '^/srv/ah2-backups/', '') -replace '/', '\')
Copy-Item -Path (Join-Path $local '*') -Destination $dest -Recurse -Force
[Console]::Error.WriteLine('Warning: Permanently added the host key (bruit sur stderr, meme en cas de succes)')
if ($mode -eq 'torn') { Get-ChildItem -LiteralPath (Join-Path $dest 'data') -Recurse -File | Select-Object -First 1 | Remove-Item -Force }
exit 0
PSEOF
  cat > "$PULLT/scp.cmd" <<'CMDEOF'
@echo off
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0fake_scp.ps1" %*
exit /b %ERRORLEVEL%
CMDEOF
  sed -i 's/$/\r/' "$PULLT/scp.cmd"
  mk_remote() { # mk_remote <ko> <marqueur> : faux depot fige cote serveur (+ manifeste)
    local R="$PULLT/remote/.pull" n
    rm -rf "$R"; mkdir -p "$R/keys" "$R/data/00" "$R/snapshots" "$R/index"
    echo cfg > "$R/config"; echo key > "$R/keys/k1"; head -c $(( $1 * 1024 )) /dev/urandom > "$R/data/00/pack1"
    echo "$2" > "$R/snapshots/s1"; echo idx > "$R/index/i1"
    n="$(find "$R" -type f | wc -l | tr -d ' ')"
    echo "{\"ts\":$(date +%s),\"files\":$n}" > "$R/PULL_MANIFEST.json"
  }
  runpull() { # runpull [options...] -> $PRC ; le journal est dans $PULLT/dest/pull_backups.log
    PATH="$PULLT:$PATH" "$PS51" -NoProfile -ExecutionPolicy Bypass -File "$PSF_WIN" -VpsHost ah2.test \
      -KeyFile "$W\\key" -Destination "$W\\dest" -RetryDelaySeconds 1 -MinFreeGB 0.05 "$@" > "$PULLT/run.out" 2>&1
    PRC=$?
  }
  marker() { cat "$PULLT/dest/$1/snapshots/s1" 2>/dev/null | tr -d '\r\n' || true; }
  plog() { cat "$PULLT/dest/pull_backups.log" 2>/dev/null | tr -d '\r'; }
  echo ok > "$PULLT/mode.txt"
  mk_remote 2000 gen1; runpull; eq "pull : 1ere copie (scp ecrit sur stderr malgre le succes) : code 0" "0" "$PRC"; eq "pull : repo = gen1" "gen1" "$(marker repo)"
  mk_remote 2000 gen2; runpull; eq "pull : 2e copie : code 0" "0" "$PRC"; eq "pull : repo = gen2, repo.prev = gen1" "gen2/gen1" "$(marker repo)/$(marker repo.prev)"
  mk_remote 2000 gen3; runpull; eq "pull : 3e copie : trois generations" "gen3/gen2/gen1" "$(marker repo)/$(marker repo.prev)/$(marker repo.prev2)"
  mk_remote 2000 gen4; echo torn > "$PULLT/mode.txt"; runpull
  eq "pull : copie tronquee : code 4" "4" "$PRC"
  eq "pull : copie tronquee : AUCUNE generation touchee (gen3/gen2/gen1)" "gen3/gen2/gen1" "$(marker repo)/$(marker repo.prev)/$(marker repo.prev2)"
  [ -d "$PULLT/dest/repo.rejected" ] && [ ! -d "$PULLT/dest/repo.new" ] && pass "pull : copie rejetee gardee dans repo.rejected, repo.new retire" "ok" || fail "pull : repo.rejected" "$(ls "$PULLT/dest")"
  plog | grep -q "REJET: copie tronquee" && pass "pull : motif du rejet journalise (manifeste)" "$(plog | grep -m1 REJET | cut -c21-120)" || fail "pull : journal du rejet" "$(plog | tail -3)"
  echo fail > "$PULLT/mode.txt"; runpull
  eq "pull : scp en echec (stderr + code 255) : code 3 et non 1" "3" "$PRC"
  plog | grep -q "Connection refused" && pass "pull : texte de stderr de scp dans le journal" "$(plog | grep -m1 'Connection refused' | cut -c21-120)" || fail "pull : stderr journalise" "$(plog | tail -3)"
  grep -qi "NativeCommandError" "$PULLT/run.out" && fail "pull : pas de NativeCommandError" "present" || pass "pull : pas de NativeCommandError (PowerShell 5.1)" "ok"
  eq "pull : echec de copie : generations intactes" "gen3/gen2/gen1" "$(marker repo)/$(marker repo.prev)/$(marker repo.prev2)"
  echo ok > "$PULLT/mode.txt"; mk_remote 300 gen5; runpull
  eq "pull : copie a moins de 70 % de la precedente : code 4" "4" "$PRC"; eq "pull : trop petite : repo inchange" "gen3" "$(marker repo)"
  runpull -Force; eq "pull : -Force accepte la copie plus petite" "0/gen5/gen3" "$PRC/$(marker repo)/$(marker repo.prev)"
  mk_remote 2000 gen6; echo flaky > "$PULLT/mode.txt"; rm -f "$PULLT/count.txt"; runpull -Force
  eq "pull : 1er essai echoue, 2e reussit : code 0" "0/gen6" "$PRC/$(marker repo)"
  plog | grep -q "essai 2/3" && pass "pull : nouvel essai journalise" "ok" || fail "pull : essai 2/3" "$(plog | tail -4)"
  echo ok > "$PULLT/mode.txt"; runpull -DryRun; eq "pull : -DryRun : code 0, rien de modifie" "0/gen6" "$PRC/$(marker repo)"
}
PS51=""
for c in /c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe "$(command -v powershell.exe 2>/dev/null)"; do [ -n "$c" ] && [ -x "$c" ] && { PS51="$c"; break; }; done
if [ -n "$PS51" ] && command -v cygpath >/dev/null 2>&1; then
  section "P. pull_backups.ps1 (Windows PowerShell 5.1, scp factice)"
  pull_tests
else info "PowerShell 5.1 ou cygpath absent" "controles de pull_backups.ps1 ignores"; fi
if [ "$ONLY_PULL" = 1 ]; then
  rm -rf "$WORK" "${PULLT:-/nonexistent-pullt}"
  echo; echo "RESULTAT (pull seul) : PASS=$NPASS FAIL=$NFAIL"; [ "$NFAIL" -eq 0 ] || { printf '  - %s
' "${FAILED[@]}"; exit 1; }; exit 0
fi

# --- 0. image, base neuve, volumes ----------------------------------------------------------
section "0. Preparation"
if [ "$BUILD" = 1 ]; then
  need docker build -q -t "$IMG" deploy/backup >/dev/null && pass "image ah2-backup construite" "$(docker images --format '{{.Size}}' "$IMG")"
fi
docker image inspect "$IMG" >/dev/null 2>&1 || { echo "Image $IMG absente (retirer --no-build)"; exit 1; }
docker image inspect "$API_IMG" >/dev/null 2>&1 || { echo "Image $API_IMG absente : lancer deploy/smoke.sh --build d'abord"; exit 1; }
need C up -d db >/dev/null 2>&1
wait_healthy db 90 && pass "db (postgres 17.6) healthy" "projet $PROJECT" || { fail "db healthy" "timeout"; exit 1; }
if C run --rm --no-deps -T --entrypoint bash api scripts/init_prod_db.sh > "$WORK/init.log" 2>&1; then
  pass "base neuve initialisee (init_prod_db.sh)" "$(tail -3 "$WORK/init.log" | tr '\n' ' ')"
else fail "init_prod_db.sh" "voir $WORK/init.log"; tail -15 "$WORK/init.log"; exit 1; fi
ALEMBIC0="$(psqld -c 'select version_num from public.alembic_version' | tr -d '\r')"
info "alembic_version" "$ALEMBIC0"

# Serveur SFTP jetable (cle d'hote generee a la construction, epinglee dans known_hosts)
mkdir -p "$WORK/sshd"
cat > "$WORK/sshd/Dockerfile" <<'EOF'
FROM alpine:3.22
RUN apk add --no-cache openssh-server \
 && ssh-keygen -A \
 && adduser -D -s /bin/sh hostinger && sed -i 's/^hostinger:!/hostinger:*/' /etc/shadow \
 && mkdir -p /home/hostinger/.ssh /home/hostinger/backups && chown -R hostinger:hostinger /home/hostinger
CMD ["/usr/sbin/sshd", "-D", "-e", "-p", "2222", "-o", "PasswordAuthentication=no", "-o", "StrictModes=no", "-o", "AuthorizedKeysFile=/keys/authorized_keys"]
EOF
need docker build -q -t "$SSHD_IMG" "$WORK/sshd" >/dev/null
docker run --rm --entrypoint sh "$IMG" -c 'ssh-keygen -q -t ed25519 -N "" -C ah2backuptest -f /tmp/k && cat /tmp/k && echo ---PUB--- && cat /tmp/k.pub' > "$WORK/keypair.txt"
sed '/---PUB---/,$d' "$WORK/keypair.txt" > "$WORK/sftp_key"
sed '1,/---PUB---/d' "$WORK/keypair.txt" > "$WORK/authorized_keys"
HOSTPUB="$(docker run --rm --entrypoint cat "$SSHD_IMG" /etc/ssh/ssh_host_ed25519_key.pub | awk '{print $1" "$2}')"
echo "[sshd]:2222 $HOSTPUB" > "$WORK/known_hosts"
echo "[sshd]:2222 $(docker run --rm --entrypoint sh "$IMG" -c 'ssh-keygen -q -t ed25519 -N "" -f /tmp/o && cut -d" " -f1,2 /tmp/o.pub')" > "$WORK/known_hosts_BAD"
chmod 600 "$WORK/sftp_key" 2>/dev/null || true
need docker run -d --name "$SSHD" --network "$NET" --network-alias sshd -v "$(cd "$WORK" && pwd -W 2>/dev/null || pwd):/keys:ro" "$SSHD_IMG" >/dev/null
sleep 2; docker ps --format '{{.Names}}' | grep -q "^$SSHD$" && pass "serveur SFTP jetable demarre" "alpine openssh, port 2222, cle d'hote epinglee" || { fail "sshd" "$(docker logs "$SSHD" 2>&1 | tail -3)"; }

# --- 1. donnees connues ----------------------------------------------------------------------
section "1. Donnees connues (base + 3 volumes)"
need psqld <<'SQL' >/dev/null
INSERT INTO users(username,password_hash,full_name,postgres_role,is_active) VALUES
  ('bk_user1','x','Backup Utilisateur Un','app_secretaire',true),('bk_user2','x','Backup Utilisateur Deux','app_admin',true);
INSERT INTO patients(first_name,last_name,birth_date,gender,created_by_name)
  SELECT 'Prenom'||g,'Nom'||g,date '1990-01-01'+g,'M','seed' FROM generate_series(1,200) g;
INSERT INTO caisse(patient_id,amount,created_by_name,handled_by,payment_method,transaction_type)
  SELECT patient_id,1000+patient_id,'seed',(SELECT user_id FROM users WHERE username='bk_user1'),'cash','consultation'
  FROM patients ORDER BY patient_id LIMIT 50;
SQL
C0="$(counts)"; info "lignes initiales (tables non vides)" "$(echo "$C0" | nonzero_counts | tr '\n' ' ')"
eq "patients initiaux" "patients=200" "$(echo "$C0" | grep '^patients=')"
need C create backup >/dev/null 2>&1       # cree les volumes uploads / product_photos / consents / bk_repo
need vr 'mk() { head -c "$2" /dev/urandom > "$1"; }
cd /data
mkdir -p uploads/ticket_logos product_photos/2026 consents/2026/10
mk uploads/ticket_logos/logo.bin 1048576          # 1 Mo aleatoire
echo "texte accentue: eleve, cafe" > uploads/note.txt
mk product_photos/2026/photo1.jpg 307200
mk "product_photos/2026/photo avec espace.jpg" 4096
mk consents/2026/10/consent1.pdf 200000
chown -R 10001:10001 /data' >/dev/null
M1="$(vr "$MANIFEST" | tr -d '\r')"
eq "volumes remplis (fichiers)" "5" "$(echo "$M1" | wc -l | tr -d ' ')"

# --- 2. demarrage reel du service backup ------------------------------------------------------
section "2. Service backup (entrypoint reel, sonde, planification)"
need C up -d backup >/dev/null 2>&1
if wait_healthy backup 180; then pass "backup healthy (sonde last_success_hourly < 2 h)" "export initial fait par l'entrypoint"
else fail "backup healthy" "$(C logs --tail 15 backup 2>&1 | tr '\n' '|')"; C logs --tail 30 backup; exit 1; fi
eq "depot restic initialise (format 2)" "2" "$(BK sh -c 'restic cat config --json | jq .version' | tr -d '\r\n')"
CRON="$(BK cat /tmp/ah2-crontab | grep -v '^#' | tr -d '\r')"
case "$CRON" in *"0 0 1 1 * /opt/backup/hourly.sh"*"5 0 1 1 * /opt/backup/nightly.sh"*"10 0 1 1 * /opt/backup/offsite.sh"*) pass "crontab genere depuis les variables" "$(echo "$CRON" | head -1)" ;; *) fail "crontab genere" "$CRON" ;; esac
eq "TZ du conteneur" "WAT" "$(BK date +%Z | tr -d '\r\n')"
eq "service tourne sous l'uid" "10001" "$(BK id -u | tr -d '\r\n')"
eq "volumes de fichiers en lecture seule" "ro" "$(BK sh -c 'touch /data/uploads/x 2>/dev/null && echo rw || echo ro' | tr -d '\r\n')"
eq "1 export horaire initial" "1" "$(nsnap hourly)"
eq "tag db sur l'export" "1" "$(BK sh -c "restic snapshots --tag hourly,db --json | jq length" | tr -d '\r\n')"

# --- 3. hourly (H1) puis ecritures, nightly (N), ecriture, hourly (H2) -----------------------
section "3. hourly / nightly (un snapshot unique = base + fichiers)"
need BK /opt/backup/hourly.sh >/dev/null 2>&1; pass "hourly.sh (H1)" "last_success_hourly=$(statusval last_success_hourly)"
H1="$(BK sh -c 'restic snapshots --tag hourly --json | jq -r "sort_by(.time)|last|.id"' | tr -d '\r\n')"
eq "H1 porte les etiquettes hourly,db,files" "db,files,hourly" "$(BK sh -c "restic snapshots $H1 --json | jq -r '.[0].tags | sort | join(\",\")'" | tr -d '\r\n')"
eq "H1 contient les 5 fichiers de depart" "5" "$(BK sh -c "restic ls $H1 | grep -cE '[.](bin|txt|jpg|pdf)\$'" | tr -d '\r\n')"
psqld -c "INSERT INTO patients(first_name,last_name,birth_date,created_by_name) SELECT 'NuitAvant'||g,'N',date '1991-01-01','seed' FROM generate_series(1,5) g" >/dev/null
need vr 'cd /data; head -c 65536 /dev/urandom > uploads/after_h1.bin; head -c 5000 /dev/urandom > consents/2026/10/consent2.pdf; chown -R 10001:10001 /data' >/dev/null
need bkenv "PRUNE=1" /opt/backup/nightly.sh >/dev/null 2>&1; pass "nightly.sh (N, avec prune)" "last_success_nightly=$(statusval last_success_nightly)"
eq "nightly : UN snapshot (nightly,db,files)" "1" "$(nsnap nightly)"
eq "nightly : etiquettes db et files sur le meme snapshot" "1" "$(BK sh -c "restic snapshots --tag nightly,db,files --json | jq length" | tr -d '\r\n')"
MN="$(vr "$MANIFEST" | tr -d '\r')"; eq "fichiers apres la nightly" "7" "$(echo "$MN" | wc -l | tr -d ' ')"
N_DB="$(BK sh -c 'restic snapshots --tag nightly,db --json | jq -r ".[0].id"' | tr -d '\r\n')"
# ecritures APRES la nuit : une ligne ET une nouvelle photo
need psqld -c "INSERT INTO patients(first_name,last_name,birth_date,created_by_name) VALUES ('APRES_NIGHTLY','Marqueur',date '1992-02-02','seed')" >/dev/null
need vr 'cd /data; head -c 120000 /dev/urandom > product_photos/2026/after_nightly_photo.jpg; chown -R 10001:10001 /data' >/dev/null
KB0="$(BK sh -c 'du -sk /backups/repo | cut -f1' | tr -d '\r\n')"; T0="$(date +%s%N)"
need BK /opt/backup/hourly.sh >/dev/null 2>&1; T1="$(date +%s%N)"; pass "hourly.sh (H2, apres une ecriture et une photo posterieures a la nightly)" "ok"
KB1="$(BK sh -c 'du -sk /backups/repo | cut -f1' | tr -d '\r\n')"
info "MESURE hourly avec changement (1 ligne, 1 photo de 120 Ko) : duree (docker exec compris)" "$(( (T1-T0)/1000000 )) ms ; depot $KB0 -> $KB1 Ko"
H2="$(BK sh -c 'restic snapshots --tag hourly --json | jq -r "sort_by(.time)|last|.id"' | tr -d '\r\n')"
ne "H2 est un nouveau snapshot" "$H1" "$H2"
M2="$(vr "$MANIFEST" | tr -d '\r')"; eq "fichiers apres H2 (photo posterieure incluse)" "8" "$(echo "$M2" | wc -l | tr -d ' ')"
C2="$(counts)"; info "lignes finales (a retrouver apres restauration)" "$(echo "$C2" | nonzero_counts | tr '\n' ' ')"
eq "patients attendus" "patients=206" "$(echo "$C2" | grep '^patients=')"

# restauration sans application dans un dossier : base ET fichiers du MEME snapshot
RO="$(BK /opt/backup/restore.sh latest /tmp/r1 2>&1)"; RRC=$?
eq "restore.sh latest <dossier> (sans application) : code 0" "0" "$RRC"
IDDB="$(echo "$RO" | sed -n 's/.*export de base (snapshot \([0-9a-f]*\)).*/\1/p' | head -1)"
IDFI="$(echo "$RO" | sed -n 's/.*des fichiers (snapshot \([0-9a-f]*\)).*/\1/p' | head -1)"
eq "latest : la base et les fichiers viennent du MEME snapshot" "$IDDB" "$IDFI"
eq "latest : ce snapshot est H2 (le plus recent)" "${H2:0:8}" "${IDDB:0:8}"
R1="$(BK sh -c "cd /tmp/r1/files/data && find uploads product_photos consents -type f | sort | while IFS= read -r f; do sha256sum \"\$f\"; done" | tr -d '\r')"
eqs "restore latest : memes empreintes que le volume au moment de H2 (photo posterieure comprise)" "$M2" "$R1"
need BK /opt/backup/restore.sh "$N_DB" /tmp/r_n >/dev/null 2>&1; need BK /opt/backup/restore.sh "$H2" /tmp/r_h >/dev/null 2>&1
dump_has() { BK sh -c "pg_restore --data-only --table=patients --file=- $1 | grep -c APRES_NIGHTLY" | tr -d '\r\n'; }
eq "export de la NUIT ne contient pas l'ecriture posterieure" "0" "$(dump_has /tmp/r_n/db/ah2.dump)"
eq "export HORAIRE (H2) contient l'ecriture posterieure" "1" "$(dump_has /tmp/r_h/db/ah2.dump)"
BK test -e /tmp/r_n/files/data/product_photos/2026/after_nightly_photo.jpg && fail "snapshot de la NUIT : sans la photo posterieure" "presente" || pass "snapshot de la NUIT : sans la photo posterieure" "absente"
BK test -e /tmp/r_h/files/data/product_photos/2026/after_nightly_photo.jpg && pass "snapshot H2 : avec la photo posterieure" "presente" || fail "snapshot H2 : photo" "absente"
# hourly sans aucun changement : cout reel de l'ajout des fichiers a l'horaire
KB2="$(BK sh -c 'du -sk /backups/repo | cut -f1' | tr -d '\r\n')"; T0="$(date +%s%N)"
need BK /opt/backup/hourly.sh >/dev/null 2>&1; T1="$(date +%s%N)"; KB3="$(BK sh -c 'du -sk /backups/repo | cut -f1' | tr -d '\r\n')"
info "MESURE hourly SANS changement (H3) : duree (docker exec compris)" "$(( (T1-T0)/1000000 )) ms ; depot $KB2 -> $KB3 Ko"
# copie figee pour le PC : manifeste coherent, lisible par restic
PM="$(BK cat /backups/repo/.pull/PULL_MANIFEST.json | tr -d '\r\n')"; PF="$(BK sh -c 'find /backups/repo/.pull -type f | wc -l' | tr -d '\r\n')"
eq "copie pour le PC : le manifeste annonce le nombre de fichiers reel" "$(( PF - 1 ))" "$(BK jq .files /backups/repo/.pull/PULL_MANIFEST.json | tr -d '\r\n')"
BK sh -c "restic -r /backups/repo/.pull --no-lock check --read-data" >/dev/null 2>&1 && pass "copie pour le PC : restic check --read-data complet reussi" "$PM" || fail "restic check de .pull" "echec"
BK /opt/backup/pull_prepare.sh 2>&1 | grep -q "PULL_MANIFEST\|files" && pass "pull_prepare.sh (rafraichissement a la demande)" "ok" || fail "pull_prepare.sh" "echec"
# horodatage : restic ecrit l'heure locale AVEC decalage (+01:00) ; la fonction ts doit la lire correctement
TS1="$(BK bash -c '. /opt/backup/lib.sh; echo "\"2026-10-28T02:30:00.123456789+01:00\"" | jq -r "$JQ_DEFS ts"' | tr -d '\r\n')"
eq "ts : 02:30 a +01:00 = 01:30 UTC" "1793151000" "$TS1"
TS2="$(BK bash -c '. /opt/backup/lib.sh; echo "\"2026-10-28T01:30:00Z\"" | jq -r "$JQ_DEFS ts"' | tr -d '\r\n')"
eq "ts : 01:30 Z = meme instant" "1793151000" "$TS2"

# --- 4. echecs voulus ------------------------------------------------------------------------
section "4. Mauvais mot de passe, export tronque ou vide"
SIG0="$(repo_sig)"; LS0="$(statusval last_success_hourly)"; NS0="$(nsnap hourly)"
bkenv "RESTIC_PASSWORD=mauvais" /opt/backup/hourly.sh > "$WORK/wp.out" 2>&1; RC=$?
ne "mauvais mot de passe : code de sortie non nul" "0" "$RC"
grep -q "BACKUP-ECHEC job=hourly" "$WORK/wp.out" && pass "mauvais mot de passe : message pour l'alerte" "$(grep -m1 BACKUP-ECHEC "$WORK/wp.out" | cut -c1-110)" || fail "message BACKUP-ECHEC" "$(cat "$WORK/wp.out")"
eq "mauvais mot de passe : depot inchange" "$SIG0" "$(repo_sig)"
eq "mauvais mot de passe : last_success_hourly inchange" "$LS0" "$(statusval last_success_hourly)"
bkenv "RESTIC_PASSWORD=mauvais" /opt/backup/nightly.sh >/dev/null 2>&1; ne "mauvais mot de passe (nightly) : echec" "0" "$?"
eq "mauvais mot de passe (nightly) : depot inchange" "$SIG0" "$(repo_sig)"
BK test -s /var/lib/ah2-status/last_error_hourly && pass "last_error_hourly ecrit pour l'alerte" "$(BK cat /var/lib/ah2-status/last_error_hourly | tr -d '\r')" || fail "last_error_hourly" "absent"
# faux pg_dump : tronque (a 100 octets), tronque a moitie, vide
BK sh -c 'cat > /tmp/pgd.sh <<"X"
#!/bin/sh
# usage : MODE=small|half|empty pgd.sh <arguments de pg_dump>
pg_dump "$@" || exit $?
f=""; for a in "$@"; do case "$a" in --file=*) f="${a#--file=}";; esac; done
size=$(wc -c < "$f")
case "$MODE" in
  small) head -c 100 "$f" > "$f.t" ;;
  half)  head -c $((size/2)) "$f" > "$f.t" ;;
  empty) : > "$f.t" ;;
esac
mv "$f.t" "$f"
X
chmod +x /tmp/pgd.sh' >/dev/null
for mode in small empty; do
  bkenv "PG_DUMP_BIN=/tmp/pgd.sh MODE=$mode" /opt/backup/hourly.sh > "$WORK/tr.out" 2>&1; RC=$?
  ne "export '$mode' : echec" "0" "$RC"
  grep -q "trop court" "$WORK/tr.out" && pass "export '$mode' : detecte (trop court)" "$(grep -m1 BACKUP-ECHEC "$WORK/tr.out" | cut -c1-100)" || fail "export '$mode' detecte" "$(tail -3 "$WORK/tr.out")"
done
bkenv "PG_DUMP_BIN=/tmp/pgd.sh MODE=half BACKUP_MIN_DUMP_BYTES=1" /opt/backup/hourly.sh > "$WORK/tr.out" 2>&1; RC=$?
ne "export tronque a moitie : echec" "0" "$RC"
grep -q "illisible ou tronque" "$WORK/tr.out" && pass "export tronque a moitie : detecte par pg_restore" "$(grep -m1 'pg_restore' "$WORK/tr.out" | cut -c1-140)" || fail "tronque detecte par pg_restore" "$(tail -3 "$WORK/tr.out")"
eq "exports invalides : last_success_hourly inchange" "$LS0" "$(statusval last_success_hourly)"
eq "exports invalides : aucun snapshot ajoute" "$NS0" "$(nsnap hourly)"
eq "exports invalides : depot inchange" "$SIG0" "$(repo_sig)"
need BK /opt/backup/hourly.sh >/dev/null 2>&1; ne "hourly.sh reussi apres echecs : marqueur renouvele" "$LS0" "$(statusval last_success_hourly)"
BK test -e /var/lib/ah2-status/last_error_hourly && fail "last_error_hourly efface a la reussite" "present" || pass "last_error_hourly efface a la reussite" "absent"

# --- 5. retention ---------------------------------------------------------------------------
section "5. Retention (KEEP_HOURLY=3, 6 exports)"
bkenv "RESTIC_REPOSITORY=/backups/repo-ret" restic init >/dev/null 2>&1
for i in 1 2 3 4 5 6; do bkenv "RESTIC_REPOSITORY=/backups/repo-ret STATUS_DIR=/tmp/st-ret KEEP_HOURLY=3" /opt/backup/hourly.sh >/dev/null 2>&1 || fail "retention : run $i" "echec"; done
eq "6 exports, KEEP_HOURLY=3 : 3 snapshots restent" "3" "$(bkenv "RESTIC_REPOSITORY=/backups/repo-ret" sh -c 'restic snapshots --tag hourly --json | jq length' | tr -d '\r\n')"
bkenv "KEEP_HOURLY=abc" /opt/backup/hourly.sh >/dev/null 2>&1; ne "KEEP_HOURLY invalide refuse (aucune suppression)" "0" "$?"

# --- 6. envoi hebdomadaire par SFTP (vrai protocole, serveur jetable) ------------------------
section "6. offsite.sh (SFTP, cle, empreinte epinglee)"
C exec -T backup sh -c 'cat > /tmp/kh_bad' < "$WORK/known_hosts_BAD"
OS0="$(statusval last_success_offsite)"
bkenv "BACKUP_SFTP_KNOWN_HOSTS=/tmp/kh_bad" /opt/backup/offsite.sh > "$WORK/kh.out" 2>&1; ne "empreinte du serveur differente : refus" "0" "$?"
eq "empreinte differente : last_success_offsite non cree" "none" "$(statusval last_success_offsite)"
if C exec -T backup /opt/backup/offsite.sh > "$WORK/off1.out" 2>&1; then pass "offsite.sh (1er envoi, depot distant cree)" "$(grep -m1 'depot distant : snapshots' "$WORK/off1.out")"; else fail "offsite.sh" "$(tail -8 "$WORK/off1.out")"; fi
ne "last_success_offsite ecrit" "none" "$(statusval last_success_offsite)"
STATS1="$(BK cat /var/lib/ah2-status/offsite_stats.json | tr -d '\r\n')"; info "offsite_stats.json" "$STATS1"
jqs() { BK jq "$1" /var/lib/ah2-status/offsite_stats.json | tr -d '\r\n'; }
eq "depot distant : snapshots (1 nuit + 1 horaire)" "2" "$(jqs .snapshots)"
RF1="$(docker exec "$SSHD" sh -c 'find /home/hostinger/backups/ah2 -type f | wc -l' | tr -d '\r\n')"
eq "fichiers comptes par le serveur = mesure du script" "$RF1" "$(jqs .files)"
OS1="$(statusval last_success_offsite)"
bkenv "RESTIC_OFFSITE_PASSWORD=mauvais" /opt/backup/offsite.sh > "$WORK/offpw.out" 2>&1; ne "mot de passe du depot distant incorrect : echec" "0" "$?"
eq "mot de passe distant incorrect : last_success_offsite inchange" "$OS1" "$(statusval last_success_offsite)"
eq "mot de passe distant incorrect : depot distant inchange" "$RF1" "$(docker exec "$SSHD" sh -c 'find /home/hostinger/backups/ah2 -type f | wc -l' | tr -d '\r\n')"
C exec -T backup /opt/backup/offsite.sh > "$WORK/off2.out" 2>&1 && pass "offsite.sh idempotent (2e envoi)" "snapshots distants: $(jqs .snapshots)" || fail "offsite 2e envoi" "$(tail -5 "$WORK/off2.out")"
eq "2e envoi sans changement local : memes snapshots distants" "2" "$(jqs .snapshots)"
RF2="$(docker exec "$SSHD" sh -c 'find /home/hostinger/backups/ah2 -type f | wc -l' | tr -d '\r\n')"
info "fichiers distants apres 1er/2e envoi (sans changement local)" "$RF1 -> $RF2"
PEAK="$(BK sh -c 'cat /sys/fs/cgroup/memory.peak 2>/dev/null || echo 0' | tr -d '\r\n')"
info "pic memoire du conteneur backup depuis son demarrage (limite 256 Mo)" "$((PEAK/1048576)) Mo"

# --- 6b. erreurs de transport : jamais de creation de depot ; verrou partage ; coupure SFTP ---
RFX="$(docker exec "$SSHD" sh -c 'find /home/hostinger/backups -type f | wc -l' | tr -d '\r\n')"
bkenv "BACKUP_SFTP_HOST=nohost.invalid BACKUP_RETRY_TRIES=2 BACKUP_RETRY_DELAY=1" /opt/backup/offsite.sh > "$WORK/nh.out" 2>&1; ne "hote injoignable : echec" "0" "$?"
grep -q "nouvel essai" "$WORK/nh.out" && pass "hote injoignable : reessaye" "$(grep -m1 'nouvel essai' "$WORK/nh.out" | cut -c1-110)" || fail "hote injoignable : reessaye" "$(tail -3 "$WORK/nh.out")"
grep -q "initialisation" "$WORK/nh.out" && fail "hote injoignable : AUCUNE initialisation de depot" "init tentee" || pass "hote injoignable : aucune initialisation de depot" "ok"
C exec -T backup sh -c 'ssh-keygen -q -t ed25519 -N "" -f /tmp/k_bad'
bkenv "BACKUP_SFTP_KEY=/tmp/k_bad BACKUP_RETRY_TRIES=1" /opt/backup/offsite.sh > "$WORK/wk.out" 2>&1; ne "mauvaise cle SSH : echec" "0" "$?"
grep -q "initialisation" "$WORK/wk.out" && fail "mauvaise cle : AUCUNE initialisation de depot" "init tentee" || pass "mauvaise cle : aucune initialisation de depot" "$(grep -m1 BACKUP-ECHEC "$WORK/wk.out" | cut -c1-130)"
eq "hote injoignable / mauvaise cle : rien cree chez Hostinger" "$RFX" "$(docker exec "$SSHD" sh -c 'find /home/hostinger/backups -type f | wc -l' | tr -d '\r\n')"
bkenv "STATUS_DIR=/tmp/st-vide BACKUP_SFTP_PATH=backups/vide" /opt/backup/offsite.sh > "$WORK/vide.out" 2>&1 && docker exec "$SSHD" test -f /home/hostinger/backups/vide/config && pass "chemin distant vraiment vide : depot cree (init)" "$(grep -m1 'initialisation' "$WORK/vide.out" | cut -c1-100)" || fail "chemin vide : init" "$(tail -4 "$WORK/vide.out")"
# verrou partage : un hourly (simule) tient le verrou 25 s, offsite ATTEND puis reussit
C exec -T backup sh -c 'flock /var/tmp/ah2-backup-repo.lock sleep 25' & HOLD=$!
sleep 4; L0="$(date +%s)"; C exec -T backup /opt/backup/offsite.sh > "$WORK/lk.out" 2>&1; RC=$?; L1="$(date +%s)"; wait $HOLD
eq "offsite lance pendant qu'un hourly tient le verrou : reussit" "0" "$RC"
ge() { if [ "$3" -ge "$2" ] 2>/dev/null; then pass "$1" "$3"; else fail "$1" "attendu >= $2, obtenu $3"; fi; }
ge "offsite a ATTENDU la fin du verrou (>= 18 s)" 18 "$((L1-L0))"
# coupure SFTP passagere : le serveur est eteint 8 s, offsite reessaie puis reussit
docker stop "$SSHD" >/dev/null
( bkenv "BACKUP_RETRY_TRIES=5 BACKUP_RETRY_DELAY=6" /opt/backup/offsite.sh > "$WORK/rt.out" 2>&1; echo $? > "$WORK/rt.rc" ) & RP=$!
sleep 8; docker start "$SSHD" >/dev/null; wait $RP
eq "coupure SFTP passagere : offsite reessaie puis reussit" "0" "$(cat "$WORK/rt.rc")"
grep -q "nouvel essai" "$WORK/rt.out" && pass "coupure SFTP : les essais sont journalises" "$(grep -m1 'nouvel essai' "$WORK/rt.out" | cut -c1-110)" || fail "coupure SFTP : essais" "$(tail -4 "$WORK/rt.out")"
# hourly et nightly lances en meme temps : le verrou les serialise, les deux reussissent, depot sain
( BK /opt/backup/hourly.sh >/dev/null 2>&1; echo $? > "$WORK/c1" ) & P1=$!
( BK /opt/backup/nightly.sh >/dev/null 2>&1; echo $? > "$WORK/c2" ) & P2=$!
wait $P1 $P2
eq "hourly + nightly simultanes : les deux reussissent" "0/0" "$(cat "$WORK/c1")/$(cat "$WORK/c2")"
BK restic check >/dev/null 2>&1 && pass "hourly + nightly simultanes : restic check du depot" "ok" || fail "restic check apres execution simultanee" "echec"
need BK /opt/backup/offsite.sh >/dev/null 2>&1   # remet les statistiques distantes de la configuration normale

# --- 7. verify.sh ----------------------------------------------------------------------------
section "7. verify.sh"
bkenv "BACKUP_CHECK_SUBSET=100%" /opt/backup/verify.sh > "$WORK/verify.out" 2>&1 && pass "verify.sh (restic check complet + relecture de l'export)" "$(grep -m1 'tables avec donnees' "$WORK/verify.out" | cut -c20-90)" || fail "verify.sh" "$(tail -5 "$WORK/verify.out")"
AGE="$(sed -n 's/.*age \(-\{0,1\}[0-9][0-9]*\) s.*/\1/p' "$WORK/verify.out" | head -1)"
if [ -n "$AGE" ] && [ "$AGE" -ge 0 ] && [ "$AGE" -le 3000 ]; then pass "verify : age du dernier export correct malgre le decalage horaire (+01:00)" "${AGE} s"; else fail "verify : age de l'export" "age=$AGE (negatif = decalage horaire mal lu)"; fi

# --- 8. entrypoint : refus propres -----------------------------------------------------------
section "8. Refus de l'entrypoint"
docker volume create "${PROJECT}_rootvol" >/dev/null
docker run --rm --user 0 --entrypoint sh -v "${PROJECT}_rootvol:/r" "$IMG" -c 'touch /r/.keep; chown 0:0 /r; chmod 755 /r'
docker run --rm -e RESTIC_PASSWORD=x -v "${PROJECT}_rootvol:/backups/repo" "$IMG" > "$WORK/ro.out" 2>&1; RC=$?
ne "depot non ecrivable : demarrage refuse" "0" "$RC"
grep -q "install -d -o 10001" "$WORK/ro.out" && pass "message avec la commande de correction" "$(grep -m1 install "$WORK/ro.out" | cut -c1-120)" || fail "message de correction" "$(cat "$WORK/ro.out")"
docker volume create "${PROJECT}_cronvol" >/dev/null
docker run --rm --user 0 --entrypoint sh -v "${PROJECT}_cronvol:/r" "$IMG" -c 'chown 10001:10001 /r'
docker run --rm -e RESTIC_PASSWORD=x -e BACKUP_HOURLY_CRON='toutes les heures' -v "${PROJECT}_cronvol:/backups/repo" "$IMG" > "$WORK/cr.out" 2>&1; RC=$?
ne "horaire invalide : demarrage refuse" "0" "$RC"
grep -q "BACKUP_HOURLY_CRON invalide" "$WORK/cr.out" && pass "message horaire invalide" "$(grep -m1 invalide "$WORK/cr.out" | cut -c1-100)" || fail "message horaire" "$(tail -3 "$WORK/cr.out")"
docker run --rm -e RESTIC_PASSWORD=x -v "${PROJECT}_cronvol:/run/secrets/backup_sftp_key:ro" "$IMG" > "$WORK/sd.out" 2>&1; RC=$?
eq "secret monte comme DOSSIER (fichier absent sur l'hote) : demarrage refuse (78)" "78" "$RC"
grep -q "est un DOSSIER" "$WORK/sd.out" && pass "message clair pour un secret qui est un dossier" "$(grep -m1 DOSSIER "$WORK/sd.out" | cut -c1-120)" || fail "message secret-dossier" "$(cat "$WORK/sd.out")"
docker run --rm -e RESTIC_PASSWORD=x -e BACKUP_SFTP_HOST=h.example "$IMG" > "$WORK/sm.out" 2>&1; RC=$?
eq "envoi configure mais cle absente : demarrage refuse (78)" "78" "$RC"
grep -q "absent ou vide" "$WORK/sm.out" && pass "message clair pour une cle absente" "$(grep -m1 'absent ou vide' "$WORK/sm.out" | cut -c1-120)" || fail "message cle absente" "$(cat "$WORK/sm.out")"
# mot de passe par fichier (RESTIC_PASSWORD_FILE), sans RESTIC_PASSWORD
BK sh -c 'printf %s "$RESTIC_PASSWORD" > /tmp/pwf; printf %s mauvais > /tmp/pwf_bad'
bkenv "RESTIC_PASSWORD= RESTIC_PASSWORD_FILE=/tmp/pwf" /opt/backup/hourly.sh >/dev/null 2>&1; eq "mot de passe lu dans RESTIC_PASSWORD_FILE : hourly reussit" "0" "$?"
bkenv "RESTIC_PASSWORD= RESTIC_PASSWORD_FILE=/tmp/pwf_bad" /opt/backup/hourly.sh >/dev/null 2>&1; ne "mauvais mot de passe dans le fichier : refuse" "0" "$?"

# --- 9. PERTE DE LA BASE ET DES VOLUMES : restauration depuis le depot local -----------------
section "9. Destruction de la base et des 3 volumes, restauration (depot local)"
C rm -sf backup db >/dev/null 2>&1
for v in pgdata uploads product_photos consents; do docker volume rm -f "${PROJECT}_$v" >/dev/null 2>&1; done
docker volume ls --format '{{.Name}}' | grep -E "^${PROJECT}_(pgdata|uploads|product_photos|consents)$" && fail "volumes detruits" "encore presents" || pass "volumes pgdata, uploads, product_photos, consents detruits" "bk_repo conserve"
need C up -d db >/dev/null 2>&1; need C create backup >/dev/null 2>&1
wait_healthy db 90 && pass "base NEUVE et vide demarree (roles via 01-roles.sh)" "$(psqld -c "select count(*) from information_schema.tables where table_schema='public'" | tr -d '\r') tables" || fail "db neuve" "timeout"
RESTORE_RUN() { # RESTORE_RUN "options" id
  # shellcheck disable=SC2046
  docker run --rm --user 0 --network "$NET" \
    -e RESTIC_PASSWORD="$RESTIC_PASSWORD" -e PGHOST=db -e PGUSER="$POSTGRES_USER" -e PGPASSWORD="$POSTGRES_PASSWORD" -e PGDATABASE="$POSTGRES_DB" \
    -v "${PROJECT}_bk_repo:/backups/repo" -v "${PROJECT}_safety:/tmp/restore" \
    -v "${PROJECT}_uploads:/apply/data/uploads" -v "${PROJECT}_product_photos:/apply/data/product_photos" -v "${PROJECT}_consents:/apply/data/consents" \
    "$IMG" /opt/backup/restore.sh $1 "$2" /tmp/restore
}
if RESTORE_RUN "--apply-to-stack" latest > "$WORK/apply.out" 2>&1; then pass "restore.sh --apply-to-stack latest" "$(grep -m1 'alembic_version' "$WORK/apply.out" | sed 's/^[0-9: -]*//')"; else fail "restore --apply-to-stack" "$(tail -10 "$WORK/apply.out")"; fi
C3="$(counts)"
eqs "memes nombres de lignes dans TOUTES les tables" "$C2" "$C3"
eq "alembic_version identique" "$ALEMBIC0" "$(psqld -c 'select version_num from public.alembic_version' | tr -d '\r')"
eq "ligne posterieure a la nightly retrouvee (export horaire)" "1" "$(psqld -c "select count(*) from patients where first_name='APRES_NIGHTLY'" | tr -d '\r')"
M3="$(vr "$MANIFEST" | tr -d '\r')"; eqs "memes empreintes SHA-256 des fichiers restaures (dont le fichier de 1 Mo)" "$M2" "$M3"
OWN="$(vr 'find /data/uploads /data/product_photos /data/consents -exec stat -c %u:%g {} + | sort -u' | tr -d '\r' | tr '\n' ' ')"; eq "proprietaire des fichiers et dossiers restaures" "10001:10001 " "$OWN"
eq "sequences restaurees (prochaine insertion sans collision)" "1" "$(psqld -c "insert into patients(first_name,last_name,birth_date,created_by_name) values ('Nouveau','Apres',date '2000-01-01','t') returning 1" | head -1 | tr -d '\r')"
info "role powersync_repl et publication" "$(psqld -c "select count(*) from pg_publication" | tr -d '\r') publication(s), $(psqld -c "select count(*) from pg_roles where rolname in ('powersync_repl','app_medical')" | tr -d '\r') role(s)"
# l'application ne tourne pas ici : on verifie que le service backup repart et se declare sain
need C up -d backup >/dev/null 2>&1; wait_healthy backup 180 && pass "service backup relance sur la base restauree : healthy" "export horaire OK" || fail "backup apres restauration" "$(C logs --tail 10 backup 2>&1 | tr '\n' '|')"
info "exports horaires dans le depot local apres restauration" "$(nsnap hourly)"

C3B="$(counts)"
# restauration sur une base NON vide (meme serveur) : export de securite de l'etat actuel d'abord
psqld -c "INSERT INTO patients(first_name,last_name,birth_date,created_by_name) VALUES ('POST_RESTORE_MARKER','X',date '2001-01-01','t')" >/dev/null
if RESTORE_RUN "--apply-to-stack --force" latest > "$WORK/apply3.out" 2>&1; then pass "restore.sh --apply-to-stack sur une base NON vide" "$(grep -m1 'export de securite' "$WORK/apply3.out" | sed 's/^[0-9: -]*//' | cut -c1-110)"; else fail "restore sur base non vide" "$(tail -8 "$WORK/apply3.out")"; fi
grep -q "base vide : pas d'export de securite" "$WORK/apply.out" && pass "1re restauration (base vide) : pas d'export de securite" "ok" || fail "base vide : message" "$(grep -m2 securite "$WORK/apply.out")"
SAFE_N="$(docker run --rm --user 0 --entrypoint sh -v "${PROJECT}_safety:/s" "$IMG" -c 'ls /s/safety/*.dump | wc -l' | tr -d '\r\n')"
eq "un export de securite a ete ecrit" "1" "$SAFE_N"
eq "l'export de securite contient l'etat AVANT (ligne POST_RESTORE_MARKER)" "1" "$(docker run --rm --user 0 --entrypoint sh -v "${PROJECT}_safety:/s" "$IMG" -c 'pg_restore --data-only --table=patients --file=- /s/safety/*.dump | grep -c POST_RESTORE_MARKER' | tr -d '\r\n')"
eq "apres la 2e restauration la ligne posterieure a la sauvegarde a disparu" "0" "$(psqld -c "select count(*) from patients where first_name='POST_RESTORE_MARKER'" | tr -d '\r')"
eqs "2e restauration : memes nombres de lignes qu'a la sauvegarde" "$C2" "$(counts)"

# --- 10. PERTE TOTALE (serveur + depot local) : restauration depuis Hostinger (SFTP) ---------
section "10. Perte totale : restauration depuis le depot distant (SFTP)"
need BK /opt/backup/hourly.sh >/dev/null 2>&1; need BK /opt/backup/offsite.sh >/dev/null 2>&1   # etat distant = etat actuel
C2B="$(counts)"; M2B="$(vr "$MANIFEST" | tr -d '\r')"
C rm -sf backup db >/dev/null 2>&1
for v in pgdata uploads product_photos consents bk_repo backup_status; do docker volume rm -f "${PROJECT}_$v" >/dev/null 2>&1; done
need C up -d db >/dev/null 2>&1; need C create backup >/dev/null 2>&1
wait_healthy db 90 || fail "db neuve (2)" "timeout"
RESTORE_RUN_OFF() {
  docker run --rm --user 0 --network "$NET" \
    -e RESTIC_PASSWORD="$RESTIC_PASSWORD" -e PGHOST=db -e PGUSER="$POSTGRES_USER" -e PGPASSWORD="$POSTGRES_PASSWORD" -e PGDATABASE="$POSTGRES_DB" \
    -e BACKUP_SFTP_HOST=sshd -e BACKUP_SFTP_USER=hostinger -e BACKUP_SFTP_PATH=backups/ah2 -e BACKUP_SFTP_PORT=2222 \
    -v "$(cd "$WORK" && pwd -W 2>/dev/null || pwd)/sftp_key:/run/secrets/backup_sftp_key:ro" \
    -v "$(cd "$WORK" && pwd -W 2>/dev/null || pwd)/known_hosts:/run/secrets/backup_known_hosts:ro" \
    -v "${PROJECT}_uploads:/apply/data/uploads" -v "${PROJECT}_product_photos:/apply/data/product_photos" -v "${PROJECT}_consents:/apply/data/consents" \
    "$IMG" /opt/backup/restore.sh --from-offsite --apply-to-stack latest /tmp/restore
}
if RESTORE_RUN_OFF > "$WORK/apply2.out" 2>&1; then pass "restore.sh --from-offsite --apply-to-stack latest (depot local ET volumes detruits)" "ok"; else fail "restore depuis Hostinger" "$(tail -10 "$WORK/apply2.out")"; fi
eqs "depuis Hostinger : memes nombres de lignes dans toutes les tables" "$C2B" "$(counts)"
eqs "depuis Hostinger : memes empreintes de fichiers" "$M2B" "$(vr "$MANIFEST" | tr -d '\r')"
eq "depuis Hostinger : proprietaire 10001" "10001:10001 " "$(vr 'find /data/uploads /data/product_photos /data/consents -exec stat -c %u:%g {} + | sort -u' | tr -d '\r' | tr '\n' ' ')"

# --- 11. volumetrie : 1 nightly + 24 hourly, puis simulation de N semaines -------------------
section "11. Volumetrie du depot (fichiers, taille)"
need C up -d backup >/dev/null 2>&1; wait_healthy backup 180 || fail "backup (volumetrie)" "pas sain"
Y="$(date -d yesterday +%F 2>/dev/null || date -v-1d +%F)"
E24="RESTIC_REPOSITORY=/backups/repo-24h STATUS_DIR=/tmp/st-24h OFFSITE_REPOSITORY=/backups/offsite-24h"
bkenv "RESTIC_REPOSITORY=/backups/repo-24h" restic init >/dev/null 2>&1
bkenv "$E24 BACKUP_FAKE_TIME=${Y}_02:30:00" /opt/backup/nightly.sh >/dev/null 2>&1 || fail "24h : nightly" "echec"
for h in $(seq 0 23); do
  psqld -c "insert into patients(first_name,last_name,birth_date,created_by_name) select 'H$h-'||g,'N',date '1985-05-05','sim' from generate_series(1,10) g" >/dev/null
  bkenv "$E24 BACKUP_FAKE_TIME=${Y}_$(printf %02d "$h"):07:00" /opt/backup/hourly.sh >/dev/null 2>&1 || fail "24 hourly : heure $h" "echec"
done
size_of() { BK sh -c "echo \$(find $1 -type f | wc -l) fichiers, \$(find $1 -type d | wc -l) dossiers, \$(du -sk $1 | cut -f1) Ko" | tr -d '\r'; }
info "depot local apres 1 nightly + 24 hourly" "$(size_of /backups/repo-24h) ; snapshots=$(bkenv "RESTIC_REPOSITORY=/backups/repo-24h" sh -c 'restic snapshots --json | jq length' | tr -d '\r\n')"
bkenv "$E24" /opt/backup/offsite.sh >/dev/null 2>&1
info "depot 'Hostinger' (simule, meme structure) apres le 1er envoi de ce depot" "$(size_of /backups/offsite-24h)"

cat > "$WORK/sim.sh" <<'SIMEOF'
set -e
export STATUS_DIR=/tmp/st-sim RESTIC_REPOSITORY=/backups/repo-sim OFFSITE_REPOSITORY=/backups/offsite-sim
restic init >/dev/null
now=$(date +%s); days=$((WEEKS*7))
for d in $(seq 0 $((days-1))); do
  ts=$((now - (days-d)*86400)); day=$(date -d @$ts "+%Y-%m-%d")
  psql -X -q -c "insert into patients(first_name,last_name,birth_date,created_by_name) select 'Sim${d}-'||g,'N',date '1980-01-01','sim' from generate_series(1,40) g"
  for k in 1 2 3; do head -c 150000 /dev/urandom > /data/product_photos/sim_${d}_$k.jpg; done
  head -c 60000 /dev/urandom > /data/consents/sim_$d.pdf
  if [ $((d%7)) = 6 ]; then export PRUNE=1; else export PRUNE=0; fi
  BACKUP_FAKE_TIME="$day 02:30:00" /opt/backup/nightly.sh >/dev/null 2>&1
  BACKUP_FAKE_TIME="$day 23:07:00" /opt/backup/hourly.sh >/dev/null 2>&1
  if [ $((d%7)) = 6 ]; then
    BACKUP_FAKE_NOW=$((ts+82000)) /opt/backup/offsite.sh >/dev/null 2>&1
    echo "SEMAINE $(( (d+1)/7 )) local_fichiers=$(find /backups/repo-sim -type f | wc -l) local_ko=$(du -sk /backups/repo-sim | cut -f1) distant_fichiers=$(find /backups/offsite-sim -type f | wc -l) distant_dossiers=$(find /backups/offsite-sim -type d | wc -l) distant_ko=$(du -sk /backups/offsite-sim | cut -f1) distant_snapshots=$(jq .snapshots /tmp/st-sim/offsite_stats.json)"
  fi
done
RESTIC_REPOSITORY=/backups/repo-sim restic check --read-data >/dev/null 2>&1 && echo "CHECK_OK local-sim"
RESTIC_REPOSITORY=/backups/offsite-sim restic check --read-data >/dev/null 2>&1 && echo "CHECK_OK distant-sim"
SIMEOF
cat > "$WORK/extrap.py" <<'PYEOF'
import re, sys
rows = [dict(re.findall(r"(\w+)=(\d+)", l)) for l in open(sys.argv[1]) if l.startswith("SEMAINE")]
rows = [{k: int(v) for k, v in r.items()} for r in rows]
if len(rows) >= 4:
    n = len(rows); last = rows[-1]; mid = rows[n // 2]
    slope = (last["distant_fichiers"] - mid["distant_fichiers"]) / max(1, (n - 1 - n // 2))
    worst = max(b["distant_fichiers"] - a["distant_fichiers"] for a, b in zip(rows, rows[1:]))
    print("EXTRAPOLATION  fichiers distants: semaine %d = %d ; pente 2e moitie = %.2f fichiers/semaine ; projection a 52 semaines = %d" % (n, last["distant_fichiers"], slope, round(last["distant_fichiers"] + max(slope, 0) * (52 - n))))
    print("EXTRAPOLATION  pire cas (pente max entre deux semaines = %d/semaine) a 52 semaines : %d fichiers ; budget libre Hostinger = 540000" % (worst, last["distant_fichiers"] + worst * (52 - n)))
    print("EXTRAPOLATION  taille distante: %d Ko a la semaine %d" % (last["distant_ko"], n))
PYEOF
SIMLOG="$WORK/sim.log"
# shellcheck disable=SC2046
docker run -i --rm --user 10001 --network "$NET" --entrypoint bash $(VOLS) -v "${PROJECT}_bk_repo:/backups/repo" \
  -e WEEKS="$WEEKS" -e RESTIC_PASSWORD="$RESTIC_PASSWORD" -e PGHOST=db -e PGUSER="$POSTGRES_USER" -e PGPASSWORD="$POSTGRES_PASSWORD" -e PGDATABASE="$POSTGRES_DB" \
  -e KEEP_HOURLY=48 -e KEEP_DAILY=14 -e KEEP_WEEKLY=8 -e KEEP_MONTHLY=6 \
  "$IMG" -s < "$WORK/sim.sh" > "$SIMLOG" 2>&1 && pass "simulation de $WEEKS semaines (1 nightly + 1 hourly par jour, 1 envoi par semaine)" "voir ci-dessous" || { fail "simulation" "$(tail -5 "$SIMLOG")"; }
cat "$SIMLOG"
python "$WORK/extrap.py" "$SIMLOG" || python3 "$WORK/extrap.py" "$SIMLOG"
grep -q "^CHECK_OK local-sim" "$SIMLOG" && grep -q "^CHECK_OK distant-sim" "$SIMLOG" && pass "restic check --read-data complet des deux depots simules (local et distant)" "ok" || fail "restic check apres simulation" "$(grep -i fatal "$SIMLOG" | head -3)"

echo
echo "=============================================="
echo "RESULTAT : PASS=$NPASS FAIL=$NFAIL"
[ "$NFAIL" -eq 0 ] || { printf 'ECHECS :\n'; printf '  - %s\n' "${FAILED[@]}"; exit 1; }
exit 0
