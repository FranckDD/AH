#!/usr/bin/env bash
# Test de l'image web (ah2-web) et du Caddyfile. Depuis la racine du depot :
#   bash deploy/tests/test_caddyfile.sh                 # construit ah2-web:test puis teste
#   SKIP_BUILD=1 bash deploy/tests/test_caddyfile.sh    # reutilise ah2-web:test
# Nettoie conteneurs, reseau et fichiers temporaires a la fin (l'image ah2-web:test
# est supprimee aussi, sauf si KEEP_IMAGE=1).
set -u
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/../.." || exit 1
ROOT_WIN="$(pwd -W 2>/dev/null || pwd)"

CADDY_IMG="caddy:2.10.2-alpine"
IMG="ah2-web:test"
NET="ah2-web-test-net"
WEB="ah2-web-test"
DOMAIN_FAKE="app.example.test"
PS_PORT=8080
HTTPS_PORT=18443
FAIL=0
TMP="$(mktemp -d)"; command -v cygpath >/dev/null && TMP="$(cygpath -m "$TMP")"

ok()   { echo "OK   $*"; }
fail() { echo "FAIL $*"; FAIL=1; }
cleanup_containers() {
  docker rm -f "$WEB" ah2-stub-api ah2-stub-ps >/dev/null 2>&1
  docker network rm "$NET" >/dev/null 2>&1
}
cleanup() {
  cleanup_containers
  [ "${KEEP_IMAGE:-0}" = "1" ] || docker rmi "$IMG" >/dev/null 2>&1
  rm -rf "$TMP"
}
trap cleanup EXIT
cleanup_containers

validate() { # description, env... (DOMAIN, PS_PORT, ... en -e)
  local d="$1"; shift
  if docker run --rm "$@" -v "$ROOT_WIN/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" "$CADDY_IMG" \
       caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | grep -q "Valid configuration"; then
    ok "$d"; else fail "$d"; fi
}

echo "== (a) caddy validate (variables fictives)"
validate "validate: ACME_CA staging" -e DOMAIN="$DOMAIN_FAKE" -e PS_PORT=$PS_PORT -e ACME_EMAIL=ops@example.test \
  -e ACME_CA=https://acme-staging-v02.api.letsencrypt.org/directory -e CADDY_TLS_MODE=
validate "validate: ACME_CA absent, local_certs" -e DOMAIN=localhost -e PS_PORT=$PS_PORT -e ACME_EMAIL=ops@example.test \
  -e CADDY_TLS_MODE=local_certs

validate "validate: HSTS_HEADER production" -e DOMAIN="$DOMAIN_FAKE" -e PS_PORT=$PS_PORT -e ACME_EMAIL=ops@example.test   -e HSTS_HEADER=max-age=31536000
if docker run --rm -e DOMAIN="$DOMAIN_FAKE" -e PS_PORT=$PS_PORT -e ACME_EMAIL=ops@example.test      -v "$ROOT_WIN/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" "$CADDY_IMG"      caddy adapt --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | grep -q '"max-age=0"'; then
  ok "adapt: HSTS max-age=0 par defaut"; else fail "adapt: HSTS par defaut"; fi

echo "== (b) build de l'image et contenu de /srv"
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  if docker build -q -f deploy/Dockerfile.web -t "$IMG" --build-arg DOMAIN="$DOMAIN_FAKE" . >/dev/null 2>&1; then
    ok "docker build"; else fail "docker build"; exit 1; fi
fi
if docker run --rm --entrypoint sh "$IMG" -c '
  set -e
  if grep -rIl "127.0.0.1:8200" /srv; then echo LEAK_ENV_LOCAL; exit 1; fi
  if grep -rIl "localhost:8000" /srv; then echo DEFAULT_API_URL_USED; exit 1; fi
  grep -rIl "https://app.example.test/api" /srv/assets >/dev/null
  grep -rIl "https://app.example.test/sync" /srv/assets >/dev/null
  grep -rIl "http://127.0.0.1:9123" /srv/assets >/dev/null
  test -s /srv/sw.js; test -s /srv/manifest.webmanifest; test -s /srv/index.html; test -s /srv/registerSW.js
  test "$(id -u)" = 10001
' >"$TMP/b.out" 2>&1; then
  ok "pas de fuite .env.local, URL api/sync/pont cuites, sw.js + manifest presents, uid 10001"
else fail "contenu de /srv"; cat "$TMP/b.out"; fi

echo "== (c) repetition locale du proxy avec deux amonts factices"
docker network create "$NET" >/dev/null
# Amonts factices : un Caddy qui repond avec le chemin, Host et X-Forwarded-For recus.
stub() { # nom port alias
  docker run -d --name "$1" --network "$NET" --network-alias "$3" --entrypoint sh "$CADDY_IMG" -c \
   "printf ':$2 {\n\trespond \"path={http.request.uri} host={http.request.host} xff={http.request.header.X-Forwarded-For} proto={http.request.header.X-Forwarded-Proto}\" 200\n}\n' > /tmp/Caddyfile && caddy run --config /tmp/Caddyfile --adapter caddyfile" >/dev/null
}
stub ah2-stub-api 8000 api
stub ah2-stub-ps $PS_PORT powersync
docker run -d --name "$WEB" --network "$NET" -p 127.0.0.1:$HTTPS_PORT:443 \
  -e DOMAIN=localhost -e PS_PORT=$PS_PORT -e ACME_EMAIL=ops@example.test -e CADDY_TLS_MODE=local_certs \
  "$IMG" >/dev/null
for i in $(seq 1 30); do
  curl -sk --max-time 2 -o /dev/null https://localhost:$HTTPS_PORT/healthz && break; sleep 1
done
U=https://localhost:$HTTPS_PORT
c() { curl -sk --max-time 30 "$@"; }

[ "$(c -o /dev/null -w '%{http_code}' $U/healthz)" = 200 ] && ok "/healthz 200" || fail "/healthz"
r=$(c "$U/api/x?y=1"); echo "$r" | grep -q "path=/x?y=1 " && ok "/api/x -> stub api, chemin /x (prefixe retire)" || fail "/api/x: $r"
r=$(c $U/sync/probes/liveness); echo "$r" | grep -q "path=/probes/liveness " && ok "/sync/probes/liveness -> stub powersync, chemin /probes/liveness" || fail "/sync: $r"
r=$(c -H 'X-Forwarded-For: 1.2.3.4' $U/api/x)
echo "     recu par l'amont: $r"
echo "$r" | grep -q "1.2.3.4" && fail "XFF forge cru par l'amont (api)" || ok "XFF forge ecrase (api)"
echo "$r" | grep -Eq "xff=[0-9a-f.:]+ " && ok "XFF = une seule adresse (client reel vu par Caddy)" || fail "XFF format"
echo "$r" | grep -q "proto=https" && ok "X-Forwarded-Proto=https" || fail "proto"
r=$(c -H 'X-Forwarded-For: 1.2.3.4' $U/sync/x); echo "$r" | grep -q "1.2.3.4" && fail "XFF forge cru (sync)" || ok "XFF forge ecrase (sync)"

head -c 5242880 /dev/zero > "$TMP/5mb.bin"; head -c 7340032 /dev/zero > "$TMP/7mb.bin"
code=$(c -o /dev/null -w '%{http_code}' -X POST --data-binary @"$TMP/5mb.bin" -H 'Content-Type: application/octet-stream' $U/api/x)
[ "$code" = 200 ] && ok "POST 5 Mo passe ($code)" || fail "POST 5 Mo: $code"
code=$(c -o /dev/null -w '%{http_code}' -X POST --data-binary @"$TMP/7mb.bin" -H 'Content-Type: application/octet-stream' $U/api/x)
[ "$code" = 413 ] && ok "POST 7 Mo refuse ($code)" || fail "POST 7 Mo: $code"

h=$(c -D - -o "$TMP/root.html" $U/)
echo "$h" | grep -qi "^cache-control: no-cache" && ok "/ no-cache" || fail "/ cache-control"
grep -q '<div id="app">' "$TMP/root.html" && ok "/ sert index.html" || fail "/ index.html"
h=$(c -D - -o "$TMP/deep.html" $U/dashboard/foo)
{ echo "$h" | head -1 | grep -q 200 && cmp -s "$TMP/root.html" "$TMP/deep.html"; } && ok "/dashboard/foo = index.html (200)" || fail "lien profond"
echo "$h" | grep -qi "^cache-control: no-cache" && ok "lien profond no-cache" || fail "lien profond cache-control"
for f in sw.js manifest.webmanifest registerSW.js; do
  h=$(c -D - -o /dev/null $U/$f)
  echo "$h" | head -1 | grep -q 200 || fail "/$f pas 200"
  echo "$h" | grep -qi "^cache-control: no-cache" && ok "/$f no-cache" || fail "/$f cache-control"
  echo "     $f: $(echo "$h" | grep -i '^content-type' | tr -d '\r')"
done
c -D - -o /dev/null $U/sw.js | grep -i '^content-type' | grep -qi javascript && ok "sw.js type javascript" || fail "sw.js content-type"
c -D - -o /dev/null $U/manifest.webmanifest | grep -i '^content-type' | grep -Eqi 'manifest\+json|application/json' && ok "manifest type json" || fail "manifest content-type"

asset=$(docker run --rm --entrypoint sh "$IMG" -c 'ls /srv/assets | grep -E "\.js$" | head -1')
h=$(c -D - -o /dev/null $U/assets/$asset)
echo "$h" | grep -qi "^cache-control: public, max-age=31536000, immutable" && ok "/assets/$asset immutable" || fail "asset cache-control"
h=$(c -D - -o /dev/null -H 'Accept-Encoding: gzip' $U/assets/$asset)
echo "$h" | grep -Eqi '^content-encoding: (gzip|zstd)' && ok "compression" || fail "compression"
h=$(c -D - -o /dev/null $U/assets/inconnu-abc123.js)
echo "$h" | head -1 | grep -q 404 && ok "/assets/inconnu.js = 404" || fail "asset inconnu: $(echo "$h" | head -1)"
echo "$h" | grep -qi "^cache-control: no-store" && ok "404 jamais mis en cache" || fail "404 cache-control: $(echo "$h" | grep -i cache-control)"
code=$(c -o /dev/null -w '%{http_code}' $U/assets/); [ "$code" != 200 ] && ok "/assets/ non listable ($code)" || fail "listing /assets/"
body=$(c $U/assets/); echo "$body" | grep -Eqi "Index of|<table" && fail "listing /assets/ (corps)" || ok "pas de listing dans le corps"
h=$(c -D - -o /dev/null $U/)
csp=$(echo "$h" | grep -i '^content-security-policy' | tr -d '\r')
echo "$csp" | grep -q "frame-ancestors 'none'" && ok "CSP presente" || fail "CSP"
for hd in strict-transport-security x-content-type-options x-frame-options referrer-policy; do
  echo "$h" | grep -qi "^$hd" && ok "en-tete $hd" || fail "en-tete $hd"
done
echo "     $csp"
docker logs "$WEB" 2>&1 | grep -q '"logger":"http.log.access' && ok "journal d'acces JSON sur stdout" || fail "journal d'acces"
c -H 'Cookie: sess=SECRETCOOKIE' -H 'Authorization: Bearer SECRETTOKEN' "$U/api/search?q=SECRETQUERY" >/dev/null
sleep 1
docker logs "$WEB" 2>&1 | grep -q 'SECRETQUERY\|SECRETCOOKIE\|SECRETTOKEN' && fail "journal: requete/cookie/jeton present" || ok "journal sans requete, cookie ni jeton"
[ "$(c -o /dev/null -w '%{http_code}' $U/api)" = 404 ] && [ "$(c -o /dev/null -w '%{http_code}' $U/sync)" = 404 ] && ok "/api et /sync nus = 404" || fail "/api /sync nus"
docker exec "$WEB" id -u | grep -q 10001 && ok "Caddy tourne en uid 10001 (ports 80/443 lies)" || fail "uid"
[ "$(docker inspect --format '{{.State.Health.Status}}' "$WEB")" != "" ] && ok "HEALTHCHECK defini"

echo
docker image inspect "$IMG" --format 'Taille image: {{.Size}} octets'
[ $FAIL = 0 ] && echo "TOUS LES TESTS OK" || echo "ECHECS"
exit $FAIL
