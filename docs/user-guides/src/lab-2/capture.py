"""Capture script for guide lab-2. Run from the repo root:
    python docs/user-guides/src/lab-2/capture.py [step ...]
Steps that act on the dev database (run once, in this order): addprod receipt signal order count ...
Demo data (fake): lab products Glucose reagent kit, EDTA sample tubes, Urine test strips.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-lab2"


def go(p, route, settle=2500):
    shots.goto(p, route)
    try:
        p.get_by_text("Connected").first.wait_for(timeout=30000)
    except Exception:
        pass
    p.wait_for_timeout(settle)
    p.keyboard.press("Escape")
    p.wait_for_timeout(1500)


def txt(p, name):
    (HERE / f"_{name}.txt").write_text(p.inner_text("body"), encoding="utf-8")
    print("-----", name); print(p.inner_text("body")[:2500])


def session(role, **kw):
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=str(PROFILE) + "-" + role, **kw)
    shots.login(p, role)
    return pw, br, p


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login"); shots.wait_ready(p)
    acc = shots.account("laborantin")
    p.fill("#username", acc["username"]); p.fill("#password", "demo-password")
    shots.annotate(p, FIG / "signin.png", [
        {"selector": "#username", "n": 1}, {"selector": "#password", "n": 2},
        {"selector": "button[type=submit]", "n": 3}], crop="form")
    shots.close(pw, br)

PRODUCTS = [("Glucose reagent kit", "Box of 100 tests", "MediLab Supplies", 10),
            ("EDTA sample tubes", "Pack of 100", "MediLab Supplies", 20),
            ("Urine test strips", "Bottle of 50", "MediLab Supplies", 5)]

if "addprod" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-products")
    p.get_by_text("Add a product", exact=True).first.click(); p.wait_for_timeout(800)
    txt(p, "addform")
    shots.shot(p, FIG / "_addform.png")
    for i, (n, pk, sp, th) in enumerate(PRODUCTS):
        if i: 
            p.get_by_text("Add a product", exact=True).first.click(); p.wait_for_timeout(800)
        p.fill("#lab-product-name", n); p.fill("#lab-product-packaging", pk)
        p.fill("#lab-product-supplier", sp); p.fill("#lab-product-threshold", str(th))
        if i == 0:
            shots.annotate(p, FIG / "product-form.png", [
                {"selector": "#lab-product-name", "n": 1, "position": "right"},
                {"selector": "#lab-product-packaging", "n": 2, "position": "top"},
                {"selector": "#lab-product-supplier", "n": 3, "position": "top"},
                {"selector": "#lab-product-threshold", "n": 4, "position": "right"},
                {"selector": "button[form=lab-product-form]", "n": 5, "position": "top"}])
        p.locator("button[form=lab-product-form]").click(); p.wait_for_timeout(2500)
        txt(p, f"added{i}")
    shots.close(pw, br)

if "receipt" in steps:
    pw, br, p = session("stock")
    p.set_viewport_size({"width": 1600, "height": 1300})
    go(p, "/dashboard/lab-stock-receipts/new")
    p.fill("#lab-invoice-number", "MS-2026-0417")
    p.fill("#lab-invoice-supplier", "MediLab Supplies")
    lines = [("Glucose", 40, 40, "GLU-2611", "2027-03-31", 3500),
             ("EDTA", 60, 60, "EDT-2610", "2026-12-15", 1200),
             ("Urine", 20, 20, "URS-2609", "2027-06-30", 2800)]
    for name, o, r, lot, exp, price in lines:
        p.get_by_role("button", name="Add a product").click(); p.wait_for_timeout(800)
        p.fill("#lab-picker-search", name); p.wait_for_timeout(800)
        p.locator("[role=dialog] >> text=" + name).first.click(); p.wait_for_timeout(1000)
        row = p.locator(f"tr:has-text('{name}'):visible, li:has-text('{name}'):visible").first
        vis = lambda sel: row.locator(sel + ":visible")
        vis("input[type=number]").nth(0).fill(str(o)); vis("input[type=number]").nth(1).fill(str(r))
        vis("input[type=text]").first.fill(lot); vis("input[type=date]").first.fill(exp)
        vis("input[type=number]").nth(2).fill(str(price)); vis("input[type=checkbox]").first.check()
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "receipt-form.png", [
        {"selector": "#lab-invoice-number", "n": 1, "position": "top"},
        {"selector": "#lab-invoice-supplier", "n": 2, "position": "top"},
        {"text": "Add a product", "exact": True, "n": 3, "position": "left"},
        {"selector": "input[type=checkbox]:visible >> nth=0", "n": 4, "position": "top"},
        {"text": "Confirm receipt", "exact": True, "n": 5, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 760})
    p.get_by_role("button", name="Confirm receipt").click(); p.wait_for_timeout(3500)
    txt(p, "receipt-done")
    shots.close(pw, br)

if "products" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-products")
    shots.annotate(p, FIG / "products.png", [
        {"text": "Lab stock", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Add a product", "exact": True, "n": 2, "position": "left"},
        {"selector": "#lab-products-search", "n": 3, "position": "right"},
        {"text": "Stock", "exact": True, "n": 4, "position": "top", "index": 0},
        {"text": "Report", "exact": True, "n": 5, "position": "left", "index": 0},
        {"text": "Edit", "exact": True, "n": 6, "position": "right", "index": 0},
    ], crop={"x": 0, "y": 20, "width": 1600, "height": 560})
    shots.close(pw, br)

if "signal" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-products")
    p.locator("tr:has-text('Glucose')").get_by_text("Report", exact=True).click(); p.wait_for_timeout(1000)
    txt(p, "signal-panel")
    shots.annotate(p, FIG / "signal.png", [
        {"text": "Almost out", "n": 1, "position": "top"},
        {"text": "Out", "exact": True, "n": 2, "position": "top"},
    ], crop={"x": 340, "y": 360, "width": 920, "height": 280})
    if "send" in steps:
        p.get_by_text("Almost out", exact=True).click(); p.wait_for_timeout(2500)
        txt(p, "signal-done")
    shots.close(pw, br)


if "order" in steps:
    pw, br, p = session("promoteur")
    go(p, "/dashboard/lab-stock-requests")
    txt(p, "promo-requests")
    p.locator("tr:has-text('Glucose')").get_by_text("Mark as ordered", exact=True).click(); p.wait_for_timeout(800)
    p.fill("#lab-order-date", "2026-10-30")
    p.locator("button[form=lab-order-form]").click(); p.wait_for_timeout(2500)
    txt(p, "promo-ordered")
    shots.close(pw, br)

if "requests" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-requests")
    p.select_option("#lab-requests-status", "all"); p.wait_for_timeout(1500)
    txt(p, "tech-requests")
    shots.annotate(p, FIG / "requests.png", [
        {"text": "To order", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"selector": "#lab-requests-status", "n": 2, "position": "right"},
        {"text": "Origin", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Received", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Expected date", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 0, "y": 20, "width": 1600, "height": 620})
    shots.close(pw, br)

if "count" in steps:
    import json, requests as rq
    def api_token(role):
        a = shots.account(role)
        return {"Authorization": "Bearer " + rq.post("http://127.0.0.1:8000/auth/login",
                data={"username": a["username"], "password": a["password"]}).json()["access_token"]}
    pw, br, p = session("laborantin")
    p.set_viewport_size({"width": 1600, "height": 1300})
    go(p, "/dashboard/lab-stock-count")
    txt(p, "count-empty")
    shots.annotate(p, FIG / "count-empty.png", [
        {"text": "Weekly count", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "a count is due", "n": 2, "position": "right", "outline": False},
        {"selector": "#lab-count-search", "n": 3, "position": "right"},
        {"text": "Last stock", "exact": True, "n": 4, "position": "top"},
        {"text": "Counted quantity", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 800})
    vals = {"EDTA sample tubes": 55, "Glucose reagent kit": 58, "produis test": 118, "Urine test strips": 3}
    for n, v in vals.items():
        p.fill(f"input[aria-label='Counted quantity for {n}']", str(v))
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "count-filled.png", [
        {"selector": "input[aria-label='Counted quantity for EDTA sample tubes']", "n": 1, "position": "left"},
        {"text": "Submit count", "exact": True, "n": 2, "position": "top"},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 800})
    h = api_token("stock")
    prods = {x["name"]: x["id"] for x in rq.get("http://127.0.0.1:8000/lab-stock/products", headers=h).json()}
    r = rq.post("http://127.0.0.1:8000/lab-stock/receipts", headers=h, json={
        "invoice_number": "MS-2026-0440", "supplier": "MediLab Supplies", "delivery_date": "2026-10-26",
        "lines": [{"product_id": prods["EDTA sample tubes"], "ordered_qty": 40, "received_qty": 40,
                   "unit_price": "1200", "lot_number": "EDT-2612", "expiry_date": "2027-02-28"}]})
    print("receipt", r.status_code, r.text[:200])
    p.get_by_text("Submit count", exact=True).click(); p.wait_for_timeout(3500)
    txt(p, "count-conflict")
    shots.annotate(p, FIG / "count-conflict.png", [
        {"text": "Stock changed during the count", "n": 1, "position": "left", "outline": False},
        {"text": "To recount", "n": 2, "position": "right", "index": 0},
        {"text": "Submit count", "exact": True, "n": 3, "position": "top"},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 800})
    p.get_by_text("Submit count", exact=True).click(); p.wait_for_timeout(3500)
    txt(p, "count-final")
    shots.shot(p, FIG / "_count-final.png", crop={"x": 256, "y": 80, "width": 1344, "height": 800})
    shots.close(pw, br)

if "due" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-alerts")
    txt(p, "alerts-due")
    shots.annotate(p, FIG / "alerts.png", [
        {"text": "Weekly count", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Go to count", "exact": True, "n": 2, "position": "left"},
        {"selector": "#lab-alerts-low", "n": 3, "position": "top"},
        {"selector": "#lab-alerts-expiring", "n": 4, "position": "top"},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 620})
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    items = p.locator("div.absolute.right-0.mt-2 div.cursor-pointer")
    for k, t in enumerate(items.all_inner_texts()): print("BELL", k, t.replace(chr(10), " / "))
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "bottom"},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=0", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 460})
    shots.close(pw, br)

if "access" in steps:
    pw, br, p = session("laborantin")
    for r in ["/dashboard/lab-stock-receipts", "/dashboard/lab-stock-receipts/new", "/dashboard/lab-stock-movements", "/dashboard/lab-stock-expenses"]:
        go(p, r, 1500)
        print("ACCESS", r, "->", p.url, "|", p.inner_text("h1")[:60] if p.locator("h1").count() else p.inner_text("body")[200:300].replace("\n", " / "))
        if r.endswith("movements"):
            txt(p, "tech-movements")
            shots.annotate(p, FIG / "history-tech.png", [
                {"selector": "#lab-mv-product", "n": 1, "position": "right"},
                {"text": "Type", "exact": True, "n": 2, "position": "top", "index": 0},
                {"text": "Stock after", "exact": True, "n": 3, "position": "top"},
            ], crop={"x": 256, "y": 80, "width": 1344, "height": 800})
    shots.close(pw, br)

if "edit" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-products")
    p.get_by_text("Add a product", exact=True).first.click(); p.wait_for_timeout(800)
    p.fill("#lab-product-name", "Pipette tips"); p.fill("#lab-product-packaging", "Bag of 500")
    p.fill("#lab-product-threshold", "15")
    p.locator("button[form=lab-product-form]").click(); p.wait_for_timeout(2500)
    # duplicate name
    p.get_by_text("Add a product", exact=True).first.click(); p.wait_for_timeout(800)
    p.fill("#lab-product-name", "Pipette tips"); p.fill("#lab-product-threshold", "15")
    p.locator("button[form=lab-product-form]").click(); p.wait_for_timeout(2000)
    txt(p, "dup-product")
    p.get_by_text("Close", exact=True).last.click(); p.wait_for_timeout(800)
    shots.close(pw, br)

if "edit2" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-products")
    p.locator("tr:has-text('Pipette tips')").get_by_text("Edit", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#lab-product-threshold", "12")
    shots.annotate(p, FIG / "product-edit.png", [
        {"selector": "#lab-product-threshold", "n": 1, "position": "right"},
        {"selector": "#lab-product-form input[type=checkbox]", "n": 2, "position": "right", "outline": False},
        {"selector": "button[form=lab-product-form]", "n": 3, "position": "top"},
    ], crop={"x": 340, "y": 100, "width": 920, "height": 800})
    p.locator("#lab-product-form input[type=checkbox]").click()
    p.locator("button[form=lab-product-form]").click(); p.wait_for_timeout(2500)
    txt(p, "deactivated")
    p.get_by_text("Show inactive products").click(); p.wait_for_timeout(1500)
    txt(p, "inactive-shown")
    shots.close(pw, br)

if "history" in steps:
    pw, br, p = session("promoteur")
    go(p, "/dashboard/lab-stock-movements")
    txt(p, "promo-movements")
    shots.annotate(p, FIG / "history.png", [
        {"selector": "#lab-mv-product", "n": 1, "position": "right"},
        {"text": "Type", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Stock after", "exact": True, "n": 3, "position": "top"},
        {"text": "By", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 900})
    shots.close(pw, br)

if "edit3" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-products")
    p.get_by_text("Show inactive products").click(); p.wait_for_timeout(1500)
    p.locator("tr:has-text('Pipette tips')").get_by_text("Edit", exact=True).click(); p.wait_for_timeout(1000)
    shots.annotate(p, FIG / "product-edit.png", [
        {"selector": "#lab-product-threshold", "n": 1, "position": "right"},
        {"selector": "#lab-product-form input[type=checkbox]", "n": 2, "position": "left", "outline": False},
        {"selector": "button[form=lab-product-form]", "n": 3, "position": "top"},
    ], crop={"x": 350, "y": 255, "width": 940, "height": 510})
    shots.close(pw, br)

if "offline" in steps:
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=str(PROFILE) + "-laborantin", offline=True)
    p.goto(shots.BASE_URL + "/dashboard/lab-stock-products"); p.wait_for_timeout(6000)
    txt(p, "off-products")
    shots.shot(p, FIG / "_off-products.png")
    p.locator("tr:has-text('Glucose')").get_by_text("Report", exact=True).click(); p.wait_for_timeout(800)
    p.get_by_text("Almost out", exact=True).click(); p.wait_for_timeout(4000)
    txt(p, "off-signal")
    shots.shot(p, FIG / "off-signal.png")
    p.goto(shots.BASE_URL + "/dashboard/lab-stock-count"); p.wait_for_timeout(5000)
    txt(p, "off-count")
    shots.shot(p, FIG / "_off-count.png")
    p.goto(shots.BASE_URL + "/dashboard/lab-stock-alerts"); p.wait_for_timeout(5000)
    txt(p, "off-alerts")
    shots.shot(p, FIG / "_off-alerts.png")
    shots.close(pw, br)

if "offline2" in steps:
    pw, br, p = session("laborantin")
    go(p, "/dashboard/lab-stock-count")
    p.fill("input[aria-label='Counted quantity for Urine test strips']", "3")
    p.context.set_offline(True); p.wait_for_timeout(1500)
    p.get_by_text("Submit count", exact=True).click(); p.wait_for_timeout(5000)
    txt(p, "off2-count")
    shots.shot(p, FIG / "off-count.png", crop={"x": 256, "y": 0, "width": 1344, "height": 700})
    p.context.set_offline(False); p.wait_for_timeout(1500)
    shots.close(pw, br)
