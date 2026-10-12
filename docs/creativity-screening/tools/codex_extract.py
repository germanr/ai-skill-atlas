"""Phase 2 extraction as Codex jobs, one chain per paper.

Chain: two independent extractions (A reads the text first, B the tables first) -> a script lists their differences ->
a reconciler settles each difference against the PDF -> a script checks every number against its quote and every quote
against the cited PDF page -> a verifier, who sees only the reconciled numbers and their sources, confirms each number
-> if anything is flagged, a fixer corrects or defends it, and a second verifier rechecks what the fixer touched.

Files (under docs/creativity-screening/extraction/): raw/<cid>.A.json, raw/<cid>.B.json, diffs/<cid>.json, <cid>.json
(reconciled, later fixed), checks/<cid>.mech.json, checks/<cid>.verify.json, checks/<cid>.reverify.json,
status/<cid>.json. The files on disk decide what each paper still needs, so a run can be relaunched as is.

Usage: python tools/codex_extract.py [--workers 8] [--only c006 c159 ...]
Germ\u00e1n, 2026-10-09: "start phase 2". Scope: the recommended papers minus the three that Review 1 Decision 9 moves out.
"""
import argparse
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import codex_pipeline as P
import extract_checks as X

P.JOB_TIMEOUT = 80 * 60
EXT = P.ROOT / "extraction"
R = P.R
SPEC = f"{R}/extraction-spec.md"
MOVED_OUT = {"c044", "c276", "c818"}  # Review 1 Decision 9: one class per arm
C750_PDF = "C:/Dropbox/Admin/website/ai-skill-atlas/public/pdfs/Contractor & Reyes (2026-09) - AI Learning RCT.pdf"

INTRO = ("This is part of the data extraction for the creativity section of the AI and Human Skill Atlas (aiskillatlas.org), "
         "a living meta-analysis. A verifier and a script check every number you record against the PDF, so accuracy matters "
         "more than speed.")

HOW_READ = {
    "A": "How to read the paper: read the markdown from start to end, design and methods before results. Then extract the text of every PDF page you cite with pymupdf and confirm each number on that page.",
    "B": "How to read the paper: start with the PDF. Go through its tables, figures, appendix, and any supplement on file first, and list every statistic reported for the outcomes in scope. Then read the design and methods to establish the arms and the counts. Confirm each number on the PDF page with pymupdf.",
}


def pdf_of(cid):
    if cid == "c750":
        return C750_PDF
    ret = P.load(P.ROOT / "retrieval.json") or {}
    return (ret.get(cid) or {}).get("pdf_path")


def inputs_block(cid):
    lines = [P.files_block(cid),
             f"- Its reconciled screening form is {R}/forms/{cid}.json: studies, arms, participants, outcomes, contrasts (with the text and locators found at screening), sample_overlap, and final.open_items. Use it as a map and check everything against the paper.",
             f"- Its citation record is {R}/forms/citations/{cid}.json.",
             f"- The rules: {SPEC} (the extraction file) and {P.CODEBOOK} (the codebook). Read both first."]
    if cid == "c750":
        lines.append(f"- For this paper, read the September 2026 version instead of the file in retrieval.json: {C750_PDF}. Rule 6 of the extraction file applies.")
    return "\n".join(lines)


def extract_prompt(cid, x):
    return "\n".join([
        f"You are extractor {x} for one paper. {INTRO} Another extractor fills the same file independently; a reconciler then settles every difference against the PDF.",
        "", P.HOW_TO_WORK, "",
        inputs_block(cid), "",
        HOW_READ[x], "",
        f"Fill the extraction file described in {SPEC} for paper {cid}, with \"extractor\": \"{x}\". Write it to {R}/extraction/raw/{cid}.{x}.json.",
        "",
        P.SUMMARY_NOTE + '"cid", "n_studies", "n_estimates", and "n_not_extracted".',
    ])


def reconcile_prompt(cid):
    return "\n".join([
        f"You are the reconciler for one paper. {INTRO}",
        "", P.HOW_TO_WORK, "",
        inputs_block(cid), "",
        f"Two extractors filled the extraction file for {cid} independently: {R}/extraction/raw/{cid}.A.json and {R}/extraction/raw/{cid}.B.json. "
        f"A script compared them: {R}/extraction/diffs/{cid}.json lists every study field and every estimate field where they differ, and the estimates "
        "that only one of them has (only_in_a, only_in_b).",
        "",
        "Your tasks:",
        "1. Settle every difference against the PDF. Open the cited page, read what is printed, and keep the right value. When both are wrong, write the right one.",
        "2. For each estimate only one extractor has, decide from the paper whether it belongs (rule 4 and 5 of the extraction file).",
        "3. Check that every in-scope outcome and contrast of the screening form appears, or is listed in not_extracted with a reason. Add what both extractors missed.",
        "4. Check the fields both extractors agree on for the counts, the question, the construct, the unit, higher_is, outcome_with_ai, and within_person: agreement is not proof.",
        "",
        f"Write the reconciled file to {R}/extraction/{cid}.json, with the structure of the extraction file, \"extractor\": \"reconciled\", and one more key, "
        '"resolutions": a list of objects with "where" (slug and field, or study and field), "a", "b", "decision", "locator", and "quote".',
        "",
        P.SUMMARY_NOTE + '"cid", "n_estimates", "n_resolutions", and "n_added".',
    ])


def verify_prompt(cid, problems, only=None):
    scope = ("every estimate in the file" if not only else
             "only these estimates, which a fixer changed or defended after the first verification: " + ", ".join(only))
    return "\n".join([
        f"You are the verifier for one paper. {INTRO} You did not take part in the extraction, and your job is to find what is wrong.",
        "", P.HOW_TO_WORK, "",
        f"Inputs: the reconciled extraction file {R}/extraction/{cid}.json and the paper (PDF at \"pdf_path\" under key \"{cid}\" in {R}/retrieval.json"
        + (f"; for this paper use {C750_PDF}" if cid == "c750" else "") + f"). The rules are in {SPEC} and {P.CODEBOOK}. "
        "Do not read the raw extractions, the diffs, or the resolutions: judge the numbers only against the paper.",
        "",
        f"Check {scope}. For each one, open the page each source cites and confirm: (a) each number in stats and in the counts is printed there with that value; "
        "(b) it belongs to this outcome, this contrast, and these arms; (c) the counts are the counts of this analysis; (d) question, construct, measure, unit, "
        "higher_is, outcome_with_ai, outcome_timing, within_person, comparison_type, and se_basis are right under the codebook. Also check that no in-scope "
        "outcome or contrast is missing (extraction file, rules 4 to 6).",
        "",
        "A script already checked every number against its quote and every quote against the cited page. It reported these problems, which you must settle: "
        + (json.dumps(problems, ensure_ascii=True)[:12000] if problems else "none") + ".",
        "",
        f"Write {R}/extraction/checks/{cid}." + ("reverify" if only else "verify") + ".json: an object with \"cid\", \"checked\" (the number of estimates "
        "you checked), \"problems\" (a list of objects with \"slug\", \"field\", \"status\" (\"wrong\", \"not_found\", \"wrong_scope\", \"wrong_code\", or "
        "\"missing_estimate\"), \"recorded\", \"printed\", \"locator\", \"quote\", and \"note\"), and \"summary\". An empty problems list means you confirmed everything.",
        "",
        P.SUMMARY_NOTE + '"cid", "checked", and "n_problems".',
    ])


def fix_prompt(cid):
    return "\n".join([
        f"You are the fixer for one paper. {INTRO}",
        "", P.HOW_TO_WORK, "",
        inputs_block(cid), "",
        f"The reconciled extraction file is {R}/extraction/{cid}.json. A verifier reported problems in {R}/extraction/checks/{cid}.verify.json, and a "
        f"script reported problems in {R}/extraction/checks/{cid}.mech.json. For each problem, check the paper. Correct the file where the problem is real, "
        "and keep the value where the verifier or the script is wrong, with the passage that shows it.",
        "",
        f"Rewrite {R}/extraction/{cid}.json in place, keeping everything else. Add a key \"fixes\" (a list of objects with \"slug\", \"field\", \"old\", "
        "\"new\", \"locator\", \"quote\", and \"basis\") and a key \"kept\" (a list of objects with \"slug\", \"field\", \"value\", \"locator\", \"quote\", "
        "and \"why_the_flag_is_wrong\").",
        "",
        P.SUMMARY_NOTE + '"cid", "n_fixes", "n_kept", and "changed_slugs".',
    ])


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)


def mech(cid, name):
    ext = P.load(EXT / f"{cid}.json")
    problems = X.mechanical_check(ext, pdf_of(cid))
    save(EXT / "checks" / f"{cid}.{name}.json", {"cid": cid, "problems": problems, "pdf": pdf_of(cid),
                                                 "checked_at": datetime.now().isoformat(timespec="seconds")})
    return problems


def chain(cid):
    raw = {x: EXT / "raw" / f"{cid}.{x}.json" for x in "AB"}
    todo = [x for x in "AB" if P.load(raw[x]) is None]
    if todo:
        with ThreadPoolExecutor(len(todo)) as pool:
            list(pool.map(lambda x: P.run_until(f"extract{x}-{cid}", extract_prompt(cid, x), raw[x]), todo))
    a, b = P.load(raw["A"]), P.load(raw["B"])
    if a is None or b is None:
        P.log_line(f"STOP   {cid}: an extraction is missing")
        return
    save(EXT / "diffs" / f"{cid}.json", X.diff_extractions(a, b))
    if P.load(EXT / f"{cid}.json") is None:
        P.run_until(f"reconcile-{cid}", reconcile_prompt(cid), EXT / f"{cid}.json")
    if P.load(EXT / f"{cid}.json") is None:
        P.log_line(f"STOP   {cid}: no reconciled file")
        return
    problems = mech(cid, "mech")
    ver = EXT / "checks" / f"{cid}.verify.json"
    if P.load(ver) is None:
        P.run_until(f"verify-{cid}", verify_prompt(cid, problems), ver)
    v = P.load(ver)
    if v is None:
        # A failed verifier (for example, a usage limit) must not read as zero problems.
        P.log_line(f"STOP   {cid}: no verifier output")
        return
    status = {"cid": cid, "mech_problems": len(problems), "verify_problems": len(v.get("problems") or [])}
    ext = P.load(EXT / f"{cid}.json") or {}
    # The verifier settles the script's flags: a fixer runs only when the verifier confirms a problem.
    if v.get("problems") and "fixes" not in ext:
        P.run_until(f"fix-{cid}", fix_prompt(cid), EXT / f"{cid}.json")
        ext = P.load(EXT / f"{cid}.json") or {}
        if "fixes" not in ext:
            P.log_line(f"STOP   {cid}: the verifier found problems but the fixer left no output")
            return
    if "fixes" in ext:
        # The second verifier rechecks every estimate the fixer touched: the values it changed and the values it kept
        # against a flag.
        changed = sorted({f.get("slug") for f in (ext.get("fixes") or []) + (ext.get("kept") or []) if f.get("slug")})
        problems2 = mech(cid, "mech2")
        status["mech2_problems"] = len(problems2)
        rv = EXT / "checks" / f"{cid}.reverify.json"
        if changed and P.load(rv) is None:
            P.run_until(f"reverify-{cid}", verify_prompt(cid, problems2, only=changed), rv)
        if changed and P.load(rv) is None:
            P.log_line(f"STOP   {cid}: no second-verifier output")
            return
        status["fixes"] = len(ext.get("fixes") or [])
        status["kept"] = len(ext.get("kept") or [])
        status["reverify_problems"] = len((P.load(rv) or {}).get("problems") or []) if changed else 0
    status["n_estimates"] = len(ext.get("estimates") or [])
    status["finished_at"] = datetime.now().isoformat(timespec="seconds")
    save(EXT / "status" / f"{cid}.json", status)
    P.log_line(f"FINAL  {cid}: {status}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    st = json.load(io.open(P.ROOT / "report-data.json", encoding="utf-8"))["status_by_cid"]
    cids = a.only or sorted(c for c, s in st.items() if s == "core" and c not in MOVED_OUT)
    P.SLOTS = threading.Semaphore(a.workers)
    P.log_line(f"extraction chains: {len(cids)} papers | job slots: {a.workers}")
    # As many chains as job slots: a chain in its reconcile or verify stage holds one slot, so the semaphore, not the
    # number of chains, limits the Codex jobs that run at once.
    with ThreadPoolExecutor(max(1, a.workers)) as pool:
        list(pool.map(chain, cids))
    done = [c for c in cids if P.load(EXT / "status" / f"{c}.json")]
    P.log_line(f"finished: {len(done)} of {len(cids)} chains have a status file")


if __name__ == "__main__":
    main()
