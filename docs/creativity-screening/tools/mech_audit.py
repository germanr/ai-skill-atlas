"""Final mechanical audit: rerun the current mechanical check on every extraction file, with the supplement PDFs, and
compare with the file's last stored mechanical check.

Usage: python tools/mech_audit.py [--only c006 c010 ...]
Writes extraction/checks/audit/<cid>.json and extraction/checks/audit/summary.json.
"""
import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_checks as X  # noqa: E402
import codex_extract as E  # noqa: E402
import codex_supplement as SUP  # noqa: E402

EXT = E.EXT
OUT = EXT / "checks" / "audit"


def last_stored(cid):
    """The latest mechanical check the chain stored for this paper (main chain and supplement pass)."""
    out = {}
    for name in ("mech3", "mech2", "mech"):
        d = E.P.load(EXT / "checks" / f"{cid}.{name}.json")
        if d is not None:
            out["main"] = (name, d.get("problems") or [])
            break
    for name in ("supmech2", "supmech"):
        d = E.P.load(EXT / "checks" / f"{cid}.{name}.json")
        if d is not None:
            out["supplement"] = (name, d.get("problems") or [])
            break
    return out


def key(p):
    return (p.get("where"), p.get("problem"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cids = sorted(p.stem for p in EXT.glob("c*.json"))
    if a.only:
        cids = [c for c in cids if c in a.only]
    summary = {}
    for cid in cids:
        ext = E.P.load(EXT / f"{cid}.json")
        if not ext:
            continue
        status = E.P.load(EXT / "status" / f"{cid}.json")
        try:
            problems = X.mechanical_check(ext, E.pdf_of(cid), extra_pdfs=SUP.supplement_pdfs(cid))
        except Exception as err:  # report and continue: one unreadable PDF must not stop the audit
            summary[cid] = {"error": repr(err)}
            print(cid, "ERROR", repr(err), flush=True)
            continue
        stored = last_stored(cid)
        before = {key(p) for _, ps in stored.values() for p in ps}
        new = [p for p in problems if key(p) not in before]
        resolved_slugs = {(r.get("slug"), r.get("field")) for r in ext.get("review_resolutions") or []}
        rec = {"cid": cid, "chain_done": bool(status), "problems": problems, "new_since_last_check": new,
               "last_checks": {k: v[0] for k, v in stored.items()}, "n_review_resolutions": len(resolved_slugs),
               "checked_at": datetime.now().isoformat(timespec="seconds")}
        with io.open(OUT / f"{cid}.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        summary[cid] = {"chain_done": bool(status), "problems": len(problems), "new": len(new)}
        print(cid, summary[cid], flush=True)
    with io.open(OUT / "summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    done = [c for c, s in summary.items() if s.get("chain_done")]
    print("papers:", len(summary), "| chain done:", len(done),
          "| with problems now:", sum(1 for c in done if summary[c]["problems"]),
          "| with problems the last check did not have:", sum(1 for c in done if summary[c]["new"]),
          "| errors:", sum(1 for s in summary.values() if "error" in s))


if __name__ == "__main__":
    main()
