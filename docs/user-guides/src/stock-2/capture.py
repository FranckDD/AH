"""Capture script for guide stock-2 (physical count). Run from the repo root:
    python docs/user-guides/src/stock-2/capture.py [step ...]
Steps that act on the dev database are marked "acts". Demo data is fake.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["explore"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-stock1"
PROFILE_ADMIN = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-stock2-admin"
CR = {"x": 276, "y": 60, "width": 1324, "height": 700}


def txt(p, name, n=3000):
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


def session(role="stock", offline=False, height=1000):
    prof = PROFILE if role == "stock" else PROFILE_ADMIN
    pw, br, p = shots.launch(width=1600, height=height, profile_dir=str(prof), offline=offline)
    if not offline:
        shots.login(p, role)
        p.wait_for_timeout(2500)
    p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
    return pw, br, p


if "explore" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-count")
    txt(p, "count-start")
    shots.shot(p, FIG / "_count-start.png")
    p.get_by_role("tab", name="Frequency").click(); p.wait_for_timeout(1500)
    txt(p, "freq")
    shots.shot(p, FIG / "_freq.png")
    p.get_by_role("tab", name="History").click(); p.wait_for_timeout(1500)
    txt(p, "hist")
    shots.shot(p, FIG / "_hist.png")
    shots.close(pw, br)

if "freq" in steps:
    # prerequisite: count 1122 shifted 40 days back in the dev DB (restored at the end of the work)
    pw, br, p = session()
    go(p, "/dashboard/stock-count")
    p.get_by_role("tab", name="Frequency").click(); p.wait_for_timeout(1500)
    txt(p, "freq-overdue")
    shots.annotate(p, FIG / "frequency.png", [
        {"text": "Never counted", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Overdue", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Up to date", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Show only products overdue", "n": 4, "position": "right"},
        {"text": "Last count", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Status", "exact": True, "n": 6, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 800})
    shots.close(pw, br)


# ---------- API helpers (only to simulate other people working while the count is open) ----------
_tok = {}


def api(role, method, path, **kw):
    import requests
    if role not in _tok:
        a = shots.account(role)
        r = requests.post("http://127.0.0.1:8000/auth/login", data={"username": a["username"], "password": a["password"]})
        _tok[role] = r.json()["access_token"]
    r = requests.request(method, "http://127.0.0.1:8000" + path, headers={"Authorization": "Bearer " + _tok[role]}, **kw)
    print("API", role, method, path, r.status_code, r.text[:200])
    return r


def receipt_arrives(product_id, qty, ref):
    """The assistant records a supplier receipt and the stock controller validates it."""
    import datetime
    r = api("assistant", "POST", "/stock/receipts", json={
        "origin": "fournisseur", "supplier": "Pharma Plus", "delivery_ref": ref,
        "received_date": datetime.date.today().isoformat(),
        "lines": [{"product_id": product_id, "qty_expected": qty, "qty_good": qty}]})
    rid = r.json()["id"]
    api("stock", "POST", f"/stock/receipts/{rid}/validate")


def fill_qty(p, pid, value):
    f = p.locator(f"#qty-{pid}")
    f.fill(value)
    f.press("Tab")
    p.wait_for_timeout(300)


if "count1" in steps:
    # acts: opens, fills and validates count A (run once). A supplier receipt for Carnet 2 arrives during the count.
    pw, br, p = session(height=1500)
    go(p, "/dashboard/stock-count")
    shots.annotate(p, FIG / "start.png", [
        {"selector": "#count-scope", "n": 1, "position": "top"},
        {"text": "Start a count", "exact": True, "n": 2, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 520})
    p.select_option("#count-scope", "selection")
    p.get_by_text("Start a count", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "c1-open", 2500)
    r = api("stock", "GET", "/stock-counts?status=en_cours&mine=true")
    cid = r.json()["items"][0]["id"]
    api("stock", "GET", f"/stock-counts/{cid}")
    shots.shot(p, FIG / "_c1-open.png")
    fill_qty(p, 7, "5")         # Api1
    fill_qty(p, 3, "12")        # carnet 1
    fill_qty(p, 4, "58")        # Carnet 2
    p.wait_for_timeout(1500)
    receipt_arrives(4, 10, "PP-8841")
    fill_qty(p, 5, "3x")        # invalid
    shots.shot(p, FIG / "_c1-invalid.png")
    txt(p, "c1-invalid", 3500)
    shots.annotate(p, FIG / "invalid.png", [
        {"selector": "#qty-5", "n": 1, "position": "top"},
        {"text": "Enter a whole number between", "n": 2, "position": "right", "outline": False},
        {"text": "Fix the invalid quantities", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 276, "y": 700, "width": 1324, "height": 800})
    fill_qty(p, 5, "29")
    fill_qty(p, 10, "80")       # Efferalgan
    p.get_by_role("button", name="Note").nth(3).click(); p.wait_for_timeout(300)   # Carnet 2
    p.locator("#obs-4").fill("Two booklets lent to the ward, not yet returned.")
    p.wait_for_timeout(300)
    txt(p, "c1-filled", 3500)
    shots.annotate(p, FIG / "count-form.png", [
        {"selector": "#count-search", "n": 1, "position": "top"},
        {"selector": "#qty-4", "n": 2, "position": "top"},
        {"selector": "#obs-4", "n": 3, "position": "right"},
        {"text": "product(s) counted out of", "n": 4, "position": "top"},
        {"text": "Validate the count", "exact": True, "n": 5, "position": "top"},
        {"text": "Abandon the count", "exact": True, "n": 6, "position": "left"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 1400})
    p.get_by_text("Validate the count", exact=True).click(); p.wait_for_timeout(3500)
    txt(p, "c1-result", 4000)
    shots.shot(p, FIG / "_c1-result.png")
    shots.close(pw, br)

if "count2" in steps:
    # acts: count B recounts Carnet 3 (no gap, replaces request 2194) and Api1 (new gap, replaces 2195). Run once.
    pw, br, p = session(height=1500)
    go(p, "/dashboard/stock-count")
    p.get_by_text("Start a count", exact=True).click(); p.wait_for_timeout(2500)
    fill_qty(p, 5, "30"); fill_qty(p, 7, "4")
    api("stock", "POST", "/stock-counts", json={"scope": "tous"})   # second start must be refused
    p.reload(); p.wait_for_timeout(3500); toast_close(p)
    txt(p, "c2-reload", 1800)
    shots.shot(p, FIG / "_c2-reload.png")
    fill_qty(p, 5, "30"); fill_qty(p, 7, "4")
    p.get_by_text("Validate the count", exact=True).click(); p.wait_for_timeout(3500)
    txt(p, "c2-result", 4000)
    shots.close(pw, br)

if "views" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/stock-count", 3500)
    p.get_by_text("Lab stock", exact=True).first.click(); p.wait_for_timeout(500)
    p.get_by_text("Lab stock", exact=True).first.click(); p.wait_for_timeout(500)
    shots.annotate(p, FIG / "menu.png", [
        {"text": "Stock management", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "Stock count", "exact": True, "n": 2, "position": "right", "index": 0},
    ], crop={"x": 0, "y": 60, "width": 330, "height": 420})
    # bell
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    items = p.locator("div.absolute.right-0.mt-2 div.cursor-pointer")
    for k, t in enumerate(items.all_inner_texts()[:14]): print("BELL", k, t.replace(chr(10), " / "))
    shots.shot(p, FIG / "_bell.png", crop={"x": 1000, "y": 0, "width": 600, "height": 700})
    p.keyboard.press("Escape")
    # forbidden
    go(p, "/dashboard/stock-adjustment-requests", 1500)
    print("ADJ URL", p.url); txt(p, "adj-forbidden", 600)
    # history
    go(p, "/dashboard/stock-count")
    p.get_by_role("tab", name="History").click(); p.wait_for_timeout(1500)
    p.get_by_text("View details", exact=True).first.click(); p.wait_for_timeout(2000)
    txt(p, "hist-detail", 3500)
    shots.shot(p, FIG / "_hist-detail.png")
    shots.close(pw, br)

if "history" in steps:
    pw, br, p = session(height=1500)
    go(p, "/dashboard/stock-count")
    p.get_by_role("tab", name="History").click(); p.wait_for_timeout(1500)
    p.get_by_text("View details", exact=True).nth(1).click(); p.wait_for_timeout(2000)
    shots.annotate(p, FIG / "history.png", [
        {"selector": "#count-date-from", "n": 1, "position": "top"},
        {"text": "Lines", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "View details", "exact": True, "n": 3, "position": "top", "index": 1},
        {"text": "System", "exact": True, "n": 4, "position": "top", "index": 0},
        {"text": "Gap", "exact": True, "n": 5, "position": "top", "index": 0},
        {"text": "Movements after counting", "exact": True, "n": 6, "position": "top", "index": 0},
        {"text": "Adjustment request", "exact": True, "n": 7, "position": "top", "index": 0},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 1250})
    p.locator("button[title='Notifications']").click(); p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=0", "n": 1, "position": "left", "outline": False},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=1", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 480})
    p.locator("div.absolute.right-0.mt-2 div.cursor-pointer").first.click(); p.wait_for_timeout(2500)
    print("BELL CLICK ->", p.url)
    shots.close(pw, br)

if "abandon" in steps:
    # acts: opens a count and abandons it (run once)
    pw, br, p = session(height=1100)
    go(p, "/dashboard/stock-count")
    p.get_by_text("Start a count", exact=True).click(); p.wait_for_timeout(2500)
    fill_qty(p, 8, "150")
    r = api("stock", "POST", "/stock-counts", json={"scope": "tous"})
    print("SECOND START", r.status_code, r.text)
    p.get_by_text("Abandon the count", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "abandoned", 1800)
    shots.annotate(p, FIG / "abandoned.png", [
        {"text": "The count was abandoned.", "n": 1, "position": "right", "outline": False},
        {"text": "Start a count", "exact": True, "n": 2, "position": "top"},
    ], crop={"x": 276, "y": 60, "width": 1324, "height": 620})
    shots.close(pw, br)

if "offline" in steps:
    pw, br, p = session(offline=True)
    p.goto(shots.BASE_URL + "/dashboard/stock-count"); p.wait_for_timeout(8000)
    toast_close(p)
    txt(p, "off-count", 1500)
    shots.shot(p, FIG / "_off-count.png")
    p.get_by_text("Start a count", exact=True).click(); p.wait_for_timeout(2500)
    txt(p, "off-start", 1500)
    shots.annotate(p, FIG / "offline.png", [
        {"text": "Offline", "n": 1, "position": "bottom", "index": 0},
    ], crop={"x": 276, "y": 0, "width": 1324, "height": 520})
    p.get_by_role("tab", name="Frequency").click(); p.wait_for_timeout(2000)
    txt(p, "off-freq", 800)
    shots.close(pw, br)

if "movements" in steps:
    pw, br, p = session()
    go(p, "/dashboard/stock-movements", 3000)
    p.select_option("#mov-product", label="Carnet 2"); p.click("button[type=submit]"); p.wait_for_timeout(2500)
    txt(p, "mv-carnet2", 2500)
    shots.close(pw, br)
