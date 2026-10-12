"""Check whether the participant-level data of each recommended or unsettled paper are publicly available.

One Codex job per paper (network on). Output: forms/data/<cid>.json. Jobs whose output already parses are skipped,
so an interrupted run can be relaunched as is.

Usage: python tools/codex_data_check.py [--workers 10] [--only c006 c094 ...]
Germ\u00e1n, 2026-10-09: "see if the raw data of the studies are available (this way we can compute what we need for
cases the papers don't report everything we need)".
"""
import argparse
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import codex_pipeline as P

OUT = P.ROOT / "forms" / "data"


def data_prompt(cid):
    R = P.R
    return "\n".join([
        f"You are the data-availability checker for one paper. {P.INTRO}",
        "Goal: find out whether the participant-level data of this paper's randomized studies are publicly available, so that "
        "we can compute statistics the paper does not print: per-person means, standard deviations, and standard errors by arm, "
        "analyzed counts, and diversity measures from the participants' texts or ideas.",
        "", P.HOW_TO_WORK, "",
        P.files_block(cid),
        f'- Its screening form is {R}/forms/{cid}.json: "studies" (the randomized studies, their arms and outcomes), '
        '"data_and_code" (what the screeners noted; unverified), and "final" -> "open_items" (statistics the paper does not report).',
        "",
        "Steps:",
        "1. Read the whole markdown text, appendices included, and find every statement about data, code, materials, "
        "preregistration, or supplementary files: data availability statements, footnotes, acknowledgments, appendix notes, and "
        "links to OSF, GitHub, Harvard Dataverse, Zenodo, Dryad, Figshare, ICPSR or openICPSR, Mendeley Data, ResearchBox, "
        "AsPredicted, the AEA registry, or the journal's supplementary material. Quote each statement exactly, with its locator.",
        "2. Check every link you found and every URL in the form's data_and_code: request it with python urllib and record the HTTP "
        "status. List the files through the repository's API: OSF (https://api.osf.io/v2/nodes/<id>/files/osfstorage/ and "
        "https://api.osf.io/v2/nodes/<id>/children/), Harvard Dataverse "
        "(https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:<doi>), Zenodo (https://zenodo.org/api/records/<id>), "
        "Dryad (https://datadryad.org/api/v2/datasets/doi%3A<url-encoded doi>), Figshare (https://api.figshare.com/v2/articles/<id>), "
        "GitHub (https://api.github.com/repos/<owner>/<repo>/git/trees/HEAD?recursive=1). The GitHub API allows about 60 requests per "
        "hour for all jobs together: use it only for repositories the paper names, and fall back to the repository's web page if it "
        "answers 403.",
        "3. Search for a deposit the paper does not mention, by title and by first author: the DataCite API "
        "(https://api.datacite.org/dois?query=<words>), Zenodo (https://zenodo.org/api/records?q=<words>), Harvard Dataverse "
        "(https://dataverse.harvard.edu/api/search?q=<words>), and OSF (https://api.osf.io/v2/nodes/?filter[title]=<words>). Also open "
        "the publisher's landing page for supplementary data files if it loads without credentials. Record each search with its query "
        "and result count.",
        "4. For each deposit, list the files and decide whether it holds data we can use: one row per participant, or per output "
        "with a participant id; the arm each participant was assigned to; and the outcome scores, or the texts or ideas from which a "
        "diversity measure can be computed. You may download a data file of up to 20 MB and read it in memory (python io.BytesIO, "
        "csv, zipfile, json; pandas or pyreadstat if installed) to see its columns and row count. Do not save data files to disk.",
        "5. Never log in, create an account, request access, or get past a login, CAPTCHA, or bot check. A deposit that needs an "
        "account or a request is recorded with that access level, and you stop there.",
        "",
        f'Write a JSON object to {R}/forms/data/{cid}.json with these keys:',
        '- "cid".',
        '- "statements": a list of {"quote", "locator"}: every data, code, or materials statement in the paper (an empty list if none).',
        '- "deposits": a list of objects with "url", "repository", "found_by" ("paper", "form", or "search"), "http_status", '
        '"access" ("public", "account_required", "on_request", "embargoed", "dead_link", or "unclear"), "n_files", "files" (up to 50 '
        'objects with "name" and "size_bytes"), "contents" ("participant_level", "output_level_with_participant_id", "aggregate_only", '
        '"code_only", "materials_only", or "unclear"), "studies_covered" (study ids from the form, or "unclear"), "has_arm_assignment", '
        '"has_outcome_scores", and "has_texts_or_ideas" (each true, false, or null), "rows_checked" (the row count you saw, or null), '
        '"columns_checked" (the column names you saw, or null), "license", and "notes".',
        '- "searches": a list of {"source", "query", "n_results", "relevant"}.',
        '- "status": "public_participant_data" (at least one public deposit with participant-level data, the arm, and the outcomes, '
        'which you confirmed by reading the columns), "public_partial" (public data that lack something we need; say what in "notes"), '
        '"code_or_materials_only", "on_request" (the paper says the data are available on request), "restricted" (an account or '
        'approval is required), or "none_found".',
        '- "what_we_could_compute": which of the missing statistics in final.open_items the public data would let us compute, or null.',
        '- "confidence" ("high", "medium", or "low") and "notes".',
        "",
        P.SUMMARY_NOTE + '"cid", "status", "n_deposits", and "best_url".',
    ])


def run(cid):
    expect = OUT / f"{cid}.json"
    if P.load(expect) is not None:
        P.log_line(f"skip   data-{cid} (output exists)")
        return
    P.run_until(f"data-{cid}", data_prompt(cid), expect, network=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    st = json.load(io.open(P.ROOT / "report-data.json", encoding="utf-8"))["status_by_cid"]
    cids = a.only or sorted(c for c, s in st.items() if s in ("core", "clarify"))
    P.SLOTS = threading.Semaphore(a.workers)
    P.log_line(f"data checks: {len(cids)} papers | workers: {a.workers}")
    with ThreadPoolExecutor(a.workers) as pool:
        list(pool.map(run, cids))
    done = sum(P.load(OUT / f"{c}.json") is not None for c in cids)
    P.log_line(f"finished: {done} of {len(cids)} outputs parse")


if __name__ == "__main__":
    main()
