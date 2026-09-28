import { PowerSyncDatabase, WASQLiteVFS } from '@powersync/web';
import { AppSchema } from './AppSchema';
import { DossierConnector } from './DossierConnector';

export const db = new PowerSyncDatabase({
  schema: AppSchema,
  database: {
    dbFilename: 'ah2-powersync.db',
    // Sans ce choix explicite, le SDK utilise par defaut IDBBatchAtomicVFS
    // (base sur IndexedDB) - PowerSync documente eux-memes que leur VFS
    // base sur OPFS offre plus de 2x les performances d'IndexedDB, surtout
    // pour l'ecriture en masse (exactement notre cas : ~150-300 lignes
    // appliquees d'un coup au premier sync apres connexion). Necessite
    // useWebWorker:true, deja la valeur par defaut du SDK.
    vfs: WASQLiteVFS.OPFSCoopSyncVFS,
  },
});

// Connexion en cours ou deja etablie. C'est une PROMESSE, pas un booleen :
// avec un booleen pose seulement en fin de fonction, deux appels simultanes
// (ex. App.vue au montage + login() juste apres) passaient tous les deux la
// garde, ouvraient chacun la base locale OPFS et se disputaient le meme
// verrou de fichier - l'un attendait que l'autre le relache. Une promesse
// partagee garantit un seul connect reel, les appels suivants s'y raccrochent.
let connectPromise = null;

// Abonnements actifs conserves au niveau module (pas dans une variable
// locale a connectPowerSync) : le SDK PowerSync detecte et journalise un
// avertissement "leaked" si l'objet SyncStreamSubscription est libere par
// le ramasse-miettes sans que unsubscribe() ait ete appele explicitement -
// message du SDK lui-meme : "consider storing them in global fields".
let activeSubscriptions = [];

// Role pour lequel activeSubscriptions a ete constitue. Necessaire pour
// detecter un changement de compte dans le meme onglet (ex. tests
// successifs de plusieurs roles) : reconnecter avec le MEME role peut
// reutiliser les abonnements existants sans risque, reconnecter avec un
// role DIFFERENT ne le peut pas (voir avertissement ci-dessous).
let activeRole = null;

// role : 'medecin' | 'nurse' - determine quel stream RDV souscrire. Ne
// jamais souscrire aux deux streams RDV pour un meme utilisateur - un
// medecin recevrait alors aussi la portee large de all_appointments,
// annulant la restriction voulue.
export function connectPowerSync(role) {
  if (connectPromise) {
    return connectPromise;
  }
  connectPromise = openConnection(role).catch((error) => {
    // Un echec ne doit pas condamner la session : on libere la garde pour
    // qu'une tentative ulterieure (prochain login) soit possible.
    connectPromise = null;
    throw error;
  });
  return connectPromise;
}

/**
 * Attendre que la base locale soit reellement synchronisee. A utiliser par
 * tout ecran qui lit les tables PowerSync juste apres l'ouverture (ex. la
 * recherche patient de la modale RDV) : la connexion ne bloque plus le
 * login, donc un ecran peut s'ouvrir avant la fin du premier sync.
 */
export function waitForInitialSync() {
  return connectPromise ?? Promise.resolve();
}

async function openConnection(role) {
  if (activeSubscriptions.length > 0 && activeRole !== role) {
    // Une session precedente dans ce meme onglet a laisse des abonnements
    // actifs pour un AUTRE role (compte different testee sans recharger
    // la page). Les garder indefiniment referencees en plus des nouvelles
    // serait une vraie fuite de ressources (pas seulement l'avertissement
    // console) : a chaque changement de role, un jeu d'abonnements
    // supplementaire resterait ouvert pour toujours. On ne peut pas non
    // plus les reutiliser, le role a change (cf. avertissement ci-dessus).
    // On paie ici le cout de resynchronisation (unsubscribe() declenche
    // l'eviction TTL cote SDK, donc un rechargement complet des buckets a
    // la prochaine souscription) - jamais a la simple deconnexion (voir
    // disconnectPowerSync), seulement quand le role a reellement change.
    await Promise.all(activeSubscriptions.map((sub) => sub.unsubscribe()));
    activeSubscriptions = [];
  }

  if (activeSubscriptions.length === 0) {
    // Souscrire AVANT de se connecter (pas apres, comme dans une version
    // precedente de ce fichier). db.connect() ouvre immediatement un flux
    // de synchronisation base sur les abonnements deja enregistres a cet
    // instant precis - si on se connecte d'abord, le premier flux s'ouvre
    // sans aucun bucket, reste inactif (18,5s observees en test reel
    // navigateur) avant qu'un 2e flux correct ne soit ouvert une fois les
    // souscriptions enregistrees. Souscrire d'abord evite cet aller-retour :
    // syncStream(...).subscribe() enregistre l'intention localement, sans
    // exiger de connexion active au prealable ("requesting it to be
    // included when connecting to the sync service" - doc du SDK).
    const streamHandles = [];
    if (role === 'medecin') {
      streamHandles.push(db.syncStream('my_appointments'));
    } else if (role === 'nurse') {
      streamHandles.push(db.syncStream('all_appointments'));
    }
    streamHandles.push(db.syncStream('patients_lookup'));
    streamHandles.push(db.syncStream('doctors_lookup'));
    if (role === 'medecin' || role === 'nurse') {
      streamHandles.push(db.syncStream('clinical_patients'));
      streamHandles.push(db.syncStream('clinical_medical_records'));
      streamHandles.push(db.syncStream('clinical_prescriptions'));
      streamHandles.push(db.syncStream('clinical_lab_results'));
    }
    if (role === 'secretaire') {
      streamHandles.push(db.syncStream('secretariat_caisse'));
      streamHandles.push(db.syncStream('secretariat_retraits'));
      streamHandles.push(db.syncStream('secretariat_payments'));
      streamHandles.push(db.syncStream('secretariat_pharmacy_stock'));
    }
    // Catalogue d'examens : demandes d'examen (medecin/nurse) et facturation
    // d'un examen en caisse (secretaire). Motifs : consultation seulement.
    if (role === 'medecin' || role === 'nurse' || role === 'secretaire' || role === 'laborantin') {
      streamHandles.push(db.syncStream('reference_exam_catalog'));
    }
    if (role === 'laborantin') {
      streamHandles.push(db.syncStream('lab_pending_prescriptions'));
      streamHandles.push(db.syncStream('lab_active_results'));
      streamHandles.push(db.syncStream('lab_active_result_details'));
      streamHandles.push(db.syncStream('reference_lab_params'));
      streamHandles.push(db.syncStream('reference_lab_ranges'));
    }
    if (role === 'medecin' || role === 'nurse') {
      streamHandles.push(db.syncStream('reference_motifs'));
    }

    activeSubscriptions = await Promise.all(streamHandles.map((s) => s.subscribe()));
    activeRole = role;
  }
  // Sinon (meme role qu'avant dans ce meme onglet) : reutilisation directe
  // des abonnements existants, sans nouvel appel subscribe() - evite a la
  // fois la fuite ET le cout de resynchronisation pour le cas le plus
  // frequent (un utilisateur qui se reconnecte).

  await db.waitForReady();

  const connector = new DossierConnector();
  await db.connect(connector);

  // subscribe() (ci-dessus) enregistre seulement l'abonnement - il ne
  // garantit PAS que les donnees sont deja synchronisees localement.
  // Sans attendre waitForFirstSync() sur l'objet qu'il retourne, l'appli
  // navigue avant que patients_lookup/les RDV n'aient eu le temps
  // d'arriver, et toute recherche locale immediate (ex. lookupPatient())
  // echoue a tort ("patient introuvable" alors que le patient existe
  // bien, juste pas encore synchronise).
  await Promise.all(activeSubscriptions.map((sub) => sub.waitForFirstSync()));
}

export async function disconnectPowerSync() {
  if (!connectPromise) {
    return;
  }
  // Libere la garde AVANT de fermer : si la connexion est encore en vol, on
  // ne veut surtout pas l'attendre (c'est precisement le cas lent).
  connectPromise = null;
  // Ne PAS appeler sub.unsubscribe() ici (ancienne version de ce fichier le
  // faisait, ajoute pour eliminer l'avertissement console "subscription
  // leaked"). D'apres la doc du SDK (sync-streams.ts) : unsubscribe() lance
  // un TTL apres lequel le stream est "evince" (donnees locales purgees) -
  // resouscrire ensuite (prochain login) force alors un re-telechargement +
  // reapplication complete de toutes les donnees du stream, ce qui explique
  // vraisemblablement le delai de ~18s observe en test reel a chaque
  // reconnexion. Le message "leaked" lui-meme suggere la vraie solution :
  // "consider storing them in global fields" - deja fait ci-dessus
  // (activeSubscriptions au niveau module) - conserver la reference suffit
  // a eviter le ramasse-miettes SANS avoir besoin d'unsubscribe().
  await db.disconnect();
}
