"""Retake of lab-1 figures (batch 3, 27 Oct 2026). python docs/user-guides/src/lab-1/retake_b3.py [step ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from retake_lib import *
FIG = Path("docs/user-guides/src/lab-1/figures")
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-lab1"
steps = sys.argv[1:] or ["explore"]
pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
fresh(p)
shots.login(p, "laborantin")
if "explore" in steps:
    go(p, "/dashboard/labo/paillasse")
    print("BENCH", txt(p, 2500))
    go(p, "/dashboard/labo/reception")
    p.fill("#lab-reception-search", "Ateba"); p.wait_for_timeout(2500)
    print("RECEP", txt(p, 1500))
    go(p, "/dashboard/labo/history")
    print("HIST", txt(p, 2500))
def row(name): return p.locator("tr", has_text=name).first
if "recep" in steps:
    go(p, "/dashboard/labo/reception")
    p.fill("#lab-reception-search", "Ateba"); p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "recep-search.png", [
        {"text": "Existing File", "exact": True, "n": 1, "position": "top"},
        {"selector": "#lab-reception-search", "n": 2, "position": "left"},
        {"text": "2 exams invoiced", "n": 3, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 110, "width": 1344, "height": 460})
    p.get_by_text("2 exams invoiced").first.click(); p.wait_for_timeout(1000)
    p.select_option("#lab-reception-doctor", label="Dr Paul Essomba, Doctor")
    p.set_viewport_size({"width": 1600, "height": 1300}); p.wait_for_timeout(800)
    print("FILLED", txt(p, 1500)[300:])
    shots.annotate(p, FIG / "recep-filled.png", [
        {"text": "Existing File", "exact": True, "n": 1, "position": "top"},
        {"text": "Change", "exact": True, "n": 2, "position": "left"},
        {"selector": "#lab-reception-doctor", "n": 3, "position": "right"},
        {"selector": "#lab-reception-exam", "n": 4, "position": "right"},
        {"text": "Remove", "n": 5, "position": "left", "index": 0},
        {"text": "CREATE REQUEST", "n": 6, "position": "top"},
    ], crop={"x": 256, "y": 100, "width": 1344, "height": 1100})
if "bench" in steps:
    go(p, "/dashboard/labo/paillasse")
    p.locator("article:has-text('Carine Ndzie')").get_by_text("Numération Formule Sanguine").click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1500}); p.wait_for_timeout(800)
    def fill(name, val, flag=None, note=None):
        row(name).locator("input[type=number]").fill(str(val)); p.wait_for_timeout(300)
        if flag: row(name).get_by_text(flag, exact=True).click()
        if note: row(name).locator("input[type=text]").fill(note)
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
    go(p, "/dashboard/labo/paillasse")
    p.locator("article:has-text('Samuel Biyick')").get_by_text("Acide urique").click()
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "bench-validated.png", [
        {"selector": "article:has-text('Samuel Biyick') button:has-text('Acide urique')", "n": 1, "position": "right"},
        {"text": "This result is validated", "n": 2, "position": "left", "outline": False},
        {"text": "Correct this result", "n": 3, "position": "top"},
    ], crop={"x": 300, "y": 190, "width": 1300, "height": 800})
if "histfig" in steps:
    go(p, "/dashboard/labo/history")
    shots.annotate(p, FIG / "history.png", [
        {"selector": "#lab-history-search", "n": 1, "position": "top"},
        {"selector": "#lab-history-status", "n": 2, "position": "top"},
        {"text": "Refresh", "exact": True, "n": 3, "position": "top"},
        {"text": "Yesterday,", "n": 4, "position": "right", "outline": False},
        {"text": "Show exams", "n": 5, "position": "bottom", "index": 0},
        {"text": "Full file PDF", "n": 6, "position": "bottom", "index": 0},
    ], crop={"x": 256, "y": 150, "width": 1344, "height": 520})
    p.get_by_text("Show exams").nth(1).click()
    p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "history-open.png", [
        {"text": "Hide exams", "n": 1, "position": "top", "index": 0},
        {"text": "View details", "n": 2, "position": "top", "index": 1},
        {"text": "Download PDF", "n": 3, "position": "top", "index": 1},
        {"text": "Correct this result", "n": 4, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 150, "width": 1344, "height": 700})
if "corr2" in steps:
    # demo data: correct the fasting glycaemia of Etoga Linda (adds a conclusion) so that its window stays short
    go(p, "/dashboard/labo/history")
    p.get_by_text("Show exams").nth(1).click(); p.wait_for_timeout(1500)
    p.get_by_text("Correct this result").nth(1).click(); p.wait_for_timeout(3500)
    p.set_viewport_size({"width": 1600, "height": 1800}); p.wait_for_timeout(800)
    p.fill("#lab-tech-note", "Fasting glucose within the usual range.")
    p.fill("textarea[id*=reason], input[id*=reason]", "Conclusion added after the doctor asked for one.")
    p.get_by_text("Save the correction").click(); p.wait_for_timeout(4000)
if "modal" in steps:
    go(p, "/dashboard/labo/history")
    p.get_by_text("Show exams").nth(1).click()
    p.wait_for_timeout(1500)
    p.get_by_text("View details").nth(2).click()
    p.wait_for_timeout(2500)
    p.set_viewport_size({"width": 1600, "height": 1500}); p.wait_for_timeout(800)
    print("MODAL", " | ".join(p.locator("[role=dialog]").first.inner_text().split())[:1200])
    shots.annotate(p, FIG / "result-modal.png", [
        {"text": "Result", "exact": True, "n": 1, "position": "top", "outline": False, "index": 0},
        {"text": "Reference Values", "n": 2, "position": "top"},
        {"text": "Interpretation", "exact": True, "n": 3, "position": "top"},
        {"text": "Conclusion / General notes", "n": 4, "position": "right", "outline": False},
        {"text": "Print", "exact": True, "n": 5, "position": "top"},
        {"selector": "[role=dialog] >> text=Correct this result", "n": 6, "position": "top"},
    ], crop="[role=dialog]")
if "pdf" in steps:
    import pypdfium2 as pdfium
    tok = p.evaluate("localStorage.getItem('token')")
    H = {"Authorization": "Bearer " + tok}
    r = p.request.get("http://127.0.0.1:8000" + "/labo/history/paginated?page=1&page_size=15&search=Etoga", headers=H)
    r = p.request.get("http://127.0.0.1:8000/labo/batch/cf1e07cd-099e-407b-8fd9-eb8ad51e2950/pdf", headers=H)
    print(r.status)
    Path("C:/Users/DD/AppData/Local/Temp/etoga.pdf").write_bytes(r.body())
if "api" in steps:
    print("LS", p.evaluate("Object.keys(localStorage)"))
    for k in p.evaluate("Object.keys(localStorage)"):
        v=p.evaluate("k=>localStorage.getItem(k)",k); print(k, (v or "")[:80])
shots.close(pw, br)
