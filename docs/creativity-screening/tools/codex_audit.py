"""Audit the assembled screening report with Codex jobs: finder lanes, then an independent verifier
for each finder's findings. One round per invocation: fix what is confirmed (in the forms, the
citation files, the builder, or report-prose.md), rebuild and reassemble, then run the next round.

Usage: python codex_audit.py [<report.md>] [--workers 8] [--lanes prose,coverage,links,tables,classes,sources,citations]
       python codex_audit.py --verify-only <audit folder>   (rerun verification for a finished finder round)

Lanes and their scope:
  prose      every number in the hand-written and assembled prose against report-data.json and the tables (1 job)
  coverage   every candidate id appears once across the report and identified-not-screened.md (1 job)
  links      every URL in the report resolves to the right work (1 job, network)
  tables     table cells of the core, clarification, small, and reclassification sections against the forms
  classes    the status of every screened paper against the codebook rules and its form
  sources    the statistics in the notes on recommended papers against the PDF itself
  citations  author labels, titles, venues, years, and DOIs of screened papers against the citation files and Crossref (network)
Output: audit/<stamp>/round/<lane-batch>.json (findings), verify-<lane-batch>.json (verdicts), summary.json.
"""
import argparse
import io
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_pipeline as cp  # noqa: E402

ROOT = cp.ROOT
R = cp.R
CODEBOOK = cp.CODEBOOK
REPORT = ROOT.parent / "creativity-screening-2026-10-04.md"

INTRO = ("You are auditing a literature screening report for the AI and Human Skill Atlas (aiskillatlas.org), a living meta-analysis "
         "that is adding a section on generative AI and creativity. The report must contain no number, name, or classification that its "
         "sources do not support. Report only problems you verified yourself. An empty list is a valid and common result.")

RULES = (f"Working rules: you run as a Codex job with {R} as your workspace. Read any file you need; write only the output file named "
         "below. Create no other files and change nothing else. Use python for reading files and JSON, for PDF text (pymupdf: "
         "doc[page_index].get_text()), and for any web request (User-Agent \"atlas-screening/0.1\", no email address). "
         "In python source, write every non-ASCII character as a \\u escape; the console loses it otherwise. "
         "Your final message is the number of findings, nothing else.")

SOURCES = (f"Sources: the report is {{report}}. It is assembled by {R}/tools/assemble_report.py from {R}/report-prose.md (hand-written "
           f"prose with computed counts), {R}/report-generated.md (tables built by {R}/tools/build_report.py), and {R}/report-data.json "
           f"(every count, plus status_by_cid). Each paper's screening form is {R}/forms/<cid>.json (finalized forms carry a 'final' "
           f"object); short forms have checker files in {R}/forms/checks/; challenges in {R}/forms/challenges/; citation checks in "
           f"{R}/forms/citations/<cid>.json. Candidates: {R}/candidates.json. Triage: {R}/triage/decisions.json. Full texts: "
           f"{R}/retrieval.json gives pdf_path and md_path for each cid. Codebook: {CODEBOOK}. Form spec: {R}/form-spec.md.")

FINDINGS = ('Write a JSON list to {out}. Each finding is an object: {{"id": "{name}-<n>", "cid": "<paper id or null>", '
            '"section": "<report section>", "location": "<row, cell, or quoted phrase>", "claim": "<what the report says>", '
            '"problem": "<what is wrong>", "evidence": "<file and field, or PDF page, and the value found there>", '
            '"severity": "blocker" | "serious" | "minor"}}. Severity: blocker = a wrong status or a wrong number that a reader would '
            'act on; serious = a wrong value or label; minor = wording or formatting. Write [] when you found nothing. Confirm with '
            'python that the file parses.')

LANES = {
    "prose": ("PROSE NUMBERS. Read every sentence of the report outside the tables, including the bullet lists. For each number, "
              "count, or named total, find its value in report-data.json, in the tables of the report, or in the files named in the "
              "sentence, and compare. Check that counts that should add up do add up (for example the status table against its total "
              "and the prose summary against the table). Check each claim about a named paper in the prose against that paper's form "
              "or citation file. Record every mismatch and every number with no source."),
    "coverage": ("COVERAGE. With python, collect every id c001 to c1002 from candidates.json, and every [cNNN] id in the report and in "
                 f"{R}/identified-not-screened.md. Each candidate must appear exactly once across the report's status sections "
                 "(recommended, needs clarification, full text not obtained, small, the three context sections, excluded after "
                 "screening, excluded at triage) plus identified-not-screened.md. The reclassification table, the diversity table, "
                 "and the after-AI table may repeat ids. Record every id missing, every id in two status sections, every id that "
                 "candidates.json lacks, and every status section whose row count differs from the status table."),
    "links": ("LINKS. With python, extract every URL in the report (deduplicate), and request each with GET, a 30-second timeout, a "
              "browser-like User-Agent, and no email address, in parallel threads. For DOIs, also query the Crossref API "
              "(https://api.crossref.org/works/<doi>) and compare the returned title with the title in the report row. Record every "
              "URL that answers 404 or 410, every malformed DOI, and every DOI whose Crossref title is a different work. A 403, a "
              "timeout, or a bot check is not a finding."),
    "tables": ("TABLE CELLS. For each paper id in your batch, find its rows in the report (the recommended table and its note, the "
               "clarification table, the small-experiments table, and the reclassification table). Compare every cell with "
               "forms/<cid>.json: people analyzed per study, design, sample, AI role, task, questions answered, statistics location, "
               "the reason or finding text, and each reported contrast quoted in the note. Record every cell the form does not support "
               "and every truncation that changes the meaning."),
    "classes": ("CLASSIFICATION. For each paper id in your batch, read the codebook's eligibility rules and the paper's form "
                "(eligibility, final, studies[].assignment, participants, outcomes). Decide which status the rules support: "
                "recommended (people randomly assigned to generative-AI assistance, at least 50 people analyzed in one randomized "
                "study, and an outcome scored on the output that compares randomized arms, with no open item that undermines one of "
                "these), needs clarification (one of these is unclear), small (randomized, scored on output, fewer than 50 analyzed), "
                "context (AI versus human output, observational, or synthesis), or excluded (a criterion fails). Watch for outcomes "
                "that compare self-selected subgroups (for example heavy versus light users) instead of randomized arms, and for "
                "self-reported creativity. Compare with the report's status (report-data.json status_by_cid). Record every paper "
                "whose report status the form and the rules do not support, with the status they support. Where the form itself "
                "looks wrong, open the PDF and say what the paper says."),
    "sources": ("SOURCES. For each paper id in your batch, read its entry in 'Notes on each recommended paper' in the report. Open the "
                "paper's PDF (pdf_path in retrieval.json) and verify, at the cited page or table, every statistic, count, percentage, "
                "and page reference in the entry, and the one-line finding. Check against the document itself, not against the form. "
                "Record every value that the document does not show at the cited place, with the value it does show and where."),
    "citations": ("CITATIONS. For each paper id in your batch, compare the report's author label, title, venue, year, and link with "
                  "forms/citations/<cid>.json, and confirm the DOI in the Crossref API (https://api.crossref.org/works/<doi>): same "
                  "title, same first author, same year (or the year the citation file explains). Labels follow this rule: one author, "
                  "Family; two, A and B; three, A, B, and C; four or more, A et al.; family names keep particles such as de and van. "
                  "Record every mismatch and every label that breaks the rule."),
}

VERIFY = ("You are an independent verifier. Another auditor reported the findings in {findings}. Check each finding yourself against "
          "the report and the source it names; for a number in a paper, open the PDF at the cited place. Do not trust the auditor's "
          "quotes. For each finding decide: \"confirmed\" (the report is wrong as the finding says), \"refuted\" (the report is "
          "right), or \"cannot_tell\". For a confirmed finding, name where the fix belongs: \"form\" (the screening form has the "
          "wrong value; give the field and the correct value with page), \"citation\" (the citation file is wrong), \"builder\" "
          "(the table generator or assembler mishandles a correct form), or \"prose\" (report-prose.md), and give the exact correct "
          "text or value. Write a JSON list to {out}: [{{\"id\": \"...\", \"cid\": \"...\", \"verdict\": \"confirmed\" | \"refuted\" | "
          "\"cannot_tell\", \"fix_target\": \"form\" | \"citation\" | \"builder\" | \"prose\" | null, \"field\": \"...\", "
          "\"correct_value\": \"...\", \"evidence\": \"<file or page and what it shows>\"}}]. Confirm with python that it parses.")


def section_ids(text):
    """Map each '## ' section of the report to the ordered list of [cNNN] ids it contains."""
    out = {}
    for part in re.split(r"(?m)^## ", text)[1:]:
        head = part.split("\n", 1)[0].strip()
        out[head] = list(dict.fromkeys(re.findall(r"\[(c\d{3,4})\]", part)))
    return out


def chunks(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


def finder_prompt(lane, name, report, out, batch=None):
    parts = [INTRO, "", RULES, "", SOURCES.format(report=report), "", "Lane: " + LANES[lane]]
    if batch:
        parts += ["", f"Your batch: {', '.join(batch)}."]
    parts += ["", FINDINGS.format(out=out, name=name)]
    return "\n".join(parts)


def verify_prompt(report, findings_path, out):
    return "\n".join([INTRO, "", RULES, "", SOURCES.format(report=report), "", VERIFY.format(findings=findings_path, out=out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", nargs="?", default=str(REPORT))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--lanes", default="prose,coverage,links,tables,classes,sources,citations")
    ap.add_argument("--verify-only")
    a = ap.parse_args()
    report = str(Path(a.report).resolve()).replace("\\", "/")
    cp.SLOTS = threading.Semaphore(a.workers)

    if a.verify_only:
        base = Path(a.verify_only)
    else:
        base = ROOT / "audit" / datetime.now().strftime("%Y-%m-%d_%H%M")
        base.mkdir(parents=True, exist_ok=True)
    cp.JOBS = base / "jobs"
    cp.JOBS.mkdir(parents=True, exist_ok=True)

    text = io.open(report, encoding="utf-8").read()
    sec = section_ids(text)
    core = sec.get("Recommended for the core dataset", [])
    clar = sec.get("Candidates that need clarification", [])
    small = sec.get("Randomized experiments under 50 participants", [])
    ctx = [c for h in ("Context: AI versus human output", "Context: observational", "Context: syntheses") for c in sec.get(h, [])]
    excl = sec.get("Excluded after screening", [])
    lib = sec.get("Reclassification of the current collection", [])
    uniq = lambda xs: list(dict.fromkeys(xs))
    scope = {
        "tables": uniq(core + clar + small + lib),
        "classes": uniq(core + clar + small + excl + lib),
        "sources": core,
        "citations": uniq(core + clar + small + ctx),
    }
    size = {"tables": 30, "classes": 20, "sources": 3, "citations": 25}

    jobs = []
    for lane in a.lanes.split(","):
        if lane in ("prose", "coverage", "links"):
            jobs.append((lane, lane, None))
        else:
            for i, b in enumerate(chunks(scope[lane], size[lane])):
                jobs.append((f"{lane}-{i:02d}", lane, b))
    net = {"links", "citations"}

    if not a.verify_only:
        cp.log_line(f"finders: {len(jobs)} jobs | scope sizes: { {k: len(v) for k, v in scope.items()} }")

        def run_finder(job):
            name, lane, batch = job
            out = str(base / f"{name}.json").replace("\\", "/")
            ok = cp.run_until(f"find-{name}", finder_prompt(lane, name, report, out, batch), base / f"{name}.json", network=lane in net)
            return name, ok

        with ThreadPoolExecutor(a.workers) as pool:
            done = list(pool.map(run_finder, jobs))
        cp.log_line(f"finders done; unreadable outputs: {[n for n, ok in done if not ok]}")

    # Verification: one independent job per finder file with findings.
    todo = []
    for name, lane, _ in jobs:
        found = cp.load(base / f"{name}.json")
        if isinstance(found, list) and found:
            todo.append((name, lane, len(found)))
    cp.log_line(f"verifiers: {len(todo)} jobs for {sum(n for _, _, n in todo)} findings")

    def run_verifier(item):
        name, lane, _ = item
        out = str(base / f"verify-{name}.json").replace("\\", "/")
        cp.run_until(f"verify-{name}", verify_prompt(report, str(base / f"{name}.json").replace("\\", "/"), out),
                     base / f"verify-{name}.json", network=lane in net)

    with ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(run_verifier, todo))

    summary = {"findings": 0, "confirmed": 0, "refuted": 0, "cannot_tell": 0, "by_lane": {}, "confirmed_items": []}
    for name, lane, _ in jobs:
        found = cp.load(base / f"{name}.json") or []
        verdicts = cp.load(base / f"verify-{name}.json") or []
        vmap = {v.get("id"): v for v in verdicts if isinstance(v, dict)}
        lane_stats = summary["by_lane"].setdefault(lane, {"findings": 0, "confirmed": 0})
        for f in found if isinstance(found, list) else []:
            summary["findings"] += 1
            lane_stats["findings"] += 1
            v = vmap.get(f.get("id"), {"verdict": "cannot_tell"})
            key = v.get("verdict") if v.get("verdict") in ("confirmed", "refuted") else "cannot_tell"
            summary[key] += 1
            if key == "confirmed":
                lane_stats["confirmed"] += 1
                summary["confirmed_items"].append({**f, "verdict": v})
    json.dump(summary, io.open(base / "summary.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    cp.log_line(f"audit done: {summary['findings']} findings, {summary['confirmed']} confirmed, {summary['refuted']} refuted, "
                f"{summary['cannot_tell']} undecided | {base / 'summary.json'}")


if __name__ == "__main__":
    main()
