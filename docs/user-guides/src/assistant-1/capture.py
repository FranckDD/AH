"""Capture script for guide assistant-1. Run from the repo root:
    python docs/user-guides/src/assistant-1/capture.py [step ...]
Steps that act on the dev database (run once, in this order): lots deliver newlot cancellot
receipt-fab receipt-sup receipt-cancel incident decide ...
Data prepared with the API before the capture (production manager): batch FAB-2026-0002 (Miel Pure,
98 good bottles) shipped, which created lot LOT-20261026-001. Demo data is fake.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-assistant1"
CROP = {"x": 276, "y": 0, "width": 1324, "height": 700}


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


def session(offline=False):
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=str(PROFILE), offline=offline)
    if not offline:
        shots.login(p, "assistant")
        p.wait_for_timeout(2500)
    p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
    return pw, br, p


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login"); shots.wait_ready(p)
    acc = shots.account("assistant")
    p.fill("#username", acc["username"]); p.fill("#password", "demo-password")
    shots.annotate(p, FIG / "signin.png", [
        {"selector": "#username", "n": 1}, {"selector": "#password", "n": 2},
        {"selector": "button[type=submit]", "n": 3}], crop="form")
    shots.close(pw, br)

if "home" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-lots")
    shots.annotate(p, FIG / "menu.png", [
        {"text": "Toxicology Monitoring", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "Stock management", "exact": True, "n": 2, "position": "right", "index": 0},
        {"text": "Stock Management", "exact": True, "n": 3, "position": "right", "index": 0},
        {"text": "Production", "exact": True, "n": 4, "position": "right", "index": 0},
        {"text": "Receipts", "exact": True, "n": 5, "position": "right", "index": 0},
        {"text": "Damages", "exact": True, "n": 6, "position": "right", "index": 0},
        {"text": "Movements", "exact": True, "n": 7, "position": "right", "index": 0},
    ], crop={"x": 0, "y": 80, "width": 330, "height": 340})
    shots.close(pw, br)

if "lots" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-lots")
    txt(p, "lots")
    shots.annotate(p, FIG / "lots.png", [
        {"text": "New lot", "exact": True, "n": 1, "position": "left"},
        {"selector": "#lots-status", "n": 2, "position": "right"},
        {"text": "Produced", "exact": True, "n": 3, "position": "top", "index": 1},
        {"text": "Mark delivered", "exact": True, "n": 4, "position": "top"},
        {"text": "Cancel", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 600})
    shots.close(pw, br)

if "newlot" in steps or "lotform" in steps:
    # "newlot" saves the lot (run once); "lotform" only takes the figure and closes the form.
    pw, br, p = session()
    go(p, "/dashboard/stock-lots")
    p.get_by_text("New lot", exact=True).click(); p.wait_for_timeout(1500)
    p.locator("button[form=lot-form]").click(); p.wait_for_timeout(500)
    txt(p, "newlot-err1", 1200)
    p.get_by_text("Close", exact=True).last.click(); p.wait_for_timeout(800)
    p.get_by_text("New lot", exact=True).click(); p.wait_for_timeout(1500)
    p.select_option("#lot-product", label="Honey")
    p.fill("#lot-quantity", "60")
    p.fill("#lot-expiry", "2027-06-30")
    p.fill("#lot-producer", "Demo apiary")
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "lot-form.png", [
        {"selector": "#lot-product", "n": 1, "position": "right"},
        {"selector": "#lot-quantity", "n": 2, "position": "right"},
        {"selector": "#lot-production", "n": 3, "position": "right"},
        {"selector": "#lot-delivery", "n": 4, "position": "top"},
        {"selector": "#lot-expiry", "n": 5, "position": "top"},
        {"selector": "#lot-producer", "n": 6, "position": "right"},
        {"selector": "button[form=lot-form]", "n": 7, "position": "top"},
    ], crop={"x": 330, "y": 120, "width": 940, "height": 710})
    if "newlot" in steps:
        p.locator("button[form=lot-form]").click(); p.wait_for_timeout(2500)
        txt(p, "newlot-done", 1500)
    shots.close(pw, br)

if "cancellot" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-lots")
    p.locator("tr:has-text('LOT-20261026-002')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "cancellot-done", 1500)
    shots.shot(p, FIG / "_cancellot.png", crop=CROP)
    shots.close(pw, br)

if "deliver" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-lots")
    p.locator("tr:has-text('LOT-20261026-001')").get_by_text("Mark delivered", exact=True).click(); p.wait_for_timeout(1500)
    txt(p, "deliver-form", 1200)
    shots.annotate(p, FIG / "deliver.png", [
        {"selector": "#deliver-date", "n": 1, "position": "right"},
        {"selector": "button[form=deliver-form]", "n": 2, "position": "top"},
    ], crop={"x": 352, "y": 215, "width": 900, "height": 400})
    p.locator("button[form=deliver-form]").click(); p.wait_for_timeout(2500)
    txt(p, "deliver-done", 1500)
    p.select_option("#lots-status", label="Delivered"); p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "lots-delivered.png", [
        {"text": "Lot marked as delivered.", "n": 1, "position": "right", "outline": False},
        {"text": "Delivered", "exact": True, "n": 2, "position": "top", "index": 1},
    ], crop=CROP)
    shots.close(pw, br)

if "receipt-fab" in steps:
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1200})
    go(p, "/dashboard/stock-receipts")
    txt(p, "receipts-empty", 800)
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(1500)
    txt(p, "rf-form0", 1500)
    p.select_option("#receipt-lot", index=1); p.wait_for_timeout(800)
    txt(p, "rf-form1", 2500)
    # error: total above expected
    p.fill("#receipt-line-0-qty_good", "99"); p.wait_for_timeout(500)
    txt(p, "rf-err-exceeds", 2500)
    shots.shot(p, FIG / "_rf-exceeds.png")
    p.fill("#receipt-line-0-qty_good", "0"); p.wait_for_timeout(300)
    p.locator("button[form=receipt-form]").click(); p.wait_for_timeout(500)
    txt(p, "rf-err-zero", 2500)
    p.fill("#receipt-line-0-qty_good", "95"); p.fill("#receipt-line-0-qty_damaged", "2")
    p.fill("#receipt-line-0-qty_lost", "1"); p.wait_for_timeout(500)
    shots.annotate(p, FIG / "receipt-form.png", [
        {"text": "Manufactured lot", "exact": True, "n": 1, "position": "left"},
        {"selector": "#receipt-date", "n": 2, "position": "right"},
        {"selector": "#receipt-lot", "n": 3, "position": "right"},
        {"selector": "#receipt-line-0-qty_good", "n": 4, "position": "top"},
        {"selector": "#receipt-line-0-qty_lost", "n": 5, "position": "top"},
        {"text": "Total", "exact": True, "n": 6, "position": "top", "index": 0},
        {"selector": "button[form=receipt-form]", "n": 7, "position": "top"},
    ])
    p.locator("button[form=receipt-form]").click(); p.wait_for_timeout(2500)
    txt(p, "rf-done", 1500)
    shots.close(pw, br)

if "lot3" in steps:
    # Run once: creates lot 003 (Honey 40), marks it delivered, saves a receipt REC-...-002 for it.
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1200})
    go(p, "/dashboard/stock-lots")
    p.get_by_text("New lot", exact=True).click(); p.wait_for_timeout(1500)
    p.select_option("#lot-product", label="Honey"); p.fill("#lot-quantity", "40")
    p.fill("#lot-expiry", "2027-08-31"); p.fill("#lot-producer", "Demo apiary")
    p.locator("button[form=lot-form]").click(); p.wait_for_timeout(2500)
    p.locator("tr:has-text('LOT-20261026-003')").get_by_text("Mark delivered", exact=True).click(); p.wait_for_timeout(1200)
    p.locator("button[form=deliver-form]").click(); p.wait_for_timeout(2500)
    go(p, "/dashboard/stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(1500)
    p.select_option("#receipt-lot", label="LOT-20261026-003 - Honey (40)"); p.wait_for_timeout(800)
    p.fill("#receipt-line-0-qty_good", "38"); p.fill("#receipt-line-0-qty_damaged", "2"); p.wait_for_timeout(500)
    p.locator("button[form=receipt-form]").click(); p.wait_for_timeout(2500)
    txt(p, "lot3-receipt", 1500)
    shots.close(pw, br)

if "receiptform" in steps:
    # Figure only: the form is filled for lot 003 and closed without saving.
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1200})
    go(p, "/dashboard/stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(1500)
    p.select_option("#receipt-lot", label="LOT-20261026-004 - Miel Pure (50)"); p.wait_for_timeout(800)
    p.fill("#receipt-line-0-qty_good", "48"); p.fill("#receipt-line-0-qty_damaged", "2"); p.wait_for_timeout(500)
    shots.annotate(p, FIG / "receipt-form.png", [
        {"selector": "label:has(input[value=fabrication])", "n": 1, "position": "left"},
        {"selector": "#receipt-date", "n": 2, "position": "right"},
        {"selector": "#receipt-lot", "n": 3, "position": "right"},
        {"selector": "#receipt-line-0-qty_good", "n": 4, "position": "top"},
        {"selector": "#receipt-line-0-qty_defective", "n": 5, "position": "top"},
        {"text": "Total", "exact": True, "n": 6, "position": "top", "index": 0},
    ], crop={"x": 232, "y": 160, "width": 1140, "height": 740})
    shots.close(pw, br)

if "receipts-list" in steps:
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/dashboard/stock-receipts")
    txt(p, "receipts-list", 1800)
    shots.annotate(p, FIG / "receipts.png", [
        {"text": "New receipt", "exact": True, "n": 1, "position": "left"},
        {"selector": "#receipts-status", "n": 2, "position": "right"},
        {"text": "Manufactured lot", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "To check", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Details", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Cancel", "exact": True, "n": 6, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 700})
    p.locator("tr:has-text('REC-20261026-001')").get_by_text("Details", exact=True).click(); p.wait_for_timeout(2000)
    txt(p, "receipt-detail", 1800)
    shots.shot(p, FIG / "_receipt-detail.png")
    shots.close(pw, br)

if "receipt-sup" in steps:
    # Saves the receipt only when the step "save" is also given (it was saved once: REC-...-003).
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1500})
    go(p, "/dashboard/stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(1500)
    p.locator("label:has(input[value=fournisseur])").click(); p.wait_for_timeout(800)
    p.locator("button[form=receipt-form]").click(); p.wait_for_timeout(500)
    txt(p, "rs-err-supplier", 1500)
    p.get_by_text("Close", exact=True).last.click(); p.wait_for_timeout(800)
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(1500)
    p.locator("label:has(input[value=fournisseur])").click(); p.wait_for_timeout(800)
    p.fill("#receipt-supplier", "Demo Pharma Supplies"); p.fill("#receipt-delivery", "DN-4471")
    p.select_option("#receipt-line-0-product", label="Efferalgan")
    p.fill("#receipt-line-0-expected", "50")
    p.fill("#receipt-line-0-qty_good", "48"); p.fill("#receipt-line-0-qty_damaged", "2")
    p.fill("#receipt-line-0-lot", "EFF-2610"); p.fill("#receipt-line-0-expiry", "2028-03-31")
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(500)
    p.select_option("#receipt-line-1-product", label="Carnet 2")
    p.fill("#receipt-line-1-expected", "30"); p.fill("#receipt-line-1-qty_good", "30")
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "receipt-supplier.png", [
        {"selector": "label:has(input[value=fournisseur])", "n": 1, "position": "left"},
        {"selector": "#receipt-supplier", "n": 2, "position": "top"},
        {"selector": "#receipt-delivery", "n": 3, "position": "top"},
        {"selector": "#receipt-line-0-product", "n": 4, "position": "top"},
        {"selector": "#receipt-line-0-lot", "n": 5, "position": "top"},
    ], crop={"x": 232, "y": 180, "width": 1140, "height": 710})
    if "save" in steps:
        p.locator("button[form=receipt-form]").click(); p.wait_for_timeout(2500)
        txt(p, "rs-done", 1500)
    shots.close(pw, br)

if "receipt-cancel" in steps:
    # Run once: a throwaway supplier receipt is created and cancelled by its author.
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1200})
    go(p, "/dashboard/stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(1500)
    p.locator("label:has(input[value=fournisseur])").click(); p.wait_for_timeout(800)
    p.fill("#receipt-supplier", "Demo Test Supplies")
    p.select_option("#receipt-line-0-product", label="Carnet 3"); p.fill("#receipt-line-0-qty_good", "5")
    p.locator("button[form=receipt-form]").click(); p.wait_for_timeout(2500)
    p.locator("tr:has-text('Demo Test Supplies')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "rc-done", 1800)
    shots.close(pw, br)

if "incident" in steps:
    # Saves the incident only with the step "save" (done once: damage of 3 Efferalgan).
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/dashboard/stock-incidents")
    txt(p, "inc-empty", 900)
    p.get_by_text("Declare damage", exact=True).click(); p.wait_for_timeout(1500)
    p.locator("button[form=incident-form]").click(); p.wait_for_timeout(500)
    txt(p, "inc-err1", 700)
    p.get_by_text("Close", exact=True).last.click(); p.wait_for_timeout(800)
    p.get_by_text("Declare damage", exact=True).click(); p.wait_for_timeout(1500)
    p.select_option("#incident-product", label="Efferalgan")
    p.select_option("#incident-kind", label="Damaged")
    p.fill("#incident-quantity", "3")
    p.fill("#incident-reason", "Box crushed while unloading the delivery.")
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "incident-form.png", [
        {"selector": "#incident-product", "n": 1, "position": "right"},
        {"selector": "#incident-kind", "n": 2, "position": "top"},
        {"selector": "#incident-quantity", "n": 3, "position": "top"},
        {"selector": "#incident-reason", "n": 4, "position": "right"},
        {"selector": "#incident-date", "n": 5, "position": "right"},
        {"selector": "button[form=incident-form]", "n": 6, "position": "top"},
    ], crop={"x": 330, "y": 60, "width": 940, "height": 800})
    if "save" in steps:
        p.locator("button[form=incident-form]").click(); p.wait_for_timeout(2500)
        txt(p, "inc-done", 1500)
    shots.close(pw, br)

if "after" in steps:
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/dashboard/stock-receipts")
    txt(p, "after-receipts", 2500)
    shots.annotate(p, FIG / "receipts.png", [
        {"text": "New receipt", "exact": True, "n": 1, "position": "left"},
        {"selector": "#receipts-status", "n": 2, "position": "right"},
        {"text": "Lot / supplier", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Validated", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Damaged count does not match", "n": 5, "position": "right", "outline": False},
        {"text": "Details", "exact": True, "n": 6, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 700})
    go(p, "/dashboard/stock-lots")
    txt(p, "after-lots", 1500)
    go(p, "/dashboard/stock-incidents")
    txt(p, "after-incidents", 1500)
    go(p, "/dashboard/stock-movements")
    txt(p, "after-movements", 1800)
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    txt(p, "after-bell", 1800)
    items = p.locator("div.absolute.right-0.mt-2 div.cursor-pointer")
    for k, t in enumerate(items.all_inner_texts()): print("BELL", k, t.replace(chr(10), " / "))
    shots.close(pw, br)

if "bell" in steps:
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/dashboard/stock-receipts", 4000)
    try:
        p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception:
        pass
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "bottom"},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=1", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 420})
    shots.close(pw, br)

if "movements" in steps:
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/dashboard/stock-movements", 3000)
    p.select_option("#mov-product", label="Efferalgan"); p.click("button[type=submit]"); p.wait_for_timeout(2500)
    txt(p, "mv-efferalgan", 2500)
    shots.annotate(p, FIG / "movements.png", [
        {"selector": "#mov-search", "n": 1, "position": "top"},
        {"selector": "#mov-product", "n": 2, "position": "top"},
        {"selector": "#mov-type", "n": 3, "position": "bottom"},
        {"text": "Movement type", "exact": True, "n": 4, "position": "top", "index": 1},
        {"text": "Author", "exact": True, "n": 5, "position": "top"},
    ], crop={"x": 276, "y": 80, "width": 1324, "height": 480})
    shots.close(pw, br)

if "access" in steps:
    pw, br, p = session()
    for r in ["/dashboard/stock-control", "/dashboard/patients", "/dashboard/stock-count", "/dashboard/lab-stock-products", "/dashboard/fabrication-lots", "/dashboard/overview"]:
        go(p, r, 1500)
        print("ACCESS", r, "->", p.url, "|", p.inner_text("body")[330:520].replace(chr(10), " / "))
        if r.endswith("stock-control"):
            shots.shot(p, FIG / "_forbidden.png")
    shots.close(pw, br)

if "stockpage" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock", 2500)
    shots.shot(p, FIG / "_stock.png")
    p.locator("tr:has-text('Carnet 2')").get_by_text("Edit", exact=True).click(); p.wait_for_timeout(1500)
    txt(p, "stock-edit", 2500)
    shots.shot(p, FIG / "_stock-edit.png")
    shots.close(pw, br)

if "offline" in steps:
    pw, br, p = session(offline=True)
    p.goto(shots.BASE_URL + "/dashboard/stock-lots"); p.wait_for_timeout(8000)
    toast_close(p)
    txt(p, "off-lots", 1500)
    shots.annotate(p, FIG / "offline-lots.png", [
        {"text": "Offline", "n": 1, "position": "bottom", "index": 0},
        {"text": "Unable to load data.", "n": 2, "position": "right", "outline": False},
        {"text": "No lots.", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 520})
    p.get_by_text("New lot", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "off-lot-form", 1200)
    shots.shot(p, FIG / "_off-lot-form.png")
    shots.close(pw, br)

if "account" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-lots", 2500)
    p.locator("button[aria-label='My Account']").click(); p.wait_for_timeout(1200)
    txt(p, "account", 1500)
    shots.annotate(p, FIG / "account.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "bottom", "outline": False},
        {"text": "Password", "exact": True, "n": 2, "position": "bottom", "outline": False},
        {"text": "Phone", "exact": True, "n": 3, "position": "left", "outline": False},
        {"text": "Save", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 440, "y": 200, "width": 720, "height": 540})
    shots.close(pw, br)

if "toxico" in steps:
    pw, br, p = session()
    go(p, "/dashboard/toxico", 3000)
    shots.annotate(p, FIG / "_toxico.png", [])
    p.get_by_text("New Toxico Admission", exact=True).click(); p.wait_for_timeout(1500)
    txt(p, "tox-adm", 1500)
    shots.close(pw, br)

if "lotguard" in steps:
    # Run once: new receipt for the delivered lot 003 after the rejection, then lot cancel refused, then undone.
    pw, br, p = session()
    p.set_viewport_size({"width": 1600, "height": 1200})
    go(p, "/dashboard/stock-receipts")
    p.get_by_text("New receipt", exact=True).click(); p.wait_for_timeout(1500)
    print("OPTIONS", p.locator("#receipt-lot option").all_inner_texts())
    p.select_option("#receipt-lot", label="LOT-20261026-003 - Honey (40)"); p.wait_for_timeout(800)
    p.fill("#receipt-line-0-qty_good", "40")
    p.locator("button[form=receipt-form]").click(); p.wait_for_timeout(2500)
    txt(p, "lg-receipt", 1200)
    go(p, "/dashboard/stock-lots")
    p.locator("tr:has-text('LOT-20261026-003')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "lg-cancel-refused", 1500)
    shots.annotate(p, FIG / "lot-cancel-refused.png", [
        {"text": "Une r", "n": 1, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 520})
    go(p, "/dashboard/stock-receipts")
    p.locator("tr:has-text('REC-20261026-005')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(2500)
    go(p, "/dashboard/stock-lots")
    p.locator("tr:has-text('LOT-20261026-003')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "lg-cancel-ok", 1500)
    shots.close(pw, br)

if "cancel-foreign" in steps:
    # LOT-20261026-004 was created and shipped by the production manager (prepared with the API).
    pw, br, p = session()
    go(p, "/dashboard/stock-lots")
    p.locator("tr:has-text('LOT-20261026-004')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "cf", 1500)
    shots.annotate(p, FIG / "lot-cancel-foreign.png", [
        {"text": "Seul le", "n": 1, "position": "right", "outline": False},
        {"text": "Cancel", "exact": True, "n": 2, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 560})
    shots.close(pw, br)

if "deliver4" in steps:
    # Run once: the assistant marks the shipped lot 004 as delivered (it then feeds the receipt form figure).
    pw, br, p = session()
    go(p, "/dashboard/stock-lots")
    p.locator("tr:has-text('LOT-20261026-004')").get_by_text("Mark delivered", exact=True).click(); p.wait_for_timeout(1200)
    p.locator("button[form=deliver-form]").click(); p.wait_for_timeout(2500)
    txt(p, "deliver4", 1500)
    shots.close(pw, br)
