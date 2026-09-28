import { db } from '@/powersync-client/client';

// Quarantaine locale (table localOnly sync_quarantine, jamais synchronisee
// donc jamais purgee) : un patient refuse definitivement a l'envoi (doublon
// national_id, 409) y est conserve avec ses consultations/prescriptions
// hors ligne, au lieu que celles-ci partent vers un patient inexistant puis
// disparaissent de la file. Resolution manuelle : reattachToExistingPatient.

export async function isPatientQuarantined(database, patientUuid) {
  if (!patientUuid) return false;
  const row = await database.getOptional(
    "SELECT id FROM sync_quarantine WHERE kind = 'patient' AND local_id = ?",
    [patientUuid]
  );
  return !!row;
}

// Utilise par labGateway.js::getPaillasseList (Task 8) pour exclure de la
// paillasse locale un dossier labo (ou une valeur de dossier) deja mis en
// quarantaine par le connecteur (Task 9) : celui-ci n'est pas retire de
// lab_results, seule sa ligne sync_quarantine est ajoutee.
export async function isLabResultQuarantined(database, resultUuid) {
  if (!resultUuid) return false;
  const row = await database.getOptional(
    "SELECT id FROM sync_quarantine WHERE kind IN ('lab_result', 'lab_result_detail') AND local_id = ?",
    [resultUuid]
  );
  return !!row;
}

export async function quarantine(database, { kind, localId, patientUuid, payload, error }) {
  // Correctif Important revue finale : FastAPI renvoie un detail qui est un
  // TABLEAU d'objets pour une erreur de validation 422 (pas une chaine) -
  // stocke tel quel, l'ecriture dans une colonne texte SQLite echoue
  // silencieusement (avalee par le try/catch du bloc quarantaine, le
  // patient ne finit jamais mis en quarantaine). Toujours convertir en
  // chaine avant l'ecriture.
  const errorText = typeof error === 'string' || error == null
    ? error
    : JSON.stringify(error);
  await database.execute(
    `INSERT INTO sync_quarantine (id, kind, local_id, patient_uuid, payload, error, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [
      crypto.randomUUID(), kind, localId, patientUuid || null,
      JSON.stringify(payload || {}), errorText || null, new Date().toISOString(),
    ]
  );
}

export async function listQuarantine() {
  return db.getAll('SELECT * FROM sync_quarantine ORDER BY created_at');
}

// Reinjecte les consultations/prescriptions retenues d'un patient refuse avec
// l'id d'un patient existant : nouvelles lignes locales (nouveaux uuid, les
// anciens ont deja ete retires de la file d'envoi) qui repartent dans la file
// normalement, prescriptions rechainees vers la nouvelle consultation. Puis
// suppression de la quarantaine et des lignes locales abandonnees.
export async function reattachToExistingPatient(patientUuid, existingPatientId) {
  const children = await db.getAll(
    `SELECT * FROM sync_quarantine
     WHERE patient_uuid = ? AND kind IN ('medical_record', 'prescription')
     ORDER BY created_at`,
    [patientUuid]
  );

  await db.writeTransaction(async (tx) => {
    const newRecordIds = {};

    for (const c of children.filter((x) => x.kind === 'medical_record')) {
      const p = JSON.parse(c.payload);
      const newId = crypto.randomUUID();
      newRecordIds[c.local_id] = newId;
      await tx.execute('DELETE FROM medical_records WHERE id = ?', [c.local_id]);
      await tx.execute(
        `INSERT INTO medical_records (
            id, patient_id, consultation_date, motif_code, appointment_id,
            marital_status, severity, bp, temperature, weight, height,
            medical_history, allergies, symptoms, diagnosis, treatment, notes
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          newId, existingPatientId, p.consultation_date ?? null, p.motif_code ?? null, p.appointment_id ?? null,
          p.marital_status ?? null, p.severity ?? null, p.bp ?? null,
          p.temperature ?? null, p.weight ?? null, p.height ?? null,
          p.medical_history ?? null, p.allergies ?? null, p.symptoms ?? null,
          p.diagnosis ?? null, p.treatment ?? null, p.notes ?? null,
        ]
      );
    }

    for (const c of children.filter((x) => x.kind === 'prescription')) {
      const p = JSON.parse(c.payload);
      const linkedRecord = p.medical_record_id ? (newRecordIds[p.medical_record_id] || p.medical_record_id) : null;
      await tx.execute('DELETE FROM prescriptions WHERE id = ?', [c.local_id]);
      await tx.execute(
        `INSERT INTO prescriptions (
            id, patient_id, medical_record_id, medication, dosage, frequency,
            duration, start_date, end_date, notes, is_lab_order, lab_exams_list
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          crypto.randomUUID(), existingPatientId, linkedRecord, p.medication ?? null,
          p.dosage ?? null, p.frequency ?? null, p.duration ?? null,
          p.start_date ?? null, p.end_date ?? null, p.notes ?? null,
          p.is_lab_order ? 1 : 0, p.lab_exams_list ?? '[]',
        ]
      );
    }

    await tx.execute('DELETE FROM patients WHERE id = ?', [patientUuid]);
    await tx.execute(
      "DELETE FROM sync_quarantine WHERE patient_uuid = ? OR (kind = 'patient' AND local_id = ?)",
      [patientUuid, patientUuid]
    );
  });
}
