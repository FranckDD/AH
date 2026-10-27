"""Retake of production-2 figures (batch 3, 27 Oct 2026). python docs/user-guides/src/production-2/retake_b3.py [step ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *
FIG = Path("docs/user-guides/src/production-2/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-production2"
steps = sys.argv[1:] or ["explore"]
pw, br, p = shots.launch(width=1600, height=2300, profile_dir=PROFILE)
fresh(p)
shots.login(p, "production")
p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
def toast_close():
    try:
        p.locator("[class*=border-l-4] button").first.click(timeout=800)
    except Exception: pass
def gor(route, settle=3000):
    shots.goto(p, route); p.wait_for_timeout(settle); toast_close()
def open_batch(number):
    gor("/dashboard/fabrication-lots")
    p.locator("tr:has-text('%s')" % number).get_by_text("Open", exact=True).click(); p.wait_for_timeout(3000); toast_close()
def pick(sel, contains):
    for l in p.locator(sel + " option").all_inner_texts():
        if contains in l:
            p.select_option(sel, label=l); return l
    raise SystemExit("no option")
if "explore" in steps:
    gor("/dashboard/fabrication-lots")
    print("LOTS", txt(p, 3500)[250:])
if "shipped" in steps:
    open_batch("FAB-2026-0004")
    y0 = int(p.get_by_text("Balance", exact=True).first.bounding_box()["y"]) - 40
    yc = int(p.get_by_text("Cost per good bottle", exact=True).bounding_box()["y"]) + 110
    shots.annotate(p, FIG / "shipped.png", [
        {"text": "Out of tolerance", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "Frozen at shipping", "exact": True, "n": 2, "position": "right"},
        {"text": "Shortfall justification", "n": 3, "position": "right"},
        {"text": "Cost per good bottle", "exact": True, "n": 4, "position": "top"},
    ], crop={"x": 262, "y": y0, "width": 1338, "height": yc - y0})
if "draft" in steps:
    # demo data: a new Miel Pure draft (cancelled again at the end)
    gor("/dashboard/fabrication-lots")
    p.get_by_text("New batch", exact=True).first.click(); p.wait_for_timeout(1000)
    pick("#fab-batch-product", "Miel Pure")
    p.fill("#fab-batch-producer", "Demo producer")
    p.locator("button[form=fab-batch-form]").click(); p.wait_for_timeout(3500)
    print("BATCH", p.locator("h1").first.inner_text().strip())
    for i, (c, q) in enumerate((("honey jars", "5"), ("glass bottles", "20"))):
        p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(500)
        print("OPTS", p.locator("#fab-draft-purchase-%d option" % i).all_inner_texts())
        pick("#fab-draft-purchase-%d" % i, c); p.fill("#fab-draft-qty-%d" % i, q)
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(3000)
    toast_close()
    shots.annotate(p, FIG / "draft.png", [
        {"text": "Consumptions", "exact": True, "n": 1, "position": "top", "index": 0},
        {"selector": "#fab-draft-purchase-0", "n": 2, "position": "top"},
        {"selector": "#fab-draft-qty-0", "n": 3, "position": "top"},
        {"text": "Remove", "exact": True, "n": 4, "position": "right", "index": 0},
        {"text": "Add a line", "exact": True, "n": 5, "position": "left"},
        {"text": "Cancel batch", "exact": True, "n": 6, "position": "top"},
        {"text": "Save", "exact": True, "n": 7, "position": "top", "index": 0},
        {"text": "Start production", "exact": True, "n": 8, "position": "top"},
    ], crop={"x": 160, "y": 160, "width": 1440, "height": 1000})
if "draftcancel" in steps:
    gor("/dashboard/fabrication-lots")
    p.locator("tr:has-text('Draft')").first.get_by_text("Open", exact=True).click(); p.wait_for_timeout(3000)
    p.get_by_text("Cancel batch", exact=True).click(); p.wait_for_timeout(1500)
    p.locator("[role=dialog] textarea").first.fill("Demo draft prepared for a screenshot.")
    p.get_by_text("Confirm cancellation", exact=True).click(); p.wait_for_timeout(2500)
    print("CANCELLED", txt(p, 600)[250:])
shots.close(pw, br)
