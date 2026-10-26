"""Capture script for guide production-1. Run from the repo root:
    python docs/user-guides/src/production-1/capture.py [step ...]
Steps that act on the dev database are marked "acts". Demo data is fake.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["explore"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-production1"


def txt(p, name, n=2500):
    (HERE / f"_{name}.txt").write_text(p.inner_text("body"), encoding="utf-8")
    print("-----", name); print(p.inner_text("body")[:n].encode("ascii", "replace").decode())


def toast_close(p):
    try:
        p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
        p.wait_for_timeout(400)
    except Exception:
        pass


def go(p, route, settle=2500):
    shots.goto(p, route)
    p.wait_for_timeout(settle)
    toast_close(p)


def session(offline=False, height=1000):
    pw, br, p = shots.launch(width=1600, height=height, profile_dir=str(PROFILE), offline=offline)
    if not offline:
        shots.login(p, "production")
        p.wait_for_timeout(2500)
    p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
    return pw, br, p


if "explore" in steps:
    pw, br, p = session()
    print("URL", p.url)
    txt(p, "home", 2500)
    shots.shot(p, FIG / "_home.png")
    go(p, "/dashboard/fabrication-intrants")
    txt(p, "intrants", 4000)
    shots.shot(p, FIG / "_intrants.png")
    shots.close(pw, br)

if "explore2" in steps:
    pw, br, p = session()
    go(p, "/dashboard/fabrication-suivi", 4000)
    txt(p, "suivi", 3500)
    shots.shot(p, FIG / "_suivi.png")
    go(p, "/dashboard/fabrication-lots/1", 3000)
    txt(p, "lot1", 3000)
    shots.shot(p, FIG / "_lot1.png")
    for r in ["patients", "stock-control", "stock-lots", "lab-stock-products", "logs", "finance"]:
        go(p, "/dashboard/" + r, 1500)
        print("=====", r, p.url, p.inner_text("body")[330:520].replace("\n", " ").encode("ascii", "replace").decode())
    go(p, "/dashboard/fabrication-intrants", 6000)
    print(p.inner_text("header")[:300] if p.locator("header").count() else "")
    try:
        p.locator("button[aria-label*='otification']").first.click(); p.wait_for_timeout(1200)
    except Exception as e:
        print("bell?", e)
    txt(p, "bell", 1500)
    shots.shot(p, FIG / "_bell.png")
    shots.close(pw, br)

CROP = {"x": 160, "y": 60, "width": 840, "height": 800}
WIDE = {"x": 160, "y": 60, "width": 1440, "height": 700}

if "menu" in steps:
    pw, br, p = session()
    go(p, "/dashboard/fabrication-lots")
    shots.annotate(p, FIG / "menu.png", [
        {"text": "Production", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "Production batches", "exact": True, "n": 2, "position": "right", "index": 0},
        {"text": "Inputs and purchases", "exact": True, "n": 3, "position": "right", "index": 0},
        {"text": "Tracking and anomalies", "exact": True, "n": 4, "position": "right", "index": 0},
    ], crop={"x": 0, "y": 60, "width": 330, "height": 340})
    shots.close(pw, br)

if "screen" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    shots.annotate(p, FIG / "screen.png", [
        {"text": "New purchase", "exact": True, "n": 1, "position": "left"},
        {"text": "Show deactivated", "exact": True, "n": 2, "position": "right"},
        {"text": "Remaining stock", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Alert threshold", "exact": True, "n": 4, "position": "top"},
        {"text": "State", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Deactivate", "exact": True, "n": 6, "position": "top", "index": 0},
        {"text": "Input purchases", "exact": True, "n": 7, "position": "top"},
        {"text": "Cancel purchase", "exact": True, "n": 8, "position": "top", "index": 0},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 880})
    shots.close(pw, br)

FORM_SEL = "#fab-purchase-form"

def open_form(p):
    p.get_by_text("New purchase", exact=True).first.click(); p.wait_for_timeout(1200)

if "buy" in steps:
    # acts: purchase GD-P1-BUY-1 (50 honey jars at 160) on the existing input (run once)
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    open_form(p)
    txt(p, "buy-form", 1800)
    p.select_option("#fab-purchase-intrant", label="Guide demo honey jars (jar)")
    p.fill("#fab-purchase-supplier", "Demo Farm Supplies")
    p.fill("#fab-purchase-ref", "GD-P1-BUY-1")
    p.fill("#fab-purchase-qty", "50")
    p.fill("#fab-purchase-cost", "160")
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "buy-form.png", [
        {"text": "Existing input", "exact": True, "n": 1, "position": "left"},
        {"selector": "#fab-purchase-intrant", "n": 2, "position": "top"},
        {"selector": "#fab-purchase-supplier", "n": 3, "position": "top"},
        {"selector": "#fab-purchase-ref", "n": 4, "position": "top"},
        {"selector": "#fab-purchase-date", "n": 5, "position": "top"},
        {"selector": "#fab-purchase-qty", "n": 6, "position": "top"},
        {"selector": "#fab-purchase-cost", "n": 7, "position": "top"},
        {"selector": "button[form=fab-purchase-form]", "n": 8, "position": "top"},
    ])
    p.locator("button[form=fab-purchase-form]").click(); p.wait_for_timeout(2500)
    txt(p, "buy-saved", 2500)
    shots.annotate(p, FIG / "buy-saved.png", [
        {"text": "Purchase saved.", "n": 1, "position": "right", "outline": False},
        {"text": "GD-P1-BUY-1", "exact": True, "n": 2, "position": "top"},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 880})
    shots.close(pw, br)

TALL = {"x": 160, "y": 60, "width": 1440, "height": 1100}

if "buyfig" in steps:
    pw, br, p = session(height=1250)
    go(p, "/dashboard/fabrication-intrants")
    shots.annotate(p, FIG / "buy-saved.png", [
        {"selector": "tr:has-text('Locked') >> nth=1 >> td >> nth=2", "n": 1, "position": "right"},
        {"selector": "tr:has-text('GD-P1-BUY-1') >> td >> nth=2", "n": 2, "position": "top"},
        {"selector": "tr:has-text('GD-P1-BUY-1') >> td >> nth=5", "n": 3, "position": "top"},
    ], crop=TALL)
    shots.close(pw, br)

if "newinput" in steps:
    # acts: creates the input "Guide demo cork stoppers" with purchase GD-P1-BUY-2 (run once)
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    open_form(p)
    p.get_by_text("New input", exact=True).click(); p.wait_for_timeout(500)
    p.fill("#fab-intrant-name", "Guide demo cork stoppers")
    p.fill("#fab-intrant-unit", "piece")
    p.fill("#fab-purchase-supplier", "Demo Cork Co")
    p.fill("#fab-purchase-ref", "GD-P1-BUY-2")
    p.fill("#fab-purchase-qty", "400")
    p.fill("#fab-purchase-cost", "25")
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "new-input-form.png", [
        {"text": "New input", "exact": True, "n": 1, "position": "left"},
        {"selector": "#fab-intrant-name", "n": 2, "position": "top"},
        {"selector": "#fab-intrant-unit", "n": 3, "position": "top"},
        {"text": "This is a container", "n": 4, "position": "right"},
        {"selector": "#fab-purchase-qty", "n": 5, "position": "top"},
        {"selector": "#fab-purchase-cost", "n": 6, "position": "top"},
    ])
    p.locator("button[form=fab-purchase-form]").click(); p.wait_for_timeout(2500)
    txt(p, "newinput-saved", 2200)
    shots.close(pw, br)

if "cancel" in steps:
    # acts: refused cancel of GD-P2-BUY-1 (already used), cancel of GD-P1-BUY-2 (run once)
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    row = p.locator("tr:has-text('GD-P2-BUY-1')")
    row.get_by_text("Cancel purchase", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#fab-cancel-reason", "Entered by mistake.")
    p.locator("button[form=fab-cancel-form]").click(); p.wait_for_timeout(2000)
    txt(p, "cancel-refused", 1500)
    shots.annotate(p, FIG / "cancel-refused.png", [
        {"selector": "#fab-cancel-reason", "n": 1, "position": "top"},
        {"selector": "[role=alert]", "n": 2, "position": "right", "outline": False},
        {"selector": "button[form=fab-cancel-form]", "n": 3, "position": "top"},
    ])
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(600)
    row = p.locator("tr:has-text('GD-P1-BUY-2')")
    row.get_by_text("Cancel purchase", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#fab-cancel-reason", "Wrong unit cost typed. The purchase will be entered again.")
    shots.annotate(p, FIG / "cancel-form.png", [
        {"selector": "#fab-cancel-reason", "n": 1, "position": "top"},
        {"selector": "button[form=fab-cancel-form]", "n": 2, "position": "top"},
    ])
    p.locator("button[form=fab-cancel-form]").click(); p.wait_for_timeout(2500)
    txt(p, "cancel-done", 2200)
    shots.annotate(p, FIG / "cancel-done.png", [
        {"text": "Purchase cancelled.", "n": 1, "position": "right", "outline": False},
        {"text": "Edit", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": "tr:has-text('GD-P1-BUY-2') >> td >> nth=7", "n": 3, "position": "top"},
    ], crop=TALL)
    shots.close(pw, br)

DLG = {"x": 340, "y": 150, "width": 930, "height": 560}

if "edit" in steps:
    # acts: edits unit of cork stoppers, deactivates, reactivates, re-enters the purchase GD-P1-BUY-3 (run once)
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    p.locator("tr:has-text('cork stoppers')").first.get_by_text("Edit", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#fab-edit-unit", "pcs"); p.wait_for_timeout(300)
    shots.annotate(p, FIG / "edit-input.png", [
        {"selector": "#fab-edit-name", "n": 1, "position": "top"},
        {"selector": "#fab-edit-unit", "n": 2, "position": "top"},
        {"text": "This is a container", "n": 3, "position": "right"},
        {"selector": "button[form=fab-edit-form]", "n": 4, "position": "top"},
    ], crop=DLG)
    p.locator("button[form=fab-edit-form]").click(); p.wait_for_timeout(2000)
    txt(p, "edit-saved", 1200)
    p.locator("tr:has-text('cork stoppers')").first.get_by_text("Deactivate", exact=True).click(); p.wait_for_timeout(1000)
    txt(p, "deact-panel", 1500)
    shots.annotate(p, FIG / "deactivate.png", [
        {"text": "Deactivate this input?", "n": 1, "position": "right", "outline": False},
        {"selector": "button:has-text('Deactivate') >> nth=-1", "n": 2, "position": "top"},
    ], crop=DLG)
    p.locator("button:has-text('Deactivate')").last.click(); p.wait_for_timeout(2000)
    txt(p, "deact-done", 1500)
    p.get_by_text("Show deactivated", exact=True).click(); p.wait_for_timeout(1500)
    txt(p, "show-inactive", 1500)
    shots.annotate(p, FIG / "inactive.png", [
        {"text": "Show deactivated", "exact": True, "n": 1, "position": "right"},
        {"text": "Deactivated", "exact": True, "n": 2, "position": "right", "index": 0},
        {"text": "Reactivate", "exact": True, "n": 3, "position": "top"},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 560})
    p.get_by_text("Reactivate", exact=True).click(); p.wait_for_timeout(800)
    p.locator("button:has-text('Reactivate')").last.click(); p.wait_for_timeout(2000)
    txt(p, "react-done", 1200)
    open_form(p)
    p.select_option("#fab-purchase-intrant", label="Guide demo cork stoppers (pcs)")
    p.fill("#fab-purchase-supplier", "Demo Cork Co"); p.fill("#fab-purchase-ref", "GD-P1-BUY-3")
    p.fill("#fab-purchase-qty", "400"); p.fill("#fab-purchase-cost", "20")
    p.locator("button[form=fab-purchase-form]").click(); p.wait_for_timeout(2500)
    txt(p, "rebuy", 2500)
    shots.close(pw, br)

if "react" in steps:
    # acts: reactivates cork stoppers and records purchase GD-P1-BUY-3 (run once)
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    p.get_by_text("Show deactivated", exact=True).click(); p.wait_for_timeout(1500)
    p.get_by_role("button", name="Reactivate").first.click(); p.wait_for_timeout(1000)
    txt(p, "react-panel", 1800)
    shots.annotate(p, FIG / "reactivate.png", [
        {"text": "Reactivate this input?", "n": 1, "position": "right", "outline": False},
        {"selector": "button:has-text('Reactivate') >> nth=-1", "n": 2, "position": "top"},
    ], crop=DLG)
    p.get_by_role("button", name="Reactivate").last.click(); p.wait_for_timeout(2000)
    txt(p, "react-done", 1200)
    open_form(p)
    p.select_option("#fab-purchase-intrant", label="Guide demo cork stoppers (pcs)")
    p.fill("#fab-purchase-supplier", "Demo Cork Co"); p.fill("#fab-purchase-ref", "GD-P1-BUY-3")
    p.fill("#fab-purchase-qty", "400"); p.fill("#fab-purchase-cost", "20")
    p.locator("button[form=fab-purchase-form]").click(); p.wait_for_timeout(2500)
    txt(p, "rebuy", 2500)
    shots.close(pw, br)

if "lotpeek" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-lots")
    p.locator("tr:has-text('FAB-2026-0001')").get_by_text("Open", exact=True).click(); p.wait_for_timeout(2500)
    print(p.url)
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(800)
    txt(p, "lotpeek", 3500)
    for o in p.locator("select option").all_inner_texts()[:40]:
        print("OPT", o.encode("ascii", "replace").decode())
    shots.close(pw, br)

ADMIN_PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-production1-admin"

def admin_threshold(value):
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=str(ADMIN_PROFILE))
    shots.login(p, "admin"); p.wait_for_timeout(2500)
    go(p, "/dashboard/fabrication-intrants")
    p.locator("tr:has-text('honey jars')").first.get_by_text("Set threshold", exact=True).click(); p.wait_for_timeout(600)
    p.fill("#fab-threshold-%s" % "", value) if False else None
    inp = p.locator("input[id^=fab-threshold-]:visible").first
    inp.fill(value)
    shots.shot(p, FIG / "_admin-threshold.png", crop={"x": 160, "y": 60, "width": 1440, "height": 560})
    p.get_by_role("button", name="Save threshold").first.click(); p.wait_for_timeout(2000)
    txt(p, "admin-threshold-" + value, 1800)
    shots.close(pw, br)

if "thr_on" in steps:
    # acts (admin account): honey jars threshold set to 300
    admin_threshold("300")

if "thr_off" in steps:
    # acts (admin account): honey jars threshold back to 0
    admin_threshold("0")

if "alerts" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    txt(p, "alert-intrants", 1800)
    shots.annotate(p, FIG / "alert.png", [
        {"text": "300", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Below threshold", "exact": True, "n": 2, "position": "right"},
        {"text": "Stock sufficient", "exact": True, "n": 3, "position": "right", "index": 0},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 540})
    go(p, "/dashboard/fabrication-suivi", 3500)
    txt(p, "alert-suivi", 3000)
    shots.close(pw, br)

if "suivifig" in steps:
    pw, br, p = session(height=1100)
    go(p, "/dashboard/fabrication-suivi", 3500)
    shots.annotate(p, FIG / "suivi-alert.png", [
        {"text": "Anomalies", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Input below its alert threshold", "exact": True, "n": 2, "position": "top"},
        {"text": "Stock 220 jar, threshold 300 jar.", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 1000})
    shots.close(pw, br)

if "filter" in steps:
    pw, br, p = session(height=1100)
    go(p, "/dashboard/fabrication-intrants")
    p.fill("#fab-purchases-from", "2026-10-27"); p.wait_for_timeout(1500)
    txt(p, "filter-future", 2500)
    p.fill("#fab-purchases-to", "2026-10-26"); p.wait_for_timeout(1500)
    txt(p, "filter-range", 2500)
    p.fill("#fab-purchases-from", "2026-10-26"); p.wait_for_timeout(1500)
    txt(p, "filter-today", 2800)
    p.fill("#fab-purchases-from", "2026-10-27"); p.wait_for_timeout(1000)
    p.fill("#fab-purchases-to", "2026-10-26"); p.wait_for_timeout(1000)
    shots.annotate(p, FIG / "filter.png", [
        {"selector": "#fab-purchases-from", "n": 1, "position": "top"},
        {"selector": "#fab-purchases-to", "n": 2, "position": "top"},
        {"text": "The start date must be before the end date.", "n": 3, "position": "right", "outline": False},
        {"text": "Clear dates", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 900})
    shots.close(pw, br)

if "profile" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    p.locator("header button:has(svg)").nth(-2).click() if False else None
    shots.annotate(p, FIG / "header.png", [
        {"text": "Offline", "n": 1, "position": "bottom", "index": 0},
        {"text": "EN", "exact": True, "n": 2, "position": "bottom", "index": 0},
        {"text": "Logout", "exact": True, "n": 4, "position": "bottom", "index": 0},
    ], crop={"x": 160, "y": 0, "width": 1440, "height": 130})
    shots.close(pw, br)

if "profile2" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    btns = p.locator("header button, header a")
    print([ (b.inner_text()[:20], b.get_attribute("aria-label")) for b in btns.all()])
    shots.close(pw, br)

if "header" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-intrants")
    shots.annotate(p, FIG / "header.png", [
        {"text": "your entries are saved", "n": 1, "position": "bottom", "index": 0},
        {"text": "EN", "exact": True, "n": 2, "position": "bottom", "index": 0},
        {"selector": "[aria-label='My Account']", "n": 3, "position": "bottom"},
        {"text": "Logout", "exact": True, "n": 4, "position": "bottom", "index": 0},
    ], crop={"x": 160, "y": 0, "width": 1440, "height": 130})
    p.locator("[aria-label='My Account']").click(); p.wait_for_timeout(1500)
    txt(p, "account", 1800)
    shots.annotate(p, FIG / "account.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Password", "exact": True, "n": 2, "position": "top", "index": 0},
    ])
    shots.close(pw, br)

if "forbidden" in steps:
    pw, br, p = session(height=800)
    go(p, "/dashboard/patients", 1500)
    shots.shot(p, FIG / "forbidden.png", crop={"x": 160, "y": 60, "width": 1440, "height": 500})
    txt(p, "forbidden", 800)
    shots.close(pw, br)

if "offline" in steps:
    pw, br, p = session(offline=True, height=900)
    go(p, "/dashboard/fabrication-intrants", 4000)
    txt(p, "offline", 1500)
    shots.shot(p, FIG / "_offline.png", crop={"x": 160, "y": 0, "width": 1440, "height": 600})
    shots.close(pw, br)

if "offline2" in steps:
    pw, br, p = session(offline=True, height=900)
    go(p, "/dashboard/fabrication-intrants", 3000)
    open_form(p)
    print(p.locator("#fab-purchase-intrant option").all_inner_texts())
    p.get_by_text("New input", exact=True).click(); p.wait_for_timeout(300)
    p.fill("#fab-intrant-name", "Guide demo offline test"); p.fill("#fab-intrant-unit", "kg")
    p.fill("#fab-purchase-qty", "5"); p.fill("#fab-purchase-cost", "10")
    p.locator("button[form=fab-purchase-form]").click(); p.wait_for_timeout(4000)
    txt(p, "offline-save", 1500)
    shots.annotate(p, FIG / "offline.png", [
        {"text": "Could not save", "n": 1, "position": "right", "outline": False},
        {"selector": "button[form=fab-purchase-form]", "n": 2, "position": "top"},
    ], crop={"x": 330, "y": 50, "width": 940, "height": 700})
    shots.close(pw, br)

D2 = {"x": 330, "y": 170, "width": 940, "height": 680}

if "retake" in steps:
    pw, br, p = session(height=1100)
    go(p, "/dashboard/fabrication-intrants")
    shots.annotate(p, FIG / "screen.png", [
        {"text": "New purchase", "exact": True, "n": 1, "position": "left"},
        {"text": "Show deactivated", "exact": True, "n": 2, "position": "right"},
        {"text": "Remaining stock", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Alert threshold", "exact": True, "n": 4, "position": "top"},
        {"text": "State", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Deactivate", "exact": True, "n": 6, "position": "top", "index": 0},
        {"text": "Input purchases", "exact": True, "n": 7, "position": "top"},
        {"text": "Cancel purchase", "exact": True, "n": 8, "position": "top", "index": 0},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 800})
    shots.annotate(p, FIG / "buy-saved.png", [
        {"selector": "tr:has-text('Locked') >> nth=2 >> td >> nth=2", "n": 1, "position": "right"},
        {"selector": "tr:has-text('GD-P1-BUY-1') >> td >> nth=2", "n": 2, "position": "top"},
        {"selector": "tr:has-text('GD-P1-BUY-1') >> td >> nth=5", "n": 3, "position": "top"},
    ], crop={"x": 160, "y": 180, "width": 1440, "height": 640})
    # new input form, not saved
    open_form(p)
    p.get_by_text("New input", exact=True).click(); p.wait_for_timeout(500)
    p.fill("#fab-intrant-name", "Guide demo cork stoppers"); p.fill("#fab-intrant-unit", "piece")
    p.fill("#fab-purchase-supplier", "Demo Cork Co"); p.fill("#fab-purchase-ref", "GD-P1-BUY-2")
    p.fill("#fab-purchase-qty", "400"); p.fill("#fab-purchase-cost", "25"); p.wait_for_timeout(300)
    shots.annotate(p, FIG / "new-input-form.png", [
        {"text": "New input", "exact": True, "n": 1, "position": "left"},
        {"selector": "#fab-intrant-name", "n": 2, "position": "top"},
        {"selector": "#fab-intrant-unit", "n": 3, "position": "top"},
        {"text": "This is a container", "n": 4, "position": "right"},
        {"selector": "#fab-purchase-qty", "n": 5, "position": "top"},
        {"selector": "#fab-purchase-cost", "n": 6, "position": "top"},
    ], crop={"x": 330, "y": 80, "width": 940, "height": 860})
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(600)
    # existing-input form, not saved
    open_form(p)
    p.select_option("#fab-purchase-intrant", label="Guide demo honey jars (jar)")
    p.fill("#fab-purchase-supplier", "Demo Farm Supplies"); p.fill("#fab-purchase-ref", "GD-P1-BUY-1")
    p.fill("#fab-purchase-qty", "50"); p.fill("#fab-purchase-cost", "160"); p.wait_for_timeout(300)
    shots.annotate(p, FIG / "buy-form.png", [
        {"text": "Existing input", "exact": True, "n": 1, "position": "left"},
        {"selector": "#fab-purchase-intrant", "n": 2, "position": "top"},
        {"selector": "#fab-purchase-supplier", "n": 3, "position": "top"},
        {"selector": "#fab-purchase-ref", "n": 4, "position": "top"},
        {"selector": "#fab-purchase-date", "n": 5, "position": "top"},
        {"selector": "#fab-purchase-qty", "n": 6, "position": "top"},
        {"selector": "#fab-purchase-cost", "n": 7, "position": "top"},
        {"selector": "button[form=fab-purchase-form]", "n": 8, "position": "top"},
    ], crop={"x": 330, "y": 170, "width": 940, "height": 680})
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(600)
    # cancel form on the active cork purchase, not confirmed
    p.locator("tr:has-text('GD-P1-BUY-3')").get_by_text("Cancel purchase", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#fab-cancel-reason", "Wrong unit cost typed. The purchase will be entered again.")
    shots.annotate(p, FIG / "cancel-form.png", [
        {"selector": "#fab-cancel-reason", "n": 1, "position": "top"},
        {"selector": "button[form=fab-cancel-form]", "n": 2, "position": "top"},
    ], crop={"x": 330, "y": 200, "width": 940, "height": 480})
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(600)
    # refused cancel
    p.locator("tr:has-text('GD-P2-BUY-1')").get_by_text("Cancel purchase", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#fab-cancel-reason", "Entered by mistake.")
    p.locator("button[form=fab-cancel-form]").click(); p.wait_for_timeout(2000)
    shots.annotate(p, FIG / "cancel-refused.png", [
        {"selector": "#fab-cancel-reason", "n": 1, "position": "top"},
        {"selector": "[role=alert]", "n": 2, "position": "right", "outline": False},
        {"selector": "button[form=fab-cancel-form]", "n": 3, "position": "top"},
    ], crop={"x": 330, "y": 200, "width": 940, "height": 480})
    shots.close(pw, br)
    # suivi anomalies card
    pw, br, p = session(height=1100)
    go(p, "/dashboard/fabrication-suivi", 3500)

if "retake2" in steps:
    pw, br, p = session(height=1250)
    go(p, "/dashboard/fabrication-intrants")
    shots.annotate(p, FIG / "buy-saved.png", [
        {"selector": "tr:has-text('Locked') >> nth=2 >> td >> nth=2", "n": 1, "position": "right"},
        {"text": "GD-P1-BUY-1", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "160 FCFA", "exact": True, "n": 3, "position": "top", "index": 0},
    ], crop={"x": 160, "y": 180, "width": 1440, "height": 860})
    shots.close(pw, br)
