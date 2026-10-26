"""Post-crops of tall form figures. Run once, right after the capture steps that
produced the raw shots (consult-form, presc-form, lab-order-form, result-detail,
appt-form, presc-list, results-list, patients-list). Boxes are in image pixels."""
from pathlib import Path
from PIL import Image
FIG = Path(__file__).resolve().parent / "figures"
def crop(name, box, out=None):
    src = FIG / f"_raw-{name}.png"
    if not src.exists():
        (FIG / f"_raw-{name}.png").write_bytes((FIG / f"{name}.png").read_bytes())
    im = Image.open(FIG / f"_raw-{name}.png")
    w, h = im.size
    l, t, r, b = box
    im.crop((l, t, min(r, w), min(b, h))).save(FIG / f"{out or name}.png")
crop("consult-form", (0, 560, 1840, 2200), "consult-form-a")
crop("consult-form", (0, 2200, 1840, 3714), "consult-form-b")
crop("presc-form", (0, 590, 1840, 2374))
crop("lab-order-form", (0, 560, 1840, 2106))
crop("result-detail", (0, 0, 2352, 1756))
crop("appt-form", (1088, 558, 2112, 2042))
crop("appt-day-panel", (440, 0, 1424, 766))
