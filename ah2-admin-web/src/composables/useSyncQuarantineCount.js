import { ref, onMounted, onBeforeUnmount } from 'vue';
import { db } from '@/powersync-client/client';

// Nombre de patients en quarantaine, mis a jour en continu (db.watch) - sert
// a afficher l'entree de menu "Echecs de synchronisation" seulement quand il
// y a quelque chose a resoudre.
export function useSyncQuarantineCount() {
  const count = ref(0);
  const controller = new AbortController();

  onMounted(() => {
    (async () => {
      try {
        for await (const result of db.watch(
          "SELECT COUNT(*) AS n FROM sync_quarantine WHERE kind = 'patient'",
          [],
          { signal: controller.signal }
        )) {
          count.value = result.rows?._array?.[0]?.n ?? 0;
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Surveillance de la quarantaine interrompue:', err);
        }
      }
    })();
  });

  onBeforeUnmount(() => controller.abort());

  return count;
}
