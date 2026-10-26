"""Capture script for guide spiritual-1. Run from the repo root:
    python docs/user-guides/src/spiritual-1/capture.py [step ...]
Steps: signin dashboard list search details file discharged record export account offline forbidden
The role is read-only: no step changes data. Demo patients come from the psychologist guide
(Marcel Ebogo AH2-910314ER, Odile Fotso AH2-781123FX).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin", "dashboard"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-spi1"


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
    acc = shots.account("spiritual")
    p.fill("#username", acc["username"])
    p.fill("#password", "demo-password")
    shots.annotate(p, FIG / "signin.png", [
        {"selector": "#username", "n": 1},
        {"selector": "#password", "n": 2},
        {"selector": "button[type=submit]", "n": 3},
    ], crop="form")
    shots.close(pw, br)

if any(s not in ("signin", "offline") for s in steps):
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
    shots.login(p, "spiritual")

if "dashboard" in steps:
    go(p, "/dashboard/toxico-dashboard", 6000)
    txt(p, "dashboard")
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
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 560})

if "search" in steps:
    go(p, "/dashboard/toxico", 3000)
    p.fill("#toxico-search", "Ebogo"); p.wait_for_timeout(2500); txt(p, "search-hit")
    p.fill("#toxico-search", "zzzz"); p.wait_for_timeout(2500); txt(p, "search-none")

if "details" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Marcel Ebogo", "Details")
    shots.annotate(p, FIG / "details.png", [
        {"text": "Identity", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Legal guardian", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "Open the full file", "n": 3, "position": "top"},
    ])
    p.locator("div[role=dialog]").first.evaluate("e => { const s = e.querySelector('.overflow-y-auto') || e; s.scrollTop = s.scrollHeight; }") if p.locator("div[role=dialog]").count() else None
    p.wait_for_timeout(500)
    txt(p, "details")

if "file" in steps:
    go(p, "/dashboard/toxico", 3000)
    row_action(p, "Odile Fotso", "File")
    txt(p, "file")
    p.get_by_text("Close the file").click(); p.wait_for_timeout(800)
    row_action(p, "Marcel Ebogo", "File")
    shots.annotate(p, FIG / "file-evals.png", [
        {"text": "Stay 1", "n": 1, "position": "left", "outline": False},
        {"text": "Relapse", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Recommendation", "n": 3, "position": "left", "outline": False, "index": 0},
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
    ], crop={"x": 256, "y": 380, "width": 1344, "height": 500})
    p.get_by_text("View record").first.click(); p.wait_for_timeout(3000); txt(p, "record")
    p.screenshot(path=str(FIG / "_record.png"))

if "export" in steps:
    go(p, "/dashboard/toxico", 3000)
    p.get_by_role("tab", name="Discharged").click(); p.wait_for_timeout(3000)
    try:
        with p.expect_download(timeout=15000) as d:
            p.get_by_text("Export PDF", exact=True).click()
        print("download:", d.value.suggested_filename)
    except Exception as e:
        print("no download event:", e)
    txt(p, "export")

if "account" in steps:
    go(p, "/dashboard/toxico", 2500)
    p.locator("button[aria-label='My Account']").click()
    p.wait_for_timeout(1200)
    shots.annotate(p, FIG / "account.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"text": "Password", "exact": True, "n": 2, "position": "bottom", "outline": False},
        {"text": "Phone", "exact": True, "n": 3, "position": "left", "outline": False},
        {"text": "Save", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 440, "y": 200, "width": 720, "height": 400})
    txt(p, "account")

if "forbidden" in steps:
    go(p, "/dashboard/patients", 2500)
    txt(p, "forbidden")
    shots.annotate(p, FIG / "forbidden.png", [{"text": "Accès Interdit", "n": 1, "position": "right", "outline": False}])

if "offline" in steps:
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/dashboard/toxico")
    p.wait_for_timeout(8000)
    txt(p, "offline")
    shots.annotate(p, FIG / "offline.png", [
        {"text": "Offline", "n": 1, "position": "bottom"},
        {"text": "0 patients followed", "n": 2, "position": "right", "outline": False},
        {"text": "No patient found.", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
