"""Retake of production-1 figures (batch 3, 27 Oct 2026). python docs/user-guides/src/production-1/retake_b3.py [step ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *
FIG = Path("docs/user-guides/src/production-1/figures")
P0 = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/"
steps = sys.argv[1:] or ["explore"]
ROLE = "admin" if "admin" in steps else "production"
PROFILE = P0 / ("chrome-profile-production1-admin" if ROLE == "admin" else "chrome-profile-production1")
pw, br, p = shots.launch(width=1600, height=1250, profile_dir=PROFILE)
fresh(p)
shots.login(p, ROLE)
p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
def toast_close():
    try:
        p.locator("[class*=border-l-4] button, div:has-text('is below its alert threshold') >> button").first.click(timeout=800)
    except Exception: pass
    try:
        p.locator("text=You have").first.locator("xpath=..").get_by_role("button").first.click(timeout=800)
        p.wait_for_timeout(400)
    except Exception: pass
def gor(route, settle=3000):
    shots.goto(p, route); p.wait_for_timeout(settle); toast_close()
if "explore" in steps:
    gor("/dashboard/fabrication-intrants")
    print("SCREEN", txt(p, 4000)[250:])
if "explore2" in steps:
    gor("/dashboard/fabrication-intrants")
    p.locator("tr:has-text('GD-P1-BUY-3')").get_by_text("Edit purchase", exact=True).click(); p.wait_for_timeout(1200)
    d = p.locator("[role=dialog]").first
    print("EDITFORM", " | ".join(d.inner_text().split()))
    print("IDS", d.evaluate("e => [...e.querySelectorAll('input,select,textarea,button')].map(x => x.tagName+'#'+x.id+'/'+(x.getAttribute('form')||''))"))
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(600)
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    print("BELL", p.locator("div.absolute.right-0.mt-2").first.inner_text().replace(chr(10), " / ")[:800])
    shots.shot(p, FIG / "_tmp.png", crop={"x": 1000, "y": 0, "width": 600, "height": 500})
def open_form():
    p.get_by_text("New purchase", exact=True).first.click(); p.wait_for_timeout(1200)
if "buy" in steps:
    gor("/dashboard/fabrication-intrants")
    shots.annotate(p, FIG / "screen.png", [
        {"text": "New purchase", "exact": True, "n": 1, "position": "left"},
        {"text": "Show deactivated", "exact": True, "n": 2, "position": "right"},
        {"text": "Remaining stock", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Alert threshold", "exact": True, "n": 4, "position": "top"},
        {"text": "State", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Deactivate", "exact": True, "n": 6, "position": "top", "index": 0},
        {"text": "Input purchases", "exact": True, "n": 7, "position": "top"},
        {"text": "Cancel purchase", "exact": True, "n": 8, "position": "left", "index": 0},
        {"text": "Edit purchase", "exact": True, "n": 9, "position": "left", "index": 0},
    ], crop={"x": 160, "y": 0, "width": 1440, "height": 860})
if "buy2" in steps:
    # demo data: purchase GD-P1-BUY-4 (50 honey jars at 160), already created
    gor("/dashboard/fabrication-intrants")
    open_form()
    p.select_option("#fab-purchase-intrant", label="Guide demo honey jars (jar)")
    p.fill("#fab-purchase-supplier", "Demo Farm Supplies"); p.fill("#fab-purchase-ref", "GD-P1-BUY-4")
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
if "buysaved" in steps:
    gor("/dashboard/fabrication-intrants")
    shots.annotate(p, FIG / "buy-saved.png", [
        {"selector": "tr:has-text('Locked'):has-text('honey jars') >> td >> nth=2", "n": 1, "position": "right"},
        {"text": "GD-P1-BUY-4", "exact": True, "n": 2, "position": "left", "index": 0},
        {"text": "160 FCFA", "exact": True, "n": 3, "position": "right", "index": 0},
        {"text": "Edit purchase", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 160, "y": 180, "width": 1440, "height": 860})
    print("BUY", txt(p, 1500)[300:900])
def CANCEL_DONE():
    shots.annotate(p, FIG / "cancel-done.png", [
        {"selector": "tr:has-text('GD-P1-BUY-4') >> td >> nth=6", "n": 1, "position": "inside"},
        {"selector": "tr:has-text('GD-P1-BUY-4') >> td >> nth=7", "n": 2, "position": "right"},
    ], crop={"x": 160, "y": 330, "width": 1440, "height": 560})
if "cancelfig" in steps:
    gor("/dashboard/fabrication-intrants")
    CANCEL_DONE()
if "editcancel" in steps:
    gor("/dashboard/fabrication-intrants")
    row = p.locator("tr:has-text('GD-P1-BUY-4')")
    row.get_by_text("Edit purchase", exact=True).click(); p.wait_for_timeout(1200)
    p.fill("#fab-pedit-cost", "165"); p.wait_for_timeout(300)
    shots.annotate(p, FIG / "edit-purchase.png", [
        {"selector": "#fab-pedit-supplier", "n": 1, "position": "top"},
        {"selector": "#fab-pedit-ref", "n": 2, "position": "top"},
        {"selector": "#fab-pedit-cost", "n": 3, "position": "top"},
        {"selector": "button[form=fab-purchase-edit-form]", "n": 4, "position": "top"},
    ], crop="[role=dialog]")
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(600)
    row.get_by_text("Cancel purchase", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#fab-cancel-reason", "Wrong unit cost typed. The purchase will be entered again.")
    shots.annotate(p, FIG / "cancel-form.png", [
        {"selector": "#fab-cancel-reason", "n": 1, "position": "top"},
        {"selector": "button[form=fab-cancel-form]", "n": 2, "position": "top"},
    ], crop="[role=dialog]")
    p.locator("button[form=fab-cancel-form]").click(); p.wait_for_timeout(3000)
    p.wait_for_timeout(4500)
    CANCEL_DONE()
    p.locator("tr:has-text('GD-P2-BUY-1')").get_by_text("Cancel purchase", exact=True).click(); p.wait_for_timeout(1000)
    p.fill("#fab-cancel-reason", "Entered by mistake.")
    p.locator("button[form=fab-cancel-form]").click(); p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "cancel-refused.png", [
        {"selector": "#fab-cancel-reason", "n": 1, "position": "top"},
        {"selector": "[role=alert]", "n": 2, "position": "right", "outline": False},
        {"selector": "button[form=fab-cancel-form]", "n": 3, "position": "top"},
    ], crop="[role=dialog]")
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(600)
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "bottom"},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=0", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 460})
shots.close(pw, br)
