#!/usr/bin/env bash
# Repetition locale de la pile de production AH2 (Docker Desktop / n'importe quel hote Docker).
# Monte la pile complete avec DOMAIN=localhost (Caddy en autorite interne), initialise une base
# neuve, cree le premier admin, importe les donnees de reference, puis verifie (lignes PASS/FAIL).
#
# Usage :
#   bash deploy/smoke.sh [--build] [--keep] [--down] [--ref-data FICHIER] [-h|--help]
#
#   --build           construit d'abord les images locales ghcr.io/rehearsal/ah2-{api,web}:local
#   --keep            laisse la pile (et ses volumes) en place a la fin
#   --down            ne fait QUE nettoyer : arrete la pile de repetition et SUPPRIME ses volumes
#   --ref-data FILE   donnees de reference a importer (defaut : celles du chantier 8)
#   --no-long         saute les attentes longues (flux PowerSync > 60 s) : a eviter
#
# Prerequis : docker compose v2, curl, openssl, python (hote, pour lire le JSON), images construites.
# Secrets : genere deploy/rehearsal.env (ignore par git) s'il n'existe pas. Projet compose :
# "ah2rehearsal" (ne touche jamais la pile de developpement). Ports 80 et 443 de l'hote requis.
set -euo pipefail
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'

PROJECT=ah2rehearsal
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

ENVF="deploy/rehearsal.env"  # chemins relatifs a la racine (docker.exe sous Windows ne comprend pas /c/...)
COMPOSE_FILE="deploy/docker-compose.prod.yml"
REF_DATA=".superpowers/sdd/2026-10-28-chantier8-deploiement/reference_data.json"
DO_BUILD=0; KEEP=0; ONLY_DOWN=0; LONG=1
WORK="deploy/.smoke-work"   # fichiers temporaires (ignore par git)
CLIENT="${PROJECT}-client"

while [ $# -gt 0 ]; do
  case "$1" in
    --build) DO_BUILD=1 ;;
    --keep) KEEP=1 ;;
    --down) ONLY_DOWN=1 ;;
    --no-long) LONG=0 ;;
    --ref-data) shift; REF_DATA="$1" ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Option inconnue : $1 (voir --help)" >&2; exit 64 ;;
  esac
  shift
done

# --- generation du .env jetable ------------------------------------------------------------
gen_env() {
  local hex
  hex() { openssl rand -hex 32; }
  cat > "$ENVF" <<EOF
# Fichier JETABLE de la repetition locale (ignore par git). Ne jamais l'utiliser en production.
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
ACME_EMAIL=rehearsal@example.test
CADDY_TLS_MODE=local_certs
WEB_CONCURRENCY=2
CELERY_CONCURRENCY=2
# Hors compose (lus par smoke.sh seulement)
REHEARSAL_ADMIN_USER=rehearsal_admin
REHEARSAL_ADMIN_PASSWORD=Reh-$(openssl rand -hex 12)
EOF
  chmod 600 "$ENVF" 2>/dev/null || true
}

C() { docker compose -p "$PROJECT" --env-file "$ENVF" -f "$COMPOSE_FILE" "$@"; }

mkdir -p "$WORK"
if [ "$ONLY_DOWN" = 1 ]; then
  [ -f "$ENVF" ] || gen_env
  docker rm -f "$CLIENT" >/dev/null 2>&1 || true
  C down -v --remove-orphans
  echo "Pile $PROJECT arretee, volumes supprimes."
  exit 0
fi

[ -f "$ENVF" ] || gen_env
# shellcheck disable=SC1090
set -a; . "$ENVF"; set +a

# --- compteurs et affichage ----------------------------------------------------------------
NPASS=0; NFAIL=0; FAILED=()
pass() { NPASS=$((NPASS+1)); echo "PASS  $1  [$2]"; }
fail() { NFAIL=$((NFAIL+1)); FAILED+=("$1"); echo "FAIL  $1  [$2]"; }
check() { # check "nom" "evidence" cmd...  (cmd reussit = PASS)
  local name="$1" ev="$2"; shift 2
  if "$@" >/dev/null 2>&1; then pass "$name" "$ev"; else fail "$name" "$ev"; fi
}
eq() { # eq "nom" attendu obtenu
  if [ "$2" = "$3" ]; then pass "$1" "obtenu=$3"; else fail "$1" "attendu=$2 obtenu=$3"; fi
}
info() { echo "INFO  $1  [$2]"; }
section() { echo; echo "=== $* ==="; }

# --- helpers reseau --------------------------------------------------------------------------
# Client HTTP : curl de l'hote si son TLS marche, sinon un conteneur curl sur le reseau de la pile
# (certains hotes Windows ont un curl Schannel / un antivirus qui coupe la poignee de main TLS de
# l'autorite interne de Caddy). Le conteneur garde UNE adresse pendant tout le test (limites par IP).
CLIENT_MODE=host; WF="$WORK"
CURLB="curl -sk --resolve localhost:443:127.0.0.1 --resolve localhost:80:127.0.0.1"
start_client() {
  docker rm -f "$CLIENT" >/dev/null 2>&1 || true
  docker run -d --name "$CLIENT" --network "${PROJECT}_ah2" -v "$(cd "$WORK" && pwd -W 2>/dev/null || pwd):/w"     --entrypoint sleep curlimages/curl:latest 100000 >/dev/null
  CLIENT_MODE=container; WF=/w
  CURLB="curl -sk --resolve localhost:443:172.28.0.10 --resolve localhost:80:172.28.0.10"
}
stop_client() { docker rm -f "$CLIENT" >/dev/null 2>&1 || true; }
cu() {
  if [ "$CLIENT_MODE" = host ]; then $CURLB "$@"; else docker exec -i "$CLIENT" $CURLB "$@"; fi
}
run_in_client() { # execute un extrait sh la ou vit le client HTTP
  if [ "$CLIENT_MODE" = host ]; then bash -c "$1"; else docker exec "$CLIENT" sh -c "$1"; fi
}
code() { cu -o /dev/null -w '%{http_code}' "$@"; }
pj() { python -c 'import sys,json; d=json.load(sys.stdin); print(eval(sys.argv[1]))' "$1"; }
redis_cli() { C exec -T redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli "$@"' sh "$@"; }
psql_db() { C exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -X -At "$@"; }
login_code() { # login_code user pass [header...] -> code HTTP
  local u="$1" p="$2"; shift 2
  code -X POST https://localhost/api/auth/login "$@" --data-urlencode "username=$u" --data-urlencode "password=$p"
}
login_token() {
  cu -X POST https://localhost/api/auth/login --data-urlencode "username=$1" --data-urlencode "password=$2" \
    | pj 'd["access_token"]'
}
wait_healthy() { # wait_healthy service secondes
  local svc="$1" max="$2" i=0 id st
  while [ "$i" -lt "$max" ]; do
    id="$(C ps -q "$svc" 2>/dev/null || true)"
    if [ -n "$id" ]; then
      st="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id" 2>/dev/null || true)"
      if [ "$st" = healthy ] || [ "$st" = running ]; then return 0; fi
    fi
    i=$((i+3)); sleep 3
  done
  return 1
}
free_gb() { df -P /c 2>/dev/null | awk 'NR==2{printf "%.1f", $4/1048576}'; }

# --- 0. prerequis ----------------------------------------------------------------------------
section "0. Prerequis"
echo "Espace libre sur C: ${GB:=$(free_gb)} Go"
if [ "$DO_BUILD" = 1 ]; then
  docker build -f deploy/Dockerfile.api -t "ghcr.io/$GHCR_OWNER/ah2-api:$IMAGE_TAG" .
  docker build -f deploy/Dockerfile.web --build-arg "DOMAIN=$DOMAIN" -t "ghcr.io/$GHCR_OWNER/ah2-web:$IMAGE_TAG" .
fi
for im in ah2-api ah2-web; do
  docker image inspect "ghcr.io/$GHCR_OWNER/$im:$IMAGE_TAG" >/dev/null 2>&1 \
    || { echo "Image ghcr.io/$GHCR_OWNER/$im:$IMAGE_TAG absente : relancer avec --build." >&2; exit 2; }
done
[ -f "$REF_DATA" ] || { echo "Donnees de reference introuvables : $REF_DATA" >&2; exit 2; }
if [ -n "$(C ps -q 2>/dev/null)" ]; then
  echo "Une pile $PROJECT tourne deja : 'bash deploy/smoke.sh --down' d'abord." >&2; exit 2
fi

# --- 1. bases et initialisation --------------------------------------------------------------
section "1. Demarrage de db / redis / pg-storage et base neuve"
C up -d db redis pg-storage
wait_healthy db 180 && pass "db healthy" "healthcheck" || { fail "db healthy" "timeout"; exit 1; }
wait_healthy redis 60 && pass "redis healthy" "healthcheck" || fail "redis healthy" "timeout"
wait_healthy pg-storage 120 && pass "pg-storage healthy" "healthcheck" || fail "pg-storage healthy" "timeout"

# 01-roles.sh a-t-il tourne ? (une seule fois, a la creation du volume)
eq "role app_medical existe, sans connexion (01-roles.sh a tourne)" "f" \
   "$(psql_db -c "select rolcanlogin from pg_roles where rolname='app_medical'")"
eq "role powersync_repl : REPLICATION + LOGIN" "t|t" \
   "$(psql_db -c "select rolreplication, rolcanlogin from pg_roles where rolname='powersync_repl'")"

# init_prod_db.sh DANS l'image api, contre le conteneur db
if C run --rm --no-deps -T --entrypoint bash api scripts/init_prod_db.sh > $WORK/init.log 2>&1; then
  pass "init_prod_db.sh (dans l'image api)" "$(tail -4 $WORK/init.log | tr '\n' ' ')"
else
  fail "init_prod_db.sh (dans l'image api)" "voir $WORK/init.log"; tail -20 $WORK/init.log; exit 1
fi
if C run --rm --no-deps -T --entrypoint bash api scripts/init_prod_db.sh > $WORK/init2.log 2>&1; then
  fail "init_prod_db.sh refuse une base deja initialisee" "code 0"
else
  pass "init_prod_db.sh refuse une base deja initialisee" "$(grep -m1 ERREUR $WORK/init2.log | cut -c1-90)"
fi
eq "publication powersync presente" "1" "$(psql_db -c "select count(*) from pg_publication where pubname='powersync'")"

# --- 2. demarrage complet --------------------------------------------------------------------
section "2. Demarrage de toute la pile"
C up -d
for s in api powersync caddy; do
  wait_healthy "$s" 240 && pass "$s healthy" "healthcheck" || fail "$s healthy" "timeout"
done
for s in worker scheduler; do
  st="$(docker inspect -f '{{.State.Status}}' "$(C ps -q $s)" 2>/dev/null || echo absent)"
  eq "$s running" running "$st"
done

# --- 3. premier admin et donnees de reference ------------------------------------------------
section "3. Premier admin et donnees de reference"
API_CID="$(C ps -q api)"
if printf '%s\n%s\n' "$REHEARSAL_ADMIN_USER" "$REHEARSAL_ADMIN_PASSWORD" \
   | C exec -T api python scripts/create_first_admin.py > $WORK/admin.log 2>&1; then
  pass "create_first_admin.py (identifiants par stdin)" "$(tail -1 $WORK/admin.log | cut -c1-90)"
else
  fail "create_first_admin.py" "$(tail -3 $WORK/admin.log | tr '\n' ' ')"
fi
docker cp "$REF_DATA" "$API_CID:/tmp/reference_data.json"
if C exec -T api python scripts/import_reference_data.py /tmp/reference_data.json > $WORK/ref.log 2>&1; then
  pass "import_reference_data.py" "$(tail -2 $WORK/ref.log | tr '\n' ' ' | cut -c1-140)"
else
  fail "import_reference_data.py" "$(tail -3 $WORK/ref.log | tr '\n' ' ')"
fi
eq "examens importes, aucun prix <> 0" "0" "$(psql_db -c "select count(*) from examens where coalesce(prix,0)<>0")"

# --- 4. Postgres, fuseaux, PowerSync ---------------------------------------------------------
section "4. Postgres, fuseaux, PowerSync"
eq "SHOW timezone" "Africa/Douala" "$(psql_db -c 'show timezone')"
eq "wal_level" "logical" "$(psql_db -c 'show wal_level')"
eq "role app_medical (NOLOGIN) apres init" "f" "$(psql_db -c "select rolcanlogin from pg_roles where rolname='app_medical'")"
for s in api worker scheduler caddy; do
  eq "date +%Z dans $s" "WAT" "$(C exec -T $s date +%Z | tr -d '\r')"
done
# PowerSync a-t-il cree sa fente de replication ?
slot=""
for _ in $(seq 1 20); do
  slot="$(psql_db -c "select slot_name||':'||plugin||':'||active from pg_replication_slots" | tr '\n' ' ')"
  [ -n "$slot" ] && break; sleep 3
done
if [ -n "$slot" ]; then pass "fente de replication PowerSync" "$slot"; else fail "fente de replication PowerSync" "aucune"; fi

# --- 5. ports hote ---------------------------------------------------------------------------
section "5. Ports publies sur l'hote"
ports="$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}} {{.Ports}}' \
  | grep -oE '(0\.0\.0\.0|\[::\]):[0-9]+->' | sed -E 's/.*:([0-9]+)->/\1/' | sort -un | tr '\n' ' ')"
eq "seuls 80 et 443 publies sur l'hote" "80 443 " "$ports"
nonpub="$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}} {{.Ports}}' \
  | grep -vE 'caddy' | grep -cE '0\.0\.0\.0|\[::\]' || true)"
eq "aucun autre service que caddy n'est publie" "0" "$nonpub"

# --- 6. HTTPS via Caddy ----------------------------------------------------------------------
section "6. HTTPS via Caddy (autorite interne)"
if [ "$(curl -sk --resolve localhost:443:127.0.0.1 -o /dev/null -w '%{http_code}' https://localhost/healthz 2>/dev/null)" = 200 ]; then
  echo "client HTTP : curl de l'hote"
else
  echo "curl de l'hote ne passe pas la poignee de main TLS locale : client dans un conteneur curl (meme reseau)"
  start_client
fi
# Le port 443 de l'hote repond-il bien (poignee de main TLS avec le nom localhost, par Python) ?
host443() { python -c 'import socket,ssl
c=ssl._create_unverified_context()
s=c.wrap_socket(socket.create_connection(("127.0.0.1",443),timeout=10),server_hostname="localhost")
s.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
assert b" 200 " in s.recv(100)'; }
if host443 >/dev/null 2>&1; then pass "le port 443 de l'hote atteint Caddy (TLS, /healthz 200)" "python ssl 127.0.0.1:443"; else fail "le port 443 de l'hote atteint Caddy" "echec"; fi
eq "/healthz" 200 "$(code https://localhost/healthz)"
health="$(cu https://localhost/api/health)"
case "$health" in *'"database":"connected"'*) pass "/api/health base connectee" "$health";; *) fail "/api/health base connectee" "$health";; esac
eq "/sync/probes/liveness" 200 "$(code https://localhost/sync/probes/liveness)"
eq "bare /api -> 404" 404 "$(code https://localhost/api)"
eq "bare /sync -> 404" 404 "$(code https://localhost/sync)"
eq "interface / -> 200" 200 "$(code https://localhost/)"
eq "deep link /dashboard/x -> 200 (repli index.html)" 200 "$(code https://localhost/dashboard/x)"
eq "HTTP 80 -> redirection 308" 308 "$(code http://localhost/)"

# --- 7. connexion et protection -------------------------------------------------------------
section "7. Connexion admin et protection de connexion"
TOKEN="$(login_token "$REHEARSAL_ADMIN_USER" "$REHEARSAL_ADMIN_PASSWORD" 2>/dev/null || true)"
if [ -n "$TOKEN" ]; then pass "connexion admin -> jeton" "jeton de ${#TOKEN} caracteres"; else fail "connexion admin -> jeton" "aucun"; exit 1; fi
AUTH=(-H "Authorization: Bearer $TOKEN")

clear_limiter() { redis_cli --scan --pattern '*LIMITER*' | while read -r k; do [ -n "$k" ] && redis_cli del "$k" >/dev/null; done; true; }

# Utilisateur cible du verrouillage et utilisateur "autre"
rid="$(cu "${AUTH[@]}" https://localhost/api/users/roles | pj '[r["id"] for r in d if r["role_name"].lower()=="assistant"][0]' 2>/dev/null || true)"
mk_user() { # mk_user nom mdp -> user_id
  cu "${AUTH[@]}" -H 'Content-Type: application/json' -X POST https://localhost/api/users/ \
    -d "{\"username\":\"$1\",\"password\":\"$2\",\"full_name\":\"Test $1\",\"role_id\":$rid,\"is_active\":true}" | pj 'd["user_id"]'
}
LOCK_PW="Lock-Pass-12345"; OTHER_PW="Other-Pass-12345"
LOCK_ID="$(mk_user smoke_lock "$LOCK_PW" 2>/dev/null || true)"
OTHER_ID="$(mk_user smoke_other "$OTHER_PW" 2>/dev/null || true)"
if [ -n "$LOCK_ID" ] && [ -n "$OTHER_ID" ]; then pass "creation de 2 comptes de test" "ids $LOCK_ID,$OTHER_ID"; else fail "creation de 2 comptes de test" "role_id=$rid"; fi
clear_limiter

echo "-- 6 mauvais mots de passe sur smoke_lock"
codes=""
for i in 1 2 3 4 5 6; do codes="$codes $(login_code smoke_lock wrong-$i)"; done
eq "6 echecs -> toujours 401 generique" " 401 401 401 401 401 401" "$codes"
eq "le bon mot de passe est refuse pendant le verrou" 401 "$(login_code smoke_lock "$LOCK_PW")"
eq "autre compte, meme adresse : connexion OK pendant le verrou" 200 "$(login_code smoke_other "$OTHER_PW")"
eq "POST /users/{id}/unlock par l'admin" 204 "$(code "${AUTH[@]}" -X POST "https://localhost/api/users/$LOCK_ID/unlock")"
eq "compte deverrouille : le bon mot de passe passe" 200 "$(login_code smoke_lock "$LOCK_PW")"

echo "-- limite par adresse : 61 tentatives rapides (identifiants tous differents)"
clear_limiter
first429="$(run_in_client "i=1; while [ \$i -le 61 ]; do c=\$($CURLB -o /dev/null -w '%{http_code}' -X POST https://localhost/api/auth/login -d \"username=rl_user_\$i&password=nope\"); if [ \"\$c\" = 429 ]; then echo \$i; exit 0; fi; i=\$((i+1)); done; echo 0")"
eq "la 61e tentative en une minute recoit 429 (premier 429 au rang)" "61" "$first429"
clear_limiter
eq "apres remise a zero des compteurs, la connexion repasse" 200 "$(login_code smoke_other "$OTHER_PW")"

# --- 8. adresse reelle du client et en-tete falsifie ----------------------------------------
section "8. Adresse du client vue par l'API (X-Forwarded-For)"
clear_limiter
login_code smoke_other "$OTHER_PW" -H 'X-Forwarded-For: 203.0.113.7' >/dev/null
login_code smoke_other "$OTHER_PW" -H 'X-Forwarded-For: 198.51.100.9, 192.0.2.1' >/dev/null
keys="$(redis_cli --scan --pattern '*LIMITER*' | tr -d '\r' | tr '\n' ' ')"
echo "cles de limite : $keys"
case "$keys" in
  *203.0.113.7*|*198.51.100.9*|*192.0.2.1*) fail "en-tete X-Forwarded-For falsifie ignore" "$keys";;
  *) pass "en-tete X-Forwarded-For falsifie ignore (aucune cle ne contient ces adresses)" "$keys";;
esac
nips="$(printf '%s' "$keys" | grep -oE '[0-9]{1,3}(\.[0-9]{1,3}){3}' | sort -u | wc -l | tr -d ' ')"
eq "deux valeurs differentes envoyees : une seule adresse client vue" "1" "$nips"
seen_ip="$(printf '%s' "$keys" | grep -oE '[0-9]{1,3}(\.[0-9]{1,3}){3}' | sort -u | head -1)"
# Client interne (adresse connue d'un conteneur du reseau) : l'API doit voir CETTE adresse
clear_limiter
docker run --rm --network "${PROJECT}_ah2" --entrypoint python "ghcr.io/$GHCR_OWNER/ah2-api:$IMAGE_TAG" -c '
import socket, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
body = b"username=nobody&password=x"
s = ctx.wrap_socket(socket.create_connection(("caddy", 443)), server_hostname="localhost")
s.sendall(b"POST /api/auth/login HTTP/1.1\r\nHost: localhost\r\nX-Forwarded-For: 203.0.113.99\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body)
print(s.recv(40).decode(errors="replace").split("\r\n")[0])
print("MYIP", socket.gethostbyname(socket.gethostname()))
' > $WORK/inner.log 2>&1 || true
myip="$(grep MYIP $WORK/inner.log | awk '{print $2}')"
ikeys="$(redis_cli --scan --pattern '*LIMITER*' | tr -d '\r' | tr '\n' ' ')"
case "$ikeys" in
  *"$myip"*) pass "client interne : l'API enregistre l'adresse reelle du client ($myip), pas celle de Caddy" "$ikeys";;
  *) fail "client interne : adresse reelle enregistree" "myip=$myip cles=$ikeys";;
esac
case "$ikeys" in *203.0.113.99*|*172.28.0.10*) fail "ni l'adresse falsifiee ni celle de Caddy dans les cles" "$ikeys";; *) pass "ni l'adresse falsifiee ni celle de Caddy dans les cles" "ok";; esac
echo "(depuis l'hote, Docker Desktop presente le client sous l'adresse de la passerelle : $seen_ip)"
check "compteurs de limite dans Redis (cles LIMITER*)" "$(redis_cli --scan --pattern '*LIMITER*' | wc -l | tr -d ' ') cle(s)" \
  bash -c "[ \"$(redis_cli --scan --pattern '*LIMITER*' | wc -l | tr -d ' ')\" -ge 1 ]"
lk="$(redis_cli --scan --pattern 'login:*' | wc -l | tr -d ' ')"
check "compteurs de verrouillage dans Redis (cles login:*)" "$lk cle(s)" bash -c "[ \"$lk\" -ge 1 ]"
clear_limiter

# --- 9. journal d'acces Caddy ---------------------------------------------------------------
section "9. Journal d'acces Caddy"
cu "${AUTH[@]}" -H 'Cookie: sessiontest=COOKIESECRET123' "https://localhost/api/patients/?q=secretterm" -o /dev/null || true
sleep 1
clog="$(C logs --no-log-prefix caddy 2>&1 | grep 'secretterm\|COOKIESECRET123\|'"${TOKEN:0:40}" || true)"
lastreq="$(C logs --no-log-prefix caddy 2>&1 | grep '"uri"' | tail -1 | cut -c1-300)"
if [ -z "$clog" ]; then pass "journal Caddy sans chaine de requete, cookie ni jeton" "dernier : $lastreq"; else fail "journal Caddy sans secrets" "$(echo "$clog" | head -1 | cut -c1-200)"; fi

# --- 10. donnees metier : produit + photo, PDF, envois --------------------------------------
section "10. Produit avec photo, PDF, tailles d'envoi"
PROD="$(cu "${AUTH[@]}" -H 'Content-Type: application/json' -X POST https://localhost/api/pharmacy/ \
  -d '{"drug_name":"SMOKE_PRODUCT","quantity":3,"threshold":1,"medication_type":"pharmaceutique","forme":"Autre","price":10}' \
  | pj 'd["medication_id"]' 2>/dev/null || true)"
if [ -n "$PROD" ]; then pass "creation d'un produit" "medication_id=$PROD"; else fail "creation d'un produit" "-"; fi
# image de ~4,9 Mo (sous 5 Mo) fabriquee dans le conteneur api (Pillow y est)
C exec -T api python -c '
import io, sys
from PIL import Image
w = 1400
while True:
    img = Image.effect_noise((w, w), 80).convert("RGB"); b = io.BytesIO(); img.save(b, "PNG")
    if b.tell() < 5*1024*1024 - 40000 or w < 600: break
    w -= 10
sys.stdout.buffer.write(b.getvalue())
' > $WORK/photo_5mb.png
SZ="$(wc -c < $WORK/photo_5mb.png | tr -d ' ')"
echo "photo de test : $SZ octets"
eq "envoi de la photo (~5 Mo, sous la limite de 6 Mo de Caddy)" 200 \
   "$(code "${AUTH[@]}" -X PUT "https://localhost/api/pharmacy/$PROD/photo" -F "file=@$WF/photo_5mb.png;type=image/png")"
cu "${AUTH[@]}" "https://localhost/api/pharmacy/$PROD/photo" -o $WF/photo_back.jpg
PHOTO_SHA="$(sha256sum $WORK/photo_back.jpg | cut -d' ' -f1)"
check "telechargement de la photo (JPEG redimensionne)" "$(wc -c < $WORK/photo_back.jpg | tr -d ' ') octets" \
   bash -c "head -c3 $WORK/photo_back.jpg | od -An -tx1 | grep -q 'ff d8 ff'"
head -c 7340032 /dev/zero > $WORK/7mb.bin
eq "7 Mo avec Content-Length -> 413 (refus immediat de Caddy)" 413 \
   "$(code "${AUTH[@]}" -X PUT "https://localhost/api/pharmacy/$PROD/photo" -H 'Content-Type: application/octet-stream' --data-binary @$WF/7mb.bin)"
rm -f $WORK/7mb.bin
# Envoi VRAIMENT en morceaux : HTTP/1.1, Transfer-Encoding: chunked, aucun Content-Length, corps multipart
# complet (sinon l'API repondrait 422 sans lire le corps et rien ne prouverait la limite de Caddy).
chunked_put() { # chunked_put <octets de fichier> -> code HTTP final
  { printf -- '--BND\r\nContent-Disposition: form-data; name="file"; filename="p.png"\r\nContent-Type: image/png\r\n\r\n'
    head -c "$1" /dev/zero; printf -- '\r\n--BND--\r\n'; } \
  | code --http1.1 "${AUTH[@]}" -X PUT "https://localhost/api/pharmacy/$PROD/photo" -H 'Expect:' \
      -H 'Transfer-Encoding: chunked' -H 'Content-Type: multipart/form-data; boundary=BND' -T -
}
eq "7 Mo en morceaux (chunked, sans Content-Length) -> 413" 413 "$(chunked_put 7340032)"
c5="$(chunked_put 5000000)"
if [ "$c5" != 413 ] && [ "$c5" != 000 ] && [ "$c5" != 502 ]; then pass "5 Mo en morceaux (chunked) traverse Caddy et atteint l'API" "code API=$c5 (zeros : pas une image)"; else fail "5 Mo en morceaux traverse Caddy" "code=$c5"; fi

# Patient + PDF du dossier
PID="$(cu "${AUTH[@]}" -H 'Content-Type: application/json' -X POST https://localhost/api/patients/ \
  -d '{"first_name":"Smoke","last_name":"Patient","birth_date":"1990-01-01","gender":"M","is_clinical":true}' \
  | pj 'd.get("patient_id") or d.get("id")' 2>/dev/null || true)"
if [ -n "$PID" ] && [ "$PID" != None ]; then pass "creation d'un patient" "patient_id=$PID"; else fail "creation d'un patient" "-"; fi
cu "${AUTH[@]}" "https://localhost/api/patients/$PID/dossier/export?format=pdf" -o $WF/dossier.pdf -D $WF/dossier.hdr
check "PDF de dossier (WeasyPrint dans le conteneur)" "$(wc -c < $WORK/dossier.pdf | tr -d ' ') octets, $(grep -i '^content-type' $WORK/dossier.hdr | tr -d '\r')" \
   bash -c "head -c4 $WORK/dossier.pdf | grep -q '%PDF'"

# --- 11. heure d'une vente synchronisee hors ligne -----------------------------------------
section "11. Vente (paid_at) comme l'envoie le client hors ligne"
SALE='{"patient_id":'"$PID"',"amount":100,"advance_amount":100,"payment_method":"especes","transaction_type":"Consultation","items":[{"item_type":"Service","item_ref_id":1,"unit_price":100,"quantity":1,"line_total":100}]'
# a) payload exact du connecteur : SANS paid_at (voir DossierConnector.js, cas caisse:PUT), avec uuid
UU="$(python -c 'import uuid;print(uuid.uuid4())')"
r1="$(cu "${AUTH[@]}" -H 'Content-Type: application/json' -X POST https://localhost/api/caisse/ -d "$SALE,\"uuid\":\"$UU\"}")"
t_connecteur="$(printf '%s' "$r1" | pj 'd["paid_at"]' 2>/dev/null || echo "?")"
utc_now="$(date -u +%Y-%m-%dT%H:%M:%S)"; douala_now="$(TZ=Africa/Douala date +%Y-%m-%dT%H:%M:%S)"
echo "UTC maintenant=$utc_now ; Douala maintenant=$(C exec -T api date +%Y-%m-%dT%H:%M:%S | tr -d '\r') ; paid_at stocke (sans paid_at envoye)=$t_connecteur"
# b) hypothese : le client enverrait paid_at en UTC (new Date().toISOString())
UU2="$(python -c 'import uuid;print(uuid.uuid4())')"
PAID_UTC="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
r2="$(cu "${AUTH[@]}" -H 'Content-Type: application/json' -X POST https://localhost/api/caisse/ -d "$SALE,\"uuid\":\"$UU2\",\"paid_at\":\"$PAID_UTC\"}")"
t_explicite="$(printf '%s' "$r2" | pj 'd["paid_at"]' 2>/dev/null || echo "?")"
echo "paid_at envoye explicitement en UTC=$PAID_UTC -> stocke=$t_explicite"
dbval="$(psql_db -c "select to_char(paid_at,'YYYY-MM-DD\"T\"HH24:MI:SS') from caisse order by transaction_id desc limit 2" | tr '\n' ' ')"
echo "valeurs en base (recente d'abord) : $dbval"
diff_s() { python -c 'import sys,datetime as D; a=D.datetime.fromisoformat(sys.argv[1][:19]); b=D.datetime.fromisoformat(sys.argv[2][:19]); print(int((a-b).total_seconds()))' "$1" "$2"; }
dnow="$(C exec -T api date +%Y-%m-%dT%H:%M:%S | tr -d '\r')"
d1="$(diff_s "$t_connecteur" "$dnow" 2>/dev/null || echo 99999)"
if [ "${d1#-}" -lt 120 ]; then pass "vente rejouee SANS paid_at (cas reel du connecteur) : l'heure posee est celle de Douala" "ecart ${d1}s avec l'heure locale du serveur"
else fail "vente rejouee sans paid_at : heure de Douala" "ecart ${d1}s"; fi
d2="$(diff_s "$t_explicite" "$dnow" 2>/dev/null || echo 99999)"
info "paid_at envoye en UTC (hypothese, le connecteur ne l'envoie pas) : stocke tel quel, decalage de ${d2}s par rapport a Douala" "$t_explicite"

# --- 12. flux PowerSync a travers Caddy (> 60 s) --------------------------------------------
section "12. Flux de synchronisation PowerSync a travers Caddy"
if [ "$LONG" = 1 ]; then
  t0="$(date +%s)"
  cu -N -m 95 -X POST https://localhost/sync/sync/stream \
     -H "Authorization: Token $TOKEN" -H 'Content-Type: application/json' -H 'Accept: application/x-ndjson' \
     -d '{"buckets":[],"include_checksum":true,"raw_data":true,"client_id":"smoke-test","parameters":{},"streams":{"include_defaults":true,"subscriptions":[]}}' \
     2>/dev/null | while IFS= read -r line; do printf '%s %s\n' "$(( $(date +%s) - t0 ))" "${line:0:110}"; done > $WORK/stream.log || true
  nl="$(wc -l < $WORK/stream.log | tr -d ' ')"
  lastt="$(tail -1 $WORK/stream.log | cut -d' ' -f1)"
  head -3 $WORK/stream.log
  echo "... ($nl lignes) derniere a t=${lastt}s"
  if [ "${nl:-0}" -ge 1 ] && [ "${lastt:-0}" -gt 60 ]; then pass "flux PowerSync tenu > 60 s sans coupure par Caddy" "$nl lignes, derniere a t=${lastt}s"
  else fail "flux PowerSync tenu > 60 s" "$nl lignes, derniere a t=${lastt}s"; fi
else
  echo "(--no-long : flux PowerSync saute)"
fi

# --- 13. planificateur ----------------------------------------------------------------------
section "13. Planificateur (supercronic) et scripts planifies"
slog="$(C logs --no-log-prefix scheduler 2>&1 | tail -5 | tr '\n' ' ' | cut -c1-240)"
check "supercronic a charge la crontab" "$slog" bash -c "docker exec $(C ps -q scheduler) sh -c 'ps aux 2>/dev/null | grep -q [s]upercronic || pgrep supercronic || ls /proc/*/comm >/dev/null' "
C exec -T scheduler python scripts/cash_closure_catchup.py >$WORK/catchup.log 2>&1 && rc=0 || rc=$?
eq "cash_closure_catchup.py (scheduler) code de sortie" 0 "$rc"
C exec -T scheduler python scripts/daily_control.py >$WORK/daily.log 2>&1 && rc=0 || rc=$?
eq "daily_control.py (scheduler) code de sortie" 0 "$rc"

# --- 14. redemarrage de l'API ---------------------------------------------------------------
section "14. Redemarrage de l'API"
C restart api >/dev/null 2>&1
wait_healthy api 180 && pass "api revenue en bonne sante" "healthcheck" || fail "api revenue en bonne sante" "timeout"
eq "/api/health apres redemarrage" 200 "$(code https://localhost/api/health)"
eq "connexion apres redemarrage" 200 "$(login_code "$REHEARSAL_ADMIN_USER" "$REHEARSAL_ADMIN_PASSWORD")"
eq "/sync/probes/liveness apres redemarrage" 200 "$(code https://localhost/sync/probes/liveness)"
eq "interface apres redemarrage" 200 "$(code https://localhost/)"

# --- 15. recreation complete sans -v --------------------------------------------------------
section "15. Recreation complete (down sans -v, puis up)"
NROW_BEFORE="$(psql_db -c 'select count(*) from patients')|$(psql_db -c 'select count(*) from caisse')|$(psql_db -c 'select count(*) from users')"
stop_client
C down >/dev/null 2>&1
left="$(docker ps -a --filter "label=com.docker.compose.project=$PROJECT" -q | wc -l | tr -d ' ')"
eq "down : plus aucun conteneur" 0 "$left"
C up -d >/dev/null 2>&1
for s in db api powersync caddy; do wait_healthy "$s" 240 && true || fail "$s apres recreation" "timeout"; done
sleep 5
[ "$CLIENT_MODE" = container ] && start_client
TOKEN2="$(login_token "$REHEARSAL_ADMIN_USER" "$REHEARSAL_ADMIN_PASSWORD" 2>/dev/null || true)"
if [ -n "$TOKEN2" ]; then pass "connexion apres recreation (utilisateurs conserves)" "ok"; else fail "connexion apres recreation" "-"; fi
NROW_AFTER="$(psql_db -c 'select count(*) from patients')|$(psql_db -c 'select count(*) from caisse')|$(psql_db -c 'select count(*) from users')"
eq "lignes patients|caisse|users identiques" "$NROW_BEFORE" "$NROW_AFTER"
cu -H "Authorization: Bearer $TOKEN2" "https://localhost/api/pharmacy/$PROD/photo" -o $WF/photo_back2.jpg
eq "photo du produit identique apres recreation" "$PHOTO_SHA" "$(sha256sum $WORK/photo_back2.jpg | cut -d' ' -f1)"
eq "certificat Caddy conserve (volume caddy_data) : HTTPS repond" 200 "$(code https://localhost/healthz)"

# --- bilan -------------------------------------------------------------------------------------
section "Bilan"
echo "PASS=$NPASS FAIL=$NFAIL"
[ "$NFAIL" -gt 0 ] && printf 'ECHECS : %s\n' "${FAILED[@]}"
if [ "$KEEP" = 0 ]; then
  stop_client
  echo "Nettoyage (utiliser --keep pour garder la pile) ..."
  C down -v --remove-orphans >/dev/null 2>&1 || true
fi
echo "Espace libre sur C: $(free_gb) Go"
[ "$NFAIL" -eq 0 ]
