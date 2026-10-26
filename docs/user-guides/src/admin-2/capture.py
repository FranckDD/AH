"""Capture script for guide admin-2. Run from the repo root:
    python docs/user-guides/src/admin-2/capture.py [step ...]
Steps perform real actions in the dev database; run each once, in the order of the guide.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:]
pw, browser, p = shots.launch(width=1600, height=1000)


def _on_dialog(d):
    print("BROWSER DIALOG:", d.message)
    d.accept()


p.on("dialog", _on_dialog)


def dump(tag, full=False):
    (HERE / f"_{tag}.txt").write_text(p.inner_text("body"), encoding="utf-8")
    p.screenshot(path=str(FIG / f"_{tag}.png"), full_page=full)


def clear_toast():
    p.keyboard.press("Escape")
    p.wait_for_timeout(700)


def settle(ms=1500):
    p.wait_for_timeout(ms)


def dialog():
    return p.locator("[role=dialog]").first


def new_invoice(name="Amara"):
    shots.goto(p, "/secretariat/caisse")
    p.get_by_role("button", name="New Invoice").first.click()
    settle(1500)
    p.locator("#inv-patient-search").press_sequentially(name, delay=80)
    settle(2500)


def send_discount(exam, note):
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
    p.select_option("#inv-manager", label="Demo Administrator")
    dialog().get_by_role("button", name="Request a discount").click()
    settle(3000)


if "disc-send" in steps:
    shots.login(p, "secretaire")
    send_discount("ALAT", "Guide demo: discount to approve at 20 percent")
    dump("disc-sent1")
    send_discount("ALAT", "Guide demo: discount to refuse")
    send_discount("ALAT", "Guide demo: instalment deadline only")
    shots.goto(p, "/secretariat/caisse")
    dump("disc-sec-list")

if "disc-look" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/discount-review")
    settle(3000)
    dump("disc-review", True)


ADMIN_PW = None
if "disc-decide" in steps:
    shots.login(p, "admin")
    ADMIN_PW = shots.account("admin")["password"]
    shots.goto(p, "/dashboard/discount-review")
    settle(2500)
    ids = p.eval_on_selector_all("input[id^='review-password-']", "els => els.map(e => e.id.replace('review-password-',''))")
    print("IDS", ids)
    a, b, c = ids[0], ids[1], ids[2]
    card = lambda i: p.locator(f"xpath=//input[@id='review-password-{i}']/ancestor::*[contains(@class,'rounded-card')][1]")
    # 1: wrong password, then right one with 20 percent
    card(a).get_by_role("button", name="20%").click()
    p.fill(f"#review-password-{a}", "wrong-password")
    card(a).get_by_role("button", name="Approve").click()
    settle(1500)
    dump("disc-wrongpw")
    card(a).scroll_into_view_if_needed()
    p.fill(f"#review-password-{a}", ADMIN_PW)
    shots.annotate(p, FIG / "discount-card.png", [
        {"selector": f"xpath=//input[@id='review-password-{a}']/ancestor::*[contains(@class,'rounded-card')][1]//button[normalize-space()='20%']", "n": 1, "position": "top"},
        {"selector": f"#review-deadline-{a}", "n": 2, "position": "right"},
        {"selector": f"#review-password-{a}", "n": 3, "position": "right"},
        {"selector": f"xpath=//input[@id='review-password-{a}']/ancestor::*[contains(@class,'rounded-card')][1]//button[normalize-space()='Approve']", "n": 4, "position": "bottom"},
        {"selector": f"xpath=//input[@id='review-password-{a}']/ancestor::*[contains(@class,'rounded-card')][1]//button[normalize-space()='Refuse']", "n": 5, "position": "bottom"},
    ], crop=f"xpath=//input[@id='review-password-{a}']/ancestor::*[contains(@class,'rounded-card')][1]")
    card(a).get_by_role("button", name="Approve").click()
    settle(2500)
    # 2: approve with neither percent nor deadline
    p.fill(f"#review-password-{b}", ADMIN_PW)
    card(b).get_by_role("button", name="Approve").click()
    settle(1500)
    dump("disc-nothing")
    # then refuse
    card(b).get_by_role("button", name="Refuse").click()
    settle(2500)
    # 3: deadline only
    p.fill(f"#review-deadline-{c}", "2026-11-15")
    p.fill(f"#review-password-{c}", ADMIN_PW)
    card(c).get_by_role("button", name="Approve").click()
    settle(2500)
    dump("disc-after")

if "disc-history" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/discount-history")
    settle(3000)
    dump("disc-history", True)
    clear_toast()
    shots.annotate(p, FIG / "discount-history.png", [
        {"text": "Approved", "exact": True, "n": 1, "position": "top", "index": 0, "outline": False},
        {"text": "This month", "exact": True, "n": 2, "position": "top"},
        {"selector": "#dh-status", "n": 3, "position": "top"},
        {"text": "Reduced amount", "exact": True, "n": 4, "position": "top", "outline": False},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 700})

if "count-look" in steps:
    shots.login(p, "stock")
    shots.goto(p, "/dashboard/stock-count")
    settle(3000)
    dump("count-stock", True)
    p.get_by_role("tab", name="Frequency").click() if p.get_by_role("tab", name="Frequency").count() else None
    settle(1500)
    dump("count-stock-freq", True)

if "count-start" in steps:
    shots.login(p, "stock")
    shots.goto(p, "/dashboard/stock-count")
    settle(3000)
    dump("count-start0")
    print(p.evaluate("[...document.querySelectorAll('select,input')].map(e=>e.id+':'+e.type+':'+e.name)"))
    p.get_by_role("button", name="Start a count").click()
    settle(3000)
    dump("count-start2", True)
    print(p.evaluate("[...document.querySelectorAll('input')].map(e=>e.id+':'+e.type)"))

def qty(name):
    return p.locator(f"xpath=(//*[normalize-space(text())='{name}']/ancestor::*[.//input[starts-with(@id,'qty-')]])[last()]//input[starts-with(@id,'qty-')]").first

if "count-do" in steps:
    shots.login(p, "stock")
    shots.goto(p, "/dashboard/stock-count")
    settle(3000)
    qty("Honey").fill("215")
    qty("Efferalgan").fill("40")
    qty("Miel Pure").fill("0")
    settle(500)
    dump("count-filled", True)
    shots.annotate(p, FIG / "_count-entry.png", [{"selector": "#count-search", "n": 1}])
    p.get_by_role("button", name="Validate the count").click()
    settle(4000)
    dump("count-reveal", True)

if "adj-look" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/stock-adjustment-requests")
    settle(3000)
    clear_toast()
    dump("adj-list", True)

if "adj-do" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/stock-adjustment-requests")
    settle(3000)
    clear_toast()
    H = "tr:has-text('Honey'):has-text('Correction')"
    shots.annotate(p, FIG / "adjust-list.png", [
        {"selector": "#adjust-status", "n": 1, "position": "right"},
        {"text": "Request type", "exact": True, "n": 2, "position": "top", "outline": False},
        {"selector": H + " >> text=Counted quantity", "n": 3, "position": "left", "outline": False},
        {"selector": H + " >> button:has-text('Approve')", "n": 4, "position": "top"},
        {"selector": H + " >> button:has-text('Refuse')", "n": 5, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 620})
    p.locator(H + " >> button:has-text('Approve')").click()
    settle(3000)
    dump("adj-approved", True)
    M = "tr:has-text('Miel Pure'):has-text('Correction')"
    p.locator(M + " >> button:has-text('Refuse')").click()
    settle(1200)
    p.fill("#refuse-note", "Recount first: the box in the back store was not included")
    shots.annotate(p, FIG / "adjust-refuse.png", [
        {"selector": "#refuse-note", "n": 1, "position": "top"},
        {"selector": "button[form=refuse-form]", "n": 2, "position": "top"},
    ], crop="[role=dialog]")
    dump("adj-refuse-panel")
    p.locator("button[form=refuse-form]").click()
    settle(3000)
    dump("adj-refused", True)
    p.select_option("#adjust-status", value="")
    settle(2500)
    dump("adj-all", True)

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


if "cc-close" in steps:
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/cloture")
    p.get_by_text("Connected").first.wait_for(timeout=30000)
    settle(800)
    fill_count(53000, 0, 0, 0)
    p.get_by_role("button", name="Validate the closing").click()
    settle(3000)
    p.fill("#comment-especes", "Change given to a patient was not written down")
    p.get_by_role("button", name="Validate the closing").click()
    settle(4000)
    dump("cc-result")
    send_correction(1, "-1000", "Change given to a patient on a 50 000 note, not recorded")
    dump("cc-sent1")
    send_correction(2, "2000", "Guide demo: second request, to be rejected")
    dump("cc-sent2")

if "cc-look" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/cash-closures")
    settle(3500)
    clear_toast()
    dump("cc-page", True)

if "cc-do" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/cash-closures")
    settle(3500)
    clear_toast()
    CARD = "xpath=//li[contains(.,'Orange Money: 2')]"
    CARD2 = "xpath=//li[contains(.,'Cash: 1')]"
    shots.annotate(p, FIG / "closures-top.png", [
        {"text": "Pending corrections", "exact": True, "n": 1, "position": "right", "outline": False},
        {"selector": CARD2 + "//button[normalize-space()='Approve']", "n": 2, "position": "top"},
        {"selector": CARD2 + "//button[normalize-space()='Reject']", "n": 3, "position": "top"},
        {"selector": "#ccr-kind", "n": 4, "position": "top"},
        {"selector": "#ccr-gap", "n": 5, "position": "right"},
        {"text": "View detail", "exact": True, "n": 6, "position": "left", "index": 0},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 860})
    p.locator(CARD2 + "//button[normalize-space()='Approve']").click()
    settle(2500)
    dump("cc-approved")
    p.locator(CARD + "//button[normalize-space()='Reject']").click()
    settle(2500)
    dump("cc-rejected", True)
    p.get_by_role("button", name="View detail").first.click()
    settle(1500)
    dump("cc-detail", True)

if "cc-detail" in steps:
    p.set_viewport_size({"width": 1600, "height": 1500})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/cash-closures")
    settle(3500)
    clear_toast()
    p.get_by_role("button", name="View detail").first.click()
    settle(1500)
    DET = "xpath=//button[normalize-space()='Close detail']/ancestor::*[contains(@class,'rounded-card')][1]"
    p.locator(DET).scroll_into_view_if_needed()
    shots.annotate(p, FIG / "closure-detail.png", [
        {"selector": DET + "//th >> text=Expected", "n": 1, "position": "top"},
        {"selector": DET + "//th >> text=Counted", "n": 2, "position": "top"},
        {"selector": DET + "//th >> text=Difference", "n": 3, "position": "top"},
        {"selector": DET + "//button[normalize-space()='Close detail']", "n": 4, "position": "left"},
    ], crop=DET)

if "modes" in steps:
    p.set_viewport_size({"width": 1600, "height": 1500})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/cash-closures")
    settle(3500)
    clear_toast()
    p.locator("#mode-label-autre_mobile").scroll_into_view_if_needed()
    p.locator("#mode-active-autre_mobile").uncheck()
    MOD = "xpath=//*[normalize-space()='Payment modes']/ancestor::*[contains(@class,'rounded-card')][1]"
    shots.annotate(p, FIG / "closure-modes.png", [
        {"selector": "#mode-label-especes", "n": 1, "position": "top"},
        {"selector": "#mode-order-orange_money", "n": 2, "position": "top"},
        {"selector": "#mode-active-autre_mobile", "n": 3, "position": "top"},
        {"selector": "li:has(#mode-label-autre_mobile) button:has-text('Save')", "n": 4, "position": "top"},
    ], crop=MOD)
    p.locator("li:has(#mode-label-autre_mobile) button:has-text('Save')").click()
    settle(2500)
    dump("modes-saved", True)

if "modes-sec" in steps:
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/cloture")
    p.get_by_text("Connected").first.wait_for(timeout=30000)
    settle(1500)
    dump("modes-sec-view", True)

if "modes-restore" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/cash-closures")
    settle(3500)
    p.locator("#mode-active-autre_mobile").check()
    p.locator("li:has(#mode-label-autre_mobile) button:has-text('Save')").click()
    settle(2500)
    dump("modes-restored", True)

if "rep-look" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    dump("rep-page", True)

if "rep-set" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    print("ORIG", p.input_value("#rs-threshold"), p.input_value("#rs-pending"))
    p.locator("#rs-threshold").scroll_into_view_if_needed()
    p.fill("#rs-threshold", "0")
    p.fill("#rs-pending", "400")
    p.get_by_role("button", name="Save the settings").click()
    settle(1200)
    dump("rep-set-err")
    SET = "xpath=//*[@id='rs-threshold']/ancestor::*[contains(@class,'rounded-card')][1]"
    shots.annotate(p, FIG / "reports-settings.png", [
        {"selector": "#rs-threshold", "n": 1, "position": "top"},
        {"selector": "#rs-pending", "n": 2, "position": "top"},
        {"text": "Save the settings", "exact": True, "n": 3, "position": "top"},
    ], crop=SET)

if "rep-set2" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    p.locator("#rs-threshold").scroll_into_view_if_needed()
    p.fill("#rs-threshold", "5")
    p.fill("#rs-pending", "2")
    SET = "xpath=//*[@id='rs-threshold']/ancestor::*[contains(@class,'rounded-card')][1]"
    p.get_by_role("button", name="Save the settings").click()
    settle(2000)
    dump("rep-set-ok")
    shots.annotate(p, FIG / "reports-settings.png", [
        {"selector": "#rs-threshold", "n": 1, "position": "inside"},
        {"selector": "#rs-pending", "n": 2, "position": "inside"},
        {"text": "Save the settings", "exact": True, "n": 3, "position": "left"},
    ], crop=SET)
    p.reload(); settle(5000)
    print("AFTER RELOAD", p.input_value("#rs-threshold"), p.input_value("#rs-pending"))
    p.fill("#rs-threshold", "3")
    p.fill("#rs-pending", "3")
    p.get_by_role("button", name="Save the settings").click()
    settle(2000)
    p.reload(); settle(5000)
    print("RESTORED", p.input_value("#rs-threshold"), p.input_value("#rs-pending"))

if "rep-fig" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    p.locator("#rs-threshold").scroll_into_view_if_needed()
    SET = "xpath=//*[@id='rs-threshold']/ancestor::*[contains(@class,'rounded-card')][1]"
    shots.annotate(p, FIG / "reports-settings.png", [
        {"selector": "#rs-threshold", "n": 1, "position": "top"},
        {"selector": "#rs-pending", "n": 2, "position": "right"},
        {"text": "Save the settings", "exact": True, "n": 3, "position": "right"},
    ], crop=SET)
    p.evaluate("window.scrollTo(0,0)")
    settle(500)
    p.locator("text=Daily check").first.scroll_into_view_if_needed()
    settle(500)
    p.evaluate("window.scrollTo(0,0)")
    shots.annotate(p, FIG / "reports-top.png", [
        {"text": "Today", "exact": True, "n": 1, "position": "top"},
        {"text": "Custom dates", "exact": True, "n": 2, "position": "top"},
        {"text": "Export as PDF", "exact": True, "n": 3, "position": "right"},
        {"text": "Daily check", "exact": True, "n": 4, "position": "right", "outline": False},
        {"text": "Open the screen", "exact": True, "n": 5, "position": "left", "index": 0},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 730})

if "rep-pdf" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    p.get_by_role("button", name="7 days").click()
    settle(3000)
    try:
        with p.expect_download(timeout=40000) as dl:
            p.get_by_role("button", name="Export as PDF").click()
        d = dl.value
        print("DOWNLOAD", d.suggested_filename)
        d.save_as(str(HERE / "_export.pdf"))
    except Exception as e:
        print("NO DOWNLOAD", str(e)[:100])
        dump("rep-export-fail")
    p.locator("button[title='Notifications']").click() if p.locator("button[title='Notifications']").count() else p.locator("button:has(svg) >> nth=0").click()
    settle(1000)
    dump("notif-open")
    # open the screen link of first control item
    p.keyboard.press("Escape")
    p.get_by_role("button", name="Open the screen").first.click()
    settle(3000)
    print("URL after Open the screen", p.url)

if "rep-pdf2" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.on("response", lambda r: print("RESP", r.status, r.url[-80:], r.headers.get("content-type")) if "export" in r.url else None)
    p.on("requestfailed", lambda r: print("REQFAIL", r.url[-80:], r.failure))
    p.on("console", lambda m: print("CONSOLE", m.type, m.text[:200]) if m.type in ("error",) else None)
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reports")
    settle(5000)
    clear_toast()
    p.get_by_role("button", name="Export as PDF").click()
    settle(8000)
    print(p.get_by_text("Could not generate").count())
    for hdrs in ({}, {"Accept": "application/json, text/plain, */*"}):
        res = p.evaluate("""async (hdrs) => {
          const tok = localStorage.getItem('token');
          try {
            const r = await fetch('http://127.0.0.1:8000/reports/export.pdf?date_from=2026-10-26&date_to=2026-10-26', {headers: {...hdrs, Authorization: 'Bearer ' + tok}});
            return r.status + ' ' + r.headers.get('content-type');
          } catch (e) { return 'ERR ' + e.message; }
        }""", hdrs)
        print("FETCH", hdrs, res)

if "staff" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reductions-personnel")
    settle(3000)
    clear_toast()
    # validation: rate 0 on exams, no save
    EX = "tr:has-text('Exams')"
    p.locator(EX + " input[type=number] >> nth=1").fill("0")
    p.locator(EX + " button:has-text('Save')").click()
    settle(1000)
    dump("staff-err")
    p.locator(EX + " input[type=number] >> nth=1").fill("15")
    p.locator(EX + " button:has-text('Save')").click()
    settle(1500)
    dump("staff-saved")
    # search and mark Amara Njoh
    p.fill("#staff-search", "Amara")
    settle(2000)
    shots.annotate(p, FIG / "staff-rules.png", [
        {"selector": "tr:has-text('Medications') input[type=number] >> nth=0", "n": 1, "position": "top"},
        {"selector": "tr:has-text('Medications') input[type=number] >> nth=1", "n": 2, "position": "top"},
        {"selector": "tr:has-text('Medications') input[type=checkbox]", "n": 3, "position": "top"},
        {"selector": "tr:has-text('Medications') button:has-text('Save')", "n": 4, "position": "right"},
        {"selector": "#staff-search", "n": 5, "position": "top"},
        {"selector": "tr:has-text('Amara Njoh') button >> nth=0", "n": 6, "position": "left"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 1180})
    p.locator("tr:has-text('Amara Njoh') button >> nth=0").click()
    settle(2500)
    dump("staff-marked", True)

if "staff-sec" in steps:
    shots.login(p, "secretaire")
    new_invoice()
    dialog().get_by_text("Amara Njoh").first.click()
    settle(800)
    dialog().get_by_role("button", name="Lab Exam").click()
    settle(800)
    dialog().locator("input[placeholder^='Search a lab exam']").press_sequentially("ALAT", delay=80)
    settle(1200)
    dialog().get_by_text("ALAT").first.click()
    settle(1500)
    dump("staff-invoice")
    dialog().get_by_role("button", name="Cancel").first.click()

if "staff-unmark" in steps:
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/reductions-personnel")
    settle(3000)
    clear_toast()
    p.locator("tr:has-text('Amara Njoh') button >> nth=0").click()
    settle(2500)
    dump("staff-unmarked", True)

if "freq" in steps or "freq-fig" in steps:
    p.set_viewport_size({"width": 1600, "height": 1200})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/stock-count")
    settle(3000)
    clear_toast()
    dump("freq-first", True)
    p.get_by_role("tab", name="Frequency").click()
    settle(2000)
    shots.annotate(p, FIG / "count-frequency.png", [
        {"selector": "#count-interval", "n": 1, "position": "inside"},
        {"text": "Save the frequency", "exact": True, "n": 2, "position": "right"},
        {"selector": "input[type=checkbox] >> nth=0", "n": 3, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 620})
    if "freq-fig" in steps and "freq" not in steps:
        shots.close(pw, browser); sys.exit(0)
    p.fill("#count-interval", "400")
    settle(800)
    print("SAVE DISABLED", p.get_by_role("button", name="Save the frequency").is_disabled())
    dump("freq-bad")
    p.fill("#count-interval", "14")
    p.get_by_role("button", name="Save the frequency").click()
    settle(2000)
    dump("freq-ok")
    p.fill("#count-interval", "30")
    p.get_by_role("button", name="Save the frequency").click()
    settle(2000)
    dump("freq-restored")

if "fab" in steps:
    p.set_viewport_size({"width": 1600, "height": 1400})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/fabrication-suivi")
    settle(3500)
    clear_toast()
    p.fill("#fab-setting-tolerance", "5")
    p.fill("#fab-setting-stale", "10")
    p.get_by_role("button", name="Save settings").click()
    settle(2000)
    dump("fab-ok")
    SETC = "xpath=//*[@id='fab-setting-tolerance']/ancestor::*[contains(@class,'rounded-card')][1]"
    shots.annotate(p, FIG / "fab-settings.png", [
        {"selector": "#fab-setting-tolerance", "n": 1, "position": "top"},
        {"selector": "#fab-setting-stale", "n": 2, "position": "top"},
        {"text": "Save settings", "exact": True, "n": 3, "position": "left"},
    ], crop=SETC)
    p.fill("#fab-setting-tolerance", "150")
    p.get_by_role("button", name="Save settings").click()
    settle(1200)
    dump("fab-bad")
    p.fill("#fab-setting-tolerance", "2")
    p.fill("#fab-setting-stale", "7")
    p.get_by_role("button", name="Save settings").click()
    settle(2000)
    dump("fab-restored")

if "config" in steps:
    p.set_viewport_size({"width": 1600, "height": 1500})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/configuration")
    settle(3500)
    clear_toast()
    dump("cfg-top", True)
    print("NAME", p.input_value("#cfg-name"), "|", p.input_value("#cfg-phone"), "|", p.input_value("#cfg-city"))
    ID = "xpath=//*[@id='cfg-structure']"
    shots.annotate(p, FIG / "config-identity.png", [
        {"selector": "#cfg-logo", "n": 1, "position": "top"},
        {"selector": "#cfg-ticket-logo", "n": 2, "position": "top"},
        {"text": "Regenerate", "n": 3, "position": "left", "outline": True},
        {"selector": "#cfg-name", "n": 4, "position": "top"},
        {"selector": "#cfg-niu", "n": 5, "position": "top"},
        {"selector": "button:has-text('Save') >> nth=0", "n": 6, "position": "left"},
    ], crop=ID) if False else None
    p.screenshot(path=str(FIG / "_cfg-id.png"))
    # save identity unchanged
    p.locator("#cfg-structure button[type=submit]").click()
    settle(2500)
    dump("cfg-saved")
    # open the two folded sections
    p.get_by_text("Prayer book types").first.click() if p.get_by_text("Prayer book types").count() else None
    settle(500)
    dump("cfg-general-before")

if "config2" in steps:
    p.set_viewport_size({"width": 1600, "height": 1500})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/configuration")
    settle(3500)
    clear_toast()
    p.get_by_text("General Settings & Maintenance").first.click()
    p.get_by_text("Prayer Book Types").first.click()
    settle(800)
    p.get_by_role("button", name="Launch Backup").click()
    settle(5000)
    p.get_by_role("button", name="Activate").click()
    settle(800)
    dump("cfg-maint-on", True)
    p.locator("#cfg-structure").scroll_into_view_if_needed()
    p.get_by_text("Maintenance Mode ACTIVE").scroll_into_view_if_needed()
    shots.annotate(p, FIG / "config-general.png", [
        {"text": "Database Backup", "n": 1, "position": "left", "outline": False},
        {"text": "Launch Backup", "exact": True, "n": 2, "position": "left"},
        {"text": "Maintenance Mode", "exact": True, "n": 3, "position": "left", "outline": False},
        {"selector": "button:has-text('Deactivate')", "n": 4, "position": "left"},
        {"text": "Prayer Book Types", "exact": True, "n": 5, "position": "right", "outline": False},
    ], crop={"x": 262, "y": 60, "width": 1338, "height": 1300}) if False else None
    p.reload(); settle(3500)
    p.get_by_text("General Settings & Maintenance").first.click()
    settle(800)
    dump("cfg-maint-reload", True)

if "logs" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/logs")
    settle(4000)
    clear_toast()
    dump("logs-access0", True)
    p.fill("#logs-from", "2026-10-26")
    p.locator("#logs-from").dispatch_event("change")
    settle(3000)
    dump("logs-access1", True)
    p.locator("#logs-tab-actions").click()
    settle(3000)
    dump("logs-actions0", True)
    p.fill("#logs-from", "2026-10-26")
    p.locator("#logs-from").dispatch_event("change")
    settle(3000)
    dump("logs-actions1", True)

if "fin" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/finance")
    settle(4000)
    clear_toast()
    shots.annotate(p, FIG / "finance-list.png", [
        {"text": "New Transaction", "exact": True, "n": 1, "position": "left"},
        {"text": "Cash Balance", "exact": True, "n": 2, "position": "top", "outline": False},
        {"selector": "#fin-search", "n": 3, "position": "top"},
        {"selector": "#fin-category", "n": 4, "position": "top"},
        {"text": "Expenses", "exact": True, "n": 5, "position": "top", "index": 1},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 900})
    p.get_by_role("button", name="New Transaction").click()
    settle(1200)
    print(p.locator("#fin-category option").all_inner_texts())
    p.get_by_role("button", name="Expenses").last.click() if False else None
    dump("fin-modal")
    p.locator("[role=dialog]").get_by_role("button", name="Expenses", exact=True).click()
    p.fill("#fin-amount", "500")
    p.select_option("[role=dialog] #fin-category", label="Other")
    p.select_option("[role=dialog] #fin-method", label="Cash")
    p.fill("#fin-desc", "Guide demo ledger test, to be cancelled")
    shots.annotate(p, FIG / "finance-form.png", [
        {"selector": "[role=dialog] button:text-is('Expenses')", "n": 1, "position": "top"},
        {"selector": "#fin-amount", "n": 2, "position": "top"},
        {"selector": "#fin-date", "n": 3, "position": "top"},
        {"selector": "[role=dialog] #fin-category", "n": 4, "position": "top"},
        {"selector": "[role=dialog] #fin-method", "n": 5, "position": "top"},
        {"selector": "#fin-desc", "n": 6, "position": "top"},
        {"selector": "button[form=finance-form]", "n": 7, "position": "top"},
    ], crop="[role=dialog]")
    p.locator("button[form=finance-form]").click()
    settle(3500)
    dump("fin-saved", True)

if "fin-cancel" in steps:
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/retrait")
    p.get_by_text("Connected").first.wait_for(timeout=30000)
    settle(1500)
    dump("fin-sec-list")
    ROW = "tr:has-text('Guide demo ledger test') >> nth=0"
    p.locator(ROW + " >> button").click()
    settle(1000)
    p.fill("#cancel-justification", "Guide demo entry, cancelled after the test")
    p.locator("[role=dialog] button[type=submit]").click()
    settle(3000)
    dump("fin-sec-cancelled")

if "adj-fig" in steps:
    p.set_viewport_size({"width": 1600, "height": 1300})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/stock-adjustment-requests")
    settle(3000)
    clear_toast()
    E = "tr:has-text('Efferalgan'):has-text('Correction')"
    p.locator(E + " >> button:has-text('Approve')").click()
    settle(3000)
    p.select_option("#adjust-status", value="")
    settle(2500)
    clear_toast()
    shots.annotate(p, FIG / "adjust-all.png", [
        {"selector": "#adjust-status", "n": 1, "position": "right"},
        {"selector": "tr:has-text('Honey'):has-text('Correction') >> text=Stock before", "n": 2, "position": "left", "outline": False},
        {"selector": "tr:has-text('Miel Pure') >> text=Decision reason", "n": 3, "position": "left", "outline": False},
        {"selector": "tr:has-text('Restock') >> button:has-text('Approve')", "n": 4, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 1000})
    dump("adj-fig", True)

if "bell" in steps:
    p.set_viewport_size({"width": 1600, "height": 900})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/overview")
    settle(6000)
    clear_toast()
    p.locator("button[title='Notifications']").click()
    settle(1200)
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "top"},
        {"selector": "div.absolute.right-0.mt-2 >> div.cursor-pointer >> nth=0", "n": 2, "position": "left", "outline": False},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 560}) if "bell-only" in steps or True else None

if "logs-fig" in steps:
    p.set_viewport_size({"width": 1600, "height": 1000})
    shots.login(p, "admin")
    shots.goto(p, "/dashboard/logs")
    settle(4000)
    clear_toast()
    p.locator("#logs-tab-actions").click()
    settle(2500)
    p.fill("#logs-from", "2026-10-26")
    p.locator("#logs-from").dispatch_event("change")
    settle(3000)
    shots.annotate(p, FIG / "logs.png", [
        {"selector": "#logs-from", "n": 1, "position": "top"},
        {"selector": "#logs-tab-access", "n": 2, "position": "top"},
        {"selector": "#logs-tab-actions", "n": 3, "position": "top"},
    ], crop={"x": 262, "y": 80, "width": 1338, "height": 520})

if "sec-after" in steps:
    shots.login(p, "secretaire")
    shots.goto(p, "/secretariat/caisse")
    p.get_by_text("Connected").first.wait_for(timeout=30000)
    settle(2000)
    dump("sec-after", True)
    p.locator("button[title='Notifications']").click()
    settle(1000)
    dump("sec-notif")

shots.close(pw, browser)
