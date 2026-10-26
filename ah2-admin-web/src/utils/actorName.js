// Libelle d'un auteur : nom complet si connu, sinon "#id", sinon tiret.
export function actorLabel(name, id) {
    if (name) return name;
    if (id !== null && id !== undefined && id !== '') return `#${id}`;
    return '-';
}
