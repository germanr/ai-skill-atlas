"""Find the printed people counts of randomized studies whose extraction left n_analyzed empty (Review 1 Decision 1a: the
analyzed count decides the 50-person rule).

One Codex job per paper writes extraction/checks/<cid>.counts.json: for each listed study, the number of people analyzed
and the number randomized, each with its locator and verbatim quote, per arm where printed. Counts are never inferred from
degrees of freedom, ideas, ratings, or arithmetic on other numbers. A script then checks every quote against the cited PDF
pages; the main session applies the counts as review_corrections.

Usage: python tools/codex_counts.py [--workers 4] [--only c057 ...]
"""
import argparse
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import codex_extract as E
import codex_pipeline as P
import codex_supplement as SUP
import extract_checks as X

R = P.R
EXT = E.EXT
PAPERS = Path("C:/Dropbox/Admin/website/ai-skill-atlas/code/creativity/papers")
RCTS = {"lab_rct", "online_rct", "field_rct", "unstated_rct"}


def missing_counts():
    """{cid: [study_id, ...]} for verified source files whose randomized studies have no analyzed count."""
    out = {}
    for f in sorted(PAPERS.glob("*.json")):
        d = P.load(f) or {}
        if d.get("status") != "verified":
            continue
        ids = [s["study_id"] for s in d.get("studies", []) if s.get("design_class") in RCTS and not isinstance(s.get("n_analyzed"), int)]
        if ids:
            out[d["cid"]] = ids
    return out


def prompt(cid, study_ids):
    return "\n".join([
        f"You check participant counts for one paper. {E.INTRO}",
        "", P.HOW_TO_WORK, "",
        E.inputs_block(cid), "",
        f"The extraction file {R}/extraction/{cid}.json left n_analyzed empty for these randomized studies: {', '.join(study_ids)}. "
        "For each, read the paper (method, results, tables, figure notes, appendices, and any supplement named in the extraction "
        "file's sources) and find:",
        "- n_analyzed: the number of people whose data enter the paper's analyses of its creativity outcomes. People, never ideas, "
        "essays, ratings, or pairs of outputs; in a within-person design each person counts once. If different creativity analyses "
        "use different counts, give the count of the analysis the extraction file treats as main and list the others in \"other_counts\".",
        "- n_randomized: the number of people randomized or enrolled, if printed.",
        "- per-arm counts, where printed.",
        "Each number needs the locator (PDF page and section, table, or figure note) and a verbatim quote that prints it. Record only "
        "numbers the paper prints. Never infer a count from degrees of freedom, from ideas or ratings, or by arithmetic on other numbers "
        "(if the paper prints only enrolled people and exclusions, report both as printed and leave n_analyzed null).",
        "",
        f"Write {R}/extraction/checks/{cid}.counts.json: {{\"cid\", \"studies\": [{{\"study_id\", \"n_analyzed\", \"n_analyzed_locator\", "
        "\"n_analyzed_quote\", \"n_randomized\", \"n_randomized_locator\", \"n_randomized_quote\", \"arms\": [{\"name\", \"n_analyzed\", "
        "\"n_randomized\", \"locator\", \"quote\"}], \"other_counts\": [{\"count\", \"what\", \"locator\", \"quote\"}], \"notes\"}]}. "
        "Use the arm names of the extraction file.",
        "",
        P.SUMMARY_NOTE + '"cid" and, per study, "n_analyzed" and "n_randomized".',
    ])


def check(cid):
    """Quote and number checks for a counts file, against the paper's PDF and its supplements."""
    d = P.load(EXT / "checks" / f"{cid}.counts.json") or {}
    pages = X.pdf_pages(E.pdf_of(cid))
    extras = [X.pdf_pages(p) for p in SUP.supplement_pdfs(cid)]

    def found(quote, locator):
        # As in the mechanical check: the cited main-PDF page (one page either side), else anywhere in a supplement.
        if X.quote_on_pages(quote, pages, X.cited_pages(locator or "")):
            return True
        return any(X.quote_on_pages(quote, extra, []) for extra in extras)

    problems = []
    for s in d.get("studies") or []:
        items = [("n_analyzed", s.get("n_analyzed"), s.get("n_analyzed_locator"), s.get("n_analyzed_quote")),
                 ("n_randomized", s.get("n_randomized"), s.get("n_randomized_locator"), s.get("n_randomized_quote"))]
        items += [(f"arm {a.get('name')}", a.get("n_analyzed") if a.get("n_analyzed") is not None else a.get("n_randomized"),
                   a.get("locator"), a.get("quote")) for a in s.get("arms") or []]
        for field, value, locator, quote in items:
            if value is None:
                continue
            if not quote or not found(quote, locator):
                problems.append({"study_id": s.get("study_id"), "field": field, "problem": "quote not found on the cited pages"})
            elif not X.number_in_quote(float(value), quote):
                problems.append({"study_id": s.get("study_id"), "field": field, "problem": f"{value} is not printed in the quote"})
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    todo = missing_counts()
    if a.only:
        todo = {c: v for c, v in todo.items() if c in a.only}
    P.SLOTS = threading.Semaphore(a.workers)
    P.log_line(f"counts: {len(todo)} papers: {' '.join(todo)}")

    def run(cid):
        out = EXT / "checks" / f"{cid}.counts.json"
        if P.load(out) is None:
            P.run_until(f"counts-{cid}", prompt(cid, todo[cid]), out)
        if P.load(out) is None:
            P.log_line(f"STOP   {cid}: no counts output")
            return
        problems = check(cid)
        P.log_line(f"FINAL  {cid} counts: {json.dumps([(s.get('study_id'), s.get('n_analyzed'), s.get('n_randomized')) for s in P.load(out).get('studies') or []])} | check problems: {len(problems)}")
        with io.open(EXT / "checks" / f"{cid}.counts-check.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"cid": cid, "problems": problems}, fh, ensure_ascii=False, indent=1)

    with ThreadPoolExecutor(max(1, a.workers)) as pool:
        list(pool.map(run, sorted(todo)))


if __name__ == "__main__":
    main()
