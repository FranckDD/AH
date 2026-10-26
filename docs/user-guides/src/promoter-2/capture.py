"""Capture script for guide promoter-2. Run from the repo root:
    python docs/user-guides/src/promoter-2/capture.py [step ...]
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


if "look" in steps:
    shots.login(p, "promoteur")
    settle(4000)
    dump("home", True)
    print(p.evaluate("[...document.querySelectorAll('nav a, aside a, nav button, aside button')].map(e=>e.innerText.trim().replace(/\n/g,' ')+' | '+(e.getAttribute('href')||''))"))


def dialog():
    return p.locator("[role=dialog]").first


def new_invoice(name="Amara"):
    shots.goto(p, "/secretariat/caisse")
    p.get_by_role("button", name="New Invoice").first.click()
    settle(1500)
    p.locator("#inv-patient-search").press_sequentially(name, delay=80)
    settle(2500)


def send_discount(exam, note, manager):
    new_invoice()
    dialog().get_by_text("Amara Njoh").first.click()
    settle(800)
    dialog().get_by_role("button", name="Lab Exam").click()
    settle(800)
    dialog().locator("input[placeholder^='Search a lab exam']").press_sequentially(exam, delay=80)
    settle(1200)
    dialog().get_by_text(exam).first.click()
    p.select_option("#inv-category", label="Laboratory")
    p.fill("#inv-note", note)
    p.select_option("#inv-manager", label=manager)
    dialog().get_by_role("button", name="Request a discount").click()
    settle(3000)


def fill_count(cash, om, mtn, other):
    for code, v in (("especes", cash), ("orange_money", om), ("mtn_money", mtn), ("autre_mobile", other)):
        p.fill(f"#count-{code}", str(v))


def send_correction(mode_index, amount, reason):
    p.get_by_role("button", name="Request an adjustment").click()
    settle(600)
    p.select_option("#correction-mode", index=mode_index)
    p.fill("#correction-amount", amount)
    p.fill("#correction-reason", reason)
    p.get_by_role("button", name="Send the request").click()
    settle(3000)


if "disc-send" in steps:
    shots.login(p, "secretaire")
    send_discount("ALAT", "Guide demo P2: approve at 50 percent", "Demo Promoter")
    dump("disc-sent1")
    send_discount("ALAT", "Guide demo P2: refuse", "Demo Promoter")
    send_discount("ALAT", "Guide demo P2: deadline only", "Demo Promoter")
    send_discount("ALAT", "Guide demo P2: sent to the admin", "Demo Administrator")
    shots.goto(p, "/secretariat/caisse")
    dump("disc-sec-list")

if "cc-close" in steps:
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/cloture")
    p.get_by_text("Connected").first.wait_for(timeout=30000)
    settle(800)
    dump("cc-form", True)
    fill_count(53000, 0, 0, 0)
    p.get_by_role("button", name="Validate the closing").click()
    settle(3000)
    p.fill("#comment-especes", "Guide demo P2: change not written down")
    p.get_by_role("button", name="Validate the closing").click()
    settle(4000)
    dump("cc-result", True)
    send_correction(1, "-1500", "Guide demo P2: change given on a 50 000 note, not recorded")
    dump("cc-sent1")
    send_correction(1, "2000", "Guide demo P2: second request, to be rejected")
    dump("cc-sent2")

def clear_toast2():
    clear_toast()

if "disc-decide" in steps:
    shots.login(p, "promoteur")
    PW = shots.account("promoteur")["password"]
    shots.goto(p, "/dashboard/discount-review")
    settle(3000)
    clear_toast()
    dump("dr-list", True)
    ids = p.eval_on_selector_all("input[id^='review-password-']", "els => els.map(e => e.id.replace('review-password-',''))")
    print("IDS", ids)
    card = lambda i: p.locator(f"xpath=//input[@id='review-password-{i}']/ancestor::*[contains(@class,'rounded-card')][1]")
    first, a, b, c = ids[0], ids[1], ids[2], ids[3]
    # request a: wrong password then right one, 50 percent
    card(a).get_by_role("button", name="50%").click()
    p.fill(f"#review-password-{a}", "wrong-password")
    card(a).get_by_role("button", name="Approve").click()
    settle(1500)
    dump("dr-wrongpw")
    p.fill(f"#review-password-{a}", PW)
    card(a).scroll_into_view_if_needed()
    B = lambda n: f"xpath=//input[@id='review-password-{a}']/ancestor::*[contains(@class,'rounded-card')][1]//button[normalize-space()='{n}']"
    shots.annotate(p, FIG / "discount-card.png", [
        {"selector": B("50%"), "n": 1, "position": "top"},
        {"selector": f"#review-deadline-{a}", "n": 2, "position": "right"},
        {"selector": f"#review-password-{a}", "n": 3, "position": "right"},
        {"selector": B("Approve"), "n": 4, "position": "bottom"},
        {"selector": B("Refuse"), "n": 5, "position": "bottom"},
    ], crop=f"xpath=//input[@id='review-password-{a}']/ancestor::*[contains(@class,'rounded-card')][1]")
    card(a).get_by_role("button", name="Approve").click()
    settle(2500)
    # request b: approve with nothing, then refuse
    p.fill(f"#review-password-{b}", PW)
    card(b).get_by_role("button", name="Approve").click()
    settle(1500)
    dump("dr-nothing")
    card(b).get_by_role("button", name="Refuse").click()
    settle(2500)
    # request c: deadline only
    p.fill(f"#review-deadline-{c}", "2026-11-20")
    p.fill(f"#review-password-{c}", PW)
    card(c).get_by_role("button", name="Approve").click()
    settle(2500)
    dump("dr-after", True)
    # old request: refuse with a percentage selected (should be rejected)
    card(first).get_by_role("button", name="10%").click()
    p.fill(f"#review-password-{first}", PW)
    card(first).get_by_role("button", name="Refuse").click()
    settle(1500)
    dump("dr-refuse-pct")

if "disc-history" in steps:
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/discount-history")
    settle(3000)
    clear_toast()
    dump("dh", True)
    shots.annotate(p, FIG / "discount-history.png", [
        {"text": "Approved", "exact": True, "n": 1, "position": "top", "index": 0, "outline": False},
        {"text": "This month", "exact": True, "n": 2, "position": "top"},
        {"selector": "#dh-status", "n": 3, "position": "top"},
        {"text": "Reduced amount", "exact": True, "n": 4, "position": "top", "outline": False},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 700})

if "cc-look" in steps:
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/cash-closures")
    settle(3500)
    clear_toast()
    dump("cc-page", True)

if "cc-do" in steps:
    p.set_viewport_size({"width": 1600, "height": 1500})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/cash-closures")
    settle(3500)
    clear_toast()
    dump("cc-page", True)
    LI1 = "xpath=//li[contains(.,'change given on a 50')]"
    LI2 = "xpath=//li[contains(.,'second request')]"
    shots.annotate(p, FIG / "closures-top.png", [
        {"text": "Pending corrections", "exact": True, "n": 1, "position": "right", "outline": False},
        {"selector": LI1 + "//button[normalize-space()='Approve']", "n": 2, "position": "top"},
        {"selector": LI1 + "//button[normalize-space()='Reject']", "n": 3, "position": "top"},
        {"selector": "#ccr-kind", "n": 4, "position": "top"},
        {"selector": "#ccr-gap", "n": 5, "position": "right"},
        {"text": "View detail", "exact": True, "n": 6, "position": "left", "index": 0},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 860})
    p.locator(LI1 + "//button[normalize-space()='Approve']").click()
    settle(2500)
    dump("cc-approved")
    p.locator(LI2 + "//button[normalize-space()='Reject']").click()
    settle(2500)
    dump("cc-rejected", True)
    p.get_by_role("button", name="View detail").first.click()
    settle(1500)
    dump("cc-detail", True)

if "bell" in steps:
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/overview")
    settle(5000)
    clear_toast()
    p.locator("button[title='Notifications']").click()
    settle(1200)
    dump("bell")
    items = p.locator("div.absolute.right-0.mt-2 div.cursor-pointer")
    n = items.count()
    texts = [t.replace(chr(10), " / ") for t in items.all_inner_texts()]
    for k, t in enumerate(texts): print(k, t)
    seen = set()
    for k, t in enumerate(texts):
        key = t.split(":")[0][:25]
        if key in seen: continue
        seen.add(key)
        shots.goto(p, "/dashboard/overview"); settle(3000); clear_toast()
        p.locator("button[title='Notifications']").click(); settle(800)
        p.locator("div.absolute.right-0.mt-2 div.cursor-pointer").nth(k).click(); settle(2500)
        print("CLICK", k, t[:50], "->", p.url)

if "bell2" in steps:
    shots.login(p, "promoteur")
    for needle in ("Daily check of", "expires in"):
        shots.goto(p, "/dashboard/overview"); settle(3000); clear_toast()
        p.locator("button[title='Notifications']").click(); settle(800)
        p.locator("div.absolute.right-0.mt-2 div.cursor-pointer", has_text=needle).first.click(); settle(3000)
        print("CLICK", needle, "->", p.url)

if "staff" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/reductions-personnel")
    settle(3000)
    clear_toast()
    for cat in ("Medications", "Exams", "Consultations", "Booklets", "Other care"):
        r = p.locator(f"tr:has-text('{cat}')")
        print(cat, r.locator("input[type=number]").evaluate_all("els=>els.map(e=>e.value)"), r.locator("input[type=checkbox]").is_checked())
    EX = "tr:has-text('Exams')"
    orig = p.locator(EX + " input[type=number] >> nth=1").input_value()
    p.locator(EX + " input[type=number] >> nth=1").fill("0")
    p.locator(EX + " button:has-text('Save')").click()
    settle(1200)
    dump("staff-err")
    p.locator(EX + " input[type=number] >> nth=1").fill("12")
    p.locator(EX + " button:has-text('Save')").click()
    settle(1500)
    dump("staff-saved")
    p.locator(EX + " input[type=number] >> nth=1").fill(orig)
    p.locator(EX + " button:has-text('Save')").click()
    settle(1500)
    dump("staff-restored")
    p.fill("#staff-search", "Amara")
    settle(2000)
    shots.annotate(p, FIG / "staff-rules.png", [
        {"selector": "tr:has-text('Medications') input[type=number] >> nth=0", "n": 1, "position": "top"},
        {"selector": "tr:has-text('Medications') input[type=number] >> nth=1", "n": 2, "position": "top"},
        {"selector": "tr:has-text('Medications') input[type=checkbox]", "n": 3, "position": "top"},
        {"selector": "tr:has-text('Medications') button:has-text('Save')", "n": 4, "position": "right"},
        {"selector": "#staff-search", "n": 5, "position": "top"},
        {"selector": "tr:has-text('Amara Njoh') button >> nth=0", "n": 6, "position": "left"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 900})
    p.locator("tr:has-text('Amara Njoh') button >> nth=0").click()
    settle(2500)
    dump("staff-marked", True)
    p.locator("tr:has-text('Amara Njoh') button >> nth=0").click()
    settle(2500)
    dump("staff-unmarked", True)

if "lab-look" in steps:
    shots.login(p, "laborantin")
    shots.goto(p, "/dashboard/lab-stock-products"); settle(3500); clear_toast()
    dump("lab-products-labo", True)
    print(p.locator("button").all_inner_texts())

if "lab-signal" in steps:
    shots.login(p, "laborantin")
    shots.goto(p, "/dashboard/lab-stock-products"); settle(3500); clear_toast()
    p.locator("tr:has-text('produis test') button:has-text('Report')").first.click(); settle(1000)
    dump("lab-signal-panel")
    btns = p.locator("[role=group] button")
    print(btns.all_inner_texts())
    btns.first.click(); settle(2500)
    dump("lab-signal-done", True)

if "lab-order" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/lab-stock-requests"); settle(3500); clear_toast()
    dump("lab-req", True)

if "lab-order2" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/lab-stock-requests"); settle(3500); clear_toast()
    p.get_by_role("button", name="Mark as ordered").click(); settle(1000)
    p.fill("#lab-order-date", "2026-10-20"); 
    p.locator("button[type=submit]").last.click(); settle(1500)
    dump("lab-order-past")
    p.fill("#lab-order-date", "2026-10-30")
    shots.annotate(p, FIG / "lab-order.png", [
        {"selector": "#lab-order-date", "n": 1, "position": "top"},
        {"selector": "[role=dialog] button[type=submit], button[form=lab-order-form]", "n": 2, "position": "top"},
    ], crop="[role=dialog]")
    p.locator("button[form=lab-order-form]").click(); settle(2500)
    dump("lab-ordered", True)
    shots.goto(p, "/dashboard/lab-stock-receipts/new"); settle(3000)
    dump("lab-receipt-form", True)
    print(p.evaluate("[...document.querySelectorAll('input,select,button')].map(e=>e.tagName+'#'+e.id+':'+(e.innerText||e.placeholder||'').slice(0,30))"))

if "lab-rcpt" in steps:
    p.set_viewport_size({"width": 1600, "height": 1200})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/lab-stock-receipts/new"); settle(3000); clear_toast()
    p.fill("#lab-invoice-number", "GD-P2-0001")
    p.fill("#lab-invoice-supplier", "ets Test")
    p.get_by_role("button", name="Add a product").click(); settle(1200)
    dump("lab-picker")
    p.fill("#lab-picker-search", "produis"); settle(1200)
    dump("lab-picker2")
    p.locator("[role=dialog] >> text=produis test").first.click(); settle(1500)
    dump("lab-line", True)
    print(p.evaluate("[...document.querySelectorAll('input,select,button')].map(e=>e.tagName+'#'+e.id+':'+e.type+':'+(e.innerText||e.placeholder||'').slice(0,25))"))

if "lab-rcpt2" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/lab-stock-receipts/new"); settle(3000); clear_toast()
    p.fill("#lab-invoice-number", "GD-P2-0001")
    p.fill("#lab-invoice-supplier", "ets Test")
    p.get_by_role("button", name="Add a product").click(); settle(1200)
    p.fill("#lab-picker-search", "produis"); settle(1200)
    p.locator("[role=dialog] >> text=produis test").first.click(); settle(1500)
    row = p.locator("tr:has-text('produis test'):visible, li:has-text('produis test'):visible").first
    vis = lambda sel: row.locator(sel + ":visible")
    vis("input[type=number]").nth(0).fill("50")
    vis("input[type=number]").nth(1).fill("50")
    vis("input[type=text]").first.fill("P2-LOT-1")
    vis("input[type=date]").first.fill("2027-06-30")
    vis("input[type=number]").nth(2).fill("1000")
    vis("input[type=checkbox]").first.check()
    settle(500)
    shots.annotate(p, FIG / "lab-receipt.png", [
        {"selector": "#lab-invoice-number", "n": 1, "position": "top"},
        {"selector": "#lab-invoice-supplier", "n": 2, "position": "top"},
        {"text": "Add a product", "exact": True, "n": 3, "position": "left"},
        {"selector": "input[type=checkbox]:visible >> nth=0", "n": 4, "position": "top"},
        {"text": "Confirm receipt", "exact": True, "n": 5, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 720})
    p.get_by_role("button", name="Confirm receipt").click(); settle(3500)
    dump("lab-rcpt-done", True)
    shots.goto(p, "/dashboard/lab-stock-requests"); settle(3000)
    p.select_option("select", label="All"); settle(2000)
    dump("lab-req-after", True)

if "tox-look" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/toxico"); settle(3500); clear_toast()
    dump("tox-list", True)
    print(p.locator("button:visible").all_inner_texts())
    p.get_by_role("button", name="Discharge").first.click(); settle(1500)
    dump("tox-discharge")

if "tox-file" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/toxico"); settle(3500); clear_toast()
    p.get_by_role("button", name="File").first.click(); settle(2500)
    dump("tox-file")
    print(p.locator("[role=dialog] button:visible").all_inner_texts())
    p.keyboard.press("Escape"); settle(500)
    shots.annotate(p, FIG / "toxico-list.png", [
        {"selector": "button:has-text('Details') >> nth=0", "n": 1, "position": "top"},
        {"selector": "button:has-text('File') >> nth=0", "n": 2, "position": "top"},
        {"selector": "button:has-text('Discharge') >> nth=0", "n": 3, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 760})

if "profile" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.login(p, "promoteur")
    PW = shots.account("promoteur")["password"]
    shots.goto(p, "/dashboard/overview"); settle(3000); clear_toast()
    p.click("[aria-label='My Account']"); settle(1500)
    dump("profile")
    M = "[class*='max-w-md']"
    shots.annotate(p, FIG / "account-profile.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Password", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": M + " input[type=tel]", "n": 3, "position": "right"},
        {"selector": M + " button[type=submit]", "n": 4, "position": "left"},
    ], crop=M)
    p.get_by_text("Password", exact=True).first.click(); settle(800)
    inputs = p.locator(M + " input[type=password]")
    inputs.nth(0).fill("wrong-old-password"); inputs.nth(1).fill("Demo-Pass-2030"); inputs.nth(2).fill("Demo-Pass-2030")
    p.locator(M + " button[type=submit]").click(); settle(2000)
    shots.annotate(p, FIG / "account-password.png", [
        {"selector": M + " input[type=password] >> nth=0", "n": 1, "position": "right"},
        {"selector": M + " input[type=password] >> nth=1", "n": 2, "position": "right"},
        {"selector": M + " input[type=password] >> nth=2", "n": 3, "position": "right"},
        {"selector": M + " button[type=submit]", "n": 4, "position": "left"},
    ], crop=M)
    dump("pw-wrong")
    inputs.nth(0).fill(PW); inputs.nth(1).fill("short"); inputs.nth(2).fill("short")
    p.locator(M + " button[type=submit]").click(); settle(1500); dump("pw-short")
    inputs.nth(0).fill(PW); inputs.nth(1).fill("Demo-Pass-2030"); inputs.nth(2).fill("Demo-Pass-2031")
    p.locator(M + " button[type=submit]").click(); settle(1500); dump("pw-mismatch")
    inputs.nth(1).fill("Demo-Pass-2030"); inputs.nth(2).fill("Demo-Pass-2030")
    p.locator(M + " button[type=submit]").click(); settle(4000)
    dump("pw-changed"); print("URL after change", p.url)

if "pw-revert" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    PW = shots.account("promoteur")["password"]
    p.goto(shots.BASE_URL + "/login"); settle(1500)
    p.fill("#username", "doc_promoteur"); p.fill("#password", "Demo-Pass-2030")
    p.click("button[type=submit]"); p.wait_for_url(lambda u: "/login" not in u, timeout=20000); shots.wait_ready(p)
    clear_toast()
    p.click("[aria-label='My Account']"); settle(1500)
    M = "[class*='max-w-md']"
    p.get_by_text("Password", exact=True).first.click(); settle(800)
    inputs = p.locator(M + " input[type=password]")
    inputs.nth(0).fill("Demo-Pass-2030"); inputs.nth(1).fill("short"); inputs.nth(2).fill("short")
    p.locator(M + " button[type=submit]").click(); settle(1500); dump("pw-short2")
    inputs.nth(1).fill(PW); inputs.nth(2).fill(PW)
    p.locator(M + " button[type=submit]").click(); settle(4000)
    dump("pw-reverted"); print("URL after revert", p.url)

if "fab-look" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.login(p, "production")
    shots.goto(p, "/dashboard/fabrication-intrants"); settle(3500); clear_toast()
    dump("fab-int", True)
    print(p.locator("button:visible").all_inner_texts())
    shots.goto(p, "/dashboard/fabrication-lots"); settle(3000)
    dump("fab-lots", True)
    print(p.locator("button:visible").all_inner_texts())

if "fab-buy" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "production")
    shots.goto(p, "/dashboard/fabrication-intrants"); settle(3500); clear_toast()
    p.get_by_role("button", name="New purchase").click(); settle(1200)
    dump("fab-buy-form")
    print(p.evaluate("[...document.querySelectorAll('[role=dialog] input,[role=dialog] select,[role=dialog] button,[role=dialog] textarea')].map(e=>e.tagName+'#'+e.id+':'+e.type+':'+(e.innerText||'').slice(0,25))"))
    shots.goto(p, "/dashboard/fabrication-lots"); settle(3000)
    p.get_by_role("button", name="New batch").click(); settle(1200)
    dump("fab-batch-form")
    print(p.evaluate("[...document.querySelectorAll('[role=dialog] input,[role=dialog] select,[role=dialog] button,[role=dialog] textarea')].map(e=>e.tagName+'#'+e.id+':'+e.type+':'+(e.innerText||'').slice(0,25))"))

if "fab-buy2" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "production")
    shots.goto(p, "/dashboard/fabrication-intrants"); settle(3500); clear_toast()
    p.get_by_role("button", name="New purchase").click(); settle(1200)
    p.get_by_text("New input", exact=True).click(); settle(800)
    dump("fab-buy-new")
    print(p.evaluate("[...document.querySelectorAll('[role=dialog] input,[role=dialog] select')].map(e=>e.tagName+'#'+e.id+':'+e.type)"))

if "fab-make" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "production")
    shots.goto(p, "/dashboard/fabrication-intrants"); settle(3500); clear_toast()
    p.get_by_role("button", name="New purchase").click(); settle(1200)
    p.get_by_text("New input", exact=True).click(); settle(800)
    p.fill("#fab-intrant-name", "Guide demo honey jars"); p.fill("#fab-intrant-unit", "jar")
    p.fill("#fab-purchase-supplier", "Demo supplier"); p.fill("#fab-purchase-ref", "GD-P2-BUY-1")
    p.fill("#fab-purchase-date", "2026-10-26"); p.fill("#fab-purchase-qty", "200"); p.fill("#fab-purchase-cost", "150")
    p.locator("[role=dialog] button[type=submit]").click(); settle(3000)
    dump("fab-bought", True)
    shots.goto(p, "/dashboard/fabrication-lots"); settle(3000)
    p.get_by_role("button", name="New batch").click(); settle(1200)
    p.select_option("#fab-batch-product", index=1)
    p.fill("#fab-batch-date", "2026-10-26"); p.fill("#fab-batch-producer", "Demo producer")
    p.locator("[role=dialog] button[type=submit]").click(); settle(3000)
    dump("fab-batch-made", True)
    print(p.url)

if "figs" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/overview"); settle(5000); clear_toast()
    shots.annotate(p, FIG / "home.png", [
        {"text": "Pending discount requests", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Cash closings", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "Staff discounts", "exact": True, "n": 3, "position": "right", "outline": False},
        {"text": "Stock count", "exact": True, "n": 4, "position": "right", "outline": False},
        {"text": "Lab stock", "exact": True, "n": 5, "position": "right", "outline": False},
        {"text": "Production", "exact": True, "n": 6, "position": "right", "outline": False},
        {"selector": "button[title='Notifications']", "n": 7, "position": "bottom"},
        {"selector": "[aria-label='My Account']", "n": 8, "position": "bottom"},
    ], crop={"x": 0, "y": 0, "width": 1600, "height": 560})
    p.locator("button[title='Notifications']").click(); settle(1200)
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "top"},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=0", "n": 2, "position": "left", "outline": False},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=1", "n": 3, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 560})
    p.keyboard.press("Escape")
    shots.goto(p, "/dashboard/fabrication-suivi"); settle(3500); clear_toast()
    dump("fab-suivi", True)
    shots.annotate(p, FIG / "production-tracking.png", [
        {"text": "Production", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Anomalies", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Recent batches", "exact": True, "n": 3, "position": "top", "outline": False},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 760})

if "figs2" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/lab-stock-alerts"); settle(3000); clear_toast()
    shots.annotate(p, FIG / "lab-alerts.png", [
        {"text": "Weekly count", "n": 1, "position": "top", "outline": False},
        {"text": "No product below its threshold.", "n": 2, "position": "top", "outline": False},
        {"text": "Upcoming expiries", "n": 3, "position": "top", "outline": False},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 560})

if "figs3" in steps:
    p.set_viewport_size({"width": 1600, "height": 1100})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/fabrication-suivi"); settle(3500); clear_toast()
    shots.annotate(p, FIG / "production-tracking.png", [
        {"text": "Draft", "exact": True, "n": 1, "position": "top", "index": 0, "outline": False},
        {"text": "Anomalies", "exact": True, "n": 2, "position": "top", "index": 0},
        {"text": "Recent batches", "exact": True, "n": 3, "position": "top", "outline": False},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 760})
    shots.goto(p, "/dashboard/toxico"); settle(3500); clear_toast()
    shots.annotate(p, FIG / "toxico-list.png", [
        {"selector": "button:has-text('Details') >> nth=0", "n": 1, "position": "top"},
        {"selector": "button:has-text('File') >> nth=0", "n": 2, "position": "top"},
        {"selector": "button:text-is('Discharge') >> nth=0", "n": 3, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 760})

if "sec-after" in steps:
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/caisse")
    p.get_by_text("Connected").first.wait_for(timeout=30000)
    settle(2500)
    p.get_by_placeholder("Search", exact=False).first.fill("Amara") if p.get_by_placeholder("Search", exact=False).count() else None
    settle(2000)
    dump("sec-after", True)
    p.locator("button[title='Notifications']").click(); settle(1000)
    dump("sec-notif")

if "acct-figs" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "promoteur")
    shots.goto(p, "/dashboard/overview"); settle(3000); clear_toast()
    p.click("[aria-label='My Account']"); settle(1500)
    M = "[class*='max-w-md']"
    CROP = {"x": 540, "y": 280, "width": 520, "height": 560}
    shots.annotate(p, FIG / "account-profile.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Password", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": M + " input[type=tel]", "n": 3, "position": "right"},
        {"selector": M + " button[type=submit]", "n": 4, "position": "left"},
    ], crop=CROP)
    p.get_by_text("Password", exact=True).first.click(); settle(800)
    inputs = p.locator(M + " input[type=password]")
    inputs.nth(0).fill("wrong-old-password"); inputs.nth(1).fill("Demo-Pass-2030"); inputs.nth(2).fill("Demo-Pass-2030")
    p.locator(M + " button[type=submit]").click(); settle(2000)
    shots.annotate(p, FIG / "account-password.png", [
        {"selector": M + " input[type=password] >> nth=0", "n": 1, "position": "right"},
        {"selector": M + " input[type=password] >> nth=1", "n": 2, "position": "right"},
        {"selector": M + " input[type=password] >> nth=2", "n": 3, "position": "right"},
        {"selector": M + " button[type=submit]", "n": 4, "position": "left"},
    ], crop=CROP)

if "tour" in steps:
    shots.login(p, "promoteur")
    settle(3000)
    clear_toast()
    p.get_by_text("Lab stock", exact=True).first.click(); p.get_by_text("Production", exact=True).first.click(); settle(800)
    dump("menu-open")
    p.locator("button[title='Notifications']").click(); settle(1200)
    dump("bell")
    p.keyboard.press("Escape")
    for r in ["discount-review","discount-history","cash-closures","reductions-personnel","stock-count","lab-stock-products","lab-stock-requests","lab-stock-receipts","lab-stock-alerts","lab-stock-movements","lab-stock-expenses","fabrication-intrants","fabrication-lots","fabrication-suivi","toxico","finance","stock-adjustment-requests","logs","configuration","patients"]:
        shots.goto(p, "/dashboard/"+r); settle(3500)
        print(r, "->", p.url)
        dump("t-"+r, True)

shots.close(pw, browser)

