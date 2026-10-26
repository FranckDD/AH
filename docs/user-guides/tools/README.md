# User guide tooling

Sources live in `docs/user-guides/src/<guide_id>/` (`guide.md`, `figures/*.png`, optional `capture.py`).
Generated PDFs go to `docs/user-guides/en/`. Demo accounts and the browser profile live in
`.superpowers/sdd/2026-10-25-user-guides/` (git-ignored): `accounts.json` is read by `shots.py`.

## Prerequisites

- API on http://127.0.0.1:8000 (`REDIS_URL=redis://localhost:16379/0 python -m uvicorn api_backend.backend_app.main:app --port 8000`).
- Frontend built with the API address forced, because `ah2-admin-web/.env.local` points elsewhere:
  `cd ah2-admin-web && VITE_API_URL=http://127.0.0.1:8000 npx vite build`, served by `npx vite preview --port 4173`.
- Python packages: playwright, Pillow, weasyprint, markdown, pypdf (pypdfium2 to render pages to PNG for review).

## Commands

```
python docs/user-guides/src/secretary-1/capture.py signin home      # take figures (real actions!)
python docs/user-guides/tools/check_style.py secretary-1            # style gate, exit 1 on violation
python docs/user-guides/tools/build_pdf.py secretary-1 --probe "Some heading"
```

## shots.py

- `launch(width=1440, profile_dir=None, offline=False)` returns `(pw, browser_or_context, page)`; English
  is forced through `localStorage.lang = 'en'`. Use width 1600 for wide tables (the cash desk overflows at 1440).
  `offline=True` with a `profile_dir` already signed in cuts the network for the PowerSync shared worker too
  (Playwright's `set_offline` does not reach it).
- `login(page, role_key)`: keys of accounts.json (admin, promoteur, secretaire, medecin, nurse, head_nurse,
  laborantin, psychologist, spiritual, toxico, assistant, stock, production). The API allows few logins per minute.
- `goto(page, route)`, `wait_ready(page)`.
- `annotate(page, out, marks, crop=None)`: each mark is `{"selector" | "text", "n", "position": left|right|top|bottom|inside, "note", "index", "exact", "outline"}`.
  `crop` is a selector or `{x, y, width, height}` in CSS pixels; the crop grows to keep every marker visible.
  Markers are deep magenta discs with white numerals. `shot(page, out, crop)` saves without markers.

## guide.md conventions

- Front matter: `title`, `role`, `subtitle`, `version`, `output` (PDF file name without extension).
- `## Chapter` is numbered automatically; `## Title {.unnumbered}` is not (front and back matter).
- Procedures are ordered lists. Keep bullets rare.
- Figures: `![Caption](figures/name.png)`; add `"small"` as title for narrow crops: `![Caption](figures/x.png "small")`.
  Captions are numbered "Figure N." automatically.
- Marker reference in text: `{3}` renders the same red disc as on the figure. UI labels: `[[Save Transaction]]`.
- Boxes: a blockquote starting with `Note:`, `Tip:`, `Caution:` or `Important:`.
- Tables: pipe tables. Glossary: definition lists (`Term` then `: definition`).
- Style: no em/en dash, no ellipsis character, no middle dot, no arrows, no emoji, none of the banned words
  listed in `check_style.py`. Quote UI labels exactly as the screen shows them.
