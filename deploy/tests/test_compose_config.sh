#!/bin/bash
# Verifie deploy/docker-compose.prod.yml par analyse de `docker compose config`
# (aucun conteneur demarre, aucune image tiree). Lancer depuis la racine du depot :
#   bash deploy/tests/test_compose_config.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

COMPOSE=deploy/docker-compose.prod.yml
ENVF=deploy/.env.example
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

PY=python3
command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' 2>/dev/null || PY=python

docker compose --env-file "$ENVF" -f "$COMPOSE" config --format json > "$OUT"
echo "OK  docker compose config reussit"

"$PY" - "$OUT" "$COMPOSE" "$ENVF" <<'PYEOF'
import json, os, re, sys

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
src = open(sys.argv[2], encoding="utf-8").read()
envfile = {}
for line in open(sys.argv[3], encoding="utf-8"):
    m = re.match(r"^([A-Z_0-9]+)=(.*)$", line.rstrip("\n"))
    if m:
        envfile[m.group(1)] = m.group(2)

svcs = cfg["services"]
COMPOSE_PATH = sys.argv[2]
COMPOSE = os.path.dirname(COMPOSE_PATH) and COMPOSE_PATH
fails = []

def check(ok, msg):
    print(("OK  " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)

def mem_bytes(v):
    if isinstance(v, int):
        return v
    m = re.match(r"^(\d+)([a-zA-Z]*)$", str(v))
    n, u = int(m.group(1)), m.group(2).lower()
    return n * {"": 1, "b": 1, "k": 1024, "kb": 1024, "m": 1024**2, "mb": 1024**2,
                "g": 1024**3, "gb": 1024**3}[u]

expected = {"caddy", "api", "worker", "scheduler", "db", "redis", "powersync", "pg-storage", "backup"}
check(expected <= set(svcs), "services attendus presents: %s" % sorted(expected))

# Ports publies
published = set()
for name, s in svcs.items():
    for p in s.get("ports", []) or []:
        published.add((name, int(p["published"]), p.get("protocol", "tcp")))
check({(n) for n, _, _ in published} <= {"caddy"}, "seul caddy publie des ports")
check({(p, pr) for _, p, pr in published} <= {(80, "tcp"), (443, "tcp"), (443, "udp")},
      "ports publies limites a 80 et 443 : %s" % sorted(published))
check({80, 443} <= {p for _, p, _ in published}, "80 et 443 sont bien publies")

# Fuseau
for name, s in svcs.items():
    check((s.get("environment") or {}).get("TZ") == "Africa/Douala", "TZ=Africa/Douala sur %s" % name)

# Base
dbcmd = " ".join(svcs["db"]["command"])
check("wal_level=logical" in dbcmd, "db: wal_level=logical")
check("timezone=Africa/Douala" in dbcmd and "log_timezone=Africa/Douala" in dbcmd, "db: timezone et log_timezone Douala")
check(svcs["db"]["image"].startswith("postgres:17."), "db: image postgres 17.x precise (%s)" % svcs["db"]["image"])

# Healthchecks
for name, s in svcs.items():
    hc = s.get("healthcheck") or {}
    if name in ("worker", "scheduler"):
        check(hc.get("disable") is True, "%s: sonde de l'image neutralisee (disable)" % name)
    else:
        check(bool(hc.get("test")) and not hc.get("disable"), "healthcheck present sur %s" % name)
check(svcs["api"]["healthcheck"]["test"][-1].endswith("healthcheck.sh"), "api: sonde = healthcheck.sh")
check(svcs["api"]["healthcheck"]["start_period"] != "0s", "api: start_period defini")

# Regles communes
for name, s in svcs.items():
    check(s.get("restart") == "unless-stopped", "%s: restart unless-stopped" % name)
    lg = s.get("logging") or {}
    check(lg.get("driver") == "json-file" and lg.get("options", {}).get("max-size") == "10m"
          and lg.get("options", {}).get("max-file") == "5", "%s: rotation des journaux" % name)
    check("no-new-privileges:true" in (s.get("security_opt") or []), "%s: no-new-privileges" % name)
    check(list(s.get("networks", {}).keys()) == ["ah2"], "%s: reseau unique ah2" % name)
    check("cap_drop" not in s, "%s: pas de cap_drop (caddy a besoin de NET_BIND_SERVICE)" % name)
for name in ("worker", "scheduler"):
    check(svcs[name].get("init") is True, "%s: init: true" % name)
check(svcs["api"].get("stop_grace_period") and svcs["worker"].get("stop_grace_period"),
      "stop_grace_period sur api et worker")

# Images
for name in ("api", "worker", "scheduler"):
    check(svcs[name]["image"] == "ghcr.io/%s/ah2-api:%s" % (envfile["GHCR_OWNER"], envfile["IMAGE_TAG"]),
          "%s: image ah2-api avec GHCR_OWNER et IMAGE_TAG" % name)
check(svcs["caddy"]["image"] == "ghcr.io/%s/ah2-web:%s" % (envfile["GHCR_OWNER"], envfile["IMAGE_TAG"]),
      "caddy: image ah2-web avec GHCR_OWNER et IMAGE_TAG")
check(re.search(r"image: ghcr\.io/\$\{GHCR_OWNER[:?][^}]*\}/ah2-web:\$\{IMAGE_TAG[:?][^}]*\}", src) is not None
      and re.search(r"image: ghcr\.io/\$\{GHCR_OWNER[:?][^}]*\}/ah2-api:\$\{IMAGE_TAG[:?][^}]*\}", src) is not None,
      "source: images api/web reference ${GHCR_OWNER} et ${IMAGE_TAG}")
for name, s in svcs.items():
    img = s["image"]
    check(not img.endswith(":latest") and ":" in img.split("/")[-1], "%s: image epinglee (%s)" % (name, img))
check("@sha256:" in svcs["powersync"]["image"], "powersync: epinglee par empreinte")

# Secrets : aucune valeur litterale dans le YAML source
bad = []
for i, line in enumerate(src.splitlines(), 1):
    m = re.match(r"^\s*([A-Z_]*(?:PASSWORD|SECRET|TOKEN)[A-Z_]*)\s*:\s*(.*?)\s*$", line)
    if m and not re.match(r"^\"?\$\{[A-Z_0-9]+(:[-?][^}]*)?\}\"?$", m.group(2)):
        bad.append((i, line.strip()))
check(not bad, "aucun PASSWORD/SECRET/TOKEN litteral dans le compose %s" % bad)
check("ghp_" not in src and "BEGIN PRIVATE" not in src, "pas de jeton evident dans le compose")

# PS_APP_HS256_SECRET derive de JWT_SECRET
ps = svcs["powersync"]
check(ps["environment"]["JWT_SECRET"] == envfile["JWT_SECRET"], "powersync recoit le meme JWT_SECRET que l'API")
check(svcs["api"]["environment"]["JWT_SECRET"] == envfile["JWT_SECRET"], "api: JWT_SECRET depuis .env")
check("PS_APP_HS256_SECRET" not in ps["environment"], "PS_APP_HS256_SECRET jamais saisi (calcule)")
ep = " ".join(ps["entrypoint"])
check("PS_APP_HS256_SECRET=$$(node -e" in ep and "process.env.JWT_SECRET" in ep and "base64url" in ep
      and "export PS_APP_HS256_SECRET" in ep, "powersync: PS_APP_HS256_SECRET = base64url(JWT_SECRET) au demarrage")

# Proxy
check(svcs["api"]["environment"]["FORWARDED_ALLOW_IPS"]
      == svcs["caddy"]["networks"]["ah2"]["ipv4_address"], "FORWARDED_ALLOW_IPS = adresse fixe de caddy")
subnet = cfg["networks"]["ah2"]["ipam"]["config"][0]["subnet"]
check(subnet == "172.28.0.0/24", "reseau a sous-reseau fixe " + subnet)
check(svcs["caddy"]["environment"]["ACME_CA"], "ACME_CA de caddy jamais vide")
check(svcs["api"]["environment"]["IS_PROD"] == "true", "api: IS_PROD=true")
check(svcs["api"]["environment"]["CORS_ORIGINS"] == "https://" + envfile["DOMAIN"], "api: CORS_ORIGINS = https://DOMAIN")
check(svcs["api"]["environment"]["AH2_API_BASE"] == "https://%s/api" % envfile["DOMAIN"], "api: AH2_API_BASE")
check("@db:5432/" in svcs["api"]["environment"]["DATABASE_URL"], "api: DATABASE_URL vise db")

# Volumes
vols = set(cfg.get("volumes", {}))
need = {"pgdata", "ps_storage_data", "uploads", "product_photos", "consents", "caddy_data", "caddy_config", "redis_data",
        "backup_status"}
check(need <= vols, "volumes nommes presents %s" % sorted(need))
api_targets = {v["target"]: v["source"] for v in svcs["api"]["volumes"]}
check(api_targets.get("/app/storage/product_photos") == "product_photos"
      and api_targets.get("/app/storage/toxico_consents") == "consents"
      and api_targets.get("/app/static/uploads") == "uploads", "api: volumes montes sur les 3 dossiers")
check(svcs["api"]["environment"]["PRODUCT_PHOTO_DIR"] == "/app/storage/product_photos"
      and svcs["api"]["environment"]["CONSENT_STORAGE_DIR"] == "/app/storage/toxico_consents",
      "variables de dossiers pointent vers les volumes")
check(any(v["target"] == "/docker-entrypoint-initdb.d" for v in svcs["db"]["volumes"]), "db: dossier d'init monte")

# Memoire
total = sum(mem_bytes(s["mem_limit"]) for s in svcs.values() if "mem_limit" in s)
check(all("mem_limit" in s for s in svcs.values()), "mem_limit sur chaque service")
check(total < 6.5 * 1024**3, "somme des mem_limit %.2f Go < 6,5 Go" % (total / 1024**3))

# --- Sauvegardes (tache 9) ---
bk = svcs["backup"]
check(bk["image"] == "ghcr.io/%s/ah2-backup:%s" % (envfile["GHCR_OWNER"], envfile["IMAGE_TAG"]),
      "backup: image ah2-backup avec GHCR_OWNER et IMAGE_TAG")
check(not bk.get("ports"), "backup: aucun port publie")
check(mem_bytes(bk["mem_limit"]) == 256 * 1024**2, "backup: mem_limit 256m")
bv = {v["target"]: v for v in bk["volumes"]}
check(all(bv["/data/" + n].get("read_only") is True and bv["/data/" + n]["source"] == n
          for n in ("uploads", "product_photos", "consents")), "backup: les 3 volumes de fichiers en lecture seule")
check(bv["/backups/repo"]["type"] == "bind" and not bv["/backups/repo"].get("read_only"),
      "backup: depot local = dossier hote en ecriture (hors volumes nommes)")
check(bv["/var/lib/ah2-status"]["source"] == "backup_status" and not bv["/var/lib/ah2-status"].get("read_only"),
      "backup: volume backup_status en ecriture (le service alerts le montera en lecture seule)")
check(bv["/run/secrets/backup_sftp_key"].get("read_only") is True and bv["/run/secrets/backup_known_hosts"].get("read_only") is True,
      "backup: cle SFTP et known_hosts montes en lecture seule")
benv = bk["environment"]
check(benv["RESTIC_PASSWORD"] == envfile["RESTIC_PASSWORD"] and benv["PGPASSWORD"] == envfile["POSTGRES_PASSWORD"],
      "backup: secrets uniquement depuis .env")
check(all(k in benv for k in ("BACKUP_HOURLY_CRON", "BACKUP_NIGHTLY_CRON", "BACKUP_OFFSITE_CRON", "KEEP_HOURLY",
                              "KEEP_DAILY", "KEEP_WEEKLY", "KEEP_MONTHLY")), "backup: horaires et retention reglables par variables")
check(bk["healthcheck"]["start_period"] not in ("0s", None) and "last_success_hourly" in bk["healthcheck"]["test"][-1]
      and "7200" in bk["healthcheck"]["test"][-1], "backup: sonde = last_success_hourly de moins de 2 h")
check(bk["depends_on"]["db"]["condition"] == "service_healthy", "backup: attend db healthy")

# --- Alertes (tache 10) : lancees par le planificateur, sans nouveau service ni docker.sock ---
sc = svcs["scheduler"]
sv = {v["target"]: v for v in sc["volumes"]}
check("alerts" not in svcs, "alertes: pas de service supplementaire (le planificateur les lance)")
check(sv["/var/lib/ah2-status"]["source"] == "backup_status" and sv["/var/lib/ah2-status"].get("read_only") is True,
      "scheduler: backup_status monte en lecture seule")
check(sv["/var/lib/ah2-alerts"]["source"] == "alerts_state" and not sv["/var/lib/ah2-alerts"].get("read_only"),
      "scheduler: volume alerts_state en ecriture (etat des alertes)")
check(sv["/run/alerts"].get("read_only") is True and sv["/run/alerts"]["type"] == "bind"
      and sv["/run/alerts"]["source"].replace(chr(92), "/").endswith("/alerts"),
      "scheduler: dossier deploy/alerts (reglages, destinataires) en lecture seule")
check(all(sv["/watch/" + n].get("read_only") is True for n in ("pgdata", "ps_storage", "backups")),
      "scheduler: volumes de donnees en lecture seule pour le controle disque")
check(not any("docker.sock" in str(v.get("source", "")) for s_ in svcs.values() for v in s_.get("volumes", []) or []),
      "aucun service ne monte docker.sock")
check(sc["environment"]["DOMAIN"] == envfile["DOMAIN"] and "/probes/liveness" in sc["environment"]["ALERT_PROBE_POWERSYNC"],
      "scheduler: DOMAIN et sonde PowerSync pour les alertes")
check("alerts_state" in vols, "volume alerts_state declare")
check("*/10 * * * * python -m deploy.alerts.run_checks" in open("deploy/scheduler/crontab", encoding="utf-8").read(),
      "crontab: ligne des alertes toutes les 10 minutes")

# --- Correctifs tache 4/5 ---
dep = svcs["caddy"]["depends_on"]
check(dep["api"]["condition"] == "service_started" and dep["powersync"]["condition"] == "service_started",
      "caddy: depends_on api/powersync en service_started")
check(svcs["api"]["depends_on"]["db"]["condition"] == "service_healthy"
      and svcs["api"]["depends_on"]["redis"]["condition"] == "service_healthy", "api: attend db et redis healthy")
import ipaddress
ipam = cfg["networks"]["ah2"]["ipam"]["config"][0]
check(ipam.get("ip_range") == "172.28.0.128/25", "reseau: ip_range 172.28.0.128/25")
check(ipaddress.ip_address("172.28.0.10") not in ipaddress.ip_network(ipam["ip_range"])
      and ipaddress.ip_network(ipam["ip_range"]).subnet_of(ipaddress.ip_network(ipam["subnet"])),
      "172.28.0.10 hors de ip_range, ip_range dans le sous-reseau")
check(svcs["api"]["environment"]["FORWARDED_ALLOW_IPS"] == "172.28.0.10", "FORWARDED_ALLOW_IPS = 172.28.0.10")
check(str(svcs["caddy"].get("sysctls", {}).get("net.ipv4.ip_unprivileged_port_start")) == "0", "caddy: sysctl ip_unprivileged_port_start=0")
check(svcs["caddy"]["healthcheck"]["test"][-1] == "wget -q -O /dev/null http://127.0.0.1:2019/config/ || exit 1",
      "caddy: sonde identique au HEALTHCHECK de Dockerfile.web")
check("wget -q -O /dev/null http://127.0.0.1:2019/config/ || exit 1" in open("deploy/Dockerfile.web", encoding="utf-8").read(),
      "Dockerfile.web: meme commande de sonde")
check(svcs["caddy"]["environment"]["HSTS_HEADER"] == "max-age=0", "caddy: HSTS_HEADER par defaut max-age=0 (pas d'HSTS)")
for name in ("db", "pg-storage"):
    check("pg_isready -h 127.0.0.1" in svcs[name]["healthcheck"]["test"][-1], "%s: pg_isready via TCP 127.0.0.1" % name)

# Toute ${VAR} du compose est definie dans .env.example (sauf celles avec valeur par defaut)
used = {}
for m in re.finditer(r"(?<!\$)\$\{([A-Z_0-9]+)(:[-?][^}]*)?\}", src):
    used.setdefault(m.group(1), []).append(m.group(2) or "")
missing = [v for v, forms in used.items() if v not in envfile and not all(f.startswith(":-") for f in forms)]
check(not missing, "toutes les ${VAR} sans defaut sont dans .env.example (manquantes: %s)" % missing)
critical = ["ACME_EMAIL", "DOMAIN", "JWT_SECRET", "POSTGRES_PASSWORD", "POWERSYNC_REPL_PASSWORD", "REDIS_PASSWORD",
            "PG_STORAGE_PASSWORD", "PS_ADMIN_TOKEN", "GHCR_OWNER", "IMAGE_TAG"]
check(all(any(f.startswith(":?") for f in used.get(v, [])) for v in critical) and
      all(all(f.startswith(":?") for f in used[v]) for v in critical),
      "variables critiques exigees par ${VAR:?...} a chaque usage")

# Sources de montage
base = os.path.dirname(COMPOSE)
for name, s in svcs.items():
    for v in s.get("volumes", []) or []:
        # deploy/secrets/ et le depot de sauvegarde sont propres au serveur (absents du depot git)
        if v.get("type") == "bind" and not any(k in v["source"].replace(chr(92), "/") for k in ("/secrets/", "ah2-backups")):
            check(os.path.exists(v["source"]) or os.path.exists(os.path.join(base, v["source"])),
                  "%s: source de montage existe (%s)" % (name, v["source"]))

# Derivation de PS_APP_HS256_SECRET : meme resultat que la recette independante (openssl|tr)
import subprocess
sample = "sample/secret+with=odd/chars?>~" + "x" * 20
b64 = subprocess.run(["openssl", "base64", "-A"], input=sample, capture_output=True, text=True).stdout
recipe = b64.translate(str.maketrans("+/", "-_")).replace("=", "")  # = tr '+/' '-_' | tr -d '='
jscmd = re.search(r"\$\(node -e '([^']*)'\)", ep).group(1)
img = "journeyapps/powersync-service:latest"
have = subprocess.run(["docker", "image", "inspect", img], capture_output=True).returncode == 0
if have:
    r = subprocess.run(["docker", "run", "--rm", "--pull", "never", "--entrypoint", "node", "-e", "JWT_SECRET=" + sample,
                        img, "-e", jscmd], capture_output=True, text=True,
                       env=dict(os.environ, MSYS_NO_PATHCONV="1"))
    check(r.returncode == 0 and r.stdout == recipe and recipe != "", "base64url(JWT_SECRET) par node == recette openssl|tr")
else:
    check(False, "image powersync locale absente: derivation non verifiee")

# ACME_EMAIL vide => config echoue
r = subprocess.run(["docker", "compose", "--env-file", sys.argv[3], "-f", COMPOSE_PATH, "config", "-q"],
                   env=dict(os.environ, ACME_EMAIL=""), capture_output=True, text=True)
check(r.returncode != 0 and "ACME_EMAIL" in r.stderr, "ACME_EMAIL vide fait echouer docker compose config")

if fails:
    print("\n%d verification(s) en echec" % len(fails))
    sys.exit(1)
print("\nTOUT EST OK")
PYEOF
