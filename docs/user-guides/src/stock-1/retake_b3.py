"""Retake of stock-1 figures (batch 3, 27 Oct 2026). python docs/user-guides/src/stock-1/retake_b3.py [step ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *
FIG = Path("docs/user-guides/src/stock-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-stock1"
steps = sys.argv[1:] or ["explore"]
OFFLINE = "offline" in steps
pw, br, p = shots.launch(width=1600, height=1100, profile_dir=PROFILE, offline=OFFLINE)
if not OFFLINE:
    fresh(p)
    shots.login(p, "stock")
p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
def toast_close():
    try: p.locator("[class*=border-l-4] button").first.click(timeout=800)
    except Exception: pass
    try: p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception: pass
def gor(route, settle=3000):
    shots.goto(p, route); p.wait_for_timeout(settle); toast_close()
if "menu" in steps:
    gor("/dashboard/stock-control")
    p.get_by_text("Lab stock", exact=True).first.click(); p.wait_for_timeout(1000)
    shots.annotate(p, FIG / "menu.png", [
        {"text": "Stock management", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "To check", "exact": True, "n": 2, "position": "right", "index": 0},
        {"text": "Movements", "exact": True, "n": 3, "position": "right", "index": 0},
        {"text": "Stock count", "exact": True, "n": 4, "position": "right", "index": 0},
        {"text": "Lab stock", "exact": True, "n": 5, "position": "right", "index": 0},
    ], crop={"x": 0, "y": 60, "width": 330, "height": 700})
if "movements" in steps:
    gor("/dashboard/stock-movements", 3500)
    p.select_option("#mov-product", label="Efferalgan"); p.click("button[type=submit]"); p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "movements.png", [
        {"selector": "#mov-search", "n": 1, "position": "top"},
        {"selector": "#mov-product", "n": 2, "position": "top"},
        {"selector": "#mov-type", "n": 3, "position": "bottom"},
        {"text": "Movement type", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Author", "exact": True, "n": 5, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 680})
if "alerts" in steps:
    gor("/dashboard/lab-stock-alerts")
    shots.annotate(p, FIG / "lab-alerts.png", [
        {"selector": "h2 >> nth=1", "n": 1, "position": "top"},
        {"selector": "h2 >> nth=2", "n": 2, "position": "top"},
        {"selector": "h2 >> nth=3", "n": 3, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 760})
if "form" in steps:
    gor("/dashboard/lab-stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(2000)
    p.fill("#lab-invoice-number", "MS-2026-0460")
    p.fill("#lab-invoice-supplier", "MediLab Supplies")
    p.get_by_text("Add a product", exact=True).click(); p.wait_for_timeout(800)
    p.fill("#lab-picker-search", "Urine"); p.wait_for_timeout(500)
    p.locator("ul button:has-text('Urine test strips')").click(); p.wait_for_timeout(600)
    p.get_by_text("Add a product", exact=True).click(); p.wait_for_timeout(800)
    p.fill("#lab-picker-search", "Glucose"); p.wait_for_timeout(500)
    p.locator("ul button:has-text('Glucose reagent kit')").click(); p.wait_for_timeout(600)
    for i, (o, rcv, lot, exp, price) in enumerate([("20", "20", "UTS-2611", "2027-11-30", "4500"), ("10", "9", "GRK-2611", "2027-08-31", "12000")]):
        row = p.locator("tbody tr").nth(i)
        row.locator("input[aria-label='Qty ordered']").fill(o)
        row.locator("input[aria-label='Qty received']").fill(rcv)
        row.locator("input[aria-label='Lot']").fill(lot)
        row.locator("input[aria-label='Expiry']").fill(exp)
        row.locator("input[aria-label='Unit price']").fill(price)
    p.locator("tbody tr").nth(0).locator("input[type=checkbox]").check()
    p.wait_for_timeout(500)
    print("FORM", txt(p, 2500)[250:])
    shots.annotate(p, FIG / "lab-receipt-form.png", [
        {"selector": "#lab-invoice-number", "n": 1, "position": "top"},
        {"selector": "#lab-invoice-supplier", "n": 2, "position": "top"},
        {"selector": "#lab-invoice-date", "n": 3, "position": "top"},
        {"text": "Add a product", "exact": True, "n": 4, "position": "top", "index": 0},
        {"selector": "tbody tr >> nth=1 >> input[type=checkbox]", "n": 5, "position": "top"},
        {"selector": "tbody tr >> nth=0 >> input[aria-label='Qty received']", "n": 6, "position": "top"},
        {"text": "Confirm receipt", "exact": True, "n": 7, "position": "left"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 900})
if "offline" in steps:
    p.goto(shots.BASE_URL + "/dashboard/stock-control"); p.wait_for_timeout(9000)
    toast_close()
    print("OFF", txt(p, 800)[250:])
    shots.annotate(p, FIG / "offline.png", [
        {"text": "Offline", "n": 1, "position": "bottom", "index": 0},
        {"text": "Unable to load", "n": 2, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 520})
shots.close(pw, br)
