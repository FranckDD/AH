"""Capture script for guide psychologist-1. Run from the repo root:
    python docs/user-guides/src/psychologist-1/capture.py [step ...]
Steps: signin dashboard list search details file eval-form eval-progress eval-maintain eval-regress
       discharged export account offline
Several steps perform real actions (evaluations) in the dev database, so run them once.
Demo data (fake): Marcel Ebogo AH2-910314ER (patient 19305?, admitted 12 Oct 2026, Alcool) and
Odile Fotso AH2-781123FX (patient 19301, admitted 19 Oct 2026, Cannabis), both with Demo Psychologist.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin", "dashboard"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-psy1"


def go(p, route, settle=3500):
    shots.goto(p, route)
    p.wait_for_timeout(settle)


def txt(p, name):
    (HERE / f"_{name}.txt").write_text(p.inner_text("body"), encoding="utf-8")


def row_action(p, name, action):
    row = p.locator("tr", has_text=name).first
    row.get_by_text(action, exact=True).click()
    p.wait_for_timeout(2500)


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("psychologist")
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
    shots.login(p, "psychologist")

if "dashboard" in steps:
    go(p, "/dashboard/toxico-dashboard", 6000)
    shots.annotate(p, FIG / "dashboard.png", [
        {"text": "Toxicology Dashboard", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Active Patients", "exact": True, "n": 2, "position": "top", "outline": False},
        {"text": "Distribution by Phase", "exact": True, "n": 3, "position": "right", "outline": False},
        {"text": "Psychologist Workload", "exact": True, "n": 4, "position": "right", "outline": False},
        {"text": "Clinical Alerts", "exact": True, "n": 5, "position": "right", "outline": False},
    ])

if "list" in steps:
    go(p, "/dashboard/toxico", 4000)
    shots.annotate(p, FIG / "list.png", [
        {"text": "Toxicology Monitoring", "exact": True, "n": 1, "position": "left", "outline": False, "index": 1},
        {"selector": "#toxico-search", "n": 2, "position": "left"},
        {"text": "Discharged", "exact": True, "n": 3, "position": "bottom"},
        {"text": "Details", "exact": True, "n": 4, "position": "top", "index": 0},
        {"text": "File", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Evaluate", "exact": True, "n": 6, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 560})

if "details" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Marcel Ebogo", "Details")
    shots.annotate(p, FIG / "details.png", [
        {"text": "Identity", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Legal guardian", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "Open the full file", "n": 3, "position": "top"},
    ])

if "file" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Odile Fotso", "File")
    shots.annotate(p, FIG / "file-history.png", [
        {"text": "Toxico History", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Medical Record", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Prescriptions", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Export record (PDF)", "n": 4, "position": "top"},
        {"text": "Close the file", "n": 5, "position": "top"},
    ])
    p.get_by_role("tab", name="Medical Record").click()
    p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "file-medical.png", [
        {"text": "Last 3 medical records", "n": 1, "position": "right", "outline": False},
    ])

def open_eval(p, name):
    go(p, "/dashboard/toxico", 3000)
    row_action(p, name, "Evaluate")


if "eval-form" in steps:
    open_eval(p, "Marcel Ebogo")
    txt(p, "eval-form")
    shots.annotate(p, FIG / "eval-form.png", [
        {"text": "Maintain Phase", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"text": "Progression", "exact": True, "n": 2, "position": "bottom", "outline": False},
        {"text": "Regression / Relapse", "exact": True, "n": 3, "position": "bottom", "outline": False},
        {"selector": "#tox-eval-obs", "n": 4, "position": "left"},
        {"selector": "#tox-eval-reco", "n": 5, "position": "left"},
        {"text": "Submit Evaluation", "n": 6, "position": "top"},
    ])

if "eval-progress" in steps:
    open_eval(p, "Marcel Ebogo")
    p.get_by_text("Progression", exact=True).click()
    p.fill("#tox-eval-obs", "Withdrawal symptoms have settled. Sleeps well, attends the daily group, cooperative during the interview.")
    p.fill("#tox-eval-reco", "Start the detox programme. Weekly interview.")
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "eval-progress.png", [
        {"text": "Progression", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"selector": "#tox-eval-obs", "n": 2, "position": "left"},
        {"text": "Summary:", "n": 3, "position": "left", "outline": False},
        {"text": "Submit Evaluation", "n": 4, "position": "top"},
    ])
    p.get_by_text("Submit Evaluation").click()
    p.wait_for_timeout(4000)
    txt(p, "eval-progress-after")

if "eval-maintain" in steps:
    open_eval(p, "Odile Fotso")
    p.fill("#tox-eval-obs", "Still in withdrawal. Anxious at night, asks for her family. Keep the same plan.")
    p.wait_for_timeout(500)
    p.get_by_text("Submit Evaluation").click()
    p.wait_for_timeout(4000)
    txt(p, "eval-maintain-after")

if "eval-regress" in steps:
    open_eval(p, "Marcel Ebogo")
    p.get_by_text("Regression / Relapse", exact=True).click()
    p.fill("#tox-eval-obs", "Short")
    p.wait_for_timeout(500)
    txt(p, "eval-regress-short")
    shots.annotate(p, FIG / "eval-regress-short.png", [
        {"text": "Regression / Relapse", "exact": True, "n": 1, "position": "top", "outline": False},
        {"selector": "#tox-eval-obs", "n": 2, "position": "left"},
        {"text": "Submit Evaluation", "n": 3, "position": "top"},
    ])
    p.fill("#tox-eval-obs", "Left the centre for two days and drank again. Brought back by the family, very low mood.")
    p.fill("#tox-eval-reco", "Daily interview this week. Family meeting.")
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "eval-regress.png", [
        {"text": "Regression / Relapse", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"text": "Warning:", "n": 2, "position": "left", "outline": False},
        {"text": "Summary:", "n": 3, "position": "left", "outline": False},
        {"text": "Submit Evaluation", "n": 4, "position": "top"},
    ])
    p.get_by_text("Submit Evaluation").click()
    p.wait_for_timeout(4000)
    txt(p, "eval-regress-after")

if "history" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Marcel Ebogo", "File")
    txt(p, "history")
    shots.annotate(p, FIG / "file-evals.png", [
        {"text": "Stay 1", "n": 1, "position": "left", "outline": False},
    ])

if "discharged" in steps:
    go(p, "/dashboard/toxico", 3000)
    p.get_by_role("tab", name="Discharged").click()
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "discharged.png", [
        {"selector": "input[placeholder='Patient name or code']", "n": 1, "position": "bottom"},
        {"selector": "select", "n": 2, "position": "bottom"},
        {"text": "Export PDF", "exact": True, "n": 3, "position": "top"},
        {"text": "View record", "n": 4, "position": "top", "index": 0},
        {"text": "PDF", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 380, "width": 1344, "height": 500})

if "account" in steps:
    go(p, "/dashboard/toxico", 2500)
    p.locator("button[aria-label='My Account']").click()
    p.wait_for_timeout(1200)
    p.locator("input").nth(-1).fill("677010111")
    shots.annotate(p, FIG / "account.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"text": "Password", "exact": True, "n": 2, "position": "bottom", "outline": False},
        {"text": "Phone", "exact": True, "n": 3, "position": "left", "outline": False},
        {"text": "Save", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 440, "y": 200, "width": 720, "height": 400})
    p.get_by_text("Save", exact=True).click()
    p.wait_for_timeout(1500)
    txt(p, "account-saved")

if "offline" in steps:
    p.context.close() if hasattr(p, "context") else None
    pw.stop()
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/dashboard/toxico")
    p.wait_for_timeout(8000)
    shots.annotate(p, FIG / "offline.png", [
        {"text": "Offline", "n": 1, "position": "bottom"},
        {"text": "0 patients followed", "n": 2, "position": "right", "outline": False},
        {"text": "No patient found.", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
