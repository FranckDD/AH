// Duree d'un sejour hospitalier : minutes, heures, puis jours (jamais "0 jour(s)").
// Les dates du serveur sont l'heure locale de Douala (naive) : on compare donc
// deux dates lues de la meme facon (le navigateur du centre est a Douala).
export function formatStayDuration(start, end, labels) {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const minutes = Math.max(0, Math.floor((Number.isFinite(ms) ? ms : 0) / 60000));
  if (minutes < 60) return `${minutes} ${labels.minutes}`;
  if (minutes < 24 * 60) return `${Math.floor(minutes / 60)} ${labels.hours} ${minutes % 60} ${labels.minutes}`;
  return `${Math.floor(minutes / 1440)} ${labels.days} ${Math.floor((minutes % 1440) / 60)} ${labels.hours}`;
}
