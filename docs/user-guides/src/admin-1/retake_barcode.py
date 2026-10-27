"""Retake of the stock figures after the barcode feature (27 Oct 2026). Nothing is saved."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from retake_lib import *
FIG = HERE / "figures"; FIG2 = HERE.parent / "admin-2" / "figures"
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-bcadm"
steps = sys.argv[1:] or ["list", "edit", "photo", "labels", "config"]
pw, br, p = shots.launch(width=1600, height=1500, profile_dir=PROFILE)
fresh(p); shots.login(p, "admin")
dlg = lambda: p.locator("[role=dialog]").first
def toast_close():
    try: p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
    except Exception: pass
if "list" in steps:
    go(p, "/dashboard/stock"); toast_close(); p.wait_for_timeout(500)
    shots.annotate(p, FIG / "stock-list.png", [
        {"selector": "#stock-search", "n": 1, "position": "top"},
        {"selector": "#stock-category", "n": 2, "position": "top"},
        {"selector": "main button:has-text('New Product') >> nth=0", "n": 3, "position": "top"},
        {"text": "Unit Price", "exact": True, "n": 4, "position": "right", "outline": False},
        {"selector": "tr:has-text('Miel Pure') button >> nth=0", "n": 5, "position": "top"},
        {"selector": "tr:has-text('Miel Pure') button >> nth=2", "n": 6, "position": "top"},
        {"selector": "main button:has-text('Print labels')", "n": 7, "position": "top"},
        {"selector": "tr:has-text('Miel Pure') button >> nth=1", "n": 8, "position": "top"},
    ], crop={"x": 280, "y": 40, "width": 1320, "height": 760})
if "edit" in steps or "photo" in steps:
    go(p, "/dashboard/stock"); toast_close()
    p.fill("#stock-search", "Demo test"); p.wait_for_timeout(2000)
    p.locator("tr:has-text('Demo test syrup') button >> nth=0").click(); p.wait_for_timeout(1500)
    if "edit" in steps:
        shots.annotate(p, FIG / "product-edit.png", [
            {"selector": "#product-price", "n": 1, "position": "top"},
            {"selector": "#product-quantity", "n": 2, "position": "top"},
            {"text": "Update", "exact": True, "n": 3, "position": "left"},
        ], crop="[role=dialog]")
    if "photo" in steps:
        p.locator("[data-testid=product-code]").scroll_into_view_if_needed(); p.wait_for_timeout(500)
        p.locator("text=Add a photo").first.scroll_into_view_if_needed(); p.wait_for_timeout(500)
        shots.annotate(p, FIG / "product-photo.png", [
            {"selector": "[data-testid=product-code]", "n": 1, "position": "top"},
            {"text": "Product photo", "exact": True, "n": 2, "position": "top"},
            {"text": "Add a photo", "exact": True, "n": 3, "position": "bottom"},
        ], crop="[role=dialog]")
    p.keyboard.press("Escape")
if "labels" in steps:
    go(p, "/dashboard/stock"); toast_close()
    p.get_by_role("button", name="Print labels").first.click(); p.wait_for_timeout(1500)
    for nm in ("Honey", "Efferalgan"):
        dlg().locator(f"label:has-text('{nm}')").first.locator("input[type=checkbox]").check()
    p.wait_for_timeout(1200)
    dlg().locator("input[type=number]").first.fill("2"); p.wait_for_timeout(1500)
    (HERE / "_labels.txt").write_text(dlg().inner_text(), encoding="utf-8")
    shots.annotate(p, FIG / "labels-modal.png", [
        {"selector": "[role=dialog] input[type=search], [role=dialog] input[placeholder^='Search']", "n": 1, "position": "top"},
        {"text": "Label roll (one label per page)", "exact": True, "n": 2, "position": "right"},
        {"text": "Preview", "exact": True, "n": 3, "position": "top", "index": 1},
        {"selector": "[role=dialog] button:has-text('Print') >> nth=-1", "n": 4, "position": "top"},
    ], crop="[role=dialog]")
    p.keyboard.press("Escape")
if "config" in steps:
    go(p, "/dashboard/configuration"); toast_close()
    p.locator("#cfg-label-width").scroll_into_view_if_needed(); p.wait_for_timeout(600)
    a = p.locator("#cfg-label-width").bounding_box(); b = p.get_by_text("Save the organisation settings", exact=True).bounding_box()
    y0 = max(a["y"] - 110, 0)
    crop = {"x": 330, "y": y0, "width": 1270, "height": b["y"] + b["height"] + 60 - y0}
    shots.annotate(p, FIG2 / "config-label-size.png", [
        {"selector": "#cfg-label-width", "n": 1, "position": "top"},
        {"selector": "#cfg-label-height", "n": 2, "position": "top"},
        {"text": "Save the organisation settings", "exact": True, "n": 3, "position": "top"},
    ], crop=crop)
shots.close(pw, br)
