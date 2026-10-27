"""Helpers shared by the retake_b2.py scripts of the guides (27 October 2026).

fresh(): drop the service worker and its caches so that the browser profile serves the latest build.
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import shots

def fresh(p):
    """Drop stale service-worker caches so the latest build is served."""
    p.goto(shots.BASE_URL + "/login")
    p.wait_for_timeout(1500)
    p.evaluate("""async () => {
      const r = await navigator.serviceWorker.getRegistrations();
      await Promise.all(r.map(x => x.unregister()));
      const k = await caches.keys();
      await Promise.all(k.map(c => caches.delete(c)));
    }""")
    p.reload()
    p.wait_for_timeout(2000)

def go(p, route, settle=3000, connected=True):
    shots.goto(p, route)
    if connected:
        try: p.get_by_text("Connected").first.wait_for(timeout=30000)
        except Exception: pass
    p.wait_for_timeout(settle)

def txt(p, n=1500):
    return " | ".join(p.inner_text("body").split())[:n]
