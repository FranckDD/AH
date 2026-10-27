"""Retake of the obsolete figures of guide toxico-2 (batch 2, 27 October 2026). Run from the repo root:
    python docs/user-guides/src/toxico-2/retake_b2.py
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

# ---- section b2_t2 ----
from pathlib import Path
F1 = Path("docs/user-guides/src/toxico-1/figures"); FIG = Path("docs/user-guides/src/toxico-2/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-tox1"
def dlg(p): return p.locator("[role=dialog]").last
def tc(p):
    try: p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception: pass
def g(p, route, settle=3500):
    shots.goto(p, route); p.wait_for_timeout(settle); tc(p)
def row_action(p, name, action):
    p.locator("tr", has_text=name).first.get_by_text(action, exact=True).click(); p.wait_for_timeout(2000)
def tab(p, name):
    p.get_by_role("tab", name=name).first.click(); p.wait_for_timeout(3000)
def to_dis(p):
    g(p, "/dashboard/toxico"); tab(p, "Discharged")
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
shots.login(p, "toxico")
# toxico-1 adm-new (marker 4 moved off the label)
g(p, "/dashboard/toxico", 3000)
p.get_by_text("New Toxico Admission").click(); p.wait_for_timeout(1500)
p.get_by_text("New patient", exact=True).click(); p.wait_for_timeout(1200)
p.fill("#tox-adm-first", "Samuel"); p.fill("#tox-adm-last", "Biyick"); p.fill("#tox-adm-dob", "1990-02-17")
p.select_option("#tox-adm-sex", index=1)
p.fill("#tox-adm-mother", "Berthe Biyick"); p.fill("#tox-adm-address", "Yaounde, Mvog-Ada"); p.fill("#tox-adm-contact", "677112200")
p.select_option("#tox-adm-substance", index=4); p.select_option("#tox-adm-psy", label="Demo Psychologist")
p.fill("#tox-adm-guardian", "Berthe Biyick"); p.fill("#tox-adm-guardian-contact", "677112201")
p.set_viewport_size({"width": 1600, "height": 1800}); p.wait_for_timeout(600)
shots.annotate(p, F1 / "adm-new.png", [
    {"selector": "#tox-adm-first", "n": 1, "position": "top"},
    {"selector": "#tox-adm-dob", "n": 2, "position": "top"},
    {"selector": "#tox-adm-mother", "n": 3, "position": "top"},
    {"selector": "#tox-adm-contact", "n": 4, "position": "right"},
    {"text": "Validate Admission", "n": 5, "position": "top"},
], crop="[role=dialog]")
dlg(p).get_by_text("Cancel").click(); p.wait_for_timeout(800)
p.set_viewport_size({"width": 1600, "height": 1000})
# discharge-other, then the hospital warning
g(p, "/dashboard/toxico")
row_action(p, "Samuel Biyick", "Discharge")
p.get_by_text("Other", exact=True).click()
dlg(p).get_by_text("Confirm discharge").click(); p.wait_for_timeout(900)
print("DOTHER", " | ".join(dlg(p).inner_text().split())[:600], flush=True)
shots.annotate(p, FIG / "discharge-other.png", [
    {"text": "Other", "exact": True, "n": 1, "position": "left"},
    {"selector": "#discharge-note", "n": 2, "position": "left"},
    {"text": "A note is required", "n": 3, "position": "right", "outline": False},
    {"text": "Confirm discharge", "n": 4, "position": "top"},
], crop="[role=dialog]")
dlg(p).get_by_text("Cancel").click(); p.wait_for_timeout(800)
g(p, "/dashboard/toxico")
row_action(p, "Verifoff Tester", "Discharge")
p.get_by_text("Dropout", exact=True).click(); p.wait_for_timeout(800)
print("DHOSP", " | ".join(dlg(p).inner_text().split())[:700], flush=True)
p.set_viewport_size({"width": 1600, "height": 1300}); p.wait_for_timeout(500)
shots.annotate(p, FIG / "discharge-hospital.png", [
    {"text": "I understand", "n": 1, "position": "left"},
    {"text": "Confirm discharge", "n": 2, "position": "top"},
], crop="[role=dialog]")
dlg(p).get_by_text("Cancel").click(); p.wait_for_timeout(800)
p.set_viewport_size({"width": 1600, "height": 1000})
# discharged tab
to_dis(p)
print("DTAB", txt(p, 1500)[450:], flush=True)
shots.annotate(p, FIG / "discharged-tab.png", [
    {"text": "Discharged", "exact": True, "n": 1, "position": "top", "index": 0},
    {"selector": "#tox-dis-search", "n": 2, "position": "top"},
    {"selector": "#tox-dis-reason", "n": 3, "position": "top"},
    {"selector": "#tox-dis-from", "n": 4, "position": "top"},
    {"text": "Export PDF", "n": 5, "position": "left"},
], crop={"x": 256, "y": 100, "width": 1344, "height": 700})
# readmit form (cancelled)
row_action(p, "Odile Fotso", "Readmit")
print("READM", " | ".join(dlg(p).inner_text().split())[:500], "SUB", p.input_value("#tox-adm-substance"), "G", p.input_value("#tox-adm-guardian"), flush=True)
p.select_option("#tox-adm-psy", label="Demo Psychologist")
p.fill("#tox-adm-notes", "Brought back by the family after a relapse. Agreed to restart the programme.")
p.set_viewport_size({"width": 1600, "height": 1500}); p.wait_for_timeout(600)
shots.annotate(p, FIG / "readmit-form.png", [
    {"text": "Patient already followed", "n": 1, "position": "left", "outline": False},
    {"selector": "#tox-adm-date", "n": 2, "position": "right"},
    {"selector": "#tox-adm-psy", "n": 3, "position": "top"},
    {"selector": "#tox-adm-guardian", "n": 4, "position": "top"},
    {"text": "Validate Admission", "n": 5, "position": "top"},
], crop="[role=dialog]")
dlg(p).get_by_text("Cancel").click(); p.wait_for_timeout(800)
p.set_viewport_size({"width": 1600, "height": 1000})
# view discharged
to_dis(p)
row_action(p, "Odile Fotso", "View record")
print("VIEWD", " | ".join(dlg(p).inner_text().split())[:600], flush=True)
shots.annotate(p, FIG / "view-discharged.png", [
    {"text": "Discharged from programme", "n": 1, "position": "right", "outline": False},
    {"text": "Recovery", "exact": True, "n": 2, "position": "right", "index": 1, "outline": False},
    {"text": "Export record (PDF)", "n": 3, "position": "top"},
])
# file with two stays
g(p, "/dashboard/toxico")
row_action(p, "Marcel Ebogo", "File")
dlg(p).evaluate("e => { for (const d of e.querySelectorAll('*')) { if (d.scrollHeight > d.clientHeight + 50 && getComputedStyle(d).overflowY !== 'visible') d.scrollTop = 99999 } }")
p.wait_for_timeout(700)
print("FILE", " | ".join(dlg(p).inner_text().split())[-900:], flush=True)
shots.annotate(p, FIG / "file-stays.png", [
    {"text": "Interrupted", "exact": True, "n": 1, "position": "right", "index": 0},
    {"text": "Stay 2", "exact": True, "n": 2, "position": "left", "outline": False},
    {"text": "Ongoing", "exact": True, "n": 3, "position": "right"},
    {"selector": "[role=dialog] button:has-text('Discharge')", "n": 4, "position": "top"},
], crop="[role=dialog]")
# full clinical file of the discharged patient
to_dis(p)
row_action(p, "Odile Fotso", "View record")
p.get_by_role("tab", name="Medical Record").click(); p.wait_for_timeout(2000)
p.get_by_text("See full history").click(); p.wait_for_timeout(5000)
p.get_by_text("Toxicology Follow-up", exact=True).click(); p.wait_for_timeout(3000)
shots.annotate(p, FIG / "full-tox-discharged.png", [
    {"text": "Toxicology Follow-up", "exact": True, "n": 1, "position": "top"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 680})
shots.close(pw, br)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
p.goto(shots.BASE_URL + "/dashboard/toxico"); p.wait_for_timeout(9000); tc(p)
p.get_by_role("tab", name="Discharged").click(); p.wait_for_timeout(4000)
print("OFFD", txt(p, 900)[250:], flush=True)
shots.annotate(p, FIG / "offline-discharged.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Discharged", "exact": True, "n": 2, "position": "top", "index": 0},
], crop={"x": 256, "y": 0, "width": 1344, "height": 800})
shots.close(pw, br)
print("T2DONE", flush=True)

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
