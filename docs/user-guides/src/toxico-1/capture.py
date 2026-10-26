"""Capture script for guide toxico-1. Run from the repo root:
    python docs/user-guides/src/toxico-1/capture.py [step ...]
Steps: signin dashboard list adm-search adm-active adm-attach adm-new details file full export bell menu account offline
adm-attach and adm-new perform real admissions in the dev database: run them once.
Demo data (fake): Nadine Tchoua AH2-880509TX (registered by the secretary, admitted by attach),
Samuel Biyick (created by the admission form), Odile Fotso (clinic consultation + prescription by the doctor),
Marcel Ebogo (already followed). Consent file: a blank one-page PDF.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
CONSENT = r"C:\Users\DD\AppData\Local\Temp\claude\c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2\27ff0bbd-56cf-4861-b20d-d557a0b9deb2\scratchpad\consent-tchoua.pdf"
steps = sys.argv[1:] or ["signin", "dashboard"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-tox1"


def go(p, route, settle=3500):
    shots.goto(p, route)
    p.wait_for_timeout(settle)
    toast_close(p)


def toast_close(p):
    try:
        p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception:
        pass


def txt(p, name):
    (HERE / f"_{name}.txt").write_text(p.inner_text("body"), encoding="utf-8")


def dlg(p):
    return p.locator("[role=dialog]").last


def row_action(p, name, action):
    p.locator("tr", has_text=name).first.get_by_text(action, exact=True).click()
    p.wait_for_timeout(2500)


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("toxico")
    p.fill("#username", acc["username"])
    p.fill("#password", "demo-password")
    shots.annotate(p, FIG / "signin.png", [
        {"selector": "#username", "n": 1},
        {"selector": "#password", "n": 2},
        {"selector": "button[type=submit]", "n": 3},
    ], crop="form")
    shots.close(pw, br)

if any(s != "signin" for s in steps):
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
    shots.login(p, "toxico")

if "dashboard" in steps:
    go(p, "/dashboard/toxico-dashboard", 6000)
    p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "dashboard.png", [
        {"text": "Toxicology Dashboard", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Active Patients", "exact": True, "n": 2, "position": "top", "outline": False},
        {"text": "Distribution by Phase", "exact": True, "n": 3, "position": "right", "outline": False},
        {"text": "Distribution by Substance", "exact": True, "n": 4, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 560})

if "list" in steps:
    go(p, "/dashboard/toxico", 4000)
    shots.annotate(p, FIG / "list.png", [
        {"text": "Toxicology Monitoring", "exact": True, "n": 1, "position": "left", "outline": False, "index": 1},
        {"selector": "#toxico-search", "n": 2, "position": "left"},
        {"text": "New Toxico Admission", "n": 3, "position": "left"},
        {"text": "Discharged", "exact": True, "n": 4, "position": "bottom"},
        {"text": "Details", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "File", "exact": True, "n": 6, "position": "top", "index": 0},
        {"text": "Discharge", "exact": True, "n": 7, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 560})

def open_adm(p):
    go(p, "/dashboard/toxico", 3000)
    p.get_by_text("New Toxico Admission").click()
    p.wait_for_timeout(1500)


def pick(p, query, name):
    p.fill("#tox-adm-search", query)
    p.wait_for_timeout(2200)
    dlg(p).get_by_role("button", name=name).first.click()
    p.wait_for_timeout(2500)


if "adm-search" in steps:
    open_adm(p)
    p.fill("#tox-adm-search", "Tchoua")
    p.wait_for_timeout(2200)
    shots.annotate(p, FIG / "adm-search.png", [
        {"selector": "#tox-adm-search", "n": 1, "position": "left"},
        {"text": "Nadine Tchoua", "n": 2, "position": "left"},
        {"text": "New patient", "n": 3, "position": "right"},
    ], crop="[role=dialog]")

if "adm-active" in steps:
    open_adm(p)
    pick(p, "Marcel", "Marcel")
    shots.annotate(p, FIG / "adm-active.png", [
        {"text": "already has an active", "n": 1, "position": "left", "outline": False},
        {"text": "Validate Admission", "n": 2, "position": "top"},
    ], crop="[role=dialog]")

if "adm-attach" in steps:
    open_adm(p)
    pick(p, "Tchoua", "Nadine")
    p.fill("#tox-adm-date", "2026-10-26")
    p.select_option("#tox-adm-substance", "Cannabis")
    p.select_option("#tox-adm-psy", label="Demo Psychologist")
    p.fill("#tox-adm-guardian", "Paul Tchoua")
    p.fill("#tox-adm-guardian-contact", "677889900")
    p.set_input_files("#tox-adm-file", CONSENT)
    p.fill("#tox-adm-notes", "Referred by her family after repeated absences from work. Consent signed on 25 October.")
    p.wait_for_timeout(800)
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "adm-attach.png", [
        {"text": "Change", "exact": True, "n": 1, "position": "left"},
        {"selector": "#tox-adm-date", "n": 2, "position": "right"},
        {"selector": "#tox-adm-substance", "n": 3, "position": "top"},
        {"selector": "#tox-adm-psy", "n": 4, "position": "top"},
        {"selector": "#tox-adm-guardian", "n": 5, "position": "top"},
        {"selector": "label[for=tox-adm-file]", "n": 6, "position": "top"},
        {"text": "Validate Admission", "n": 7, "position": "top"},
    ], crop="[role=dialog]")
    dlg(p).get_by_text("Validate Admission").click()
    p.wait_for_timeout(4000)
    txt(p, "adm-attach-after")
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.shot(p, FIG / "_adm-attach-after.png")

if "adm-new" in steps:
    open_adm(p)
    p.get_by_text("New patient", exact=True).click()
    p.wait_for_timeout(1200)
    p.fill("#tox-adm-first", "Samuel")
    p.fill("#tox-adm-last", "Biyick")
    p.fill("#tox-adm-dob", "1990-02-17")
    p.fill("#tox-adm-mother", "Berthe Biyick")
    p.fill("#tox-adm-address", "Yaounde, Mvog-Ada")
    p.fill("#tox-adm-contact", "677112200")
    p.select_option("#tox-adm-substance", "Cocaïne")
    p.select_option("#tox-adm-psy", label="Demo Psychologist")
    p.fill("#tox-adm-guardian", "Berthe Biyick")
    p.fill("#tox-adm-guardian-contact", "677112201")
    p.set_viewport_size({"width": 1600, "height": 1700})
    p.wait_for_timeout(600)
    shots.annotate(p, FIG / "adm-new.png", [
        {"selector": "#tox-adm-first", "n": 1, "position": "top"},
        {"selector": "#tox-adm-dob", "n": 2, "position": "top"},
        {"selector": "#tox-adm-mother", "n": 3, "position": "top"},
        {"selector": "#tox-adm-contact", "n": 4, "position": "top"},
        {"text": "Validate Admission", "n": 5, "position": "top"},
    ], crop="[role=dialog]")
    dlg(p).get_by_text("Validate Admission").click()
    p.wait_for_timeout(4000)
    txt(p, "adm-new-after")
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.shot(p, FIG / "_adm-new-after.png")

if "details" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Nadine Tchoua", "Details")
    txt(p, "details")
    (HERE / "_details-dlg.txt").write_text(dlg(p).inner_text(), encoding="utf-8")
    shots.annotate(p, FIG / "details.png", [
        {"text": "Identity", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Legal guardian", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "Open the full file", "n": 3, "position": "top"},
    ], crop="[role=dialog]")

if "file" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Odile Fotso", "File")
    shots.annotate(p, FIG / "file-history.png", [
        {"text": "Toxico History", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Medical Record", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Prescriptions", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Export record (PDF)", "n": 4, "position": "top"},
        {"text": "Discharge", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Close the file", "n": 6, "position": "top"},
    ])
    p.get_by_role("tab", name="Medical Record").click()
    p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "file-medical.png", [
        {"text": "Last 3 medical records", "n": 1, "position": "right", "outline": False},
        {"text": "See full history", "n": 2, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_role("tab", name="Prescriptions").click()
    p.wait_for_timeout(2500)
    txt(p, "file-rx")
    shots.annotate(p, FIG / "file-rx.png", [
        {"text": "Last 3 prescriptions", "n": 1, "position": "right", "outline": False},
        {"text": "See full history", "n": 2, "position": "left"},
    ], crop="[role=dialog]")

if "full" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Odile Fotso", "File")
    p.get_by_role("tab", name="Medical Record").click()
    p.wait_for_timeout(2000)
    p.get_by_text("See full history").click()
    p.wait_for_timeout(5000)
    print("URL", p.url)
    txt(p, "full")
    shots.annotate(p, FIG / "full-file.png", [
        {"text": "Medical Record", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Exams", "exact": True, "n": 2, "position": "top"},
        {"text": "Treatments", "exact": True, "n": 3, "position": "top"},
        {"text": "Toxicology Follow-up", "exact": True, "n": 4, "position": "top"},
        {"text": "Export PDF", "exact": True, "n": 5, "position": "top"},
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 520})
    p.get_by_text("Toxicology Follow-up", exact=True).click()
    p.wait_for_timeout(3000)
    txt(p, "full-tox")
    shots.shot(p, FIG / "_full-tox.png")
    p.get_by_text("Treatments", exact=True).click()
    p.wait_for_timeout(3000)
    txt(p, "full-treat")
    shots.shot(p, FIG / "_full-treat.png")
    p.get_by_text("Exams", exact=True).click()
    p.wait_for_timeout(3000)
    txt(p, "full-exams")

if "patients" in steps:
    go(p, "/dashboard/patients", 4000)
    p.fill("input[placeholder^='Search by name']", "Tchoua")
    p.wait_for_timeout(2500)
    txt(p, "patients")
    shots.annotate(p, FIG / "_patients.png", [])

if "offline" in steps:
    p.context.close()
    pw.stop()
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/dashboard/toxico")
    p.wait_for_timeout(9000)
    toast_close(p)
    shots.annotate(p, FIG / "offline-list.png", [
        {"text": "Offline", "n": 1, "position": "bottom"},
        {"text": "0 patients followed", "n": 2, "position": "right", "outline": False},
        {"text": "No patient found.", "n": 3, "position": "right", "outline": False},
        {"text": "New Toxico Admission", "n": 4, "position": "left"},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
    p.get_by_text("New Toxico Admission").click()
    p.wait_for_timeout(1500)
    p.get_by_text("New patient", exact=True).click()
    p.wait_for_timeout(800)
    p.fill("#tox-adm-first", "Test"); p.fill("#tox-adm-last", "Offline")
    p.fill("#tox-adm-dob", "1990-01-01"); p.fill("#tox-adm-mother", "Mere Offline")
    p.select_option("#tox-adm-psy", index=1) if p.locator("#tox-adm-psy option").count() > 1 else None
    p.fill("#tox-adm-guardian", "X Offline"); p.fill("#tox-adm-guardian-contact", "600000000")
    p.wait_for_timeout(500)
    print("psy options:", p.locator("#tox-adm-psy option").count())
    txt(p, "offline-adm")

if "account" in steps:
    go(p, "/dashboard/toxico", 2500)
    p.locator("button[aria-label='My Account']").click()
    p.wait_for_timeout(1200)
    shots.annotate(p, FIG / "account.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"text": "Password", "exact": True, "n": 2, "position": "bottom", "outline": False},
        {"text": "Phone", "exact": True, "n": 3, "position": "left", "outline": False},
        {"text": "Save", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 440, "y": 200, "width": 720, "height": 460})

if "export" in steps:
    # The PDF is fetched with the session token and rendered to a figure (the browser download itself is not captured).
    import json, urllib.request
    import pypdfium2 as pdfium
    tok = {}
    p.on("request", lambda r: tok.__setitem__("a", r.headers.get("authorization")) if r.headers.get("authorization") and r.url.startswith("http://127.0.0.1:8000") else None)
    go(p, "/dashboard/toxico", 4000)
    def api(u):
        return urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000" + u, headers={"Authorization": tok["a"]})).read()
    rows = json.loads(api("/toxico/patients?search=Tchoua"))["data"]
    pid = [r for r in rows if "Nadine" in r["patientName"]][0]["patient_id"]
    pdf = api(f"/toxico/patients/{pid}/export")
    (HERE / "_export.pdf").write_bytes(pdf)
    img = pdfium.PdfDocument(str(HERE / "_export.pdf"))[0].render(scale=2).to_pil()
    img.crop((0, 0, img.width, int(img.height * 0.62))).save(FIG / "export-pdf.png")
    print("export bytes", len(pdf))
