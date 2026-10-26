"""Capture script for guide lab-1. Run from the repo root:
    python docs/user-guides/src/lab-1/capture.py [step ...]
Steps that act on the dev database (run once): recep ext bench
Demo data (fake): Linda Etoga AH2-960220EX (doctor lab order NFS + Glycemie a jeun, registered at reception),
Rosine Ateba (invoiced for Acide urique by the secretary, no prescription), external patients Samuel Biyick and Carine Ndzie.
figures/pdf-sheet.png was cut from the batch PDF downloaded straight from the API (GET /labo/batch/{batch_id}/pdf), because the browser download fails.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin", "dashboard"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-lab1"


def go(p, route, settle=3000):
    shots.goto(p, route)
    try:
        p.get_by_text("Connected").first.wait_for(timeout=30000)
    except Exception:
        pass
    p.wait_for_timeout(settle)


def txt(p, name):
    (HERE / f"_{name}.txt").write_text(p.inner_text("body"), encoding="utf-8")


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("laborantin")
    p.fill("#username", acc["username"])
    p.fill("#password", "demo-password")
    shots.annotate(p, FIG / "signin.png", [
        {"selector": "#username", "n": 1},
        {"selector": "#password", "n": 2},
        {"selector": "button[type=submit]", "n": 3},
    ], crop="form")
    shots.close(pw, br)

if any(s != "signin" for s in steps):
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
    shots.login(p, "laborantin")

if "dashboard" in steps:
    go(p, "/dashboard/labo/overviewlab")
    shots.annotate(p, FIG / "dashboard.png", [
        {"text": "Laboratory", "exact": True, "n": 1, "position": "right", "outline": False, "index": 0},
        {"text": "Connected", "n": 2, "position": "bottom"},
        {"text": "Reception", "exact": True, "n": 3, "position": "bottom"},
        {"text": "This month", "exact": True, "n": 4, "position": "bottom"},
        {"text": "Pending (Bench)", "n": 5, "position": "right", "outline": False},
        {"text": "Pathological", "n": 6, "position": "right", "outline": False},
        {"text": "Enter", "exact": True, "n": 7, "position": "left", "index": 0},
    ])

if "recep" in steps:
    go(p, "/dashboard/labo/reception")
    p.fill("#lab-reception-search", "Etoga")
    p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "recep-search.png", [
        {"text": "Existing File", "exact": True, "n": 1, "position": "top"},
        {"selector": "#lab-reception-search", "n": 2, "position": "left"},
        {"text": "2 exams prescribed", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 110, "width": 1344, "height": 460})
    p.get_by_text("2 exams prescribed").first.click()
    p.wait_for_timeout(1000)
    p.select_option("#lab-reception-doctor", label="Dr Paul Essomba, Doctor")
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.wait_for_timeout(800)
    txt(p, "recep-filled")
    shots.annotate(p, FIG / "recep-filled.png", [
        {"text": "Existing File", "exact": True, "n": 1, "position": "top"},
        {"text": "Change", "exact": True, "n": 2, "position": "left"},
        {"selector": "#lab-reception-doctor", "n": 3, "position": "right"},
        {"selector": "#lab-reception-exam", "n": 4, "position": "right"},
        {"text": "Remove", "n": 5, "position": "left", "index": 0},
        {"text": "CREATE REQUEST", "n": 6, "position": "top"},
    ], crop={"x": 256, "y": 100, "width": 1344, "height": 1100})
    p.once("dialog", lambda d: (print("ALERT:", d.message), d.accept()))
    p.get_by_text("CREATE REQUEST").click()
    p.wait_for_timeout(4000)
    txt(p, "recep-after")
    shots.shot(p, FIG / "_recep-after.png")
    p.set_viewport_size({"width": 1600, "height": 1000})

if "ext" in steps:
    go(p, "/dashboard/labo/reception")
    p.fill("#lab-reception-search", "Ateba")
    p.wait_for_timeout(2500)
    txt(p, "recep-noprescr")
    shots.shot(p, FIG / "_recep-noprescr.png")
    p.fill("#lab-reception-search", "")
    p.get_by_text("External Patient", exact=True).click()
    p.wait_for_timeout(800)
    p.fill("#lab-ext-name", "Samuel Biyick")
    p.fill("#lab-ext-age", "34")
    p.select_option("#lab-reception-doctor", label="Dr Paul Essomba, Doctor")
    for ex in ("Acide urique (ACIDE_URIQUE)", "Créatinine (CREAT)"):
        p.select_option("#lab-reception-exam", label=ex)
        p.get_by_text("Add", exact=True).click()
        p.wait_for_timeout(400)
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.wait_for_timeout(800)
    shots.annotate(p, FIG / "recep-external.png", [
        {"text": "External Patient", "exact": True, "n": 1, "position": "top"},
        {"selector": "#lab-ext-name", "n": 2, "position": "top"},
        {"selector": "#lab-ext-age", "n": 3, "position": "top"},
        {"selector": "#lab-ext-gender", "n": 4, "position": "top"},
        {"selector": "#lab-reception-doctor", "n": 5, "position": "right"},
        {"text": "Add", "exact": True, "n": 6, "position": "top"},
        {"text": "CREATE REQUEST", "n": 7, "position": "top"},
    ], crop={"x": 256, "y": 100, "width": 1344, "height": 1100})
    p.once("dialog", lambda d: (print("ALERT:", d.message), d.accept()))
    p.get_by_text("CREATE REQUEST").click()
    p.wait_for_timeout(4000)
    txt(p, "ext-after")
    p.set_viewport_size({"width": 1600, "height": 1000})

if "bench" in steps:
    go(p, "/dashboard/labo/paillasse")
    txt(p, "bench-top")
    p.locator("article:has-text('Etoga Linda')").get_by_text("Numération Formule Sanguine").click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 2000})
    p.wait_for_timeout(800)
    shots.annotate(p, FIG / "bench-list.png", [
        {"text": "Refresh the list", "n": 1, "position": "right"},
        {"text": "Samuel Biyick", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "0 of 2 exams done", "n": 3, "position": "right", "outline": False, "index": 1},
        {"text": "Numération Formule Sanguine", "n": 4, "position": "right", "index": 0},
    ], crop={"x": 256, "y": 150, "width": 1344, "height": 700})
    def row(name):
        return p.locator("tr", has_text=name).first
    def fill(name, val, flag=None, note=None):
        row(name).locator("input[type=number]").fill(str(val))
        p.wait_for_timeout(300)
        if flag:
            row(name).get_by_text(flag, exact=True).click()
        if note:
            row(name).locator("input[type=text]").fill(note)
    fill("Erythrocytes", 3.9)
    fill("Hémoglobine", 9.8)
    fill("Hématocrite", 31, "Low", "Low, in line with anaemia")
    fill("Leucocytes", 7200, "Normal")
    fill("Plaquettes", 480000, "High")
    p.fill("#lab-tech-note", "Mild anaemia. Platelets slightly raised. Repeat in four weeks.")
    p.wait_for_timeout(500)
    txt(p, "bench-filled")
    shots.annotate(p, FIG / "bench-form.png", [
        {"text": "Numération Formule Sanguine", "n": 1, "position": "right", "index": 1, "outline": False},
        {"text": "parameters entered", "n": 2, "position": "right", "outline": False},
        {"selector": "tr:has-text('Hémoglobine') input[type=number]", "n": 3, "position": "left"},
        {"text": "Reference", "exact": True, "n": 4, "position": "top"},
        {"selector": "tr:has-text('Hématocrite') >> text=Low", "n": 5, "position": "right"},
        {"selector": "tr:has-text('Hématocrite') input[type=text]", "n": 6, "position": "bottom"},
    ], crop={"x": 700, "y": 150, "width": 900, "height": 900})
    shots.annotate(p, FIG / "bench-actions.png", [
        {"selector": "#lab-tech-note", "n": 1, "position": "top"},
        {"text": "Save Draft", "n": 2, "position": "top"},
        {"text": "Validate & Close", "n": 3, "position": "top"},
        {"text": "VALIDATE & PRINT", "n": 4, "position": "top"},
    ], crop={"x": 700, "y": 1200, "width": 900, "height": 420})
    p.get_by_text("Save Draft").click()
    p.wait_for_timeout(3500)
    txt(p, "bench-draft")
    shots.shot(p, FIG / "_bench-draft.png")
    p.set_viewport_size({"width": 1600, "height": 1000})

if "validate" in steps:
    go(p, "/dashboard/labo/paillasse")
    p.locator("article:has-text('Etoga Linda')").get_by_text("Numération Formule Sanguine").click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 2000})
    p.wait_for_timeout(800)
    txt(p, "val-reopened")
    shots.shot(p, FIG / "_val-reopened.png")
    p.get_by_text("Validate & Close").click()
    p.wait_for_timeout(4000)
    txt(p, "val-after")
    shots.shot(p, FIG / "_val-after.png")
    p.set_viewport_size({"width": 1600, "height": 1000})

if "glyc" in steps:
    go(p, "/dashboard/labo/paillasse")
    p.locator("article:has-text('Etoga Linda')").get_by_text("Glycémie à jeun").click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1400})
    p.wait_for_timeout(800)
    txt(p, "glyc-open")
    shots.shot(p, FIG / "_glyc-open.png")
    ins = p.locator("tr input[type=number]")
    print("inputs", ins.count())
    ins.nth(0).fill("0.92"); ins.nth(1).fill("0.95")
    p.wait_for_timeout(500)
    shots.shot(p, FIG / "_glyc-filled.png")
    with p.expect_download(timeout=20000) as dl:
        p.get_by_text("VALIDATE & PRINT").click()
    d = dl.value
    d.save_as(str(HERE / "figures/_glyc.pdf"))
    p.wait_for_timeout(2500)
    txt(p, "glyc-after")
    shots.shot(p, FIG / "_glyc-after.png")
    p.set_viewport_size({"width": 1600, "height": 1000})

if "hist" in steps:
    go(p, "/dashboard/labo/history")
    shots.annotate(p, FIG / "history.png", [
        {"selector": "#lab-history-search", "n": 1, "position": "top"},
        {"selector": "#lab-history-status", "n": 2, "position": "top"},
        {"text": "Refresh", "exact": True, "n": 3, "position": "top"},
        {"text": "Today,", "n": 4, "position": "right", "outline": False},
        {"text": "Show exams", "n": 5, "position": "bottom", "index": 0},
        {"text": "Full file PDF", "n": 6, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 150, "width": 1344, "height": 520})
    p.get_by_text("Show exams").first.click()
    p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "history-open.png", [
        {"text": "Hide exams", "n": 1, "position": "right", "index": 0},
        {"text": "View details", "n": 2, "position": "bottom", "index": 0},
        {"text": "Download PDF", "n": 3, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 150, "width": 1344, "height": 600})
    p.get_by_text("View details").first.click()
    p.wait_for_timeout(2500)
    txt(p, "hist-modal")
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.wait_for_timeout(800)
    print("dialogs", p.locator("[role=dialog]").count())
    shots.annotate(p, FIG / "result-modal.png", [
        {"text": "Biological Results", "n": 1, "position": "top", "outline": False},
        {"text": "Reference Values", "n": 2, "position": "top"},
        {"text": "Interpretation", "exact": True, "n": 3, "position": "top"},
        {"text": "Conclusion / General notes", "n": 4, "position": "right", "outline": False},
        {"text": "Print", "exact": True, "n": 5, "position": "left"},
    ], crop="[role=dialog]")
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.keyboard.press("Escape")
    p.wait_for_timeout(500)
    p.reload(); p.wait_for_timeout(3000)
    p.fill("#lab-history-search", "Kamdem")
    p.wait_for_timeout(2500)
    shots.shot(p, FIG / "_hist-search.png")
    txt(p, "hist-search")
    p.fill("#lab-history-search", "")
    p.select_option("#lab-history-status", label="Pending")
    p.wait_for_timeout(2500)
    shots.shot(p, FIG / "_hist-pending.png")
    txt(p, "hist-pending")

if "bell" in steps:
    go(p, "/dashboard/labo/overviewlab")
    p.locator("button[title='Notifications']").first.click()
    p.wait_for_timeout(2000)
    txt(p, "bell")
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "top"},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 360})

if "profile" in steps:
    go(p, "/dashboard/labo/overviewlab")
    p.click("[aria-label='My Account']")
    p.wait_for_timeout(1500)
    txt(p, "profile")
    shots.annotate(p, FIG / "account-profile.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Password", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": "[class*='max-w-md'] input[type=tel]", "n": 3, "position": "right"},
        {"selector": "[class*='max-w-md'] button[type=submit]", "n": 4, "position": "left"},
    ], crop="[class*='max-w-md']")

if "sync" in steps:
    go(p, "/dashboard/labo/sync-failures")
    txt(p, "sync")
    shots.shot(p, FIG / "_sync.png")

if "offline" in steps:
    for route in ("/dashboard/labo/overviewlab", "/dashboard/labo/reception", "/dashboard/labo/paillasse", "/dashboard/labo/history"):
        go(p, route, settle=5000)
    p.locator("article:has-text('Samuel Biyick')").get_by_text("Acide urique").click()
    p.wait_for_timeout(3000)
    shots.close(pw, br)
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/dashboard/labo/paillasse")
    p.get_by_text("Offline").first.wait_for(timeout=60000)
    shots.wait_ready(p)
    p.wait_for_timeout(4000)
    txt(p, "off-bench")
    shots.shot(p, FIG / "_off-bench.png")
    p.locator("article:has-text('Samuel Biyick')").get_by_text("Acide urique").click()
    p.wait_for_timeout(3500)
    txt(p, "off-open")
    shots.shot(p, FIG / "_off-open.png")
    p.locator("tr input[type=number]").first.fill("41")
    p.wait_for_timeout(500)
    p.get_by_text("Validate & Close").click()
    p.wait_for_timeout(3500)
    txt(p, "off-validated")
    shots.annotate(p, FIG / "offline-bench.png", [
        {"selector": "text=/Offline|Sending error/ >> visible=true", "n": 1, "position": "bottom"},
        {"text": "Technical Bench", "n": 2, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 700})
    shots.close(pw, br)
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
    shots.goto(p, "/dashboard/labo/history")
    p.get_by_text("Connected").first.wait_for(timeout=60000)
    p.wait_for_timeout(12000)
    p.reload(); p.wait_for_timeout(5000)
    txt(p, "off-synced")

if "benchfig" in steps:
    # Retake of the list and the action bar with Samuel Biyick (nothing is saved here).
    go(p, "/dashboard/labo/paillasse")
    shots.annotate(p, FIG / "bench-list.png", [
        {"text": "Refresh the list", "n": 1, "position": "right"},
        {"text": "External", "exact": True, "n": 2, "position": "left", "index": 0},
        {"text": "1 of 2 exams done", "n": 3, "position": "right", "outline": False, "index": 0},
        {"selector": "article:has-text('Samuel Biyick') button:has-text('Créatinine')", "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 150, "width": 560, "height": 560})
    p.locator("article:has-text('Samuel Biyick')").get_by_text("Créatinine").click()
    p.wait_for_timeout(3000)
    p.fill("tr input[type=number]", "9.4")
    p.fill("#lab-tech-note", "Value to confirm on the next sample.")
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "bench-actions.png", [
        {"selector": "tr input[type=number]", "n": 1, "position": "top"},
        {"selector": "#lab-tech-note", "n": 2, "position": "top"},
        {"text": "Save Draft", "n": 3, "position": "top"},
        {"text": "Validate & Close", "n": 4, "position": "top"},
        {"text": "VALIDATE & PRINT", "n": 5, "position": "top"},
    ], crop={"x": 700, "y": 150, "width": 900, "height": 760})
    txt(p, "benchfig")

if "recep2" in steps:
    # Extra external request used only to retake the entry form without touching earlier cases.
    go(p, "/dashboard/labo/reception")
    p.get_by_text("External Patient", exact=True).click()
    p.wait_for_timeout(800)
    p.fill("#lab-ext-name", "Carine Ndzie")
    p.fill("#lab-ext-age", "29")
    p.select_option("#lab-ext-gender", "F")
    p.select_option("#lab-reception-doctor", label="Dr Paul Essomba, Doctor")
    p.select_option("#lab-reception-exam", label="Numération Formule Sanguine (NFS)")
    p.get_by_text("Add", exact=True).click()
    p.wait_for_timeout(400)
    p.once("dialog", lambda d: d.accept())
    p.get_by_text("CREATE REQUEST").click()
    p.wait_for_timeout(4000)

if "benchform" in steps:
    go(p, "/dashboard/labo/paillasse")
    p.locator("article:has-text('Carine Ndzie')").get_by_text("Numération Formule Sanguine").click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.wait_for_timeout(800)
    def row(name):
        return p.locator("tr", has_text=name).first
    def fill(name, val, flag=None, note=None):
        row(name).locator("input[type=number]").fill(str(val))
        p.wait_for_timeout(300)
        if flag:
            row(name).get_by_text(flag, exact=True).click()
        if note:
            row(name).locator("input[type=text]").fill(note)
    fill("Hémoglobine", 9.8)
    fill("Hématocrite", 31, "Low", "Low, in line with anaemia")
    fill("Leucocytes", 7200, "Normal")
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "bench-form.png", [
        {"text": "#EXT-", "n": 1, "position": "right", "outline": False},
        {"text": "parameters entered", "n": 2, "position": "right", "outline": False},
        {"selector": "tr:has-text('Hémoglobine') input[type=number]", "n": 3, "position": "left"},
        {"text": "Reference", "exact": True, "n": 4, "position": "top"},
        {"selector": "tr:has-text('Hématocrite') >> text=Low", "n": 5, "position": "top"},
        {"selector": "tr:has-text('Hématocrite') input[type=text]", "n": 6, "position": "bottom"},
    ], crop={"x": 700, "y": 150, "width": 900, "height": 1000})
    p.set_viewport_size({"width": 1600, "height": 1000})

if any(s != "signin" for s in steps):
    shots.close(pw, br)
