--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: consultation_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.consultation_type AS ENUM (
    'medical',
    'spirituel'
);


--
-- Name: motif_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.motif_enum AS ENUM (
    'consultation',
    'rendez-vous',
    'suivi_prenatal',
    'hospitalisation',
    'urgence',
    'gratuite'
);


--
-- Name: prescription_spirituel; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.prescription_spirituel AS ENUM (
    'miel',
    'message',
    'prieres'
);


--
-- Name: role_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.role_enum AS ENUM (
    'admin',
    'personnel_medical',
    'medecin',
    'infirmier',
    'secretaire',
    'laborantin',
    'pharmacien'
);


--
-- Name: type_sexe; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.type_sexe AS ENUM (
    'M',
    'F'
);


--
-- Name: check_technician_role(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_technician_role(p_technician_id integer) RETURNS boolean
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    IF p_technician_id IS NULL THEN
        RETURN TRUE;
    END IF;
    
    RETURN EXISTS (
        SELECT 1 FROM users 
        WHERE user_id = p_technician_id 
        AND postgres_role = 'app_laborantin'
    );
END;
$$;


--
-- Name: create_appointment(integer, integer, timestamp without time zone, text); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_appointment(IN p_patient_id integer, IN p_doctor_id integer, IN p_appointment_date timestamp without time zone, IN p_reason text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Seul le personnel médical peut créer un rendez-vous.';
    END IF;

    INSERT INTO appointments (patient_id, doctor_id, appointment_date, reason)
    VALUES (p_patient_id, p_doctor_id, p_appointment_date, p_reason);

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE APPOINTMENT', p_patient_id);
END;
$$;


--
-- Name: create_lab_result(integer, character varying, jsonb, integer, text); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_lab_result(IN p_patient_id integer, IN p_test_type character varying, IN p_result_value jsonb, IN p_prescribed_by integer, IN p_note text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO lab_results (
        patient_id, test_type, result_value,
        prescribed_by, note
    ) VALUES (
        p_patient_id, p_test_type, p_result_value,
        p_prescribed_by, p_note
    );

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE LAB RESULT', p_patient_id);
END;
$$;


--
-- Name: create_medical_record(integer, timestamp without time zone, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text, character varying, integer, character varying, integer, character varying, integer); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_medical_record(IN p_patient_id integer, IN p_consultation_date timestamp without time zone, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text, IN p_motif_code character varying, IN p_created_by integer DEFAULT NULL::integer, IN p_created_by_name character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying, IN p_appointment_id integer DEFAULT NULL::integer)
    LANGUAGE plpgsql
    AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name, appointment_id
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name, p_appointment_id
            );
        END;
        $$;


--
-- Name: create_medical_record(integer, timestamp without time zone, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text, character varying, integer, character varying, integer, character varying, integer, uuid); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_medical_record(IN p_patient_id integer, IN p_consultation_date timestamp without time zone, IN p_marital_status character varying, IN p_bp character varying, IN p_temperature numeric, IN p_weight numeric, IN p_height numeric, IN p_medical_history text, IN p_allergies text, IN p_symptoms text, IN p_diagnosis text, IN p_treatment text, IN p_severity character varying, IN p_notes text, IN p_motif_code character varying, IN p_created_by integer DEFAULT NULL::integer, IN p_created_by_name character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying, IN p_appointment_id integer DEFAULT NULL::integer, IN p_uuid uuid DEFAULT NULL::uuid)
    LANGUAGE plpgsql
    AS $$
        BEGIN
            INSERT INTO public.medical_records (
                patient_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis,
                treatment, severity, notes, motif_code, created_by, created_by_name,
                last_updated_by, last_updated_by_name, appointment_id, uuid
            ) VALUES (
                p_patient_id, p_consultation_date, p_marital_status, p_bp, p_temperature,
                p_weight, p_height, p_medical_history, p_allergies, p_symptoms, p_diagnosis,
                p_treatment, p_severity, p_notes, p_motif_code, p_created_by, p_created_by_name,
                p_last_updated_by, p_last_updated_by_name, p_appointment_id,
                COALESCE(p_uuid, gen_random_uuid())
            );
        END;
        $$;


--
-- Name: create_metier_profile(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_metier_profile() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
          role_nom TEXT;
        BEGIN
          SELECT ar.role_name
            INTO role_nom
            FROM public.application_roles ar
           WHERE ar.role_id = NEW.role_id;

          IF role_nom = 'medecin' THEN
            INSERT INTO public.doctor(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'nurse' THEN
            INSERT INTO public.nurse(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'secretaire' THEN
            INSERT INTO public.secretaire(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'admin' THEN
            INSERT INTO public.admin(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          ELSIF role_nom = 'laborantin' THEN
            INSERT INTO public.laborantin(user_id) VALUES (NEW.user_id) ON CONFLICT (user_id) DO NOTHING;
          END IF;

          RETURN NEW;
        END;
        $$;


--
-- Name: create_patient(character varying, character varying, character varying, date, character varying, character varying, text, character varying, character varying, character varying, character varying); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_patient(IN p_code_patient character varying, IN p_first_name character varying, IN p_last_name character varying, IN p_birth_date date, IN p_gender character varying, IN p_contact_phone character varying, IN p_residence text, IN p_national_id character varying DEFAULT NULL::character varying, IN p_assurance character varying DEFAULT NULL::character varying, IN p_father_name character varying DEFAULT NULL::character varying, IN p_mother_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Insertion du patient
    INSERT INTO patients (
        code_patient, first_name, last_name, birth_date, gender,
        national_id, contact_phone, assurance, residence,
        father_name, mother_name
    ) VALUES (
        p_code_patient, p_first_name, p_last_name, p_birth_date, p_gender,
        p_national_id, p_contact_phone, p_assurance, p_residence,
        p_father_name, p_mother_name
    );

    -- Insertion dans l'audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE PATIENT', currval('patients_patient_id_seq'));
END;
$$;


--
-- Name: create_patient(character varying, character varying, character varying, date, character varying, character varying, text, character varying, character varying, character varying, character varying, integer, character varying, integer, character varying, boolean, boolean, boolean); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_patient(p_code_patient character varying, p_first_name character varying, p_last_name character varying, p_birth_date date, p_gender character varying, p_contact_phone character varying, p_residence text, p_national_id character varying DEFAULT NULL::character varying, p_assurance character varying DEFAULT NULL::character varying, p_father_name character varying DEFAULT NULL::character varying, p_mother_name character varying DEFAULT NULL::character varying, p_created_by integer DEFAULT NULL::integer, p_created_by_name character varying DEFAULT NULL::character varying, p_last_updated_by integer DEFAULT NULL::integer, p_last_updated_by_name character varying DEFAULT NULL::character varying, p_is_clinical boolean DEFAULT false, p_is_toxicology boolean DEFAULT false, p_is_spiritual boolean DEFAULT false) RETURNS TABLE(new_patient_id integer, new_patient_code character varying)
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_new_id INT;
            v_final_code VARCHAR;
            v_seq_val INT;
        BEGIN
            v_seq_val := nextval('patients_patient_id_seq');
            v_final_code := p_code_patient;

            INSERT INTO public.patients (
                patient_id,
                code_patient, first_name, last_name, birth_date, gender,
                national_id, contact_phone, assurance, residence,
                father_name, mother_name,
                created_at, created_by, created_by_name,
                last_updated_at, last_updated_by, last_updated_by_name,
                is_clinical, is_toxicology, is_spiritual,
                is_deleted, deleted_at, deleted_by
            ) VALUES (
                v_seq_val,
                v_final_code, p_first_name, p_last_name, p_birth_date, p_gender,
                p_national_id, p_contact_phone, p_assurance, p_residence,
                p_father_name, p_mother_name,
                now(), p_created_by, p_created_by_name,
                now(), p_last_updated_by, p_last_updated_by_name,
                p_is_clinical, p_is_toxicology, p_is_spiritual,
                false, NULL, NULL
            )
            RETURNING patient_id INTO v_new_id;

            RETURN QUERY SELECT v_new_id, v_final_code;
        END;
        $$;


--
-- Name: create_prescription(integer, character varying, character varying, character varying, character varying, integer, date, date, text); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_prescription(IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Vérification de l'existence du patient
    IF NOT EXISTS (
        SELECT 1 FROM patients WHERE patient_id = p_patient_id
    ) THEN
        RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', p_patient_id;
    END IF;

    -- Vérification de l'existence du dossier médical (si fourni)
    IF p_medical_record_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id
        ) THEN
            RAISE EXCEPTION 'Aucun dossier médical avec l''ID % n''existe.', p_medical_record_id;
        END IF;
    END IF;

    -- Vérification des dates
    IF p_end_date IS NOT NULL AND p_end_date < p_start_date THEN
        RAISE EXCEPTION 'La date de fin (%) ne peut pas être antérieure à la date de début (%)',
            p_end_date, p_start_date;
    END IF;

    -- Insertion de l'ordonnance
    INSERT INTO prescriptions (
        patient_id, medical_record_id, medication,
        dosage, frequency, duration, start_date,
        end_date, notes
    ) VALUES (
        p_patient_id, p_medical_record_id, p_medication,
        p_dosage, p_frequency, p_duration, p_start_date,
        p_end_date, p_notes
    );

    -- Insertion dans l'audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE PRESCRIPTION', p_patient_id);
END;
$$;


--
-- Name: create_prescription(integer, character varying, character varying, character varying, character varying, integer, date, date, text, integer, character varying); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_prescription(IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text, IN p_prescribed_by integer DEFAULT NULL::integer, IN p_prescribed_by_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM patients WHERE patient_id = p_patient_id) THEN
                RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', p_patient_id;
            END IF;

            IF p_medical_record_id IS NOT NULL THEN
                IF NOT EXISTS (SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id) THEN
                    RAISE EXCEPTION 'Aucun dossier medical avec l''ID % n''existe.', p_medical_record_id;
                END IF;
            END IF;

            IF p_end_date IS NOT NULL AND p_end_date < p_start_date THEN
                RAISE EXCEPTION 'La date de fin ne peut pas etre anterieure a la date de debut';
            END IF;

            INSERT INTO public.prescriptions (
                patient_id,
                medical_record_id,
                medication,
                dosage,
                frequency,
                duration,
                start_date,
                end_date,
                notes,
                prescribed_by,
                prescribed_by_name
            ) VALUES (
                p_patient_id,
                p_medical_record_id,
                p_medication,
                p_dosage,
                p_frequency,
                p_duration,
                p_start_date,
                p_end_date,
                p_notes,
                p_prescribed_by,
                p_prescribed_by_name
            );
        END;
        $$;


--
-- Name: create_spiritual_consultation(integer, character varying, text, timestamp without time zone); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_spiritual_consultation(IN p_patient_id integer, IN p_prescription character varying, IN p_notes text DEFAULT NULL::text, IN p_consultation_date timestamp without time zone DEFAULT NULL::timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_prescription_valid BOOLEAN;
BEGIN
    -- Vérification du rôle (secretaire ou medical)
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) NOT IN ('app_secretaire', 'app_medical') THEN
        RAISE EXCEPTION 'Accès refusé. Seuls le secrétariat et le personnel médical peuvent créer des consultations spirituelles.';
    END IF;

    -- Validation du type de prescription
    SELECT p_prescription IN ('Hony', 'Massage', 'Prayer') INTO v_prescription_valid;
    IF NOT v_prescription_valid THEN
        RAISE EXCEPTION 'Prescription invalide. Doit être Hony, Massage ou Prayer';
    END IF;

    -- Vérification de l'existence du patient
    IF NOT EXISTS (SELECT 1 FROM patients WHERE patient_id = p_patient_id) THEN
        RAISE EXCEPTION 'Patient ID % non trouvé', p_patient_id;
    END IF;

    -- Insertion avec gestion des valeurs par défaut
    INSERT INTO consultation_spirituel (
        patient_id,
        prescription,
        consultation_date,
        created_by,
        notes
    ) VALUES (
        p_patient_id,
        p_prescription,
        COALESCE(p_consultation_date, NOW()),
        current_user_id(),
        p_notes
    );

    -- Audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'CREATE SPIRITUAL CONSULTATION', p_patient_id);
END;
$$;


--
-- Name: create_user(character varying, text, character varying, character varying, integer, integer); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.create_user(IN p_username character varying, IN p_password_hash text, IN p_full_name character varying, IN p_postgres_role character varying, IN p_specialty_id integer DEFAULT NULL::integer, IN p_role_id integer DEFAULT NULL::integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT role_name FROM application_roles WHERE role_id = 
        (SELECT role_id FROM users WHERE user_id = current_user_id())) != 'admin' THEN
        RAISE EXCEPTION 'Seul un administrateur peut créer des utilisateurs';
    END IF;

    INSERT INTO users (
        username, password_hash, full_name,
        postgres_role, specialty_id, role_id
    ) VALUES (
        p_username, p_password_hash, p_full_name,
        p_postgres_role, p_specialty_id, p_role_id
    );
END;
$$;


--
-- Name: create_view_for_motif(character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_view_for_motif(motif_in character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    view_name VARCHAR;
BEGIN
    view_name := 'vue_' || motif_in;
    EXECUTE format(
      'CREATE OR REPLACE VIEW %I AS SELECT * FROM medical_records WHERE motif_code = %L',
      view_name, motif_in
    );
END;
$$;


--
-- Name: current_user_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.current_user_id() RETURNS integer
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
        DECLARE
          user_id INT;
        BEGIN
          SELECT u.user_id INTO user_id
          FROM users u
          WHERE u.username = current_user;

          RETURN user_id;
        END;
        $$;


--
-- Name: delete_appointment(integer); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.delete_appointment(IN p_appointment_id integer)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_patient_id INT;
BEGIN
    SELECT patient_id INTO v_patient_id FROM appointments WHERE appointment_id = p_appointment_id;
    
    DELETE FROM appointments WHERE appointment_id = p_appointment_id;

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'DELETE APPOINTMENT', v_patient_id);
END;
$$;


--
-- Name: delete_patient(integer, integer); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.delete_patient(IN p_patient_id integer, IN p_deleted_by integer)
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_user_name VARCHAR(100);
        BEGIN
            -- Get user name for audit trail
            SELECT username INTO v_user_name FROM public.users WHERE user_id = p_deleted_by;

            -- Soft delete the patient
            UPDATE public.patients
            SET is_deleted = true, deleted_by = p_deleted_by, deleted_at = NOW()
            WHERE patient_id = p_patient_id;

            -- Log the action to audit_user_actions using correct column name
            INSERT INTO public.audit_user_actions(user_id, resource_type, resource_id, action_performed, username)
            VALUES (p_deleted_by, 'Patient', p_patient_id, 'SOFT DELETE', COALESCE(v_user_name, 'Unknown'));
        END;
        $$;


--
-- Name: fix_lab_names(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fix_lab_names() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Mise à jour du nom du TECHNICIEN (seulement si l'ID est là)
    -- On utilise uniquement 'full_name' car 'first_name' n'existe pas
    IF NEW.technician_id IS NOT NULL THEN
        SELECT full_name INTO NEW.technician_name 
        FROM public.users 
        WHERE user_id = NEW.technician_id;
    END IF;

    -- Mise à jour du nom du CRÉATEUR (seulement si l'ID est là)
    IF NEW.created_by IS NOT NULL THEN
        SELECT full_name INTO NEW.created_by_name 
        FROM public.users 
        WHERE user_id = NEW.created_by;
    END IF;

    -- NOTE : On ne touche PAS à prescribed_by (on garde juste l'ID)
    
    RETURN NEW;
END;
$$;


--
-- Name: fn_caisse_protect_cancelled(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_caisse_protect_cancelled() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
          IF OLD.status = 'cancelled' THEN
            IF NEW.status <> 'active' THEN
              RAISE EXCEPTION 'Impossible de modifier une transaction annulee (ID=%).', OLD.transaction_id;
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$;


--
-- Name: log_user_action(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.log_user_action() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_user_id INTEGER;
    v_resource_id INTEGER;
    v_action_performed VARCHAR(50);
    v_old_values JSONB := NULL;
    v_new_values JSONB := NULL;
BEGIN
    -- 1. Récupération de l'ID de la ressource (Adapté selon la table)
    IF TG_TABLE_NAME = 'patients' THEN
        v_resource_id := COALESCE(NEW.patient_id, OLD.patient_id);
    ELSIF TG_TABLE_NAME = 'medical_records' THEN
        v_resource_id := COALESCE(NEW.record_id, OLD.record_id); -- Vérifiez si c'est record_id ou patient_id
    ELSIF TG_TABLE_NAME = 'prescriptions' THEN
        v_resource_id := COALESCE(NEW.prescription_id, OLD.prescription_id);
    ELSE
        -- Fallback générique si possible, sinon NULL
        v_resource_id := NULL;
    END IF;

    -- 2. Détermination de l'Action et des Valeurs
    IF TG_OP = 'INSERT' THEN
        v_action_performed := 'CREATE';
        v_new_values := to_jsonb(NEW);
        -- Pour un insert, l'utilisateur est le créateur
        -- On tente de récupérer created_by si la colonne existe dans la table cible
        BEGIN
            v_user_id := NEW.created_by;
        EXCEPTION WHEN OTHERS THEN
            v_user_id := NULL; -- Si la colonne n'existe pas
        END;

    ELSIF TG_OP = 'UPDATE' THEN
        v_new_values := to_jsonb(NEW);
        v_old_values := to_jsonb(OLD);
        
        -- Détection du Soft Delete (Si on passe de is_deleted=false à true)
        -- On utilise to_jsonb pour vérifier l'existence de la clé sans erreur
        IF (v_new_values ? 'is_deleted') AND (CAST(v_new_values->>'is_deleted' AS BOOLEAN) = true) AND (CAST(v_old_values->>'is_deleted' AS BOOLEAN) = false) THEN
            v_action_performed := 'SOFT_DELETE';
            -- Pour un soft delete, l'utilisateur est celui qui a supprimé
            BEGIN
                v_user_id := NEW.deleted_by;
            EXCEPTION WHEN OTHERS THEN v_user_id := NULL; END;
        ELSE
            v_action_performed := 'UPDATE';
            -- Pour un update standard, l'utilisateur est celui qui a mis à jour
            BEGIN
                v_user_id := NEW.last_updated_by;
            EXCEPTION WHEN OTHERS THEN v_user_id := NULL; END;
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        v_action_performed := 'HARD_DELETE';
        v_old_values := to_jsonb(OLD);
        -- Difficile de savoir qui a fait un DELETE physique via le trigger seul
        -- On essaie de prendre l'ancien updater ou on laisse NULL
        v_user_id := NULL; 
    END IF;

    -- 3. Sécurité : Si v_user_id est NULL (ex: action via SQL direct), on essaie de trouver l'ID via le current_user postgres
    -- Cela évite l'erreur de contrainte NOT NULL si votre application n'a pas rempli created_by/updated_by
    IF v_user_id IS NULL THEN
        SELECT user_id INTO v_user_id FROM public.users WHERE username = current_user LIMIT 1;
        
        -- Si toujours NULL (cas rare ou utilisateur système non mappé), on met une valeur par défaut ou on lève une alerte.
        -- Pour l'instant, on suppose que l'appli envoie toujours un user valide.
    END IF;

    -- 4. Insertion dans la table d'audit (Correspondance exacte des colonnes)
    INSERT INTO public.audit_user_actions (
        user_id,
        resource_type,
        resource_id,
        action_performed,
        old_values,
        new_values,
        ip_address -- Optionnel: peut être récupéré via inet_client_addr() si dispo
    ) VALUES (
        v_user_id,              -- Doit exister dans la table users !
        TG_TABLE_NAME,          -- resource_type
        v_resource_id,          -- resource_id
        v_action_performed,     -- action_performed
        v_old_values,           -- old_values (JSONB)
        v_new_values,           -- new_values (JSONB)
        inet_client_addr()::text -- Récupère l'IP du client si possible
    );

    RETURN NEW;
END;
$$;


--
-- Name: refresh_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.refresh_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$;


--
-- Name: set_default_specialty(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_default_specialty() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            IF NEW.postgres_role = 'app_medical' AND NEW.specialty_id IS NULL THEN
                NEW.specialty_id := (SELECT specialty_id FROM medical_specialties WHERE name = 'Generaliste');
            END IF;
            RETURN NEW;
        END;
        $$;


--
-- Name: track_patient_changes(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.track_patient_changes() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
          IF TG_OP = 'INSERT' THEN
            IF NEW.created_by IS NULL THEN
               NEW.created_by := current_user_id();
            END IF;
            NEW.last_updated_by := current_user_id();
          ELSIF TG_OP = 'UPDATE' THEN
            NEW.last_updated_by := current_user_id();
          END IF;
          RETURN NEW;
        END;
        $$;


--
-- Name: update_appointment(integer, integer, timestamp without time zone, integer, text, character varying, text); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_appointment(IN p_appointment_id integer, IN p_doctor_id integer DEFAULT NULL::integer, IN p_appointment_date timestamp without time zone DEFAULT NULL::timestamp without time zone, IN p_duration_min integer DEFAULT NULL::integer, IN p_reason text DEFAULT NULL::text, IN p_status character varying DEFAULT NULL::character varying, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Accès réservé au personnel médical';
    END IF;

    UPDATE appointments SET
        doctor_id = COALESCE(p_doctor_id, doctor_id),
        appointment_date = COALESCE(p_appointment_date, appointment_date),
        duration_min = COALESCE(p_duration_min, duration_min),
        reason = COALESCE(p_reason, reason),
        status = COALESCE(p_status, status),
        notes = COALESCE(p_notes, notes)
    WHERE appointment_id = p_appointment_id;

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE APPOINTMENT', (SELECT patient_id FROM appointments WHERE appointment_id = p_appointment_id));
END;
$$;


--
-- Name: update_medical_record(integer, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_medical_record(IN p_record_id integer, IN p_marital_status character varying DEFAULT NULL::character varying, IN p_bp character varying DEFAULT NULL::character varying, IN p_temperature numeric DEFAULT NULL::numeric, IN p_weight numeric DEFAULT NULL::numeric, IN p_height numeric DEFAULT NULL::numeric, IN p_medical_history text DEFAULT NULL::text, IN p_allergies text DEFAULT NULL::text, IN p_symptoms text DEFAULT NULL::text, IN p_diagnosis text DEFAULT NULL::text, IN p_treatment text DEFAULT NULL::text, IN p_severity character varying DEFAULT NULL::character varying, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Accès réservé au personnel médical';
    END IF;

    UPDATE medical_records SET
        marital_status = COALESCE(p_marital_status, marital_status),
        bp = COALESCE(p_bp, bp),
        temperature = COALESCE(p_temperature, temperature),
        weight = COALESCE(p_weight, weight),
        height = COALESCE(p_height, height),
        medical_history = COALESCE(p_medical_history, medical_history),
        allergies = COALESCE(p_allergies, allergies),
        symptoms = COALESCE(p_symptoms, symptoms),
        diagnosis = COALESCE(p_diagnosis, diagnosis),
        treatment = COALESCE(p_treatment, treatment),
        severity = COALESCE(p_severity, severity),
        notes = COALESCE(p_notes, notes),
        last_updated_by = current_user_id()
    WHERE record_id = p_record_id;

    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE MEDICAL RECORD', (SELECT patient_id FROM medical_records WHERE record_id = p_record_id));
END;
$$;


--
-- Name: update_medical_record(integer, character varying, character varying, numeric, numeric, numeric, text, text, text, text, text, character varying, text, character varying, integer, character varying); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_medical_record(IN p_record_id integer, IN p_marital_status character varying DEFAULT NULL::character varying, IN p_bp character varying DEFAULT NULL::character varying, IN p_temperature numeric DEFAULT NULL::numeric, IN p_weight numeric DEFAULT NULL::numeric, IN p_height numeric DEFAULT NULL::numeric, IN p_medical_history text DEFAULT NULL::text, IN p_allergies text DEFAULT NULL::text, IN p_symptoms text DEFAULT NULL::text, IN p_diagnosis text DEFAULT NULL::text, IN p_treatment text DEFAULT NULL::text, IN p_severity character varying DEFAULT NULL::character varying, IN p_notes text DEFAULT NULL::text, IN p_motif_code character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Note: La vérification du rôle (current_user_id) peut être délicate si le contexte n'est pas set.
    -- Si vous gérez les permissions via l'app Python, vous pouvez commenter ce IF.
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id()) != 'app_medical' THEN
        RAISE EXCEPTION 'Accès réservé au personnel médical';
    END IF;

    UPDATE medical_records SET
        marital_status = COALESCE(p_marital_status, marital_status),
        bp = COALESCE(p_bp, bp),
        temperature = COALESCE(p_temperature, temperature),
        weight = COALESCE(p_weight, weight),
        height = COALESCE(p_height, height),
        medical_history = COALESCE(p_medical_history, medical_history),
        allergies = COALESCE(p_allergies, allergies),
        symptoms = COALESCE(p_symptoms, symptoms),
        diagnosis = COALESCE(p_diagnosis, diagnosis),
        treatment = COALESCE(p_treatment, treatment),
        severity = COALESCE(p_severity, severity),
        notes = COALESCE(p_notes, notes),
        motif_code = COALESCE(p_motif_code, motif_code),
        last_updated_by = p_last_updated_by,
        last_updated_by_name = p_last_updated_by_name
    WHERE record_id = p_record_id;

    -- L'audit est géré par Python (Controller)
END;
$$;


--
-- Name: update_patient(integer, character varying, character varying, date, character varying, character varying, character varying, character varying, text, character varying, character varying); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_patient(IN p_patient_id integer, IN p_first_name character varying DEFAULT NULL::character varying, IN p_last_name character varying DEFAULT NULL::character varying, IN p_birth_date date DEFAULT NULL::date, IN p_gender character varying DEFAULT NULL::character varying, IN p_national_id character varying DEFAULT NULL::character varying, IN p_contact_phone character varying DEFAULT NULL::character varying, IN p_assurance character varying DEFAULT NULL::character varying, IN p_residence text DEFAULT NULL::text, IN p_father_name character varying DEFAULT NULL::character varying, IN p_mother_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Vérification de rôle
    IF (SELECT postgres_role FROM users WHERE user_id = current_user_id())
       NOT IN ('app_secretaire', 'app_medical') THEN
        RAISE EXCEPTION 'Accès refusé. Rôle non autorisé.';
    END IF;

    -- Mise à jour des champs (seuls ceux non-NULL écrasent les existants)
    UPDATE patients
    SET
        first_name    = COALESCE(p_first_name, first_name),
        last_name     = COALESCE(p_last_name, last_name),
        birth_date    = COALESCE(p_birth_date, birth_date),
        gender        = COALESCE(p_gender, gender),
        national_id   = COALESCE(p_national_id, national_id),
        contact_phone = COALESCE(p_contact_phone, contact_phone),
        assurance     = COALESCE(p_assurance, assurance),
        residence     = COALESCE(p_residence, residence),
        father_name   = COALESCE(p_father_name, father_name),
        mother_name   = COALESCE(p_mother_name, mother_name)
    WHERE patient_id = p_patient_id;

    -- Audit
    INSERT INTO audit_user_actions(user_name, action, patient_id)
    VALUES (current_user, 'UPDATE PATIENT', p_patient_id);
END;
$$;


--
-- Name: update_patient(integer, character varying, character varying, date, character varying, character varying, character varying, character varying, text, character varying, character varying, integer, character varying, boolean, boolean, boolean); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_patient(IN p_patient_id integer, IN p_first_name character varying DEFAULT NULL::character varying, IN p_last_name character varying DEFAULT NULL::character varying, IN p_birth_date date DEFAULT NULL::date, IN p_gender character varying DEFAULT NULL::character varying, IN p_national_id character varying DEFAULT NULL::character varying, IN p_contact_phone character varying DEFAULT NULL::character varying, IN p_assurance character varying DEFAULT NULL::character varying, IN p_residence text DEFAULT NULL::text, IN p_father_name character varying DEFAULT NULL::character varying, IN p_mother_name character varying DEFAULT NULL::character varying, IN p_last_updated_by integer DEFAULT NULL::integer, IN p_last_updated_by_name character varying DEFAULT NULL::character varying, IN p_is_clinical boolean DEFAULT NULL::boolean, IN p_is_toxicology boolean DEFAULT NULL::boolean, IN p_is_spiritual boolean DEFAULT NULL::boolean)
    LANGUAGE plpgsql
    AS $$
        BEGIN
            UPDATE public.patients
            SET
                first_name          = COALESCE(p_first_name, first_name),
                last_name           = COALESCE(p_last_name, last_name),
                birth_date          = COALESCE(p_birth_date, birth_date),
                gender              = COALESCE(p_gender, gender),
                national_id         = COALESCE(p_national_id, national_id),
                contact_phone       = COALESCE(p_contact_phone, contact_phone),
                assurance           = COALESCE(p_assurance, assurance),
                residence           = COALESCE(p_residence, residence),
                father_name         = COALESCE(p_father_name, father_name),
                mother_name         = COALESCE(p_mother_name, mother_name),
                last_updated_at     = now(),
                last_updated_by     = p_last_updated_by,
                last_updated_by_name = p_last_updated_by_name,
                is_clinical         = COALESCE(p_is_clinical, is_clinical),
                is_toxicology       = COALESCE(p_is_toxicology, is_toxicology),
                is_spiritual        = COALESCE(p_is_spiritual, is_spiritual)
            WHERE patient_id = p_patient_id;
        END;
        $$;


--
-- Name: update_pharmacy_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_pharmacy_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$;


--
-- Name: update_prescribed_names(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_prescribed_names() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
          IF NEW.prescribed_by IS NOT NULL THEN
            SELECT username INTO NEW.prescribed_by_name
              FROM users WHERE user_id = NEW.prescribed_by;
          END IF;
          RETURN NEW;
        END;
        $$;


--
-- Name: update_prescription(integer, integer, character varying, character varying, character varying, character varying, integer, date, date, text); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_prescription(IN p_prescription_id integer, IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Vérifier que la prescription existe
    IF NOT EXISTS (
        SELECT 1 FROM prescriptions WHERE prescription_id = p_prescription_id
    ) THEN
        RAISE EXCEPTION 'Aucune prescription avec l''ID % n''existe.', p_prescription_id;
    END IF;
    
    -- Vérifier l'existence du patient
    IF NOT EXISTS (
        SELECT 1 FROM patients WHERE patient_id = p_patient_id
    ) THEN
        RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', p_patient_id;
    END IF;

    -- Vérifier l'existence du dossier médical (si fourni)
    IF p_medical_record_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id
        ) THEN
            RAISE EXCEPTION 'Aucun dossier médical avec l''ID % n''existe.', p_medical_record_id;
        END IF;
    END IF;

    -- Vérification de la cohérence des dates
    IF p_end_date IS NOT NULL AND p_end_date < p_start_date THEN
        RAISE EXCEPTION 'La date de fin (%) ne peut pas être antérieure à la date de début (%)',
            p_end_date, p_start_date;
    END IF;

    -- Mise à jour de la prescription
    UPDATE prescriptions
    SET patient_id = p_patient_id,
        medical_record_id = p_medical_record_id,
        medication = p_medication,
        dosage = p_dosage,
        frequency = p_frequency,
        duration = p_duration,
        start_date = p_start_date,
        end_date = p_end_date,
        notes = p_notes
    WHERE prescription_id = p_prescription_id;

    -- Enregistrement dans l'audit
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE PRESCRIPTION', p_patient_id);
END;
$$;


--
-- Name: update_prescription(integer, integer, character varying, character varying, character varying, character varying, integer, date, date, text, integer, character varying); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_prescription(IN p_prescription_id integer, IN p_patient_id integer, IN p_medication character varying, IN p_dosage character varying, IN p_frequency character varying, IN p_duration character varying, IN p_medical_record_id integer DEFAULT NULL::integer, IN p_start_date date DEFAULT CURRENT_DATE, IN p_end_date date DEFAULT NULL::date, IN p_notes text DEFAULT NULL::text, IN p_prescribed_by integer DEFAULT NULL::integer, IN p_prescribed_by_name character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_patient_id  integer;
            v_start_date  date;
            v_end_date    date;
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM prescriptions WHERE prescription_id = p_prescription_id) THEN
                RAISE EXCEPTION 'Aucune prescription avec l''ID % n''existe.', p_prescription_id;
            END IF;

            SELECT COALESCE(p_patient_id, patient_id),
                   COALESCE(p_start_date, start_date),
                   COALESCE(p_end_date, end_date)
              INTO v_patient_id, v_start_date, v_end_date
              FROM prescriptions
             WHERE prescription_id = p_prescription_id;

            IF NOT EXISTS (SELECT 1 FROM patients WHERE patient_id = v_patient_id) THEN
                RAISE EXCEPTION 'Aucun patient avec l''ID % n''existe.', v_patient_id;
            END IF;

            IF p_medical_record_id IS NOT NULL THEN
                IF NOT EXISTS (SELECT 1 FROM medical_records WHERE record_id = p_medical_record_id) THEN
                    RAISE EXCEPTION 'Aucun dossier medical avec l''ID % n''existe.', p_medical_record_id;
                END IF;
            END IF;

            IF v_end_date IS NOT NULL AND v_end_date < v_start_date THEN
                RAISE EXCEPTION 'La date de fin ne peut pas etre anterieure a la date de debut';
            END IF;

            UPDATE public.prescriptions
               SET patient_id         = v_patient_id,
                   medical_record_id  = COALESCE(p_medical_record_id, medical_record_id),
                   medication         = COALESCE(p_medication, medication),
                   dosage             = COALESCE(p_dosage, dosage),
                   frequency          = COALESCE(p_frequency, frequency),
                   duration           = COALESCE(p_duration, duration),
                   start_date         = v_start_date,
                   end_date           = v_end_date,
                   notes              = COALESCE(p_notes, notes),
                   prescribed_by      = COALESCE(p_prescribed_by, prescribed_by),
                   prescribed_by_name = COALESCE(p_prescribed_by_name, prescribed_by_name)
             WHERE prescription_id = p_prescription_id;
        END;
        $$;


--
-- Name: update_user(integer, character varying, text, character varying, character varying, integer, integer, boolean); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_user(IN p_user_id integer, IN p_username character varying DEFAULT NULL::character varying, IN p_password_hash text DEFAULT NULL::text, IN p_full_name character varying DEFAULT NULL::character varying, IN p_postgres_role character varying DEFAULT NULL::character varying, IN p_specialty_id integer DEFAULT NULL::integer, IN p_role_id integer DEFAULT NULL::integer, IN p_is_active boolean DEFAULT NULL::boolean)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_current_user_id INT;
    v_current_user_role TEXT;
BEGIN
    -- Récupérer l'ID et le rôle de l'utilisateur courant
    v_current_user_id := current_user_id();  -- Supposée fonction existante
    SELECT ar.role_name INTO v_current_user_role
    FROM users u
    JOIN application_roles ar ON ar.role_id = u.role_id
    WHERE u.user_id = v_current_user_id;

    -- Cas 1 : Admin → peut tout faire
    IF v_current_user_role = 'admin' THEN
        UPDATE users SET
            username = COALESCE(p_username, username),
            password_hash = COALESCE(p_password_hash, password_hash),
            full_name = COALESCE(p_full_name, full_name),
            postgres_role = COALESCE(p_postgres_role, postgres_role),
            specialty_id = COALESCE(p_specialty_id, specialty_id),
            role_id = COALESCE(p_role_id, role_id),
            is_active = COALESCE(p_is_active, is_active)
        WHERE user_id = p_user_id;

    -- Cas 2 : Utilisateur standard → ne peut modifier que son propre compte, et certains champs seulement
    ELSIF v_current_user_id = p_user_id THEN
        UPDATE users SET
            username = COALESCE(p_username, username),
            password_hash = COALESCE(p_password_hash, password_hash),
            full_name = COALESCE(p_full_name, full_name),
            specialty_id = COALESCE(p_specialty_id, specialty_id)
        WHERE user_id = p_user_id;

    -- Cas 3 : Interdiction
    ELSE
        RAISE EXCEPTION 'Vous n''avez pas les droits pour modifier ce compte.';
    END IF;

    -- (Optionnel) Historique d'action
    INSERT INTO audit_user_actions (user_name, action, patient_id)
    VALUES (current_user, 'UPDATE USER', p_user_id);
END;
$$;


--
-- Name: update_user_names_cs(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_user_names_cs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Lors d'un INSERT, si created_by est renseigné, on remplit created_by_name
    IF TG_OP = 'INSERT' THEN
        IF NEW.created_by IS NOT NULL THEN
            NEW.created_by_name := (
                SELECT full_name
                FROM public.users
                WHERE user_id = NEW.created_by
            );
        END IF;
    END IF;

    -- Il n'existe pas de colonne last_updated_by dans consultation_spirituel, donc on ne la gère pas ici.

    RETURN NEW;
END;
$$;


--
-- Name: update_user_names_lab_results(integer); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.update_user_names_lab_results(IN p_lab_result_id integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Prescribed by -> prescribed_by_name
    UPDATE public.lab_results lr
    SET prescribed_by_name = sub.full_name
    FROM (
        SELECT user_id, COALESCE(full_name, concat_ws(' ', first_name, last_name)) AS full_name
        FROM public.users
    ) sub
    WHERE lr.prescribed_by = sub.user_id
      AND lr.lab_result_id = p_lab_result_id;

    -- Technician -> technician_name
    UPDATE public.lab_results lr
    SET technician_name = sub.full_name
    FROM (
        SELECT user_id, COALESCE(full_name, concat_ws(' ', first_name, last_name)) AS full_name
        FROM public.users
    ) sub
    WHERE lr.technician_id = sub.user_id
      AND lr.lab_result_id = p_lab_result_id;

    -- Ajouter d'autres colonnes (ex: filled_by) ici si nécessaire
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin (
    user_id integer NOT NULL,
    access_level smallint,
    last_login timestamp with time zone,
    permissions text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT admin_access_level_check CHECK (((access_level >= 1) AND (access_level <= 10)))
);


--
-- Name: admissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admissions (
    admission_id integer NOT NULL,
    patient_id integer NOT NULL,
    admission_date timestamp with time zone DEFAULT now(),
    discharge_date timestamp with time zone,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    current_phase integer DEFAULT 1,
    notes_admission text,
    created_by integer,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    CONSTRAINT admissions_current_phase_check CHECK (((current_phase >= 1) AND (current_phase <= 4)))
);


--
-- Name: admissions_admission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admissions_admission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admissions_admission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admissions_admission_id_seq OWNED BY public.admissions.admission_id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: application_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.application_roles (
    role_id integer NOT NULL,
    role_name character varying(50) NOT NULL
);


--
-- Name: application_roles_role_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.application_roles_role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: application_roles_role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.application_roles_role_id_seq OWNED BY public.application_roles.role_id;


--
-- Name: appointments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.appointments (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer,
    specialty character varying(100),
    appointment_date date NOT NULL,
    appointment_time time without time zone NOT NULL,
    reason text,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: appointments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.appointments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: appointments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.appointments_id_seq OWNED BY public.appointments.id;


--
-- Name: audit_access; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_access (
    access_id integer NOT NULL,
    user_id integer,
    "timestamp" timestamp with time zone DEFAULT now(),
    action_type character varying(50) NOT NULL,
    ip_address character varying(45),
    user_agent text,
    details text
);


--
-- Name: audit_access_access_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_access_access_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_access_access_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_access_access_id_seq OWNED BY public.audit_access.access_id;


--
-- Name: audit_access_old; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_access_old (
    log_id integer NOT NULL,
    user_role character varying(50) NOT NULL,
    patient_id integer,
    action_time timestamp without time zone DEFAULT now()
);


--
-- Name: audit_access_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_access_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_access_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_access_log_id_seq OWNED BY public.audit_access_old.log_id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    log_id integer NOT NULL,
    user_role character varying(50) NOT NULL,
    action text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now()
);


--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_log_id_seq OWNED BY public.audit_logs.log_id;


--
-- Name: audit_user_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_user_actions (
    action_id integer NOT NULL,
    user_id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    resource_type character varying(50) NOT NULL,
    resource_id integer,
    action_performed character varying(50) NOT NULL,
    old_values jsonb,
    new_values jsonb,
    ip_address character varying(45),
    username character varying(100)
);


--
-- Name: audit_user_actions_old; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_user_actions_old (
    action_id integer NOT NULL,
    user_name character varying(100) NOT NULL,
    action text NOT NULL,
    patient_id integer,
    action_time timestamp without time zone DEFAULT now()
);


--
-- Name: audit_user_actions_action_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_user_actions_action_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_user_actions_action_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_user_actions_action_id_seq OWNED BY public.audit_user_actions_old.action_id;


--
-- Name: audit_user_actions_action_id_seq1; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_user_actions_action_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_user_actions_action_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_user_actions_action_id_seq1 OWNED BY public.audit_user_actions.action_id;


--
-- Name: caisse; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.caisse (
    transaction_id integer NOT NULL,
    patient_id integer,
    amount numeric(10,2) NOT NULL,
    paid_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by_name character varying(100) NOT NULL,
    handled_by integer NOT NULL,
    payment_method character varying(50) NOT NULL,
    transaction_type character varying(50) NOT NULL,
    note text,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    advance_amount numeric(10,2) DEFAULT 0 NOT NULL,
    patient_label character varying(100),
    cancelled_by integer,
    cancelled_at timestamp without time zone,
    cancel_justification text,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_error text,
    staff_discount_amount numeric(10,2) DEFAULT 0 NOT NULL,
    staff_discount_details jsonb,
    CONSTRAINT ck_caisse_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'cancelled'::character varying, 'refunded'::character varying, 'pending_approval'::character varying])::text[])))
);


--
-- Name: caisse_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.caisse_item (
    item_id integer NOT NULL,
    transaction_id integer NOT NULL,
    item_type character varying(50) NOT NULL,
    item_ref_id integer NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    quantity integer NOT NULL,
    line_total numeric(10,2) NOT NULL,
    note text,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL
);


--
-- Name: caisse_item_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.caisse_item_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: caisse_item_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.caisse_item_item_id_seq OWNED BY public.caisse_item.item_id;


--
-- Name: caisse_retrait; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.caisse_retrait (
    retrait_id integer NOT NULL,
    amount numeric(10,2) NOT NULL,
    justification text,
    retrait_at timestamp without time zone DEFAULT now() NOT NULL,
    handled_by integer NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    cancelled_by integer,
    cancelled_at timestamp without time zone,
    cancel_justification text,
    category character varying(50) DEFAULT NULL::character varying,
    payment_method character varying(50) DEFAULT NULL::character varying,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: caisse_retrait_retrait_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.caisse_retrait_retrait_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: caisse_retrait_retrait_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.caisse_retrait_retrait_id_seq OWNED BY public.caisse_retrait.retrait_id;


--
-- Name: caisse_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.caisse_transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: caisse_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.caisse_transaction_id_seq OWNED BY public.caisse.transaction_id;


--
-- Name: consultation_spirituel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.consultation_spirituel (
    consultation_id integer NOT NULL,
    patient_id integer,
    consultation_date timestamp without time zone DEFAULT now(),
    created_by integer,
    created_by_name character varying(100),
    notes text,
    type_consultation character varying(30) NOT NULL,
    presc_generic text[],
    presc_med_spirituel text[],
    mp_type character varying(200),
    fr_registered_at timestamp without time zone,
    fr_appointment_at timestamp without time zone,
    fr_amount_paid numeric(10,2),
    fr_observation text,
    psaume text,
    CONSTRAINT ck_fr_only_for_family CHECK (((((type_consultation)::text = 'FamilyRestoration'::text) AND (fr_registered_at IS NOT NULL) AND (fr_appointment_at IS NOT NULL) AND (fr_amount_paid IS NOT NULL)) OR (((type_consultation)::text = 'Spiritual'::text) AND (fr_registered_at IS NULL) AND (fr_appointment_at IS NULL) AND (fr_amount_paid IS NULL) AND (fr_observation IS NULL)))),
    CONSTRAINT ck_presc_generic CHECK (((presc_generic IS NULL) OR (presc_generic <@ ARRAY['Hony'::text, 'Massage'::text, 'Prayer'::text]))),
    CONSTRAINT ck_presc_med_spirituel CHECK (((presc_med_spirituel IS NULL) OR (presc_med_spirituel <@ ARRAY['SE'::text, 'TIS'::text, 'AE'::text]))),
    CONSTRAINT ck_type_consultation CHECK (((type_consultation)::text = ANY (ARRAY[('Spiritual'::character varying)::text, ('FamilyRestoration'::character varying)::text])))
);


--
-- Name: consultation_spirituel_consultation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.consultation_spirituel_consultation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consultation_spirituel_consultation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.consultation_spirituel_consultation_id_seq OWNED BY public.consultation_spirituel.consultation_id;


--
-- Name: discount_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discount_requests (
    id integer NOT NULL,
    transaction_id integer NOT NULL,
    requested_by integer NOT NULL,
    requested_to integer NOT NULL,
    original_amount numeric(10,2) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    decision_percent integer,
    decision_echelonne_deadline date,
    decided_by integer,
    decided_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: discount_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.discount_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: discount_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.discount_requests_id_seq OWNED BY public.discount_requests.id;


--
-- Name: doctor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.doctor (
    user_id integer NOT NULL,
    license_number character varying(20),
    specialty_id integer,
    years_experience smallint,
    phone character varying(20),
    address character varying(200),
    birth_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT doctor_years_experience_check CHECK ((years_experience >= 0))
);


--
-- Name: examens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.examens (
    id integer NOT NULL,
    code character varying(20) NOT NULL,
    nom text NOT NULL,
    categorie text NOT NULL,
    prix numeric(10,2)
);


--
-- Name: examens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.examens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: examens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.examens_id_seq OWNED BY public.examens.id;


--
-- Name: hospitalization_status_updates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hospitalization_status_updates (
    id integer NOT NULL,
    hospitalization_id integer NOT NULL,
    status character varying(20) NOT NULL,
    note text,
    created_by integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT hospitalization_status_updates_status_check CHECK (((status)::text = ANY ((ARRAY['AMELIORATION'::character varying, 'STABLE'::character varying, 'AGGRAVATION'::character varying])::text[])))
);


--
-- Name: hospitalization_status_updates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.hospitalization_status_updates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hospitalization_status_updates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.hospitalization_status_updates_id_seq OWNED BY public.hospitalization_status_updates.id;


--
-- Name: hospitalizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hospitalizations (
    id integer NOT NULL,
    patient_id integer NOT NULL,
    admitted_at timestamp without time zone DEFAULT now() NOT NULL,
    admitted_by integer NOT NULL,
    admission_reason text,
    discharged_at timestamp without time zone,
    discharge_disposition character varying(30),
    discharge_note text,
    discharged_by integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT hospitalizations_discharge_disposition_check CHECK (((discharge_disposition)::text = ANY ((ARRAY['GUERI'::character varying, 'TRANSFERE'::character varying, 'SORTIE_CONTRE_AVIS_MEDICAL'::character varying, 'DECES'::character varying])::text[])))
);


--
-- Name: hospitalizations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.hospitalizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hospitalizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.hospitalizations_id_seq OWNED BY public.hospitalizations.id;


--
-- Name: lab_result_details; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lab_result_details (
    detail_id integer NOT NULL,
    result_id integer NOT NULL,
    parametre_id integer NOT NULL,
    valeur_text text NOT NULL,
    interpretation character varying(50),
    flagged boolean DEFAULT false,
    valeur_num numeric
);


--
-- Name: lab_result_details_detail_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lab_result_details_detail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lab_result_details_detail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lab_result_details_detail_id_seq OWNED BY public.lab_result_details.detail_id;


--
-- Name: lab_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lab_results (
    result_id integer NOT NULL,
    patient_id integer,
    test_type character varying(100) NOT NULL,
    test_date timestamp without time zone DEFAULT now(),
    prescribed_by integer,
    technician_id integer,
    technician_name character varying(100),
    status character varying(20) DEFAULT 'pending'::character varying,
    note text,
    examen_id integer,
    code_lab_patient character varying(20) NOT NULL,
    created_by integer,
    created_by_name text,
    last_updated_by integer,
    last_updated_by_name text,
    external_patient_info jsonb,
    origin_prescription_id integer,
    batch_id uuid,
    prescribed_by_name character varying(100),
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    batch_uuid character varying(36),
    CONSTRAINT chk_technician_role CHECK (public.check_technician_role(technician_id)),
    CONSTRAINT note_length_check CHECK ((length(note) <= 1000))
);


--
-- Name: TABLE lab_results; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.lab_results IS 'Résultats de laboratoire liés aux dossiers médicaux';


--
-- Name: COLUMN lab_results.batch_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.lab_results.batch_id IS 'Identifiant unique de lot (UUID) pour grouper les examens créés simultanément';


--
-- Name: lab_results_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lab_results_audit (
    audit_id integer NOT NULL,
    result_id integer,
    operation character(1) NOT NULL,
    old_data jsonb,
    new_data jsonb,
    changed_by integer NOT NULL,
    changed_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: lab_results_audit_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lab_results_audit_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lab_results_audit_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lab_results_audit_audit_id_seq OWNED BY public.lab_results_audit.audit_id;


--
-- Name: lab_results_result_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lab_results_result_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lab_results_result_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lab_results_result_id_seq OWNED BY public.lab_results.result_id;


--
-- Name: laborantin; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.laborantin (
    user_id integer NOT NULL,
    lab_section character varying(100) DEFAULT 'général'::character varying NOT NULL,
    certification_date date DEFAULT CURRENT_DATE,
    equipment_access text DEFAULT ''::text,
    hire_date date DEFAULT CURRENT_DATE
);


--
-- Name: medical_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.medical_records (
    record_id integer NOT NULL,
    patient_id integer NOT NULL,
    consultation_date timestamp without time zone DEFAULT now(),
    marital_status character varying(20),
    bp character varying(10),
    temperature numeric(4,1),
    weight numeric(5,2),
    height numeric(5,2),
    medical_history text,
    allergies text,
    symptoms text,
    diagnosis text,
    treatment text,
    severity character varying(20),
    notes text,
    motif_code character varying(20) NOT NULL,
    created_by integer,
    created_by_name character varying(100),
    last_updated_by integer,
    last_updated_by_name character varying(100),
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    appointment_id integer,
    needs_doctor_review boolean DEFAULT false NOT NULL,
    assigned_doctor_id integer,
    reviewed_by integer,
    reviewed_at timestamp without time zone,
    CONSTRAINT medical_records_motif_code_check CHECK (((motif_code)::text = ANY (ARRAY[('consultation'::character varying)::text, ('appointment'::character varying)::text, ('prenatal'::character varying)::text, ('hospitalization'::character varying)::text, ('emergency'::character varying)::text, ('free'::character varying)::text]))),
    CONSTRAINT medical_records_severity_check CHECK (((severity)::text = ANY (ARRAY[('low'::character varying)::text, ('medium'::character varying)::text, ('high'::character varying)::text])))
);


--
-- Name: medical_records_record_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.medical_records_record_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: medical_records_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.medical_records_record_id_seq OWNED BY public.medical_records.record_id;


--
-- Name: medical_specialties; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.medical_specialties (
    specialty_id integer NOT NULL,
    name character varying(100) NOT NULL
);


--
-- Name: medical_specialties_specialty_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.medical_specialties_specialty_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: medical_specialties_specialty_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.medical_specialties_specialty_id_seq OWNED BY public.medical_specialties.specialty_id;


--
-- Name: motif_translations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.motif_translations (
    code character varying(20) NOT NULL,
    label_fr character varying(50) NOT NULL,
    label_en character varying(50) NOT NULL
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    recipient_user_id integer NOT NULL,
    type character varying(50) NOT NULL,
    payload jsonb,
    status character varying(20) DEFAULT 'unread'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    read_at timestamp without time zone
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: nurse; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nurse (
    user_id integer NOT NULL,
    registration_number character varying(20),
    department character varying(100),
    shift character varying(50),
    phone character varying(20),
    hire_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: nurse_shifts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nurse_shifts (
    id integer NOT NULL,
    shift_date date NOT NULL,
    shift_type character varying(20) NOT NULL,
    nurse_id integer NOT NULL,
    created_by integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT nurse_shifts_shift_type_check CHECK (((shift_type)::text = ANY ((ARRAY['MATIN'::character varying, 'APRES_MIDI'::character varying, 'NUIT'::character varying])::text[])))
);


--
-- Name: nurse_shifts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nurse_shifts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nurse_shifts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nurse_shifts_id_seq OWNED BY public.nurse_shifts.id;


--
-- Name: staff_discount_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staff_discount_rules (
    id integer NOT NULL,
    category character varying(30) NOT NULL,
    min_invoice_amount numeric(10,2) DEFAULT 0 NOT NULL,
    rate_percent integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_by integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_by integer,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT staff_discount_rules_category_check CHECK (((category)::text = ANY ((ARRAY['medicament'::character varying, 'examen'::character varying, 'consultation'::character varying, 'carnet'::character varying, 'autre_soin'::character varying])::text[]))),
    CONSTRAINT staff_discount_rules_min_amount_check CHECK ((min_invoice_amount >= (0)::numeric)),
    CONSTRAINT staff_discount_rules_rate_check CHECK (((rate_percent >= 1) AND (rate_percent <= 100)))
);


--
-- Name: staff_discount_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.staff_discount_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: staff_discount_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.staff_discount_rules_id_seq OWNED BY public.staff_discount_rules.id;


--
-- Name: organization_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_config (
    id integer NOT NULL,
    name character varying(255) DEFAULT 'AH2 CLINIC'::character varying NOT NULL,
    slogan character varying(255),
    logo_url character varying(255),
    address character varying(255),
    city character varying(100),
    po_box character varying(50),
    phone character varying(50),
    phone2 character varying(50),
    email character varying(100),
    website character varying(255),
    niu character varying(100),
    rccm character varying(100),
    legal_info text,
    ticket_logo_url character varying,
    ticket_print_token character varying
);


--
-- Name: organization_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.organization_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: organization_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.organization_config_id_seq OWNED BY public.organization_config.id;


--
-- Name: paiement_echelonne; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paiement_echelonne (
    payment_id integer NOT NULL,
    transaction_id integer NOT NULL,
    paid_amount numeric(10,2) NOT NULL,
    payment_date timestamp without time zone DEFAULT now() NOT NULL,
    payment_method character varying(50) NOT NULL,
    payment_type character varying(50) NOT NULL,
    handled_by integer NOT NULL,
    note text,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL
);


--
-- Name: paiement_echelonne_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.paiement_echelonne_payment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: paiement_echelonne_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.paiement_echelonne_payment_id_seq OWNED BY public.paiement_echelonne.payment_id;


--
-- Name: parametres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parametres (
    id integer NOT NULL,
    examen_id integer NOT NULL,
    nom_parametre text NOT NULL,
    unite text NOT NULL,
    type_valeur text NOT NULL,
    input_type character varying(20) DEFAULT 'numeric'::character varying,
    options_list text
);


--
-- Name: parametres_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parametres_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parametres_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parametres_id_seq OWNED BY public.parametres.id;


--
-- Name: patient_contacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patient_contacts (
    contact_id integer NOT NULL,
    patient_id integer NOT NULL,
    full_name character varying(150) NOT NULL,
    relationship character varying(50),
    phone_number character varying(50) NOT NULL,
    is_primary boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: patient_contacts_contact_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patient_contacts_contact_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patient_contacts_contact_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patient_contacts_contact_id_seq OWNED BY public.patient_contacts.contact_id;


--
-- Name: patients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patients (
    patient_id integer NOT NULL,
    first_name character varying(50) NOT NULL,
    last_name character varying(50) NOT NULL,
    birth_date date NOT NULL,
    gender character varying(10),
    national_id character varying(20),
    contact_phone character varying(20),
    assurance character varying(20),
    created_at timestamp without time zone DEFAULT now(),
    created_by integer,
    created_by_name character varying(100),
    last_updated_by integer,
    last_updated_by_name character varying(100),
    residence text,
    code_patient character varying(20),
    father_name character varying(100),
    mother_name character varying(100),
    last_updated_at timestamp without time zone DEFAULT now(),
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    is_toxicology boolean DEFAULT false,
    is_clinical boolean DEFAULT false,
    is_spiritual boolean DEFAULT false,
    is_deleted boolean DEFAULT false,
    deleted_at timestamp without time zone,
    deleted_by integer,
    is_staff boolean DEFAULT false NOT NULL
);


--
-- Name: patients_patient_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.patients_patient_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: patients_patient_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.patients_patient_id_seq OWNED BY public.patients.patient_id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    permission_id integer NOT NULL,
    permission_name character varying(100) NOT NULL,
    procedure_name character varying(100) NOT NULL,
    description_procedure character varying(100)
);


--
-- Name: permissions_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permissions_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permissions_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permissions_permission_id_seq OWNED BY public.permissions.permission_id;


--
-- Name: pharmacy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pharmacy (
    medication_id integer NOT NULL,
    patient_id integer,
    drug_name character varying(100) NOT NULL,
    quantity integer DEFAULT 0 NOT NULL,
    threshold integer DEFAULT 0 NOT NULL,
    medication_type character varying(20) NOT NULL,
    dosage_mg numeric(10,2),
    expiry_date timestamp without time zone,
    stock_status character varying(20) DEFAULT 'normal'::character varying NOT NULL,
    prescribed_by integer,
    name_dr character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    forme character varying(50) DEFAULT 'Autre'::character varying NOT NULL,
    price numeric(10,2) DEFAULT 0.00 NOT NULL
);


--
-- Name: pharmacy_medication_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pharmacy_medication_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pharmacy_medication_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pharmacy_medication_id_seq OWNED BY public.pharmacy.medication_id;


--
-- Name: prayer_book_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prayer_book_type (
    type_code character varying(10) NOT NULL,
    label character varying(100) NOT NULL
);


--
-- Name: prescriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prescriptions (
    prescription_id integer NOT NULL,
    patient_id integer NOT NULL,
    medical_record_id integer,
    medication character varying(100) NOT NULL,
    dosage character varying(50) NOT NULL,
    frequency character varying(50) NOT NULL,
    duration character varying(50) NOT NULL,
    start_date date DEFAULT CURRENT_DATE,
    end_date date,
    status character varying(20) DEFAULT 'active'::character varying,
    prescribed_by integer,
    prescribed_by_name character varying(100),
    notes text,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    is_lab_order boolean DEFAULT false,
    lab_exams_list jsonb DEFAULT '[]'::jsonb,
    CONSTRAINT prescriptions_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('completed'::character varying)::text, ('cancelled'::character varying)::text])))
);


--
-- Name: TABLE prescriptions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.prescriptions IS 'Prescriptions médicales liées aux dossiers médicaux';


--
-- Name: prescriptions_prescription_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.prescriptions_prescription_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: prescriptions_prescription_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.prescriptions_prescription_id_seq OWNED BY public.prescriptions.prescription_id;


--
-- Name: psych_evaluations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.psych_evaluations (
    eval_id integer NOT NULL,
    admission_id integer NOT NULL,
    doctor_id integer,
    eval_date timestamp with time zone DEFAULT now(),
    mood_score integer,
    observations text NOT NULL,
    recommendations text,
    phase_at_time integer,
    CONSTRAINT psych_evaluations_mood_score_check CHECK (((mood_score >= 1) AND (mood_score <= 10)))
);


--
-- Name: psych_evaluations_eval_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.psych_evaluations_eval_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: psych_evaluations_eval_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.psych_evaluations_eval_id_seq OWNED BY public.psych_evaluations.eval_id;


--
-- Name: reference_ranges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reference_ranges (
    id integer NOT NULL,
    parametre_id integer NOT NULL,
    sexe character(1) NOT NULL,
    age_min integer NOT NULL,
    age_max integer NOT NULL,
    valeur_min numeric NOT NULL,
    valeur_max numeric NOT NULL,
    CONSTRAINT reference_ranges_sexe_check CHECK ((sexe = ANY (ARRAY['M'::bpchar, 'F'::bpchar, 'X'::bpchar])))
);


--
-- Name: reference_ranges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reference_ranges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reference_ranges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reference_ranges_id_seq OWNED BY public.reference_ranges.id;


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_permissions (
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- Name: secretaire; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.secretaire (
    user_id integer NOT NULL,
    office_number character varying(10),
    phone_ext character varying(10),
    fax_number character varying(20),
    hire_date date DEFAULT CURRENT_DATE
);


--
-- Name: spiritual_attendance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.spiritual_attendance (
    session_id integer NOT NULL,
    admission_id integer NOT NULL,
    status character varying(20) DEFAULT 'PRESENT'::character varying,
    notes text
);


--
-- Name: spiritual_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.spiritual_sessions (
    session_id integer NOT NULL,
    session_date date NOT NULL,
    conductor_name character varying(100),
    topic character varying(200),
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: spiritual_sessions_session_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.spiritual_sessions_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: spiritual_sessions_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.spiritual_sessions_session_id_seq OWNED BY public.spiritual_sessions.session_id;


--
-- Name: stock_movement; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stock_movement (
    movement_id integer NOT NULL,
    medication_id integer NOT NULL,
    change_qty integer NOT NULL,
    movement_type character varying(50) NOT NULL,
    note text,
    created_by character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: stock_movement_movement_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stock_movement_movement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stock_movement_movement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stock_movement_movement_id_seq OWNED BY public.stock_movement.movement_id;


--
-- Name: toxico_dossiers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.toxico_dossiers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: toxico_dossiers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.toxico_dossiers (
    id integer DEFAULT nextval('public.toxico_dossiers_id_seq'::regclass) NOT NULL,
    patient_id integer NOT NULL,
    psychologist_id integer,
    admission_date date DEFAULT CURRENT_DATE NOT NULL,
    substance character varying(100) NOT NULL,
    current_phase integer DEFAULT 1 NOT NULL,
    relapse_count integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    guardian_name character varying(150),
    guardian_contact character varying(50),
    consent_file character varying(255),
    notes_admission text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: toxico_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.toxico_evaluations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: toxico_evaluations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.toxico_evaluations (
    id integer DEFAULT nextval('public.toxico_evaluations_id_seq'::regclass) NOT NULL,
    dossier_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    created_by integer,
    decision character varying(50) NOT NULL,
    observation text NOT NULL,
    recommendation text,
    phase_before integer NOT NULL,
    phase_after integer NOT NULL,
    is_relapse boolean DEFAULT false
);


--
-- Name: toxico_phase_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.toxico_phase_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: toxico_phase_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.toxico_phase_history (
    id integer DEFAULT nextval('public.toxico_phase_history_id_seq'::regclass) NOT NULL,
    dossier_id integer NOT NULL,
    phase integer NOT NULL,
    start_date date NOT NULL,
    end_date date,
    status character varying(50) DEFAULT 'En cours'::character varying NOT NULL,
    comments text
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash text NOT NULL,
    full_name character varying(100) NOT NULL,
    postgres_role character varying(20),
    is_active boolean DEFAULT true,
    specialty_id integer,
    role_id integer,
    email character varying(150),
    contact character varying(50),
    token_version integer DEFAULT 0 NOT NULL,
    is_head_nurse boolean DEFAULT false NOT NULL,
    CONSTRAINT chk_specialty CHECK ((((postgres_role)::text = 'app_medical'::text) OR (((postgres_role)::text <> 'app_medical'::text) AND (specialty_id IS NULL)))),
    CONSTRAINT users_postgres_role_check CHECK (((postgres_role)::text = ANY (ARRAY['app_secretaire'::text, 'app_medical'::text, 'app_laborantin'::text, 'app_admin'::text, 'app_toxico_web'::text])))
);


--
-- Name: user_specialties; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.user_specialties AS
 SELECT u.user_id,
    u.full_name,
    u.postgres_role,
    COALESCE(ms.name, 'Généraliste'::character varying) AS specialty_name,
    COALESCE(ms.specialty_id, ( SELECT medical_specialties.specialty_id
           FROM public.medical_specialties
          WHERE ((medical_specialties.name)::text = 'Généraliste'::text))) AS effective_specialty_id
   FROM (public.users u
     LEFT JOIN public.medical_specialties ms ON ((u.specialty_id = ms.specialty_id)))
  WHERE ((u.postgres_role)::text = 'app_medical'::text);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: view_patient_summary; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.view_patient_summary AS
 SELECT p.patient_id,
    p.code_patient,
    mr.consultation_date AS last_consultation,
    mr.diagnosis AS last_diagnosis,
    mr.bp AS last_bp,
    mr.weight AS last_weight,
    mr.allergies
   FROM (public.patients p
     LEFT JOIN LATERAL ( SELECT medical_records.consultation_date,
            medical_records.diagnosis,
            medical_records.bp,
            medical_records.weight,
            medical_records.allergies
           FROM public.medical_records
          WHERE (medical_records.patient_id = p.patient_id)
          ORDER BY medical_records.consultation_date DESC
         LIMIT 1) mr ON (true));


--
-- Name: vue_appointment; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_appointment AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'appointment'::text);


--
-- Name: vue_autre; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_autre AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text <> ALL (ARRAY[('consultation'::character varying)::text, ('appointment'::character varying)::text, ('prenatal'::character varying)::text, ('hospitalization'::character varying)::text, ('emergency'::character varying)::text, ('free'::character varying)::text]));


--
-- Name: vue_consultation; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_consultation AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'consultation'::text);


--
-- Name: vue_emergency; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_emergency AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'emergency'::text);


--
-- Name: vue_free; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_free AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'free'::text);


--
-- Name: vue_hospitalization; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_hospitalization AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'hospitalization'::text);


--
-- Name: vue_new_motif; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_new_motif AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'new_motif'::text);


--
-- Name: vue_prenatal; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.vue_prenatal AS
 SELECT record_id,
    patient_id,
    consultation_date,
    marital_status,
    bp,
    temperature,
    weight,
    height,
    medical_history,
    allergies,
    symptoms,
    diagnosis,
    treatment,
    severity,
    notes,
    motif_code,
    created_by,
    created_by_name,
    last_updated_by,
    last_updated_by_name
   FROM public.medical_records
  WHERE ((motif_code)::text = 'prenatal'::text);


--
-- Name: admissions admission_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admissions ALTER COLUMN admission_id SET DEFAULT nextval('public.admissions_admission_id_seq'::regclass);


--
-- Name: application_roles role_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_roles ALTER COLUMN role_id SET DEFAULT nextval('public.application_roles_role_id_seq'::regclass);


--
-- Name: appointments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appointments ALTER COLUMN id SET DEFAULT nextval('public.appointments_id_seq'::regclass);


--
-- Name: audit_access access_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_access ALTER COLUMN access_id SET DEFAULT nextval('public.audit_access_access_id_seq'::regclass);


--
-- Name: audit_access_old log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_access_old ALTER COLUMN log_id SET DEFAULT nextval('public.audit_access_log_id_seq'::regclass);


--
-- Name: audit_logs log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN log_id SET DEFAULT nextval('public.audit_logs_log_id_seq'::regclass);


--
-- Name: audit_user_actions action_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_user_actions ALTER COLUMN action_id SET DEFAULT nextval('public.audit_user_actions_action_id_seq1'::regclass);


--
-- Name: audit_user_actions_old action_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_user_actions_old ALTER COLUMN action_id SET DEFAULT nextval('public.audit_user_actions_action_id_seq'::regclass);


--
-- Name: caisse transaction_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse ALTER COLUMN transaction_id SET DEFAULT nextval('public.caisse_transaction_id_seq'::regclass);


--
-- Name: caisse_item item_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse_item ALTER COLUMN item_id SET DEFAULT nextval('public.caisse_item_item_id_seq'::regclass);


--
-- Name: caisse_retrait retrait_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse_retrait ALTER COLUMN retrait_id SET DEFAULT nextval('public.caisse_retrait_retrait_id_seq'::regclass);


--
-- Name: consultation_spirituel consultation_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultation_spirituel ALTER COLUMN consultation_id SET DEFAULT nextval('public.consultation_spirituel_consultation_id_seq'::regclass);


--
-- Name: discount_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_requests ALTER COLUMN id SET DEFAULT nextval('public.discount_requests_id_seq'::regclass);


--
-- Name: examens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.examens ALTER COLUMN id SET DEFAULT nextval('public.examens_id_seq'::regclass);


--
-- Name: hospitalization_status_updates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalization_status_updates ALTER COLUMN id SET DEFAULT nextval('public.hospitalization_status_updates_id_seq'::regclass);


--
-- Name: hospitalizations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalizations ALTER COLUMN id SET DEFAULT nextval('public.hospitalizations_id_seq'::regclass);


--
-- Name: lab_result_details detail_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_result_details ALTER COLUMN detail_id SET DEFAULT nextval('public.lab_result_details_detail_id_seq'::regclass);


--
-- Name: lab_results result_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results ALTER COLUMN result_id SET DEFAULT nextval('public.lab_results_result_id_seq'::regclass);


--
-- Name: lab_results_audit audit_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results_audit ALTER COLUMN audit_id SET DEFAULT nextval('public.lab_results_audit_audit_id_seq'::regclass);


--
-- Name: medical_records record_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records ALTER COLUMN record_id SET DEFAULT nextval('public.medical_records_record_id_seq'::regclass);


--
-- Name: medical_specialties specialty_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_specialties ALTER COLUMN specialty_id SET DEFAULT nextval('public.medical_specialties_specialty_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: nurse_shifts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nurse_shifts ALTER COLUMN id SET DEFAULT nextval('public.nurse_shifts_id_seq'::regclass);


--
-- Name: staff_discount_rules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_discount_rules ALTER COLUMN id SET DEFAULT nextval('public.staff_discount_rules_id_seq'::regclass);


--
-- Name: organization_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_config ALTER COLUMN id SET DEFAULT nextval('public.organization_config_id_seq'::regclass);


--
-- Name: paiement_echelonne payment_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paiement_echelonne ALTER COLUMN payment_id SET DEFAULT nextval('public.paiement_echelonne_payment_id_seq'::regclass);


--
-- Name: parametres id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametres ALTER COLUMN id SET DEFAULT nextval('public.parametres_id_seq'::regclass);


--
-- Name: patient_contacts contact_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_contacts ALTER COLUMN contact_id SET DEFAULT nextval('public.patient_contacts_contact_id_seq'::regclass);


--
-- Name: patients patient_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients ALTER COLUMN patient_id SET DEFAULT nextval('public.patients_patient_id_seq'::regclass);


--
-- Name: permissions permission_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions ALTER COLUMN permission_id SET DEFAULT nextval('public.permissions_permission_id_seq'::regclass);


--
-- Name: pharmacy medication_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacy ALTER COLUMN medication_id SET DEFAULT nextval('public.pharmacy_medication_id_seq'::regclass);


--
-- Name: prescriptions prescription_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prescriptions ALTER COLUMN prescription_id SET DEFAULT nextval('public.prescriptions_prescription_id_seq'::regclass);


--
-- Name: psych_evaluations eval_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psych_evaluations ALTER COLUMN eval_id SET DEFAULT nextval('public.psych_evaluations_eval_id_seq'::regclass);


--
-- Name: reference_ranges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reference_ranges ALTER COLUMN id SET DEFAULT nextval('public.reference_ranges_id_seq'::regclass);


--
-- Name: spiritual_sessions session_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spiritual_sessions ALTER COLUMN session_id SET DEFAULT nextval('public.spiritual_sessions_session_id_seq'::regclass);


--
-- Name: stock_movement movement_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_movement ALTER COLUMN movement_id SET DEFAULT nextval('public.stock_movement_movement_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: admin admin_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin
    ADD CONSTRAINT admin_pkey PRIMARY KEY (user_id);


--
-- Name: admissions admissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_pkey PRIMARY KEY (admission_id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: application_roles application_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_roles
    ADD CONSTRAINT application_roles_pkey PRIMARY KEY (role_id);


--
-- Name: application_roles application_roles_role_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_roles
    ADD CONSTRAINT application_roles_role_name_key UNIQUE (role_name);


--
-- Name: appointments appointments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_pkey PRIMARY KEY (id);


--
-- Name: audit_access_old audit_access_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_access_old
    ADD CONSTRAINT audit_access_pkey PRIMARY KEY (log_id);


--
-- Name: audit_access audit_access_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_access
    ADD CONSTRAINT audit_access_pkey1 PRIMARY KEY (access_id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (log_id);


--
-- Name: audit_user_actions_old audit_user_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_user_actions_old
    ADD CONSTRAINT audit_user_actions_pkey PRIMARY KEY (action_id);


--
-- Name: audit_user_actions audit_user_actions_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_user_actions
    ADD CONSTRAINT audit_user_actions_pkey1 PRIMARY KEY (action_id);


--
-- Name: caisse_item caisse_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse_item
    ADD CONSTRAINT caisse_item_pkey PRIMARY KEY (item_id);


--
-- Name: caisse caisse_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_pkey PRIMARY KEY (transaction_id);


--
-- Name: caisse_retrait caisse_retrait_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse_retrait
    ADD CONSTRAINT caisse_retrait_pkey PRIMARY KEY (retrait_id);


--
-- Name: consultation_spirituel consultation_spirituel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_pkey PRIMARY KEY (consultation_id);


--
-- Name: discount_requests discount_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_pkey PRIMARY KEY (id);


--
-- Name: doctor doctor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctor
    ADD CONSTRAINT doctor_pkey PRIMARY KEY (user_id);


--
-- Name: examens examens_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.examens
    ADD CONSTRAINT examens_code_key UNIQUE (code);


--
-- Name: examens examens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.examens
    ADD CONSTRAINT examens_pkey PRIMARY KEY (id);


--
-- Name: hospitalization_status_updates hospitalization_status_updates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalization_status_updates
    ADD CONSTRAINT hospitalization_status_updates_pkey PRIMARY KEY (id);


--
-- Name: hospitalizations hospitalizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalizations
    ADD CONSTRAINT hospitalizations_pkey PRIMARY KEY (id);


--
-- Name: lab_result_details lab_result_details_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_result_details
    ADD CONSTRAINT lab_result_details_pkey PRIMARY KEY (detail_id);


--
-- Name: lab_results_audit lab_results_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results_audit
    ADD CONSTRAINT lab_results_audit_pkey PRIMARY KEY (audit_id);


--
-- Name: lab_results lab_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_pkey PRIMARY KEY (result_id);


--
-- Name: laborantin laborantin_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.laborantin
    ADD CONSTRAINT laborantin_pkey PRIMARY KEY (user_id);


--
-- Name: medical_records medical_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_pkey PRIMARY KEY (record_id);


--
-- Name: medical_specialties medical_specialties_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_specialties
    ADD CONSTRAINT medical_specialties_name_key UNIQUE (name);


--
-- Name: medical_specialties medical_specialties_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_specialties
    ADD CONSTRAINT medical_specialties_pkey PRIMARY KEY (specialty_id);


--
-- Name: motif_translations motif_translations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.motif_translations
    ADD CONSTRAINT motif_translations_pkey PRIMARY KEY (code);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: nurse nurse_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nurse
    ADD CONSTRAINT nurse_pkey PRIMARY KEY (user_id);


--
-- Name: nurse_shifts nurse_shifts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nurse_shifts
    ADD CONSTRAINT nurse_shifts_pkey PRIMARY KEY (id);


--
-- Name: staff_discount_rules staff_discount_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_discount_rules
    ADD CONSTRAINT staff_discount_rules_pkey PRIMARY KEY (id);


--
-- Name: organization_config organization_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_config
    ADD CONSTRAINT organization_config_pkey PRIMARY KEY (id);


--
-- Name: paiement_echelonne paiement_echelonne_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paiement_echelonne
    ADD CONSTRAINT paiement_echelonne_pkey PRIMARY KEY (payment_id);


--
-- Name: parametres parametres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametres
    ADD CONSTRAINT parametres_pkey PRIMARY KEY (id);


--
-- Name: patient_contacts patient_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_contacts
    ADD CONSTRAINT patient_contacts_pkey PRIMARY KEY (contact_id);


--
-- Name: patients patients_code_patient_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_code_patient_key UNIQUE (code_patient);


--
-- Name: patients patients_national_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_national_id_key UNIQUE (national_id);


--
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (patient_id);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (permission_id);


--
-- Name: pharmacy pharmacy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacy
    ADD CONSTRAINT pharmacy_pkey PRIMARY KEY (medication_id);


--
-- Name: prayer_book_type prayer_book_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prayer_book_type
    ADD CONSTRAINT prayer_book_type_pkey PRIMARY KEY (type_code);


--
-- Name: prescriptions prescriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_pkey PRIMARY KEY (prescription_id);


--
-- Name: psych_evaluations psych_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psych_evaluations
    ADD CONSTRAINT psych_evaluations_pkey PRIMARY KEY (eval_id);


--
-- Name: reference_ranges reference_ranges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reference_ranges
    ADD CONSTRAINT reference_ranges_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_id);


--
-- Name: secretaire secretaire_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.secretaire
    ADD CONSTRAINT secretaire_pkey PRIMARY KEY (user_id);


--
-- Name: spiritual_attendance spiritual_attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spiritual_attendance
    ADD CONSTRAINT spiritual_attendance_pkey PRIMARY KEY (session_id, admission_id);


--
-- Name: spiritual_sessions spiritual_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spiritual_sessions
    ADD CONSTRAINT spiritual_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: stock_movement stock_movement_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_movement
    ADD CONSTRAINT stock_movement_pkey PRIMARY KEY (movement_id);


--
-- Name: toxico_dossiers toxico_dossiers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT toxico_dossiers_pkey PRIMARY KEY (id);


--
-- Name: toxico_evaluations toxico_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_evaluations
    ADD CONSTRAINT toxico_evaluations_pkey PRIMARY KEY (id);


--
-- Name: toxico_phase_history toxico_phase_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_phase_history
    ADD CONSTRAINT toxico_phase_history_pkey PRIMARY KEY (id);


--
-- Name: toxico_dossiers uq_toxico_patient; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT uq_toxico_patient UNIQUE (patient_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: appointments_uuid_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX appointments_uuid_key ON public.appointments USING btree (uuid);


--
-- Name: caisse_retrait_uuid_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX caisse_retrait_uuid_key ON public.caisse_retrait USING btree (uuid);


--
-- Name: caisse_uuid_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX caisse_uuid_key ON public.caisse USING btree (uuid);


--
-- Name: idx_admissions_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admissions_active ON public.admissions USING btree (status) WHERE ((status)::text = 'ACTIVE'::text);


--
-- Name: idx_appointments_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_appointments_date ON public.appointments USING btree (appointment_date);


--
-- Name: idx_caisse_payment_method; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_caisse_payment_method ON public.caisse USING btree (payment_method);


--
-- Name: idx_caisse_retrait_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_caisse_retrait_category ON public.caisse_retrait USING btree (category);


--
-- Name: idx_caisse_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_caisse_status ON public.caisse USING btree (status);


--
-- Name: idx_code_lab_patient; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_code_lab_patient ON public.lab_results USING btree (code_lab_patient);


--
-- Name: idx_lab_details_parametre; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lab_details_parametre ON public.lab_result_details USING btree (parametre_id);


--
-- Name: idx_lab_result_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lab_result_code ON public.lab_results USING btree (code_lab_patient);


--
-- Name: idx_lab_results_batch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lab_results_batch_id ON public.lab_results USING btree (batch_id);


--
-- Name: idx_lab_results_patient_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lab_results_patient_date ON public.lab_results USING btree (patient_id, test_date DESC);


--
-- Name: idx_medical_records_motif_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_medical_records_motif_code ON public.medical_records USING btree (motif_code);


--
-- Name: idx_medical_records_patient_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_medical_records_patient_date ON public.medical_records USING btree (patient_id, consultation_date DESC);


--
-- Name: idx_paiement_trans_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_paiement_trans_id ON public.paiement_echelonne USING btree (transaction_id);


--
-- Name: idx_parametres_examen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parametres_examen ON public.parametres USING btree (examen_id);


--
-- Name: idx_patients_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_active ON public.patients USING btree (is_deleted) WHERE (is_deleted = false);


--
-- Name: idx_patients_clinical; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_clinical ON public.patients USING btree (is_clinical) WHERE (is_clinical = true);


--
-- Name: idx_patients_code_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_code_search ON public.patients USING btree (code_patient);


--
-- Name: idx_patients_full_name_lower; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_full_name_lower ON public.patients USING btree (lower((((last_name)::text || ' '::text) || (first_name)::text)));


--
-- Name: idx_patients_global_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_global_search ON public.patients USING btree (code_patient, last_name, first_name) WHERE (is_deleted = false);


--
-- Name: idx_patients_name_rev_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_name_rev_search ON public.patients USING btree (lower((((first_name)::text || ' '::text) || (last_name)::text)));


--
-- Name: idx_patients_spiritual; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_spiritual ON public.patients USING btree (is_spiritual) WHERE (is_spiritual = true);


--
-- Name: idx_patients_toxico; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_patients_toxico ON public.patients USING btree (is_toxicology) WHERE (is_toxicology = true);


--
-- Name: idx_pharmacy_drug_name_lower; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pharmacy_drug_name_lower ON public.pharmacy USING btree (lower((drug_name)::text));


--
-- Name: idx_pharmacy_stock_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pharmacy_stock_status ON public.pharmacy USING btree (stock_status);


--
-- Name: idx_prescriptions_patient_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_prescriptions_patient_status ON public.prescriptions USING btree (patient_id, status);


--
-- Name: idx_reference_ranges_parametre; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reference_ranges_parametre ON public.reference_ranges USING btree (parametre_id);


--
-- Name: idx_toxico_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_toxico_active ON public.toxico_dossiers USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_toxico_psy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_toxico_psy ON public.toxico_dossiers USING btree (psychologist_id);


--
-- Name: ix_discount_requests_requested_to_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_discount_requests_requested_to_status ON public.discount_requests USING btree (requested_to, status);


--
-- Name: ix_discount_requests_transaction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_discount_requests_transaction ON public.discount_requests USING btree (transaction_id);


--
-- Name: ix_hospitalization_status_updates_hospitalization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hospitalization_status_updates_hospitalization ON public.hospitalization_status_updates USING btree (hospitalization_id);


--
-- Name: ix_hospitalizations_patient; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hospitalizations_patient ON public.hospitalizations USING btree (patient_id);


--
-- Name: ix_lab_results_batch_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lab_results_batch_uuid ON public.lab_results USING btree (batch_uuid);


--
-- Name: ix_lab_results_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_lab_results_uuid ON public.lab_results USING btree (uuid);


--
-- Name: ix_medical_records_pending_review; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_medical_records_pending_review ON public.medical_records USING btree (needs_doctor_review, reviewed_at) WHERE ((needs_doctor_review = true) AND (reviewed_at IS NULL));


--
-- Name: ix_notifications_recipient_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_recipient_status ON public.notifications USING btree (recipient_user_id, status);


--
-- Name: ix_nurse_shifts_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_nurse_shifts_date ON public.nurse_shifts USING btree (shift_date);


--
-- Name: medical_records_uuid_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX medical_records_uuid_key ON public.medical_records USING btree (uuid);


--
-- Name: paiement_echelonne_uuid_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX paiement_echelonne_uuid_key ON public.paiement_echelonne USING btree (uuid);


--
-- Name: patients_uuid_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX patients_uuid_key ON public.patients USING btree (uuid);


--
-- Name: ux_hospitalizations_one_open_per_patient; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_hospitalizations_one_open_per_patient ON public.hospitalizations USING btree (patient_id) WHERE (discharged_at IS NULL);


--
-- Name: ux_nurse_shifts_no_duplicate; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_nurse_shifts_no_duplicate ON public.nurse_shifts USING btree (shift_date, shift_type, nurse_id);


--
-- Name: uq_staff_discount_rules_active_category; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_staff_discount_rules_active_category ON public.staff_discount_rules USING btree (category) WHERE is_active;


--
-- Name: caisse trg_caisse_protect_cancelled; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_caisse_protect_cancelled BEFORE UPDATE ON public.caisse FOR EACH ROW EXECUTE FUNCTION public.fn_caisse_protect_cancelled();


--
-- Name: users trg_default_specialty; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_default_specialty BEFORE INSERT ON public.users FOR EACH ROW EXECUTE FUNCTION public.set_default_specialty();


--
-- Name: lab_results trg_fix_lab_names_safe; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_fix_lab_names_safe BEFORE INSERT OR UPDATE ON public.lab_results FOR EACH ROW EXECUTE FUNCTION public.fix_lab_names();


--
-- Name: patients trg_patient_tracking; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_patient_tracking BEFORE INSERT OR UPDATE ON public.patients FOR EACH ROW EXECUTE FUNCTION public.track_patient_changes();


--
-- Name: prescriptions trg_prescription_names; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_prescription_names BEFORE INSERT OR UPDATE ON public.prescriptions FOR EACH ROW EXECUTE FUNCTION public.update_prescribed_names();


--
-- Name: appointments trg_refresh_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_refresh_updated_at BEFORE UPDATE ON public.appointments FOR EACH ROW EXECUTE FUNCTION public.refresh_updated_at();


--
-- Name: consultation_spirituel trg_spiritual_names; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_spiritual_names BEFORE INSERT OR UPDATE ON public.consultation_spirituel FOR EACH ROW EXECUTE FUNCTION public.update_user_names_cs();


--
-- Name: pharmacy trg_update_pharmacy_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_update_pharmacy_updated_at BEFORE UPDATE ON public.pharmacy FOR EACH ROW EXECUTE FUNCTION public.update_pharmacy_updated_at();


--
-- Name: users trg_user_after_insert; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_after_insert AFTER INSERT ON public.users FOR EACH ROW EXECUTE FUNCTION public.create_metier_profile();


--
-- Name: users trg_user_after_update_role; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_user_after_update_role AFTER UPDATE OF role_id ON public.users FOR EACH ROW WHEN ((old.role_id IS DISTINCT FROM new.role_id)) EXECUTE FUNCTION public.create_metier_profile();


--
-- Name: admin admin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin
    ADD CONSTRAINT admin_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: admissions admissions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: admissions admissions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admissions
    ADD CONSTRAINT admissions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: appointments appointments_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: appointments appointments_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: audit_access audit_access_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_access
    ADD CONSTRAINT audit_access_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: audit_user_actions audit_user_actions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_user_actions
    ADD CONSTRAINT audit_user_actions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: caisse caisse_cancelled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_cancelled_by_fkey FOREIGN KEY (cancelled_by) REFERENCES public.users(user_id);


--
-- Name: caisse caisse_handled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_handled_by_fkey FOREIGN KEY (handled_by) REFERENCES public.users(user_id);


--
-- Name: caisse_item caisse_item_transaction_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse_item
    ADD CONSTRAINT caisse_item_transaction_fkey FOREIGN KEY (transaction_id) REFERENCES public.caisse(transaction_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: caisse caisse_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse
    ADD CONSTRAINT caisse_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: consultation_spirituel consultation_spirituel_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: consultation_spirituel consultation_spirituel_mp_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_mp_type_fkey FOREIGN KEY (mp_type) REFERENCES public.prayer_book_type(type_code) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: consultation_spirituel consultation_spirituel_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consultation_spirituel
    ADD CONSTRAINT consultation_spirituel_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: discount_requests discount_requests_decided_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_decided_by_fkey FOREIGN KEY (decided_by) REFERENCES public.users(user_id);


--
-- Name: discount_requests discount_requests_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(user_id);


--
-- Name: discount_requests discount_requests_requested_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_requested_to_fkey FOREIGN KEY (requested_to) REFERENCES public.users(user_id);


--
-- Name: discount_requests discount_requests_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_requests
    ADD CONSTRAINT discount_requests_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.caisse(transaction_id);


--
-- Name: doctor doctor_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctor
    ADD CONSTRAINT doctor_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.medical_specialties(specialty_id);


--
-- Name: doctor doctor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctor
    ADD CONSTRAINT doctor_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: spiritual_attendance fk_att_admission; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spiritual_attendance
    ADD CONSTRAINT fk_att_admission FOREIGN KEY (admission_id) REFERENCES public.admissions(admission_id);


--
-- Name: spiritual_attendance fk_att_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spiritual_attendance
    ADD CONSTRAINT fk_att_session FOREIGN KEY (session_id) REFERENCES public.spiritual_sessions(session_id);


--
-- Name: caisse_retrait fk_caisse_retrait_cancelled_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse_retrait
    ADD CONSTRAINT fk_caisse_retrait_cancelled_by FOREIGN KEY (cancelled_by) REFERENCES public.users(user_id);


--
-- Name: patient_contacts fk_contact_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patient_contacts
    ADD CONSTRAINT fk_contact_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: toxico_evaluations fk_eval_creator; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_evaluations
    ADD CONSTRAINT fk_eval_creator FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: toxico_evaluations fk_eval_dossier; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_evaluations
    ADD CONSTRAINT fk_eval_dossier FOREIGN KEY (dossier_id) REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE;


--
-- Name: toxico_phase_history fk_history_dossier; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_phase_history
    ADD CONSTRAINT fk_history_dossier FOREIGN KEY (dossier_id) REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE;


--
-- Name: lab_results fk_origin_prescription; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT fk_origin_prescription FOREIGN KEY (origin_prescription_id) REFERENCES public.prescriptions(prescription_id);


--
-- Name: paiement_echelonne fk_paiement_caisse; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paiement_echelonne
    ADD CONSTRAINT fk_paiement_caisse FOREIGN KEY (transaction_id) REFERENCES public.caisse(transaction_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: caisse_retrait fk_retrait_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caisse_retrait
    ADD CONSTRAINT fk_retrait_user FOREIGN KEY (handled_by) REFERENCES public.users(user_id);


--
-- Name: stock_movement fk_stockmed_pharmacy; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_movement
    ADD CONSTRAINT fk_stockmed_pharmacy FOREIGN KEY (medication_id) REFERENCES public.pharmacy(medication_id) ON DELETE CASCADE;


--
-- Name: toxico_dossiers fk_toxico_patient; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT fk_toxico_patient FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE;


--
-- Name: toxico_dossiers fk_toxico_psychologist; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.toxico_dossiers
    ADD CONSTRAINT fk_toxico_psychologist FOREIGN KEY (psychologist_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: users fk_user_specialty; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_user_specialty FOREIGN KEY (specialty_id) REFERENCES public.medical_specialties(specialty_id);


--
-- Name: users fk_users_role_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_role_id FOREIGN KEY (role_id) REFERENCES public.application_roles(role_id) ON DELETE SET NULL;


--
-- Name: hospitalization_status_updates hospitalization_status_updates_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalization_status_updates
    ADD CONSTRAINT hospitalization_status_updates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: hospitalization_status_updates hospitalization_status_updates_hospitalization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalization_status_updates
    ADD CONSTRAINT hospitalization_status_updates_hospitalization_id_fkey FOREIGN KEY (hospitalization_id) REFERENCES public.hospitalizations(id);


--
-- Name: hospitalizations hospitalizations_admitted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalizations
    ADD CONSTRAINT hospitalizations_admitted_by_fkey FOREIGN KEY (admitted_by) REFERENCES public.users(user_id);


--
-- Name: hospitalizations hospitalizations_discharged_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalizations
    ADD CONSTRAINT hospitalizations_discharged_by_fkey FOREIGN KEY (discharged_by) REFERENCES public.users(user_id);


--
-- Name: hospitalizations hospitalizations_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hospitalizations
    ADD CONSTRAINT hospitalizations_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: lab_result_details lab_result_details_parametre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_result_details
    ADD CONSTRAINT lab_result_details_parametre_id_fkey FOREIGN KEY (parametre_id) REFERENCES public.parametres(id) ON DELETE RESTRICT;


--
-- Name: lab_result_details lab_result_details_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_result_details
    ADD CONSTRAINT lab_result_details_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.lab_results(result_id) ON DELETE CASCADE;


--
-- Name: lab_results_audit lab_results_audit_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results_audit
    ADD CONSTRAINT lab_results_audit_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.lab_results(result_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: lab_results lab_results_examen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_examen_id_fkey FOREIGN KEY (examen_id) REFERENCES public.examens(id);


--
-- Name: lab_results lab_results_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: lab_results lab_results_prescribed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_prescribed_by_fkey FOREIGN KEY (prescribed_by) REFERENCES public.users(user_id);


--
-- Name: lab_results lab_results_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lab_results
    ADD CONSTRAINT lab_results_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.users(user_id);


--
-- Name: laborantin laborantin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.laborantin
    ADD CONSTRAINT laborantin_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: medical_records medical_records_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE SET NULL;


--
-- Name: medical_records medical_records_assigned_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_assigned_doctor_id_fkey FOREIGN KEY (assigned_doctor_id) REFERENCES public.users(user_id);


--
-- Name: medical_records medical_records_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: medical_records medical_records_last_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_last_updated_by_fkey FOREIGN KEY (last_updated_by) REFERENCES public.users(user_id);


--
-- Name: medical_records medical_records_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: medical_records medical_records_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.medical_records
    ADD CONSTRAINT medical_records_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(user_id);


--
-- Name: notifications notifications_recipient_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_recipient_user_id_fkey FOREIGN KEY (recipient_user_id) REFERENCES public.users(user_id);


--
-- Name: nurse_shifts nurse_shifts_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nurse_shifts
    ADD CONSTRAINT nurse_shifts_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: nurse_shifts nurse_shifts_nurse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nurse_shifts
    ADD CONSTRAINT nurse_shifts_nurse_id_fkey FOREIGN KEY (nurse_id) REFERENCES public.users(user_id);


--
-- Name: staff_discount_rules staff_discount_rules_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_discount_rules
    ADD CONSTRAINT staff_discount_rules_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: staff_discount_rules staff_discount_rules_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_discount_rules
    ADD CONSTRAINT staff_discount_rules_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(user_id);


--
-- Name: nurse nurse_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nurse
    ADD CONSTRAINT nurse_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: parametres parametres_examen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametres
    ADD CONSTRAINT parametres_examen_id_fkey FOREIGN KEY (examen_id) REFERENCES public.examens(id) ON DELETE CASCADE;


--
-- Name: patients patients_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: patients patients_deleted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_deleted_by_fkey FOREIGN KEY (deleted_by) REFERENCES public.users(user_id);


--
-- Name: patients patients_last_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_last_updated_by_fkey FOREIGN KEY (last_updated_by) REFERENCES public.users(user_id);


--
-- Name: pharmacy pharmacy_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacy
    ADD CONSTRAINT pharmacy_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: pharmacy pharmacy_prescribed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacy
    ADD CONSTRAINT pharmacy_prescribed_by_fkey FOREIGN KEY (prescribed_by) REFERENCES public.users(user_id);


--
-- Name: prescriptions prescriptions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id);


--
-- Name: prescriptions prescriptions_prescribed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prescriptions
    ADD CONSTRAINT prescriptions_prescribed_by_fkey FOREIGN KEY (prescribed_by) REFERENCES public.users(user_id);


--
-- Name: psych_evaluations psych_evaluations_admission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psych_evaluations
    ADD CONSTRAINT psych_evaluations_admission_id_fkey FOREIGN KEY (admission_id) REFERENCES public.admissions(admission_id) ON DELETE CASCADE;


--
-- Name: psych_evaluations psych_evaluations_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.psych_evaluations
    ADD CONSTRAINT psych_evaluations_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.users(user_id);


--
-- Name: reference_ranges reference_ranges_parametre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reference_ranges
    ADD CONSTRAINT reference_ranges_parametre_id_fkey FOREIGN KEY (parametre_id) REFERENCES public.parametres(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(permission_id);


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.application_roles(role_id);


--
-- Name: secretaire secretaire_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.secretaire
    ADD CONSTRAINT secretaire_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: patients medical_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY medical_policy ON public.patients TO app_medical USING (true);


--
-- Migration 019: fabrication, reception et avaries du stock
--

CREATE TABLE public.production_lots (
    id serial PRIMARY KEY,
    lot_number varchar(30) NOT NULL,
    product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
    quantity_produced integer NOT NULL,
    production_date date NOT NULL,
    delivery_date date,
    expiry_date date,
    producer varchar(150),
    status varchar(20) NOT NULL DEFAULT 'produit',
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT production_lots_lot_number_key UNIQUE (lot_number),
    CONSTRAINT production_lots_quantity_check CHECK (quantity_produced > 0),
    CONSTRAINT production_lots_status_check
        CHECK (status IN ('produit','livre','recu','annule'))
);
CREATE INDEX idx_production_lots_status
    ON public.production_lots (status);

CREATE TABLE public.stock_receipts (
    id serial PRIMARY KEY,
    receipt_number varchar(30) NOT NULL,
    origin varchar(20) NOT NULL,
    production_lot_id integer REFERENCES public.production_lots(id),
    supplier varchar(150),
    delivery_ref varchar(100),
    received_date date NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'a_controler',
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    controlled_by integer REFERENCES public.users(user_id),
    controlled_at timestamp,
    reject_reason text,
    CONSTRAINT stock_receipts_receipt_number_key UNIQUE (receipt_number),
    CONSTRAINT stock_receipts_origin_check
        CHECK (origin IN ('fabrication','fournisseur')),
    CONSTRAINT stock_receipts_status_check
        CHECK (status IN ('a_controler','valide','rejete')),
    CONSTRAINT stock_receipts_origin_lot_check CHECK (
        (origin = 'fabrication' AND production_lot_id IS NOT NULL) OR
        (origin = 'fournisseur' AND production_lot_id IS NULL))
);
CREATE INDEX idx_stock_receipts_status
    ON public.stock_receipts (status);

CREATE TABLE public.stock_receipt_lines (
    id serial PRIMARY KEY,
    receipt_id integer NOT NULL
        REFERENCES public.stock_receipts(id) ON DELETE CASCADE,
    product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
    qty_expected integer,
    qty_good integer NOT NULL DEFAULT 0,
    qty_damaged integer NOT NULL DEFAULT 0,
    qty_lost integer NOT NULL DEFAULT 0,
    qty_defective integer NOT NULL DEFAULT 0,
    lot_number varchar(30),
    expiry_date date,
    CONSTRAINT stock_receipt_lines_qty_good_check CHECK (qty_good >= 0),
    CONSTRAINT stock_receipt_lines_qty_damaged_check CHECK (qty_damaged >= 0),
    CONSTRAINT stock_receipt_lines_qty_lost_check CHECK (qty_lost >= 0),
    CONSTRAINT stock_receipt_lines_qty_defective_check CHECK (qty_defective >= 0)
);
CREATE INDEX idx_stock_receipt_lines_receipt
    ON public.stock_receipt_lines (receipt_id);

CREATE TABLE public.stock_incidents (
    id serial PRIMARY KEY,
    product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
    kind varchar(20) NOT NULL,
    quantity integer NOT NULL,
    reason text NOT NULL,
    incident_date date NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'a_controler',
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    controlled_by integer REFERENCES public.users(user_id),
    controlled_at timestamp,
    reject_reason text,
    CONSTRAINT stock_incidents_kind_check
        CHECK (kind IN ('endommage','perdu','defectueux')),
    CONSTRAINT stock_incidents_quantity_check CHECK (quantity > 0),
    CONSTRAINT stock_incidents_status_check
        CHECK (status IN ('a_controler','valide','rejete'))
);
CREATE INDEX idx_stock_incidents_status
    ON public.stock_incidents (status);

CREATE TABLE public.stock_adjustment_requests (
    id serial PRIMARY KEY,
    product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
    kind varchar(20) NOT NULL,
    quantity integer NOT NULL,
    reason text NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'en_attente',
    requested_by integer NOT NULL REFERENCES public.users(user_id),
    requested_at timestamp NOT NULL DEFAULT now(),
    decided_by integer REFERENCES public.users(user_id),
    decided_at timestamp,
    decision_note text,
    stock_before integer,
    stock_after integer,
    stock_at_request integer,
    CONSTRAINT stock_adjustment_requests_kind_check
        CHECK (kind IN ('reapprovisionnement','correction')),
    CONSTRAINT stock_adjustment_requests_quantity_check CHECK (quantity >= 0),
    CONSTRAINT stock_adjustment_requests_reappro_qty_check
        CHECK (kind <> 'reapprovisionnement' OR quantity > 0),
    CONSTRAINT stock_adjustment_requests_status_check
        CHECK (status IN ('en_attente','approuve','refuse','annule'))
);
CREATE INDEX idx_stock_adjustment_requests_status
    ON public.stock_adjustment_requests (status);

CREATE TABLE public.lab_stock_products (
    id serial PRIMARY KEY,
    name varchar(150) NOT NULL,
    packaging varchar(100),
    alert_threshold integer NOT NULL DEFAULT 0,
    supplier varchar(150),
    quantity integer NOT NULL DEFAULT 0,
    last_counted_at timestamp,
    is_active boolean NOT NULL DEFAULT true,
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT lab_stock_products_threshold_check CHECK (alert_threshold >= 0),
    CONSTRAINT lab_stock_products_quantity_check CHECK (quantity >= 0)
);
CREATE UNIQUE INDEX uq_lab_stock_products_name_active
    ON public.lab_stock_products (lower(name)) WHERE is_active;

CREATE TABLE public.lab_stock_receipts (
    id serial PRIMARY KEY,
    invoice_number varchar(100) NOT NULL,
    supplier varchar(150) NOT NULL,
    delivery_date date NOT NULL,
    total_amount numeric(10,2) NOT NULL DEFAULT 0,
    status varchar(20) NOT NULL DEFAULT 'valide',
    cancel_reason text,
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    cancelled_by integer REFERENCES public.users(user_id),
    cancelled_at timestamp,
    CONSTRAINT lab_stock_receipts_total_check CHECK (total_amount >= 0),
    CONSTRAINT lab_stock_receipts_status_check
        CHECK (status IN ('valide','annule'))
);
CREATE UNIQUE INDEX uq_lab_stock_receipts_supplier_invoice
    ON public.lab_stock_receipts (lower(supplier), lower(invoice_number))
    WHERE status = 'valide';

CREATE TABLE public.lab_stock_receipt_lines (
    id serial PRIMARY KEY,
    receipt_id integer NOT NULL
        REFERENCES public.lab_stock_receipts(id) ON DELETE CASCADE,
    product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
    ordered_qty integer,
    received_qty integer NOT NULL,
    unit_price numeric(10,2) NOT NULL DEFAULT 0,
    line_total numeric(10,2) NOT NULL DEFAULT 0,
    lot_number varchar(50) NOT NULL,
    expiry_date date NOT NULL,
    note text,
    CONSTRAINT lab_stock_receipt_lines_ordered_check
        CHECK (ordered_qty IS NULL OR ordered_qty >= 0),
    CONSTRAINT lab_stock_receipt_lines_received_check CHECK (received_qty > 0),
    CONSTRAINT lab_stock_receipt_lines_price_check CHECK (unit_price >= 0),
    CONSTRAINT lab_stock_receipt_lines_total_check CHECK (line_total >= 0)
);
CREATE INDEX idx_lab_stock_receipt_lines_receipt
    ON public.lab_stock_receipt_lines (receipt_id);

CREATE TABLE public.lab_stock_counts (
    id serial PRIMARY KEY,
    counted_by integer NOT NULL REFERENCES public.users(user_id),
    counted_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE public.lab_stock_count_lines (
    id serial PRIMARY KEY,
    count_id integer NOT NULL
        REFERENCES public.lab_stock_counts(id) ON DELETE CASCADE,
    product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
    previous_qty integer NOT NULL,
    counted_qty integer NOT NULL,
    CONSTRAINT lab_stock_count_lines_previous_check CHECK (previous_qty >= 0),
    CONSTRAINT lab_stock_count_lines_counted_check CHECK (counted_qty >= 0)
);
CREATE INDEX idx_lab_stock_count_lines_count
    ON public.lab_stock_count_lines (count_id);

CREATE TABLE public.lab_stock_movements (
    id serial PRIMARY KEY,
    product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
    change_qty integer NOT NULL,
    movement_type varchar(30) NOT NULL,
    ref_type varchar(30),
    ref_id integer,
    quantity_after integer NOT NULL,
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT lab_stock_movements_type_check
        CHECK (movement_type IN ('reception','comptage','annulation_reception')),
    CONSTRAINT lab_stock_movements_after_check CHECK (quantity_after >= 0)
);
CREATE INDEX idx_lab_stock_movements_product_date
    ON public.lab_stock_movements (product_id, created_at);

CREATE TABLE public.lab_stock_requests (
    id serial PRIMARY KEY,
    product_id integer NOT NULL REFERENCES public.lab_stock_products(id),
    origin varchar(20) NOT NULL,
    level varchar(20),
    status varchar(20) NOT NULL DEFAULT 'a_commander',
    requested_by integer REFERENCES public.users(user_id),
    ordered_by integer REFERENCES public.users(user_id),
    expected_date date,
    closed_by_receipt_id integer REFERENCES public.lab_stock_receipts(id),
    cancel_reason text,
    created_at timestamp NOT NULL DEFAULT now(),
    ordered_at timestamp,
    closed_at timestamp,
    CONSTRAINT lab_stock_requests_origin_check
        CHECK (origin IN ('signalement','seuil','peremption')),
    CONSTRAINT lab_stock_requests_level_check
        CHECK (level IS NULL OR level IN ('bientot_fini','fini')),
    CONSTRAINT lab_stock_requests_status_check
        CHECK (status IN ('a_commander','commande','recu','annule'))
);
CREATE UNIQUE INDEX uq_lab_stock_requests_open_product
    ON public.lab_stock_requests (product_id)
    WHERE status IN ('a_commander','commande');

CREATE INDEX idx_lab_stock_receipt_lines_product
    ON public.lab_stock_receipt_lines (product_id);
CREATE INDEX idx_lab_stock_receipts_delivery_date
    ON public.lab_stock_receipts (delivery_date);
CREATE INDEX idx_lab_stock_requests_status
    ON public.lab_stock_requests (status);
CREATE INDEX idx_lab_stock_requests_product
    ON public.lab_stock_requests (product_id);
CREATE INDEX idx_lab_stock_requests_closed_receipt
    ON public.lab_stock_requests (closed_by_receipt_id);
CREATE INDEX idx_lab_stock_count_lines_product
    ON public.lab_stock_count_lines (product_id);

CREATE TABLE public.toxico_stays (
    id serial PRIMARY KEY,
    dossier_id integer NOT NULL
        REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE,
    stay_number integer NOT NULL,
    admission_date date NOT NULL,
    psychologist_id integer REFERENCES public.users(user_id) ON DELETE SET NULL,
    substance varchar(100) NOT NULL,
    discharge_date date,
    discharge_reason varchar(20),
    discharge_note text,
    discharged_by integer REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT toxico_stays_number_check CHECK (stay_number >= 1),
    CONSTRAINT toxico_stays_reason_check
        CHECK (discharge_reason IS NULL
               OR discharge_reason IN ('guerison','abandon','exclusion','autre')),
    CONSTRAINT toxico_stays_discharge_consistency_check
        CHECK ((discharge_date IS NULL) = (discharge_reason IS NULL)),
    CONSTRAINT toxico_stays_dates_check
        CHECK (discharge_date IS NULL OR discharge_date >= admission_date),
    CONSTRAINT uq_toxico_stays_dossier_number UNIQUE (dossier_id, stay_number)
);
CREATE UNIQUE INDEX uq_toxico_stays_one_open
    ON public.toxico_stays (dossier_id) WHERE discharge_date IS NULL;
CREATE INDEX idx_toxico_stays_psychologist
    ON public.toxico_stays (psychologist_id);

ALTER TABLE public.toxico_phase_history
    ADD COLUMN stay_id integer REFERENCES public.toxico_stays(id);
ALTER TABLE public.toxico_evaluations
    ADD COLUMN stay_id integer REFERENCES public.toxico_stays(id);
CREATE INDEX idx_toxico_phase_history_stay
    ON public.toxico_phase_history (stay_id);
CREATE INDEX idx_toxico_evaluations_stay
    ON public.toxico_evaluations (stay_id);

CREATE TABLE public.fab_intrants (
    id serial PRIMARY KEY,
    name varchar(150) NOT NULL,
    unit varchar(20) NOT NULL,
    is_container boolean NOT NULL DEFAULT false,
    alert_threshold numeric(12,3) NOT NULL DEFAULT 0,
    is_active boolean NOT NULL DEFAULT true,
    CONSTRAINT fab_intrants_threshold_check CHECK (alert_threshold >= 0)
);

CREATE TABLE public.fab_intrant_purchases (
    id serial PRIMARY KEY,
    intrant_id integer NOT NULL REFERENCES public.fab_intrants(id),
    supplier varchar(150),
    delivery_ref varchar(100),
    purchase_date date NOT NULL,
    quantity numeric(12,3) NOT NULL,
    unit_cost numeric(12,2) NOT NULL,
    remaining_qty numeric(12,3) NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'actif',
    cancel_reason text,
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT fab_intrant_purchases_quantity_check CHECK (quantity > 0),
    CONSTRAINT fab_intrant_purchases_unit_cost_check CHECK (unit_cost >= 0),
    CONSTRAINT fab_intrant_purchases_remaining_check
        CHECK (remaining_qty >= 0 AND remaining_qty <= quantity),
    CONSTRAINT fab_intrant_purchases_status_check
        CHECK (status IN ('actif','annule'))
);
CREATE INDEX idx_fab_intrant_purchases_status
    ON public.fab_intrant_purchases (status);
CREATE INDEX idx_fab_intrant_purchases_intrant
    ON public.fab_intrant_purchases (intrant_id);

CREATE TABLE public.fab_batches (
    id serial PRIMARY KEY,
    batch_number varchar(30) NOT NULL,
    product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
    status varchar(20) NOT NULL DEFAULT 'brouillon',
    production_date date NOT NULL,
    producer_name varchar(150),
    qty_good integer NOT NULL DEFAULT 0,
    qty_damaged integer NOT NULL DEFAULT 0,
    qty_rejected integer NOT NULL DEFAULT 0,
    liquid_lost numeric(12,3) NOT NULL DEFAULT 0,
    expected_qty integer,
    found_qty integer,
    missing_qty integer,
    missing_pct numeric(6,2),
    tolerance_applied numeric(5,2),
    out_of_tolerance boolean NOT NULL DEFAULT false,
    justification text,
    total_cost numeric(12,2),
    unit_cost numeric(12,2),
    delivery_date date,
    expiry_date date,
    production_lot_id integer REFERENCES public.production_lots(id),
    cancel_reason text,
    created_by integer NOT NULL REFERENCES public.users(user_id),
    created_at timestamp NOT NULL DEFAULT now(),
    started_at timestamp,
    finished_at timestamp,
    expedited_at timestamp,
    expedited_by integer REFERENCES public.users(user_id),
    CONSTRAINT fab_batches_batch_number_key UNIQUE (batch_number),
    CONSTRAINT fab_batches_status_check
        CHECK (status IN ('brouillon','en_production','termine','expedie','annule')),
    CONSTRAINT fab_batches_qty_good_check CHECK (qty_good >= 0),
    CONSTRAINT fab_batches_qty_damaged_check CHECK (qty_damaged >= 0),
    CONSTRAINT fab_batches_qty_rejected_check CHECK (qty_rejected >= 0),
    CONSTRAINT fab_batches_liquid_lost_check CHECK (liquid_lost >= 0)
);
CREATE INDEX idx_fab_batches_status
    ON public.fab_batches (status);

CREATE TABLE public.fab_consumptions (
    id serial PRIMARY KEY,
    batch_id integer NOT NULL REFERENCES public.fab_batches(id),
    purchase_id integer NOT NULL REFERENCES public.fab_intrant_purchases(id),
    quantity numeric(12,3) NOT NULL,
    unit_cost_snapshot numeric(12,2),
    restored_at timestamp,
    CONSTRAINT fab_consumptions_quantity_check CHECK (quantity > 0),
    CONSTRAINT fab_consumptions_cost_check
        CHECK (unit_cost_snapshot IS NULL OR unit_cost_snapshot >= 0)
);
CREATE INDEX idx_fab_consumptions_batch
    ON public.fab_consumptions (batch_id);
CREATE INDEX idx_fab_consumptions_purchase
    ON public.fab_consumptions (purchase_id);

CREATE TABLE public.fab_settings (
    id integer PRIMARY KEY,
    tolerance_pct numeric(5,2) NOT NULL DEFAULT 2.00,
    stale_days integer NOT NULL DEFAULT 7,
    updated_by integer REFERENCES public.users(user_id),
    updated_at timestamp,
    CONSTRAINT fab_settings_single_row_check CHECK (id = 1),
    CONSTRAINT fab_settings_tolerance_check CHECK (tolerance_pct >= 0),
    CONSTRAINT fab_settings_stale_days_check CHECK (stale_days > 0)
);
INSERT INTO public.fab_settings (id, tolerance_pct, stale_days)
VALUES (1, 2.00, 7)
ON CONFLICT (id) DO NOTHING;

-- Migration 024: cloture de caisse (colonnes received_at, modes de paiement, clotures)
ALTER TABLE public.paiement_echelonne ADD COLUMN received_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.caisse_retrait ADD COLUMN received_at timestamptz NOT NULL DEFAULT now();
CREATE INDEX idx_paiement_echelonne_received_at
    ON public.paiement_echelonne (received_at);
CREATE INDEX idx_caisse_retrait_received_at
    ON public.caisse_retrait (received_at);

CREATE TABLE public.payment_modes (
    code varchar(30) PRIMARY KEY,
    label varchar(80) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    sort_order integer NOT NULL DEFAULT 0
);
INSERT INTO public.payment_modes (code, label, is_active, sort_order) VALUES
    ('especes', 'Especes', true, 1),
    ('orange_money', 'Orange Money', true, 2),
    ('mtn_money', 'MTN Money', true, 3),
    ('autre_mobile', 'Autre mobile', true, 4)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE public.cash_closures (
    id serial PRIMARY KEY,
    period_start timestamptz NOT NULL,
    period_end timestamptz NOT NULL,
    business_date date NOT NULL,
    kind varchar(10) NOT NULL,
    closed_by integer REFERENCES public.users(user_id),
    closed_at timestamptz NOT NULL DEFAULT now(),
    opening_cash numeric(14,2) NOT NULL DEFAULT 0,
    expected_cash numeric(14,2) NOT NULL DEFAULT 0,
    counted_cash numeric(14,2),
    difference numeric(14,2),
    opening_from_auto boolean NOT NULL DEFAULT false,
    comment text,
    unsynced_ignored boolean NOT NULL DEFAULT false,
    CONSTRAINT cash_closures_kind_check CHECK (kind IN ('manual','auto')),
    CONSTRAINT cash_closures_period_check CHECK (period_end > period_start),
    CONSTRAINT cash_closures_counted_check CHECK (counted_cash IS NULL OR counted_cash >= 0),
    CONSTRAINT cash_closures_opening_check CHECK (opening_cash >= 0),
    CONSTRAINT cash_closures_closed_by_check CHECK (kind = 'auto' OR closed_by IS NOT NULL),
    CONSTRAINT cash_closures_period_end_key UNIQUE (period_end)
);
CREATE INDEX idx_cash_closures_business_date
    ON public.cash_closures (business_date);

CREATE TABLE public.cash_closure_lines (
    id serial PRIMARY KEY,
    closure_id integer NOT NULL REFERENCES public.cash_closures(id),
    mode_code varchar(30) NOT NULL,
    source varchar(20) NOT NULL,
    opening numeric(14,2) NOT NULL DEFAULT 0,
    entries numeric(14,2) NOT NULL DEFAULT 0,
    exits numeric(14,2) NOT NULL DEFAULT 0,
    expected numeric(14,2) NOT NULL DEFAULT 0,
    counted numeric(14,2),
    difference numeric(14,2),
    comment text,
    CONSTRAINT cash_closure_lines_source_check
        CHECK (source IN ('physical','operator_statement')),
    CONSTRAINT cash_closure_lines_counted_check CHECK (counted IS NULL OR counted >= 0),
    CONSTRAINT cash_closure_lines_closure_mode_key UNIQUE (closure_id, mode_code)
);
CREATE INDEX idx_cash_closure_lines_closure
    ON public.cash_closure_lines (closure_id);

CREATE TABLE public.cash_closure_corrections (
    id serial PRIMARY KEY,
    closure_id integer NOT NULL REFERENCES public.cash_closures(id),
    mode_code varchar(30) NOT NULL,
    amount_delta numeric(14,2) NOT NULL,
    reason text NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'pending',
    requested_by integer NOT NULL REFERENCES public.users(user_id),
    requested_at timestamptz NOT NULL DEFAULT now(),
    decided_by integer REFERENCES public.users(user_id),
    decided_at timestamptz,
    CONSTRAINT cash_closure_corrections_status_check
        CHECK (status IN ('pending','approved','rejected')),
    CONSTRAINT cash_closure_corrections_reason_check CHECK (length(btrim(reason)) > 0)
);
CREATE INDEX idx_cash_closure_corrections_closure
    ON public.cash_closure_corrections (closure_id);

CREATE TABLE public.cash_closure_start (
    id smallint PRIMARY KEY,
    started_at timestamptz NOT NULL,
    opening_cash numeric(14,2) NOT NULL,
    set_by integer REFERENCES public.users(user_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT cash_closure_start_single_row_check CHECK (id = 1),
    CONSTRAINT cash_closure_start_opening_check CHECK (opening_cash >= 0)
);

CREATE OR REPLACE FUNCTION public.cash_closure_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'cash closure records are immutable (table %, operation %)',
        TG_TABLE_NAME, TG_OP USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cash_closures_immutable ON public.cash_closures;
CREATE TRIGGER trg_cash_closures_immutable
    BEFORE UPDATE OR DELETE ON public.cash_closures
    FOR EACH ROW EXECUTE FUNCTION public.cash_closure_immutable();
DROP TRIGGER IF EXISTS trg_cash_closure_lines_immutable ON public.cash_closure_lines;
CREATE TRIGGER trg_cash_closure_lines_immutable
    BEFORE UPDATE OR DELETE ON public.cash_closure_lines
    FOR EACH ROW EXECUTE FUNCTION public.cash_closure_immutable();
DROP TRIGGER IF EXISTS trg_cash_closure_start_immutable ON public.cash_closure_start;
CREATE TRIGGER trg_cash_closure_start_immutable
    BEFORE UPDATE OR DELETE ON public.cash_closure_start
    FOR EACH ROW EXECUTE FUNCTION public.cash_closure_immutable();

-- Migration 025: sorties declarees de fabrication
CREATE TABLE public.fab_batch_outputs (
    id serial PRIMARY KEY,
    batch_id integer NOT NULL REFERENCES public.fab_batches(id),
    reason varchar(20) NOT NULL,
    quantity integer NOT NULL,
    note text,
    status varchar(20) NOT NULL DEFAULT 'active',
    declared_by integer NOT NULL REFERENCES public.users(user_id),
    declared_at timestamp NOT NULL DEFAULT now(),
    cancelled_by integer REFERENCES public.users(user_id),
    cancelled_at timestamp,
    cancel_reason text,
    CONSTRAINT fab_batch_outputs_quantity_check CHECK (quantity > 0),
    CONSTRAINT fab_batch_outputs_reason_check
        CHECK (reason IN ('echantillon','autre')),
    CONSTRAINT fab_batch_outputs_status_check
        CHECK (status IN ('active','annulee')),
    CONSTRAINT fab_batch_outputs_autre_note_check
        CHECK (reason <> 'autre' OR length(trim(coalesce(note,''))) > 0),
    CONSTRAINT fab_batch_outputs_cancel_check
        CHECK (status <> 'annulee'
               OR (cancelled_by IS NOT NULL
                   AND length(trim(coalesce(cancel_reason,''))) > 0))
);
CREATE INDEX idx_fab_batch_outputs_batch
    ON public.fab_batch_outputs (batch_id);
CREATE INDEX idx_fab_batch_outputs_status
    ON public.fab_batch_outputs (status);

CREATE TABLE public.stock_counts (
    id serial PRIMARY KEY,
    status varchar(20) NOT NULL DEFAULT 'en_cours',
    started_by integer NOT NULL REFERENCES public.users(user_id),
    started_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    submitted_at timestamp,
    scope varchar(20) NOT NULL DEFAULT 'tous',
    CONSTRAINT stock_counts_status_check CHECK (status IN ('en_cours','valide','abandonne')),
    CONSTRAINT stock_counts_scope_check CHECK (scope IN ('tous','selection'))
);
CREATE UNIQUE INDEX uq_stock_counts_one_open_per_user
    ON public.stock_counts (started_by) WHERE status = 'en_cours';
CREATE INDEX idx_stock_counts_status
    ON public.stock_counts (status);

CREATE TABLE public.stock_count_lines (
    id serial PRIMARY KEY,
    count_id integer NOT NULL REFERENCES public.stock_counts(id) ON DELETE CASCADE,
    product_id integer NOT NULL REFERENCES public.pharmacy(medication_id),
    counted_qty integer NOT NULL,
    previous_qty integer NOT NULL,
    difference integer NOT NULL,
    observation text,
    movements_during integer NOT NULL DEFAULT 0,
    adjustment_request_id integer REFERENCES public.stock_adjustment_requests(id),
    CONSTRAINT stock_count_lines_counted_check CHECK (counted_qty >= 0),
    CONSTRAINT stock_count_lines_previous_check CHECK (previous_qty >= 0),
    CONSTRAINT stock_count_lines_movements_check CHECK (movements_during >= 0),
    CONSTRAINT stock_count_lines_count_product_key UNIQUE (count_id, product_id)
);
CREATE INDEX idx_stock_count_lines_count
    ON public.stock_count_lines (count_id);

CREATE TABLE public.stock_count_settings (
    id smallint PRIMARY KEY,
    interval_days integer NOT NULL DEFAULT 30,
    updated_by integer REFERENCES public.users(user_id),
    updated_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT stock_count_settings_single_row_check CHECK (id = 1),
    CONSTRAINT stock_count_settings_interval_check CHECK (interval_days BETWEEN 1 AND 365)
);
INSERT INTO public.stock_count_settings (id, interval_days) VALUES (1, 30)
ON CONFLICT (id) DO NOTHING;

CREATE OR REPLACE FUNCTION public.stock_count_lines_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'stock count lines are immutable (operation %)', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.stock_counts_final_immutable() RETURNS trigger AS $$
BEGIN
    IF OLD.status IN ('valide','abandonne') THEN
        RAISE EXCEPTION 'a closed stock count is immutable (status %, operation %)',
            OLD.status, TG_OP USING ERRCODE = 'restrict_violation';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_stock_count_lines_immutable ON public.stock_count_lines;
CREATE TRIGGER trg_stock_count_lines_immutable
    BEFORE UPDATE OR DELETE ON public.stock_count_lines
    FOR EACH ROW EXECUTE FUNCTION public.stock_count_lines_immutable();
DROP TRIGGER IF EXISTS trg_stock_counts_final_immutable ON public.stock_counts;
CREATE TRIGGER trg_stock_counts_final_immutable
    BEFORE UPDATE OR DELETE ON public.stock_counts
    FOR EACH ROW EXECUTE FUNCTION public.stock_counts_final_immutable();

-- 027_stock_count_line_times : heure de comptage par ligne et mouvements nets apres comptage
ALTER TABLE public.stock_count_lines ADD COLUMN IF NOT EXISTS counted_at timestamp NOT NULL;
ALTER TABLE public.stock_count_lines ADD COLUMN IF NOT EXISTS movements_net integer NOT NULL DEFAULT 0;

-- 028_reports_control : controle quotidien (anomalies du jour) et seuils des rapports
CREATE TABLE public.daily_controls (
    id serial PRIMARY KEY,
    business_date date NOT NULL,
    anomalies jsonb NOT NULL DEFAULT '[]'::jsonb,
    new_count integer NOT NULL DEFAULT 0,
    open_count integer NOT NULL DEFAULT 0,
    computed_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    notified_at timestamp,
    reminder_sent_at timestamp,
    recomputed boolean NOT NULL DEFAULT false,
    CONSTRAINT daily_controls_business_date_key UNIQUE (business_date),
    CONSTRAINT daily_controls_anomalies_array_check CHECK (jsonb_typeof(anomalies) = 'array'),
    CONSTRAINT daily_controls_new_count_check CHECK (new_count >= 0),
    CONSTRAINT daily_controls_open_count_check CHECK (open_count >= 0)
);
CREATE INDEX idx_daily_controls_business_date
    ON public.daily_controls (business_date);

CREATE TABLE public.report_settings (
    id smallint PRIMARY KEY,
    cancelled_sales_threshold integer NOT NULL DEFAULT 3,
    adjustment_pending_days integer NOT NULL DEFAULT 3,
    updated_by integer REFERENCES public.users(user_id),
    updated_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    CONSTRAINT report_settings_single_row_check CHECK (id = 1),
    CONSTRAINT report_settings_cancelled_threshold_check
        CHECK (cancelled_sales_threshold BETWEEN 1 AND 1000),
    CONSTRAINT report_settings_adjustment_days_check
        CHECK (adjustment_pending_days BETWEEN 1 AND 365)
);
INSERT INTO public.report_settings (id, cancelled_sales_threshold, adjustment_pending_days)
VALUES (1, 3, 3)
ON CONFLICT (id) DO NOTHING;

-- 029_daily_control_notify : decision d'envoi stockee avec l'instantane
ALTER TABLE public.daily_controls ADD COLUMN notify_reason text;
ALTER TABLE public.daily_controls ADD COLUMN notify_new_count integer NOT NULL DEFAULT 0;
ALTER TABLE public.daily_controls ADD COLUMN notify_open_count integer NOT NULL DEFAULT 0;
ALTER TABLE public.daily_controls ADD CONSTRAINT daily_controls_notify_reason_check
    CHECK (notify_reason IN ('nouveau', 'rappel'));

-- 030_lab_amend_invoice_link : correction tracee d'un resultat valide + lien facture -> dossier labo
ALTER TABLE public.lab_results ADD COLUMN corrected boolean NOT NULL DEFAULT false;
ALTER TABLE public.lab_results ADD COLUMN corrected_at timestamp;
ALTER TABLE public.lab_results ADD COLUMN origin_caisse_item_id integer
    REFERENCES public.caisse_item(item_id) ON DELETE SET NULL;
CREATE UNIQUE INDEX uq_lab_results_origin_caisse_item
    ON public.lab_results (origin_caisse_item_id) WHERE origin_caisse_item_id IS NOT NULL;

CREATE TABLE public.lab_result_amendments (
    amendment_id serial PRIMARY KEY,
    result_id integer NOT NULL REFERENCES public.lab_results(result_id) ON DELETE CASCADE,
    amended_by integer,
    amended_by_name text,
    amended_at timestamp NOT NULL DEFAULT (now() AT TIME ZONE 'Africa/Douala'),
    reason text NOT NULL,
    previous_values jsonb NOT NULL DEFAULT '[]'::jsonb,
    previous_note text,
    CONSTRAINT lab_result_amendments_reason_check CHECK (length(btrim(reason)) > 0)
);
CREATE INDEX idx_lab_result_amendments_result
    ON public.lab_result_amendments (result_id);

ALTER TABLE public.parametres ADD COLUMN ordre integer NOT NULL DEFAULT 0;

ALTER TABLE public.users ADD COLUMN sees_own_toxico_only boolean DEFAULT false NOT NULL;

ALTER TABLE public.users ADD COLUMN is_head_lab boolean DEFAULT false NOT NULL;

CREATE TABLE public.toxico_psychologist_transfers (
    id serial PRIMARY KEY,
    dossier_id integer NOT NULL REFERENCES public.toxico_dossiers(id) ON DELETE CASCADE,
    from_psychologist_id integer REFERENCES public.users(user_id),
    to_psychologist_id integer NOT NULL REFERENCES public.users(user_id),
    decided_by integer NOT NULL REFERENCES public.users(user_id),
    decided_at timestamp without time zone NOT NULL,
    reason text NOT NULL,
    stay_id integer REFERENCES public.toxico_stays(id) ON DELETE SET NULL,
    CONSTRAINT toxico_transfers_reason_check CHECK (length(btrim(reason)) > 0),
    CONSTRAINT toxico_transfers_distinct_check CHECK (from_psychologist_id IS DISTINCT FROM to_psychologist_id)
);
CREATE INDEX idx_toxico_transfers_dossier ON public.toxico_psychologist_transfers (dossier_id);
CREATE INDEX idx_toxico_transfers_from ON public.toxico_psychologist_transfers (from_psychologist_id);
CREATE INDEX idx_toxico_transfers_to ON public.toxico_psychologist_transfers (to_psychologist_id);

CREATE SEQUENCE public.pharmacy_barcode_seq START WITH 10000000 MINVALUE 10000000 MAXVALUE 19999999 NO CYCLE;
ALTER TABLE public.pharmacy ADD COLUMN barcode varchar(12) NOT NULL DEFAULT nextval('public.pharmacy_barcode_seq')::text;
ALTER TABLE public.pharmacy ADD CONSTRAINT pharmacy_barcode_key UNIQUE (barcode);

ALTER TABLE public.pharmacy ADD COLUMN photo_path varchar(255);
ALTER TABLE public.pharmacy ADD COLUMN photo_version integer NOT NULL DEFAULT 0;
ALTER TABLE public.organization_config ADD COLUMN label_width_mm integer NOT NULL DEFAULT 50;
ALTER TABLE public.organization_config ADD COLUMN label_height_mm integer NOT NULL DEFAULT 30;

CREATE TABLE public.spiritual_notes (
    id serial PRIMARY KEY,
    author_id integer NOT NULL REFERENCES public.users(user_id),
    meeting_date date NOT NULL,
    counsel boolean NOT NULL DEFAULT false,
    prayer boolean NOT NULL DEFAULT false,
    verse_read boolean NOT NULL DEFAULT false,
    discussion boolean NOT NULL DEFAULT false,
    text_given boolean NOT NULL DEFAULT false,
    qa boolean NOT NULL DEFAULT false,
    verse_reference varchar(120),
    no_one_spoke boolean NOT NULL DEFAULT false,
    content text,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT spiritual_notes_content_len_check
        CHECK (content IS NULL OR char_length(content) <= 5000)
);
CREATE INDEX idx_spiritual_notes_order
    ON public.spiritual_notes (meeting_date DESC, created_at DESC, id DESC);
CREATE INDEX idx_spiritual_notes_author ON public.spiritual_notes (author_id);

CREATE TABLE public.lab_external_prescribers (
    id serial PRIMARY KEY,
    title varchar(20) NOT NULL,
    name varchar(80) NOT NULL DEFAULT '',
    last_used_at timestamp NOT NULL DEFAULT now(),
    CONSTRAINT lab_external_prescribers_title_check
        CHECK (title IN ('Dr', 'I.D.E.', 'Fr', 'Br', 'M.', 'Mme', 'Volontaire', 'Autre'))
);
CREATE UNIQUE INDEX uq_lab_external_prescribers_title_name
    ON public.lab_external_prescribers (title, lower(name));
CREATE INDEX idx_lab_external_prescribers_recent
    ON public.lab_external_prescribers (last_used_at DESC);

CREATE TABLE public.lab_dossier_days (
    year integer NOT NULL,
    day date NOT NULL,
    counter integer NOT NULL CHECK (counter >= 1),
    PRIMARY KEY (year, day),
    CONSTRAINT uq_lab_dossier_days_counter UNIQUE (year, counter),
    CONSTRAINT uq_lab_dossier_days_counter_day UNIQUE (year, counter, day)
);
CREATE TABLE public.lab_dossier_ranks (
    year integer NOT NULL,
    counter integer NOT NULL,
    rank integer NOT NULL CHECK (rank >= 1),
    patient_key text NOT NULL,
    day date NOT NULL,
    PRIMARY KEY (year, counter, rank),
    CONSTRAINT uq_lab_dossier_ranks_patient_day UNIQUE (year, day, patient_key),
    CONSTRAINT fk_lab_dossier_ranks_day FOREIGN KEY (year, counter)
        REFERENCES public.lab_dossier_days (year, counter),
    CONSTRAINT fk_lab_dossier_ranks_counter_day FOREIGN KEY (year, counter, day)
        REFERENCES public.lab_dossier_days (year, counter, day)
);
ALTER TABLE public.lab_results ADD COLUMN dossier_year integer;
ALTER TABLE public.lab_results ADD COLUMN dossier_counter integer;
ALTER TABLE public.lab_results ADD COLUMN dossier_rank integer;
ALTER TABLE public.lab_results ADD COLUMN patient_key text;
ALTER TABLE public.lab_results ADD CONSTRAINT fk_lab_results_dossier
    FOREIGN KEY (dossier_year, dossier_counter, dossier_rank)
    REFERENCES public.lab_dossier_ranks (year, counter, rank);
ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_dossier_all_or_none
    CHECK ((dossier_year IS NULL) = (dossier_counter IS NULL)
       AND (dossier_year IS NULL) = (dossier_rank IS NULL));
CREATE INDEX idx_lab_results_dossier
    ON public.lab_results (dossier_year, dossier_counter, dossier_rank);

ALTER TABLE public.patients ADD COLUMN pregnancy_status varchar(20) NOT NULL DEFAULT 'inconnu';
ALTER TABLE public.patients ADD COLUMN expected_delivery_date date;
ALTER TABLE public.patients ADD COLUMN pregnancy_program_number varchar(50);
ALTER TABLE public.patients ADD CONSTRAINT ck_patients_pregnancy_status
    CHECK (pregnancy_status IN ('enceinte', 'non_enceinte', 'inconnu'));
ALTER TABLE public.lab_results ADD COLUMN gestational_age_weeks smallint;
ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_gestational_age_weeks
    CHECK (gestational_age_weeks IS NULL OR gestational_age_weeks BETWEEN 0 AND 45);

ALTER TABLE public.reference_ranges ADD COLUMN age_min_days integer;
ALTER TABLE public.reference_ranges ADD COLUMN age_max_days integer;
ALTER TABLE public.reference_ranges ADD COLUMN ga_min_weeks smallint;
ALTER TABLE public.reference_ranges ADD COLUMN ga_max_weeks smallint;
UPDATE public.reference_ranges
   SET age_min_days = age_min * 365, age_max_days = (age_max + 1) * 365 - 1;
ALTER TABLE public.reference_ranges ALTER COLUMN age_min DROP NOT NULL;
ALTER TABLE public.reference_ranges ALTER COLUMN age_max DROP NOT NULL;
ALTER TABLE public.reference_ranges ADD CONSTRAINT ck_reference_ranges_ga_weeks
    CHECK ((ga_min_weeks IS NULL OR ga_min_weeks BETWEEN 0 AND 45)
       AND (ga_max_weeks IS NULL OR ga_max_weeks BETWEEN 0 AND 45)
       AND (ga_min_weeks IS NULL OR ga_max_weeks IS NULL OR ga_min_weeks <= ga_max_weeks));
ALTER TABLE public.reference_ranges ADD CONSTRAINT ck_reference_ranges_age_days
    CHECK ((age_min_days IS NULL OR age_min_days >= 0)
       AND (age_max_days IS NULL OR age_max_days >= 0)
       AND (age_min_days IS NULL OR age_max_days IS NULL OR age_min_days <= age_max_days));

ALTER TABLE public.examens ADD COLUMN section text;
ALTER TABLE public.examens ADD COLUMN method text;
ALTER TABLE public.examens ADD COLUMN layout_family varchar(20) NOT NULL DEFAULT 'label_value';
ALTER TABLE public.examens ADD COLUMN signature_label text;
ALTER TABLE public.examens ADD COLUMN print_title text;
ALTER TABLE public.examens ADD COLUMN sort_order integer NOT NULL DEFAULT 0;
ALTER TABLE public.examens ADD COLUMN is_active boolean NOT NULL DEFAULT true;
ALTER TABLE public.examens ADD CONSTRAINT ck_examens_layout_family
    CHECK (layout_family IN ('table', 'three_columns', 'label_value', 'narrative', 'boxed'));
ALTER TABLE public.parametres ADD COLUMN print_label text;
ALTER TABLE public.parametres ADD COLUMN result_kind varchar(10) NOT NULL DEFAULT 'numeric';
ALTER TABLE public.parametres ADD COLUMN choices jsonb;
ALTER TABLE public.parametres ADD COLUMN is_active boolean NOT NULL DEFAULT true;
ALTER TABLE public.parametres ADD CONSTRAINT ck_parametres_result_kind
    CHECK (result_kind IN ('numeric', 'text', 'choice', 'pos_neg'));
ALTER TABLE public.organization_config ADD COLUMN agrement_number varchar(200);
ALTER TABLE public.organization_config ADD COLUMN footer_text text;
ALTER TABLE public.organization_config ADD COLUMN signature_label_default varchar(120);

ALTER TABLE public.lab_results ADD COLUMN external_pregnancy_info jsonb;
ALTER TABLE public.lab_results ADD COLUMN pregnancy_status_at_result text;
ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_pregnancy_status_at_result
    CHECK (pregnancy_status_at_result IS NULL
           OR pregnancy_status_at_result IN ('enceinte', 'non_enceinte', 'inconnu'));
ALTER TABLE public.lab_results ADD COLUMN print_snapshot jsonb;
ALTER TABLE public.lab_results ADD COLUMN print_snapshot_at timestamp without time zone;
ALTER TABLE public.lab_results ADD COLUMN print_snapshot_by integer;
ALTER TABLE public.lab_results ADD COLUMN print_snapshot_history jsonb;
ALTER TABLE public.lab_results ADD COLUMN conclusion text;
ALTER TABLE public.lab_results ADD CONSTRAINT ck_lab_results_conclusion_length
    CHECK (conclusion IS NULL OR length(conclusion) <= 5000);
ALTER TABLE public.parametres ADD COLUMN group_label text;
ALTER TABLE public.parametres ADD COLUMN norm_text text;
ALTER TABLE public.reference_ranges ADD COLUMN display_text text;
ALTER TABLE public.examens ADD COLUMN fixed_notes jsonb;
ALTER TABLE public.parametres ADD CONSTRAINT ck_parametres_group_label_length
    CHECK (group_label IS NULL OR length(group_label) <= 80);
ALTER TABLE public.parametres ADD CONSTRAINT ck_parametres_norm_text_length
    CHECK (norm_text IS NULL OR length(norm_text) <= 200);
ALTER TABLE public.reference_ranges ADD CONSTRAINT ck_reference_ranges_display_text_length
    CHECK (display_text IS NULL OR length(display_text) <= 60);
ALTER TABLE public.examens ADD CONSTRAINT ck_examens_fixed_notes_array
    CHECK (fixed_notes IS NULL OR jsonb_typeof(fixed_notes) = 'array');
ALTER TABLE public.organization_config ADD COLUMN lab_sheet_title_variant varchar(20) NOT NULL DEFAULT 'centered_results';
ALTER TABLE public.organization_config ADD CONSTRAINT ck_organization_config_lab_sheet_variant
    CHECK (lab_sheet_title_variant IN ('centered_results', 'left_laboratory'));

--
-- Name: powersync; Type: PUBLICATION; Schema: -; Owner: -
--

CREATE PUBLICATION powersync FOR ALL TABLES WITH (publish = 'insert, update, delete, truncate');


--
-- PostgreSQL database dump complete
--

