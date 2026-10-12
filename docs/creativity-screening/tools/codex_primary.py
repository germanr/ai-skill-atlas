"""Settle the primary-record ties that the builder reports, as two independent Codex proposals per paper.

Input: a ties file written by `node scripts/build-creativity.mjs --report-ties <file>` (one entry per tied pool key, with the
candidate estimate ids). For each paper, proposers A and B each choose one candidate per tie group by the rules below,
quoting the paper; a script compares them. Agreement becomes a proposal ready for review; disagreement is listed for the
main session to decide. Nothing is written to code/creativity/primary-overrides.json here: apply_primary.py does that after review.

Files: primary/<paper_key>.A.json, .B.json, primary/proposals.json.
Usage: python tools/codex_primary.py --ties <ties.json> [--workers 6]
"""
import argparse
import io
import json
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import codex_extract as E
import codex_pipeline as P

R = P.R
OUT = P.ROOT / "primary"
PAPERS = Path("C:/Dropbox/Admin/website/ai-skill-atlas/code/creativity/papers")

RULES = """Choose one candidate per tie group by these rules, in order; use a later rule only when the earlier ones do not separate
the candidates:
1. The outcome, contrast, or analysis that the preregistration or the paper names as primary or main (quote it).
2. The paper's main specification: the estimate its abstract or introduction reports (quote the sentence). Robustness variants
   (other controls, estimators, samples, thresholds, or metrics) lose to the main one. This rule compares specifications of
   one outcome; it never chooses between different outcomes (the builder already orders outcomes: overall creativity, novelty,
   usefulness, flexibility, fluency, elaboration). When the paper does not single out a specification, the one with no added
   covariates, fixed effects, or controls (the plain randomized contrast) wins.
3. Among different analyses of the same contrast and outcome (for example an ANOVA main effect and a two-group t-test of the
   same arms), the one whose printed or posted-data statistics allow a participant-level standardized effect: arm means with
   participant-level SDs and counts, or data_stats.
4. Repeated sessions of one contrast: the paper's own summary across sessions if it prints one; otherwise the session the
   abstract or introduction emphasizes; otherwise the first session with AI, the design most comparable to single-session studies.
5. Several AI arms sharing a control: the arm closest to free use of a general chatbot; then the paper's contrast of all AI arms
   combined against the shared control.
6. A full-sample contrast over contrasts within cells or subgroups. In a factorial design without one, the contrast in which AI
   access is the only difference between the arms (the other factor at its baseline level).
7. For after_ai: a task the person did not do with AI over a repeat of the task done with AI, whose originality can reflect
   recall of the AI's ideas.
Never choose by the size, sign, precision, or significance of the results. If no rule separates the candidates, say so and
leave "chosen" null."""


def prompt(paper_key, groups, cid, x):
    sup = []
    try:
        import codex_supplement as S
        sup = S.supplement_files(cid)
    except Exception:
        pass
    return "\n".join([
        f"You are proposer {x} for the primary records of one paper. {E.INTRO} Another proposer works independently; disagreements go to a person.",
        "", P.HOW_TO_WORK, "",
        f"Inputs: the paper's source file {PAPERS.as_posix()}/{paper_key}.json (studies, arms, and every estimate with its outcome, arms, "
        f"statistics, sources, notes, and any data_stats); the paper's PDF (\"pdf_path\" under key \"{cid}\" in {R}/retrieval.json"
        + (f"; for this paper use {E.C750_PDF}" if cid == "c750" else "") + ")"
        + (f"; the supplement files {json.dumps(sup, ensure_ascii=True)}" if sup else "") + f"; and the codebook {P.CODEBOOK}, section 8.",
        "",
        "The codebook's rules left these pool keys (sample, question, comparison type) with several equally ranked candidates:",
        json.dumps(groups, ensure_ascii=True, indent=1),
        "",
        RULES,
        "",
        f"Write {R}/primary/{paper_key}.{x}.json: an object with \"paper_key\" and \"choices\", a list with one object per tie group: "
        "\"pool_key\" (as given), \"chosen\" (one candidate estimate id, or null), \"rule\" (the number of the rule that decided), \"reason\" "
        "(one or two sentences), \"locator\", and \"quote\" (the passage that supports the choice, at most 40 words).",
        "",
        P.SUMMARY_NOTE + '"paper_key", "n_groups", and "n_chosen".',
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ties", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    ties = json.load(io.open(a.ties, encoding="utf-8"))
    by_paper = defaultdict(list)
    for t in ties:
        if t.get("candidates"):
            by_paper[t["paper_key"]].append({"pool_key": t["pool_key"], "candidates": t["candidates"]})
    OUT.mkdir(exist_ok=True)
    P.SLOTS = threading.Semaphore(a.workers)

    def run(paper_key):
        cid = json.load(io.open(PAPERS / f"{paper_key}.json", encoding="utf-8"))["cid"]
        for x in "AB":
            out = OUT / f"{paper_key}.{x}.json"
            if P.load(out) is None:
                P.run_until(f"primary{x}-{paper_key}", prompt(paper_key, by_paper[paper_key], cid, x), out)

    with ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(run, sorted(by_paper)))
    proposals = {"agreed": [], "disagreed": [], "undecided": []}
    for paper_key, groups in sorted(by_paper.items()):
        ca = {json.dumps(c.get("pool_key")): c for c in (P.load(OUT / f"{paper_key}.A.json") or {}).get("choices", [])}
        cb = {json.dumps(c.get("pool_key")): c for c in (P.load(OUT / f"{paper_key}.B.json") or {}).get("choices", [])}
        for g in groups:
            k = json.dumps(g["pool_key"])
            xa, xb = ca.get(k) or {}, cb.get(k) or {}
            item = {"paper_key": paper_key, "pool_key": g["pool_key"], "candidates": g["candidates"], "A": xa, "B": xb}
            if xa.get("chosen") and xa.get("chosen") == xb.get("chosen"):
                proposals["agreed"].append(item)
            elif not xa.get("chosen") and not xb.get("chosen"):
                proposals["undecided"].append(item)
            else:
                proposals["disagreed"].append(item)
    with io.open(OUT / "proposals.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(proposals, fh, ensure_ascii=False, indent=1)
    P.log_line(f"primary proposals: agreed {len(proposals['agreed'])}, disagreed {len(proposals['disagreed'])}, undecided {len(proposals['undecided'])}")


if __name__ == "__main__":
    main()
