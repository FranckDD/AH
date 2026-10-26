"""Capture script for guide nurse-1. Run from the repo root:
    python docs/user-guides/src/nurse-1/capture.py [step ...]
Several steps perform real actions in the dev database, so run them once:
    signin dashboard patients refer book appt hosp results bell profile offline
The new-patient figures (newpat-form, newpat-code, vitals-form) were taken during the real
registration of the demo patients Cyrille Mbonda and Odile Fotso (code kept in this docstring).
Demo data (fake): Mireille Tchoua AH2-910314TX (19299, nurse consultation referred to Dr Paul Essomba),
Cyrille Mbonda AH2-840702MX (nursing note, not referred), Odile Fotso AH2-781123FX (19301, shared queue).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import shots  # noqa: E402

FIG = HERE / "figures"
steps = sys.argv[1:] or ["signin", "dashboard"]
PROFILE = shots.ROOT / ".superpowers/sdd/2026-10-25-user-guides/chrome-profile-nurse1"


def go(p, route, settle=3500):
    shots.goto(p, route)
    try:
        p.get_by_text("Connected").first.wait_for(timeout=30000)
    except Exception:
        pass
    p.wait_for_timeout(settle)


def dialog(p):
    return p.locator("[role=dialog]").first


def txt(p, name, loc=None):
    t = (loc or p).inner_text("body") if loc is None else loc.inner_text()
    (HERE / f"_{name}.txt").write_text(t, encoding="utf-8")


def open_form(p, name):
    go(p, "/medical/patients")
    p.fill("#patient-search", name)
    p.wait_for_timeout(2500)
    p.get_by_text("Voir Dossier").first.click()
    p.wait_for_timeout(4000)


if "signin" in steps:
    pw, br, p = shots.launch(width=1600)
    p.goto(shots.BASE_URL + "/login")
    shots.wait_ready(p)
    acc = shots.account("nurse")
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
    shots.login(p, "nurse")

if "dashboard" in steps:
    go(p, "/medical/doctors")
    shots.annotate(p, FIG / "dashboard.png", [
        {"text": "Activity", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Connected", "n": 2, "position": "bottom"},
        {"text": "Patients awaiting review", "n": 3, "position": "right", "outline": False},
        {"text": "Quick access", "exact": True, "n": 4, "position": "right", "outline": False},
        {"text": "Statistics for the period", "n": 5, "position": "right", "outline": False},
    ])

if "patients" in steps:
    go(p, "/medical/patients")
    shots.annotate(p, FIG / "patients-list.png", [
        {"text": "Ajouter un patient", "n": 1, "position": "left"},
        {"selector": "#patient-search", "n": 2, "position": "bottom"},
        {"text": "All Patients", "n": 3, "position": "top"},
        {"text": "Voir Dossier", "n": 4, "position": "left", "index": 0},
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 560})
    go(p, "/medical/patients/19301")
    shots.annotate(p, FIG / "dossier.png", [
        {"text": "Odile Fotso", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Blood Pressure", "n": 2, "position": "top", "outline": False},
        {"text": "Known Allergies", "n": 3, "position": "top", "outline": False},
        {"text": "New consultation", "exact": True, "n": 4, "position": "left"},
        {"text": "Modifier", "exact": True, "n": 5, "position": "bottom"},
        {"text": "Prescrire", "exact": True, "n": 6, "position": "bottom"},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 800})

if "refer" in steps:
    # form from a file, referral switched on with a named doctor (nothing saved here)
    open_form(p, "Tchoua")
    p.get_by_text("New consultation", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.set_viewport_size({"width": 1600, "height": 2300})
    p.wait_for_timeout(800)
    dialog(p).locator("input[type=checkbox]").first.check(force=True)
    p.wait_for_timeout(500)
    p.select_option("#mr-assign", label="Dr Paul Essomba")
    shots.annotate(p, FIG / "refer-named.png", [
        {"text": "Refer to doctor", "exact": True, "n": 1, "position": "right"},
        {"selector": "#mr-assign", "n": 2, "position": "right"},
        {"text": "Save", "exact": True, "n": 3, "position": "top"},
    ], crop={"x": 256, "y": 1560, "width": 1100, "height": 560})
    dialog(p).locator("input[type=checkbox]").first.uncheck(force=True)
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "refer-off.png", [
        {"text": "Refer to doctor", "exact": True, "n": 1, "position": "right"},
    ], crop={"x": 256, "y": 1560, "width": 1100, "height": 560})
    dialog(p).get_by_text("Cancel", exact=True).click()
    p.set_viewport_size({"width": 1600, "height": 1000})

if "newpat" in steps:
    # Registers a real demo patient (Brice Eyenga) and enters the first measurements.
    go(p, "/medical/patients")
    p.get_by_text("Ajouter un patient").click()
    p.wait_for_timeout(1500)
    p.fill("#patient-first-name", "Brice")
    p.fill("#patient-last-name", "Eyenga")
    p.fill("#patient-birth-date", "1969-05-09")
    p.select_option("#patient-gender", index=1)
    p.fill("#patient-phone", "+237677010010")
    p.fill("#patient-residence", "Douala")
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.wait_for_timeout(600)
    shots.annotate(p, FIG / "newpat-form.png", [
        {"selector": "#patient-first-name", "n": 1, "position": "right"},
        {"selector": "#patient-birth-date", "n": 2, "position": "right"},
        {"selector": "#patient-gender", "n": 3, "position": "right"},
        {"selector": "#patient-phone", "n": 4, "position": "right"},
        {"text": "Créer", "exact": True, "n": 5, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Créer").click()
    p.wait_for_timeout(4000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(500)
    shots.annotate(p, FIG / "newpat-code.png", [
        {"text": "Patient code", "exact": True, "n": 1, "position": "right", "outline": False},
        {"text": "Copy", "exact": True, "n": 2, "position": "right"},
        {"text": "OK", "exact": True, "n": 3, "position": "left"},
    ], crop={"x": 380, "y": 120, "width": 840, "height": 560})
    p.get_by_text("OK", exact=True).click()
    p.wait_for_timeout(2500)
    p.set_viewport_size({"width": 1600, "height": 2300})
    p.wait_for_timeout(800)
    p.select_option("#mr-motif", "consultation")
    p.select_option("#mr-severity", "medium")
    p.fill("#mr-bp", "146/92")
    p.fill("#mr-temperature", "36.8")
    p.fill("#mr-weight", "88")
    p.fill("#mr-height", "172")
    p.fill("#mr-allergies", "Penicillin")
    p.fill("#mr-symptoms", "Headache in the morning for one week. Dizzy when standing up.")
    p.fill("#mr-notes", "Blood pressure checked twice, same result. Known smoker.")
    shots.annotate(p, FIG / "vitals-form.png", [
        {"selector": "#mr-motif", "n": 1, "position": "right"},
        {"selector": "#mr-bp", "n": 2, "position": "top"},
        {"selector": "#mr-temperature", "n": 3, "position": "top"},
        {"selector": "#mr-allergies", "n": 4, "position": "right"},
        {"text": "Refer to doctor", "exact": True, "n": 5, "position": "right"},
        {"selector": "#mr-assign", "n": 6, "position": "right"},
        {"text": "Save", "exact": True, "n": 7, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "saved-toast.png", [
        {"text": "Measurements saved.", "n": 1, "position": "left"},
    ], crop={"x": 900, "y": 60, "width": 700, "height": 140})

if "book" in steps:
    go(p, "/medical/appointments")
    p.get_by_text("Book Appointment").click()
    p.wait_for_timeout(2000)
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.fill("#appt-patient-code", "AH2-910314TX")
    p.keyboard.press("Tab")
    p.wait_for_timeout(2500)
    p.select_option("#appt-specialty", "Généraliste")
    p.select_option("#appt-doctor", label="Dr Paul Essomba")
    p.fill("#appt-date", "2026-11-03")
    p.select_option("#appt-time", "10:00")
    p.fill("#appt-reason", "Review of back pain")
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
    p.fill("#appt-search", "Tchoua") if p.locator("#appt-search").count() else None
    p.wait_for_timeout(2500)
    txt(p, "booked")
    shots.annotate(p, FIG / "appointments-list.png", [
        {"selector": "#appt-search, input[placeholder*='Search']", "n": 1, "position": "bottom"},
        {"text": "Calendar view", "n": 2, "position": "bottom"},
        {"text": "Book Appointment", "n": 3, "position": "left"},
        {"text": "Start consultation", "exact": True, "n": 4, "position": "top", "index": 0},
    ])

if "hosp" in steps:
    go(p, "/medical/patients/19300")
    p.get_by_role("tab", name="Hospitalization").click()
    p.wait_for_timeout(1500)
    p.get_by_role("button", name="Admit", exact=True).click()
    p.wait_for_timeout(800)
    p.fill("#hosp-reason", "Dehydration after three days of vomiting. Drip and observation.")
    shots.annotate(p, FIG / "admit-form.png", [
        {"text": "Admit", "exact": True, "n": 1, "position": "left"},
        {"selector": "#hosp-reason", "n": 2, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 3, "position": "bottom"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 470})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    p.set_viewport_size({"width": 1600, "height": 1200})
    p.get_by_role("button", name="Update status", exact=True).first.click()
    p.wait_for_timeout(800)
    p.select_option("#hosp-status", "STABLE")
    p.fill("#hosp-status-note", "Drip running. Temperature 37.0, blood pressure 118/74. Drinking small amounts.")
    shots.annotate(p, FIG / "status-form.png", [
        {"text": "Update status", "exact": True, "n": 1, "position": "left", "index": 0},
        {"selector": "#hosp-status", "n": 2, "position": "right"},
        {"selector": "#hosp-status-note", "n": 3, "position": "right"},
        {"text": "Confirm", "exact": True, "n": 4, "position": "right"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 730})
    p.get_by_role("button", name="Confirm", exact=True).click()
    p.wait_for_timeout(2500)
    txt(p, "hosp-after")
    shots.annotate(p, FIG / "hosp-card.png", [
        {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
        {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "right", "outline": False},
        {"text": "Discharge", "exact": True, "n": 3, "position": "top"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 560})
    go(p, "/medical/hospitalizations")
    shots.annotate(p, FIG / "hosp-list.png", [
        {"text": "Current status", "exact": True, "n": 1, "position": "top", "outline": False},
        {"text": "View record", "exact": True, "n": 2, "position": "left", "index": 0},
    ], crop={"x": 256, "y": 60, "width": 1344, "height": 560})

if "hosp-fig" in steps:
    go(p, "/medical/patients/19300")
    p.get_by_role("tab", name="Hospitalization").click()
    p.wait_for_timeout(1500)
    shots.annotate(p, FIG / "hosp-card.png", [
        {"text": "Latest update", "exact": True, "n": 1, "position": "left", "outline": False},
        {"text": "Current stay's clinical updates", "exact": True, "n": 2, "position": "top", "outline": False},
        {"text": "Update status", "exact": True, "n": 3, "position": "bottom", "index": 0},
        {"text": "Discharge", "exact": True, "n": 4, "position": "bottom"},
    ], crop={"x": 256, "y": 330, "width": 1344, "height": 560})

if "results" in steps:
    go(p, "/medical/lab-results")
    p.fill("#lab-results-search", "Kamdem")
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "results-list.png", [
        {"selector": "#lab-results-search", "n": 1, "position": "bottom"},
        {"text": "Refresh", "exact": True, "n": 2, "position": "bottom"},
        {"text": "View details", "exact": True, "n": 3, "position": "top", "index": 0},
        {"text": "Download PDF", "exact": True, "n": 4, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 620})
    p.get_by_text("View details", exact=True).nth(1).click()
    p.wait_for_timeout(2500)
    p.set_viewport_size({"width": 1600, "height": 1400})
    p.wait_for_timeout(800)
    txt(p, "result-detail")
    shots.annotate(p, FIG / "result-detail.png", [
        {"text": "Biological Results", "exact": True, "n": 1, "position": "top", "outline": False},
        {"text": "Reference Values", "exact": True, "n": 2, "position": "top", "outline": False},
        {"text": "Interpretation", "exact": True, "n": 3, "position": "top", "outline": False},
    ], crop="[role=dialog]")
    p.set_viewport_size({"width": 1600, "height": 1000})
    go(p, "/medical/patients/19294")
    p.get_by_role("tab", name="Exams").click()
    p.wait_for_timeout(2000)
    txt(p, "dossier-exams")

if "bell" in steps:
    go(p, "/medical/doctors")
    p.wait_for_timeout(2000)
    print("bell buttons:", p.locator("button[title='Notifications']").count(), p.locator("header button").count())
    p.locator("button[title='Notifications']").first.click()
    p.wait_for_timeout(2000)
    txt(p, "bell")
    shots.annotate(p, FIG / "bell.png", [
        {"selector": "button[title='Notifications']", "n": 1, "position": "top"},
    ], crop={"x": 1000, "y": 0, "width": 600, "height": 300})

if "appt" in steps:
    go(p, "/medical/appointments")
    p.fill("#appt-search", "Tchoua") if p.locator("#appt-search").count() else None
    p.wait_for_timeout(2500)
    p.get_by_text("Edit", exact=True).first.click()
    p.wait_for_timeout(2000)
    p.set_viewport_size({"width": 1600, "height": 1300})
    p.select_option("#appt-time", "11:00")
    p.wait_for_timeout(300)
    shots.annotate(p, FIG / "appt-edit.png", [
        {"selector": "#appt-time", "n": 1, "position": "top"},
        {"text": "Save", "exact": True, "n": 2, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    txt(p, "appt-edited")
    p.get_by_text("View record", exact=True).first.click()
    p.wait_for_timeout(4000)
    print("view record ->", p.url)

if "profile" in steps:
    go(p, "/medical/doctors")
    p.click("[aria-label='My Account']")
    p.wait_for_timeout(1500)
    p.locator("[class*='max-w-md'] input[type=tel]").fill("+237677010098")
    shots.annotate(p, FIG / "account-profile.png", [
        {"text": "Profile", "exact": True, "n": 1, "position": "top", "index": 0},
        {"text": "Password", "exact": True, "n": 2, "position": "top", "index": 0},
        {"selector": "[class*='max-w-md'] input[type=tel]", "n": 3, "position": "right"},
        {"selector": "[class*='max-w-md'] button[type=submit]", "n": 4, "position": "left"},
    ], crop="[class*='max-w-md']")
    p.locator("[class*='max-w-md'] button[type=submit]").click()
    p.wait_for_timeout(2500)
    txt(p, "profile-saved")

if "offline" in steps:
    for route in ("/medical/doctors", "/medical/patients", "/medical/patients/19299", "/medical/appointments", "/medical/hospitalizations"):
        go(p, route, settle=5000)
    shots.close(pw, br)
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE, offline=True)
    p.goto(shots.BASE_URL + "/medical/doctors")
    p.get_by_text("Offline").first.wait_for(timeout=60000)
    shots.wait_ready(p)
    p.wait_for_timeout(3000)
    txt(p, "off-dashboard")
    p.goto(shots.BASE_URL + "/medical/patients")
    shots.wait_ready(p)
    p.wait_for_timeout(4000)
    p.get_by_text("Ajouter un patient").click()
    p.wait_for_timeout(1500)
    p.fill("#patient-first-name", "Solange")
    p.fill("#patient-last-name", "Nkodo")
    p.fill("#patient-birth-date", "1995-01-17")
    p.select_option("#patient-gender", index=2)
    p.fill("#patient-phone", "+237677010011")
    dialog(p).get_by_text("Créer").click()
    p.wait_for_timeout(4000)
    txt(p, "off-code")
    shots.annotate(p, FIG / "offline-code.png", [
        {"text": "Offline", "n": 1, "position": "bottom"},
        {"text": "OK", "exact": True, "n": 2, "position": "left"},
    ], crop={"x": 380, "y": 0, "width": 1220, "height": 700})
    p.get_by_text("OK", exact=True).click()
    p.wait_for_timeout(2500)
    p.set_viewport_size({"width": 1600, "height": 2300})
    p.wait_for_timeout(800)
    p.select_option("#mr-motif", "consultation")
    p.fill("#mr-bp", "110/70")
    p.fill("#mr-temperature", "36.7")
    p.fill("#mr-weight", "58")
    p.fill("#mr-symptoms", "Sore throat since yesterday.")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3500)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(800)
    txt(p, "off-saved")
    shots.shot(p, FIG / "_off-saved.png")
    # a note on a file already open on this computer
    p.goto(shots.BASE_URL + "/medical/patients/19299")
    shots.wait_ready(p)
    p.wait_for_timeout(4000)
    p.get_by_text("New consultation", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.set_viewport_size({"width": 1600, "height": 2300})
    p.select_option("#mr-motif", "consultation")
    p.fill("#mr-bp", "116/74")
    p.fill("#mr-temperature", "36.8")
    p.fill("#mr-notes", "Back pain eased after rest. Entered while the connection was down.")
    dialog(p).get_by_text("Save", exact=True).click()
    p.wait_for_timeout(3000)
    p.set_viewport_size({"width": 1600, "height": 1000})
    p.wait_for_timeout(800)
    txt(p, "off-note")
    shots.annotate(p, FIG / "offline-saved.png", [
        {"selector": "text=/Offline|Sending error/ >> visible=true", "n": 1, "position": "bottom"},
        {"text": "Entered while the connection was down.", "n": 2, "position": "right", "outline": False},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 760})
    shots.close(pw, br)
    pw, br, p = shots.launch(width=1600, height=1000, profile_dir=PROFILE)
    shots.goto(p, "/medical/patients")
    p.get_by_text("Connected").first.wait_for(timeout=60000)
    p.wait_for_timeout(10000)
    p.fill("#patient-search", "Nkodo")
    p.wait_for_timeout(3000)
    txt(p, "off-synced")

if "presc" in steps:
    # form only, nothing saved (the real prescription was saved earlier for Mireille Tchoua)
    go(p, "/medical/patients/19299")
    p.set_viewport_size({"width": 1600, "height": 1500})
    p.get_by_text("Prescrire", exact=True).first.click()
    p.wait_for_timeout(1500)
    p.fill("#presc-medication", "Paracetamol 500 mg tablets")
    p.fill("#presc-dosage", "500 mg")
    p.fill("#presc-frequency", "3 times a day")
    p.fill("#presc-duration", "3 days")
    print("lab order box:", p.locator("#is_lab_order").count())
    shots.annotate(p, FIG / "presc-form.png", [
        {"selector": "#is_lab_order", "n": 1, "position": "top"},
        {"selector": "#presc-medication", "n": 2, "position": "top"},
        {"selector": "#presc-dosage", "n": 3, "position": "top"},
        {"selector": "#presc-duration", "n": 4, "position": "top"},
        {"text": "Save", "exact": True, "n": 5, "position": "top"},
    ], crop="[role=dialog]")
    dialog(p).get_by_text("Cancel", exact=True).click()
    p.set_viewport_size({"width": 1600, "height": 1000})

if "consultations" in steps:
    go(p, "/medical/medical-records")
    p.fill("#mr-search", "Fotso")
    p.wait_for_timeout(3000)
    shots.annotate(p, FIG / "consultations-list.png", [
        {"text": "New consultation", "exact": True, "n": 1, "position": "left"},
        {"selector": "#mr-search", "n": 2, "position": "bottom"},
        {"text": "Edit", "exact": True, "n": 3, "position": "top", "index": 0},
    ], crop={"x": 256, "y": 0, "width": 1344, "height": 520})

if any(s != "signin" for s in steps):
    shots.close(pw, br)
