"""Figures for the Spiritual notes chapter (28 Oct 2026). Creates two invented notes with the demo
counsellor account, photographs them, then deletes them (step 'clean'). Run from the repo root:
    python docs/user-guides/src/spiritual-1/retake_notes.py
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from retake_lib import *
FIG = HERE / "figures"
dlg = lambda p: p.locator("[role=dialog]").first

pw, br, p = shots.launch(width=1600, height=1000)
p.on("dialog", lambda d: d.accept())
shots.login(p, "spiritual")
go(p, "/dashboard/spiritual-notes", connected=False)
print(txt(p, 400))
shots.annotate(p, FIG / "notes-menu.png", [
    {"text": "Spiritual notes", "exact": True, "n": 1, "position": "right", "index": 0},
], crop={"x": 0, "y": 60, "width": 260, "height": 330})

# note 1 (today): prayer, verse, text given
p.get_by_role("button", name="New note").click(); p.wait_for_timeout(1200)
d = dlg(p)
for lab in ("Prayer", "Verse read", "Text given"):
    d.get_by_label(lab, exact=True).check()
p.fill("#sn-verse", "John 3:16")
p.fill("#sn-content", "Short visit in the morning. Prayer for the family. The patient kept the printed text to read this week.")
p.wait_for_timeout(500)
shots.annotate(p, FIG / "notes-form.png", [
    {"selector": "#sn-date", "n": 1},
    {"text": "Prayer", "exact": True, "n": 2, "position": "right", "outline": False},
    {"selector": "#sn-verse", "n": 3, "position": "right"},
    {"text": "People did not want to talk", "exact": True, "n": 4, "position": "right", "outline": False},
    {"selector": "#sn-content", "n": 5, "position": "right"},
    {"text": "Save", "exact": True, "n": 6, "position": "top", "index": 0},
])
d.get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(2500)

# note 2 (past): nobody wanted to talk
p.get_by_role("button", name="New note").click(); p.wait_for_timeout(1200)
p.fill("#sn-date", "2026-10-24")
dlg(p).get_by_label("People did not want to talk", exact=True).check()
p.fill("#sn-content", "Went around the ward. Nobody wished to talk today.")
dlg(p).get_by_role("button", name="Save", exact=True).click(); p.wait_for_timeout(2500)
go(p, "/dashboard/spiritual-notes", connected=False)
print(txt(p, 600))
shots.annotate(p, FIG / "notes-list.png", [
    {"text": "New note", "exact": True, "n": 1, "position": "right", "index": 0},
    {"text": "Last note", "exact": True, "n": 2, "position": "right"},
    {"text": "Text given", "exact": True, "n": 3, "position": "right", "outline": False},
    {"text": "Edit", "exact": True, "n": 4, "position": "top", "index": 0},
    {"text": "Delete", "exact": True, "n": 5, "position": "top", "index": 0},
    {"text": "People did not want to talk", "exact": True, "n": 6, "position": "right", "outline": False},
])
shots.close(pw, br)

# read-only view as promoteur (notes still exist)
pw, br, p = shots.launch(width=1600, height=1000)
shots.login(p, "promoteur")
go(p, "/dashboard/spiritual-notes", connected=False)
print(txt(p, 500))
try: p.get_by_role("button", name="Close").first.click(timeout=2000)
except Exception: pass
p.wait_for_timeout(500)
shots.annotate(p, FIG / "notes-readonly.png", [
    {"text": "Spiritual notes", "exact": True, "n": 1, "position": "right", "index": 0},
    {"text": "Last note", "exact": True, "n": 2, "position": "right"},
])
shots.close(pw, br)

# clean: delete the notes created above
pw, br, p = shots.launch(width=1600, height=1000)
p.on("dialog", lambda d: d.accept())
shots.login(p, "spiritual")
go(p, "/dashboard/spiritual-notes", connected=False)
while p.get_by_role("button", name="Delete").count():
    p.get_by_role("button", name="Delete").first.click(); p.wait_for_timeout(1800)
print("left:", p.get_by_role("button", name="Delete").count())
shots.close(pw, br)
