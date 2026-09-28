import { db } from '@/powersync-client/client';

// Lecture locale du catalogue d'examens, dans la meme forme que la reponse
// HTTP GET /labo/exams (controller/lab_controller.py::_serialize_examen) :
// les ecrans consommateurs (modale de prescription, caisse) n'ont ainsi rien
// a adapter entre le chemin en ligne et le secours hors ligne.
export async function getExamCatalogLocal() {
  const rows = await db.getAll('SELECT * FROM exam_catalog ORDER BY nom');
  return rows.map((r) => ({
    id: r.server_id,
    code: r.code,
    nom: r.nom,
    categorie: r.categorie,
    prix: Number(r.prix) || 0,
  }));
}
