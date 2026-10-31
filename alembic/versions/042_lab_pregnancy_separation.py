# alembic/versions/042_lab_pregnancy_separation.py
"""grossesse du laboratoire : colonne separee pour l'externe et statut a la reception

lab_results.external_pregnancy_info jsonb : donnees de grossesse d'un patient EXTERNE (statut, DPA, numero de
    suivi, SA). Aucun flux PowerSync ne selectionne cette colonne, alors que external_patient_info est livre
    par le flux lab_active_results : les cles de grossesse en sont donc sorties (migration des donnees).
lab_results.pregnancy_status_at_result text : statut de grossesse AU MOMENT de la reception (enceinte,
    non_enceinte, inconnu). Le rapport de subvention s'appuie sur ce cliche, jamais sur le statut actuel.
    Les lignes existantes restent a NULL (sauf externes dont le statut vient d'etre deplace) ; un resultat
    portant une SA compte quand meme comme grossesse.

Idempotent ; le retour arriere remet les cles dans external_patient_info.

Revision ID: 042_lab_pregnancy_separation
Revises: 041_lab_catalogue_extended
Create Date: 2026-10-31

"""
import json

import sqlalchemy as sa
from alembic import op

revision = '042_lab_pregnancy_separation'
down_revision = '041_lab_catalogue_extended'
branch_labels = None
depends_on = None

_CANON = ("pregnancy_status", "expected_delivery_date", "pregnancy_program_number", "gestational_age_weeks")
_EXACT = {"pregnancystatus", "expecteddeliverydate", "pregnancyprogramnumber", "gestationalageweeks",
          "grossesse", "enceinte", "dpa"}
_PREFIXES = ("pregnancy", "gestational", "grossesse", "enceinte")
_STATUSES = ("enceinte", "non_enceinte", "inconnu")


def _is_pregnancy_key(key):
    n = "".join(ch for ch in str(key).lower() if ch not in " _-\t")
    return n in _EXACT or n.startswith(_PREFIXES)


def upgrade():
    op.execute("ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS external_pregnancy_info jsonb")
    op.execute("ALTER TABLE public.lab_results ADD COLUMN IF NOT EXISTS pregnancy_status_at_result text")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_lab_results_pregnancy_status_at_result') THEN
                ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_pregnancy_status_at_result
                    CHECK (pregnancy_status_at_result IS NULL
                           OR pregnancy_status_at_result IN ('enceinte', 'non_enceinte', 'inconnu'));
            END IF;
        END $$
    """)
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT result_id, external_patient_info::text, external_pregnancy_info::text "
        "FROM public.lab_results WHERE external_patient_info IS NOT NULL"
    )).fetchall()
    for result_id, info_txt, preg_txt in rows:
        try:
            info = json.loads(info_txt)
        except ValueError:
            continue
        if not isinstance(info, dict):
            continue
        moved = {k: v for k, v in info.items() if _is_pregnancy_key(k)}
        if not moved:
            continue
        kept = {k: v for k, v in info.items() if k not in moved}
        try:
            existing = json.loads(preg_txt) if preg_txt else {}
        except ValueError:
            existing = {}
        if not isinstance(existing, dict):
            existing = {}
        merged = {**moved, **existing}
        status = moved.get("pregnancy_status")
        bind.execute(
            sa.text(
                "UPDATE public.lab_results SET external_patient_info = CAST(:kept AS jsonb), "
                "external_pregnancy_info = CAST(:moved AS jsonb), "
                "pregnancy_status_at_result = COALESCE(pregnancy_status_at_result, :status) "
                "WHERE result_id = :rid"
            ),
            {"kept": json.dumps(kept), "moved": json.dumps(merged), "rid": result_id,
             "status": status if status in _STATUSES else None},
        )


def downgrade():
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT result_id, external_patient_info::text, external_pregnancy_info::text "
        "FROM public.lab_results WHERE external_pregnancy_info IS NOT NULL"
    )).fetchall()
    for result_id, info_txt, preg_txt in rows:
        try:
            preg = json.loads(preg_txt)
            info = json.loads(info_txt) if info_txt else {}
        except ValueError:
            continue
        if not isinstance(preg, dict) or not preg:
            continue
        if not isinstance(info, dict):
            info = {}
        bind.execute(
            sa.text("UPDATE public.lab_results SET external_patient_info = CAST(:info AS jsonb) WHERE result_id = :rid"),
            {"info": json.dumps({**info, **preg}), "rid": result_id},
        )
    op.execute("ALTER TABLE public.lab_results DROP CONSTRAINT IF EXISTS ck_lab_results_pregnancy_status_at_result")
    op.execute("ALTER TABLE public.lab_results DROP COLUMN IF EXISTS pregnancy_status_at_result")
    op.execute("ALTER TABLE public.lab_results DROP COLUMN IF EXISTS external_pregnancy_info")
