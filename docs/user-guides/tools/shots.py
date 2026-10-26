"""Screenshot helpers for the Glostone-Care user guides.

Usage (from the repository root):

    from docs.user_guides_tools import ...   # or: sys.path.insert(0, 'docs/user-guides/tools')
    import shots
    pw, browser, page = shots.launch()
    shots.login(page, "secretaire")
    shots.goto(page, "/secretariat/patients")
    shots.annotate(page, "docs/user-guides/src/secretary-1/figures/patients.png",
                   [{"selector": "text=New patient", "n": 1},
                    {"text": "Search", "n": 2, "position": "left"}])
    shots.close(pw, browser)

Environment variables: GUIDES_BASE_URL (default http://localhost:4173),
GUIDES_ACCOUNTS (default .superpowers/sdd/2026-10-25-user-guides/accounts.json).
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
BASE_URL = os.environ.get("GUIDES_BASE_URL", "http://localhost:4173")
ACCOUNTS = Path(os.environ.get(
    "GUIDES_ACCOUNTS", ROOT / ".superpowers/sdd/2026-10-25-user-guides/accounts.json"))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# House style for markers: one accent colour, white numerals.
ACCENT = (200, 30, 90)        # deep magenta, distinct from the app's brand colours
OUTLINE = (255, 255, 255)
SCALE = 2                     # deviceScaleFactor
MARK_RADIUS = 15              # CSS px


def launch(headless: bool = True, width: int = 1440, height: int = 900,
           profile_dir=None, offline: bool = False):
    """Start Chrome. The frontend must be built with VITE_API_URL=http://127.0.0.1:8000
    (see README). profile_dir keeps the browser profile (service worker, local
    PowerSync database, session) between launches. offline=True routes every
    request except the app shell on :4173 to a dead proxy, which also cuts the
    PowerSync shared worker (Playwright's set_offline does not reach it)."""
    pw = sync_playwright().start()
    kwargs = {"headless": headless}
    if Path(CHROME).exists():
        kwargs["executable_path"] = CHROME
    if offline:
        kwargs["args"] = ["--proxy-server=http://127.0.0.1:9",
                          "--proxy-bypass-list=<-loopback>;localhost:4173"]
    ctx_kwargs = dict(viewport={"width": width, "height": height},
                      device_scale_factor=SCALE, locale="en-US")
    if profile_dir:
        ctx = pw.chromium.launch_persistent_context(str(profile_dir), **kwargs, **ctx_kwargs)
        ctx.add_init_script("try { localStorage.setItem('lang', 'en'); } catch (e) {}")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        return pw, ctx, page
    browser = pw.chromium.launch(**kwargs)
    ctx = browser.new_context(**ctx_kwargs)
    # The interface language is read from localStorage 'lang' at start-up (src/i18n.js).
    ctx.add_init_script("try { localStorage.setItem('lang', 'en'); } catch (e) {}")
    page = ctx.new_page()
    return pw, browser, page


def close(pw, browser):
    browser.close()
    pw.stop()


def account(role_key: str) -> dict:
    return json.loads(ACCOUNTS.read_text(encoding="utf-8"))[role_key]


def login(page, role_key: str):
    acc = account(role_key)
    page.goto(BASE_URL + "/login")
    page.wait_for_timeout(1500)
    if "/login" not in page.url:      # persistent profile, session still open
        wait_ready(page)
        return
    page.fill("#username", acc["username"])
    page.fill("#password", acc["password"])
    page.click("button[type=submit]")
    page.wait_for_url(lambda u: "/login" not in u, timeout=20000)
    wait_ready(page)


def goto(page, route: str):
    page.goto(BASE_URL + route)
    wait_ready(page)


def wait_ready(page, timeout: int = 15000):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    try:
        page.wait_for_function(
            "() => !/(Loading|Chargement)/.test(document.body.innerText)", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(400)


def _locate(page, mark):
    if "selector" in mark:
        loc = page.locator(mark["selector"])
    else:
        loc = page.get_by_text(mark["text"], exact=mark.get("exact", False))
    loc = loc.nth(mark.get("index", 0))
    box = loc.bounding_box()
    if box is None:
        raise RuntimeError(f"marker target not visible: {mark}")
    return box


def _font(size):
    for f in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def annotate(page, out_path, marks, crop=None, outline=True):
    """Take a viewport screenshot and draw numbered markers.

    marks: list of dicts with 'selector' or 'text', 'n' (number), optional
    'position' (left, right, top, bottom, inside; default left), optional
    'note' (short text drawn next to the marker), optional 'index'.
    crop: None, a dict {x, y, width, height} in CSS px, or a selector string.
    """
    boxes = [(m, _locate(page, m)) for m in marks]
    clip_box = None
    if isinstance(crop, str):
        clip_box = page.locator(crop).first.bounding_box()
    elif isinstance(crop, dict):
        clip_box = crop
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    draw = ImageDraw.Draw(img)
    r = MARK_RADIUS * SCALE
    font = _font(int(r * 1.15))
    note_font = _font(int(r * 0.85))
    circles = []
    for m, b in boxes:
        x, y, w, h = (v * SCALE for v in (b["x"], b["y"], b["width"], b["height"]))
        if m.get("outline", outline):
            draw.rounded_rectangle([x - 4, y - 4, x + w + 4, y + h + 4], radius=8,
                                   outline=ACCENT, width=3 * SCALE // 2)
        pos = m.get("position", "left")
        cx, cy = {
            "left": (x - r - 10, y + h / 2),
            "right": (x + w + r + 10, y + h / 2),
            "top": (x + w / 2, y - r - 10),
            "bottom": (x + w / 2, y + h + r + 10),
            "inside": (x + r + 6, y + h / 2),
        }[pos]
        cx = min(max(cx, r + 2), img.width - r - 2)
        cy = min(max(cy, r + 2), img.height - r - 2)
        circles.append((cx - r, cy - r, cx + r, cy + r))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT, outline=OUTLINE, width=3)
        draw.text((cx, cy), str(m["n"]), fill=OUTLINE, font=font, anchor="mm")
        if m.get("note"):
            tx = cx + r + 8 if pos != "left" else cx - r - 8
            anchor = "lm" if pos != "left" else "rm"
            bb = draw.textbbox((tx, cy), m["note"], font=note_font, anchor=anchor)
            draw.rectangle([bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4], fill=OUTLINE, outline=ACCENT, width=2)
            draw.text((tx, cy), m["note"], fill=ACCENT, font=note_font, anchor=anchor)
    if clip_box:
        pad = 12
        x0 = (clip_box["x"] - pad) * SCALE
        y0 = (clip_box["y"] - pad) * SCALE
        x1 = (clip_box["x"] + clip_box["width"] + pad) * SCALE
        y1 = (clip_box["y"] + clip_box["height"] + pad) * SCALE
        # grow the crop so that no marker is cut off
        for c in circles:
            x0, y0 = min(x0, c[0] - 8), min(y0, c[1] - 8)
            x1, y1 = max(x1, c[2] + 8), max(y1, c[3] + 8)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(img.width, x1), min(img.height, y1)
        img = img.crop((int(x0), int(y0), int(x1), int(y1)))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


def shot(page, out_path, crop=None):
    """Plain screenshot, no markers."""
    return annotate(page, out_path, [], crop=crop)
