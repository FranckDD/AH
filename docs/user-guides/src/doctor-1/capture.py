"""Capture script for guide doctor-1. Run from the repo root:
    python docs/user-guides/src/doctor-1/capture.py [step ...]
Steps (several perform real actions in the dev database, so run them once):
    signin dashboard appointments patients claim consult prescribe lab results profile offline
After the form steps (consult, prescribe, forms, result-detail, appt, book), run postcrop.py once
to crop the tall dialog shots into the figures the guide uses.
Demo data (created beforehand with the secretary and nurse demo accounts):
    Nadine Fouda 19293, Pierre Kamdem 19294, Linda Etoga 19295, Rosine Ateba 19296.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin", "dashboard"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-doctor1"


def go(p, route, settle=3000):
    """Open a route and wait for the green indicator so local data is loaded."""
    shots.goto(p, route)
    try:
        p.get_by_text("Connected").first.wait_for(timeout=30000)
    except Exception:
        pass
    p.wait_for_timeout(settle)


def dialog(p):
    return p.locator("[role=dialog]").first


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("medecin")
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
    shots.login(p, "medecin")

if "dashboard" in steps:
    go(p, "/medical/doctors")
    shots.annotate(p, FIG / "dashboard.png", [
        {"text": "Activity", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Connected", "n": 2, "position": "bottom"},
        {"text": "Patients awaiting review", "n": 3, "position": "right", "outline": False},
        {"text": "Take in charge", "n": 4, "position": "top"},
        {"text": "Quick access", "exact": True, "n": 5, "position": "right", "outline": False},
        {"text": "Statistics for the period", "n": 6, "position": "right", "outline": False},
    ])

if "appointments" in steps:
    go(p, "/medical/appointments")
    shots.annotate(p, FIG / "appointments-list.png", [
        {"selector": "#appt-search, input[placeholder*='Search']", "n": 1, "position": "bottom"},
        {"text": "Calendar view", "n": 2, "position": "bottom"},
        {"text": "Book Appointment", "n": 3, "position": "left"},
    ])

if "patients" in steps:
    go(p, "/medical/patients")
    shots.annotate(p, FIG / "patients-list.png", [
        {"selector": "#patient-search", "n": 1, "position": "bottom"},
        {"text": "All Patients", "n": 2, "position": "top"},
        {"text": "Voir Dossier", "n": 3, "position": "left", "index": 0},
    ])

if "consult" in steps:
    go(p, "/medical/patients/19294")
    shots.annotate(p, FIG / "dossier.png", [
        {"text": "Pierre Kamdem", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Export PDF", "n": 2, "position": "left"},
        {"text": "Blood Pressure", "n": 3, "position": "top", "outline": False},
        {"text": "Known Allergies", "n": 4, "position": "top", "outline": False},
        {"text": "Exams", "exact": True, "n": 5, "position": "top"},
        {"text": "New consultation", "n": 6, "position": "left"},
        {"text": "Modifier", "exact": True, "n": 7, "position": "bottom"},
        {"text": "Prescrire", "exact": True, "n": 8, "position": "bottom"},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 800})
    p.get_by_text("Modifier", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.set_viewport_size({"width": 1600, "height": 2200})
    p.wait_for_timeout(800)
    p.fill("#mr-history", "Asthma in childhood, no treatment for ten years.")
    p.fill("#mr-symptoms", "Cough and chest tightness for one week. No fever. Wheeze on both sides.")
    p.fill("#mr-diagnosis", "Acute bronchitis")
    p.fill("#mr-treatment", "Azithromycin 500 mg once a day for 3 days, rest and plenty of fluids.")
    p.fill("#mr-notes", "Review in one week if the cough continues. Penicillin allergy checked.")
    shots.annotate(p, FIG / "consult-form.png", [
        {"selector": "#mr-severity", "n": 1, "position": "right"},
        {"selector": "#mr-bp", "n": 2, "position": "top"},
        {"selector": "#mr-history", "n": 3, "position": "right"},
        {"selector": "#mr-symptoms", "n": 4, "position": "right"},
        {"selector": "#mr-diagnosis", "n": 5, "position": "top"},
        {"selector": "#mr-treatment", "n": 6, "position": "top"},
        {"selector": "#mr-notes", "n": 7, "position": "right"},
        {"text": "Save", "exact": True, "n": 8, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3500)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(800)
    (HERE / "_consult.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.shot(p, FIG / "_consult-after.png")

if "prescribe" in steps:
    go(p, "/medical/patients/19294")
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.get_by_text("Prescrire", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.fill("#presc-medication", "Azithromycin 500 mg tablets")
    p.fill("#presc-dosage", "500 mg")
    p.fill("#presc-frequency", "1 time a day")
    p.fill("#presc-duration", "3 days")
    p.fill("#presc-end", "2026-10-28")
    p.fill("#presc-notes", "Take after a meal.")
    shots.annotate(p, FIG / "presc-form.png", [
        {"selector": "#is_lab_order", "n": 1, "position": "right"},
        {"selector": "#presc-medication", "n": 2, "position": "top"},
        {"selector": "#presc-dosage", "n": 3, "position": "top"},
        {"selector": "#presc-duration", "n": 4, "position": "top"},
        {"selector": "#presc-start", "n": 5, "position": "top"},
        {"selector": "#presc-end", "n": 6, "position": "top"},
        {"text": "Save", "exact": True, "n": 7, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3000)
    # lab order from the same consultation
    p.get_by_text("Prescrire", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.check("#is_lab_order")
    p.wait_for_timeout(1500)
    p.fill("#presc-exam-filter", "Num")
    p.wait_for_timeout(500)
    shots.shot(p, FIG / "_lab-filter.png")
    (HERE / "_lab-exams.txt").write_text(dialog(p).inner_text(), encoding="utf-8")
    p.fill("#presc-exam-filter", "")
    p.get_by_text("Numération Formule Sanguine", exact=True).first.check() if False else None
    p.locator("label", has_text="Numération Formule Sanguine").first.locator("input").check()
    p.fill("#presc-exam-filter", "CRP")
    p.locator("label", has_text="CRP").first.locator("input").check()
    p.fill("#presc-exam-filter", "")
    p.fill("#presc-notes", "Chest infection suspected.")
    shots.annotate(p, FIG / "lab-order-form.png", [
        {"selector": "#is_lab_order", "n": 1, "position": "right"},
        {"selector": "#presc-exam-filter", "n": 2, "position": "top"},
        {"text": "Numération Formule Sanguine", "exact": True, "n": 3, "position": "left"},
        {"text": "Save", "exact": True, "n": 4, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/medical/prescriptions")
    p.fill("#presc-search", "Kamdem")
    p.wait_for_timeout(2500)
    (HERE / "_presc-list.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.annotate(p, FIG / "presc-list.png", [
        {"text": "New Prescription", "n": 1, "position": "left"},
        {"selector": "#presc-search", "n": 2, "position": "bottom"},
        {"text": "Lab order", "exact": True, "n": 3, "position": "left", "index": 0},
        {"text": "Edit", "exact": True, "n": 4, "position": "top", "index": 0},
    ])

if "forms" in steps:
    # Re-shoots the two prescription forms without saving anything (Cancel at the end).
    go(p, "/medical/patients/19294")
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.get_by_text("Prescrire", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.fill("#presc-medication", "Azithromycin 500 mg tablets")
    p.fill("#presc-dosage", "500 mg")
    p.fill("#presc-frequency", "1 time a day")
    p.fill("#presc-duration", "3 days")
    p.fill("#presc-end", "2026-10-28")
    p.fill("#presc-notes", "Take after a meal.")
    shots.annotate(p, FIG / "presc-form.png", [
        {"selector": "#is_lab_order", "n": 1, "position": "top"},
        {"selector": "#presc-medication", "n": 2, "position": "top"},
        {"selector": "#presc-dosage", "n": 3, "position": "top"},
        {"selector": "#presc-duration", "n": 4, "position": "top"},
        {"selector": "#presc-start", "n": 5, "position": "top"},
        {"selector": "#presc-end", "n": 6, "position": "top"},
        {"text": "Save", "exact": True, "n": 7, "position": "top"},
    ], crop="[role=dialog]")
    p.check("#is_lab_order")
    p.wait_for_timeout(1000)
    p.fill("#presc-exam-filter", "Num")
    p.locator("label", has_text="Numération Formule Sanguine").first.locator("input").check()
    p.fill("#presc-notes", "Chest infection suspected.")
    p.fill("#presc-exam-filter", "Prot")
    p.locator("label", has_text="CRP").first.locator("input").check()
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "lab-order-form.png", [
        {"selector": "#is_lab_order", "n": 1, "position": "top"},
        {"selector": "#presc-exam-filter", "n": 2, "position": "top"},
        {"selector": "label:has-text('CRP')", "n": 3, "position": "right"},
        {"text": "Save", "exact": True, "n": 4, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Cancel", exact=True).click()
    p.set_viewport_size({"width": 1600, "height": 1000})

if "results-pre" in steps:
    go(p, "/medical/lab-results")
    p.fill("#lab-results-search", "Kamdem")
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "results-empty.png", [
        {"text": "No completed exam found.", "exact": True, "n": 1, "position": "left", "outline": False},
        {"text": "Exams in progress are only visible to the laboratory.", "exact": True, "n": 2, "position": "left", "outline": False},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 640})
    print("PRE:", " | ".join(p.inner_text("body").split())[-300:])

if "results" in steps:
    go(p, "/medical/lab-results")
    p.fill("#lab-results-search", "Kamdem")
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "results-list.png", [
        {"selector": "#lab-results-search", "n": 1, "position": "bottom"},
        {"text": "Refresh", "exact": True, "n": 2, "position": "bottom"},
        {"text": "View details", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Download PDF", "exact": True, "n": 4, "position": "top", "index": 0},
    ])
    p.get_by_text("View details", exact=True).first.click()
    p.wait_for_timeout(2500)
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.wait_for_timeout(800)
    shots.shot(p, FIG / "_result-detail.png")
    (HERE / "_result-detail.txt").write_text(p.inner_text("body"), encoding="utf-8")
    p.set_viewport_size({"width": 1600, "height": 1000})

if "result-detail" in steps:
    go(p, "/medical/lab-results")
    p.fill("#lab-results-search", "Kamdem")
    p.wait_for_timeout(3000)
    p.get_by_text("View details", exact=True).nth(1).click()
    p.wait_for_timeout(2500)
    p.set_viewport_size({"width": 1600, "height": 1400})
    p.wait_for_timeout(800)
    shots.annotate(p, FIG / "result-detail.png", [
        {"text": "Biological Results", "exact": True, "n": 1, "position": "top", "outline": False},
        {"text": "Reference Values", "exact": True, "n": 2, "position": "top", "outline": False},
        {"text": "Interpretation", "exact": True, "n": 3, "position": "top", "outline": False},
        {"text": "Print", "exact": True, "n": 4, "position": "top"},
    ], crop="[role=dialog]")
    p.set_viewport_size({"width": 1600, "height": 1000})

if "dossier-tabs" in steps:
    go(p, "/medical/patients/19294")
    p.get_by_role("tab", name="Exams").click()
    p.wait_for_timeout(2000)
    shots.annotate(p, FIG / "dossier-exams.png", [
        {"text": "Exams", "exact": True, "n": 1, "position": "top"},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 1000})
    p.get_by_role("tab", name="Treatments").click()
    p.wait_for_timeout(2000)
    (HERE / "_treatments.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.annotate(p, FIG / "dossier-treatments.png", [
        {"text": "Treatments", "exact": True, "n": 1, "position": "top"},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 1000})

if "appt" in steps:
    go(p, "/medical/appointments")
    p.get_by_text("Calendar view").click()
    p.wait_for_timeout(2000)
    p.get_by_text("15:00 Linda").first.click()
    p.wait_for_timeout(2000)
    shots.annotate(p, FIG / "appt-day-panel.png", [
        {"text": "Start consultation", "exact": True, "n": 1, "position": "top"},
        {"text": "Complete", "exact": True, "n": 2, "position": "top"},
        {"text": "View record", "exact": True, "n": 3, "position": "bottom"},
        {"text": "Edit", "exact": True, "n": 4, "position": "bottom"},
        {"text": "Reject", "exact": True, "n": 5, "position": "bottom"},
    ], crop={"x": 925, "y": 170, "width": 680, "height": 260})
    p.get_by_text("Start consultation", exact=True).first.click()
    p.wait_for_timeout(4000)
    print("URL", p.url, "dialogs", p.locator("[role=dialog]").count())
    p.get_by_text("New consultation", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.set_viewport_size({"width": 1600, "height": 2200})
    p.wait_for_timeout(1000)
    p.select_option("#mr-motif", "appointment")
    p.select_option("#mr-severity", "low")
    p.fill("#mr-bp", "110/70")
    p.fill("#mr-temperature", "36.8")
    p.fill("#mr-weight", "59")
    p.fill("#mr-height", "162")
    p.fill("#mr-symptoms", "Tiredness has improved. No more joint pain.")
    p.fill("#mr-diagnosis", "Anaemia improving on iron")
    p.fill("#mr-treatment", "Continue iron for one more month.")
    p.fill("#mr-notes", "Check haemoglobin at the next visit.")
    shots.annotate(p, FIG / "newconsult-form.png", [
        {"selector": "#mr-patient-code", "n": 1, "position": "right"},
        {"selector": "#mr-motif", "n": 2, "position": "top"},
        {"selector": "#mr-bp", "n": 3, "position": "top"},
        {"selector": "#mr-diagnosis", "n": 4, "position": "top"},
        {"text": "Refer to doctor", "exact": True, "n": 5, "position": "right"},
        {"text": "Save", "exact": True, "n": 6, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(4000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(800)
    shots.shot(p, FIG / "_after-new.png")
    (HERE / "_after-new.txt").write_text(p.inner_text("body"), encoding="utf-8")

if "complete" in steps:
    go(p, "/medical/appointments")
    # (the real run clicked Complete on Linda Etoga's row; on a second run only the figure is retaken)
    shots.annotate(p, FIG / "appointments-done.png", [
        {"text": "Completed", "exact": True, "n": 1, "position": "top", "index": 1},
        {"text": "Pending", "exact": True, "n": 2, "position": "top", "index": 1},
    ], crop={"x": 256, "y": 80, "width": 1344, "height": 640})

if "profile" in steps:
    go(p, "/medical/doctors")
    p.click("[aria-label='My Account']")
    p.wait_for_timeout(1500)
    p.locator("[class*='max-w-md'] input[type=tel]").fill("+237677010099")
    shots.annotate(p, FIG / "account-profile.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Password", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": "[class*='max-w-md'] input[type=tel]", "n": 3, "position": "right"},
        {"selector": "[class*='max-w-md'] button[type=submit]", "n": 4, "position": "left"},
    ], crop="[class*='max-w-md']")
    p.locator("[class*='max-w-md'] button[type=submit]").click()
    p.wait_for_timeout(2500)
    (HERE / "_profile-saved.txt").write_text(p.inner_text("body"), encoding="utf-8")
    p.get_by_text("Password", exact=True).first.click()
    p.wait_for_timeout(800)
    inputs = p.locator("[class*='max-w-md'] input[type=password]")
    inputs.nth(0).fill("wrong-old-password")
    inputs.nth(1).fill("Demo-Pass-2031")
    inputs.nth(2).fill("Demo-Pass-2031")
    p.locator("[class*='max-w-md'] button[type=submit]").click()
    p.wait_for_timeout(2500)
    shots.annotate(p, FIG / "account-password.png", [
        {"selector": "[class*='max-w-md'] input[type=password] >> nth=0", "n": 1, "position": "right"},
        {"selector": "[class*='max-w-md'] input[type=password] >> nth=1", "n": 2, "position": "right"},
        {"selector": "[class*='max-w-md'] input[type=password] >> nth=2", "n": 3, "position": "right"},
        {"selector": "[class*='max-w-md'] button[type=submit]", "n": 4, "position": "left"},
    ], crop="[class*='max-w-md']")
    (HERE / "_password-wrong.txt").write_text(p.inner_text("body"), encoding="utf-8")

if "offline" in steps:
    # 1. sign in online with the persistent profile so the app and its local data are cached
    for route in ("/medical/doctors", "/medical/appointments", "/medical/patients/19293", "/medical/prescriptions", "/medical/lab-results"):
        go(p, route, settle=5000)
    shots.close(pw, br)
    # 2. same profile, network cut
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/medical/doctors")
    p.get_by_text("Offline").first.wait_for(timeout=60000)
    shots.wait_ready(p)
    p.wait_for_timeout(3000)
    shots.shot(p, FIG / "_off-dashboard.png")
    (HERE / "_off-dashboard.txt").write_text(p.inner_text("body"), encoding="utf-8")
    p.goto(shots.BASE_URL + "/medical/appointments")
    shots.wait_ready(p)
    p.wait_for_timeout(3000)
    (HERE / "_off-appointments.txt").write_text(p.inner_text("body"), encoding="utf-8")
    p.goto(shots.BASE_URL + "/medical/patients/19293")
    shots.wait_ready(p)
    p.wait_for_timeout(4000)
    shots.shot(p, FIG / "_off-dossier.png")
    p.get_by_text("New consultation", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.set_viewport_size({"width": 1600, "height": 2200})
    p.select_option("#mr-motif", "consultation")
    p.fill("#mr-bp", "130/85")
    p.fill("#mr-temperature", "37.0")
    p.fill("#mr-symptoms", "Fever gone, headache much better.")
    p.fill("#mr-diagnosis", "Viral fever, resolving")
    p.fill("#mr-notes", "Entered while the connection was down.")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(800)
    (HERE / "_off-saved.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.annotate(p, FIG / "offline-saved.png", [
        {"selector": "text=/Offline|Sending error/ >> visible=true", "n": 1, "position": "bottom"},
        {"text": "Viral fever, resolving", "exact": True, "n": 2, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 760})
    shots.close(pw, br)
    # 3. network back: the entry is sent
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
    shots.goto(p, "/medical/patients/19293")
    p.get_by_text("Connected").first.wait_for(timeout=60000)
    p.wait_for_timeout(8000)
    shots.annotate(p, FIG / "online-again.png", [
        {"selector": "text=Connected >> visible=true", "n": 1, "position": "bottom"},
    ], crop={"x": 700, "y": 0, "width": 900, "height": 80})

if "restricted" in steps:
    go(p, "/medical/patients/111")
    p.get_by_role("tab", name="Toxicology Follow-up").click()
    p.wait_for_timeout(2000)
    (HERE / "_restricted.txt").write_text(p.inner_text("body"), encoding="utf-8")
    shots.annotate(p, FIG / "dossier-restricted.png", [
        {"text": "TOXICOLOGIE", "exact": True, "n": 1, "position": "bottom"},
        {"text": "Toxicology Follow-up", "exact": True, "n": 2, "position": "top"},
        {"text": "Ce domaine relève d'un autre service, non affiché ici.", "exact": True, "n": 3, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 760})

if "consultations" in steps:
    go(p, "/medical/medical-records")
    p.fill("#mr-search", "Etoga")
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "consultations-list.png", [
        {"text": "New consultation", "exact": True, "n": 1, "position": "left"},
        {"selector": "#mr-search", "n": 2, "position": "bottom"},
        {"selector": "#mr-motif-filter", "n": 3, "position": "bottom"},
        {"text": "Edit", "exact": True, "n": 4, "position": "top", "index": 0},
        {"text": "Consultation closed: a more recent consultation exists", "exact": True, "n": 5, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
    (HERE / "_consultations.txt").write_text(p.inner_text("body"), encoding="utf-8")

if "dossier-fig" in steps:
    go(p, "/medical/patients/19294")
    shots.annotate(p, FIG / "dossier.png", [
        {"text": "Pierre Kamdem", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Export PDF", "n": 2, "position": "left"},
        {"text": "Blood Pressure", "n": 3, "position": "top", "outline": False},
        {"text": "Known Allergies", "n": 4, "position": "top", "outline": False},
        {"text": "Exams", "exact": True, "n": 5, "position": "top"},
        {"text": "New consultation", "exact": True, "n": 6, "position": "left"},
        {"text": "Modifier", "exact": True, "n": 7, "position": "bottom"},
        {"text": "Prescrire", "exact": True, "n": 8, "position": "bottom"},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 1000})

if "book" in steps:
    go(p, "/medical/appointments")
    p.get_by_text("Book Appointment").click()
    p.wait_for_timeout(2000)
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.fill("#appt-patient-code", "AH2-750903KX")
    p.keyboard.press("Tab")
    p.wait_for_timeout(2500)
    p.select_option("#appt-specialty", "Généraliste")
    p.select_option("#appt-doctor", label="Dr Paul Essomba")
    p.fill("#appt-date", "2026-11-02")
    p.select_option("#appt-time", "09:00")
    p.fill("#appt-reason", "Review of bronchitis")
    shots.annotate(p, FIG / "appt-form.png", [
        {"selector": "#appt-patient-code", "n": 1, "position": "right"},
        {"selector": "#appt-doctor", "n": 2, "position": "top"},
        {"selector": "#appt-date", "n": 3, "position": "top"},
        {"selector": "#appt-time", "n": 4, "position": "top"},
        {"text": "Save", "exact": True, "n": 5, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(500)
    (HERE / "_booked.txt").write_text(p.inner_text("body"), encoding="utf-8")

if "reject" in steps:
    go(p, "/medical/appointments")
    p.on("dialog", lambda d: (print("DIALOG:", d.message), d.accept()))
    row = p.locator("tr, li, div", has_text="Review of bronchitis").last
    p.get_by_text("Reject", exact=True).first.click()
    p.wait_for_timeout(3000)
    (HERE / "_rejected.txt").write_text(p.inner_text("body"), encoding="utf-8")

if "claim" in steps:
    go(p, "/medical/doctors")
    p.get_by_text("Take in charge").first.click()
    p.wait_for_timeout(4000)
    print("after claim:", p.url, "dialogs:", p.locator("[role=dialog]").count())
    shots.annotate(p, FIG / "claimed.png", [
        {"text": "Pris en charge", "exact": True, "n": 1, "position": "right"},
        {"text": "Modifier", "exact": True, "n": 2, "position": "bottom"},
        {"text": "Prescrire", "exact": True, "n": 3, "position": "bottom"},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 1000})

if any(s != "signin" for s in steps):
    shots.close(pw, br)
