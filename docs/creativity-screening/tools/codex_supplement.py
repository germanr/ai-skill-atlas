"""Supplement pass: add what a newly obtained supplement prints to a paper's finished extraction, then verify the changes.

For each paper with supplement files on file (D:/projects/ai-skill-atlas/creativity-supplements/manifest.json) and a finished
extraction chain (extraction/status/<cid>.json): a Codex job reads the supplement and (1) fills statistics that the main text
lacks for estimates already in the file, (2) adds in-scope estimates printed only in the supplement. It changes no number
taken from the main text. Every change is logged in "supplement_changes" and every new estimate in "supplement_added". A script
then checks every number against its quote and every quote against the main PDF or the supplement; a verifier rechecks only
what changed; a fixer and a second verifier follow when anything is flagged.

Files: extraction/<cid>.json (in place), checks/<cid>.supmech.json, checks/<cid>.supverify.json, checks/<cid>.supreverify.json,
status/<cid>.json ("supplement" block).
Usage: python tools/codex_supplement.py [--workers 6] [--only c006 ...]
"""
import argparse
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import codex_extract as E
import codex_pipeline as P
import extract_checks as X

R = P.R
EXT = E.EXT


def supplement_files(cid):
    m = P.load("D:/projects/ai-skill-atlas/creativity-supplements/manifest.json") or {}
    out = []
    for f in (m.get(cid) or {}).get("files") or []:
        if f.get("unpacked"):
            from pathlib import Path
            for p in sorted(Path(f["unpacked"]).rglob("*")):
                if p.suffix.lower() in (".pdf", ".md", ".docx", ".xlsx", ".csv", ".txt"):
                    out.append(str(p).replace("\\", "/"))
        elif f.get("path"):
            out.append(f["path"].replace("\\", "/"))
            if f.get("md_path"):
                out.append(f["md_path"].replace("\\", "/"))
    return out


def supplement_pdfs(cid):
    return [p for p in supplement_files(cid) if p.lower().endswith(".pdf")]


def supplement_prompt(cid):
    files = supplement_files(cid)
    return "\n".join([
        f"You add a newly obtained supplement to one paper's finished extraction. {E.INTRO}",
        "", P.HOW_TO_WORK, "",
        E.inputs_block(cid),
        f"- The finished extraction is {R}/extraction/{cid}.json. It was made from the main PDF only.",
        f"- The supplement files, downloaded from the publisher or Europe PMC, are: {json.dumps(files, ensure_ascii=True)}. Read every one in full "
        "(the .md files are conversions of the PDFs; check numbers against the PDF pages with pymupdf).",
        "",
        "Tasks:",
        "1. For each estimate already in the file, add the statistics that the main text lacks and the supplement prints for the same outcome, "
        "contrast, arms, sample, and analysis: arm means, SDs, SEs, counts, differences, intervals, exact p-values, test statistics. Do not "
        "change a number that came from the main text. If the supplement contradicts the main text, keep the main-text number and say so in "
        "the estimate's notes.",
        "2. Add every in-scope estimate (extraction file, rules 4 to 6) that the supplement prints and the file lacks: other contrasts, "
        "preregistered tests, replications, or studies. Follow the extraction file's structure exactly, with new slugs. A study that the file "
        "lacks is added to \"studies\" with the same fields as the others. Mark preregistered_primary \"yes\" where the supplement says a test "
        "is the preregistered primary test.",
        "3. Every number you add has a source whose locator names the supplement file and its page, for example "
        "\"Supplement sciadv.adn5290_sm.pdf, p. 12, table S3\", and a verbatim quote that contains the number.",
        "4. Update not_extracted and open_items: remove what the supplement settles, and keep the rest.",
        "",
        f"Rewrite {R}/extraction/{cid}.json in place, keeping everything else, with two more keys: \"supplement_changes\" (a list of objects "
        "with \"slug\", \"field\", \"old\", \"new\", \"locator\", and \"quote\") and \"supplement_added\" (the slugs of the estimates you added).",
        "",
        P.SUMMARY_NOTE + '"cid", "n_changes", "n_added", and "settled_open_items".',
    ])


def sup_verify_prompt(cid, slugs, problems, name):
    files = supplement_files(cid)
    return "\n".join([
        f"You are the verifier for one paper's supplement pass. {E.INTRO} You did not take part in it, and your job is to find what is wrong.",
        "", P.HOW_TO_WORK, "",
        f"Inputs: the extraction file {R}/extraction/{cid}.json; the main paper (PDF at \"pdf_path\" under key \"{cid}\" in {R}/retrieval.json"
        + (f"; for this paper use {E.C750_PDF}" if cid == "c750" else "") + f"); the supplement files {json.dumps(files, ensure_ascii=True)}. "
        f"The rules are in {E.SPEC} and {P.CODEBOOK}.",
        "",
        f"Check only these estimates, which the supplement pass changed or added: {', '.join(slugs) or 'none'}. For each, open the page each "
        "source cites (main PDF or supplement) and confirm: (a) each number is printed there with that value; (b) it belongs to this outcome, "
        "contrast, arms, sample, and analysis; (c) the counts are the counts of this analysis; (d) the codes (question, construct, measure, unit, "
        "higher_is, outcome_with_ai, outcome_timing, within_person, comparison_type, se_basis, preregistered_primary) are right. Also check that "
        "no main-text number was changed (compare the supplement_changes log with the main PDF).",
        "",
        "A script already checked every number against its quote and every quote against the cited pages. It reported: "
        + (json.dumps(problems, ensure_ascii=True)[:12000] if problems else "nothing") + ".",
        "",
        f"Write {R}/extraction/checks/{cid}.{name}.json: an object with \"cid\", \"checked\", \"problems\" (objects with \"slug\", \"field\", "
        "\"status\", \"recorded\", \"printed\", \"locator\", \"quote\", \"note\"), and \"summary\". An empty problems list means you confirmed everything.",
        "",
        P.SUMMARY_NOTE + '"cid", "checked", and "n_problems".',
    ])


def sup_fix_prompt(cid):
    return "\n".join([
        f"You are the fixer for one paper's supplement pass. {E.INTRO}",
        "", P.HOW_TO_WORK, "",
        E.inputs_block(cid),
        f"- Supplement files: {json.dumps(supplement_files(cid), ensure_ascii=True)}.",
        f"The extraction file is {R}/extraction/{cid}.json. A verifier reported problems in {R}/extraction/checks/{cid}.supverify.json and a script "
        f"in {R}/extraction/checks/{cid}.supmech.json. For each, check the source. Correct the file where the problem is real; keep the value "
        "where the flag is wrong, with the passage that shows it.",
        f"Rewrite {R}/extraction/{cid}.json in place, keeping everything else, and add \"supplement_fixes\" (slug, field, old, new, locator, quote, "
        "basis) and \"supplement_kept\" (slug, field, value, locator, quote, why_the_flag_is_wrong).",
        "",
        P.SUMMARY_NOTE + '"cid", "n_fixes", and "n_kept".',
    ])


def mech(cid, name):
    ext = P.load(EXT / f"{cid}.json")
    problems = X.mechanical_check(ext, E.pdf_of(cid), extra_pdfs=supplement_pdfs(cid))
    E.save(EXT / "checks" / f"{cid}.{name}.json", {"cid": cid, "problems": problems, "pdf": E.pdf_of(cid), "supplements": supplement_pdfs(cid),
                                                   "checked_at": datetime.now().isoformat(timespec="seconds")})
    return problems


def chain(cid):
    status = P.load(EXT / "status" / f"{cid}.json")
    if not status:
        P.log_line(f"SKIP   {cid}: extraction chain not finished")
        return
    ext = P.load(EXT / f"{cid}.json") or {}
    if "supplement_changes" not in ext:
        P.run_until(f"supplement-{cid}", supplement_prompt(cid), EXT / f"{cid}.json")
        ext = P.load(EXT / f"{cid}.json") or {}
    if "supplement_changes" not in ext:
        P.log_line(f"STOP   {cid}: the supplement pass did not finish")
        return
    slugs = sorted({c.get("slug") for c in ext.get("supplement_changes") or [] if c.get("slug")} | set(ext.get("supplement_added") or []))
    problems = mech(cid, "supmech")
    ver = EXT / "checks" / f"{cid}.supverify.json"
    if slugs and P.load(ver) is None:
        P.run_until(f"supverify-{cid}", sup_verify_prompt(cid, slugs, problems, "supverify"), ver)
    if slugs and P.load(ver) is None:
        P.log_line(f"STOP   {cid}: no supplement verifier output")
        return
    v = P.load(ver) or {"problems": []}
    block = {"changes": len(ext.get("supplement_changes") or []), "added": len(ext.get("supplement_added") or []),
             "supmech_problems": len(problems), "supverify_problems": len(v.get("problems") or [])}
    if v.get("problems") and "supplement_fixes" not in ext:
        P.run_until(f"supfix-{cid}", sup_fix_prompt(cid), EXT / f"{cid}.json")
        ext = P.load(EXT / f"{cid}.json") or {}
        if "supplement_fixes" not in ext:
            P.log_line(f"STOP   {cid}: the supplement verifier found problems but the fixer left no output")
            return
    if "supplement_fixes" in ext:
        changed = sorted({f.get("slug") for f in (ext.get("supplement_fixes") or []) + (ext.get("supplement_kept") or []) if f.get("slug")})
        problems2 = mech(cid, "supmech2")
        rv = EXT / "checks" / f"{cid}.supreverify.json"
        if changed and P.load(rv) is None:
            P.run_until(f"supreverify-{cid}", sup_verify_prompt(cid, changed, problems2, "supreverify"), rv)
        if changed and P.load(rv) is None:
            P.log_line(f"STOP   {cid}: no second supplement verifier output")
            return
        block.update({"fixes": len(ext.get("supplement_fixes") or []), "kept": len(ext.get("supplement_kept") or []),
                      "supmech2_problems": len(problems2), "supreverify_problems": len((P.load(rv) or {}).get("problems") or []) if changed else 0})
    block["finished_at"] = datetime.now().isoformat(timespec="seconds")
    status["supplement"] = block
    E.save(EXT / "status" / f"{cid}.json", status)
    P.log_line(f"FINAL  {cid} supplement: {block}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    m = P.load("D:/projects/ai-skill-atlas/creativity-supplements/manifest.json") or {}
    cids = a.only or sorted(c for c, v in m.items() if v.get("files"))
    P.SLOTS = threading.Semaphore(a.workers)
    P.log_line(f"supplement passes: {len(cids)} papers | job slots: {a.workers}")
    with ThreadPoolExecutor(max(1, a.workers)) as pool:
        list(pool.map(chain, cids))


if __name__ == "__main__":
    main()
