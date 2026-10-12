"""Combine the two independent triage passes and assign each candidate a screening path.

Paths:
  experiment_full   either screener calls it an experiment (unless both state fewer than 50 people)
  experiment_small  an experiment for which both screeners read fewer than 50 participants
  context           no screener calls it an experiment and at least one calls it context
  out               both screeners call it out
Library papers always get a full-text path. Writes triage/decisions.json and prints a report.
"""
import io
import json
from collections import Counter
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
VERDICTS = {"experiment", "context_ai_vs_human", "context_observational", "context_synthesis", "out"}


def main():
    cands = json.load(io.open(ROOT / "candidates.json", encoding="utf-8"))
    by = {c["cid"]: {} for c in cands}
    problems = []
    for path in sorted((ROOT / "triage").glob("batch-*.json")):
        try:
            data = json.load(io.open(path, encoding="utf-8"))
        except Exception as exc:
            problems.append(f"{path.name}: does not parse ({exc})")
            continue
        screener = data.get("screener") or path.stem.split(".")[-1]
        for item in data.get("items", []):
            cid = item.get("cid")
            if cid not in by:
                problems.append(f"{path.name}: unknown cid {cid!r}")
                continue
            if item.get("verdict") not in VERDICTS:
                problems.append(f"{path.name}: {cid} verdict {item.get('verdict')!r}")
            by[cid][screener] = item

    decisions, stats, disagreements = [], Counter(), []
    for c in cands:
        cid = c["cid"]
        a, b = by[cid].get("A"), by[cid].get("B")
        va, vb = (a or {}).get("verdict"), (b or {}).get("verdict")
        na, nb = (a or {}).get("n_participants"), (b or {}).get("n_participants")
        in_lib = bool(c.get("library"))
        if a is None or b is None:
            path = "untriaged"
        elif "experiment" in (va, vb):
            small = isinstance(na, int) and isinstance(nb, int) and na < 50 and nb < 50
            path = "experiment_small" if small and not in_lib else "experiment_full"
        elif va == "out" and vb == "out":
            path = "context" if in_lib else "out"
        else:
            path = "context"
        agree = va == vb
        stats[path] += 1
        stats["agree" if agree else "disagree"] += 1
        if not agree:
            disagreements.append((cid, va, vb, (c["title"] or "")[:70]))
        decisions.append({
            "cid": cid, "path": path, "in_library": in_lib, "title": c["title"],
            "a": va, "b": vb, "agree": agree,
            "a_reason": (a or {}).get("out_reason"), "b_reason": (b or {}).get("out_reason"),
            "n_a": na, "n_b": nb,
            "randomized_a": (a or {}).get("randomized"), "randomized_b": (b or {}).get("randomized"),
            "outcome_a": (a or {}).get("outcome_on_output"), "outcome_b": (b or {}).get("outcome_on_output"),
            "abstract_found": [(a or {}).get("abstract_found"), (b or {}).get("abstract_found")],
            "note_a": (a or {}).get("note", ""), "note_b": (b or {}).get("note", ""),
        })
    with io.open(ROOT / "triage" / "decisions.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(decisions, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("candidates:", len(cands), dict(stats))
    pair = Counter((d["a"], d["b"]) for d in decisions)
    for (va, vb), n in sorted(pair.items(), key=lambda kv: -kv[1]):
        print(f"  A={va!s:24s} B={vb!s:24s} {n}")
    print("out reasons:", dict(Counter(d["a_reason"] for d in decisions if d["path"] == "out")))
    print("disagreements:", len(disagreements))
    for row in disagreements[:80]:
        print("  ", row)
    print("problems:", len(problems))
    for line in problems[:40]:
        print("  ", line)


if __name__ == "__main__":
    main()
