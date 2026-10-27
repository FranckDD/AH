"""Retake of lab-2 figures (batch 3, 27 Oct 2026). python docs/user-guides/src/lab-2/retake_b3.py [step ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *
FIG = Path("docs/user-guides/src/lab-2/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-lab2-laborantin"
steps = sys.argv[1:] or ["explore"]
ROLE = "promoteur" if "order" in steps else "laborantin"
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=str(PROFILE).replace("laborantin", ROLE))
fresh(p)
shots.login(p, ROLE)
if "order" in steps:
    # demo data: the promoter marks the Glucose request as ordered
    go(p, "/dashboard/lab-stock-requests")
    p.locator("tr:has-text('Glucose')").get_by_text("Mark as ordered", exact=True).click(); p.wait_for_timeout(800)
    p.fill("#lab-order-date", "2026-10-30")
    p.locator("button[form=lab-order-form]").click(); p.wait_for_timeout(2500)
    print("ORDERED", txt(p, 800)[300:])
if "explore" in steps:
    for r in ("lab-stock-products", "lab-stock-requests", "lab-stock-alerts", "lab-stock-movements", "lab-stock-count"):
        go(p, "/dashboard/" + r)
        print("==", r, txt(p, 1800)[300:])
if "report" in steps:
    # demo data: two stock reports (Glucose: Almost out, Urine strips: Out)
    go(p, "/dashboard/lab-stock-products")
    p.locator("tr:has-text('Glucose')").get_by_text("Report", exact=True).click(); p.wait_for_timeout(1000)
    p.get_by_text("Almost out", exact=True).click(); p.wait_for_timeout(2500)
    p.locator("tr:has-text('Urine')").get_by_text("Report", exact=True).click(); p.wait_for_timeout(1000)
    p.get_by_text("Out", exact=True).last.click(); p.wait_for_timeout(2500)
    print("REPORT", txt(p, 800)[300:])
if "figs" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    go(p, "/dashboard/lab-stock-products")
    shots.annotate(p, FIG / "products.png", [
        {"text": "Lab stock", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Add a product", "exact": True, "n": 2, "position": "left"},
        {"selector": "#lab-products-search", "n": 3, "position": "right"},
        {"text": "Stock", "exact": True, "n": 4, "position": "top", "index": 0},
        {"text": "Report", "exact": True, "n": 5, "position": "left", "index": 0},
        {"text": "Edit", "exact": True, "n": 6, "position": "right", "index": 0},
    ], crop={"x": 0, "y": 20, "width": 1600, "height": 560})
    go(p, "/dashboard/lab-stock-requests")
    p.select_option("#lab-requests-status", "all"); p.wait_for_timeout(1500)
    print("REQ", txt(p, 1500)[300:])
    shots.annotate(p, FIG / "requests.png", [
        {"text": "To order", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"selector": "#lab-requests-status", "n": 2, "position": "right"},
        {"text": "Origin", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Status", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Expected date", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 0, "y": 20, "width": 1600, "height": 620})
    go(p, "/dashboard/lab-stock-count")
    shots.annotate(p, FIG / "count-empty.png", [
        {"text": "Weekly count", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"selector": "#lab-count-search", "n": 2, "position": "right"},
        {"text": "Last stock", "exact": True, "n": 3, "position": "top"},
        {"text": "Counted quantity", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 800})
    go(p, "/dashboard/lab-stock-alerts")
    shots.annotate(p, FIG / "alerts.png", [
        {"text": "Weekly count", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Go to count", "exact": True, "n": 2, "position": "left"},
        {"selector": "#lab-alerts-low", "n": 3, "position": "top"},
        {"selector": "#lab-alerts-expiring", "n": 4, "position": "top"},
    ], crop={"x": 0, "y": 20, "width": 1600, "height": 760})
if "hist" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    go(p, "/dashboard/lab-stock-movements")
    shots.annotate(p, FIG / "history.png", [
        {"selector": "#lab-mv-product", "n": 1, "position": "right"},
        {"text": "Type", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Stock after", "exact": True, "n": 3, "position": "top"},
        {"text": "By", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 0, "y": 20, "width": 1600, "height": 900})
shots.close(pw, br)
