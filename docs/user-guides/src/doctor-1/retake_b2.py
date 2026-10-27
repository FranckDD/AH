"""Retake of the obsolete figures of guide doctor-1 (batch 2, 27 October 2026). Run from the repo root:
    python docs/user-guides/src/doctor-1/retake_b2.py
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

# ---- section b2_d1g ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor1"
pw, br, p = shots.launch(width=1600, height=1400, profile_dir=PROFILE)
shots.login(p, "medecin")
go(p, "/medical/doctors")
shots.annotate(p, FIG / "dashboard.png", [
    {"text": "Activity", "exact": True, "n": 1, "position": "right", "outline": False},
    {"text": "Connected", "n": 2, "position": "bottom"},
    {"text": "Patients awaiting review", "n": 3, "position": "right", "outline": False},
    {"text": "Take in charge", "n": 4, "position": "top"},
    {"text": "Quick access", "exact": True, "n": 5, "position": "right", "outline": False},
    {"text": "Statistics for the period", "n": 6, "position": "right", "outline": False},
], crop={"x": 0, "y": 0, "width": 1600, "height": 1180})
shots.close(pw, br)

# ---- section b2_d1b ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor1"
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "medecin")
go(p, "/medical/appointments")
p.get_by_text("Calendar view").click(); p.wait_for_timeout(2000)
p.get_by_text("10:30 Nadin").first.click(); p.wait_for_timeout(2000)
shots.annotate(p, FIG / "appt-day-panel.png", [
    {"text": "Start consultation", "exact": True, "n": 1, "position": "top"},
    {"text": "Complete", "exact": True, "n": 2, "position": "top"},
    {"text": "View record", "exact": True, "n": 3, "position": "bottom"},
    {"text": "Edit", "exact": True, "n": 4, "position": "bottom"},
    {"text": "Reject", "exact": True, "n": 5, "position": "bottom"},
], crop={"x": 925, "y": 170, "width": 680, "height": 260})
go(p, "/medical/patients/19294")
shots.annotate(p, FIG / "dossier.png", [
    {"text": "Pierre Kamdem", "exact": True, "n": 1, "position": "right", "outline": False},
    {"text": "Export PDF", "n": 2, "position": "left"},
    {"text": "Blood pressure", "n": 3, "position": "top", "outline": False},
    {"text": "Known allergies", "n": 4, "position": "top", "outline": False},
    {"text": "Exams", "exact": True, "n": 5, "position": "top"},
    {"text": "New consultation", "exact": True, "n": 6, "position": "left"},
    {"text": "Edit", "exact": True, "n": 7, "position": "bottom"},
    {"text": "Prescribe", "exact": True, "n": 8, "position": "bottom"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 1000})
go(p, "/medical/patients/111")
p.get_by_role("tab", name="Toxicology Follow-up").click(); p.wait_for_timeout(2000)
print("RESTR", txt(p, 1500)[300:])
shots.close(pw, br)

# ---- section b2_d1c ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor1"
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
shots.login(p, "medecin")
go(p, "/medical/patients/111")
p.get_by_role("tab", name="Toxicology Follow-up").click(); p.wait_for_timeout(2000)
shots.annotate(p, FIG / "dossier-restricted.png", [
    {"text": "TOXICOLOGY", "exact": True, "n": 1, "position": "bottom"},
    {"text": "Toxicology Follow-up", "exact": True, "n": 2, "position": "top"},
    {"text": "This area belongs to another department and is not shown here.", "exact": True, "n": 3, "position": "right", "outline": False},
], crop={"x": 256, "y": 0, "width": 1344, "height": 760})
go(p, "/medical/lab-results")
p.fill("#lab-results-search", "")
p.wait_for_timeout(3000)
print("RES", txt(p, 2500)[400:])
shots.close(pw, br)

# ---- section b2_d1f ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor1"
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
shots.login(p, "medecin")
go(p, "/medical/appointments")
p.get_by_text("Calendar view").click(); p.wait_for_timeout(2000)
p.get_by_text("10:30 Nadin").first.click(); p.wait_for_timeout(2000)
shots.annotate(p, FIG / "appt-day-panel.png", [
    {"text": "Start consultation", "exact": True, "n": 1, "position": "left"},
    {"text": "Complete", "exact": True, "n": 2, "position": "top"},
    {"text": "View record", "exact": True, "n": 3, "position": "bottom"},
    {"text": "Edit", "exact": True, "n": 4, "position": "bottom"},
    {"text": "Reject", "exact": True, "n": 5, "position": "bottom"},
], crop={"x": 1000, "y": 90, "width": 600, "height": 330})
go(p, "/medical/lab-results")
p.fill("#lab-results-search", "Kamdem"); p.wait_for_timeout(3000)
p.get_by_text("View details", exact=True).nth(1).click(); p.wait_for_timeout(2500)
p.set_viewport_size({"width": 1600, "height": 1500}); p.wait_for_timeout(800)
shots.annotate(p, FIG / "result-detail.png", [
    {"text": "Parameter", "exact": True, "n": 1, "position": "top", "outline": False},
    {"text": "Reference Values", "exact": True, "n": 2, "position": "top", "outline": False},
    {"text": "Interpretation", "exact": True, "n": 3, "position": "top", "outline": False},
    {"text": "Print", "exact": True, "n": 4, "position": "top"},
], crop="[role=dialog]")
shots.close(pw, br)

# ---- section b2_d1h ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor1"
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
shots.login(p, "medecin")
go(p, "/medical/lab-results")
p.fill("#lab-results-search", "Kamdem"); p.wait_for_timeout(3000)
p.get_by_text("View details", exact=True).nth(1).click(); p.wait_for_timeout(2500)
p.set_viewport_size({"width": 1600, "height": 1500}); p.wait_for_timeout(800)
shots.annotate(p, FIG / "result-detail.png", [
    {"text": "Result", "exact": True, "n": 1, "position": "top", "outline": False},
    {"text": "Reference Values", "exact": True, "n": 2, "position": "top", "outline": False},
    {"text": "Interpretation", "exact": True, "n": 3, "position": "top", "outline": False},
    {"text": "Print", "exact": True, "n": 4, "position": "top"},
], crop="[role=dialog]")
shots.close(pw, br)

# ---- section b2_d1e_all ----
from pathlib import Path
FIG = Path("docs/user-guides/src/doctor-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor1"
def dialog(p): return p.locator("[role=dialog]").first
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
shots.login(p, "medecin")
for route in ("/medical/doctors", "/medical/appointments", "/medical/patients/19293", "/medical/prescriptions", "/medical/lab-results"):
    go(p, route, settle=5000)
shots.close(pw, br)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
p.goto(shots.BASE_URL + "/medical/doctors")
p.get_by_text("Offline").first.wait_for(timeout=60000)
shots.wait_ready(p); p.wait_for_timeout(3000)
p.goto(shots.BASE_URL + "/medical/patients/19293")
shots.wait_ready(p); p.wait_for_timeout(4000)
p.get_by_text("New consultation", exact=True).first.click(); p.wait_for_timeout(1500)
p.set_viewport_size({"width": 1600, "height": 2200})
p.select_option("#mr-motif", "consultation")
p.fill("#mr-bp", "130/85"); p.fill("#mr-temperature", "37.0")
p.fill("#mr-symptoms", "Fever gone, headache much better.")
p.fill("#mr-diagnosis", "Viral fever, resolving")
p.fill("#mr-notes", "Entered while the connection was down.")
dialog(p).get_by_text("Save", exact=True).click(); p.wait_for_timeout(3000)
p.set_viewport_size({"width": 1600, "height": 1000}); p.wait_for_timeout(800)
print(txt(p, 900)[300:])
shots.annotate(p, FIG / "offline-saved.png", [
    {"selector": "text=/Offline|Sending error/ >> visible=true", "n": 1, "position": "bottom"},
    {"text": "Viral fever, resolving", "exact": True, "n": 2, "position": "right", "outline": False},
], crop={"x": 256, "y": 0, "width": 1344, "height": 760})
shots.close(pw, br)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
shots.goto(p, "/medical/patients/19293")
p.get_by_text("Connected").first.wait_for(timeout=60000)
p.wait_for_timeout(8000)
shots.close(pw, br)
