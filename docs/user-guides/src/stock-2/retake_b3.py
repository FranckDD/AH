"""Retake of stock-2 figures (batch 3, 27 Oct 2026). python docs/user-guides/src/stock-2/retake_b3.py [step ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *
FIG = Path("docs/user-guides/src/stock-2/figures")
P0 = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/"
steps = sys.argv[1:] or ["explore"]
ROLE = "admin" if "admin" in steps else "stock"
PROFILE = P0 / ("chrome-profile-stock2-admin" if ROLE == "admin" else "chrome-profile-stock1")
pw, br, p = shots.launch(width=1600, height=1500, profile_dir=PROFILE)
fresh(p)
shots.login(p, ROLE)
p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
if "explore" in steps:
    go(p, "/dashboard/stock-count", connected=False)
    print("START", txt(p, 1500)[250:])
    p.get_by_role("tab", name="History").click(); p.wait_for_timeout(2500)
    print("HIST", txt(p, 3500)[250:])
    shots.shot(p, FIG / "_hist.png")
def fill_qty(pid, value):
    f = p.locator(f"#qty-{pid}"); f.fill(value); f.press("Tab"); p.wait_for_timeout(300)
if "start" in steps:
    go(p, "/dashboard/stock-count", connected=False)
    try:
        p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=1500)
    except Exception: pass
    p.wait_for_timeout(800)
    shots.annotate(p, FIG / "start.png", [
        {"text": "Start a count", "exact": True, "n": 1, "position": "right"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 460})
if "form" in steps:
    # opens a count, types, then abandons it (no data left)
    go(p, "/dashboard/stock-count", connected=False)
    p.get_by_text("Start a count", exact=True).click(); p.wait_for_timeout(3000)
    for pid, v in ((7, "5"), (3, "12"), (4, "58"), (5, "29"), (10, "80")):
        fill_qty(pid, v)
    p.get_by_role("button", name="Note").nth(3).click(); p.wait_for_timeout(300)
    p.locator("#obs-4").fill("Two booklets lent to the ward, not yet returned."); p.wait_for_timeout(500)
    print("FORM", txt(p, 2500)[250:])
    shots.annotate(p, FIG / "count-form.png", [
        {"selector": "#count-search", "n": 1, "position": "top"},
        {"selector": "#qty-4", "n": 2, "position": "top"},
        {"selector": "#obs-4", "n": 3, "position": "right"},
        {"text": "product(s) counted out of", "n": 4, "position": "top"},
        {"text": "Validate the count", "exact": True, "n": 5, "position": "top"},
        {"text": "Abandon the count", "exact": True, "n": 6, "position": "left"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 1400})
    p.get_by_text("Abandon the count", exact=True).click(); p.wait_for_timeout(2500)
if "hist" in steps:
    p.set_viewport_size({"width": 1600, "height": 1500})
    go(p, "/dashboard/stock-count", connected=False)
    p.get_by_role("tab", name="History").click(); p.wait_for_timeout(2000)
    shots.annotate(p, FIG / "history.png", [
        {"selector": "#count-date-from", "n": 1, "position": "top"},
        {"text": "Lines", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "View details", "exact": True, "n": 3, "position": "top", "index": 1},
        {"text": "My adjustment requests", "exact": True, "n": 4, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 1300})
    p.get_by_text("View details", exact=True).nth(1).click(); p.wait_for_timeout(2000)
    p.set_viewport_size({"width": 1600, "height": 2400}); p.wait_for_timeout(800)
    y = p.get_by_text("Count no. 1123", exact=False).first.bounding_box()["y"]
    shots.annotate(p, FIG / "history-detail.png", [
        {"text": "System", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Gap", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Movements after counting", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Adjustment request", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 276, "y": int(y) - 30, "width": 1324, "height": 560})
shots.close(pw, br)
