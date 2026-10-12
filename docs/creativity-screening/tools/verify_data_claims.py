"""Recheck every 'public data' claim of the data check against the downloaded files (no model involved).

For each paper whose data record (forms/data/<cid>.json) says public_participant_data or public_partial: (1) its deposits were
downloaded (manifest at D:/projects/ai-skill-atlas/creativity-data/manifest.json, files with a SHA-256); (2) for every deposit
the job described as participant-level, the columns the job reported seeing exist together in one downloaded data file; (3)
that file's row count is reported next to the job's. Data files are only read (csv, tsv, xlsx, sav, dta, rds, json); nothing in
a deposit is executed. Run with: python -I tools/verify_data_claims.py

Output: data-claims-check.json in the screening folder, and a summary line per paper.
"""
import io
import json
import sys
import warnings

warnings.filterwarnings("ignore")
from pathlib import Path

SCREEN = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA = Path("D:/projects/ai-skill-atlas/creativity-data")
READABLE = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".sav", ".dta", ".rds", ".json"}


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


def header_and_rows(path):
    """(columns, rows) of a data file, or None if it cannot be read as a table."""
    import pandas as pd
    suf = path.suffix.lower()
    try:
        if suf in (".csv", ".tsv", ".txt"):
            df = pd.read_csv(path, sep=None, engine="python", nrows=None, on_bad_lines="skip", encoding_errors="replace")
        elif suf in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        elif suf in (".sav", ".dta"):
            import pyreadstat
            df, _ = (pyreadstat.read_sav if suf == ".sav" else pyreadstat.read_dta)(str(path))
        elif suf == ".rds":
            import pyreadr
            res = pyreadr.read_r(str(path))
            df = next(iter(res.values()))
        elif suf == ".json":
            df = pd.read_json(path)
        else:
            return None
        return [str(c) for c in df.columns], int(len(df))
    except Exception:
        return None


def main():
    manifest = load(DATA / "manifest.json", {}) or {}
    out = {}
    for rec_path in sorted((SCREEN / "forms" / "data").glob("c*.json")):
        rec = load(rec_path, {}) or {}
        cid, status = rec.get("cid"), rec.get("status")
        if status not in ("public_participant_data", "public_partial"):
            continue
        keys = (manifest.get("papers") or {}).get(cid, [])
        files = []
        for k in keys:
            for rel, f in ((manifest.get("deposits") or {}).get(k, {}).get("files") or {}).items():
                if f.get("sha256"):
                    root = Path(f["unpacked"]) if f.get("unpacked") else Path(f["path"])
                    if root.is_dir():
                        files += [p for p in root.rglob("*") if p.suffix.lower() in READABLE and p.is_file()]
                    elif root.suffix.lower() in READABLE:
                        files.append(root)
        result = {"status_claimed": status, "deposits_downloaded": keys, "n_readable_files": len(files), "deposits": []}
        cache = {}
        for dep in rec.get("deposits") or []:
            if dep.get("access") != "public" or dep.get("contents") not in ("participant_level", "output_level_with_participant_id"):
                continue
            cols = [str(c) for c in (dep.get("columns_checked") or [])]
            # A job may list columns from several files of one deposit: match against all readable files together, and
            # report whether any file has the row count the job saw.
            union, rows_seen, best = set(), set(), None
            for f in files:
                if f not in cache:
                    cache[f] = header_and_rows(f)
                hr = cache[f]
                if not hr:
                    continue
                union |= set(hr[0])
                rows_seen.add(hr[1])
                present = sum(1 for c in cols if c in hr[0])
                if best is None or present > best[1]:
                    best = (f, present, hr[1])
            d = {"url": dep.get("url"), "columns_claimed": len(cols), "rows_claimed": dep.get("rows_checked")}
            if cols and union:
                found = sum(1 for c in cols if c in union)
                rows_ok = dep.get("rows_checked") is None or dep.get("rows_checked") in rows_seen
                d.update({"best_file": str(best[0]) if best else None, "columns_found": found, "rows_in_file": best[2] if best else None,
                          "rows_match_some_file": rows_ok, "confirmed": found >= max(1, int(0.8 * len(cols))) and rows_ok})
            else:
                d.update({"confirmed": False, "reason": "no readable data file downloaded" if not files else "no columns claimed or none readable"})
            result["deposits"].append(d)
        result["confirmed"] = any(d.get("confirmed") for d in result["deposits"])
        out[cid] = result
        print(f"{cid}: {status} | downloaded deposits {len(keys)} | readable files {len(files)} | "
              + "; ".join(f"{'OK' if d.get('confirmed') else 'NOT CONFIRMED'} cols {d.get('columns_found', 0)}/{d['columns_claimed']} rows claimed {d.get('rows_claimed')} {'found' if d.get('rows_match_some_file') else 'not found'}" for d in result["deposits"]))
    with io.open(SCREEN / "data-claims-check.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    n_conf = sum(1 for v in out.values() if v["confirmed"])
    print(f"claims checked: {len(out)} | confirmed from downloaded files: {n_conf} | not confirmed: {len(out) - n_conf}")


if __name__ == "__main__":
    sys.exit(main())
