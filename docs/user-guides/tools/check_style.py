"""Style check for the user guide sources.

    python docs/user-guides/tools/check_style.py               # every guide
    python docs/user-guides/tools/check_style.py secretary-1   # one guide

Exit status 1 when a hard violation is found. Review items are printed but do
not fail the check.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

FORBIDDEN_CHARS = {
    "—": "em dash", "–": "en dash", "…": "ellipsis character",
    "·": "middle dot", "•": "bullet character",
}
ARROWS = re.compile(r"[←-⇿⟰-⟿⤀-⥿⬀-⯿]|->|=>|<-")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")
BANNED = ["seamless", "robust", "leverage", "streamline", "ensure", "utilize", "utilise",
          "delve", "crucial", "comprehensive solution", "in conclusion", "let us", "let's"]
TRIAD = re.compile(r"\b(\w+), (\w+),? and (\w+) (\w+)")


def strip_code(text: str) -> str:
    return re.sub(r"`[^`]*`", "", text)


def check(guide: Path):
    hard, review = [], []
    md = guide / "guide.md"
    raw = md.read_text(encoding="utf-8")
    body = raw.split("---", 2)[2] if raw.startswith("---") else raw
    for no, line in enumerate(raw.splitlines(), 1):
        text = strip_code(line)
        for ch, name in FORBIDDEN_CHARS.items():
            if ch in text:
                hard.append(f"{md.name}:{no}: {name}")
        if ARROWS.search(text):
            hard.append(f"{md.name}:{no}: arrow")
        if EMOJI.search(text):
            hard.append(f"{md.name}:{no}: emoji or symbol")
        low = text.lower()
        for w in BANNED:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                hard.append(f"{md.name}:{no}: banned word '{w}'")
        for m in TRIAD.finditer(text):
            review.append(f"{md.name}:{no}: list of three, check it is not decorative: '{m.group(0)}'")
        if re.match(r"#{2,4} [^:]+: ", line):
            review.append(f"{md.name}:{no}: heading with a colon subtitle")
    for fig in re.findall(r"!\[[^\]]*\]\(([^) ]+)", body):
        if not (guide / fig).exists():
            hard.append(f"{md.name}: missing figure {fig}")
    # sentence openings
    prose = re.sub(r"!\[[^\]]*\]\([^)]*\)|^#.*$|^\|.*$", "", body, flags=re.M)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose) if len(s.split()) > 3]
    firsts = Counter(re.sub(r"^[\d.\s>*\-]+", "", s).split(" ")[0].lower() for s in sentences)
    if sentences:
        word, n = firsts.most_common(1)[0]
        share = n / len(sentences)
        if share > 0.4:
            hard.append(f"{md.name}: {share:.0%} of sentences start with '{word}'")
        elif share > 0.2:
            review.append(f"{md.name}: {share:.0%} of sentences start with '{word}'")
    return hard, review


def main(argv):
    guides = [SRC / g for g in argv] if argv else sorted(p for p in SRC.iterdir() if (p / "guide.md").exists())
    failed = False
    for g in guides:
        hard, review = check(g)
        print(f"== {g.name}: {len(hard)} violation(s), {len(review)} review item(s)")
        for h in hard:
            print("  ERROR ", h)
        for r in review:
            print("  REVIEW", r)
        failed |= bool(hard)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
