"""Retake of assistant-1 figures (batch 3, 27 Oct 2026). python docs/user-guides/src/assistant-1/retake_b3.py [step ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *
FIG = Path("docs/user-guides/src/assistant-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-assistant1"
steps = sys.argv[1:] or ["explore"]
OFFLINE = "offline" in steps
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=OFFLINE)
if not OFFLINE:
    fresh(p)
    shots.login(p, "assistant")
p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
def toast_close():
    for sel in ("[class*=border-l-4] button",):
        try: p.locator(sel).first.click(timeout=800)
        except Exception: pass
def gor(route, settle=3000):
    shots.goto(p, route); p.wait_for_timeout(settle); toast_close()
if "explore" in steps:
    gor("/dashboard/stock-lots")
    print("LOTS", txt(p, 3500)[250:])
    shots.shot(p, FIG / "_tmp.png")
if "newlot" in steps:
    # demo data: a lot created by the assistant (Honey, 30, Demo apiary)
    gor("/dashboard/stock-lots")
    p.get_by_text("New lot", exact=True).click(); p.wait_for_timeout(1500)
    p.select_option("#lot-product", label="Honey")
    p.fill("#lot-quantity", "30"); p.fill("#lot-expiry", "2027-09-30"); p.fill("#lot-producer", "Demo apiary")
    p.locator("button[form=lot-form]").click(); p.wait_for_timeout(3000)
if "lots" in steps:
    gor("/dashboard/stock-lots")
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.annotate(p, FIG / "lots.png", [
        {"text": "New lot", "exact": True, "n": 1, "position": "left"},
        {"selector": "#lots-status", "n": 2, "position": "right"},
        {"text": "Status", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Mark delivered", "exact": True, "n": 4, "position": "top", "index": 0},
        {"text": "Cancel", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 760})
if "movements" in steps:
    gor("/dashboard/stock-movements", 3500)
    p.select_option("#mov-product", label="Efferalgan"); p.click("button[type=submit]"); p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "movements.png", [
        {"selector": "#mov-search", "n": 1, "position": "top"},
        {"selector": "#mov-product", "n": 2, "position": "top"},
        {"selector": "#mov-type", "n": 3, "position": "bottom"},
        {"text": "Movement type", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Author", "exact": True, "n": 5, "position": "top"},
    ], crop={"x": 276, "y": 80, "width": 1324, "height": 680})
if "offline" in steps:
    p.goto(shots.BASE_URL + "/dashboard/stock-lots"); p.wait_for_timeout(9000)
    toast_close()
    print("OFF", txt(p, 800)[250:])
    shots.annotate(p, FIG / "offline-lots.png", [
        {"text": "Offline", "n": 1, "position": "bottom", "index": 0},
        {"text": "Unable to load data.", "n": 2, "position": "right", "outline": False},
        {"text": "No lots.", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 520})
if "bell" in steps:
    gor("/dashboard/stock-receipts", 4000)
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "bottom"},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=1", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 520})
shots.close(pw, br)
