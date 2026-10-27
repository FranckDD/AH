"""Retake of the New invoice figures after the barcode scan feature (27 Oct 2026). Nothing is saved."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from retake_lib import *
FIG = HERE / "figures"
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-bc"
pw, br, p = shots.launch(width=1600, height=1100, profile_dir=PROFILE)
fresh(p); shots.login(p, "secretaire")
dlg = lambda: p.locator("[role=dialog]").first
go(p, "/secretariat/caisse")
p.get_by_role("button", name="New Invoice").first.click(); p.wait_for_timeout(1500)
p.locator("#inv-patient-search").press_sequentially("Amara", delay=80); p.wait_for_timeout(2500)
shots.annotate(p, FIG / "invoice-patient.png", [
    {"selector": "#inv-patient-search", "n": 1},
    {"selector": "#inv-patient-label", "n": 2, "position": "right"},
], crop={"x": 140, "y": 30, "width": 1120, "height": 330})
dlg().get_by_text("Amara Njoh").first.click(); p.wait_for_timeout(1000)
# scan figure
p.keyboard.type("10000000", delay=20); p.keyboard.press("Enter"); p.wait_for_timeout(1500)
shots.annotate(p, FIG / "invoice-scan.png", [
    {"selector": "#inv-scan", "n": 1, "position": "top"},
    {"selector": "#line-1-price", "n": 2, "position": "right"},
    {"text": "Selected product", "exact": True, "n": 3, "position": "left", "outline": False},
    {"selector": "[aria-label='Maximize window']", "n": 4, "position": "bottom"},
], crop="[role=dialog]")
# lines figure: remove the pharmacy line, rebuild as before
p.keyboard.press("Escape"); p.wait_for_timeout(800)
p.reload(); p.wait_for_timeout(3000)
p.get_by_role("button", name="New Invoice").first.click(); p.wait_for_timeout(1500)
p.locator("#inv-patient-search").press_sequentially("Amara", delay=80); p.wait_for_timeout(2500)
dlg().get_by_text("Amara Njoh").first.click(); p.wait_for_timeout(1000)
dlg().get_by_role("button", name="Lab Exam").click(); p.wait_for_timeout(800)
dlg().locator("input[placeholder^='Search a lab exam']").press_sequentially("Acide", delay=80); p.wait_for_timeout(1200)
dlg().get_by_text("Acide urique").first.click(); p.wait_for_timeout(800)
dlg().get_by_role("button", name="Free-form Service").click(); p.wait_for_timeout(800)
free = dlg().locator("#line-2-qty").locator("xpath=ancestor::*[.//input[@type='text']][1]").locator("input[type=text]").first
free.fill("Medical certificate"); p.fill("#line-2-price", "2000"); p.wait_for_timeout(600)
p.locator("#line-1-price").scroll_into_view_if_needed()
shots.annotate(p, FIG / "invoice-lines.png", [
    {"selector": "[role=dialog] button:has-text('Pharmacy')", "n": 3, "position": "left"},
    {"selector": "#line-1-price", "n": 4},
    {"selector": "#line-2-price", "n": 5, "position": "bottom"},
    {"text": "Invoice total", "n": 6, "position": "left", "outline": False},
])
p.select_option("#inv-category", label="Laboratory"); p.select_option("#inv-method", label="Cash")
p.fill("#inv-advance", "10000"); p.fill("#inv-note", "Uric acid test and certificate")
p.locator("#inv-note").scroll_into_view_if_needed()
shots.annotate(p, FIG / "invoice-payment.png", [
    {"selector": "#inv-category", "n": 7}, {"selector": "#inv-method", "n": 8, "position": "top"},
    {"selector": "#inv-advance", "n": 9, "position": "top"}, {"text": "Save Transaction", "n": 10, "position": "top"},
])
p.keyboard.press("Escape")
shots.close(pw, br)
