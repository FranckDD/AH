"""Capture script for guide production-2. Run from the repo root:
    python docs/user-guides/src/production-2/capture.py [step ...]
Steps that act on the dev database are marked "acts". Demo data is fake.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["explore"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-production2"


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
        shots.login(p, "production")
        p.wait_for_timeout(2500)
    p.on("dialog", lambda d: (print("DIALOG", d.message), d.accept()))
    return pw, br, p


if "explore" in steps:
    pw, br, p = session()
    go(p, "/dashboard/fabrication-lots")
    txt(p, "lots", 3000)
    shots.shot(p, FIG / "_lots.png")
    p.locator("tr:has-text('FAB-2026-0001')").get_by_text("Open", exact=True).click(); p.wait_for_timeout(2500)
    print(p.url)
    txt(p, "draft", 3000)
    shots.shot(p, FIG / "_draft.png")
    shots.close(pw, br)

def pick(p, sel, contains):
    labels = p.locator(sel + " option").all_inner_texts()
    for l in labels:
        if contains in l:
            p.select_option(sel, label=l); return l
    raise SystemExit("no option %s in %s" % (contains, labels))


def setline(p, idx, contains, qty):
    pick(p, "#fab-draft-purchase-%d" % idx, contains)
    p.fill("#fab-draft-qty-%d" % idx, qty)


def err(p):
    try:
        return p.locator("[role=alert]").first.inner_text(timeout=1500)
    except Exception:
        return None


if "make" in steps:
    # acts: creates batch A (Miel Pure) in draft, tries invalid drafts
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-lots")
    p.get_by_text("New batch", exact=True).first.click(); p.wait_for_timeout(1000)
    txt(p, "newbatch", 1500)
    pick(p, "#fab-batch-product", "Miel Pure")
    p.fill("#fab-batch-producer", "Demo producer")
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "new-batch.png", [
        {"selector": "#fab-batch-product", "n": 1, "position": "top"},
        {"selector": "#fab-batch-date", "n": 2, "position": "top"},
        {"selector": "#fab-batch-producer", "n": 3, "position": "top"},
        {"selector": "button[form=fab-batch-form]", "n": 4, "position": "top"},
    ], crop={"x": 330, "y": 80, "width": 940, "height": 700})
    p.locator("button[form=fab-batch-form]").click(); p.wait_for_timeout(3000)
    print("URL", p.url)
    txt(p, "created", 1500)
    # test 1: honey only (no container)
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(500)
    setline(p, 0, "honey jars", "5")
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(2500)
    print("ERR no container:", err(p)); txt(p, "err-nocontainer", 1500)
    # test 2: container decimal
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(500)
    setline(p, 1, "glass bottles", "20.5")
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(2500)
    print("ERR decimal container:", err(p)); txt(p, "err-decimal", 1500)
    # test 3: more than remaining
    p.fill("#fab-draft-qty-1", "500")
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(2500)
    print("ERR over remaining:", err(p)); txt(p, "err-over", 1500)
    # test 4: same purchase twice
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(500)
    setline(p, 2, "honey jars", "1")
    p.fill("#fab-draft-qty-1", "20")
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(2500)
    print("ERR same purchase twice:", err(p)); txt(p, "err-dup", 1500)
    shots.close(pw, br)


def open_batch(p, number):
    go(p, "/dashboard/fabrication-lots")
    p.locator("tr:has-text('%s')" % number).get_by_text("Open", exact=True).click(); p.wait_for_timeout(2500)


def msg(p):
    out = []
    for sel in ("[role=alert]", "[role=status]"):
        try:
            out += [x.strip() for x in p.locator(sel).all_inner_texts() if x.strip()]
        except Exception:
            pass
    return out


if "flow1" in steps:
    # acts: fixes draft of FAB-2026-0004 (two-container test first), starts it
    pw, br, p = session(height=1250)
    open_batch(p, "FAB-2026-0004")
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(500)
    setline(p, 2, "Remaining 10", "5")
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(2500)
    print("ERR two containers:", msg(p))
    # remove line 2 (third) and the empty extra; fix bottles to 20
    p.get_by_role("button", name="Remove").nth(2).click(); p.wait_for_timeout(400)
    p.fill("#fab-draft-qty-1", "20")
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(2500)
    print("SAVED:", msg(p))
    txt(p, "draft-ok", 2500)
    shots.shot(p, FIG / "_draft-ok.png")
    shots.close(pw, br)

if "draftfig" in steps:
    pw, br, p = session(height=1250)
    open_batch(p, "FAB-2026-0004")
    shots.annotate(p, FIG / "draft.png", [
        {"text": "Consumptions", "exact": True, "n": 1, "position": "top", "index": 0},
        {"selector": "#fab-draft-purchase-0", "n": 2, "position": "top"},
        {"selector": "#fab-draft-qty-0", "n": 3, "position": "top"},
        {"text": "Remove", "exact": True, "n": 4, "position": "right", "index": 0},
        {"text": "Add a line", "exact": True, "n": 5, "position": "left"},
        {"text": "Cancel batch", "exact": True, "n": 6, "position": "top"},
        {"text": "Save", "exact": True, "n": 7, "position": "top", "index": 0},
        {"text": "Start production", "exact": True, "n": 8, "position": "top"},
    ], crop={"x": 160, "y": 160, "width": 1440, "height": 850})
    shots.close(pw, br)

if "start" in steps:
    # acts: starts FAB-2026-0004 (reserves stock)
    pw, br, p = session(height=1250)
    open_batch(p, "FAB-2026-0004")
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(3000)
    print("START:", msg(p))
    txt(p, "started", 2500)
    shots.annotate(p, FIG / "started.png", [
        {"text": "Batch in production, stock reserved.", "n": 1, "position": "right", "outline": False},
        {"text": "In production", "exact": True, "n": 2, "position": "right", "index": 0},
        {"text": "Cancel batch", "exact": True, "n": 3, "position": "top"},
        {"text": "Finish and enter results", "exact": True, "n": 4, "position": "top"},
    ], crop={"x": 160, "y": 60, "width": 1440, "height": 700})
    shots.close(pw, br)

if "finish" in steps:
    # acts: finishes FAB-2026-0004 (good 17, broken 1, rejected 0, lost 0.5): 2 missing of 20 = 10 percent
    pw, br, p = session(height=1250)
    open_batch(p, "FAB-2026-0004")
    p.get_by_role("button", name="Finish and enter results").click(); p.wait_for_timeout(1000)
    p.fill("#fab-finish-good", "21"); p.wait_for_timeout(200)
    p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(2500)
    print("ERR over expected:", msg(p))
    p.fill("#fab-finish-good", "12.5"); p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(1500)
    print("ERR decimal good:", msg(p), p.url)
    p.fill("#fab-finish-good", "17"); p.fill("#fab-finish-damaged", "1"); p.fill("#fab-finish-rejected", "0")
    p.fill("#fab-finish-lost", "0.5"); p.wait_for_timeout(300)
    shots.annotate(p, FIG / "finish-form.png", [
        {"selector": "#fab-finish-good", "n": 1, "position": "top"},
        {"selector": "#fab-finish-damaged", "n": 2, "position": "top"},
        {"selector": "#fab-finish-rejected", "n": 3, "position": "top"},
        {"selector": "#fab-finish-lost", "n": 4, "position": "top"},
        {"selector": "button[form=fab-finish-form]", "n": 5, "position": "top"},
    ], crop={"x": 330, "y": 80, "width": 940, "height": 600})
    p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(3000)
    print("FIN:", msg(p))
    txt(p, "finished", 3500)
    shots.shot(p, FIG / "_finished.png")
    shots.close(pw, br)

if "out1" in steps:
    # acts: declares outputs on FAB-2026-0004
    pw, br, p = session(height=2300)
    open_batch(p, "FAB-2026-0004")
    shots.shot(p, FIG / "_out0.png")
    txt(p, "out0", 4000)
    print("form visible:", p.locator("#fab-output-form").count())
    # other without note: button state
    p.select_option("#fab-output-reason", value="other") if False else p.select_option("#fab-output-reason", value="autre")
    p.fill("#fab-output-qty", "2"); p.wait_for_timeout(300)
    print("declare disabled (other, no note):", p.locator("#fab-output-form button[type=submit]").is_disabled())
    # too many
    p.fill("#fab-output-note", "x"); p.fill("#fab-output-qty", "99"); p.wait_for_timeout(200)
    p.locator("#fab-output-form button[type=submit]").click(); p.wait_for_timeout(1500)
    print("ERR too many:", msg(p))
    # sample 3
    p.select_option("#fab-output-reason", value="echantillon"); p.fill("#fab-output-qty", "3")
    p.fill("#fab-output-note", "Sample for a partner clinic"); p.wait_for_timeout(300)
    shots.shot(p, FIG / "_out-form.png")
    p.locator("#fab-output-form button[type=submit]").click(); p.wait_for_timeout(2500)
    print("DECL1:", msg(p))
    # mistaken one
    p.select_option("#fab-output-reason", value="echantillon"); p.fill("#fab-output-qty", "1")
    p.locator("#fab-output-form button[type=submit]").click(); p.wait_for_timeout(2500)
    print("DECL2:", msg(p))
    # other 2
    p.select_option("#fab-output-reason", value="autre"); p.fill("#fab-output-qty", "2")
    p.fill("#fab-output-note", "Two bottles leaked in the crate"); p.wait_for_timeout(200)
    p.locator("#fab-output-form button[type=submit]").click(); p.wait_for_timeout(2500)
    print("DECL3:", msg(p))
    txt(p, "out1", 5000)
    shots.shot(p, FIG / "_out1.png")
    shots.close(pw, br)

if "out2" in steps:
    # acts: cancels the mistaken sample of 1 on FAB-2026-0004
    pw, br, p = session(height=2300)
    open_batch(p, "FAB-2026-0004")
    p.locator("li:has-text('Sample, 1')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(1000)
    shots.shot(p, FIG / "_cancel-panel.png")
    p.fill("#fab-output-cancel-reason", "Declared by mistake, no bottle left the batch")
    p.wait_for_timeout(300)
    shots.shot(p, FIG / "_cancel-panel2.png")
    p.locator("button[form=fab-output-cancel-form]").click(); p.wait_for_timeout(2500)
    print("CANC:", msg(p))
    txt(p, "out2", 5000)
    shots.close(pw, br)

if "out3" in steps:
    pw, br, p = session(height=2300)
    open_batch(p, "FAB-2026-0004")
    p.get_by_role("button", name="Reopen").click(); p.wait_for_timeout(2500)
    print("REOPEN with outputs:", msg(p))
    p.get_by_role("button", name="Cancel batch").click(); p.wait_for_timeout(1000)
    p.fill("#fab-batch-cancel-reason", "test"); p.locator("button[form=fab-batch-cancel-form]").click(); p.wait_for_timeout(2500)
    print("CANCEL with outputs:", msg(p))
    shots.close(pw, br)
    pw, br, p = session(height=2300)
    open_batch(p, "FAB-2026-0004")
    shots.annotate(p, FIG / "outputs.png", [
        {"text": "Good bottles: 17, outputs: 5, to ship: 12", "n": 1, "position": "right", "outline": False},
        {"text": "Cancel", "exact": True, "n": 2, "position": "left", "index": 0},
        {"text": "Cancelled", "exact": True, "n": 3, "position": "right", "index": 0},
        {"selector": "#fab-output-reason", "n": 4, "position": "top"},
        {"selector": "#fab-output-qty", "n": 5, "position": "top"},
        {"selector": "#fab-output-note", "n": 6, "position": "top"},
        {"text": "Declare the output", "exact": True, "n": 7, "position": "top"},
    ], crop={"x": 262, "y": 1330, "width": 1338, "height": 830})
    shots.close(pw, br)

if "ship" in steps:
    # acts: ships FAB-2026-0004 (12 bottles to the centre, creates a production lot)
    pw, br, p = session(height=1000)
    open_batch(p, "FAB-2026-0004")
    p.get_by_role("button", name="Validate balance and ship").click(); p.wait_for_timeout(1000)
    txt(p, "ship-panel", 2000)
    print("ship disabled empty:", p.locator("button[form=fab-ship-form]").is_disabled())
    p.fill("#fab-ship-delivery", "2026-10-30"); p.fill("#fab-ship-expiry", "2027-12-31")
    print("ship disabled no justification:", p.locator("button[form=fab-ship-form]").is_disabled())
    p.fill("#fab-ship-justification", "Two bottles cracked while capping. The rest was counted twice by two people.")
    p.wait_for_timeout(300)
    shots.screenshot = None
    shots.shot(p, FIG / "_ship-panel.png")
    shots.annotate(p, FIG / "ship-form.png", [
        {"selector": "#fab-ship-delivery", "n": 1, "position": "top"},
        {"selector": "#fab-ship-expiry", "n": 2, "position": "top"},
        {"text": "Shortfall out of tolerance", "n": 3, "position": "right", "outline": False},
        {"selector": "#fab-ship-justification", "n": 4, "position": "top"},
        {"selector": "button[form=fab-ship-form]", "n": 5, "position": "top"},
    ])
    p.locator("button[form=fab-ship-form]").click(); p.wait_for_timeout(3500)
    print("SHIP:", msg(p))
    txt(p, "shipped", 3500)
    shots.close(pw, br)


def make_batch(p, lines):
    """Creates a Miel Pure batch in the UI and fills the draft lines [(contains, qty), ...]. Returns number."""
    go(p, "/dashboard/fabrication-lots")
    p.get_by_text("New batch", exact=True).first.click(); p.wait_for_timeout(1000)
    pick(p, "#fab-batch-product", "Miel Pure")
    p.fill("#fab-batch-producer", "Demo producer")
    p.locator("button[form=fab-batch-form]").click(); p.wait_for_timeout(3000)
    number = p.locator("h1").first.inner_text().strip()
    for i, (c, q) in enumerate(lines):
        p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(400)
        setline(p, i, c, q)
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(2500)
    print("MADE", number, msg(p))
    return number


if "flowB" in steps:
    # acts: batch B (FAB-2026-0005): 50 bottles, 10 jars; finish good 49 (1 missing = exactly 2 percent)
    pw, br, p = session(height=1000)
    n = make_batch(p, [("honey jars | Demo supplier", "10"), ("Remaining 130", "50")])
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(3000)
    print("START:", msg(p))
    p.get_by_role("button", name="Finish and enter results").click(); p.wait_for_timeout(1000)
    p.fill("#fab-finish-good", "49"); p.fill("#fab-finish-lost", "1,5"); p.wait_for_timeout(300)
    shots.shot(p, FIG / "_finish-panel.png")
    p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(1500)
    print("comma liquid:", msg(p))
    p.fill("#fab-finish-lost", "1.5")
    shots.annotate(p, FIG / "finish-form.png", [
        {"selector": "#fab-finish-good", "n": 1, "position": "top"},
        {"selector": "#fab-finish-damaged", "n": 2, "position": "top"},
        {"selector": "#fab-finish-rejected", "n": 3, "position": "top"},
        {"selector": "#fab-finish-lost", "n": 4, "position": "top"},
        {"selector": "button[form=fab-finish-form]", "n": 5, "position": "top"},
    ], crop={"x": 340, "y": 150, "width": 920, "height": 560})
    p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(3000)
    print("FIN:", msg(p))
    txt(p, "B-finished", 3000)
    shots.close(pw, br)

if "flowB2" in steps:
    # acts: reopens FAB-2026-0005, finishes again (48 good, 1 broken), ships it without justification
    pw, br, p = session(height=1000)
    open_batch(p, "FAB-2026-0005")
    p.get_by_role("button", name="Reopen").click(); p.wait_for_timeout(2500)
    print("REOPEN:", msg(p))
    p.get_by_role("button", name="Finish and enter results").click(); p.wait_for_timeout(1000)
    p.fill("#fab-finish-good", "48"); p.fill("#fab-finish-damaged", "1"); p.fill("#fab-finish-rejected", "0")
    p.fill("#fab-finish-lost", "1.5"); p.wait_for_timeout(300)
    shots.annotate(p, FIG / "finish-form.png", [
        {"selector": "#fab-finish-good", "n": 1, "position": "top"},
        {"selector": "#fab-finish-damaged", "n": 2, "position": "top"},
        {"selector": "#fab-finish-rejected", "n": 3, "position": "top"},
        {"selector": "#fab-finish-lost", "n": 4, "position": "top"},
        {"selector": "button[form=fab-finish-form]", "n": 5, "position": "top"},
    ], crop={"x": 340, "y": 150, "width": 920, "height": 560})
    p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(3000)
    print("FIN:", msg(p))
    p.get_by_role("button", name="Validate balance and ship").click(); p.wait_for_timeout(1000)
    print("justification field:", p.locator("#fab-ship-justification").count())
    p.fill("#fab-ship-delivery", "2026-10-31")
    shots.shot(p, FIG / "_ship-b.png")
    p.locator("button[form=fab-ship-form]").click(); p.wait_for_timeout(3500)
    print("SHIP:", msg(p))
    shots.close(pw, br)
    pw, br, p = session(height=1900)
    open_batch(p, "FAB-2026-0005")
    shots.shot(p, FIG / "_shipped-b.png")
    txt(p, "B-shipped", 3500)
    shots.close(pw, br)

def stocks():
    sys.path.insert(0, "C:/Users/DD/AppData/Local/Temp/claude/c--Users-DD-Desktop-Project-Stage-ah2-v2-AH2/27ff0bbd-56cf-4861-b20d-d557a0b9deb2/scratchpad")
    import api
    s, j = api.call("production", "GET", "/fabrication/intrants")
    return {x["name"]: x["stock"] for x in j}


if "flowC" in steps:
    # acts: batch C (cancelled while in production), batch D (left in production)
    pw, br, p = session(height=1000)
    print("stock before:", stocks())
    n = make_batch(p, [("honey jars | Demo supplier", "2"), ("Remaining 10", "10")])
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(3000)
    print("START:", msg(p), "stock reserved:", stocks())
    p.get_by_role("button", name="Cancel batch").click(); p.wait_for_timeout(1000)
    p.fill("#fab-batch-cancel-reason", "Wrong container chosen, the batch is prepared again")
    shots.annotate(p, FIG / "cancel-batch.png", [
        {"text": "Reserved quantities will be given back", "n": 1, "position": "right", "outline": False},
        {"selector": "#fab-batch-cancel-reason", "n": 2, "position": "top"},
        {"selector": "button[form=fab-batch-cancel-form]", "n": 3, "position": "top"},
    ], crop={"x": 340, "y": 150, "width": 920, "height": 560})
    p.locator("button[form=fab-batch-cancel-form]").click(); p.wait_for_timeout(3000)
    print("CANCEL:", msg(p), "stock restored:", stocks())
    txt(p, "C-cancelled", 1800)
    shots.close(pw, br)

if "flowD" in steps:
    # acts: batch D (FAB-2026-0007) left in production; batch E (0008) cancelled as a draft
    pw, br, p = session(height=1000)
    n = make_batch(p, [("honey jars | Demo supplier", "1"), ("Remaining 80", "20")])
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(3000)
    print("START D:", msg(p))
    n = make_batch(p, [("honey jars | Demo supplier", "1"), ("Remaining 60", "5")])
    p.get_by_role("button", name="Cancel batch").click(); p.wait_for_timeout(1000)
    print("draft cancel panel hint present:", p.get_by_text("Reserved quantities").count())
    p.fill("#fab-batch-cancel-reason", "Created twice by mistake")
    p.locator("button[form=fab-batch-cancel-form]").click(); p.wait_for_timeout(3000)
    print("CANCEL draft:", msg(p))
    print("buttons left:", [b.inner_text() for b in p.locator("main button").all()][:10])
    shots.close(pw, br)

if "list" in steps:
    pw, br, p = session(height=1000)
    go(p, "/dashboard/fabrication-lots")
    txt(p, "lots2", 2500)
    p.select_option("#fab-lots-status", label="Shipped"); p.wait_for_timeout(1500)
    print("shipped rows:", p.locator("tbody tr").count())
    p.select_option("#fab-lots-status", label="Cancelled"); p.wait_for_timeout(1500)
    print("cancelled rows:", p.locator("tbody tr").count())
    p.select_option("#fab-lots-status", label="All statuses")
    p.fill("#fab-lots-from", "2026-10-27"); p.wait_for_timeout(1500)
    txt(p, "lots-future", 1500)
    p.fill("#fab-lots-to", "2026-10-26"); p.wait_for_timeout(1500)
    print("range msg:", msg(p))
    p.fill("#fab-lots-from", ""); p.fill("#fab-lots-to", ""); p.wait_for_timeout(300)
    p.select_option("#fab-lots-status", label="In production"); p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "lots.png", [
        {"text": "New batch", "exact": True, "n": 1, "position": "left"},
        {"selector": "#fab-lots-status", "n": 2, "position": "top"},
        {"selector": "#fab-lots-from", "n": 3, "position": "top"},
        {"selector": "#fab-lots-to", "n": 4, "position": "top"},
        {"text": "Open", "exact": True, "n": 5, "position": "left", "index": 0},
    ], crop={"x": 262, "y": 60, "width": 1338, "height": 400})
    p.select_option("#fab-lots-status", label="All statuses"); p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "lots-all.png", [
        {"text": "Batch number", "exact": True, "n": 1, "position": "top"},
        {"text": "Good bottles", "exact": True, "n": 2, "position": "top"},
        {"text": "Out of tolerance", "exact": True, "n": 3, "position": "right", "index": 0},
        {"text": "Open", "exact": True, "n": 4, "position": "left", "index": 0},
    ], crop={"x": 262, "y": 60, "width": 1338, "height": 700})
    shots.close(pw, br)

if "suivi" in steps:
    pw, br, p = session(height=1900)
    go(p, "/dashboard/fabrication-suivi", 4000)
    txt(p, "suivi2", 5000)
    shots.shot(p, FIG / "_suivi2.png")
    shots.close(pw, br)

if "offline" in steps:
    pw, br, p = session(offline=True, height=900)
    go(p, "/dashboard/fabrication-lots", 4000)
    txt(p, "off-lots", 1500)
    shots.shot(p, FIG / "_off-lots.png")
    p.get_by_text("New batch", exact=True).first.click(); p.wait_for_timeout(1500)
    print("products options:", p.locator("#fab-batch-product option").all_inner_texts())
    pick(p, "#fab-batch-product", "Miel") if p.locator("#fab-batch-product option").count() > 1 else None
    p.locator("button[form=fab-batch-form]").click(); p.wait_for_timeout(4000)
    print("create offline:", msg(p), p.url)
    txt(p, "off-create", 1800)
    shots.shot(p, FIG / "_off-create.png")
    go(p, "/dashboard/fabrication-lots/3155", 4000)
    txt(p, "off-batch", 1500)
    shots.close(pw, br)

if "offline2" in steps:
    pw, br, p = session(height=1000)
    open_batch(p, "FAB-2026-0007")
    p.get_by_role("button", name="Finish and enter results").click(); p.wait_for_timeout(1000)
    p.fill("#fab-finish-good", "18"); p.fill("#fab-finish-damaged", "1")
    br.set_offline(True)
    p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(4000)
    print("OFFLINE finish:", msg(p))
    shots.annotate(p, FIG / "offline.png", [
        {"text": "Could not save. Try again.", "n": 1, "position": "right", "outline": False},
        {"selector": "button[form=fab-finish-form]", "n": 2, "position": "top"},
    ], crop={"x": 340, "y": 150, "width": 920, "height": 560})
    br.set_offline(False)
    p.get_by_text("Close", exact=True).click(); p.wait_for_timeout(500)
    print("status still:", p.get_by_text("In production").count())
    shots.close(pw, br)

if "qtytests" in steps:
    pw, br, p = session(height=1000)
    open_batch(p, "FAB-2026-0001")
    p.get_by_role("button", name="Start production").click(); p.wait_for_timeout(2500)
    print("start empty:", msg(p))
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(400)
    setline(p, 0, "honey jars | Demo supplier", "5.5555")
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(1500)
    print("4 decimals:", msg(p))
    p.fill("#fab-draft-qty-0", "0")
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(1500)
    print("zero:", msg(p))
    p.fill("#fab-draft-qty-0", "abc")
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(1500)
    print("letters:", msg(p))
    p.fill("#fab-draft-qty-0", "2,5")
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(2500)
    print("comma decimal:", msg(p))
    txt(p, "qty-comma", 2500)
    # empty purchase
    p.get_by_text("Add a line", exact=True).click(); p.wait_for_timeout(400)
    p.fill("#fab-draft-qty-1", "3")
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(1500)
    print("no purchase chosen:", msg(p))
    # leave draft clean again
    p.get_by_role("button", name="Remove").nth(1).click(); p.get_by_role("button", name="Remove").nth(0).click(); p.wait_for_timeout(300)
    p.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(2500)
    print("cleaned:", msg(p))
    shots.close(pw, br)

if "edge" in steps:
    # acts on FAB-2026-0007: finish with 0 good, reopen; finish 10 good, declare all as samples, cancel it, reopen
    pw, br, p = session(height=1000)
    open_batch(p, "FAB-2026-0007")
    def finish(good, dam):
        p.get_by_role("button", name="Finish and enter results").click(); p.wait_for_timeout(800)
        p.fill("#fab-finish-good", good); p.fill("#fab-finish-damaged", dam)
        p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(2500)
    finish("0", "19")
    print("zero good buttons:", [b.inner_text().strip() for b in p.locator("button").all() if b.is_visible()])
    p.get_by_role("button", name="Reopen").click(); p.wait_for_timeout(2500)
    finish("10", "9")
    p.select_option("#fab-output-reason", value="echantillon"); p.fill("#fab-output-qty", "10")
    p.locator("#fab-output-form button[type=submit]").click(); p.wait_for_timeout(2500)
    print("all out:", msg(p), "form:", p.locator("#fab-output-form").count(),
          "ship disabled:", p.get_by_role("button", name="Validate balance and ship").is_disabled())
    p.locator("li:has-text('Sample, 10')").get_by_text("Cancel", exact=True).click(); p.wait_for_timeout(800)
    p.fill("#fab-output-cancel-reason", "Test of the all-out case"); p.locator("button[form=fab-output-cancel-form]").click(); p.wait_for_timeout(2500)
    p.get_by_role("button", name="Reopen").click(); p.wait_for_timeout(2500)
    print("final:", msg(p))
    shots.close(pw, br)

if "figs" in steps:
    pw, br, p = session(height=2300)
    open_batch(p, "FAB-2026-0004")
    shots.annotate(p, FIG / "shipped.png", [
        {"text": "Shipped", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "LOT-20261026-005", "n": 2, "position": "right"},
        {"text": "Out of tolerance", "exact": True, "n": 3, "position": "right", "index": 0},
        {"text": "Frozen at shipping", "exact": True, "n": 4, "position": "right"},
        {"text": "Shortfall justification", "n": 5, "position": "right"},
        {"text": "Cost per good bottle", "exact": True, "n": 6, "position": "top"},
    ], crop={"x": 262, "y": 150, "width": 1338, "height": 1140})
    txt(p, "A-shipped", 4000)
    shots.close(pw, br)
    pw, br, p = session(height=2000)
    go(p, "/dashboard/fabrication-suivi", 4000)
    shots.annotate(p, FIG / "suivi.png", [
        {"text": "In production", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Anomalies", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Recent batches", "exact": True, "n": 3, "position": "top"},
        {"text": "Open", "exact": True, "n": 4, "position": "left", "index": 0},
        {"text": "Gap between shipped and received", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 262, "y": 150, "width": 1338, "height": 1330})
    y = int(p.locator("#fab-out-from").bounding_box()["y"]) - 110
    shots.annotate(p, FIG / "suivi-outputs.png", [
        {"selector": "#fab-out-from", "n": 1, "position": "top"},
        {"selector": "#fab-out-reason", "n": 2, "position": "right"},
        {"text": "To check", "exact": True, "n": 3, "position": "right"},
        {"selector": "tr:has-text('FAB-2026-0004') >> text=Cancelled", "n": 4, "position": "left"},
    ], crop={"x": 262, "y": y, "width": 1338, "height": 640})
    shots.close(pw, br)


if "cleanD" in steps:
    pw, br, p = session(height=1000)
    open_batch(p, "FAB-2026-0007")
    p.get_by_role("button", name="Finish and enter results").click(); p.wait_for_timeout(800)
    p.fill("#fab-finish-good", "19"); p.fill("#fab-finish-damaged", "1")
    p.locator("button[form=fab-finish-form]").click(); p.wait_for_timeout(2500)
    p.get_by_role("button", name="Reopen").click(); p.wait_for_timeout(2500)
    print(msg(p))
    shots.close(pw, br)

if "outfilter" in steps:
    pw, br, p = session(height=1900)
    go(p, "/dashboard/fabrication-suivi", 4000)
    rows = lambda: p.locator("tr:has(td):has-text('Miel Pure')").count()
    print("all rows:", rows())
    p.select_option("#fab-out-reason", value="autre"); p.wait_for_timeout(1500); print("other rows:", rows())
    p.select_option("#fab-out-reason", value="echantillon"); p.wait_for_timeout(1500); print("sample rows:", rows())
    p.select_option("#fab-out-reason", value=""); 
    p.fill("#fab-out-from", "2026-10-27"); p.wait_for_timeout(1500); print("from 27/10 rows:", rows(), msg(p))
    p.fill("#fab-out-to", "2026-10-26"); p.wait_for_timeout(1500); print("inverted:", msg(p))
    shots.close(pw, br)

if "figs2" in steps:
    pw, br, p = session(height=2300)
    open_batch(p, "FAB-2026-0004")
    y0 = int(p.get_by_text("Balance", exact=True).first.bounding_box()["y"]) - 40
    yc = int(p.get_by_text("Cost per good bottle", exact=True).bounding_box()["y"]) + 110
    shots.annotate(p, FIG / "shipped.png", [
        {"text": "Out of tolerance", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "Frozen at shipping", "exact": True, "n": 2, "position": "right"},
        {"text": "Shortfall justification", "n": 3, "position": "right"},
        {"text": "Cost per good bottle", "exact": True, "n": 4, "position": "top"},
    ], crop={"x": 262, "y": y0, "width": 1338, "height": yc - y0})
    shots.close(pw, br)
    pw, br, p = session(height=2000)
    go(p, "/dashboard/fabrication-suivi", 4000)
    yr = int(p.get_by_text("Recent batches", exact=True).bounding_box()["y"]) - 30
    shots.annotate(p, FIG / "suivi.png", [
        {"text": "In production", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Anomalies", "exact": True, "n": 2, "position": "top", "index": 0},
    ], crop={"x": 262, "y": 150, "width": 1338, "height": yr - 150})
    ya = int(p.get_by_text("Anomalies", exact=True).nth(1).bounding_box()["y"]) - 30
    shots.annotate(p, FIG / "suivi-anomalies.png", [
        {"text": "Shortfall out of tolerance", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Gap between shipped and received", "exact": True, "n": 2, "position": "top", "index": 0},
    ], crop={"x": 262, "y": ya, "width": 1338, "height": 330})
    shots.close(pw, br)
