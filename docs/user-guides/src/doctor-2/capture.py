"""Capture script for guide doctor-2. Run from the repo root:
    python docs/user-guides/src/doctor-2/capture.py [step ...]
Steps (several perform real actions in the dev database, so run them once and in this order):
    signin admit status aggravation list discharge readmit
Demo patients (fake): Linda Etoga 19295 (full stay, discharged, readmitted),
Rosine Ateba 19296 (stay with an aggravation alert), Nadine Fouda 19293, Pierre Kamdem 19294.
Scratch files are named _*; delete them when the guide is finished.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor2"


def go(p, route, settle=2500):
    shots.goto(p, route)
    try:
        p.get_by_text("Connected").first.wait_for(timeout=30000)
    except Exception:
        pass
    p.wait_for_timeout(settle)


def hosp_tab(p, pid):
    go(p, f"/medical/patients/{pid}")
    p.get_by_role("tab", name="Hospitalization").click()
    p.wait_for_timeout(1500)


def txt(p, name):
    (HERE / f"_{name}.txt").write_text(p.inner_text("body"), encoding="utf-8")


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("medecin")
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
    shots.login(p, "medecin")

if "admit" in steps:
    # Linda Etoga (19295) was admitted the same way beforehand (reason: severe pneumonia).
    # This step admits Rosine Ateba and takes the figures.
    hosp_tab(p, 19296)
    p.get_by_role("button", name="Admit", exact=True).click()
    p.wait_for_timeout(800)
    p.fill("#hosp-reason", "Severe malaria with vomiting and dehydration. Intravenous fluids and artesunate.")
    shots.annotate(p, FIG / "admit-form.png", [
        {"text": "Admit", "exact": True, "n": 1, "position": "left"},
        {"selector": "#hosp-reason", "n": 2, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 3, "position": "bottom"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 470})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "admit-after")
    shots.shot(p, FIG / "_admit-after.png")

if "status" in steps:
    hosp_tab(p, 19295)
    p.get_by_role("button", name="Update status", exact=True).click()
    p.wait_for_timeout(800)
    p.select_option("#hosp-status", "STABLE")
    p.fill("#hosp-status-note", "Fever 38.5. Oxygen at 2 litres. Taking fluids by mouth.")
    shots.annotate(p, FIG / "status-form.png", [
        {"text": "Update status", "exact": True, "n": 1, "position": "top", "index": 0},
        {"selector": "#hosp-status", "n": 2, "position": "right"},
        {"selector": "#hosp-status-note", "n": 3, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 600})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    p.get_by_role("button", name="Update status", exact=True).click()
    p.wait_for_timeout(600)
    p.select_option("#hosp-status", "AMELIORATION")
    p.fill("#hosp-status-note", "Fever down to 37.2. Off oxygen. Walking in the room.")
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "status-after")
    shots.annotate(p, FIG / "status-list.png", [
        {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
        {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 560})

if "reshoot-status" in steps:
    # Figures only, no saving (the stay of Linda Etoga is open with two updates).
    hosp_tab(p, 19295)
    p.set_viewport_size({"width": 1600, "height": 1200})
    p.get_by_role("button", name="Update status", exact=True).click()
    p.wait_for_timeout(800)
    p.fill("#hosp-status-note", "Fever down to 37.2. Off oxygen. Walking in the room.")
    shots.annotate(p, FIG / "status-form.png", [
        {"text": "Update status", "exact": True, "n": 1, "position": "left", "index": 0},
        {"selector": "#hosp-status", "n": 2, "position": "right"},
        {"selector": "#hosp-status-note", "n": 3, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 730})
    p.get_by_role("button", name="Update status", exact=True).first.click()
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "status-list.png", [
        {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
        {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "History", "exact": True, "n": 3, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 560})

if "aggravation" in steps:
    hosp_tab(p, 19296)
    p.get_by_role("button", name="Update status", exact=True).click()
    p.wait_for_timeout(600)
    p.select_option("#hosp-status", "AGGRAVATION")
    p.fill("#hosp-status-note", "Fever 39.8 and repeated vomiting. Drowsy. Blood sugar to check.")
    shots.annotate(p, FIG / "aggravation-form.png", [
        {"selector": "#hosp-status", "n": 1, "position": "right"},
        {"selector": "#hosp-status-note", "n": 2, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 3, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 730})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "aggravation-after")
    shots.annotate(p, FIG / "aggravation-after.png", [
        {"text": "Worsening", "exact": True, "n": 1, "position": "left", "index": 0},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 520})

if "list" in steps:
    go(p, "/medical/hospitalizations")
    txt(p, "list")
    shots.annotate(p, FIG / "hosp-list.png", [
        {"text": "Hospitalized Patients", "exact": True, "n": 1, "position": "right", "outline": False, "index": 1},
        {"text": "Current status", "exact": True, "n": 2, "position": "top", "outline": False},
        {"text": "View record", "exact": True, "n": 3, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 90, "width": 1344, "height": 420})

if "discharge" in steps:
    hosp_tab(p, 19295)
    p.get_by_role("button", name="Discharge", exact=True).click()
    p.wait_for_timeout(600)
    p.select_option("#hosp-discharge", "GUERI")
    p.fill("#hosp-discharge-note", "Afebrile for 48 hours, eating well. Finish oral antibiotics for 5 days. Review in the clinic in one week.")
    shots.annotate(p, FIG / "discharge-form.png", [
        {"text": "Discharge", "exact": True, "n": 1, "position": "left", "index": 0},
        {"selector": "#hosp-discharge", "n": 2, "position": "right"},
        {"selector": "#hosp-discharge-note", "n": 3, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 780})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "discharge-after")
    shots.annotate(p, FIG / "discharge-after.png", [
        {"text": "Download discharge letter", "exact": True, "n": 1, "position": "left"},
        {"text": "Admit", "exact": True, "n": 2, "position": "left"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 420})
    with p.expect_download() as d:
        p.get_by_role("button", name="Download discharge letter").click()
    d.value.save_as(str(HERE / "_letter.pdf"))

if "letter" in steps:
    hosp_tab(p, 19295)
    p.on("response", lambda r: print("RESP", r.status, r.url) if "discharge-letter" in r.url else None)
    p.on("console", lambda m: print("CON", m.text[:200]) if m.type == "error" else None)
    with p.expect_download(timeout=20000) as d:
        p.get_by_text("Download discharge letter", exact=True).click()
    d.value.save_as(str(HERE / "_letter.pdf"))
    print("saved", d.value.suggested_filename)

if "letter2" in steps:
    hosp_tab(p, 19295)
    p.on("requestfailed", lambda r: print("FAILED", r.url, r.failure))
    p.on("request", lambda r: print("REQ", r.url, r.headers.get("authorization", "")[:20]) if "discharge-letter" in r.url else None)
    p.get_by_text("Download discharge letter", exact=True).click()
    p.wait_for_timeout(5000)
    print(p.inner_text("body")[-300:])

if "letter3" in steps:
    hosp_tab(p, 19295)
    p.on("response", lambda r: print("RESP", r.status, r.url, r.headers) if "discharge-letter" in r.url else None)
    p.on("console", lambda m: print("CON", m.type, m.text[:300]))
    p.get_by_text("Download discharge letter", exact=True).click()
    p.wait_for_timeout(6000)

if "letter4" in steps:
    hosp_tab(p, 19295)
    print(p.evaluate("""async () => {
      const keys = Object.keys(localStorage); 
      const tk = localStorage.getItem('token') || localStorage.getItem('access_token');
      let out = {keys};
      try {
        const r = await fetch('http://127.0.0.1:8000/hospitalizations/1293/discharge-letter', {headers: {Authorization: 'Bearer ' + tk}});
        out.status = r.status; out.type = r.headers.get('content-type');
      } catch (e) { out.err = String(e); }
      try {
        const r = await fetch('http://127.0.0.1:8000/hospitalizations/current', {headers: {Authorization: 'Bearer ' + tk}});
        out.status2 = r.status;
      } catch (e) { out.err2 = String(e); }
      return out; }"""))

if "readmit" in steps:
    hosp_tab(p, 19295)
    p.get_by_role("button", name="Admit", exact=True).click()
    p.wait_for_timeout(600)
    p.fill("#hosp-reason", "Return of fever and cough five days after discharge. Chest X-ray requested.")
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "readmit-after")
    shots.annotate(p, FIG / "history.png", [
        {"text": "History", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Download discharge letter", "exact": True, "n": 2, "position": "left"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 620})

if "reshoot" in steps:
    # Figures only, nothing saved: Linda Etoga has an open second stay.
    hosp_tab(p, 19295)
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "history.png", [
        {"text": "History", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Download discharge letter", "exact": True, "n": 2, "position": "top"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 620})
    p.get_by_role("button", name="Discharge", exact=True).click()
    p.wait_for_timeout(600)
    p.select_option("#hosp-discharge", "GUERI")
    p.fill("#hosp-discharge-note", "Afebrile for 48 hours, eating well. Finish oral antibiotics for 5 days. Review in the clinic in one week.")
    shots.annotate(p, FIG / "discharge-form.png", [
        {"text": "Discharge", "exact": True, "n": 1, "position": "right", "index": 0},
        {"selector": "#hosp-discharge", "n": 2, "position": "right"},
        {"selector": "#hosp-discharge-note", "n": 3, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 820})

if "dashboard" in steps:
    go(p, "/medical/doctors")
    txt(p, "dashboard")
    shots.annotate(p, FIG / "dashboard.png", [
        {"text": "Current stays", "n": 1, "position": "top"},
        {"text": "Hospitalized patients", "n": 2, "position": "top", "outline": False},
    ])

if "followup" in steps:
    go(p, "/medical/patients/19295")
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.wait_for_timeout(800)
    txt(p, "followup-tab")
    shots.annotate(p, FIG / "followup-tab.png", [
        {"text": "Medical Record", "exact": True, "n": 1, "position": "top"},
        {"text": "New consultation", "n": 2, "position": "left"},
        {"text": "Modifier", "exact": True, "n": 3, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 1200})
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/medical/medical-records")
    p.fill("input[type=search], input[placeholder*='Search'], input[placeholder*='search']", "Etoga")
    p.wait_for_timeout(2500)
    txt(p, "consultations")
    shots.annotate(p, FIG / "consultations-patient.png", [
        {"selector": "input[type=search], input[placeholder*='Search'], input[placeholder*='search']", "n": 1, "position": "bottom"},
    ])
