"""Classify every candidate from the files on disk and print a compact status table.

Final status per paper:
  core            reconciled form says core yes, and no challenge refuted it
  clarify         core unclear, a challenge refuted the coding, or a reconciliation item is unresolved
  small           randomized experiment with fewer than 50 people
  context_*       AI versus human output, observational, synthesis
  excluded        screened in full text and outside every class (reason given)
  no_fulltext     screened from the abstract only
  out             both triage screeners excluded it
  pending         not screened yet
Writes status.json next to candidates.json.
"""
import io
import json
from collections import Counter
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")


def load(path, default=None):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return default


def main():
    cands = load(ROOT / "candidates.json", [])
    decisions = {d["cid"]: d for d in load(ROOT / "triage" / "decisions.json", [])}
    retrieval = load(ROOT / "retrieval.json", {})
    rows, counts = [], Counter()
    for c in cands:
        cid = c["cid"]
        form = load(ROOT / "forms" / f"{cid}.json")
        dec = decisions.get(cid, {})
        challenges = [load(p) for p in sorted((ROOT / "forms" / "challenges").glob(f"{cid}.*.json"))]
        challenges = [x for x in challenges if x]
        check = load(ROOT / "forms" / "checks" / f"{cid}.json")
        cite = load(ROOT / "forms" / "citations" / f"{cid}.json")
        status, why = "pending", ""
        if form:
            el = form.get("eligibility", {})
            studies = form.get("studies", [])
            designs = sorted({s.get("design_class", "?") for s in studies})
            ns = [s.get("participants", {}).get("n_analyzed") for s in studies]
            ns = [n for n in ns if isinstance(n, int)]
            rec = form.get("reconciliation", {})
            refuted = [x.get("lens") for x in challenges if x.get("refuted")]
            fulltext = retrieval.get(cid, {}).get("status") == "ok"
            if el.get("core") == "yes":
                if refuted:
                    status, why = "clarify", "challenge refuted: " + ", ".join(refuted)
                elif rec.get("n_unresolved"):
                    status, why = "clarify", f"{rec.get('n_unresolved')} unresolved reconciliation item(s)"
                elif not fulltext:
                    status, why = "no_fulltext", "core by abstract only"
                else:
                    status = "core"
            elif el.get("core") == "unclear":
                status, why = "clarify", (el.get("reason") or "")[:140]
            elif el.get("criterion_1_random_assignment_of_ai") == "met" and el.get("criterion_2_at_least_50_people") == "not_met" \
                    and el.get("criterion_3_outcome_scored_on_output") != "not_met":
                status, why = "small", f"n analyzed {max(ns) if ns else '?'}"
            elif el.get("context_class") in ("ai_vs_human", "observational", "synthesis"):
                status = "context_" + el["context_class"]
            else:
                status, why = "excluded", (el.get("reason") or "")[:140]
            if not fulltext and status not in ("core", "no_fulltext"):
                why = ("[abstract only] " + why).strip()
            row_extra = {"designs": designs, "n": max(ns) if ns else None,
                         "screener": form.get("screener"), "n_diff": rec.get("n_differences"),
                         "challenges": {x.get("lens"): bool(x.get("refuted")) for x in challenges},
                         "check_agrees": (check or {}).get("agrees")}
        elif dec.get("path") == "out":
            status, why = "out", f"triage: {dec.get('a_reason')} / {dec.get('b_reason')}"
            row_extra = {}
        else:
            row_extra = {}
        counts[status] += 1
        rows.append({"cid": cid, "status": status, "why": why, "path": dec.get("path", "library" if c.get("library") else None),
                     "title": c["title"], "authors": c["authors"], "year": c["year"],
                     "fulltext": retrieval.get(cid, {}).get("status") == "ok", "has_citation": bool(cite), **row_extra})
    with io.open(ROOT / "status.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(dict(counts))
    for r in rows:
        if r["status"] != "pending" and r["status"] != "out":
            print(f"{r['cid']} {r['status']:22s} n={str(r.get('n')):>6s} {'/'.join(r.get('designs', []))[:28]:28s} "
                  f"{(r['authors'] or '')[:22]:22s} {r['year']} | {r['why'][:90]}")


if __name__ == "__main__":
    main()
