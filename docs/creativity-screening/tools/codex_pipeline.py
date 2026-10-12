"""Run the screening stages as Codex jobs (codex exec), one job per paper and stage.

Same methodology as creativity-fulltext-v2.js and creativity-light.js: two independent screeners, a
reconciler, three challengers and a finalizer for core papers, a citation checker; and for the short
path one screener, an independent checker, a fixer when they disagree, and a citation checker.
The files on disk decide what each paper still needs, so an interrupted run can be relaunched as is.

Usage:
  python codex_pipeline.py --args triage/finish-args-2026-10-08.json [--workers 8] [--only full|light]
  python codex_pipeline.py --full c031 c032 ... [--light-small c195 ...] [--light-context ...] [--light-nonrandom ...]

Each job gets a folder under codex-jobs/<stage>-<cid>/ with brief.md, out.md, and run.log.
Germán, 2026-10-08: subagents are Codex jobs (gpt-6-astra from ~/.codex/config.toml), not Claude agents.
"""
import argparse
import io
import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
CODEBOOK = "C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-codebook.md"
SPEC = str(ROOT / "form-spec.md").replace("\\", "/")
JOBS = ROOT / "codex-jobs"
R = str(ROOT).replace("\\", "/")
JOB_TIMEOUT = 45 * 60
LOCK = threading.Lock()
SLOTS = None  # semaphore set in main()
STAMP = datetime.now().strftime("%Y-%m-%d_%H%M")


# ----------------------------------------------------------------------------- helpers
def load(path):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return None


def form(cid):
    return load(ROOT / "forms" / f"{cid}.json")


def has_raw(cid, s):
    return (ROOT / "forms" / "raw" / f"{cid}.{s}.json").exists()


def has_challenge(cid, lens):
    return (ROOT / "forms" / "challenges" / f"{cid}.{lens}.json").exists()


def has_cite(cid):
    return (ROOT / "forms" / "citations" / f"{cid}.json").exists()


def check(cid):
    return load(ROOT / "forms" / "checks" / f"{cid}.json")


def log_line(msg):
    with LOCK:
        print(f"{datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


def run_job(name, brief, network=False):
    """Run one codex exec job; return (ok, seconds, tokens). ok means exit code 0."""
    job = JOBS / name
    job.mkdir(parents=True, exist_ok=True)
    (job / "brief.md").write_text(brief, encoding="utf-8")
    cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write"]
    if network:
        cmd += ["-c", "sandbox_workspace_write.network_access=true"]
    cmd += ["-C", str(ROOT), "-o", str(job / "out.md"), "-"]
    t0 = time.time()
    with SLOTS:
        log_line(f"start  {name}")
        with io.open(job / "run.log", "w", encoding="utf-8") as logf:
            try:
                proc = subprocess.run(cmd, input=brief, stdout=logf, stderr=subprocess.STDOUT,
                                      text=True, encoding="utf-8", timeout=JOB_TIMEOUT, shell=True)
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = -9
                logf.write("\n[codex_pipeline] timeout\n")
    secs = round(time.time() - t0)
    tokens = None
    try:
        text = io.open(job / "run.log", encoding="utf-8", errors="replace").read()
        m = re.findall(r"tokens used\s*\n\s*([\d,]+)", text)
        if m:
            tokens = int(m[-1].replace(",", ""))
    except Exception:
        pass
    with LOCK:
        with io.open(JOBS / f"jobs-{STAMP}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"job": name, "exit": code, "seconds": secs, "tokens": tokens, "network": network}) + "\n")
    log_line(f"done   {name}  exit={code} {secs}s tokens={tokens}")
    return code == 0, secs, tokens


def run_until(name, brief, expect, network=False, tries=2):
    """Run a job and retry once if the expected output file is missing or does not parse."""
    for attempt in range(tries):
        run_job(name if attempt == 0 else f"{name}-retry{attempt}", brief, network)
        if expect is None or load(expect) is not None:
            return True
        log_line(f"retry  {name}: {Path(expect).name} missing or unparseable")
    return False


# ----------------------------------------------------------------------------- shared prompt parts
INTRO = ("This is part of a full-text literature screening for the AI and Human Skill Atlas (aiskillatlas.org), a living "
         "meta-analysis that is adding a section on generative AI and creativity, ideation, and homogenization of ideas. "
         "A later audit checks every recorded number against the PDF, so accuracy matters more than speed.")

HOW_TO_WORK = f"""Working rules for this job:
- You run as a Codex job with the screening folder {R} as your workspace. You may read any file on this computer. Write only the file named in this brief. Create no other files and change no other file.
- Read the markdown conversion with your file-reading tool or with python, in chunks, until you have covered the whole document, appendices included. To check a PDF page, extract its text with python: import pymupdf; doc = pymupdf.open(r"<pdf path>"); print(doc[<page index>].get_text()); doc[<page index>].find_tables() recovers tables that the markdown scrambled.
- Write JSON with python: json.dump(obj, fh, ensure_ascii=False, indent=1) into a file opened with encoding="utf-8". Then confirm with python that the file parses.
- Non-ASCII text (dashes, minus signs, Greek letters, section signs, accented names) is lost when python code passes through the console. In python source, write every non-ASCII character as a \\u escape (for example \\u2013 for an en dash, \\u2212 for a minus sign, \\u03b7 for eta, \\u00e9 for e-acute), or read the text from the source file instead of typing it. Never write a question mark in place of a character you cannot type.
- No web search is available. Where an API is named, call it with python urllib (User-Agent "atlas-screening/0.1"; send no email address or personal identifier). If a request fails, try another named source. Never guess a value: write null for what you cannot confirm.
- Your final message is the short JSON summary described at the end of this brief, and nothing else."""


def files_block(cid):
    return "\n".join([
        f"Paper: {cid}.",
        f'- Its search record is the object with "cid": "{cid}" in {R}/candidates.json. The notes there ("evidence", "design_guesses") are unverified leads.',
        f'- Its files are under key "{cid}" in {R}/retrieval.json: "md_path" is a markdown conversion of the PDF at "pdf_path". The entry may also say which version of the paper is on file ("version_saved") and how it differs from the latest version.',
        '- If "pdf_path" is null, "md_path" holds the publisher\'s article text saved from its web page ("text_only_note" says what it lacks). That text is the source of record: cite sections and tables as locators, since it has no page numbers.',
    ])


HOW_READ = {
    "A": "How to read the paper: read the markdown from start to end, design and methods before results. Then extract the text of the PDF pages that hold the design description, the participant counts, and each table or figure you cite, and check your entries against those pages.",
    "B": "How to read the paper: start with the PDF. Go through the tables, figures, and any appendix or supplement first and list every outcome they report. Then read the design and methods sections to establish who was assigned to what. Check each entry against the PDF page.",
}

SUMMARY_NOTE = "Final message: a JSON object with "


def screen_prompt(cid, s):
    return "\n".join([
        f"You are screener {s} for one paper. {INTRO}",
        "A second screener fills the same form independently, and a third agent then compares the two forms against the source.",
        "", HOW_TO_WORK, "", files_block(cid), "",
        "Read first:",
        f"1. {CODEBOOK} (scope, the three questions, eligibility, and the coded vocabulary).",
        f"2. {SPEC} (the form and its rules).",
        "", HOW_READ[s], "",
        f'Then fill the form for this paper and save it to {R}/forms/raw/{cid}.{s}.json, with "cid": "{cid}" and "screener": "{s}". Do not open any other file under {R}/forms.',
        "",
        "Points that screeners often get wrong:",
        '- Whether people were randomly assigned to AI assistance, or whether the paper compares AI-generated output with human-generated output. In the second case no person receives AI help and the design class is "ai_vs_human".',
        '- Participant counts. Count people. A paper that reports 400 ideas or 200 essays may have far fewer participants. Write "analyzed" for a count after exclusions and "randomized" only for a count given at assignment.',
        '- Whether AI was available while the scored output was produced. An outcome measured after AI was taken away is "after_ai".',
        '- Whether the paper reanalyzes another paper\'s participants ("sample_overlap").',
        '- Whether the statistics sit in a supplement that is not in this PDF ("source.supplement").',
        '- Papers with no human participants at all (model-only studies, theory, reviews): fill "source", "paper_design_summary", one study entry with the right "design_class", the "synthesis" block for reviews, "eligibility", and "one_line_finding"; leave the rest at its defaults.',
        "",
        SUMMARY_NOTE + '"cid", "file", "main_design_class" (the design class of the study that best supports eligibility), "core" (yes, no, or unclear), "n_people_analyzed" (the largest number of people analyzed in a single study, or null), "n_studies", "n_outcomes".',
    ])


def reconcile_prompt(cid):
    return "\n".join([
        f"You are the reconciler for one paper. {INTRO}",
        "Two screeners filled the same form independently. You produce the final form and settle every difference between them against the source document.",
        "", HOW_TO_WORK, "", files_block(cid), "",
        "Other inputs:",
        f"- {CODEBOOK} and {SPEC}: the definitions and the form.",
        f"- The two raw forms: {R}/forms/raw/{cid}.A.json and {R}/forms/raw/{cid}.B.json. If one of them is missing or does not parse, say so in your final message, screen the paper yourself from the source, and treat every field as a difference.",
        "",
        "Steps:",
        "1. Read both forms and list every substantive difference: design class; assignment (randomized, unit, structure); arms; participant counts; AI tool and role; task; which outcomes are listed; each outcome's construct, question, measure, unit, AI availability, timing, and primary status; the reported statistics and their locators; the supplement; sample overlap; company involvement; each eligibility criterion; the one-line finding. Differences of wording that mean the same thing do not count.",
        "2. Settle each difference from the source: open the passage (markdown first, then the PDF page) and decide which form is right, or that neither is. Record the resolved value with a verbatim quote (40 words at most) and a locator. If the source does not settle it, mark it unresolved and say what is missing.",
        "3. Agreement between the screeners is not proof. Confirm from the source, once each, the facts that decide eligibility even where the forms agree: how assignment was done, the number of people analyzed, that the outcome is scored on the output, and whether AI was available when the output was produced.",
        "4. Keep an outcome that only one screener listed if the source supports it.",
        f'5. Write the final form to {R}/forms/{cid}.json: the structure in the spec, with "screener": "reconciled", plus a top-level "reconciliation" object with "differences" (a list of objects with "field", "a", "b", "resolved", "quote", "locator", and "status" equal to "resolved" or "unresolved"), "agreed_fields_checked" (a list of objects with "field", "value", "quote", "locator", "confirmed"), "n_differences", and "n_unresolved".',
        "",
        SUMMARY_NOTE + '"cid", "file", "main_design_class", "core" (repeats eligibility.core), "n_people_analyzed", "n_differences", "n_unresolved", "unresolved" (each unresolved item in a few words), "questions" (which of with_ai, across_people, after_ai the outcomes answer), "one_line_finding".',
    ])


LENSES = [
    {"id": "assignment",
     "claim": "the paper is a randomized experiment in which people were randomly assigned to generative-AI assistance",
     "criterion": "people were randomly assigned to conditions that differ in generative-AI assistance (criterion 1)",
     "read": 'Read "studies[].assignment", "arms", and "ai_tool" in the final form.',
     "checks": "For each study the form calls randomized, check: (a) does the document itself say that assignment to conditions was random, and where; (b) what was assigned: access to a generative-AI tool, or AI-generated material, for the participant's own work, as opposed to conditions that only differ in whose output gets evaluated; (c) is the tool generative AI (a large language model or an image generator); (d) does the comparison arm match the form (no AI, another aid, or another AI configuration); (e) in a within-person design, was the order of conditions randomized."},
    {"id": "people",
     "claim": "at least 50 people took part, and the participant counts in the form are right",
     "criterion": "at least 50 people were analyzed across all arms of at least one randomized study (criterion 2)",
     "read": 'Read "studies[].participants" and "arms" in the final form.',
     "checks": "Check: (a) the number of people randomized and analyzed in each study and arm, from the participant section, any flow diagram, the tables, and the appendix; (b) that the form's counts are people and not ideas, texts, ratings, sessions, or pairs; (c) exclusions and attrition between randomization and analysis; (d) whether the same people appear in more than one study of the paper, or in another paper; (e) whether at least one study on its own has 50 or more people analyzed."},
    {"id": "outcome",
     "claim": "the paper scores creativity or diversity on the output that participants produced, and each outcome's question, construct, measure, unit, and AI availability are coded correctly",
     "criterion": "at least one outcome is scored on the output that participants produced, by raters or a computed measure (criterion 3)",
     "read": 'Read "studies[].outcomes" in the final form, and the codebook sections on questions and outcome fields.',
     "checks": 'For each outcome in the form, check: (a) it is scored on the produced output, by raters or a computed measure, and is not self-reported; (b) whether AI was available while that output was produced, and whether "question" follows the codebook rule (after AI is removed: after_ai; with AI and a diversity construct: across_people; otherwise with_ai); (c) the construct (diversity always compares different people; variety within one person is flexibility); (d) the unit is the unit of the paper\'s own analysis; (e) the "reported" numbers match the cited table or figure exactly. Also look for outcomes that bear on the three questions and are missing from the form.'},
]


def challenge_prompt(cid, lens):
    return "\n".join([
        f"You are a skeptical checker. {INTRO}",
        f"Another agent has concluded that, for paper {cid}, {lens['claim']}. Try to refute that conclusion from the source document.",
        "", HOW_TO_WORK, "", files_block(cid), "",
        f"Other inputs: the final form at {R}/forms/{cid}.json, and the definitions in {CODEBOOK}. {lens['read']} Do not rely on the form's quotes: find the passages in the PDF yourself.",
        "", lens["checks"], "",
        "Give two verdicts.",
        '- "refuted": true if any part of the coding is wrong or is not supported by the text; false only if you found explicit support for each part. If you cannot find the supporting text, the answer is true.',
        f'- "eligibility_holds": does this conclusion stand after your check: {lens["criterion"]}? Answer "yes", "no", or "unclear". Errors of detail that leave this conclusion intact do not change the answer.',
        "",
        f'Write a JSON object to {R}/forms/challenges/{cid}.{lens["id"]}.json with "cid", "lens" ("{lens["id"]}"), "refuted", "eligibility_holds", "problems" (a list of objects with "where" (study or outcome id), "field", "form_value", "source_says", "quote" (verbatim, 40 words at most), "locator"), "confirmed" (a list of short statements you verified, each with its locator), and "summary" (two sentences). Do not change the form.',
        "",
        SUMMARY_NOTE + '"cid", "lens", "refuted", "eligibility_holds", "n_problems", "summary".',
    ])


def finalize_prompt(cid):
    return "\n".join([
        f"You are the finalizer for one paper. {INTRO}",
        f"Skeptical checkers may have examined the reconciled screening form of paper {cid}. You apply what they found, after confirming each point against the source, and state the final eligibility.",
        "", HOW_TO_WORK, "", files_block(cid), "",
        "Other inputs:",
        f"- {CODEBOOK} and {SPEC}: the definitions and the form (the spec may have gained fields since the form was written).",
        f"- The form: {R}/forms/{cid}.json.",
        f"- The challenge files: every file matching {R}/forms/challenges/{cid}.*.json (list the folder with python). There may be none: non-core papers get no challenge. Each has \"problems\" with quotes and locators.",
        "",
        "Steps:",
        '1. For each problem in each challenge file, open the source passage yourself and decide: "corrected" (the checker is right: fix the form), "rejected" (the form was right: say why, with a quote), or "open" (the source does not settle it).',
        '2. Apply the corrections to the form. Also bring the form in line with the current spec: fill "source.supplement" if it is missing; a reanalysis of another paper\'s experiment takes that experiment\'s design class; prose says "analyzed" for counts after exclusions.',
        '3. Re-evaluate the three eligibility criteria after the corrections and update "eligibility".',
        '4. Go through "open_questions" and any unresolved item in "reconciliation.differences". For each, say whether it affects an eligibility criterion and what would settle it: "supplement", "posted_data", "authors", "journal_version", or "nothing_needed".',
        f'5. Rewrite {R}/forms/{cid}.json with the same structure, "screener": "final", the "reconciliation" object unchanged, and a new top-level "final" object: {{"core": "yes" | "no" | "unclear", "criteria": {{"random_assignment_of_ai": "met" | "not_met" | "unclear", "at_least_50_people": "met" | "not_met" | "unclear", "outcome_scored_on_output": "met" | "not_met" | "unclear"}}, "challenge_resolution": [{{"lens": "...", "problem": "...", "action": "corrected" | "rejected" | "open", "what_changed": "...", "quote": "...", "locator": "..."}}], "open_items": [{{"item": "...", "affects_eligibility": true | false, "settled_by": "..."}}], "n_corrected": 0, "n_rejected": 0, "n_open": 0}}.',
        "",
        SUMMARY_NOTE + '"cid", "core", "random_assignment_of_ai", "at_least_50_people", "outcome_scored_on_output", "n_corrected", "n_rejected", "n_open", "open_eligibility_items" (the open items that affect eligibility, in a few words each).',
    ])


def cite_prompt(cid):
    return "\n".join([
        f"You are the citation checker for one paper. {INTRO}",
        f"The owner's rule is strict: never fabricate or guess any reference field. Confirm the bibliographic record of paper {cid} against primary sources.",
        "", HOW_TO_WORK, "",
        f'Inputs: the object with "cid": "{cid}" in {R}/candidates.json (title, authors, year, venue, DOI, arXiv id, URL, other versions: all unverified), and, if a file is on record, the first two pages of the PDF at "pdf_path" under key "{cid}" in {R}/retrieval.json (extract their text with pymupdf).',
        "",
        "Check against the Crossref API (https://api.crossref.org/works/<doi> or https://api.crossref.org/works?query.bibliographic=<title>), the OpenAlex API (https://api.openalex.org/works/doi:<doi>), the arXiv API (http://export.arxiv.org/api/query?id_list=<id> or search_query=ti:...), the OSF API, or the publisher page: the exact title; the full author list in order; the year; the venue with volume, issue, and pages or article number; the DOI; and every version of the work (preprint ids with dates, journal publication date). Establish which version the PDF on disk is, if there is one, and whether a later version exists. Many publisher sites return HTTP 403 to scripts; the APIs usually suffice. If an API answers HTTP 429, wait a few seconds and try once more, then use another source.",
        "",
        f'Write a JSON object to {R}/forms/citations/{cid}.json with "cid", "pdf_version" (what the PDF on disk is, or null if none), "latest_version" (an object with "title", "authors" (list of full names in order), "authors_family" (the family names in the same order, as Crossref or the publisher gives them, for example "Van de Cruys", "de Rooij", "Dell\'Acqua"), "year", "venue", "volume_issue_pages", "doi", "url", "status" (journal, proceedings, working_paper, or preprint), "date"), "other_versions" (a list of objects with "what", "id_or_doi", "date", "title_if_different"), "pdf_is_latest" (true, false, or null), "corrections_to_candidate_record" (a list of strings; empty if the record was right), "checked_against" (which sources you used), and "unverified_fields" (fields you could not confirm). Write null for anything you could not confirm.',
        "",
        SUMMARY_NOTE + '"cid", "citation" (one line in the form Authors (Year), "Title", Venue), "corrections" (repeats corrections_to_candidate_record), "unverified_fields".',
    ])


# ----------------------------------------------------------------------------- light (short-form) prompts
LIGHT_FILES = lambda cid: "\n".join([
    f"Paper: {cid}.",
    f'- Its search record is the object with "cid": "{cid}" in {R}/candidates.json. The notes there ("evidence", "design_guesses") are unverified leads.',
    f'- Its triage record is the object with "cid": "{cid}" in {R}/triage/decisions.json (two screeners\' readings of the abstract).',
    f'- If a full text is on file, key "{cid}" in {R}/retrieval.json has "status": "ok" with "md_path" (markdown) and "pdf_path" (PDF). Check every number against the PDF page, because the markdown conversion can drop or scramble tables.',
    '- If "pdf_path" is null but "status" is "ok", "md_path" holds the publisher\'s article text saved from its web page ("text_only_note" says what it lacks). That text is the source of record: cite sections and tables as locators.',
    '- If no full text is on file, work from primary records you can reach without credentials: the abstract through the OpenAlex, Crossref, arXiv, Semantic Scholar, or Europe PMC APIs (python urllib; no email address in headers), an open HTML full text on the publisher\'s site if one loads, or a preprint. You may read a PDF in memory with pymupdf without saving it. Do not try to get past paywalls, logins, or bot checks. Set "source.version" to say exactly what you read, for example "abstract only (Crossref)" or "arXiv v2 read in memory".',
])

SHORT = {
    "context": "\n".join([
        "Context papers are listed on the site with a one-line finding and never enter a pooled estimate. Fill the SHORT version of the form:",
        '- "source" (including "supplement" if you can tell) and "paper_design_summary".',
        '- One entry in "studies" per study or dataset: "study_id", "label", "design_class", "assignment" (fill "randomized", "quote", and "locator" only if people are assigned to conditions), "participants" (people if there are any; for a corpus, describe it in "who" and put its size in each outcome\'s "n_units"), "ai_tool", "task".',
        '- Up to five main outcomes that bear on the three questions, each with "name", "construct", "question" ("none" when AI output is compared with human output; otherwise the closest of the three), "measure", "unit", "n_units", and one contrast with "treatment_arm", "control_arm", "comparison_type", "direction", "reported" (numbers exactly as printed), and "locator".',
        '- The "synthesis" block for reviews and meta-analyses: number of studies, number of effect sizes, search end date, inclusion rule, and every pooled estimate with its interval, what it compares, and what it standardizes.',
        '- "eligibility": "core" is "no" and "context_class" is "ai_vs_human", "observational", "synthesis", or "none" (with the reason, for example a count of AI text with no diversity or novelty outcome, a model-only study, or a narrative review). One exception: if the paper contains a study in which people were randomly assigned to generative-AI assistance and creativity or diversity was scored on their output, set "core" to "unclear" and say so in "reason"; the paper then goes to the two-screener pipeline.',
        '- "one_line_finding": one plain sentence with the main numbers and where they are printed.',
    ]),
    "small": "\n".join([
        "Triage read fewer than 50 participants in this experiment. Under the current rule, randomized experiments with fewer than 50 participants are listed in the screening report and left out of the dataset. Your job is to confirm the participant count and the design. Fill the SHORT version of the form:",
        '- "source" and "paper_design_summary".',
        '- One entry in "studies" per experiment: "design_class", "assignment" ("randomized", "what_was_assigned", "unit", "structure", "quote", "locator"), "arms" with counts, "participants" ("n_randomized", "n_analyzed", "counts_are", "population", "who", "quote", "locator"), "ai_tool", "task".',
        '- Up to three main outcomes, each with "name", "construct", "question", "measure", "unit", and one contrast with "reported" and "locator".',
        '- "eligibility": criterion 2 is "not_met" when fewer than 50 people were analyzed across all arms. If you find 50 or more, set "core" to "unclear" and explain: the paper then goes to the two-screener pipeline.',
        '- "one_line_finding".',
    ]),
    "nonrandom": "\n".join([
        "Triage read a design in which people were not randomly assigned to generative-AI assistance: a quasi-experiment, a classroom or cohort comparison, a single-group before-and-after study, or self-selected groups. Under the codebook only randomized experiments enter the core dataset. Your job is to confirm the assignment mechanism from the text and record the main result. Fill the SHORT version of the form:",
        '- "source" and "paper_design_summary".',
        '- One entry in "studies" per study: "design_class", "assignment" ("randomized", "what_was_assigned", "unit", "structure", "quote", "locator"; quote the sentence that says how people came to be in each condition), "arms" with counts, "participants" ("n_randomized" only if assignment was random, "n_analyzed", "counts_are", "population", "who", "quote", "locator"), "ai_tool", "task".',
        '- Up to three main outcomes, each with "name", "construct", "question", "measure", "unit", and one contrast with "reported" and "locator".',
        '- "eligibility": criterion 1 is "not_met" when the text states a non-random allocation and "unclear" when the text does not say how people were allocated. If you find that people were randomly assigned to conditions that differ in generative-AI assistance, set "core" to "unclear" and explain: the paper then goes to the two-screener pipeline.',
        '- "one_line_finding".',
    ]),
    "unstated": "\n".join([
        "Triage could not tell from the abstract how people came to be in each condition. Under the codebook only experiments that randomly assign people to conditions that differ in generative-AI assistance enter the core dataset. Your job is to establish the assignment mechanism from the full text and record the main result. Fill the SHORT version of the form:",
        '- "source" and "paper_design_summary".',
        '- One entry in "studies" per study: "design_class", "assignment" ("randomized" is "yes" only when the text states random assignment, "no" when it states another allocation, "not_stated" otherwise; "what_was_assigned", "unit", "structure", "quote" (the sentence that says how people came to be in each condition), "locator"), "arms" with counts, "participants" ("n_randomized" only if assignment was random, "n_analyzed", "counts_are", "population", "who", "quote", "locator"), "ai_tool", "task".',
        '- Up to three main outcomes, each with "name", "construct", "question", "measure", "unit", and one contrast with "reported" and "locator".',
        '- "eligibility": criterion 1 is "met" when the text states random assignment of generative-AI assistance to people, "not_met" when it states a non-random allocation, and "unclear" when it does not say. If criterion 1 is "met" or "unclear" and at least 50 people were analyzed and an outcome is scored on the output, set "core" to "unclear" and explain: the paper then goes to the two-screener pipeline. Otherwise "core" is "no" with the reason.',
        '- "one_line_finding".',
    ]),
    "abstract_only": "\n".join([
        'Triage called this an experiment, and no full text could be obtained. The paper will be listed as "full text not obtained" so that the owner can download it. Fill the SHORT version of the form from what you can reach:',
        '- "source" (say exactly what you read) and "paper_design_summary".',
        '- One entry in "studies" per experiment: "design_class", "assignment" ("randomized" is "not_stated" unless the text you read states it; "quote"; "locator" such as "abstract"), "arms", "participants" (counts only if stated), "ai_tool", "task".',
        '- The outcomes the abstract names, each with "name", "construct", "question", "measure" if stated, and one contrast with "reported" (numbers exactly as printed, or an empty string) and "locator".',
        '- "eligibility": each criterion is "met", "not_met", or "unclear" on the evidence you read, and "core" is "unclear" unless a criterion clearly fails.',
        '- "one_line_finding", and in "open_questions" what the full text must settle (random assignment, people analyzed, how the outcome was scored, whether AI was available).',
    ]),
}
TAG = {"context": "single", "small": "single_small", "abstract_only": "single_abstract", "nonrandom": "single_nonrandom", "unstated": "single_unstated"}


def light_screen_prompt(cid, kind):
    return "\n".join([
        f"You are the screener for one paper. {INTRO}",
        "An independent checker will compare your form with the source.",
        "", HOW_TO_WORK, "", LIGHT_FILES(cid), "",
        f"Read first: {CODEBOOK} (scope, the three questions, eligibility, vocabulary) and {SPEC} (the form and its rules).",
        "", SHORT[kind], "",
        f'Leave every other field of the form at its default. Save the form to {R}/forms/{cid}.json, with "cid": "{cid}" and "screener": "{TAG[kind]}". Do not open any other file under {R}/forms.',
        "",
        SUMMARY_NOTE + '"cid", "main_design_class", "core", "context_class", "n_people_analyzed", "version_read".',
    ])


def light_check_prompt(cid):
    return "\n".join([
        f"You are the checker for one paper. {INTRO}",
        f"Another agent filled a short screening form at {R}/forms/{cid}.json. Check it against the source, independently: find the passages yourself.",
        "", HOW_TO_WORK, "", LIGHT_FILES(cid), "",
        f"Definitions: {CODEBOOK}. Form rules: {SPEC}.",
        "",
        "Check:",
        '1. The design class and the context class. Does the paper contain any study in which people were randomly assigned to generative-AI assistance, with creativity or diversity scored on their output? If so it belongs in the two-screener pipeline: set "has_randomized_people_study" to true and describe the study.',
        "2. The counts: people versus texts, ideas, or ratings; people randomized versus analyzed; for small experiments, whether fewer than 50 people were analyzed.",
        '3. Every "reported" string and the one-line finding: the numbers must match the cited table, figure, or passage exactly.',
        "4. For syntheses: the number of studies, the pooled estimates, their intervals, and what they standardize.",
        '5. The version read ("source.version") and whether the form says more than that source supports.',
        "",
        f'Write a JSON object to {R}/forms/checks/{cid}.json: {{"cid": "{cid}", "agrees": true or false, "has_randomized_people_study": true or false, "corrections": [{{"field": "...", "form_value": "...", "source_says": "...", "quote": "verbatim, 40 words at most", "locator": "..."}}], "confirmed": ["short statements you verified, with locators"], "summary": "two sentences"}}. "agrees" is true only if you found nothing to correct. Do not change the form.',
        "",
        SUMMARY_NOTE + '"cid", "agrees", "has_randomized_people_study", "n_corrections", "summary".',
    ])


def light_fix_prompt(cid):
    return "\n".join([
        f"You are the fixer for one paper. {INTRO}",
        f'A checker found problems in the short screening form at {R}/forms/{cid}.json. The problems are in {R}/forms/checks/{cid}.json ("corrections").',
        "", HOW_TO_WORK, "", LIGHT_FILES(cid), "",
        f"Definitions: {CODEBOOK}. Form rules: {SPEC}.",
        "",
        f'For each correction, open the source passage yourself and decide whether the checker or the form is right. Apply the corrections that hold. Then rewrite {R}/forms/{cid}.json with the same structure, "screener" set to its current value plus "_fixed", and a new top-level "fix" object: {{"applied": [{{"field": "...", "old": "...", "new": "...", "quote": "...", "locator": "..."}}], "rejected": [{{"field": "...", "why": "...", "quote": "...", "locator": "..."}}]}}. Re-evaluate "eligibility" after the changes.',
        "",
        SUMMARY_NOTE + '"cid", "core", "context_class", "n_applied", "n_rejected".',
    ])


# ----------------------------------------------------------------------------- chains
def full_chain(cid):
    """Full pipeline for one paper, running only the stages whose files are missing."""
    result = {"cid": cid, "stages": []}
    f = form(cid)
    if f is None or f.get("screener") not in ("reconciled", "final"):
        with ThreadPoolExecutor(2) as pool:
            futs = [pool.submit(run_until, f"screen{s}-{cid}", screen_prompt(cid, s), ROOT / "forms" / "raw" / f"{cid}.{s}.json")
                    for s in "AB" if not has_raw(cid, s)]
            for fut in futs:
                fut.result()
        result["stages"].append("screen")
        if not run_until(f"reconcile-{cid}", reconcile_prompt(cid), ROOT / "forms" / f"{cid}.json"):
            result["failed"] = "reconcile"
            return result
        result["stages"].append("reconcile")
        f = form(cid)
    core = ((f.get("final") or {}).get("core")) or (f.get("eligibility") or {}).get("core")
    result["core_before"] = core
    tasks = []
    if not has_cite(cid):
        tasks.append(("cite", lambda: run_until(f"cite-{cid}", cite_prompt(cid), ROOT / "forms" / "citations" / f"{cid}.json", network=True)))
    if f.get("screener") != "final" and core in ("yes", "unclear"):
        for lens in LENSES:
            if not has_challenge(cid, lens["id"]):
                tasks.append((f"challenge-{lens['id']}", (lambda L=lens: run_until(f"challenge-{L['id']}-{cid}", challenge_prompt(cid, L), ROOT / "forms" / "challenges" / f"{cid}.{L['id']}.json"))))
    if tasks:
        with ThreadPoolExecutor(len(tasks)) as pool:
            futs = [(name, pool.submit(fn)) for name, fn in tasks]
            for name, fut in futs:
                fut.result()
                result["stages"].append(name)
    if f.get("screener") != "final":
        if run_until(f"finalize-{cid}", finalize_prompt(cid), None):
            result["stages"].append("finalize")
        f2 = form(cid)
        if f2 and f2.get("screener") == "final":
            result["final_core"] = (f2.get("final") or {}).get("core")
        else:
            result["failed"] = "finalize"
    else:
        result["final_core"] = core
    return result


def light_chain(cid, kind):
    result = {"cid": cid, "kind": kind, "stages": []}
    if form(cid) is None:
        if not run_until(f"lscreen-{cid}", light_screen_prompt(cid, kind), ROOT / "forms" / f"{cid}.json", network=True):
            result["failed"] = "screen"
            return result
        result["stages"].append("screen")
    tasks = []
    if check(cid) is None:
        tasks.append(("check", lambda: run_until(f"lcheck-{cid}", light_check_prompt(cid), ROOT / "forms" / "checks" / f"{cid}.json", network=True)))
    if not has_cite(cid):
        tasks.append(("cite", lambda: run_until(f"cite-{cid}", cite_prompt(cid), ROOT / "forms" / "citations" / f"{cid}.json", network=True)))
    if tasks:
        with ThreadPoolExecutor(len(tasks)) as pool:
            futs = [(name, pool.submit(fn)) for name, fn in tasks]
            for name, fut in futs:
                fut.result()
                result["stages"].append(name)
    ck = check(cid) or {}
    f = form(cid) or {}
    if ck.get("agrees") is False and not str(f.get("screener", "")).endswith("_fixed"):
        if run_until(f"lfix-{cid}", light_fix_prompt(cid), None, network=True):
            result["stages"].append("fix")
    f = form(cid) or {}
    result["core"] = (f.get("eligibility") or {}).get("core")
    result["context_class"] = (f.get("eligibility") or {}).get("context_class")
    result["promote"] = bool(ck.get("has_randomized_people_study")) or result["core"] == "unclear"
    return result


# ----------------------------------------------------------------------------- main
def main():
    global SLOTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--args", help="finish-args JSON (args1/args2 full cids, args3 light lists)")
    ap.add_argument("--full", nargs="*", default=[])
    ap.add_argument("--light-context", nargs="*", default=[])
    ap.add_argument("--light-small", nargs="*", default=[])
    ap.add_argument("--light-nonrandom", nargs="*", default=[])
    ap.add_argument("--light-abstract", nargs="*", default=[])
    ap.add_argument("--light-unstated", nargs="*", default=[])
    ap.add_argument("--only", choices=["full", "light"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    full, light = list(a.full), []
    light += [(c, "context") for c in a.light_context] + [(c, "small") for c in a.light_small]
    light += [(c, "nonrandom") for c in a.light_nonrandom] + [(c, "abstract_only") for c in a.light_abstract]
    light += [(c, "unstated") for c in a.light_unstated]
    if a.args:
        d = load(a.args) or {}
        for key in ("args1", "args2"):
            full += [c for c in (d.get(key) or {}).get("cids", []) if c not in full]
        a3 = d.get("args3") or {}
        for kind in ("context", "nonrandom", "small"):
            light += [(c, kind) for c in a3.get(kind, []) if c not in {x[0] for x in light}]
    if a.only == "full":
        light = []
    if a.only == "light":
        full = []
    # Drop papers that are already complete.
    full = [c for c in full if not ((form(c) or {}).get("screener") == "final" and has_cite(c))]
    light = [(c, k) for c, k in light if not (form(c) and check(c) is not None and has_cite(c)
                                               and not ((check(c) or {}).get("agrees") is False and not str((form(c) or {}).get("screener", "")).endswith("_fixed")))]
    SLOTS = threading.Semaphore(a.workers)
    JOBS.mkdir(exist_ok=True)
    log_line(f"full chains: {len(full)} | light chains: {len(light)} | workers: {a.workers}")
    results = {"full": [], "light": []}
    with ThreadPoolExecutor(a.workers) as pool:
        futs = [("full", pool.submit(full_chain, c)) for c in full] + [("light", pool.submit(light_chain, c, k)) for c, k in light]
        for kind, fut in futs:
            try:
                results[kind].append(fut.result())
            except Exception as exc:  # keep going; record the failure
                results[kind].append({"error": repr(exc)})
    out = JOBS / f"run-{STAMP}.json"
    json.dump(results, io.open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    failed = [r for k in results for r in results[k] if r.get("failed") or r.get("error")]
    promote = [r["cid"] for r in results["light"] if r.get("promote")]
    log_line(f"finished. results: {out} | failed: {len(failed)} | light papers to promote: {promote}")


if __name__ == "__main__":
    main()
