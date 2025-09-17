-- ===========================
-- SCHEMA OFFLINE SQLITE (SIH)
-- Version: sync-ready (UUID + queue + meta)
-- ===========================

PRAGMA foreign_keys = ON;

-- ---------- Roles ----------
CREATE TABLE IF NOT EXISTS application_roles (
    role_id    INTEGER PRIMARY KEY,
    role_name  TEXT NOT NULL UNIQUE
);

-- Pré-remplir rôles (exemples basés sur ta BD)
INSERT OR IGNORE INTO application_roles (role_id, role_name) VALUES
 (1, 'admin'),
 (2, 'personnel_medical'),
 (3, 'medecin'),
 (4, 'infirmier'),
 (5, 'secretaire'),
 (6, 'laborantin'),
 (7, 'pharmacien');

-- ---------- Devices (pour sync) ----------
CREATE TABLE IF NOT EXISTS devices (
    device_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    device_uuid    TEXT NOT NULL UNIQUE,         -- identifiant du poste/client
    name           TEXT,
    last_seen_at   DATETIME,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------- Core tables (avec meta sync) ----------
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid           TEXT UNIQUE,                  -- mappage entre server et local
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    full_name      TEXT,
    postgres_role  TEXT,
    is_active      INTEGER DEFAULT 1,
    specialty_id   INTEGER,
    role_id        INTEGER REFERENCES application_roles(role_id) ON DELETE SET NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified  DATETIME DEFAULT CURRENT_TIMESTAMP,
    revision       INTEGER DEFAULT 1,
    sync_status    TEXT DEFAULT 'created'        -- created | updated | deleted | synced
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

CREATE TABLE IF NOT EXISTS patients (
    patient_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid           TEXT UNIQUE,
    code_patient   TEXT UNIQUE,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    birth_date     DATE,
    gender         TEXT,
    national_id    TEXT UNIQUE,
    contact_phone  TEXT,
    assurance      TEXT,
    residence      TEXT,
    father_name    TEXT,
    mother_name    TEXT,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified  DATETIME DEFAULT CURRENT_TIMESTAMP,
    revision       INTEGER DEFAULT 1,
    sync_status    TEXT DEFAULT 'created'
);

CREATE INDEX IF NOT EXISTS idx_patients_code ON patients(code_patient);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid           TEXT UNIQUE,
    patient_id     INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    doctor_id        INTEGER NOT NULL REFERENCES users(user_id) ON DELETE SET NULL,
    specialty      TEXT,
    appointment_date DATETIME NOT NULL,
    appointment_time TEXT,
    reason         TEXT,
    status         TEXT DEFAULT 'pending',
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified  DATETIME DEFAULT CURRENT_TIMESTAMP,
    revision       INTEGER DEFAULT 1,
    sync_status    TEXT DEFAULT 'created'
);

CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);

CREATE TABLE IF NOT EXISTS medical_records (
    record_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid           TEXT UNIQUE,
    patient_id     INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    appointment_id INTEGER REFERENCES appointments(appointment_id) ON DELETE SET NULL,
    consultation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    marital_status TEXT,
    bp             TEXT,
    temperature    NUMERIC,
    weight         NUMERIC,
    height         NUMERIC,
    medical_history TEXT,
    allergies      TEXT,
    symptoms       TEXT,
    diagnosis      TEXT,
    treatment      TEXT,
    severity       TEXT,
    notes          TEXT,
    motif_code     TEXT,
    created_by     INTEGER REFERENCES users(user_id),
    created_by_name TEXT,
    last_updated_by INTEGER REFERENCES users(user_id),
    last_updated_by_name TEXT,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified  DATETIME DEFAULT CURRENT_TIMESTAMP,
    revision       INTEGER DEFAULT 1,
    sync_status    TEXT DEFAULT 'created'
);

CREATE INDEX IF NOT EXISTS idx_medical_records_patient ON medical_records(patient_id);

CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid            TEXT UNIQUE,
    patient_id      INTEGER REFERENCES patients(patient_id) ON DELETE CASCADE,
    medical_record_id INTEGER REFERENCES medical_records(record_id) ON DELETE SET NULL,
    medication      TEXT NOT NULL,
    dosage          TEXT,
    frequency       TEXT,
    duration        TEXT,
    start_date      DATE,
    end_date        DATE,
    notes           TEXT,
    status          TEXT DEFAULT 'active',
    prescribed_by   INTEGER REFERENCES users(user_id),
    prescribed_by_name TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified   DATETIME DEFAULT CURRENT_TIMESTAMP,
    revision        INTEGER DEFAULT 1,
    sync_status     TEXT DEFAULT 'created'
);

CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id);

-- Table des spécialités médicales (équivalent Postgres)
CREATE TABLE IF NOT EXISTS medical_specialties (
    specialty_id INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_medical_specialties_name ON medical_specialties(name);


-- ---------- Audit / Logs ----------
CREATE TABLE IF NOT EXISTS audit_user_actions (
    action_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name      TEXT,
    action         TEXT,
    patient_id     INTEGER,
    action_time    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------- SYNC INFRA (queue + conflicts) ----------
CREATE TABLE IF NOT EXISTS sync_queue (
    change_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    change_uuid    TEXT UNIQUE,                    -- uuid côté device pour retrouver la modification
    device_uuid    TEXT,                           -- device that made change
    table_name     TEXT NOT NULL,
    row_id         INTEGER,                        -- integer PK local
    row_uuid       TEXT,                           -- uuid of row if present
    operation      TEXT NOT NULL,                  -- INSERT | UPDATE | DELETE
    payload        TEXT,                           -- optional JSON payload string (app can generate)
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    attempted_at   DATETIME,
    synced         INTEGER DEFAULT 0,              -- 0 = not yet, 1 = synced to server
    retry_count    INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sync_queue_table ON sync_queue(table_name);

CREATE TABLE IF NOT EXISTS sync_conflicts (
    conflict_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name     TEXT,
    row_id         INTEGER,
    row_uuid       TEXT,
    server_payload TEXT,
    local_payload  TEXT,
    detected_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved       INTEGER DEFAULT 0,
    resolution     TEXT
);

-- ---------- VUES SIMPLIFIÉES ----------
CREATE VIEW IF NOT EXISTS vue_consultation AS
SELECT 
    mr.record_id,
    COALESCE(p.first_name,'') || ' ' || COALESCE(p.last_name,'') AS patient_name,
    a.appointment_date,
    u.full_name AS doctor_name,
    mr.diagnosis,
    mr.notes
FROM medical_records mr
LEFT JOIN patients p ON mr.patient_id = p.patient_id
LEFT JOIN appointments a ON mr.appointment_id = a.appointment_id
LEFT JOIN users u ON a.user_id = u.user_id;

CREATE VIEW IF NOT EXISTS vue_appointment AS
SELECT 
    a.appointment_id,
    COALESCE(p.first_name,'') || ' ' || COALESCE(p.last_name,'') AS patient_name,
    u.full_name AS doctor_name,
    a.appointment_date,
    a.status
FROM appointments a
LEFT JOIN patients p ON a.patient_id = p.patient_id
LEFT JOIN users u ON a.user_id = u.user_id;

-- ---------- TRIGGERS: update timestamps + push into sync_queue ----------
-- generic helper trigger function isn't available in SQLite; create per table

-- USERS: on update -> bump updated_at, last_modified, revision and queue
CREATE TRIGGER IF NOT EXISTS trg_users_update
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP, last_modified = CURRENT_TIMESTAMP, revision = NEW.revision + 1 WHERE user_id = OLD.user_id;
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('users', OLD.user_id, NEW.uuid, 'UPDATE', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_users_insert
AFTER INSERT ON users
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('users', NEW.user_id, NEW.uuid, 'INSERT', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_users_delete
AFTER DELETE ON users
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('users', OLD.user_id, OLD.uuid, 'DELETE', NULL, NULL);
END;

-- PATIENTS
CREATE TRIGGER IF NOT EXISTS trg_patients_update
AFTER UPDATE ON patients
BEGIN
    UPDATE patients SET last_updated_at = CURRENT_TIMESTAMP, last_modified = CURRENT_TIMESTAMP, revision = NEW.revision + 1 WHERE patient_id = OLD.patient_id;
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('patients', OLD.patient_id, NEW.uuid, 'UPDATE', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_patients_insert
AFTER INSERT ON patients
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('patients', NEW.patient_id, NEW.uuid, 'INSERT', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_patients_delete
AFTER DELETE ON patients
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('patients', OLD.patient_id, OLD.uuid, 'DELETE', NULL, NULL);
END;

-- APPOINTMENTS
CREATE TRIGGER IF NOT EXISTS trg_appointments_insert
AFTER INSERT ON appointments
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('appointments', NEW.appointment_id, NEW.uuid, 'INSERT', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_appointments_update
AFTER UPDATE ON appointments
BEGIN
    UPDATE appointments SET updated_at = CURRENT_TIMESTAMP, last_modified = CURRENT_TIMESTAMP, revision = NEW.revision + 1 WHERE appointment_id = OLD.appointment_id;
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('appointments', OLD.appointment_id, NEW.uuid, 'UPDATE', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_appointments_delete
AFTER DELETE ON appointments
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('appointments', OLD.appointment_id, OLD.uuid, 'DELETE', NULL, NULL);
END;

-- MEDICAL_RECORDS
CREATE TRIGGER IF NOT EXISTS trg_medical_records_insert
AFTER INSERT ON medical_records
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('medical_records', NEW.record_id, NEW.uuid, 'INSERT', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_medical_records_update
AFTER UPDATE ON medical_records
BEGIN
    UPDATE medical_records SET updated_at = CURRENT_TIMESTAMP, last_modified = CURRENT_TIMESTAMP, revision = NEW.revision + 1 WHERE record_id = OLD.record_id;
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('medical_records', OLD.record_id, NEW.uuid, 'UPDATE', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_medical_records_delete
AFTER DELETE ON medical_records
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('medical_records', OLD.record_id, OLD.uuid, 'DELETE', NULL, NULL);
END;

-- PRESCRIPTIONS
CREATE TRIGGER IF NOT EXISTS trg_prescriptions_insert
AFTER INSERT ON prescriptions
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('prescriptions', NEW.prescription_id, NEW.uuid, 'INSERT', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_prescriptions_update
AFTER UPDATE ON prescriptions
BEGIN
    UPDATE prescriptions SET last_modified = CURRENT_TIMESTAMP, revision = NEW.revision + 1 WHERE prescription_id = OLD.prescription_id;
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('prescriptions', OLD.prescription_id, NEW.uuid, 'UPDATE', NULL, NULL);
END;

CREATE TRIGGER IF NOT EXISTS trg_prescriptions_delete
AFTER DELETE ON prescriptions
BEGIN
    INSERT INTO sync_queue(table_name, row_id, row_uuid, operation, payload, device_uuid)
    VALUES ('prescriptions', OLD.prescription_id, OLD.uuid, 'DELETE', NULL, NULL);
END;

-- final pragma (safe): ensure foreign keys on
PRAGMA foreign_keys = ON;


