"""Capture script for guide nurse-2. Run from the repo root:
    python docs/user-guides/src/nurse-2/capture.py [step ...]
Steps (several perform real actions in the dev database, run once, in this order):
    plan-head plan-nurse hosp-list admit status aggravation discharge letter
Demo data (fake): shifts created for 26 Oct to 1 Nov 2026 for Demo Nurse, Etto Leto,
Demo Head Nurse and Infirmier Test; Odile Fotso (19301) admitted by the nurse;
Cyrille Mbonda (nurse stay) discharged by the nurse.
Scratch files are named _*; delete them when the guide is finished.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["plan-head"]
SDD = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides"


def go(p, route, settle=2500):
    shots.goto(p, route)
    try:
        p.get_by_text("Connected").first.wait_for(timeout=30000)
    except Exception:
        pass
    p.wait_for_timeout(settle)


def txt(p, name):
    (HERE / f"_{name}.txt").write_text(p.inner_text("body"), encoding="utf-8")


def day(p, ddmmyyyy):
    p.get_by_label(ddmmyyyy).first.click()
    p.wait_for_timeout(700)


def assign(p, ddmmyyyy, idx, nurse):
    """idx 0 morning, 1 afternoon, 2 night"""
    day(p, ddmmyyyy)
    p.get_by_label("Select a nurse").nth(idx).select_option(label=nurse)
    p.get_by_role("button", name="Add a nurse").nth(idx).click()
    p.wait_for_timeout(1200)


def hosp_tab(p, pid):
    go(p, f"/medical/patients/{pid}")
    p.get_by_role("tab", name="Hospitalization").click()
    p.wait_for_timeout(1500)


PLAN = [  # (date, shift idx, nurse)
    ("26/10/2026", 0, "Demo Nurse"), ("26/10/2026", 1, "Etto Leto"), ("26/10/2026", 2, "Infirmier Test (Head nurse)"),
    ("27/10/2026", 0, "Demo Head Nurse (Head nurse)"), ("27/10/2026", 1, "Demo Nurse"), ("27/10/2026", 2, "Etto Leto"),
    ("28/10/2026", 0, "Etto Leto"), ("28/10/2026", 0, "Demo Nurse"), ("28/10/2026", 2, "Demo Head Nurse (Head nurse)"),
    ("29/10/2026", 1, "Infirmier Test (Head nurse)"), ("29/10/2026", 2, "Demo Nurse"),
    ("30/10/2026", 0, "Demo Nurse"), ("30/10/2026", 1, "Demo Head Nurse (Head nurse)"),
]

if "plan-head" in steps:
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=SDD / "chrome-profile-head_nurse")
    shots.login(p, "head_nurse")
    go(p, "/medical/nurse-shifts")
    day(p, "27/10/2026")
    shots.annotate(p, FIG / "plan-empty.png", [
        {"text": "Nurse Schedule", "exact": True, "n": 1, "position": "right", "outline": False, "index": 1},
        {"text": "Month", "exact": True, "n": 2, "position": "top"},
        {"text": "Today", "exact": True, "n": 3, "position": "top", "index": 1},
        {"selector": "[aria-label='Select a nurse'] >> nth=0", "n": 4, "position": "left"},
        {"text": "Add a nurse", "exact": True, "n": 5, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 620})
    for d, i, n in PLAN:
        assign(p, d, i, n)
    day(p, "28/10/2026")
    p.get_by_label("Select a nurse").nth(0).select_option(index=1)
    shots.annotate(p, FIG / "plan-filled.png", [
        {"text": "Week", "exact": True, "n": 1, "position": "top"},
        {"text": "Remove", "exact": True, "n": 2, "position": "left", "index": 0},
        {"selector": "[aria-label='Select a nurse'] >> nth=0", "n": 3, "position": "left"},
        {"text": "Add a nurse", "exact": True, "n": 4, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 620})
    txt(p, "plan-filled")
    shots.close(pw, br)

if "reshoot-plan" in steps:
    pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-head_nurse")
    shots.login(p, "head_nurse")
    go(p, "/medical/nurse-shifts")
    nxt = p.get_by_label("Next week")
    nxt.click(); p.wait_for_timeout(800); nxt.click(); p.wait_for_timeout(1200)
    day(p, "10/11/2026")
    while p.get_by_text("Remove", exact=True).count():   # leave the demo week empty
        p.get_by_text("Remove", exact=True).first.click()
        p.wait_for_timeout(1200)
    shots.annotate(p, FIG / "plan-empty.png", [
        {"text": "Month", "exact": True, "n": 1, "position": "top"},
        {"text": "Today", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": "[aria-label='Select a nurse'] >> nth=0", "n": 3, "position": "left"},
        {"text": "Add a nurse", "exact": True, "n": 4, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 190, "width": 1344, "height": 640})
    p.get_by_label("Select a nurse").nth(0).select_option(label="Demo Nurse")
    p.get_by_role("button", name="Add a nurse").nth(0).click()
    p.wait_for_timeout(1500)
    p.get_by_label("Select a nurse").nth(0).select_option(label="Etto Leto")
    p.get_by_role("button", name="Add a nurse").nth(0).click()
    p.wait_for_timeout(1500)
    txt(p, "added")
    shots.annotate(p, FIG / "plan-added.png", [
        {"text": "Remove", "exact": True, "n": 1, "position": "left", "index": 1},
        {"text": "Add a nurse", "exact": True, "n": 2, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 190, "width": 1344, "height": 640})
    p.get_by_text("Remove", exact=True).nth(1).click()
    p.wait_for_timeout(1500)
    txt(p, "removed")
    while p.get_by_text("Remove", exact=True).count():
        p.get_by_text("Remove", exact=True).first.click()
        p.wait_for_timeout(1200)
    p.get_by_role("button", name="Today", exact=True).click()
    p.wait_for_timeout(1200)
    day(p, "28/10/2026")
    shots.annotate(p, FIG / "plan-filled.png", [
        {"text": "Week", "exact": True, "n": 1, "position": "top"},
        {"text": "Remove", "exact": True, "n": 2, "position": "left", "index": 0},
        {"selector": "[aria-label='Select a nurse'] >> nth=0", "n": 3, "position": "left"},
        {"text": "Add a nurse", "exact": True, "n": 4, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 190, "width": 1344, "height": 800})
    # month view of the real week
    p.get_by_role("button", name="Today", exact=True).click()
    p.wait_for_timeout(800)
    p.get_by_role("button", name="Month", exact=True).click()
    p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "plan-month.png", [
        {"text": "Month", "exact": True, "n": 1, "position": "top"},
    ], crop={"x": 256, "y": 190, "width": 900, "height": 900})
    shots.close(pw, br)

if "plan-nurse" in steps:
    pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-nurse")
    shots.login(p, "nurse")
    go(p, "/medical/nurse-shifts")
    day(p, "27/10/2026")
    txt(p, "nurse-plan")
    shots.annotate(p, FIG / "plan-nurse.png", [
        {"text": "Month", "exact": True, "n": 1, "position": "top"},
        {"text": "Only the physician or the head nurse can edit this schedule.", "exact": True, "n": 2, "position": "top", "outline": False},
        {"selector": "[data-view=week] button >> nth=0 >> li >> nth=0", "n": 3, "position": "top", "outline": False},
    ], crop={"x": 256, "y": 190, "width": 1344, "height": 800})
    # the server refuses a direct write by a nurse who is not a head nurse
    print(p.evaluate("""async () => {
      const t = localStorage.getItem('token');
      const r = await fetch('http://127.0.0.1:8000/nurse-shifts/', {method: 'POST',
        headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + t},
        body: JSON.stringify({shift_date: '2026-11-20', shift_type: 'MATIN', nurse_id: 1})});
      return r.status + ' ' + await r.text();
    }"""))
    shots.close(pw, br)

if "hosp-list" in steps:
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=SDD / "chrome-profile-nurse")
    shots.login(p, "nurse")
    go(p, "/medical/hospitalizations")
    txt(p, "list")
    shots.annotate(p, FIG / "hosp-list.png", [
        {"text": "Hospitalized Patients", "exact": True, "n": 1, "position": "right", "outline": False, "index": 1},
        {"text": "Worsening", "exact": True, "n": 2, "position": "right", "index": 0},
        {"text": "View record", "exact": True, "n": 3, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 90, "width": 1344, "height": 420})
    p.get_by_text("Cyrille Mbonda").first.click()
    p.wait_for_timeout(3000)
    print("URL", p.url)
    shots.close(pw, br)

if "admit" in steps:
    pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-nurse")
    shots.login(p, "nurse")
    hosp_tab(p, 19301)
    txt(p, "odile-before")
    p.get_by_role("button", name="Admit", exact=True).click()
    p.wait_for_timeout(800)
    p.fill("#hosp-reason", "Dehydration after three days of diarrhoea. Oral rehydration not tolerated, intravenous fluids needed.")
    shots.annotate(p, FIG / "admit-form.png", [
        {"text": "Admit", "exact": True, "n": 1, "position": "left"},
        {"selector": "#hosp-reason", "n": 2, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 3, "position": "bottom"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 470})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "odile-after")
    shots.close(pw, br)

if "status" in steps:
    pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-nurse")
    shots.login(p, "nurse")
    hosp_tab(p, 19301)
    p.get_by_role("button", name="Update status", exact=True).click()
    p.wait_for_timeout(800)
    p.select_option("#hosp-status", "STABLE")
    p.fill("#hosp-status-note", "Drip running, 1 litre in 4 hours. Pulse 96, temperature 37.9. Drinking small sips.")
    shots.annotate(p, FIG / "status-form.png", [
        {"text": "Update status", "exact": True, "n": 1, "position": "left", "index": 0},
        {"selector": "#hosp-status", "n": 2, "position": "right"},
        {"selector": "#hosp-status-note", "n": 3, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 730})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    p.get_by_role("button", name="Update status", exact=True).click()
    p.wait_for_timeout(600)
    p.select_option("#hosp-status", "AGGRAVATION")
    p.fill("#hosp-status-note", "Repeated vomiting since 14:00, pulse 118, very drowsy. Drip stopped, doctor called.")
    shots.annotate(p, FIG / "aggravation-form.png", [
        {"selector": "#hosp-status", "n": 1, "position": "right"},
        {"selector": "#hosp-status-note", "n": 2, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 3, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 730})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "odile-status")
    shots.annotate(p, FIG / "status-card.png", [
        {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
        {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "Discharge", "exact": True, "n": 3, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 620})
    shots.close(pw, br)

if "discharge" in steps:
    pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-nurse")
    shots.login(p, "nurse")
    hosp_tab(p, 19300)
    txt(p, "cyrille-before")
    p.get_by_role("button", name="Update status", exact=True).click()
    p.wait_for_timeout(600)
    p.select_option("#hosp-status", "AMELIORATION")
    p.fill("#hosp-status-note", "Fever gone, eating, walking without help.")
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    p.get_by_role("button", name="Discharge", exact=True).click()
    p.wait_for_timeout(600)
    p.select_option("#hosp-discharge", "GUERI")
    p.fill("#hosp-discharge-note", "Afebrile for 48 hours. Finish the oral treatment. Review with a doctor in one week.")
    shots.annotate(p, FIG / "discharge-form.png", [
        {"text": "Discharge", "exact": True, "n": 1, "position": "left", "index": 0},
        {"selector": "#hosp-discharge", "n": 2, "position": "right"},
        {"selector": "#hosp-discharge-note", "n": 3, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 800})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "cyrille-after")
    shots.annotate(p, FIG / "discharged.png", [
        {"text": "Download discharge letter", "exact": True, "n": 1, "position": "left"},
        {"text": "Admit", "exact": True, "n": 2, "position": "left"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 520})
    with p.expect_download(timeout=30000) as d:
        p.get_by_text("Download discharge letter", exact=True).click()
    d.value.save_as(str(HERE / "_letter.pdf"))
    print("saved", d.value.suggested_filename)
    shots.close(pw, br)


if "reshoot" in steps:
    # Figures only, nothing saved.
    pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-nurse")
    shots.login(p, "nurse")
    hosp_tab(p, 19301)
    shots.annotate(p, FIG / "status-card.png", [
        {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
        {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "Discharge", "exact": True, "n": 3, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 460, "width": 1344, "height": 620})
    hosp_tab(p, 19300)
    shots.annotate(p, FIG / "discharged.png", [
        {"text": "Download discharge letter", "exact": True, "n": 1, "position": "top"},
        {"text": "Admit", "exact": True, "n": 2, "position": "left"},
    ], crop={"x": 256, "y": 460, "width": 1344, "height": 600})
    shots.close(pw, br)

if "offline" in steps:
    pw, br, p = shots.launch(width=1600, height=1250, profile_dir=SDD / "chrome-profile-head_nurse", offline=True)
    p.goto(shots.BASE_URL + "/medical/nurse-shifts")
    p.wait_for_timeout(8000)
    txt(p, "offline-shifts")
    shots.shot(p, FIG / "_offline-shifts.png")
    shots.close(pw, br)
