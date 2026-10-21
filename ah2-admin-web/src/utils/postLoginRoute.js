// Page d'accueil de chaque role apres connexion (fonction pure, testee).
// Le medecin arrive sur son tableau de bord (/medical/doctors, DoctorKpiView).
// L'infirmiere partage la meme interface et la meme page d'accueil (certaines\n// fonctions reservees au medecin sont simplement masquees pour elle).
export function getPostLoginPath(role) {
    // Normalisation reelle (registre L4e, chantier L4b-e)
    const userRole = (role || '').toLowerCase();

    switch (userRole) {
        case 'admin':
        case 'promoteur':
            return '/dashboard/overview';

        case 'psychologist':
        case 'spiritualcounsellor':
        case 'toxicomanager':
        case 'assistant':
            return '/dashboard/toxico-dashboard';

        case 'laborantin':
        case 'biologiste':
            return '/dashboard/labo/overviewlab';

        case 'stockcontroller':
            return '/dashboard/stock-control';

        case 'medecin':
        case 'nurse':
            return '/medical/doctors';

        case 'secretaire':
            return '/secretariat/';

        default:
            return '/dashboard/toxico-dashboard';
    }
}

// Roles reellement connus de l'application (hors defaut).
const KNOWN_ROLES = [
    'admin', 'promoteur', 'psychologist', 'spiritualcounsellor', 'toxicomanager',
    'assistant', 'laborantin', 'stockcontroller', 'medecin', 'nurse', 'secretaire',
];

// Cible des redirections racine ('/' , '/dashboard', route inconnue).
// - non authentifie : /login
// - role connu : la page d'accueil du role (identique a celle du login)
// - role inconnu : /forbidden (le defaut de getPostLoginPath serait refuse par
//   le routeur et ferait boucler / rebondir l'utilisateur)
export function resolveRootPath(role, isAuthenticated) {
    if (!isAuthenticated) return '/login';
    const r = (role || '').toLowerCase();
    if (!KNOWN_ROLES.includes(r)) return '/forbidden';
    return getPostLoginPath(r);
}
