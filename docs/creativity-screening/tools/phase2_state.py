"""Where each of the 84 extraction papers stands, stage by stage (no model involved).

Usage: python tools/phase2_state.py [--json out.json]
"""
import argparse
import io
import json
from collections import Counter
from pathlib import Path

S = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
EXT = S / "extraction"


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    st = (load(S / "report-data.json", {}) or {}).get("status_by_cid", {})
    scope = sorted(c for c, v in st.items() if v == "core" and c not in {"c044", "c276", "c818"})
    supp = {c for c, v in (load("D:/projects/ai-skill-atlas/creativity-supplements/manifest.json", {}) or {}).items() if v.get("files")}
    data = set(((load("D:/projects/ai-skill-atlas/creativity-data/manifest.json", {}) or {}).get("papers") or {}).keys())
    rows = {}
    for c in scope:
        raw_a, raw_b = (EXT / "raw" / f"{c}.A.json"), (EXT / "raw" / f"{c}.B.json")
        r = {
            "raw_A": raw_a.exists() and load(raw_a) is not None,
            "raw_B": raw_b.exists() and load(raw_b) is not None,
            "reconciled": load(EXT / f"{c}.json") is not None,
            "verify": load(EXT / "checks" / f"{c}.verify.json") is not None,
            "chain_done": load(EXT / "status" / f"{c}.json") is not None,
            "supplement_needed": c in supp,
            "supplement_done": "supplement" in (load(EXT / "status" / f"{c}.json", {}) or {}),
            "data_downloaded": c in data,
            "analysis_done": (S / "analysis" / c / "compare.json").exists(),
            "unparseable": [str(p.name) for p in (raw_a, raw_b, EXT / f"{c}.json") if p.exists() and load(p) is None],
        }
        if r["chain_done"]:
            stage = "chain done"
        elif r["verify"]:
            stage = "verified, fix pending"
        elif r["reconciled"]:
            stage = "reconciled, verify pending"
        elif r["raw_A"] and r["raw_B"]:
            stage = "both extractions, reconcile pending"
        elif r["raw_A"] or r["raw_B"]:
            stage = "one extraction only"
        else:
            stage = "not started"
        r["stage"] = stage
        todo = []
        if r["chain_done"] and r["supplement_needed"] and not r["supplement_done"]:
            todo.append("supplement")
        if r["chain_done"] and r["data_downloaded"] and not r["analysis_done"]:
            todo.append("analysis")
        r["todo_after_chain"] = todo
        rows[c] = r
    print("papers:", len(rows))
    for k, n in Counter(r["stage"] for r in rows.values()).most_common():
        print(f"  {k}: {n} {' '.join(c for c, r in rows.items() if r['stage'] == k) if k != 'chain done' else ''}")
    print("chain done but supplement pending:", [c for c, r in rows.items() if "supplement" in r["todo_after_chain"]])
    print("chain done but analysis pending:", [c for c, r in rows.items() if "analysis" in r["todo_after_chain"]])
    print("unparseable files:", {c: r["unparseable"] for c, r in rows.items() if r["unparseable"]})
    if a.json:
        io.open(a.json, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
