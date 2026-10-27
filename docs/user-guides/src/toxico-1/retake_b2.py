"""Retake of the obsolete figures of guide toxico-1 (batch 2, 27 October 2026). Run from the repo root:
    python docs/user-guides/src/toxico-1/retake_b2.py
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

# ---- section b2_t1 ----
from pathlib import Path
FIG = Path("docs/user-guides/src/toxico-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-tox1"
CONSENT = str(Path(__file__).resolve().parent / "_scratch_consent.pdf")  # any one-page PDF
def dlg(p): return p.locator("[role=dialog]").last
def tc(p):
    try: p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception: pass
def g(p, route, settle=3500):
    shots.goto(p, route); p.wait_for_timeout(settle); tc(p)
def open_adm(p):
    g(p, "/dashboard/toxico", 3000)
    p.get_by_text("New Toxico Admission").click(); p.wait_for_timeout(1500)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "toxico")
g(p, "/dashboard/toxico-dashboard", 6000); p.wait_for_timeout(1500)
shots.annotate(p, FIG / "dashboard.png", [
    {"text": "Toxicology Dashboard", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
    {"text": "Active Patients", "exact": True, "n": 2, "position": "top", "outline": False},
    {"text": "Distribution by Phase", "exact": True, "n": 3, "position": "right", "outline": False},
    {"text": "Distribution by Substance", "exact": True, "n": 4, "position": "right", "outline": False},
], crop={"x": 256, "y": 60, "width": 1344, "height": 560})
open_adm(p)
p.fill("#tox-adm-search", "Kamdem"); p.wait_for_timeout(2200)
dlg(p).get_by_role("button", name="Pierre").first.click(); p.wait_for_timeout(2500)
p.fill("#tox-adm-date", "2026-10-27"); p.select_option("#tox-adm-substance", "Cannabis")
print("PSY", [o for o in p.locator("#tox-adm-psy option").all_inner_texts()])
p.select_option("#tox-adm-psy", label="Demo Psychologist")
p.fill("#tox-adm-guardian", "Paul Kamdem"); p.fill("#tox-adm-guardian-contact", "677889900")
p.set_input_files("#tox-adm-file", CONSENT)
p.fill("#tox-adm-notes", "Referred by his family after repeated absences from work. Consent signed on 25 October.")
p.set_viewport_size({"width": 1600, "height": 1500}); p.wait_for_timeout(800)
shots.annotate(p, FIG / "adm-attach.png", [
    {"text": "Change", "exact": True, "n": 1, "position": "left"},
    {"selector": "#tox-adm-date", "n": 2, "position": "right"},
    {"selector": "#tox-adm-substance", "n": 3, "position": "top"},
    {"selector": "#tox-adm-psy", "n": 4, "position": "top"},
    {"selector": "#tox-adm-guardian", "n": 5, "position": "top"},
    {"selector": "label[for=tox-adm-file]", "n": 6, "position": "top"},
    {"text": "Validate Admission", "n": 7, "position": "top"},
], crop="[role=dialog]")
dlg(p).get_by_text("Cancel").click(); p.wait_for_timeout(800)
p.set_viewport_size({"width": 1600, "height": 1000})
open_adm(p)
p.get_by_text("New patient", exact=True).click(); p.wait_for_timeout(1200)
p.fill("#tox-adm-first", "Samuel"); p.fill("#tox-adm-last", "Biyick")
p.fill("#tox-adm-dob", "1990-02-17")
print("SELECTS", dlg(p).evaluate("e => [...e.querySelectorAll('select,input')].map(x => x.id + ':' + x.type)"))
sexsel = dlg(p).locator("select[id*=sex], select[id*=gender]")
if sexsel.count(): sexsel.first.select_option(index=1)
p.fill("#tox-adm-mother", "Berthe Biyick"); p.fill("#tox-adm-address", "Yaounde, Mvog-Ada")
p.fill("#tox-adm-contact", "677112200")
p.select_option("#tox-adm-substance", "Cocaïne"); p.select_option("#tox-adm-psy", label="Demo Psychologist")
p.fill("#tox-adm-guardian", "Berthe Biyick"); p.fill("#tox-adm-guardian-contact", "677112201")
p.set_viewport_size({"width": 1600, "height": 1800}); p.wait_for_timeout(600)
shots.annotate(p, FIG / "adm-new.png", [
    {"selector": "#tox-adm-first", "n": 1, "position": "top"},
    {"selector": "#tox-adm-dob", "n": 2, "position": "top"},
    {"selector": "#tox-adm-mother", "n": 3, "position": "top"},
    {"selector": "#tox-adm-contact", "n": 4, "position": "top"},
    {"text": "Validate Admission", "n": 5, "position": "top"},
], crop="[role=dialog]")
dlg(p).get_by_text("Cancel").click(); p.wait_for_timeout(800)
p.set_viewport_size({"width": 1600, "height": 1000})
g(p, "/dashboard/toxico", 3000)
p.locator("tr", has_text="Odile Fotso").first.get_by_text("File", exact=True).click(); p.wait_for_timeout(2500)
p.get_by_role("tab", name="Medical Record").click(); p.wait_for_timeout(2000)
p.get_by_text("See full history").click(); p.wait_for_timeout(5000)
print("FULL", txt(p, 900)[300:])
shots.annotate(p, FIG / "full-file.png", [
    {"text": "Medical Record", "exact": True, "n": 1, "position": "top", "index": 0},
    {"text": "Exams", "exact": True, "n": 2, "position": "top"},
    {"text": "Treatments", "exact": True, "n": 3, "position": "top"},
    {"text": "Toxicology Follow-up", "exact": True, "n": 4, "position": "top"},
    {"text": "Export PDF", "exact": True, "n": 5, "position": "top"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 580})
shots.close(pw, br)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
p.goto(shots.BASE_URL + "/dashboard/toxico"); p.wait_for_timeout(9000); tc(p)
shots.annotate(p, FIG / "offline-list.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Cannot load the data.", "n": 2, "position": "right", "outline": False},
    {"text": "Retry", "exact": True, "n": 3, "position": "right"},
    {"text": "New Toxico Admission", "n": 4, "position": "left"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
shots.close(pw, br)

# ---- section b2_t1b ----
from pathlib import Path
FIG = Path("docs/user-guides/src/toxico-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-tox1"
CONSENT = str(Path(__file__).resolve().parent / "_scratch_consent.pdf")  # any one-page PDF
def dlg(p): return p.locator("[role=dialog]").last
def tc(p):
    try: p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception: pass
def g(p, route, settle=3500):
    shots.goto(p, route); p.wait_for_timeout(settle); tc(p)
def open_adm(p):
    g(p, "/dashboard/toxico", 3000)
    p.get_by_text("New Toxico Admission").click(); p.wait_for_timeout(1500)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "toxico")
g(p, "/dashboard/toxico", 3000)
p.locator("tr", has_text="Samuel Biyick").first.get_by_text("File", exact=True).click(); p.wait_for_timeout(2500)
p.get_by_role("tab", name="Medical Record").click(); p.wait_for_timeout(2000)
p.get_by_text("See full history").click(); p.wait_for_timeout(5000)
print("FULL", txt(p, 900)[300:])
shots.annotate(p, FIG / "full-file.png", [
    {"text": "Medical Record", "exact": True, "n": 1, "position": "top", "index": 0},
    {"text": "Exams", "exact": True, "n": 2, "position": "top"},
    {"text": "Treatments", "exact": True, "n": 3, "position": "top"},
    {"text": "Toxicology Follow-up", "exact": True, "n": 4, "position": "top"},
    {"text": "Export PDF", "exact": True, "n": 5, "position": "top"},
], crop={"x": 256, "y": 0, "width": 1344, "height": 580})
shots.close(pw, br)
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
p.goto(shots.BASE_URL + "/dashboard/toxico"); p.wait_for_timeout(9000); tc(p)
shots.annotate(p, FIG / "offline-list.png", [
    {"text": "Offline", "n": 1, "position": "bottom"},
    {"text": "Cannot load the data.", "n": 2, "position": "right", "outline": False},
    {"text": "Retry", "exact": True, "n": 3, "position": "right"},
    {"text": "New Toxico Admission", "n": 4, "position": "left"},
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
