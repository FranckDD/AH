"""Capture script for guide toxico-2. Run from the repo root:
    python docs/user-guides/src/toxico-2/capture.py [step ...]
Steps (discharge-* and readmit perform real actions in the dev database, run once, in order):
    signin dischargeform discharge-odile discharge-nadine discharge-marcel tab filters readmit file exports offline account
Demo patients (fake): Odile Fotso (recovery), Nadine Tchoua (hospitalised by the doctor, then discharged),
Marcel Ebogo (dropout, then readmitted), Samuel Biyick (stays active).
Scratch files are named _*.
"""
import sys, json, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-tox1"
CONSENT = r"C:\Users\DD\AppData\Local\Temp\claude\c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2\27ff0bbd-56cf-4861-b20d-d557a0b9deb2\scratchpad\consent-tchoua.pdf"


def go(p, route, settle=3500):
    shots.goto(p, route)
    p.wait_for_timeout(settle)
    try:
        p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception:
        pass


def txt(p, name, loc=None):
    t = (loc or p.locator("body")).inner_text()
    (HERE / f"_{name}.txt").write_text(t, encoding="utf-8")


def dlg(p):
    return p.locator("[role=dialog]").last


def row_action(p, name, action):
    p.locator("tr", has_text=name).first.get_by_text(action, exact=True).click()
    p.wait_for_timeout(2000)


def tab(p, name):
    p.get_by_role("tab", name=name).first.click()
    p.wait_for_timeout(3000)


alerts = []

if "signin" in steps:
    pass

pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
shots.login(p, "toxico")
p.on("dialog", lambda d: (alerts.append(d.message), d.accept()))


def discharge(p, name, reason, note, fig=None, marks=None):
    go(p, "/dashboard/toxico")
    row_action(p, name, "Discharge")
    p.get_by_text(reason, exact=True).click()
    if note:
        p.fill("#discharge-note", note)
    p.wait_for_timeout(400)
    if fig:
        shots.annotate(p, FIG / fig, marks, crop="[role=dialog]")
    dlg(p).get_by_text("Confirm discharge").click()
    p.wait_for_timeout(3500)
    print("alerts", alerts)
    txt(p, "after-" + name.split()[0])


if "dischargeform" in steps:
    go(p, "/dashboard/toxico")
    row_action(p, "Samuel Biyick", "Discharge")
    p.get_by_text("Other", exact=True).click()
    dlg(p).get_by_text("Confirm discharge").click()
    p.wait_for_timeout(800)
    shots.annotate(p, FIG / "discharge-other.png", [
        {"text": "Other", "exact": True, "n": 1, "position": "left"},
        {"selector": "#discharge-note", "n": 2, "position": "left"},
        {"text": "A note is required", "n": 3, "position": "right", "outline": False},
        {"text": "Confirm discharge", "n": 4, "position": "top"},
    ], crop="[role=dialog]")
    dlg(p).get_by_text("Cancel").click()

if "discharge-odile" in steps:
    discharge(p, "Odile Fotso", "Recovery", "Completed the programme. Family informed, follow-up visit planned in one month.",
              "discharge-form.png", [
        {"text": "Recovery", "exact": True, "n": 1, "position": "left"},
        {"selector": "#discharge-note", "n": 2, "position": "left"},
        {"text": "Confirm discharge", "n": 3, "position": "top"},
    ])

if "discharge-nadine" in steps:
    discharge(p, "Nadine Tchoua", "Dropout", "Left the centre against advice while on a drip at the hospital ward.")

if "discharge-marcel" in steps:
    discharge(p, "Marcel Ebogo", "Dropout", "Did not come back after a family visit. Family unreachable.")

if "tab" in steps:
    go(p, "/dashboard/toxico")
    tab(p, "Discharged")
    txt(p, "tab")
    shots.annotate(p, FIG / "discharged-tab.png", [
        {"text": "Discharged", "exact": True, "n": 1, "position": "top", "index": 0},
        {"selector": "#tox-dis-search", "n": 2, "position": "top"},
        {"selector": "#tox-dis-reason", "n": 3, "position": "top"},
        {"selector": "#tox-dis-from", "n": 4, "position": "top"},
        {"text": "Export PDF", "n": 5, "position": "left"},
    ], crop={"x": 256, "y": 100, "width": 1344, "height": 700})


def to_discharged(p):
    go(p, "/dashboard/toxico")
    tab(p, "Discharged")


if "filters" in steps:
    to_discharged(p)
    p.fill("#tox-dis-reason", "") if False else None
    p.select_option("#tox-dis-reason", "abandon")
    p.wait_for_timeout(2500)
    txt(p, "f-reason")
    p.select_option("#tox-dis-reason", "")
    p.fill("#tox-dis-search", "Ebogo")
    p.wait_for_timeout(2500)
    txt(p, "f-search")
    p.fill("#tox-dis-search", "")
    p.fill("#tox-dis-from", "2026-10-27")
    p.wait_for_timeout(2500)
    txt(p, "f-date")
    p.fill("#tox-dis-from", "2026-10-26")
    p.fill("#tox-dis-to", "2026-10-20")
    p.wait_for_timeout(2500)
    txt(p, "f-bad")
    shots.shot(p, FIG / "_f-bad.png")

if "view" in steps:
    to_discharged(p)
    row_action(p, "Marcel Ebogo", "View record")
    txt(p, "view")
    shots.shot(p, FIG / "_view.png")

if "readmit0" in steps:
    to_discharged(p)
    row_action(p, "Marcel Ebogo", "Readmit")
    txt(p, "readmit0", dlg(p))
    shots.shot(p, FIG / "_readmit0.png")


if "readmit" in steps:
    to_discharged(p)
    row_action(p, "Marcel Ebogo", "Readmit")
    p.fill("#tox-adm-date", "2026-10-25")
    p.select_option("#tox-adm-psy", label="Demo Psychologist")
    p.fill("#tox-adm-guardian", "Joseph Ebogo")
    p.fill("#tox-adm-guardian-contact", "677445566")
    p.wait_for_timeout(600)
    txt(p, "readmit-early", dlg(p))
    dlg(p).get_by_text("Validate Admission").click()
    p.wait_for_timeout(2500)
    txt(p, "readmit-early-after", dlg(p))
    shots.shot(p, FIG / "_readmit-early.png")
    p.fill("#tox-adm-date", "2026-10-26")
    p.fill("#tox-adm-notes", "Brought back by the family after the dropout. Agreed to restart the programme.")
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.wait_for_timeout(600)
    shots.annotate(p, FIG / "readmit-form.png", [
        {"text": "Patient already followed", "n": 1, "position": "left", "outline": False},
        {"selector": "#tox-adm-date", "n": 2, "position": "right"},
        {"selector": "#tox-adm-psy", "n": 3, "position": "top"},
        {"selector": "#tox-adm-guardian", "n": 4, "position": "top"},
        {"text": "Validate Admission", "n": 5, "position": "top"},
    ], crop="[role=dialog]")
    dlg(p).get_by_text("Validate Admission").click()
    p.wait_for_timeout(4000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    txt(p, "readmit-after")
    shots.shot(p, FIG / "_readmit-after.png")

if "newadm-discharged" in steps:
    go(p, "/dashboard/toxico")
    p.get_by_text("New Toxico Admission").click()
    p.wait_for_timeout(1500)
    p.fill("#tox-adm-search", "Fotso")
    p.wait_for_timeout(2200)
    dlg(p).get_by_role("button", name="Odile").first.click()
    p.wait_for_timeout(2500)
    txt(p, "newadm-discharged", dlg(p))
    shots.shot(p, FIG / "_newadm-discharged.png")


if "exports" in steps:
    import io
    import pypdfium2 as pdfium
    seen = []
    p.on("response", lambda r: seen.append((r.status, r.url.split("8000")[-1], r.headers.get("content-type"))) if "export" in r.url else None)
    to_discharged(p)
    p.get_by_text("Export PDF", exact=True).click()
    p.wait_for_timeout(4000)
    tr = p.locator("tr", has_text="Odile Fotso").first
    tr.get_by_text("PDF", exact=True).click()
    p.wait_for_timeout(4000)
    print("responses", seen)
    txt(p, "exports-ui")
    shots.annotate(p, FIG / "exports-buttons.png", [
        {"text": "Export PDF", "exact": True, "n": 1, "position": "left"},
        {"text": "PDF", "exact": True, "n": 2, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 520})
    # files fetched with the session token (browser downloads are not captured)
    tok = {}
    p.on("request", lambda r: tok.__setitem__("a", r.headers.get("authorization")) if r.headers.get("authorization") and r.url.startswith("http://127.0.0.1:8000") else None)
    go(p, "/dashboard/toxico", 3500)
    def api(u):
        return urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000" + u, headers={"Authorization": tok["a"]})).read()
    lst = api("/toxico/dossiers/discharged/export?search=Fotso")
    (HERE / "_list-export.pdf").write_bytes(api("/toxico/dossiers/discharged/export?reason=abandon"))
    (HERE / "_odile.pdf").write_bytes(api("/toxico/patients/19301/export"))
    (HERE / "_marcel.pdf").write_bytes(api("/toxico/patients/19306/export"))
    for n in ("_list-export", "_odile", "_marcel"):
        d = pdfium.PdfDocument(str(HERE / f"{n}.pdf")); print(n, len(d))
        d[0].render(scale=2).to_pil().save(FIG / f"{n}-p1.png")


if "buttons" in steps:
    to_discharged(p)
    shots.annotate(p, FIG / "exports-buttons.png", [
        {"text": "Export PDF", "exact": True, "n": 1, "position": "left"},
        {"text": "PDF", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Readmit", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "View record", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 520})

if "file" in steps:
    go(p, "/dashboard/toxico")
    row_action(p, "Marcel Ebogo", "File")
    txt(p, "file-marcel", dlg(p))
    dlg(p).evaluate("e => { for (const d of e.querySelectorAll('*')) { if (d.scrollHeight > d.clientHeight + 50 && getComputedStyle(d).overflowY !== 'visible') d.scrollTop = 99999 } }")
    p.wait_for_timeout(600)
    shots.annotate(p, FIG / "file-stays.png", [
        {"text": "Interrompu", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "Stay 2", "exact": True, "n": 2, "position": "left", "outline": False},
        {"text": "Ongoing", "exact": True, "n": 3, "position": "right"},
        {"selector": "[role=dialog] button:has-text('Discharge')", "n": 4, "position": "top"},
    ], crop="[role=dialog]")

if "view-odile" in steps:
    to_discharged(p)
    row_action(p, "Odile Fotso", "View record")
    txt(p, "view-odile", dlg(p))
    shots.annotate(p, FIG / "view-discharged.png", [
        {"text": "Discharged from programme", "n": 1, "position": "right", "outline": False},
        {"text": "Recovery", "exact": True, "n": 2, "position": "right", "index": 1, "outline": False},
        {"text": "Export record (PDF)", "n": 3, "position": "top"},
    ])

if "offline" in steps:
    p.context.close(); pw.stop()
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/dashboard/toxico")
    p.wait_for_timeout(9000)
    p.get_by_role("tab", name="Discharged").click()
    p.wait_for_timeout(4000)
    txt(p, "offline")
    shots.annotate(p, FIG / "offline-discharged.png", [
        {"text": "Offline", "n": 1, "position": "bottom"},
        {"text": "Discharged", "exact": True, "n": 2, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 800})


if "full" in steps:
    go(p, "/dashboard/toxico")
    tab(p, "Discharged")
    row_action(p, "Odile Fotso", "View record")
    p.get_by_role("tab", name="Medical Record").click()
    p.wait_for_timeout(2000)
    p.get_by_text("See full history").click()
    p.wait_for_timeout(5000)
    p.get_by_text("Toxicology Follow-up", exact=True).click()
    p.wait_for_timeout(3000)
    txt(p, "full-odile")
    shots.annotate(p, FIG / "full-tox-discharged.png", [
        {"text": "Toxicology Follow-up", "exact": True, "n": 1, "position": "top"},
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 620})


if "defaultsub" in steps:
    to_discharged(p)
    row_action(p, "Odile Fotso", "Readmit")
    print("SUBSTANCE", p.input_value("#tox-adm-substance"), "| GUARDIAN", repr(p.input_value("#tox-adm-guardian")), "| DATE", p.input_value("#tox-adm-date"))

shots.close(pw, br)
