"""Capture script for guide secretary-1. Run from the repo root:
    python docs/user-guides/src/secretary-1/capture.py [step ...]
Steps (each one performs real actions in the dev database, so run them once):
    signin home patient duplicate search invoice installment discount history offline
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin", "home", "patient", "search", "invoice"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile"
# 1600 px wide: at 1440 the cash desk table overflows and the page scrolls sideways.
ONLINE_STEPS = [x for x in steps if x != "offline"]
pw, browser, p = shots.launch(width=1600)


def dialog():
    return p.locator("[role=dialog]").first


if "signin" in steps:
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("secretaire")
    p.fill("#username", acc["username"])
    p.fill("#password", "demo-password")
    shots.annotate(p, FIG / "signin.png", [
        {"selector": "#username", "n": 1},
        {"selector": "#password", "n": 2},
        {"selector": "button[type=submit]", "n": 3},
    ], crop="form")

shots.login(p, "secretaire")

if "home" in steps:
    shots.goto(p, "/secretariat/")
    shots.annotate(p, FIG / "home.png", [
        {"text": "Daily work", "n": 1, "position": "right", "outline": False},
        {"text": "Connected", "n": 2, "position": "bottom"},
        {"text": "EN", "exact": True, "n": 3, "position": "bottom"},
        {"text": "Quick actions", "n": 4, "position": "left"},
        {"text": "Money for the period", "n": 5, "position": "left"},
    ])

if "patient" in steps:
    shots.goto(p, "/secretariat/patients")
    p.get_by_text("Ajouter un patient").click()
    p.wait_for_timeout(1000)
    p.fill("#patient-first-name", "Amara")
    p.fill("#patient-last-name", "Njoh")
    p.fill("#patient-birth-date", "1991-03-14")
    p.select_option("#patient-gender", index=2)
    p.fill("#patient-national-id", "DEMO-CNI-000123")
    p.fill("#patient-phone", "+237677000123")
    p.fill("#patient-residence", "Yaounde, Bastos")
    shots.annotate(p, FIG / "patient-form.png", [
        {"selector": "#patient-first-name", "n": 1},
        {"selector": "#patient-birth-date", "n": 2},
        {"selector": "#patient-national-id", "n": 3},
        {"selector": "#patient-phone", "n": 4},
        {"text": "Créer", "exact": True, "n": 5},
    ], crop="[role=dialog]")
    dialog().get_by_text("Créer", exact=True).click()
    p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "patient-code.png", [
        {"text": "Patient code", "n": 6, "position": "left", "outline": False},
        {"text": "Copy", "exact": True, "n": 7, "position": "left"},
        {"text": "OK", "exact": True, "n": 8, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_text("OK", exact=True).click()

if "duplicate" in steps:
    shots.goto(p, "/secretariat/patients")
    p.get_by_text("Ajouter un patient").click()
    p.wait_for_timeout(1000)
    p.fill("#patient-first-name", "Bella")
    p.fill("#patient-last-name", "Njoh")
    p.fill("#patient-birth-date", "1994-07-02")
    p.fill("#patient-national-id", "DEMO-CNI-000123")
    dialog().get_by_text("Créer", exact=True).click()
    p.wait_for_timeout(8000)
    shots.shot(p, FIG / "_dup.png")
    (HERE / "_dup.txt").write_text(p.inner_text("body"), encoding="utf-8")

if "search" in steps:
    shots.goto(p, "/secretariat/patients")
    p.locator("input[placeholder^='Search by name']").press_sequentially("Njoh", delay=80)
    p.keyboard.press("Enter")
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "patient-search.png", [
        {"selector": "input[placeholder^='Search by name']", "n": 1, "position": "right"},
        {"text": "All Patients", "n": 2, "position": "bottom"},
        {"text": "Modifier", "exact": True, "n": 3, "position": "left"},
    ], crop={"x": 280, "y": 80, "width": 1310, "height": 420})

def new_invoice(name="Amara"):
    shots.goto(p, "/secretariat/caisse")
    p.get_by_role("button", name="New Invoice").first.click()
    p.wait_for_timeout(1500)
    p.locator("#inv-patient-search").press_sequentially(name, delay=80)
    p.wait_for_timeout(2500)


def dump(tag):
    (HERE / f"_{tag}.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.shot(p, FIG / f"_{tag}.png")


if "invoicefig" in steps:
    new_invoice()
    shots.annotate(p, FIG / "invoice-patient.png", [
        {"selector": "#inv-patient-search", "n": 1},
        {"selector": "#inv-patient-label", "n": 2, "position": "right"},
    ], crop={"x": 140, "y": 30, "width": 1120, "height": 330})
    p.keyboard.press("Escape")

if "invoice" in steps:
    new_invoice()
    dialog().get_by_text("Amara Njoh").first.click()
    p.wait_for_timeout(800)
    dialog().get_by_role("button", name="Lab Exam").click()
    p.wait_for_timeout(800)
    lab = dialog().locator("input[placeholder^='Search a lab exam']")
    lab.press_sequentially("Acide", delay=80)
    p.wait_for_timeout(1200)
    dialog().get_by_text("Acide urique").first.click()
    p.wait_for_timeout(800)
    dialog().get_by_role("button", name="Free-form Service").click()
    p.wait_for_timeout(800)
    free = dialog().locator("#line-2-qty").locator("xpath=ancestor::*[.//input[@type='text']][1]").locator("input[type=text]").first
    free.fill("Medical certificate")
    p.fill("#line-2-price", "2000")
    p.wait_for_timeout(600)
    p.locator("#line-1-price").scroll_into_view_if_needed()
    shots.annotate(p, FIG / "invoice-lines.png", [
        {"selector": "[role=dialog] button:has-text('Pharmacy')", "n": 3, "position": "left"},
        {"selector": "#line-1-price", "n": 4},
        {"selector": "#line-2-price", "n": 5, "position": "bottom"},
        {"text": "Invoice total", "n": 6, "position": "left", "outline": False},
    ])
    dump("lines")
    p.select_option("#inv-category", label="Laboratory")
    p.select_option("#inv-method", label="Cash")
    p.fill("#inv-advance", "10000")
    p.fill("#inv-note", "Uric acid test and certificate")
    p.locator("#inv-note").scroll_into_view_if_needed()
    shots.annotate(p, FIG / "invoice-payment.png", [
        {"selector": "#inv-category", "n": 7},
        {"selector": "#inv-method", "n": 8, "position": "top"},
        {"selector": "#inv-advance", "n": 9, "position": "top"},
        {"text": "Save Transaction", "n": 10, "position": "top"},
    ])
    dialog().get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(4000)
    dump("saved")

ROW = "tr:has-text('Amara Njoh') >> nth=0"

if "installment" in steps:
    shots.goto(p, "/secretariat/caisse")
    shots.annotate(p, FIG / "cash-list.png", [
        {"selector": ROW + " >> [title='Add Payment']", "n": 1, "position": "top"},
        {"selector": ROW + " >> [title='Settle']", "n": 2, "position": "bottom"},
        {"selector": ROW + " >> [title='Reprint ticket']", "n": 3, "position": "top"},
        {"selector": ROW + " >> td >> nth=5", "n": 4, "position": "bottom", "outline": True},
    ], crop="main")
    p.locator(ROW + " >> [title='Add Payment']").click()
    p.wait_for_timeout(1200)
    p.fill("#installment-amount", "5000")
    shots.annotate(p, FIG / "installment.png", [
        {"text": "Balance Due :", "n": 5, "position": "left", "outline": False},
        {"selector": "#installment-amount", "n": 6},
        {"selector": "#installment-method", "n": 7},
        {"text": "Save Transaction", "exact": True, "n": 8, "position": "left"},
    ], crop={"x": 350, "y": 250, "width": 900, "height": 400})
    dump("installment-form")
    p.get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(3000)
    dump("installment-saved")

if "discount" in steps:
    new_invoice()
    dialog().get_by_text("Amara Njoh").first.click()
    p.wait_for_timeout(800)
    dialog().get_by_role("button", name="Lab Exam").click()
    p.wait_for_timeout(800)
    dialog().locator("input[placeholder^='Search a lab exam']").press_sequentially("ALAT", delay=80)
    p.wait_for_timeout(1200)
    dialog().get_by_text("ALAT").first.click()
    p.select_option("#inv-category", label="Laboratory")
    p.fill("#inv-note", "Patient asks for a reduced price")
    p.select_option("#inv-manager", label="Demo Promoter")
    p.locator("#inv-manager").scroll_into_view_if_needed()
    shots.annotate(p, FIG / "discount-request.png", [
        {"selector": "#inv-advance", "n": 1, "position": "top"},
        {"selector": "#inv-manager", "n": 2},
        {"text": "Request a discount", "exact": True, "n": 3, "position": "top"},
    ])
    dialog().get_by_role("button", name="Request a discount").click()
    p.wait_for_timeout(3000)
    dump("discount-sent")
    shots.goto(p, "/secretariat/caisse")
    p.select_option("select >> nth=0", label="Awaiting approval")
    p.wait_for_timeout(2000)
    dump("awaiting")

if "history" in steps:
    shots.goto(p, "/secretariat/discount-history")
    dump("history")

shots.close(pw, browser)


if "offline" in steps:
    # 1. sign in online with a persistent profile, so the app and its local data are cached
    pw, ctx, p = shots.launch(width=1600, profile_dir=PROFILE)
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/patients")
    p.wait_for_timeout(8000)
    shots.close(pw, ctx)
    # 2. same profile, network cut
    pw, ctx, p = shots.launch(width=1600, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/secretariat/patients")
    p.get_by_text("Offline").first.wait_for(timeout=60000)
    shots.wait_ready(p)
    p.get_by_text("Ajouter un patient").click()
    p.wait_for_timeout(1000)
    p.fill("#patient-first-name", "Yaw")
    p.fill("#patient-last-name", "Mensah")
    p.fill("#patient-birth-date", "1985-11-20")
    p.locator("[role=dialog]").first.get_by_text("Créer", exact=True).click()
    p.wait_for_timeout(2500)
    shots.shot(p, FIG / "_offline-raw.png")
    (HERE / "_offline.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.annotate(p, FIG / "offline-code.png", [
        {"selector": "text=/Offline|Sending error/ >> visible=true", "n": 1, "position": "bottom"},
        {"text": "Assigning the code", "n": 2, "position": "left", "outline": False},
    ])
    shots.close(pw, ctx)
    # 3. network back: the patient is sent and receives its code
    pw, ctx, p = shots.launch(width=1600, profile_dir=PROFILE)
    shots.goto(p, "/secretariat/patients")
    p.get_by_text("Connected").first.wait_for(timeout=60000)
    p.wait_for_timeout(8000)
    p.locator("#patient-search").fill("Mensah")
    p.keyboard.press("Enter")
    p.wait_for_timeout(3000)
    (HERE / "_back-online.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.annotate(p, FIG / "online.png", [
        {"selector": "text=Connected >> visible=true", "n": 1, "position": "bottom"},
    ], crop={"x": 300, "y": 0, "width": 1300, "height": 80})
    shots.close(pw, ctx)
