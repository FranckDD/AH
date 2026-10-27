"""Retake of the obsolete figures of guide nurse-1 (batch 2, 27 October 2026). Run from the repo root:
    python docs/user-guides/src/nurse-1/retake_b2.py
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

# ---- section b2_n1 ----
from pathlib import Path
FIG = Path("docs/user-guides/src/nurse-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-nurse1"
def dialog(p): return p.locator("[role=dialog]").first
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "nurse")
go(p, "/medical/patients")
shots.annotate(p, FIG / "patients-list.png", [
    {"text": "Add a patient", "n": 1, "position": "left"},
    {"selector": "#patient-search", "n": 2, "position": "bottom"},
    {"text": "All Patients", "n": 3, "position": "top"},
    {"text": "View record", "n": 4, "position": "left", "index": 0},
], crop={"x": 256, "y": 60, "width": 1344, "height": 560})
go(p, "/medical/patients/19301")
print("DOS", txt(p, 1800)[500:])
shots.annotate(p, FIG / "dossier.png", [
    {"text": "Odile Fotso", "exact": True, "n": 1, "position": "right", "outline": False},
    {"text": "Blood pressure", "n": 2, "position": "top", "outline": False},
    {"text": "Known allergies", "n": 3, "position": "top", "outline": False},
    {"text": "New consultation", "exact": True, "n": 4, "position": "left"},
    {"text": "Edit", "exact": True, "n": 5, "position": "bottom"},
    {"text": "Prescribe", "exact": True, "n": 6, "position": "bottom"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 800})
go(p, "/medical/patients")
p.get_by_text("Add a patient").click(); p.wait_for_timeout(1500)
p.fill("#patient-first-name", "Brice"); p.fill("#patient-last-name", "Eyenga")
p.fill("#patient-birth-date", "1969-05-09")
p.select_option("#patient-gender", index=1)
p.fill("#patient-phone", "+237677010010"); p.fill("#patient-residence", "Douala")
p.set_viewport_size({"width": 1600, "height": 1300}); p.wait_for_timeout(600)
print("FORM", " | ".join(dialog(p).inner_text().split())[:700])
shots.annotate(p, FIG / "newpat-form.png", [
    {"selector": "#patient-first-name", "n": 1, "position": "right"},
    {"selector": "#patient-birth-date", "n": 2, "position": "right"},
    {"selector": "#patient-gender", "n": 3, "position": "right"},
    {"selector": "#patient-phone", "n": 4, "position": "right"},
    {"text": "Create", "exact": True, "n": 5, "position": "top"},
], crop="[role=dialog]")
shots.close(pw, br)

# ---- section b2_n1c ----
from pathlib import Path
FIG = Path("docs/user-guides/src/nurse-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-nurse1"
def dialog(p): return p.locator("[role=dialog]").first
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "nurse")
go(p, "/medical/patients")
shots.annotate(p, FIG / "patients-list.png", [
    {"text": "Add a patient", "n": 1, "position": "top"},
    {"selector": "#patient-search", "n": 2, "position": "right"},
    {"text": "All Patients", "n": 3, "position": "top"},
    {"text": "View record", "n": 4, "position": "left", "index": 0},
], crop={"x": 256, "y": 0, "width": 1344, "height": 640})
shots.close(pw, br)
