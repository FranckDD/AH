"""Build the adoption PDFs (one-pagers, outage sheet, plan) from Markdown.

    python docs/adoption/build_adoption_pdfs.py

One-page sheets shrink their font until they fit on one A4 page. Same look as the user guides.
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from pypdf import PdfReader
from weasyprint import CSS, HTML

HERE = Path(__file__).resolve().parent

BASE_CSS = """
@page { size: A4; margin: %(margin)s;
  @bottom-left { content: "Glostone-Care"; font: 8pt "Segoe UI"; color: #666; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8pt "Segoe UI"; color: #666; } }
html { font: %(fs)spt/1.38 "Segoe UI", Georgia; color: #1d2327; }
header { background: #0f5e57; color: white; padding: 4mm 6mm; margin-bottom: 4mm; border-radius: 1.5mm; }
header .brand { font: bold 8.5pt "Segoe UI"; letter-spacing: 1.2pt; color: #bfe6df; }
header h1 { font: bold %(h1)spt/1.15 "Segoe UI"; margin: 1mm 0 0; color: white; }
header .sub { font: %(sub)spt "Segoe UI"; color: #e6f3f0; margin-top: 0.5mm; }
h2 { font: bold %(h2)spt "Segoe UI"; color: #0f5e57; margin: 3.5mm 0 1.5mm; break-after: avoid; }
p { margin: 0 0 2mm; }
ol { padding-left: 0; margin: 1mm 0 2mm; counter-reset: step; list-style: none; }
ol > li { counter-increment: step; position: relative; padding-left: 8mm; margin-bottom: 1.4mm; }
ol > li::before { content: counter(step); position: absolute; left: 0; top: 0.2mm; width: 5.4mm; height: 5.4mm;
  border-radius: 50%%; background: #0f5e57; color: white; font: bold 8.5pt/5.4mm "Segoe UI"; text-align: center; }
ul { margin: 1mm 0 2mm; padding-left: 0; list-style: none; } ul > li { margin-bottom: 0.8mm; padding-left: 4mm; position: relative; }
ul > li::before { content: "-"; position: absolute; left: 0; color: #0f5e57; font-weight: bold; }
.box { border: 0.8pt solid #9fb3b1; border-left: 3pt solid #0f5e57; padding: 2mm 3.5mm; margin: 2.5mm 0; background: #f5f9f8; break-inside: avoid; }
.box.caution { border-left-color: #b4471b; background: #fdf6f2; border-color: #e1b9a6; }
.box .label { font: bold 8.5pt "Segoe UI"; text-transform: uppercase; letter-spacing: 0.6pt; color: #0f5e57; display: block; margin-bottom: 0.8mm; }
.box.caution .label { color: #b4471b; }
.box p { margin: 0; }
table { border-collapse: collapse; width: 100%%; margin: 2mm 0 3mm; font: 9pt/1.35 "Segoe UI"; }
th { text-align: left; background: #e8f0ef; border-bottom: 1pt solid #0f5e57; padding: 1.5mm 2mm; }
td { border-bottom: 0.4pt solid #d5dcdd; padding: 1.5mm 2mm; vertical-align: top; }
tr { break-inside: avoid; }
"""


def render(md_path: Path, fs: float, one_page: bool) -> str:
    raw = md_path.read_text(encoding="utf-8")
    meta = {}
    if raw.startswith("---"):
        _, fm, raw = raw.split("---", 2)
        for line in fm.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    body = markdown.markdown(raw, extensions=["tables"])

    def box(m):
        label, rest = m.group(1).rstrip("."), m.group(2)
        cls = "caution" if "wrong" in label.lower() else ""
        return f'<div class="box {cls}"><span class="label">{label}</span><p>{rest.strip()}</p></div>'
    def boxes(m):
        return "".join(re.sub(r"<p><strong>(.*?)</strong>(.*?)</p>", box, q, flags=re.S)
                       for q in re.findall(r"<p>.*?</p>", m.group(1), flags=re.S))
    body = re.sub(r"<blockquote>(.*?)</blockquote>", boxes, body, flags=re.S)
    css = BASE_CSS % dict(margin="11mm 13mm 13mm 13mm" if one_page else "18mm 18mm 18mm 18mm",
                          fs=fs, h1=fs + 8, sub=fs, h2=fs + 2.5)
    head = (f'<header><div class="brand">GLOSTONE-CARE</div><h1>{meta.get("title","")}</h1>'
            f'<div class="sub">{meta.get("subtitle","")}</div></header>')
    return f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{head}{body}</body></html>"


def build(md_path: Path, one_page: bool, start: float = 14.0) -> int:
    out = md_path.with_suffix(".pdf")
    fs = start if one_page else 10.5
    while True:
        HTML(string=render(md_path, fs, one_page), base_url=str(md_path.parent)).write_pdf(out)
        pages = len(PdfReader(out).pages)
        if not one_page or pages == 1 or fs <= 8.5:
            print(f"{md_path.relative_to(HERE)}: {pages} page(s), font {fs}")
            return pages
        fs -= 0.25


if __name__ == "__main__":
    for p in sorted((HERE / "one-pagers").glob("*.md")):
        build(p, True)
    build(HERE / "outage-sheet.md", True, 11.5)
    build(HERE / "training-and-pilot-plan.md", False)
