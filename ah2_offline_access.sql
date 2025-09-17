-- ===========================
-- SCHEMA OFFLINE SQLITE (SIH)
-- ===========================

-- Table des utilisateurs
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,        -- médecin, infirmier, secrétaire, admin, etc.
    full_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table des patients
CREATE TABLE patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth DATE,
    gender TEXT,
    phone TEXT,
    address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table des rendez-vous
CREATE TABLE appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,   -- médecin/infirmier assigné
    appointment_date DATETIME NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Table des dossiers médicaux
CREATE TABLE medical_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    appointment_id INTEGER,
    diagnosis TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
);

-- Table des prescriptions
CREATE TABLE prescriptions (
    prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL,
    medication_name TEXT NOT NULL,
    dosage TEXT,
    duration TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (record_id) REFERENCES medical_records(record_id)
);

-- ===========================
-- VUES SIMPLIFIÉES
-- ===========================
CREATE VIEW vue_consultation AS
SELECT 
    mr.record_id,
    p.first_name || ' ' || p.last_name AS patient_name,
    a.appointment_date,
    u.full_name AS doctor_name,
    mr.diagnosis,
    mr.notes
FROM medical_records mr
LEFT JOIN patients p ON mr.patient_id = p.patient_id
LEFT JOIN appointments a ON mr.appointment_id = a.appointment_id
LEFT JOIN users u ON a.user_id = u.user_id;

CREATE VIEW vue_appointment AS
SELECT 
    a.appointment_id,
    p.first_name || ' ' || p.last_name AS patient_name,
    u.full_name AS doctor_name,
    a.appointment_date,
    a.status
FROM appointments a
LEFT JOIN patients p ON a.patient_id = p.patient_id
LEFT JOIN users u ON a.user_id = u.user_id;

-- ===========================
-- TRIGGERS SIMPLES (updated_at)
-- ===========================
CREATE TRIGGER trg_update_user
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = OLD.user_id;
END;

CREATE TRIGGER trg_update_patient
AFTER UPDATE ON patients
FOR EACH ROW
BEGIN
    UPDATE patients SET updated_at = CURRENT_TIMESTAMP WHERE patient_id = OLD.patient_id;
END;

CREATE TRIGGER trg_update_appointment
AFTER UPDATE ON appointments
FOR EACH ROW
BEGIN
    UPDATE appointments SET updated_at = CURRENT_TIMESTAMP WHERE appointment_id = OLD.appointment_id;
END;

CREATE TRIGGER trg_update_record
AFTER UPDATE ON medical_records
FOR EACH ROW
BEGIN
    UPDATE medical_records SET updated_at = CURRENT_TIMESTAMP WHERE record_id = OLD.record_id;
END;
