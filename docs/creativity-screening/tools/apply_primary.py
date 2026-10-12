"""Review and apply primary-record proposals (primary/proposals.json) to code/creativity/primary-overrides.json.

Without --apply: prints every agreed proposal (chosen estimate, rule, reason, quote) and every disagreement, and writes nothing.
With --apply: writes the agreed proposals, and the main session's own decisions in primary/decisions.json (a list of
{"paper_key", "slug", "reason"} for disagreements and undecided groups), as primary_override entries. A pool key that
already has an override is left alone.

Usage: python tools/apply_primary.py [--apply]
"""
import argparse
import io
import json
from datetime import date
from pathlib import Path

S = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
OV = Path("C:/Dropbox/Admin/website/ai-skill-atlas/code/creativity/primary-overrides.json")


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


def slug_of(estimate_id, paper_key):
    return estimate_id[len(paper_key) + 2:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    prop = load(S / "primary" / "proposals.json", {}) or {}
    decisions = load(S / "primary" / "decisions.json", []) or []
    ov = load(OV)
    existing = {(k, e["slug"]) for k, lst in ov["papers"].items() for e in lst}
    to_write = []
    for item in prop.get("agreed", []):
        k = item["paper_key"]
        chosen = item["A"]["chosen"]
        slug = slug_of(chosen, k)
        print(f"AGREED  {k} {item['pool_key'][1:]} -> {slug} (rules {item['A'].get('rule')}/{item['B'].get('rule')})")
        print(f"        A: {item['A'].get('reason')} [{item['A'].get('locator')}: {item['A'].get('quote')}]")
        print(f"        B: {item['B'].get('reason')}")
        to_write.append((k, slug, f"Rule {item['A'].get('rule')}: {item['A'].get('reason')} ({item['A'].get('locator')}: \"{item['A'].get('quote')}\")",
                         "two independent Codex proposers (agreed); reviewed by Claude (main session)"))
    for kind in ("disagreed", "undecided"):
        for item in prop.get(kind, []):
            print(f"{kind.upper():9} {item['paper_key']} {item['pool_key'][1:]}: A -> {item['A'].get('chosen')} | B -> {item['B'].get('chosen')}")
            print(f"        A: {item['A'].get('reason')}")
            print(f"        B: {item['B'].get('reason')}")
    for d in decisions:
        to_write.append((d["paper_key"], d["slug"], d["reason"], "Claude (main session), after the two proposers disagreed or left it open"))
    if not a.apply:
        print(f"\n{len(to_write)} overrides would be written; run with --apply after review.")
        return
    n = 0
    for k, slug, reason, by in to_write:
        if (k, slug) in existing:
            continue
        ov["papers"].setdefault(k, []).append({"slug": slug, "primary_override": True, "reason": reason, "decided_by": by,
                                               "date": date.today().isoformat()})
        n += 1
    with io.open(OV, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ov, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"written: {n} overrides")


if __name__ == "__main__":
    main()
