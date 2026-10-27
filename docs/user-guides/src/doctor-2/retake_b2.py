"""Retake of the obsolete figures of guide doctor-2 (batch 2, 27 October 2026). Run from the repo root:
    python docs/user-guides/src/doctor-2/retake_b2.py
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

# ---- section b2_d2c ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-2/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor2"
SP = Path(__file__).resolve().parent
def hosp_tab(p, pid):
    go(p, f"/medical/patients/{pid}")
    p.get_by_role("tab", name="Hospitalization").click(); p.wait_for_timeout(1500)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "medecin")
go(p, "/medical/hospitalizations")
print("LIST", txt(p, 1800)[500:])
shots.annotate(p, FIG / "hosp-list.png", [
    {"text": "Hospitalized Patients", "exact": True, "n": 1, "position": "right", "outline": False, "index": 1},
    {"text": "Current status", "exact": True, "n": 2, "position": "top", "outline": False},
    {"text": "View record", "exact": True, "n": 3, "position": "top", "index": 0},
], crop={"x": 256, "y": 90, "width": 1344, "height": 420})
hosp_tab(p, 19294)
p.set_viewport_size({"width": 1600, "height": 1300}); p.wait_for_timeout(800)
shots.annotate(p, FIG / "status-list.png", [
    {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
    {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
    {"text": "History", "exact": True, "n": 3, "position": "right", "outline": False},
], crop={"x": 256, "y": 330, "width": 1344, "height": 560})
shots.annotate(p, FIG / "history.png", [
    {"text": "History", "exact": True, "n": 1, "position": "right", "outline": False},
    {"text": "Download discharge letter", "exact": True, "n": 2, "position": "top"},
], crop={"x": 256, "y": 330, "width": 1344, "height": 620})
shots.close(pw, br)

# ---- section b2_d2d ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-2/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor2"
SP = Path(__file__).resolve().parent
def hosp_tab(p, pid):
    go(p, f"/medical/patients/{pid}")
    p.get_by_role("tab", name="Hospitalization").click(); p.wait_for_timeout(1500)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "medecin")
hosp_tab(p, 19294)
p.set_viewport_size({"width": 1600, "height": 1800}); p.wait_for_timeout(800)
shots.annotate(p, FIG / "status-list.png", [
    {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
    {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
    {"text": "History", "exact": True, "n": 3, "position": "right", "outline": False},
], crop={"x": 256, "y": 440, "width": 1344, "height": 560})
shots.annotate(p, FIG / "history.png", [
    {"text": "History", "exact": True, "n": 1, "position": "right", "outline": False},
    {"text": "Download discharge letter", "exact": True, "n": 2, "position": "top"},
], crop={"x": 256, "y": 440, "width": 1344, "height": 1180})
shots.close(pw, br)
