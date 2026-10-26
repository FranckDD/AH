"""Capture script for guide promoter-1. Run from the repo root:
    python docs/user-guides/src/promoter-1/capture.py [step ...]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:]
pw, browser, p = shots.launch(width=1600, height=1000)
p.on("dialog", lambda d: (print("DIALOG:", d.message), d.accept()))


def dump(tag, full=False):
    (HERE / f"_{tag}.txt").write_text(p.inner_text("body"), encoding="utf-8")
    p.screenshot(path=str(FIG / f"_{tag}.png"), full_page=full)


def settle(ms=1500):
    p.wait_for_timeout(ms)


def clear_toast():
    p.keyboard.press("Escape")
    p.wait_for_timeout(700)


def reports(preset=None):
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    if preset:
        p.get_by_role("button", name=preset, exact=True).click()
        settle(4000)


if "look" in steps:
    shots.login(p, "promoteur")
    dump("home", True)
    reports()
    dump("rep-today", True)
    p.get_by_role("button", name="30 days", exact=True).click()
    settle(5000)
    dump("rep-30", True)


if "look2" in steps:
    shots.login(p, "promoteur")
    reports()
    dump("rep-today2", True)
    p.locator("button[title='Notifications']").click()
    settle(1200)
    dump("bell")
    p.keyboard.press("Escape")
    reports()
    p.get_by_role("button", name="Custom dates", exact=True).click()
    settle(800)
    dump("custom0")
    p.fill("#rp-from", "2026-10-26"); p.fill("#rp-to", "2026-10-20")
    p.get_by_role("button", name="Apply").click()
    settle(800)
    dump("custom-bad")
    p.fill("#rp-from", "2026-10-20"); p.fill("#rp-to", "2026-10-26")
    p.get_by_role("button", name="Apply").click()
    settle(4000)
    dump("custom-ok", True)
    print("settings card:", p.get_by_text("Daily check settings").count())
    p.fill("#rp-search", "Hon"); settle(1500)
    dump("tbl-search")
    p.fill("#rp-search", ""); p.select_option("#rp-type", "Examen"); settle(2000)
    dump("tbl-exam")
    p.select_option("#rp-type", "Consultation"); settle(2000)
    dump("tbl-cons")
    p.select_option("#rp-type", "Service"); settle(2000)
    dump("tbl-serv")


def card(title):
    return f"xpath=//article[.//h3[normalize-space()='{title}']]"


if "figs" in steps:
    p.set_viewport_size({"width": 1600, "height": 2600})
    shots.login(p, "promoteur")
    reports("7 days")
    p.evaluate("window.scrollTo(0,0)")
    shots.annotate(p, FIG / "reports-top.png", [
        {"text": "Today", "exact": True, "n": 1, "position": "top"},
        {"text": "Custom dates", "exact": True, "n": 2, "position": "top"},
        {"text": "Export as PDF", "exact": True, "n": 3, "position": "right"},
        {"text": "Daily check", "exact": True, "n": 4, "position": "right", "outline": False},
        {"text": "To watch", "exact": True, "n": 5, "position": "left"},
        {"text": "Open the screen", "exact": True, "n": 6, "position": "left", "index": 0},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 800})
    p.get_by_role("button", name="Custom dates", exact=True).click()
    settle(600)
    shots.annotate(p, FIG / "custom-dates.png", [
        {"selector": "#rp-from", "n": 1, "position": "top"},
        {"selector": "#rp-to", "n": 2, "position": "top"},
        {"text": "Apply", "exact": True, "n": 3, "position": "right"},
    ], crop={"x": 262, "y": 180, "width": 900, "height": 260})
    p.get_by_role("button", name="30 days", exact=True).click()
    settle(5000)
    LI = "xpath=//section[@aria-labelledby='control-title']//li[contains(.,'already reported')][1]"
    shots.annotate(p, FIG / "control-item.png", [
        {"selector": LI + "//*[normalize-space()='Pending adjustment']", "n": 1, "position": "bottom"},
        {"selector": LI + "//*[contains(.,'first seen on') and not(*)]", "n": 2, "position": "bottom"},
        {"selector": LI + "//*[contains(.,'already reported on') and not(*)]", "n": 3, "position": "bottom"},
        {"selector": LI + "//*[normalize-space()='Current state']", "n": 4, "position": "bottom"},
    ], crop=LI)
    shots.annotate(p, FIG / "money.png", [
        {"selector": card("Collected over the period"), "n": 1, "position": "top"},
        {"selector": card("Cash gaps"), "n": 2, "position": "top"},
        {"selector": card("Withdrawals and cancelled sales"), "n": 3, "position": "top"},
        {"selector": card("Discounts granted"), "n": 4, "position": "top"},
        {"selector": card("Collected per secretary"), "n": 5, "position": "top"},
    ], crop="section[aria-labelledby=block-money]")
    shots.annotate(p, FIG / "products.png", [
        {"selector": card("Products sold versus received"), "n": 1, "position": "top"},
        {"selector": card("Stock count"), "n": 2, "position": "top"},
        {"selector": card("Out of stock and low stock"), "n": 3, "position": "top"},
    ], crop="section[aria-labelledby=block-products]")
    p.locator("section[aria-labelledby=block-production]").scroll_into_view_if_needed(); settle(500)
    shots.annotate(p, FIG / "production.png", [
        {"selector": card("Batch status"), "n": 1, "position": "top"},
        {"selector": card("Bottles produced, released and shipped"), "n": 2, "position": "top"},
        {"selector": card("Shortfall and cost price"), "n": 3, "position": "top"},
    ], crop="section[aria-labelledby=block-production]")
    for d in p.locator("section[aria-labelledby=block-growth] details").all():
        d.locator("summary").click()
    settle(800)
    shots.annotate(p, FIG / "growth.png", [
        {"selector": card("New patients and consultations over 3 months"), "n": 1, "position": "top"},
        {"text": "See the weekly figures", "exact": True, "n": 2, "position": "right", "index": 0},
        {"selector": card("Sales over 3 months"), "n": 3, "position": "top"},
    ], crop="section[aria-labelledby=block-growth]")
    p.locator("#rp-search").scroll_into_view_if_needed()
    p.select_option("#rp-type", "Examen")
    settle(2000)
    TB = "xpath=//input[@id='rp-search']/ancestor::*[contains(@class,'rounded-card')][1]"
    shots.annotate(p, FIG / "table.png", [
        {"selector": "#rp-search", "n": 1, "position": "top"},
        {"selector": "#rp-type", "n": 2, "position": "top"},
        {"selector": "#rp-category", "n": 3, "position": "top"},
        {"selector": "#rp-sort", "n": 4, "position": "top"},
        {"text": "Next", "exact": True, "n": 5, "position": "top"},
    ], crop=TB)

if "bellfig" in steps:
    p.set_viewport_size({"width": 1600, "height": 900})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    p.locator("button[title='Notifications']").click()
    settle(1200)
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "left"},
        {"text": "Daily check of", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 560})

if "export" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "promoteur")
    reports()
    p.get_by_role("button", name="Export as PDF").click()
    settle(5000)
    shots.annotate(p, FIG / "export-fail.png", [
        {"text": "Export as PDF", "exact": True, "n": 1, "position": "right"},
        {"text": "Could not generate", "n": 2, "position": "right", "outline": False},
    ], crop={"x": 262, "y": 240, "width": 1100, "height": 330})

if "nav" in steps:
    shots.login(p, "promoteur")
    reports("30 days")
    for k in range(3):
        btns = p.get_by_role("button", name="Open the screen")
        print("open buttons", btns.count())
        item = p.locator("section[aria-labelledby=control-title] li").nth(k)
        print(item.inner_text().replace(chr(10), " | ")[:120])
        b = item.get_by_role("button", name="Open the screen")
        if b.count():
            b.click(); settle(3000); print("->", p.url)
            p.screenshot(path=str(FIG / f"_nav{k}.png"))
            reports("30 days")
    for r in ("/dashboard/users", "/dashboard/stock-adjustment-requests", "/dashboard/finance", "/dashboard/logs"):
        shots.goto(p, r); settle(1500); print(r, "->", p.url)


if "homefig" in steps:
    shots.login(p, "promoteur")
    settle(5000)
    clear_toast()
    shots.annotate(p, FIG / "home.png", [
        {"text": "Reports", "exact": True, "n": 1, "position": "right"},
        {"selector": "button[title='Notifications']", "n": 2, "position": "bottom"},
        {"text": "Total Revenue", "exact": True, "n": 3, "position": "top", "outline": False},
        {"text": "Pending discount requests", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 0, "y": 0, "width": 1600, "height": 560})

shots.close(pw, browser)
