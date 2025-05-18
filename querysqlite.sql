-- Table: patients
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom varchar(65) NOT NULL,
    prenom varchar(65),
    adresse varchar(65),
    telephone varchar(65),
    mois_naiss DATE,
    email varchar(65),
    assurance varchar(65),
    date_enregistrement DATETIME
);

-- Table: medical_records
CREATE TABLE IF NOT EXISTS medical_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    consultation_date TEXT DEFAULT (datetime('now')),
    bp TEXT,
    temperature NUMERIC,
    weight NUMERIC,
    height NUMERIC,
    medical_history TEXT,
    allergies TEXT,
    symptoms TEXT,
    diagnosis TEXT,
    treatment TEXT,
    severity TEXT CHECK(severity IN ('low', 'medium', 'high')),
    notes TEXT,
    created_by INTEGER,
    created_by_name TEXT,
    last_updated_by INTEGER,
    last_updated_by_name TEXT,
    motif TEXT CHECK(motif IN (
        'consultation', 'appointment', 'prenatal', 
        'hospitalization', 'emergency', 'free'
    )),
    marital_status TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Table: caisse_transactions
CREATE TABLE IF NOT EXISTS caisse(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    montant NUMERIC,
    date_transaction TEXT DEFAULT (datetime('now')),
    type_transaction TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);