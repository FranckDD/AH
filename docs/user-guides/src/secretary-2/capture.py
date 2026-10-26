"""Capture script for guide secretary-2. Run from the repo root:
    python docs/user-guides/src/secretary-2/capture.py [step ...]
Steps (each one performs real actions in the dev database, so run them once, in this order):
    notset start retraits-list retrait-form retrait-saved retrait-cancel sales closure-form
    closure-gap closure-result correction
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:]
pw, browser, p = shots.launch(width=1600, height=1500 if 'closure2' in steps or 'closure3' in steps else 900)


def dump(tag):
    (HERE / f"_{tag}.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.shot(p, FIG / f"_{tag}.png")


def connected():
    try:
        p.get_by_text("Connected").first.wait_for(timeout=30000)
    except Exception:
        pass
    p.wait_for_timeout(500)


role = "admin" if "start" in steps else "secretaire"

if "notset" in steps:
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/cloture")
    connected()
    dump("notset")
    shots.annotate(p, FIG / "not-configured.png", [
        {"text": "Cash closing", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "Till not set up", "n": 2, "position": "left", "outline": False},
    ])

if "start" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/cash-closures")
    connected()
    p.fill("#start-opening", "50000")
    p.get_by_role("button", name="Initialize the cash register").click()
    p.wait_for_timeout(800)
    dump("start-confirm")
    p.locator("[role=alert]").first.scroll_into_view_if_needed()
    shots.annotate(p, FIG / "admin-start.png", [
        {"selector": "#start-opening", "n": 1, "position": "right"},
    ], crop="main")
    btns = p.locator("main button[type=submit]")
    btns.last.click()
    p.wait_for_timeout(2500)
    dump("start-done")

def sec():
    shots.login(p, "secretaire")


def w_open():
    shots.goto(p, "/secretariat/retrait")
    connected()


def new_withdrawal(amount, category, mode, text):
    p.get_by_role("button", name="New Withdrawal").first.click()
    p.wait_for_timeout(1000)
    p.fill("#retrait-amount", str(amount))
    p.select_option("#retrait-category", label=category)
    p.select_option("#retrait-method", label=mode)
    p.fill("#retrait-justification", text)


if "w-list" in steps:
    sec(); w_open()
    dump("w-list")
    p.get_by_role("button", name="New Withdrawal").first.click()
    p.wait_for_timeout(1000)
    dump("w-form")

if "w-save" in steps:
    sec(); w_open()
    p.get_by_role("button", name="New Withdrawal").first.click()
    p.wait_for_timeout(1000)
    opts = p.locator("#retrait-method option").all_inner_texts()
    print("MODES", opts)
    p.fill("#retrait-amount", "3000")
    p.select_option("#retrait-category", label="Supplies") if False else None
    print("CATS", p.locator("#retrait-category option").all_inner_texts())
    p.select_option("#retrait-category", value="SUPPLIES")
    p.select_option("#retrait-method", label="Cash")
    p.fill("#retrait-justification", "Printer paper for the reception desk")
    shots.annotate(p, FIG / "withdrawal-form.png", [
        {"selector": "#retrait-amount", "n": 1, "position": "right"},
        {"selector": "#retrait-category", "n": 2, "position": "top"},
        {"selector": "#retrait-method", "n": 3, "position": "top"},
        {"selector": "#retrait-justification", "n": 4, "position": "right"},
        {"text": "Save Transaction", "exact": True, "n": 5, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(3000)
    dump("w-saved1")
    # second: mobile money
    new_withdrawal(5000, "Bills", "Orange Money", "Electricity bill paid from the mobile wallet") if False else None
    p.get_by_role("button", name="New Withdrawal").first.click()
    p.wait_for_timeout(1000)
    p.fill("#retrait-amount", "5000")
    p.select_option("#retrait-category", value="BILLS")
    p.select_option("#retrait-method", index=2)
    p.fill("#retrait-justification", "Electricity bill paid from the mobile wallet")
    p.get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(3000)
    # third: to be cancelled
    p.get_by_role("button", name="New Withdrawal").first.click()
    p.wait_for_timeout(1000)
    p.fill("#retrait-amount", "1500")
    p.select_option("#retrait-category", value="OTHER")
    p.select_option("#retrait-method", label="Cash")
    p.fill("#retrait-justification", "Taxi fare for a patient (entered twice)")
    p.get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(3000)
    dump("w-saved3")

if "w-cancel" in steps:
    sec(); w_open()
    ROW = "tr:has-text('Taxi fare') >> nth=0"
    shots.annotate(p, FIG / "withdrawal-list.png", [
        {"selector": "#retrait-search", "n": 1, "position": "right"},
        {"selector": "#retrait-status", "n": 2, "position": "top"},
        {"selector": "main table >> td >> nth=4", "n": 3, "position": "top", "outline": False},
        {"selector": ROW + " >> button", "n": 4, "position": "left"},
    ], crop={"x": 280, "y": 60, "width": 1320, "height": 520})
    p.locator(ROW + " >> button").click()
    p.wait_for_timeout(1000)
    p.fill("#cancel-justification", "Entered twice by mistake, the first entry stays")
    shots.annotate(p, FIG / "withdrawal-cancel.png", [
        {"selector": "#cancel-justification", "n": 5, "position": "right"},
        {"selector": "[role=dialog] button[type=submit]", "n": 6, "position": "left"},
    ], crop="[role=dialog]")
    dump("w-cancel-modal")
    p.locator("[role=dialog] button[type=submit]").click()
    p.wait_for_timeout(3000)
    p.select_option("#retrait-status", value="cancelled")
    p.wait_for_timeout(2000)
    shots.annotate(p, FIG / "withdrawal-cancelled.png", [
        {"selector": "main table >> td >> nth=5", "n": 1, "position": "bottom", "outline": False},
    ], crop={"x": 280, "y": 60, "width": 1320, "height": 520})
    dump("w-cancelled")

def dlg():
    return p.locator("[role=dialog]").first


def invoice(desc, price, method, advance):
    shots.goto(p, "/secretariat/caisse")
    connected()
    p.get_by_role("button", name="New Invoice").first.click()
    p.wait_for_timeout(1500)
    p.locator("#inv-patient-search").press_sequentially("Amara", delay=80)
    p.wait_for_timeout(2500)
    dlg().get_by_text("Amara Njoh").first.click()
    p.wait_for_timeout(800)
    dlg().get_by_role("button", name="Free-form Service").click()
    p.wait_for_timeout(800)
    free = dlg().locator("#line-1-qty").locator("xpath=ancestor::*[.//input[@type='text']][1]").locator("input[type=text]").first
    free.fill(desc)
    p.fill("#line-1-price", str(price))
    p.select_option("#inv-category", label="Consultation")
    p.select_option("#inv-method", label=method)
    p.fill("#inv-advance", str(advance))
    dlg().get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(4000)


if "sales" in steps:
    sec()
    invoice("Consultation fee", 10000, "Cash", 10000)
    invoice("Consultation fee", 8000, "Orange Money", 8000)
    invoice("Certificate (to be cancelled)", 4000, "Cash", 4000)
    dump("sales")

if "sale-cancel" in steps:
    sec()
    shots.goto(p, "/secretariat/caisse")
    connected()
    ROW = "tr:has-text('4 000 FCFA') >> nth=0"
    p.locator(ROW + " >> [title='Cancel']").click()
    p.wait_for_timeout(1000)
    dump("sale-cancel-modal")
    p.fill("#cancel-justification", "Certificate not issued, patient refunded in cash")
    shots.annotate(p, FIG / "sale-cancel.png", [
        {"selector": "#cancel-justification", "n": 1, "position": "right"},
        {"selector": "[role=dialog] button[type=submit]", "n": 2, "position": "left"},
    ], crop="[role=dialog]")
    p.locator("[role=dialog] button[type=submit]").click()
    p.wait_for_timeout(3000)
    dump("sale-cancelled")

def fill_count(cash, om, mtn, other):
    for code, v in (("especes", cash), ("orange_money", om), ("mtn_money", mtn), ("autre_mobile", other)):
        p.fill(f"#count-{code}", str(v))


if "closure" in steps:
    sec()
    shots.goto(p, "/secretariat/cloture")
    connected()
    print(p.locator("fieldset legend").all_inner_texts())
    dump("closure-empty")
    shots.annotate(p, FIG / "closure-form-empty.png", [
        {"text": "Last closing", "n": 1, "position": "right", "outline": False} if False else {"text": "Count", "exact": True, "n": 1, "position": "left", "outline": False},
        {"selector": "#count-especes", "n": 2, "position": "right"},
        {"selector": "#count-orange_money", "n": 3, "position": "right"},
    ])
    # wrong count: cash short by 2000 and no comment
    fill_count(55000, 3000, 0, 0)
    p.wait_for_timeout(500)
    dump("closure-filled")
    p.get_by_role("button", name="Validate the closing").click()
    p.wait_for_timeout(3000)
    dump("closure-gap-msg")
    shots.shot(p, FIG / "_gap-msg.png")

if "closure2" in steps:
    sec()
    shots.goto(p, "/secretariat/cloture")
    connected()
    fill_count(55000, 3000, 0, 0)
    shots.annotate(p, FIG / "closure-form.png", [
        {"text": "Cash counted", "n": 1, "position": "left", "outline": False},
        {"selector": "#count-especes", "n": 2, "position": "right"},
        {"selector": "#count-orange_money", "n": 3, "position": "right"},
        {"selector": "#count-mtn_money", "n": 4, "position": "right"},
        {"selector": "#comment-especes", "n": 5, "position": "left"},
        {"text": "Validate the closing", "exact": True, "n": 6, "position": "left"},
    ], crop="main")
    p.get_by_role("button", name="Validate the closing").click()
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "closure-gap.png", [
        {"selector": "#comment-especes", "n": 1, "position": "left"},
        {"text": "A difference was found on Cash", "n": 2, "position": "right", "outline": False},
    ], crop="main")
    p.fill("#comment-especes", "Two 1000 notes given as change to a patient, not recorded")
    p.wait_for_timeout(500)
    p.get_by_role("button", name="Validate the closing").click()
    p.wait_for_timeout(4000)
    dump("closure-result")
    shots.shot(p, FIG / "_result_raw.png")

if "closure3" in steps:
    # second closing of the day: one more withdrawal, cash counted 500 over
    sec(); w_open()
    new_withdrawal(1000, "Maintenance/Repairs", "Cash", "Door lock oil")
    p.get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(3000)
    shots.goto(p, "/secretariat/cloture")
    connected()
    fill_count(54500, 0, 0, 0)
    CROP = {"x": 300, "y": 40, "width": 1300, "height": 1100}
    shots.annotate(p, FIG / "closure-form.png", [
        {"selector": "#count-especes", "n": 1, "position": "left"},
        {"selector": "#comment-especes", "n": 2, "position": "top"},
        {"selector": "#count-orange_money", "n": 3, "position": "left"},
        {"selector": "#count-mtn_money", "n": 4, "position": "left"},
        {"text": "Validate the closing", "exact": True, "n": 5, "position": "left"},
    ], crop=CROP)
    p.get_by_role("button", name="Validate the closing").click()
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "closure-gap.png", [
        {"selector": "#comment-especes", "n": 1, "position": "top"},
        {"text": "A difference was found on Cash", "n": 2, "position": "left", "outline": False},
        {"text": "Validate the closing", "exact": True, "n": 3, "position": "left"},
    ], crop=CROP)
    p.fill("#comment-especes", "A 500 coin found in the drawer, source unknown")
    p.wait_for_timeout(500)
    p.get_by_role("button", name="Validate the closing").click()
    p.wait_for_timeout(4000)
    dump("closure3-result")
    shots.annotate(p, FIG / "closure-result.png", [
        {"text": "Closing saved", "n": 1, "position": "left", "outline": False},
        {"text": "Opening", "exact": True, "n": 2, "position": "top"},
        {"text": "Expected", "exact": True, "n": 3, "position": "top"},
        {"text": "Counted", "exact": True, "n": 4, "position": "top"},
        {"text": "Difference", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 300, "y": 40, "width": 1300, "height": 760})
    p.get_by_role("button", name="Request an adjustment").click()
    p.wait_for_timeout(600)
    p.select_option("#correction-mode", index=1)
    p.fill("#correction-amount", "-500")
    p.fill("#correction-reason", "The 500 coin belongs to the cafeteria float")
    shots.annotate(p, FIG / "correction-form.png", [
        {"selector": "#correction-mode", "n": 1, "position": "top"},
        {"selector": "#correction-amount", "n": 2, "position": "top"},
        {"selector": "#correction-reason", "n": 3, "position": "top"},
        {"text": "Send the request", "exact": True, "n": 4, "position": "left"},
    ], crop="#cash-correction-form")
    p.get_by_role("button", name="Send the request").click()
    p.wait_for_timeout(3000)
    dump("correction-sent")

if "approve" in steps:
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/cash-closures")
    connected()
    dump("approve-before")
    p.get_by_role("button", name="Approve").first.click()
    p.wait_for_timeout(2500)
    dump("approve-after")

if "closure4" in steps:
    sec()
    shots.goto(p, "/secretariat/cloture")
    connected()
    fill_count(54000, 0, 0, 0)
    p.get_by_role("button", name="Validate the closing").click()
    p.wait_for_timeout(4000)
    dump("closure4-result")
    shots.annotate(p, FIG / "closure-adjusted.png", [
        {"text": "Adjustments applied to this period", "n": 1, "position": "left", "outline": False},
        {"text": "Done", "exact": True, "n": 2, "position": "top"},
    ], crop={"x": 300, "y": 40, "width": 1300, "height": 1100})

if "offline" in steps:
    shots.close(pw, browser)
    PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-s2"
    pw, ctx, p = shots.launch(width=1600, height=1500, profile_dir=PROFILE)
    sec()
    shots.goto(p, "/secretariat/cloture")
    connected()
    p.wait_for_timeout(6000)
    shots.close(pw, ctx)
    pw, ctx, p = shots.launch(width=1600, height=1500, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/secretariat/cloture")
    p.get_by_text("Offline").first.wait_for(timeout=60000)
    p.wait_for_timeout(4000)
    dump("closure-offline")
    shots.annotate(p, FIG / "closure-offline.png", [
        {"text": "Offline", "n": 1, "position": "bottom"},
        {"text": "Unable to load the closing status", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 300, "y": 0, "width": 1300, "height": 380})
    browser = ctx

shots.close(pw, browser)
