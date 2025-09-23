# view_pyqt6/utils/csv_exporter.py
from typing import Any, Dict, List, Optional, Callable
import csv
import os
import json

DEFAULT_PER_PAGE = 100  # protège contre la limite backend

def _ensure_dict(item: Any) -> Dict:
    if isinstance(item, dict):
        return item
    try:
        # collecte les attributs publics simples
        return {k: getattr(item, k) for k in dir(item) if not k.startswith("_") and not callable(getattr(item, k))}
    except Exception:
        return {"_raw": str(item)}

def fetch_all_as_dicts(
    controller: Any,
    params: Optional[Dict] = None,
    fetch_fn: str = "list_patients",
    per_page: int = DEFAULT_PER_PAGE,
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None
) -> List[Dict]:
    """Pages through controller.fetch_fn and returns flat list of dicts.
    progress_callback(done_count, total_estimate) is called after each page; it
    may raise an exception to abort (e.g. user cancelled).
    """
    if params is None:
        params = {}
    try:
        per_page = int(per_page)
    except Exception:
        per_page = DEFAULT_PER_PAGE
    per_page = min(per_page, DEFAULT_PER_PAGE)

    fetch = getattr(controller, fetch_fn, None)
    if not callable(fetch):
        raise AttributeError(f"Controller has no method '{fetch_fn}'")

    page = 1
    results: List[Dict] = []
    total_estimate = None

    while True:
        raw = fetch(**{**params, "page": page, "per_page": per_page})
        if isinstance(raw, dict) and "data" in raw:
            items = raw.get("data") or []
            total_estimate = raw.get("total")
        elif isinstance(raw, list):
            items = raw
            if page == 1:
                total_estimate = len(items)
        else:
            items = []

        for it in items:
            if not isinstance(it, dict):
                try:
                    it = _ensure_dict(it)
                except Exception:
                    it = {"_raw": str(it)}
            results.append(it)

        # call progress callback if provided
        if progress_callback:
            try:
                progress_callback(len(results), total_estimate)
            except Exception:
                # propagate to caller (e.g. canceled)
                raise

        # decide to break
        if isinstance(total_estimate, int):
            if len(results) >= int(total_estimate):
                break
        if not items or len(items) < per_page:
            break
        page += 1

    return results

def fetch_all_and_export_csv(
    controller: Any,
    path: str,
    params: Optional[Dict] = None,
    fetch_fn: str = "list_patients",
    per_page: int = DEFAULT_PER_PAGE,
    encoding: str = "utf-8-sig",
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None
) -> int:
    """
    Pages through controller and writes CSV to `path`.
    Returns number of exported rows.
    """
    rows = fetch_all_as_dicts(controller, params=params, fetch_fn=fetch_fn, per_page=per_page, progress_callback=progress_callback)
    if not rows:
        # create empty CSV with a default header
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", newline="", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerow(["patient_id", "code_patient", "last_name", "first_name", "father_name", "mother_name"])
        return 0

    # infer columns in stable order, ensure parents columns exist
    columns: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in columns:
                columns.append(k)
    # Ensure parent columns exist (if anywhere)
    parents_needed = False
    for p in ("father_name", "mother_name"):
        if any(p in r for r in rows) and p not in columns:
            columns.append(p)
            parents_needed = True

    # Ensure common ordering: put id/code/name first if present
    preferred = ["patient_id", "code_patient", "last_name", "first_name", "father_name", "mother_name"]
    ordered = []
    for p in preferred:
        if p in columns:
            ordered.append(p)
    for c in columns:
        if c not in ordered:
            ordered.append(c)
    columns = ordered

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for r in rows:
            row = []
            for c in columns:
                v = r.get(c) if isinstance(r, dict) else getattr(r, c, "")
                if v is None:
                    v = ""
                elif isinstance(v, (list, dict)):
                    try:
                        v = json.dumps(v, ensure_ascii=False)
                    except Exception:
                        v = str(v)
                row.append(str(v))
            writer.writerow(row)

    return len(rows)
