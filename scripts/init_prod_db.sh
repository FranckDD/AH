#!/usr/bin/env bash
# Initialise une base de production NEUVE : schema, roles applicatifs, puis "alembic stamp head".
#
#   DATABASE_URL=postgresql://user:pass@host:5432/base scripts/init_prod_db.sh
#
# Les caracteres speciaux du mot de passe de DATABASE_URL doivent etre encodes en pourcentage
# (@ = %40, / = %2F, : = %3A, # = %23, ? = %3F, % = %25), sinon psql et le masquage echouent.
#
# Sur le serveur (depuis la pile docker compose, l'image api contient ci/, alembic/ et le
# script ; psql doit y etre present, voir deploy/Dockerfile.api) :
#   docker compose -f deploy/docker-compose.prod.yml exec api scripts/init_prod_db.sh
#
# Securite : s'arrete (code 2) si la base contient deja un objet dans le schema public ;
# n'affiche jamais le mot de passe de DATABASE_URL. Le role app_medical n'est pas cree ici
# (c'est deploy/postgres/init/01-roles.sh qui le fait au premier demarrage de Postgres).
# Jamais "alembic upgrade" sur une base vide : le schema vient de ci/schema_only.sql.
set -euo pipefail
export PSQL_PAGER=cat PAGER=cat  # pas de pagineur interactif (Windows: "more")

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

mask() { sed -E 's#(://[^:/@]*):[^@]*@#\1:***@#g'; }
die() { echo "ERREUR: $1" | mask >&2; exit "${2:-1}"; }

[ -n "${DATABASE_URL:-}" ] || die "DATABASE_URL n'est pas definie."
command -v psql >/dev/null 2>&1 || die "psql est introuvable (installer postgresql-client dans l'image api ou lancer depuis l'hote)."
[ -f ci/schema_only.sql ] && [ -f ci/seed_application_roles.sql ] || die "ci/schema_only.sql ou ci/seed_application_roles.sql manquant."

# psql n'accepte pas le suffixe de pilote SQLAlchemy (postgresql+psycopg2://).
PSQL_URL="$(printf '%s' "$DATABASE_URL" | sed -E 's#^postgres(ql)?\+[a-z0-9_]+://#postgresql://#')"
echo "Base cible : $(printf '%s' "$PSQL_URL" | mask)"

psql_q() { psql "$PSQL_URL" -X -P pager=off -v ON_ERROR_STOP=1 -At "$@"; }

psql_q -c "select 1" >/dev/null || die "connexion a la base impossible."

existing="$(psql_q -c "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind in ('r','p','v','m','f','S')")"
if [ "$existing" != "0" ]; then
  die "la base contient deja $existing objet(s) dans le schema public : rien n'a ete modifie. Utiliser une base vide." 2
fi

STARTED=0
recovery() {
  rc=$?
  if [ "$rc" -ne 0 ] && [ "$STARTED" = "1" ]; then
    {
      echo "ERREUR: echec apres le debut de la creation du schema (code $rc). La base est peut-etre"
      echo "partiellement initialisee et ce script refusera de la relancer (code 2)."
      echo "Recuperation, sur une base JETABLE/neuve uniquement (efface TOUT le schema public) :"
      echo "  psql \"\$DATABASE_URL\" -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
      echo "puis relancer scripts/init_prod_db.sh. Ou recreer la base vide."
    } >&2
  fi
  exit "$rc"
}
trap recovery EXIT

echo "1/3 schema (ci/schema_only.sql)"
STARTED=1
psql "$PSQL_URL" -X -P pager=off -q -v ON_ERROR_STOP=1 -f ci/schema_only.sql >/dev/null
echo "2/3 roles applicatifs (ci/seed_application_roles.sql)"
psql "$PSQL_URL" -X -P pager=off -q -v ON_ERROR_STOP=1 -f ci/seed_application_roles.sql >/dev/null
echo "3/3 alembic stamp head"
python -m alembic stamp head 2>&1 | mask

tables="$(psql_q -c "select count(*) from information_schema.tables where table_schema='public' and table_type='BASE TABLE'")"
roles="$(psql_q -c "select count(*) from public.application_roles")"
current="$(psql_q -c "select version_num from public.alembic_version")"
echo "----- Resume -----"
echo "Tables (schema public) : $tables"
echo "alembic_version        : $current"
echo "Roles applicatifs      : $roles"
echo "Base initialisee. Etape suivante : scripts/create_first_admin.py, puis scripts/import_reference_data.py."
