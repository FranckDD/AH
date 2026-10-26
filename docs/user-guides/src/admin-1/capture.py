"""Capture script for guide admin-1. Run from the repo root:
    python docs/user-guides/src/admin-1/capture.py [step ...]
Steps (each one performs real actions in the dev database, run them once, in this order):
    signin home users-list user-create user-edit user-signin account
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


def dump(tag):
    (HERE / f"_{tag}.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.shot(p, FIG / f"_{tag}.png")


def dlg():
    return p.locator("[role=dialog]").first


def settle(ms=1500):
    p.wait_for_timeout(ms)


if "signin" in steps:
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("admin")
    p.fill("#username", acc["username"])
    p.fill("#password", "demo-password")
    shots.annotate(p, FIG / "signin.png", [
        {"selector": "#username", "n": 1},
        {"selector": "#password", "n": 2},
        {"selector": "button[type=submit]", "n": 3},
    ], crop="form >> xpath=..")

if steps and steps != ["signin"] and not any(x.startswith("try-") or x in ("account", "price-lock") for x in steps):
    shots.login(p, "admin")

if "home" in steps:
    shots.goto(p, "/dashboard/overview")
    settle(10000)
    dump("home")
    shots.annotate(p, FIG / "home.png", [
        {"text": "Users", "exact": True, "n": 1, "position": "right", "index": 0},
        {"text": "System Configuration", "n": 2, "position": "right", "index": 0},
        {"text": "EN", "exact": True, "n": 3, "position": "bottom"},
        {"selector": "[aria-label='My Account']", "n": 4, "position": "bottom"},
        {"text": "Quick actions", "n": 5, "position": "left", "outline": False},
    ], crop={"x": 0, "y": 0, "width": 1600, "height": 900})

if "users-list" in steps:
    shots.goto(p, "/dashboard/users")
    settle()
    dump("users")


PWD = "Demo-Pass-2026"


def open_new():
    shots.goto(p, "/dashboard/users")
    p.get_by_role("button", name="New Account").click()
    settle(1200)


def fill_user(first, last, username, email, phone, group, role, pwd=PWD):
    p.fill("#user-firstname", first)
    p.fill("#user-lastname", last)
    p.fill("#user-username", username)
    p.fill("#user-email", email)
    p.fill("#user-phone", phone)
    p.fill("#user-password", pwd)
    p.select_option("#user-group", label=group)
    p.select_option("#user-role", label=role)


def search(term):
    p.fill("#user-search", term)
    settle(2000)


if "user-create" in steps:
    open_new()
    fill_user("Test", "Accueil", "demo.accueil", "demo.accueil@example.org", "600000001",
              "Secretariat", "Secrétaire")
    p.click("button[aria-label='Show password']")
    shots.annotate(p, FIG / "user-form.png", [
        {"selector": "#user-firstname", "n": 1, "position": "top"},
        {"selector": "#user-username", "n": 2, "position": "top"},
        {"selector": "#user-password", "n": 3, "position": "top"},
        {"selector": "#user-group", "n": 4, "position": "top"},
        {"selector": "#user-role", "n": 5, "position": "top"},
        {"text": "Active account (allowed to log in)", "n": 6, "position": "right", "outline": False},
        {"text": "Create Account", "exact": True, "n": 7, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Create Account").click()
    settle(2500)
    dump("user-created1")

if "user-create2" in steps:
    # head nurse
    open_new()
    fill_user("Test", "Infirmier", "demo.infirmier", "demo.infirmier@example.org", "600000002",
              "Medical Service", "Infirmier(e)")
    p.locator("label:has-text('Head nurse') input").check()
    shots.annotate(p, FIG / "user-headnurse.png", [
        {"selector": "#user-role", "n": 1, "position": "top"},
        {"selector": "label:has-text('Head nurse')", "n": 2, "position": "right"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Create Account").click()
    settle(2500)
    # doctor with specialty
    open_new()
    fill_user("Test", "Medecin", "demo.medecin", "demo.medecin@example.org", "600000003",
              "Medical Service", "Médecin")
    settle(500)
    print("SPECS", p.locator("#user-specialty option").all_inner_texts()[:6])
    p.select_option("#user-specialty", index=1)
    shots.annotate(p, FIG / "user-specialty.png", [
        {"selector": "#user-specialty", "n": 1, "position": "top"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Create Account").click()
    settle(2500)
    search("demo.")
    dump("user-created3")
    shots.annotate(p, FIG / "users-list.png", [
        {"selector": "#user-search", "n": 1, "position": "right"},
        {"text": "New Account", "exact": True, "n": 2, "position": "left"},
        {"text": "Role", "exact": True, "n": 3, "position": "right", "index": 0, "outline": False},
        {"text": "Status", "exact": True, "n": 4, "position": "right", "index": 0, "outline": False},
        {"selector": "tr:has-text('demo.accueil') button >> nth=0", "n": 5, "position": "top"},
        {"selector": "tr:has-text('demo.accueil') button >> nth=1", "n": 6, "position": "bottom"},
    ], crop={"x": 280, "y": 40, "width": 1320, "height": 760})


def row_btn(user, n):
    return f"tr:has-text('{user}') button >> nth={n}"


if "user-edit" in steps and False:
    shots.goto(p, "/dashboard/users")
    search("demo.accueil")
    p.locator(row_btn("demo.accueil", 0)).click()
    settle(1200)
    dump("user-edit-open")
    p.fill("#user-username", "demo.accueil.changed")
    p.fill("#user-password", "Demo-Pass-2027")
    p.locator("label:has-text('Active account') input").uncheck()
    shots.annotate(p, FIG / "user-edit.png", [
        {"selector": "#user-username", "n": 1, "position": "top"},
        {"selector": "#user-password", "n": 2, "position": "top"},
        {"selector": "#user-role", "n": 3, "position": "top"},
        {"selector": "label:has-text('Active account')", "n": 4, "position": "right"},
        {"text": "Update", "exact": True, "n": 5, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Update").click()
    settle(2500)
    search("demo.accueil")
    dump("user-edit-saved")
    shots.annotate(p, FIG / "user-inactive.png", [
        {"text": "Inactive", "exact": True, "n": 1, "position": "left"},
    ], crop={"x": 280, "y": 40, "width": 1320, "height": 420})


def try_login(user, pwd, shot=None):
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    p.fill("#username", user)
    p.fill("#password", pwd)
    p.click("button[type=submit]")
    settle(2500)
    print("URL", p.url)
    dump("try")
    if shot:
        shots.annotate(p, FIG / shot, [
            {"selector": "[role=alert]", "n": 1, "position": "right"},
        ], crop="form >> xpath=..")


if "try-wrong" in steps:
    try_login("doc_admin", "not-the-password", "login-refused.png")

if "try-inactive" in steps:
    try_login("demo.accueil", "Demo-Pass-2027", "login-inactive.png")


if "user-reactivate" in steps:
    shots.goto(p, "/dashboard/users")
    search("demo.accueil")
    p.locator(row_btn("demo.accueil", 0)).click()
    settle(1200)
    p.locator("label:has-text('Active account') input").check()
    p.get_by_role("button", name="Update").click()
    settle(2500)
    search("demo.accueil")
    dump("user-reactivated")

if "try-old" in steps:
    try_login("demo.accueil", "Demo-Pass-2026")

if "try-new" in steps:
    try_login("demo.accueil", "Demo-Pass-2027")
    shots.annotate(p, FIG / "_first-login.png", [{"text": "Dashboard", "n": 1}] ) if False else None


if "account" in steps:
    # history: the password was already moved 2026 -> 2027 -> 2028 on the first run (success message verified)
    try_login("demo.accueil", "Demo-Pass-2028")
    p.click("[aria-label='My Account']")
    settle(1500)
    pf = p.locator("form").last
    p.locator("[class*='max-w-md'] input[type=tel]").fill("600000099")
    dump("account-profile")
    shots.annotate(p, FIG / "account-profile.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Password", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": "[class*='max-w-md'] input[type=tel]", "n": 3, "position": "right"},
        {"selector": "[class*='max-w-md'] button[type=submit]", "n": 4, "position": "left"},
    ], crop="[class*='max-w-md']")
    p.locator("[class*='max-w-md'] button[type=submit]").click()
    settle(2000)
    dump("account-profile-saved")
    p.get_by_text("Password", exact=True).first.click()
    settle(800)
    inputs = p.locator("[class*='max-w-md'] input[type=password]")
    inputs.nth(0).fill("wrong-old-password")
    inputs.nth(1).fill("Demo-Pass-2029")
    inputs.nth(2).fill("Demo-Pass-2029")
    p.locator("[class*='max-w-md'] button[type=submit]").click()
    settle(2000)
    shots.annotate(p, FIG / "account-password.png", [
        {"selector": "[class*='max-w-md'] input[type=password] >> nth=0", "n": 1, "position": "right"},
        {"selector": "[class*='max-w-md'] input[type=password] >> nth=1", "n": 2, "position": "right"},
        {"selector": "[class*='max-w-md'] input[type=password] >> nth=2", "n": 3, "position": "right"},
        {"selector": "[class*='max-w-md'] button[type=submit]", "n": 4, "position": "left"},
        {"text": "L'ancien mot de passe est incorrect", "n": 5, "position": "right", "outline": False},
    ], crop="[class*='max-w-md']")


if "user-edit2" in steps:
    shots.goto(p, "/dashboard/users")
    search("demo.infirmier")
    p.locator(row_btn("demo.infirmier", 0)).click()
    settle(1200)
    shots.annotate(p, FIG / "user-edit.png", [
        {"selector": "#user-username", "n": 1, "position": "top"},
        {"selector": "button[aria-label='Show password']", "n": 2, "position": "right"},
        {"selector": "#user-role", "n": 3, "position": "top"},
        {"selector": "label:has-text('Head nurse')", "n": 4, "position": "right"},
        {"selector": "label:has-text('Active account')", "n": 5, "position": "right"},
        {"text": "Update", "exact": True, "n": 6, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Cancel").click()


def cfg_open():
    shots.goto(p, "/dashboard/configuration")
    settle(2500)
    p.get_by_text("Exam Pricing", exact=True).first.scroll_into_view_if_needed()
    settle(800)


if "config-look" in steps:
    cfg_open()
    dump("config-exams")
    p.screenshot(path=str(FIG / "_cfgx.png"))
    p.get_by_role("button", name="New Exam").first.click()
    settle(1000)
    dump("config-newexam")
    print("MODAL", dlg().inner_text())


if "exam-create" in steps:
    cfg_open()
    shots.annotate(p, FIG / "exam-list.png", [
        {"selector": "#cfg-exam-search", "n": 1, "position": "top"},
        {"text": "New Exam", "exact": True, "n": 2, "position": "top"},
        {"text": "Price (FCFA)", "exact": True, "n": 3, "position": "top", "outline": False},
        {"selector": "tr:has-text('ACIDE_URIQUE') button >> nth=0", "n": 4, "position": "top"},
        {"selector": "tr:has-text('ACIDE_URIQUE') button >> nth=1", "n": 5, "position": "top"},
    ], crop={"x": 280, "y": 480, "width": 1320, "height": 520})
    p.get_by_role("button", name="New Exam").first.click()
    settle(1000)
    p.fill("#exam-nom", "Demo test exam")
    p.fill("#exam-code", "DEMO_TEST")
    p.fill("#exam-categorie", "Biochimie")
    p.fill("#exam-prix", "7500")
    shots.annotate(p, FIG / "exam-form.png", [
        {"selector": "#exam-nom", "n": 1, "position": "top"},
        {"selector": "#exam-code", "n": 2, "position": "top"},
        {"selector": "#exam-categorie", "n": 3, "position": "top"},
        {"selector": "#exam-prix", "n": 4, "position": "top"},
        {"text": "Save", "exact": True, "n": 5, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Save", exact=True).click()
    settle(2500)
    p.fill("#cfg-exam-search", "DEMO_TEST")
    settle(800)
    dump("exam-created")

if "exam-edit" in steps:
    cfg_open()
    p.fill("#cfg-exam-search", "DEMO_TEST")
    settle(800)
    p.locator("tr:has-text('DEMO_TEST') button >> nth=0").click()
    settle(1000)
    p.fill("#exam-prix", "8000")
    shots.annotate(p, FIG / "exam-edit.png", [
        {"selector": "#exam-code", "n": 1, "position": "top"},
        {"selector": "#exam-prix", "n": 2, "position": "top"},
        {"text": "Save", "exact": True, "n": 3, "position": "left"},
    ], crop="[role=dialog]")
    p.get_by_role("button", name="Save", exact=True).click()
    settle(2500)
    dump("exam-edited")


if "product-create" in steps:
    shots.goto(p, "/dashboard/stock")
    settle(2000)
    dump("stock")
    shots.annotate(p, FIG / "stock-list.png", [
        {"selector": "#stock-search", "n": 1, "position": "top"},
        {"selector": "#stock-category", "n": 2, "position": "top"},
        {"selector": "main button:has-text('New Product') >> nth=0", "n": 3, "position": "left"},
        {"text": "Unit Price", "exact": True, "n": 4, "position": "right", "outline": False},
        {"selector": "tr:has-text('Honey') button >> nth=0", "n": 5, "position": "top"},
        {"selector": "tr:has-text('Honey') button >> nth=1", "n": 6, "position": "top"},
    ], crop={"x": 280, "y": 40, "width": 1320, "height": 760})
    p.locator("main button:has-text('New Product') >> nth=0").click()
    settle(1000)
    p.fill("#product-name", "Demo test syrup")
    p.select_option("#product-category", value="PHARMA")
    p.fill("#product-price", "1200")
    p.fill("#product-quantity", "20")
    p.fill("#product-threshold", "5")
    p.fill("#product-dosage", "250mg")
    p.fill("#product-expiry", "2027-12-31")
    shots.annotate(p, FIG / "product-form.png", [
        {"selector": "#product-name", "n": 1, "position": "top"},
        {"selector": "#product-category", "n": 2, "position": "top"},
        {"selector": "#product-price", "n": 3, "position": "top"},
        {"selector": "#product-quantity", "n": 4, "position": "top"},
        {"selector": "#product-threshold", "n": 5, "position": "top"},
        {"selector": "#product-expiry", "n": 6, "position": "top"},
    ], crop="[role=dialog]")
    print(dlg().inner_text())
    dlg().get_by_role("button", name="Save", exact=True).click()
    settle(2500)
    p.fill("#stock-search", "Demo test")
    settle(2000)
    dump("product-created")


if "product-edit" in steps:
    shots.goto(p, "/dashboard/stock")
    settle(1500)
    p.fill("#stock-search", "Demo test")
    settle(2000)
    p.locator("tr:has-text('Demo test syrup') button >> nth=0").click()
    settle(1000)
    p.fill("#product-price", "1500")
    shots.annotate(p, FIG / "product-edit.png", [
        {"selector": "#product-price", "n": 1, "position": "top"},
        {"selector": "#product-quantity", "n": 2, "position": "top"},
        {"text": "Mettre à jour", "exact": True, "n": 3, "position": "left"},
    ], crop="[role=dialog]")
    dlg().get_by_role("button").last.click()
    settle(2500)
    p.fill("#stock-search", "Demo test")
    settle(2000)
    dump("product-edited")


if "price-lock" in steps:
    try_login("demo.accueil", "Demo-Pass-2028")
    shots.goto(p, "/secretariat/caisse")
    p.get_by_role("button", name="New Invoice").first.click()
    settle(1500)
    p.locator("#inv-patient-search").press_sequentially("Amara", delay=80)
    settle(2500)
    dlg().get_by_text("Amara Njoh").first.click()
    settle(800)
    dlg().get_by_role("button", name="Lab Exam").click()
    settle(800)
    lab = dlg().locator("input[placeholder^='Search a lab exam']")
    lab.press_sequentially("Demo test", delay=80)
    settle(1200)
    dlg().get_by_text("Demo test exam").first.click()
    settle(800)
    dlg().get_by_role("button", name="Lab Exam").click()
    settle(800)
    dlg().locator("input[placeholder^='Search a lab exam']").last.press_sequentially("Skin", delay=80)
    settle(1200)
    dlg().get_by_text("Skin snip test").first.click()
    settle(800)
    dlg().get_by_role("button", name="Free-form Service").click()
    settle(800)
    p.locator("#line-1-price").scroll_into_view_if_needed()
    dump("price-lock")
    print("P1", p.input_value("#line-1-price"), "P2", p.input_value("#line-2-price"), "RO", p.locator("#line-1-price").get_attribute("readonly"), p.locator("#line-3-price").get_attribute("readonly"))
    shots.annotate(p, FIG / "price-lock.png", [
        {"selector": "#line-1-price", "n": 1, "position": "right"},
        {"selector": "#line-2-price", "n": 2, "position": "right"},
        {"selector": "#line-3-price", "n": 3, "position": "right"},
    ])
    dlg().get_by_role("button", name="Cancel").first.click()


if "exam-list" in steps:
    cfg_open()
    shots.annotate(p, FIG / "exam-list.png", [
        {"selector": "#cfg-exam-search", "n": 1, "position": "top"},
        {"text": "New Exam", "exact": True, "n": 2, "position": "top"},
        {"text": "Price (FCFA)", "exact": True, "n": 3, "position": "right", "outline": False},
        {"selector": "tr:has-text('ACIDE_URIQUE') button >> nth=0", "n": 4, "position": "top"},
        {"selector": "tr:has-text('ACIDE_URIQUE') button >> nth=1", "n": 5, "position": "top"},
    ], crop={"x": 280, "y": 480, "width": 1320, "height": 520})

if "lab-config" in steps:
    shots.goto(p, "/dashboard/labo/config")
    settle(9000)
    dump("lab-config")
    shots.annotate(p, FIG / "lab-catalog.png", [
        {"text": "Config", "exact": True, "n": 1, "position": "bottom", "index": 0},
        {"text": "New Exam", "exact": True, "n": 2, "position": "left"},
        {"text": "Category", "exact": True, "n": 3, "position": "right", "outline": False},
        {"selector": "tr:has-text('ACIDE_URIQUE') button", "n": 4, "position": "left"},
    ], crop={"x": 280, "y": 60, "width": 1320, "height": 620})


if "dups" in steps:
    open_new()
    fill_user("Test", "Double", "demo.medecin", "demo.double@example.org", "600000004", "Medical Service", "Infirmier(e)")
    p.get_by_role("button", name="Create Account").click()
    settle(2500)
    dump("dup-user")
    print("DUP USER DIALOGS above; modal still open:", dlg().is_visible())
    shots.annotate(p, FIG / "_dup-user.png", [{"selector": "#user-username", "n": 1}], crop="[role=dialog]") if False else None
    p.keyboard.press("Escape")
    cfg_open()
    p.get_by_role("button", name="New Exam").first.click()
    settle(800)
    p.fill("#exam-nom", "Demo duplicate")
    p.fill("#exam-code", "DEMO_TEST")
    p.fill("#exam-categorie", "Biochimie")
    p.fill("#exam-prix", "100")
    p.get_by_role("button", name="Save", exact=True).click()
    settle(2500)
    dump("dup-exam")


if "cleanup" in steps:
    for u in ("demo.medecin", "demo.infirmier", "demo.accueil"):
        shots.goto(p, "/dashboard/users")
        search(u)
        p.locator(row_btn(u, 1)).click()
        settle(2500)
        search(u)
        print("USER", u, "still listed:", p.locator(f"tr:has-text('{u}')").count())
    cfg_open()
    p.fill("#cfg-exam-search", "DEMO_TEST")
    settle(800)
    p.locator("tr:has-text('DEMO_TEST') button >> nth=1").click()
    settle(2500)
    p.fill("#cfg-exam-search", "DEMO_TEST")
    settle(800)
    print("EXAM still listed:", p.locator("tr:has-text('DEMO_TEST')").count())
    shots.goto(p, "/dashboard/stock")
    settle(1500)
    p.fill("#stock-search", "Demo test")
    settle(2000)
    p.locator("tr:has-text('Demo test syrup') button >> nth=1").click()
    settle(2500)
    p.fill("#stock-search", "Demo test")
    settle(2000)
    print("PRODUCT still listed:", p.locator("tr:has-text('Demo test syrup')").count())


if "step-check" in steps:
    cfg_open()
    p.locator("tr:has-text('ACIDE_URIQUE') button >> nth=0").click()
    settle(1000)
    p.fill("#exam-prix", "7550")
    print("STEP MISMATCH 7550:", p.evaluate("document.querySelector('#exam-prix').validity.stepMismatch"))
    p.fill("#exam-prix", "7500")
    print("STEP MISMATCH 7500:", p.evaluate("document.querySelector('#exam-prix').validity.stepMismatch"))
    p.get_by_role("button", name="Cancel").click()


if "stock-fig" in steps:
    shots.goto(p, "/dashboard/stock")
    settle(10000)
    shots.annotate(p, FIG / "stock-list.png", [
        {"selector": "#stock-search", "n": 1, "position": "top"},
        {"selector": "#stock-category", "n": 2, "position": "top"},
        {"selector": "main button:has-text('New Product') >> nth=0", "n": 3, "position": "left"},
        {"text": "Unit Price", "exact": True, "n": 4, "position": "right", "outline": False},
        {"selector": "tr:has-text('Honey') button >> nth=0", "n": 5, "position": "top"},
        {"selector": "tr:has-text('Honey') button >> nth=1", "n": 6, "position": "top"},
    ], crop={"x": 280, "y": 40, "width": 1320, "height": 760})


if "role-options" in steps:
    open_new()
    for g in ("Administration & Management", "Medical Service", "Secretariat", "Laboratory"):
        p.select_option("#user-group", label=g)
        settle(300)
        print(g, "->", p.locator("#user-role option").all_inner_texts())
    p.keyboard.press("Escape")

shots.close(pw, browser)
