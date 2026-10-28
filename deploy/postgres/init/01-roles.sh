#!/bin/sh
# Compatible POSIX sh : l'entrypoint postgres SOURCE (".") les .sh non executables,
# donc pas de "set -o pipefail", pas de bashisme, et rien qui modifie le shell appelant.
# (Au commit : git update-index --chmod=+x deploy/postgres/init/01-roles.sh)
# Execute UNE fois par l'image postgres, a la creation du volume pgdata
# (/docker-entrypoint-initdb.d), en superutilisateur. Idempotent quand meme.
#  - app_medical : role (sans connexion) que ci/schema_only.sql attend
#    (la CI fait "CREATE ROLE app_medical;" avant de charger le schema).
#  - powersync_repl : role de replication logique de PowerSync, lecture seule.
# Le schema lui-meme est charge plus tard par scripts/init_prod_db.sh.
if [ -z "${POWERSYNC_REPL_PASSWORD:-}" ]; then
  echo "POWERSYNC_REPL_PASSWORD manquant" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v repl_pw="$POWERSYNC_REPL_PASSWORD" -v app_user="$POSTGRES_USER" <<'SQL'
SELECT 'CREATE ROLE app_medical NOLOGIN'
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_medical') \gexec

SELECT format('CREATE ROLE powersync_repl REPLICATION LOGIN PASSWORD %L', :'repl_pw')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'powersync_repl') \gexec
SELECT format('ALTER ROLE powersync_repl REPLICATION LOGIN PASSWORD %L', :'repl_pw') \gexec

SELECT format('GRANT CONNECT ON DATABASE %I TO powersync_repl', current_database()) \gexec
GRANT USAGE ON SCHEMA public TO powersync_repl;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO powersync_repl;
-- Tables creees plus tard (migrations alembic, executees par le role applicatif)
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT ON TABLES TO powersync_repl', :'app_user') \gexec
SQL
