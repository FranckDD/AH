"""Retake of the obsolete figures of guide nurse-2 (batch 2, 27 October 2026). Run from the repo root:
    python docs/user-guides/src/nurse-2/retake_b2.py
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

# ---- section b2_n2 ----
from pathlib import Path
FIG = Path("docs/user-guides/src/nurse-2/figures")
SDD = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides"
def hosp_tab(p, pid):
    go(p, f"/medical/patients/{pid}")
    p.get_by_role("tab", name="Hospitalization").click(); p.wait_for_timeout(1500)
pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-nurse")
fresh(p)
shots.login(p, "nurse")
go(p, "/medical/hospitalizations")
shots.annotate(p, FIG / "hosp-list.png", [
    {"text": "Hospitalized Patients", "exact": True, "n": 1, "position": "right", "outline": False, "index": 1},
    {"text": "Worsening", "exact": True, "n": 2, "position": "right", "index": 0},
    {"text": "View record", "exact": True, "n": 3, "position": "top", "index": 0},
], crop={"x": 256, "y": 90, "width": 1344, "height": 420})
hosp_tab(p, 19301)
shots.annotate(p, FIG / "status-card.png", [
    {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
    {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
    {"text": "Discharge", "exact": True, "n": 3, "position": "bottom", "index": 0},
], crop={"x": 256, "y": 460, "width": 1344, "height": 620})
hosp_tab(p, 19299)
shots.annotate(p, FIG / "discharged.png", [
    {"text": "Download discharge letter", "exact": True, "n": 1, "position": "top"},
    {"text": "Admit", "exact": True, "n": 2, "position": "left"},
], crop={"x": 256, "y": 460, "width": 1344, "height": 600})
shots.close(pw, br)

# ---- section b2_n2b ----
from pathlib import Path
FIG = Path("docs/user-guides/src/nurse-2/figures")
SDD = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides"
pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-head_nurse")
shots.login(p, "head_nurse")
go(p, "/medical/nurse-shifts")
p.get_by_label("28/10/2026").first.click(); p.wait_for_timeout(1000)
# fix the demo day: Etto Leto worked the night before, so swap for a nurse who did not
p.get_by_text("Remove", exact=True).first.click(); p.wait_for_timeout(1500)
p.get_by_label("Select a nurse").nth(0).select_option(label="Infirmier Test (Head nurse)")
p.get_by_role("button", name="Add a nurse").nth(0).click(); p.wait_for_timeout(1800)
print("DAY", txt(p, 2500)[500:])
shots.annotate(p, FIG / "plan-filled.png", [
    {"text": "Week", "exact": True, "n": 1, "position": "top"},
    {"text": "Remove", "exact": True, "n": 2, "position": "left", "index": 0},
    {"selector": "[aria-label='Select a nurse'] >> nth=0", "n": 3, "position": "left"},
    {"text": "Add a nurse", "exact": True, "n": 4, "position": "bottom", "index": 0},
], crop={"x": 256, "y": 150, "width": 1344, "height": 700})
p.get_by_role("button", name="Month", exact=True).click(); p.wait_for_timeout(1800)
shots.shot(p, Path(__file__).resolve().parent / "_scratch_n2_month.png")
shots.annotate(p, FIG / "plan-month.png", [
    {"text": "Month", "exact": True, "n": 1, "position": "top"},
], crop={"x": 256, "y": 150, "width": 900, "height": 1000})
shots.close(pw, br)
