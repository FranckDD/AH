"""Build a Glostone-Care user guide PDF from docs/user-guides/src/<guide_id>/guide.md.

    python docs/user-guides/tools/build_pdf.py secretary-1
    python docs/user-guides/tools/build_pdf.py secretary-1 --out-name secretary-1-patients-appointments-invoicing

Conventions are described in docs/user-guides/tools/README.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
from pathlib import Path

import markdown
from weasyprint import CSS, HTML

GUIDES = Path(__file__).resolve().parents[1]
FONTS = Path("C:/Windows/Fonts")

CSS_TEXT = """

@page {
  size: A4; margin: 22mm 20mm 22mm 22mm;
  @top-left { content: "Glostone-Care"; font: bold 8.5pt "Segoe UI"; color: #0f5e57; }
  @top-right { content: string(chapter); font: 8.5pt "Segoe UI"; color: #666; }
  @bottom-left { content: string(guide); font: 8.5pt "Segoe UI"; color: #666; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8.5pt "Segoe UI"; color: #666; }
}
@page cover { margin: 0; @top-left { content: none } @top-right { content: none }
  @bottom-left { content: none } @bottom-right { content: none } }
@page toc { @top-right { content: none } }

html { font: 10pt/1.45 Georgia; color: #1d2327; }
body { counter-reset: chapter figure; }

.cover { page: cover; height: 297mm; position: relative; background: #0f5e57; color: white; }
.cover .band { position: absolute; left: 22mm; right: 22mm; top: 70mm; }
.cover .wordmark { font: bold 15pt "Segoe UI"; letter-spacing: 1.5pt; color: #bfe6df; }
.cover h1 { font: bold 30pt/1.15 "Segoe UI"; margin: 18mm 0 6mm; color: white; string-set: guide content(); }
.cover .subtitle { font: 13pt/1.4 Georgia; color: #e6f3f0; max-width: 140mm; }
.cover .meta { position: absolute; left: 22mm; bottom: 25mm; font: 10pt/1.6 "Segoe UI"; color: #bfe6df; }
.cover .meta b { color: white; }

nav.toc { page: toc; break-after: page; }
nav.toc h2 { font: bold 18pt "Segoe UI"; color: #0f5e57; margin: 0 0 8mm; }
nav.toc ol { list-style: none; padding: 0; margin: 0; }
nav.toc li { margin: 0 0 2.5mm; font: 11pt "Segoe UI"; }
nav.toc li.h3 { margin-left: 8mm; font-size: 10pt; color: #444; }
nav.toc a { color: inherit; text-decoration: none; }
nav.toc a::after { content: leader('.') target-counter(attr(href), page); }

h2 { font: bold 17pt/1.25 "Segoe UI"; color: #0f5e57; margin: 10mm 0 4mm; break-after: avoid;
     counter-increment: chapter; string-set: chapter content(); }
h2::before { content: counter(chapter) ". "; }
h2.unnumbered { counter-increment: none; }
h2.unnumbered::before { content: none; }
h2.newpage { break-before: page; margin-top: 0; }
h3 { font: bold 12pt/1.3 "Segoe UI"; color: #1d2327; margin: 7mm 0 2mm; break-after: avoid; }
h4 { font: bold 10.5pt "Segoe UI"; margin: 5mm 0 1mm; break-after: avoid; }
p { margin: 0 0 3mm; orphans: 3; widows: 3; }

main ol { padding-left: 0; margin: 2mm 0 4mm; counter-reset: step; list-style: none; }
main ol > li { counter-increment: step; position: relative; padding-left: 9mm; margin-bottom: 2mm; }
main ol > li::before { content: counter(step); position: absolute; left: 0; top: 0.3mm;
  width: 5.6mm; height: 5.6mm; border-radius: 50%; background: #0f5e57; color: white;
  font: bold 8.5pt/5.6mm "Segoe UI"; text-align: center; }
ul { margin: 1mm 0 3mm; padding-left: 6mm; }
ul > li { margin-bottom: 1mm; }

strong { font-weight: bold; }
.ui { font-family: "Segoe UI"; font-weight: bold; color: #0f3d3a; }
.mk { display: inline-block; min-width: 4.2mm; height: 4.2mm; border-radius: 50%;
  background: rgb(200,30,90); color: white; font: bold 7.5pt/4.2mm "Segoe UI"; text-align: center;
  vertical-align: 0.3mm; }

figure { margin: 4mm 0 5mm; break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 105mm; border: 0.4pt solid #c9d1d3; }
figure.small img { max-width: 62%; max-height: 70mm; }
figcaption { font: 9pt/1.35 "Segoe UI"; color: #444; margin-top: 2mm; text-align: left; }
figcaption::before { counter-increment: figure; content: "Figure " counter(figure) ". "; font-weight: bold; color: #1d2327; }

.box { border: 0.8pt solid #9fb3b1; border-left: 3pt solid #0f5e57; padding: 2.5mm 4mm; margin: 3mm 0 4mm;
  break-inside: avoid; background: #f5f9f8; }
.box.caution { border-left-color: #b4471b; background: #fdf6f2; border-color: #e1b9a6; }
.box .label { font: bold 9pt "Segoe UI"; text-transform: uppercase; letter-spacing: 0.6pt; color: #0f5e57; display: block; margin-bottom: 1mm; }
.box.caution .label { color: #b4471b; }
.box p:last-child { margin-bottom: 0; }

table { border-collapse: collapse; width: 100%; margin: 3mm 0 5mm; font: 9.5pt/1.4 "Segoe UI"; break-inside: avoid; }
th { text-align: left; background: #e8f0ef; border-bottom: 1pt solid #0f5e57; padding: 1.8mm 2.5mm; }
td { border-bottom: 0.4pt solid #d5dcdd; padding: 1.8mm 2.5mm; vertical-align: top; }
code { font: 9pt Consolas, monospace; background: #f0f2f3; padding: 0 1mm; }
dl { break-inside: avoid; }
dl dt { font: bold 10pt "Segoe UI"; margin-top: 2mm; }
dl dd { margin: 0 0 1mm 6mm; }
"""


def parse_front_matter(text: str):
    meta = {}
    if text.startswith("---"):
        _, fm, text = text.split("---", 2)
        for line in fm.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, text


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def postprocess(body: str) -> str:
    # Figures: a paragraph holding only an image becomes <figure> with caption.
    def fig(m):
        attrs = m.group(1)
        alt = re.search(r'alt="([^"]*)"', attrs).group(1)
        cls = ' class="small"' if "small" in attrs else ""
        attrs = attrs.replace(' title="small"', "")
        return f"<figure{cls}><img{attrs}><figcaption>{alt}</figcaption></figure>"
    body = re.sub(r"<p><img([^>]*)/?></p>", fig, body)

    # Note / Caution boxes from blockquotes.
    def box(m):
        inner = m.group(1).strip()
        k = re.match(r"<p>(Note|Caution|Tip|Important):\s*", inner)
        if not k:
            return m.group(0)
        kind = k.group(1)
        inner = "<p>" + inner[k.end():]
        cls = "caution" if kind in ("Caution", "Important") else "note"
        return f'<div class="box {cls}"><span class="label">{kind}</span>{inner}</div>'
    body = re.sub(r"<blockquote>(.*?)</blockquote>", box, body, flags=re.S)

    # Marker references: (3) after a UI label -> red disc; [[Save]] -> UI label style.
    body = re.sub(r"\[\[(.+?)\]\]", r'<span class="ui">\1</span>', body)
    body = re.sub(r"\{(\d{1,2})\}", r'<span class="mk">\1</span>', body)
    return body


def build_toc(body: str):
    entries = []

    def add_id(m):
        level, attrs, title = m.group(1), m.group(2) or "", m.group(3)
        plain = re.sub("<[^>]+>", "", title)
        anchor = slug(plain)
        entries.append((level, anchor, plain, "unnumbered" in attrs))
        return f'<h{level}{attrs} id="{anchor}">{title}</h{level}>'
    body = re.sub(r"<h([23])((?: [^>]*)?)>(.*?)</h\1>", add_id, body)
    n = 0
    items = []
    for level, anchor, plain, unnumbered in entries:
        label = html.escape(html.unescape(plain))
        if level == "2" and not unnumbered:
            n += 1
            label = f"{n}. {label}"
        items.append(f'<li class="h{level}"><a href="#{anchor}">{label}</a></li>')
    toc = '<nav class="toc"><h2 class="unnumbered" style="break-before:auto;string-set:none">Contents</h2><ol>' + "".join(items) + "</ol></nav>"
    return toc, body


def build(guide_id: str, out_name: str | None = None) -> Path:
    src = GUIDES / "src" / guide_id
    meta, text = parse_front_matter((src / "guide.md").read_text(encoding="utf-8"))
    # "## Title {.unnumbered}" support
    text = re.sub(r"^## (.+?) \{\.unnumbered\}$", r'<h2 class="unnumbered">\1</h2>', text, flags=re.M)
    body = markdown.markdown(text, extensions=["tables", "attr_list", "def_list", "sane_lists"])
    body = postprocess(body)
    toc, body = build_toc(body)
    version = meta.get("version") or dt.date.today().isoformat()
    cover = f"""
<section class="cover"><div class="band">
  <div class="wordmark">GLOSTONE-CARE</div>
  <h1>{html.escape(meta.get('title', guide_id))}</h1>
  <div class="subtitle">{html.escape(meta.get('subtitle', ''))}</div>
</div>
<div class="meta">User guide for the role <b>{html.escape(meta.get('role', ''))}</b><br>
Version of {html.escape(version)}<br>Glostone-Care, by Motadje Franck</div></section>"""
    doc = f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{html.escape(meta.get('title', ''))}</title></head><body>{cover}{toc}<main>{body}</main></body></html>"
    out_dir = GUIDES / "en"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{out_name or meta.get('output') or guide_id}.pdf"
    HTML(string=doc, base_url=str(src) + "/").write_pdf(out, stylesheets=[CSS(string=CSS_TEXT)])
    return out


def verify_text(pdf: Path, probe: str) -> bool:
    """WeasyPrint subsets fonts, so text is never searchable in raw bytes; check
    extraction with pypdf after a write round trip."""
    import io
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(str(pdf)))
    buf = io.BytesIO()
    w.write(buf)
    buf.seek(0)
    text = "".join(p.extract_text() or "" for p in PdfReader(buf).pages)
    return probe in text


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("guide_id")
    ap.add_argument("--out-name")
    ap.add_argument("--probe", help="text that must be extractable from the PDF")
    a = ap.parse_args()
    out = build(a.guide_id, a.out_name)
    from pypdf import PdfReader
    print(f"{out} ({len(PdfReader(str(out)).pages)} pages)")
    if a.probe:
        ok = verify_text(out, a.probe)
        print("text extraction:", "ok" if ok else "FAILED")
        raise SystemExit(0 if ok else 1)
