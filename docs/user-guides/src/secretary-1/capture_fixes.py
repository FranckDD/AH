"""Re-capture of the figures changed by the 2026-10-26 defect fixes.
    python docs/user-guides/src/secretary-1/capture_fixes.py [search settle]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["search", "settle"]
pw, browser, p = shots.launch(width=1600)
shots.login(p, "secretaire")
dlg = lambda: p.locator("[role=dialog]").first

if "search" in steps:
    shots.goto(p, "/secretariat/patients")
    p.locator("input[placeholder^='Search by name']").press_sequentially("Njoh", delay=80)
    p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "patient-search.png", [
        {"selector": "input[placeholder^='Search by name']", "n": 1, "position": "right"},
        {"text": "All Patients", "n": 2, "position": "bottom"},
        {"text": "Modifier", "exact": True, "n": 3, "position": "left"},
    ], crop={"x": 280, "y": 80, "width": 1310, "height": 420})

if "settle" in steps:
    shots.goto(p, "/secretariat/caisse")
    p.get_by_role("button", name="New Invoice").first.click()
    p.wait_for_timeout(1500)
    p.locator("#inv-patient-search").press_sequentially("Amara", delay=80)
    p.wait_for_timeout(2500)
    dlg().get_by_text("Amara Njoh").first.click()
    p.wait_for_timeout(800)
    dlg().get_by_role("button", name="Lab Exam").click()
    p.wait_for_timeout(800)
    dlg().locator("input[placeholder^='Search a lab exam']").press_sequentially("Acide", delay=80)
    p.wait_for_timeout(1200)
    dlg().get_by_text("Acide urique").first.click()
    p.select_option("#inv-category", label="Laboratory")
    p.select_option("#inv-method", label="Cash")
    p.fill("#inv-advance", "3000")
    dlg().get_by_role("button", name="Save Transaction").click()
    p.wait_for_timeout(4000)
    shots.goto(p, "/secretariat/caisse")
    ROW = "tr:has-text('Amara Njoh') >> nth=0"
    shots.annotate(p, FIG / "cash-list.png", [
        {"selector": ROW + " >> [title='Add Payment']", "n": 1, "position": "top"},
        {"selector": ROW + " >> [title='Settle']", "n": 2, "position": "top"},
        {"selector": ROW + " >> [title='Reprint ticket']", "n": 3, "position": "top"},
        {"selector": ROW + " >> td >> nth=5", "n": 4, "position": "bottom", "outline": True},
    ], crop="main")
    p.locator(ROW + " >> [title='Settle']").click()
    p.wait_for_timeout(1200)
    (HERE / "_settle.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.annotate(p, FIG / "settle.png", [
        {"text": "Balance Due :", "n": 1, "position": "left", "outline": False},
        {"selector": "#installment-amount", "n": 2},
        {"selector": "#installment-method", "n": 3},
        {"text": "Confirm settlement", "exact": True, "n": 4, "position": "left"},
    ], crop={"x": 350, "y": 250, "width": 900, "height": 400})
    p.get_by_role("button", name="Confirm settlement").click()
    p.wait_for_timeout(3000)
    (HERE / "_settled.txt").write_text(p.inner_text("body"), encoding="utf-8")
shots.close(pw, browser)
