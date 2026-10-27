"""Retake of the obsolete figures of guide psychologist-1 (batch 2, 27 October 2026). Run from the repo root:
    python docs/user-guides/src/psychologist-1/retake_b2.py
Sections run one after the other, each with its own browser. They only read the screens, apart from the
demo data noted in the comments. Needs the API on :8000 and the preview on :4173 built with the latest code
(the first section clears the service worker of the browser profile so that no stale build is served).
Some sections were first run on their own: a section that fails on data the later sections changed
(a patient already discharged, a pending appointment already completed) must be adapted to the demo data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *  # noqa: F401,F403

# ---- section b2_p1 ----
from pathlib import Path
FIG = Path("docs/user-guides/src/psychologist-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-psy1"
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "psychologist")
go(p, "/dashboard/toxico-dashboard", settle=6000, connected=False)
print("DASH", txt(p, 1400)[400:])
shots.annotate(p, FIG / "dashboard.png", [
    {"text": "Toxicology Dashboard", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
    {"text": "Active Patients", "exact": True, "n": 2, "position": "top", "outline": False},
    {"text": "Distribution by Phase", "exact": True, "n": 3, "position": "right", "outline": False},
    {"text": "Psychologist Workload", "exact": True, "n": 4, "position": "right", "outline": False},
    {"text": "Clinical Alerts", "exact": True, "n": 5, "position": "right", "outline": False},
])
go(p, "/dashboard/toxico", settle=5000, connected=False)
print("LIST", txt(p, 1200)[400:])
shots.close(pw, br)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
p.goto(shots.BASE_URL + "/dashboard/toxico")
p.wait_for_timeout(9000)
print("OFF", txt(p, 1200)[400:])
shots.annotate(p, FIG / "offline.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Cannot load the data while offline", "n": 2, "position": "right", "outline": False},
    {"text": "Retry", "exact": True, "n": 3, "position": "right"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
shots.close(pw, br)

# ---- section b2_p1b ----
from pathlib import Path
FIG = Path("docs/user-guides/src/psychologist-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-psy1"
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
p.goto(shots.BASE_URL + "/dashboard/toxico")
p.wait_for_timeout(9000)
print("OFF", txt(p, 1200)[400:])
shots.annotate(p, FIG / "offline.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Cannot load the data.", "n": 2, "position": "right", "outline": False},
    {"text": "Retry", "exact": True, "n": 3, "position": "right"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
shots.close(pw, br)

# ---- section b2_off (offline figures of the three toxicology guides, navigator.onLine false) ----
from pathlib import Path
SDD = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides"
G = Path("docs/user-guides/src")


def tc(p):
    try:
        p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception:
        pass


def offline_page(profile):
    """Proxy cut (health check reads Offline) plus set_offline so that navigator.onLine is false:
    the toxicology screens then show the 'while offline' message instead of the generic one."""
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=profile, offline=True)
    p.goto(shots.BASE_URL + "/dashboard/toxico")
    p.wait_for_timeout(8000)
    br.set_offline(True)
    tc(p)
    p.get_by_text("Retry", exact=True).first.click()
    p.wait_for_timeout(3000)
    return pw, br, p


pw, br, p = offline_page(SDD / "chrome-profile-psy1")
shots.annotate(p, G / "psychologist-1/figures/offline.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Cannot load the data while offline", "n": 2, "position": "right", "outline": False},
    {"text": "Retry", "exact": True, "n": 3, "position": "right"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
shots.close(pw, br)

pw, br, p = offline_page(SDD / "chrome-profile-tox1")
shots.annotate(p, G / "toxico-1/figures/offline-list.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Cannot load the data while offline", "n": 2, "position": "right", "outline": False},
    {"text": "Retry", "exact": True, "n": 3, "position": "right"},
    {"text": "New Toxico Admission", "n": 4, "position": "left"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
p.get_by_role("tab", name="Discharged").click()
p.wait_for_timeout(3500)
print("DIS", txt(p, 900)[300:], flush=True)
shots.annotate(p, G / "toxico-2/figures/offline-discharged.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Discharged", "exact": True, "n": 2, "position": "top", "index": 0},
], crop={"x": 256, "y": 0, "width": 1344, "height": 800})
shots.close(pw, br)
