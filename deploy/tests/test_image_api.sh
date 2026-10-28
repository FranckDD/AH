#!/bin/sh
# Test de l'image ah2-api. Usage (depuis la racine du depot) : sh deploy/tests/test_image_api.sh
# Variable : MAX_BYTES (defaut 1,5 Go).
set -u
cd "$(dirname "$0")/../.."
IMG=ah2-api:test
MAX_BYTES="${MAX_BYTES:-1610612736}"
FAIL=0
NAMES=""

# MSYS_NO_PATHCONV evite que Git Bash (Windows) transforme les chemins Linux.
export MSYS_NO_PATHCONV=1
ENVS="-e DATABASE_URL=postgresql://u:p@127.0.0.1:1/x -e JWT_SECRET=test-secret -e JWT_ALGORITHM=HS256 -e AH2_API_BASE=http://localhost:8000 -e REDIS_URL=redis://127.0.0.1:1/0"

cleanup() { for n in $NAMES; do docker rm -f "$n" >/dev/null 2>&1; done; }
trap cleanup EXIT INT TERM

ok()   { echo "OK   $1"; }
ko()   { echo "FAIL $1"; FAIL=1; }
run()  { docker run --rm "$@"; }

echo "== build"
docker build -f deploy/Dockerfile.api -t "$IMG" . || { echo "FAIL build"; exit 1; }

out=$(run --entrypoint date "$IMG" +%Z)
[ "$out" = "WAT" ] && ok "fuseau WAT" || ko "fuseau: '$out'"

out=$(run --entrypoint id "$IMG" -u)
[ "$out" != "0" ] && [ -n "$out" ] && ok "utilisateur non root ($out)" || ko "uid '$out'"

if run --entrypoint test "$IMG" -e /app/.env; then ko "/app/.env present"; else ok "pas de /app/.env"; fi
out=$(run --entrypoint sh "$IMG" -c 'find /app -name ".env*" -o -name tests -o -name "*.db" | head')
[ -z "$out" ] && ok "pas de .env/tests/*.db dans l'image" || ko "fichiers indesirables: $out"

for d in storage/product_photos storage/toxico_consents static/uploads; do
  out=$(run --entrypoint sh "$IMG" -c "test -w /app/$d && echo w")
  [ "$out" = "w" ] && ok "$d inscriptible" || ko "$d non inscriptible"
done

run --entrypoint python "$IMG" -c "import weasyprint; b=weasyprint.HTML(string='<p>ok</p>').write_pdf(); assert b[:4]==b'%PDF'" \
  && ok "WeasyPrint genere un PDF" || ko "WeasyPrint"

# Import sans variables : doit echouer pour cause de variable manquante
out=$(run --entrypoint python "$IMG" -c "import api_backend.backend_app.main" 2>&1); rc=$?
if [ $rc -ne 0 ] && echo "$out" | grep -q "must be defined\|is not set"; then ok "import sans env refuse (variable manquante)"; else ko "import sans env: rc=$rc"; fi

# shellcheck disable=SC2086
run $ENVS --entrypoint python "$IMG" -c "import api_backend.backend_app.main" >/dev/null 2>&1 \
  && ok "import de l'API avec env" || ko "import de l'API avec env"
# shellcheck disable=SC2086
run $ENVS --entrypoint python "$IMG" -c "import celery_app, tasks.toxico_tasks" >/dev/null 2>&1 \
  && ok "import celery_app + tasks" || ko "import celery_app + tasks"
run --entrypoint supercronic "$IMG" -version >/dev/null 2>&1 || run --entrypoint supercronic "$IMG" --version >/dev/null 2>&1 \
  && ok "supercronic present" || ko "supercronic"
run --entrypoint python "$IMG" -c "import alembic, os; assert os.path.isfile('alembic.ini') and os.path.isfile('ci/schema_only.sql') and os.path.isfile('ci/seed_application_roles.sql') and os.path.isfile('scripts/daily_control.py') and os.path.isfile('assets/logo_light.png')" \
  && ok "alembic.ini, ci/*.sql, scripts, logos" || ko "fichiers de deploiement manquants"

# commande inconnue
out=$(run "$IMG" bogus 2>&1); rc=$?
[ $rc -ne 0 ] && echo "$out" | grep -q "inconnue" && ok "run.sh bogus refuse (rc=$rc)" || ko "run.sh bogus rc=$rc"

# api : demarre et repond sur /health (base absente : success=false mais HTTP 200)
N=ah2api-test-$$; NAMES="$NAMES $N"
# shellcheck disable=SC2086
docker run -d --name "$N" $ENVS "$IMG" api >/dev/null
i=0; code=""
while [ $i -lt 30 ]; do
  code=$(docker exec "$N" python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).status)" 2>/dev/null)
  [ "$code" = "200" ] && break
  i=$((i+1)); sleep 2
done
[ "$code" = "200" ] && ok "api repond sur /health" || { ko "api /health ($code)"; docker logs "$N" 2>&1 | tail -15; }
# healthcheck.sh doit echouer : HTTP 200 mais success=false (base injoignable)
if docker exec "$N" /app/deploy/entrypoints/healthcheck.sh; then ko "healthcheck.sh passe alors que la base est injoignable"; else ok "healthcheck.sh echoue base injoignable"; fi
# gunicorn demarre avec les options de delai et le tmp en memoire
docker exec "$N" sh -c 'tr "\0" " " < /proc/1/cmdline' | grep -q -- "--timeout 120 --graceful-timeout 30 --worker-tmp-dir /dev/shm" \
  && ok "gunicorn: timeout 120, graceful 30, tmp /dev/shm" || ko "options gunicorn"
docker rm -f "$N" >/dev/null 2>&1

# volume nomme neuf monte sur storage/product_photos : inscriptible par l'utilisateur de l'image
V=ah2vol-test-$$
docker volume create "$V" >/dev/null
out=$(run -v "$V":/app/storage/product_photos --entrypoint sh "$IMG" -c 'touch /app/storage/product_photos/x && echo w' 2>&1)
[ "$out" = "w" ] && ok "volume neuf inscriptible par uid 10001" || ko "volume neuf: $out"
docker volume rm "$V" >/dev/null 2>&1

# controle quotidien avec base injoignable : code de sortie non nul (cwd, imports, erreur geree)
# shellcheck disable=SC2086
timeout 90 docker run --rm $ENVS --entrypoint python "$IMG" scripts/daily_control.py >/dev/null 2>&1; rc=$?
[ $rc -eq 1 ] && ok "daily_control.py base injoignable -> code 1" || ko "daily_control.py rc=$rc (attendu 1)"

# worker : demarre et reste en vie quelques secondes
N=ah2worker-test-$$; NAMES="$NAMES $N"
# shellcheck disable=SC2086
docker run -d --name "$N" $ENVS "$IMG" worker >/dev/null
sleep 12
st=$(docker inspect -f '{{.State.Running}}' "$N" 2>/dev/null)
logs=$(docker logs "$N" 2>&1)
# Redis injoignable : le worker reste en vie et reessaie, "celery@... ready" n'apparait pas.
if [ "$st" = "true" ] && echo "$logs" | grep -q "celery@.* v5\|\[tasks\]"; then ok "worker demarre (tasks charges)"; else ko "worker (running=$st)"; echo "$logs" | tail -15; fi
docker rm -f "$N" >/dev/null 2>&1

# scheduler : demarre, parse la crontab, reste en vie
N=ah2sched-test-$$; NAMES="$NAMES $N"
docker run -d --name "$N" "$IMG" scheduler >/dev/null
sleep 4
st=$(docker inspect -f '{{.State.Running}}' "$N" 2>/dev/null)
logs=$(docker logs "$N" 2>&1)
if [ "$st" = "true" ] && ! echo "$logs" | grep -qi "error\|fatal\|bad crontab"; then ok "scheduler demarre (crontab lue)"; else ko "scheduler (running=$st)"; echo "$logs" | tail -10; fi
docker rm -f "$N" >/dev/null 2>&1
# crontab invalide detectee par supercronic -test
run --entrypoint supercronic "$IMG" -test /app/deploy/scheduler/crontab >/dev/null 2>&1 \
  && ok "supercronic -test valide la crontab" || ko "supercronic -test"

size=$(docker image inspect "$IMG" --format '{{.Size}}')
echo "taille de l'image: $size octets ($((size / 1048576)) Mo)"
[ "$size" -le "$MAX_BYTES" ] && ok "taille <= limite" || ko "image trop grosse"

[ $FAIL -eq 0 ] && echo "TOUT EST OK" || echo "ECHECS"
exit $FAIL
