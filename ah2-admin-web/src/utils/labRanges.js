// Plage de reference a afficher pour un patient : celle de son sexe, a defaut la plage generique
// 'X'. Jamais la plage de l'autre sexe (une plage masculine seule ne s'affiche pas pour une femme).
// Meme regle que le serveur (utils/lab_reference.py).

const MALE = new Set(['m', 'male', 'homme', 'man', 'masculin', 'h']);
const FEMALE = new Set(['f', 'female', 'femme', 'woman', 'feminin', 'féminin']);

export function normalizeSex(raw) {
  const s = String(raw ?? '').trim().toLowerCase();
  if (MALE.has(s)) return 'M';
  if (FEMALE.has(s)) return 'F';
  return 'X';
}

const fmt = (r) => `${r.min} - ${r.max}`;

export function rangeLabelForPatient(ranges, sexe) {
  if (!ranges || ranges.length === 0) return '-';
  const code = normalizeSex(sexe);
  const generic = ranges.find((r) => r.sexe === 'X');
  if (code === 'M' || code === 'F') {
    const match = ranges.find((r) => r.sexe === code) || generic;
    return match ? fmt(match) : '-';
  }
  if (generic) return fmt(generic);
  // Sexe inconnu : on ne choisit pas a la place du technicien, on montre tout.
  return ranges.map((r) => `${r.sexe} ${fmt(r)}`).join(' / ');
}
