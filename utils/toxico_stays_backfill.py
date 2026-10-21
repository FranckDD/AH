"""SQL de remplissage des sejours toxico pour les dossiers existants (migration 022).

Idempotent : un dossier qui a deja un sejour n'en recoit pas un second, et seules
les lignes sans stay_id sont rattachees au sejour 1.
"""

INSERT_FIRST_STAYS_SQL = """
INSERT INTO public.toxico_stays
    (dossier_id, stay_number, admission_date, psychologist_id, substance,
     discharge_date, discharge_reason, discharge_note, created_at)
SELECT d.id, 1, d.admission_date, d.psychologist_id, d.substance,
       CASE WHEN d.is_active THEN NULL
            ELSE GREATEST(d.admission_date,
                         COALESCE(d.updated_at::date, d.created_at::date, d.admission_date)) END,
       CASE WHEN d.is_active THEN NULL ELSE 'autre' END,
       CASE WHEN d.is_active THEN NULL
            ELSE 'Sortie antérieure au suivi des motifs' END,
       COALESCE(d.created_at, now())
FROM public.toxico_dossiers d
WHERE NOT EXISTS (SELECT 1 FROM public.toxico_stays s WHERE s.dossier_id = d.id)
"""

LINK_PHASE_HISTORY_SQL = """
UPDATE public.toxico_phase_history ph
SET stay_id = s.id
FROM public.toxico_stays s
WHERE s.dossier_id = ph.dossier_id AND s.stay_number = 1 AND ph.stay_id IS NULL
"""

LINK_EVALUATIONS_SQL = """
UPDATE public.toxico_evaluations ev
SET stay_id = s.id
FROM public.toxico_stays s
WHERE s.dossier_id = ev.dossier_id AND s.stay_number = 1 AND ev.stay_id IS NULL
"""

BACKFILL_STATEMENTS = (INSERT_FIRST_STAYS_SQL, LINK_PHASE_HISTORY_SQL, LINK_EVALUATIONS_SQL)
