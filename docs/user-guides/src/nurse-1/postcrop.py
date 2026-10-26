"""Run once after capture.py newpat: removes the empty middle sections of the tall measurements
form so the figure stays readable (rows are in pixels of the 2x screenshot)."""
from pathlib import Path
from PIL import Image
FIG = Path(__file__).resolve().parent / "figures"
im = Image.open(FIG / "vitals-form.png")
W, H = im.size
s = H / 2000.0   # displayed height of the review image was 2000
cuts = [(int(1255 * s), int(1480 * s)), (int(80 * s), int(280 * s))]   # diagnosis block, patient block
keep = im
for a, b in sorted(cuts, reverse=True):
    top = keep.crop((0, 0, W, a)); bot = keep.crop((0, b, W, keep.size[1]))
    out = Image.new("RGB", (W, top.size[1] + bot.size[1]), "white")
    out.paste(top, (0, 0)); out.paste(bot, (0, top.size[1])); keep = out
keep.save(FIG / "vitals-form.png")
print(keep.size)

# Second pass (run once, after capture.py book / refer): trims blank areas around dialogs and lists.
def crop(name, box):
    im = Image.open(FIG / name)
    im.crop(box).save(FIG / name)
    print(name, Image.open(FIG / name).size)
crop("appt-form.png", (1050, 540, 2150, 2100))
crop("refer-named.png", (0, 0, 2248, 1300))
crop("refer-off.png", (0, 0, 2248, 1230))
crop("appointments-list.png", (0, 0, 3200, 1050))
