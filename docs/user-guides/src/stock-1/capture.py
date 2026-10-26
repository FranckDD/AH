"""Capture script for guide stock-1. Run from the repo root:
    python docs/user-guides/src/stock-1/capture.py [step ...]
Steps that act on the dev database are marked "acts". Data prepared with the API (assistant account) before
the capture: receipts REC-20261026-006 (lot 004, Miel Pure) and -007 (supplier), damage reports 1309, 1310, 1311.
Demo data is fake.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["explore"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-stock1"


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
        shots.login(p, "stock")
        p.wait_for_timeout(2500)
    p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
    return pw, br, p


if "explore" in steps:
    pw, br, p = session()
    print("URL", p.url)
    txt(p, "home", 3000)
    shots.shot(p, FIG / "_home.png")
    shots.close(pw, br)

if "menu" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-control")
    p.get_by_text("Lab stock", exact=True).first.click(); p.wait_for_timeout(800)
    txt(p, "menu", 1500)
    shots.annotate(p, FIG / "menu.png", [
        {"text": "Stock management", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "To check", "exact": True, "n": 2, "position": "right", "index": 0},
        {"text": "Movements", "exact": True, "n": 3, "position": "right", "index": 0},
        {"text": "Stock count", "exact": True, "n": 4, "position": "right", "index": 0},
        {"text": "Lab stock", "exact": True, "n": 5, "position": "right", "index": 0},
    ], crop={"x": 0, "y": 60, "width": 330, "height": 560})
    shots.close(pw, br)

if "queue" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-control")
    p.get_by_text("REC-20261026-006").click(); p.wait_for_timeout(1000)
    txt(p, "queue-sel", 2500)
    shots.annotate(p, FIG / "queue.png", [
        {"text": "Receipts (2)", "n": 1, "position": "top"},
        {"text": "Damages (", "n": 2, "position": "top"},
        {"text": "REC-20261026-006", "n": 3, "position": "left", "index": 0},
        {"text": "Entered by", "n": 4, "position": "right", "index": 0},
        {"selector": "input[aria-label='Good']", "n": 5, "position": "top"},
        {"text": "Reject", "exact": True, "n": 6, "position": "top", "index": 0},
        {"text": "Validate", "exact": True, "n": 7, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 640})
    shots.close(pw, br)

if "fab" in steps:
    # acts: corrects, then validates REC-20261026-006 (run once)
    pw, br, p = session(height=1100)
    go(p, "/dashboard/stock-control")
    p.get_by_text("REC-20261026-006").click(); p.wait_for_timeout(1000)
    g = "input[aria-label='Good']"; d = "input[aria-label='Damaged']"
    # error 1: total above what the assistant entered
    p.fill(g, "50"); p.fill(d, "2"); p.wait_for_timeout(300)
    p.get_by_text("Save corrections", exact=True).click(); p.wait_for_timeout(1500)
    txt(p, "fab-err-total", 2500)
    shots.shot(p, FIG / "_fab-err-total.png", crop={"x": 276, "y": 60, "width": 1324, "height": 700})
    # error 2: above expected
    p.fill(g, "60"); p.wait_for_timeout(300)
    p.get_by_text("Save corrections", exact=True).click(); p.wait_for_timeout(1000)
    txt(p, "fab-err-exp", 2500)
    # correction
    p.fill(g, "47"); p.fill(d, "3"); p.wait_for_timeout(400)
    shots.annotate(p, FIG / "correct.png", [
        {"selector": g, "n": 1, "position": "top"},
        {"selector": d, "n": 2, "position": "top"},
        {"text": "Save corrections", "exact": True, "n": 3, "position": "top"},
        {"text": "Validate", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 640})
    p.get_by_text("Save corrections", exact=True).click(); p.wait_for_timeout(2000)
    txt(p, "fab-saved", 2500)
    p.get_by_text("Validate", exact=True).first.click(); p.wait_for_timeout(2500)
    txt(p, "fab-validated", 2500)
    shots.annotate(p, FIG / "validated.png", [
        {"text": "Validated: stock has been updated.", "n": 1, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 500})
    shots.close(pw, br)

if "sup" in steps:
    # acts: REC-20261026-008 corrected and validated; REC-20261026-007 rejected (run once)
    pw, br, p = session(height=1100)
    go(p, "/dashboard/stock-control")
    p.get_by_text("REC-20261026-008").click(); p.wait_for_timeout(1000)
    g = "input[aria-label='Good']"; d = "input[aria-label='Damaged']"
    p.fill(g, "28"); p.wait_for_timeout(300)
    p.get_by_text("Save corrections", exact=True).click(); p.wait_for_timeout(2000)
    txt(p, "sup-err-raise", 2500)
    shots.shot(p, FIG / "_sup-err-raise.png", crop={"x": 276, "y": 60, "width": 1324, "height": 700})
    go(p, "/dashboard/stock-control")
    p.get_by_text("REC-20261026-008").click(); p.wait_for_timeout(1000)
    p.fill(g, "22"); p.fill(d, "3"); p.wait_for_timeout(400)
    shots.annotate(p, FIG / "correct.png", [
        {"text": "Expected", "exact": True, "n": 1, "position": "top", "index": 0},
        {"selector": g, "n": 2, "position": "top"},
        {"selector": d, "n": 3, "position": "top"},
        {"text": "Save corrections", "exact": True, "n": 4, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 700})
    p.get_by_text("Save corrections", exact=True).click(); p.wait_for_timeout(2000)
    txt(p, "sup-saved", 2500)
    p.get_by_text("Validate", exact=True).first.click(); p.wait_for_timeout(2500)
    txt(p, "sup-validated", 1800)
    # rejection of 007
    p.get_by_text("REC-20261026-007").click(); p.wait_for_timeout(1000)
    p.get_by_text("Reject", exact=True).first.click(); p.wait_for_timeout(1200)
    p.locator("button[form=reject-form]").click(); p.wait_for_timeout(600)
    txt(p, "rej-empty", 1500)
    p.fill("#reject-reason", "The delivery note DN-5120 lists 50 Efferalgan, not 55. Ask the supplier to confirm and enter the receipt again.")
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "reject.png", [
        {"selector": "#reject-reason", "n": 1, "position": "top"},
        {"selector": "button[form=reject-form]", "n": 2, "position": "top"},
    ], crop={"x": 330, "y": 120, "width": 940, "height": 560})
    p.locator("button[form=reject-form]").click(); p.wait_for_timeout(2500)
    txt(p, "rej-done", 1500)
    shots.close(pw, br)

if "inc" in steps:
    # acts: damages 1311 (refused: no stock), 1309 validated, 1310 rejected (run once)
    pw, br, p = session(height=1000)
    go(p, "/dashboard/stock-control")
    p.get_by_role("tab", name="Damages").click(); p.wait_for_timeout(1000)
    txt(p, "inc-list", 2000)
    shots.annotate(p, FIG / "damages.png", [
        {"text": "Damages (3)", "n": 1, "position": "top"},
        {"text": "Entered by", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Validate", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Reject", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 560})
    # 1311: no stock
    row = p.locator("tr:has-text('Api1')")
    row.get_by_text("Validate", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "inc-nostock", 1500)
    shots.annotate(p, FIG / "nostock.png", [
        {"text": "Stock insuffisant", "n": 1, "position": "right", "outline": False},
        {"text": "Reject", "exact": True, "n": 2, "position": "top", "index": 2},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 560})
    # 1309 validated
    p.locator("tr:has-text('Two boxes were missing')").get_by_text("Validate", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "inc-validated", 1500)
    # 1310 rejected
    p.locator("tr:has-text('Caps found loose')").get_by_text("Reject", exact=True).click(); p.wait_for_timeout(1200)
    p.fill("#reject-reason", "Photos of the jars are needed before they leave the stock. Send them to the stock controller.")
    p.wait_for_timeout(300)
    shots.shot(p, FIG / "reject.png")
    p.locator("button[form=reject-form]").click(); p.wait_for_timeout(2500)
    txt(p, "inc-rejected", 1500)
    shots.close(pw, br)

if "retake" in steps:
    # acts: REC-...-009 corrected and validated, REC-...-010 rejected, damage 1311 rejected
    pw, br, p = session(height=1000)
    g = "input[aria-label='Good']"; d = "input[aria-label='Damaged']"
    go(p, "/dashboard/stock-control")
    p.get_by_role("tab", name="Damages").click(); p.wait_for_timeout(800)
    p.locator("tr:has-text('Api1')").get_by_text("Validate", exact=True).click(); p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "nostock.png", [
        {"text": "Stock insuffisant", "n": 1, "position": "right", "outline": False},
        {"text": "Reject", "exact": True, "n": 2, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 560})
    p.locator("tr:has-text('Api1')").get_by_text("Reject", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#reject-reason", "The system holds no stock of this product. Check the physical count first.")
    p.locator("button[form=reject-form]").click(); p.wait_for_timeout(2500)
    go(p, "/dashboard/stock-control")
    p.get_by_text("DN-7790").count()
    p.get_by_text("REC-20261026-009").click(); p.wait_for_timeout(1000)
    p.fill(g, "23"); p.fill(d, "3"); p.wait_for_timeout(400)
    shots.annotate(p, FIG / "correct.png", [
        {"selector": g, "n": 1, "position": "top"},
        {"selector": d, "n": 2, "position": "top"},
        {"text": "Save corrections", "exact": True, "n": 3, "position": "top"},
        {"text": "Validate", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 700})
    p.get_by_text("Save corrections", exact=True).click(); p.wait_for_timeout(2000)
    p.get_by_text("Validate", exact=True).first.click(); p.wait_for_timeout(2500)
    p.get_by_text("REC-20261026-010").click(); p.wait_for_timeout(1000)
    p.get_by_text("Reject", exact=True).first.click(); p.wait_for_timeout(1200)
    p.fill("#reject-reason", "The delivery note DN-5121 is not signed. Ask the supplier for a signed copy, then enter the receipt again.")
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "reject.png", [
        {"selector": "#reject-reason", "n": 1, "position": "top"},
        {"selector": "button[form=reject-form]", "n": 2, "position": "top"},
    ], crop={"x": 400, "y": 400, "width": 1200, "height": 500})
    p.locator("button[form=reject-form]").click(); p.wait_for_timeout(2500)
    shots.close(pw, br)

if "rejectfig" in steps:
    # acts: rejects REC-20261026-011 (run once)
    pw, br, p = session(height=1000)
    go(p, "/dashboard/stock-control")
    p.get_by_text("REC-20261026-011").click(); p.wait_for_timeout(1000)
    p.get_by_text("Reject", exact=True).first.click(); p.wait_for_timeout(1200)
    p.fill("#reject-reason", "The delivery note DN-5122 is not signed. Ask the supplier for a signed copy, then enter the receipt again.")
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "reject.png", [
        {"selector": "#reject-reason", "n": 1, "position": "right"},
        {"selector": "button[form=reject-form]", "n": 2, "position": "top"},
    ], crop={"x": 330, "y": 330, "width": 960, "height": 350})
    p.locator("button[form=reject-form]").click(); p.wait_for_timeout(2500)
    shots.close(pw, br)

if "labexplore" in steps:
    pw, br, p = session()
    for r in ["lab-stock-products", "lab-stock-requests", "lab-stock-receipts", "lab-stock-movements", "lab-stock-alerts", "lab-stock-count", "lab-stock-expenses", "stock", "stock-lots", "stock-count"]:
        go(p, "/dashboard/" + r, 2000)
        print("=====", r, p.url)
        print(p.inner_text("body")[330:1400].encode("ascii", "replace").decode())
        shots.shot(p, FIG / f"_x-{r}.png")
    shots.close(pw, br)

def fill_lab_receipt(p, invoice):
    p.fill("#lab-invoice-number", invoice)
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
    p.wait_for_timeout(400)


if "labreceipt" in steps:
    # acts when "save" is given: enters a lab receipt MS-2026-0452 (run once)
    pw, br, p = session(height=1100)
    go(p, "/dashboard/lab-stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(2000)
    txt(p, "lr-empty", 1500)
    shots.shot(p, FIG / "_lr-empty.png")
    fill_lab_receipt(p, "MS-2026-0440")
    txt(p, "lr-filled", 2500)
    shots.shot(p, FIG / "_lr-filled.png")
    p.get_by_text("Confirm receipt", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "lr-dup", 1500)
    shots.shot(p, FIG / "_lr-dup.png")
    if "save" in steps:
        p.fill("#lab-invoice-number", "MS-2026-0452"); p.wait_for_timeout(300)
        for i in range(2):
            p.locator("tbody tr").nth(i).locator("input[type=checkbox]").check()
        shots.annotate(p, FIG / "lab-receipt-form.png", [
            {"selector": "#lab-invoice-number", "n": 1, "position": "top"},
            {"selector": "#lab-invoice-supplier", "n": 2, "position": "top"},
            {"selector": "#lab-invoice-date", "n": 3, "position": "top"},
            {"text": "Add a product", "exact": True, "n": 4, "position": "top", "index": 0},
            {"selector": "tbody tr >> nth=0 >> input[type=checkbox]", "n": 5, "position": "top"},
            {"selector": "tbody tr >> nth=0 >> input[aria-label='Qty received']", "n": 6, "position": "top"},
            {"text": "Confirm receipt", "exact": True, "n": 7, "position": "top"},
        ])
        p.get_by_text("Confirm receipt", exact=True).click(); p.wait_for_timeout(3000)
        print("URL", p.url)
        txt(p, "lr-done", 2500)
    shots.close(pw, br)

if "labfig" in steps:
    # figures only: the second submit is refused as a duplicate, nothing is saved
    pw, br, p = session(height=1100)
    go(p, "/dashboard/lab-stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(2000)
    fill_lab_receipt(p, "MS-2026-0460")
    for i in range(2):
        p.locator("tbody tr").nth(i).locator("input[type=checkbox]").check()
    CR = {"x": 276, "y": 60, "width": 1324, "height": 740}
    shots.annotate(p, FIG / "lab-receipt-form.png", [
        {"selector": "#lab-invoice-number", "n": 1, "position": "top"},
        {"selector": "#lab-invoice-supplier", "n": 2, "position": "top"},
        {"selector": "#lab-invoice-date", "n": 3, "position": "top"},
        {"text": "Add a product", "exact": True, "n": 4, "position": "top", "index": 0},
        {"selector": "tbody tr >> nth=0 >> input[type=checkbox]", "n": 5, "position": "top"},
        {"selector": "tbody tr >> nth=0 >> input[aria-label='Qty received']", "n": 6, "position": "top"},
        {"text": "Confirm receipt", "exact": True, "n": 7, "position": "top"},
    ], crop=CR)
    p.fill("#lab-invoice-number", "MS-2026-0452"); p.wait_for_timeout(200)
    p.get_by_text("Confirm receipt", exact=True).click(); p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "lab-dup.png", [
        {"text": "Invoice already recorded", "n": 1, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 330})
    shots.close(pw, br)

if "labafter" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/lab-stock-receipts")
    shots.annotate(p, FIG / "lab-receipts.png", [
        {"text": "New receipt", "exact": True, "n": 1, "position": "left"},
        {"selector": "#lab-receipts-supplier", "n": 2, "position": "top"},
        {"text": "Invoice no.", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Valid", "exact": True, "n": 4, "position": "top", "index": 0},
        {"text": "Details", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 640})
    p.get_by_text("Details", exact=True).first.click(); p.wait_for_timeout(2000)
    txt(p, "lab-detail", 2000)
    shots.shot(p, FIG / "_lab-detail.png")
    go(p, "/dashboard/lab-stock-products")
    txt(p, "lab-products", 1500)
    shots.annotate(p, FIG / "lab-products.png", [
        {"text": "Add a product", "exact": True, "n": 1, "position": "left"},
        {"text": "Stock", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Edit", "exact": True, "n": 3, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 560})
    go(p, "/dashboard/lab-stock-movements")
    txt(p, "lab-history", 1800)
    shots.annotate(p, FIG / "lab-history.png", [
        {"text": "Product", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Receipt", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Stock after", "exact": True, "n": 3, "position": "top"},
        {"text": "Receipt #", "n": 4, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 600})
    go(p, "/dashboard/lab-stock-requests")
    txt(p, "lab-requests", 1500)
    shots.shot(p, FIG / "_lab-requests.png")
    shots.close(pw, br)

if "labreq" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/lab-stock-requests")
    txt(p, "lab-req-open", 1800)
    shots.annotate(p, FIG / "lab-requests.png", [
        {"text": "Status", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Origin", "exact": True, "n": 2, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 460})
    shots.close(pw, br)

if "labreceipt2" in steps:
    # acts: receipt MS-2026-0455 with a partial delivery of the reported product (run once)
    pw, br, p = session(height=1100)
    go(p, "/dashboard/lab-stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(2000)
    p.fill("#lab-invoice-number", "MS-2026-0455"); p.fill("#lab-invoice-supplier", "MediLab Supplies")
    p.get_by_text("Add a product", exact=True).click(); p.wait_for_timeout(800)
    p.fill("#lab-picker-search", "Glucose"); p.wait_for_timeout(500)
    p.locator("ul button:has-text('Glucose reagent kit')").click(); p.wait_for_timeout(600)
    row = p.locator("tbody tr").nth(0)
    row.locator("input[aria-label='Qty ordered']").fill("10"); row.locator("input[aria-label='Qty received']").fill("5")
    row.locator("input[aria-label='Lot']").fill("GRK-2612"); row.locator("input[aria-label='Expiry']").fill("2028-01-31")
    row.locator("input[aria-label='Unit price']").fill("12000"); row.locator("input[type=checkbox]").check()
    p.get_by_text("Confirm receipt", exact=True).click(); p.wait_for_timeout(3000)
    go(p, "/dashboard/lab-stock-requests")
    p.select_option("select", label="All"); p.wait_for_timeout(1500)
    txt(p, "lab-req-after", 1800)
    shots.close(pw, br)

if "movements" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/stock-movements", 3000)
    txt(p, "mv-all", 1800)
    p.select_option("#mov-product", label="Efferalgan"); p.click("button[type=submit]"); p.wait_for_timeout(2500)
    txt(p, "mv-eff", 2500)
    shots.annotate(p, FIG / "movements.png", [
        {"selector": "#mov-search", "n": 1, "position": "top"},
        {"selector": "#mov-product", "n": 2, "position": "top"},
        {"selector": "#mov-type", "n": 3, "position": "bottom"},
        {"text": "Movement type", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Author", "exact": True, "n": 5, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 560})
    shots.close(pw, br)

if "bell" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/stock-control", 4000)
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    items = p.locator("div.absolute.right-0.mt-2 div.cursor-pointer")
    for k, t in enumerate(items.all_inner_texts()[:14]): print("BELL", k, t.replace(chr(10), " / "))
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "bottom"},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=0", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 520})
    shots.close(pw, br)

if "alerts" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/lab-stock-alerts", 2500)
    shots.annotate(p, FIG / "lab-alerts.png", [
        {"selector": "h2 >> nth=1", "n": 1, "position": "top"},
        {"selector": "h2 >> nth=2", "n": 2, "position": "top"},
        {"selector": "h2 >> nth=3", "n": 3, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 640})
    go(p, "/dashboard/lab-stock-products", 2500)
    p.get_by_text("Edit", exact=True).first.click(); p.wait_for_timeout(1500)
    txt(p, "lab-edit", 1500)
    shots.shot(p, FIG / "_lab-edit.png")
    shots.close(pw, br)

if "account" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-control", 2500)
    p.locator("button[aria-label='My Account']").click(); p.wait_for_timeout(1200)
    txt(p, "account", 1500)
    shots.annotate(p, FIG / "account.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"text": "Password", "exact": True, "n": 2, "position": "bottom", "outline": False},
        {"text": "Phone", "exact": True, "n": 3, "position": "left", "outline": False},
        {"text": "Save", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 440, "y": 200, "width": 720, "height": 540})
    shots.close(pw, br)

if "bellclick" in steps:
    pw, br, p = session()
    go(p, "/dashboard/lab-stock-products", 3000)
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1200)
    p.locator("div.absolute.right-0.mt-2 div.cursor-pointer").first.click(); p.wait_for_timeout(2500)
    print("AFTER CLICK", p.url)
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1200)
    print(p.locator("div.absolute.right-0.mt-2").inner_text()[:600])
    shots.close(pw, br)

if "offline" in steps:
    pw, br, p = session(offline=True)
    p.goto(shots.BASE_URL + "/dashboard/stock-control"); p.wait_for_timeout(8000)
    toast_close(p)
    txt(p, "off-control", 1500)
    shots.annotate(p, FIG / "offline.png", [
        {"text": "Offline", "n": 1, "position": "bottom", "index": 0},
        {"text": "Unable to load", "n": 2, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 520})
    shots.close(pw, br)

if "access" in steps:
    pw, br, p = session()
    for r in ["/dashboard/stock-lots", "/dashboard/stock-receipts", "/dashboard/stock", "/dashboard/patients", "/dashboard/lab-stock-count", "/dashboard/lab-stock-expenses", "/dashboard/overview", "/dashboard/stock-adjustment-requests", "/dashboard/fabrication-lots"]:
        go(p, r, 1500)
        print("ACCESS", r, "->", p.url)
    shots.close(pw, br)
