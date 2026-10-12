"""Analyst A, c130: validate deposited inputs and record unavailable analyses.

Run with python -I -B <absolute path to A.py>.
Only A.json is written. Author files are treated as untrusted data and never
executed. Network responses are inspected in memory and never saved.

The full 48-page markdown conversion, including Appendices A-E and references,
was read. PDF pages 8, 15, 16, 20, 22, and 41 were checked with PyMuPDF.
The paper randomizes individual people to three fixed arms. Each person provides
one solution per task; the two experts' ratings are averaged within each person.
The second task is unassisted transfer, not randomized within-person crossover.
All 18 extraction estimates require between-person contrasts, with HC2 errors
once participant data and the paper's means/counts can be reproduced.

The supplied XLSX and SPS are actually HTML sign-in pages. There are no rows or
variable names to map and no reproducible participant statistics. This script
therefore stops before estimation and records every estimate as skipped. It
does not substitute statistics calculated from rounded published summaries.
If actual data replace these files or become accessible, stop and inspect them
before implementing participant selection or any statistical calculation.
"""

import sys
sys.dont_write_bytecode = True

from pathlib import Path
import hashlib
import io
import json
import re
import urllib.error
import urllib.request
import zipfile

ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = ROOT / "analysis" / "c130" / "A.py"
OUTPUT = ROOT / "analysis" / "c130" / "A.json"
EXTRACTION = ROOT / "extraction" / "c130.json"
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data/osf-t7an8")
DATA_FILES = [DEPOSIT / "Supplemental Data.xlsx",
              DEPOSIT / "Supplemental Analysis Code.sps"]
SOURCES = [
    ("corrected workbook download",
     "https://osf.io/download/vbtmp/?view_only=fc490583cdc8458e8b895b29e4df2345"),
    ("OSF files API",
     "https://api.osf.io/v2/nodes/t7an8/files/osfstorage/?view_only=fc490583cdc8458e8b895b29e4df2345"),
    ("paper's OSF overview",
     "https://osf.io/t7an8/overview?view_only=fc490583cdc8458e8b895b29e4df2345"),
]


def inspect_payload(payload):
    """Inspect bytes only; do not execute scripts or open a browser."""
    head = payload[:4096]
    title_match = re.search(rb"<title[^>]*>(.*?)</title>", head, re.I | re.S)
    title = (title_match.group(1).decode("utf-8", errors="replace").strip()
             if title_match else None)
    html = payload.lstrip().lower().startswith((b"<!doctype html", b"<html"))
    is_zip = zipfile.is_zipfile(io.BytesIO(payload))
    return {"bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "html": html, "title": title, "is_zip": is_zip}


def try_source(label, url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "atlas-screening/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = response.read(8 * 1024 * 1024 + 1)
            description = inspect_payload(payload)
            if not description["html"]:
                raise RuntimeError(
                    "New non-HTML source content is available at " + url
                    + "; inspect it and implement verified variable mapping "
                    "before producing results. No analysis output was written.")
            return {"label": label, "url": url, "status": response.status,
                    "content_type": response.headers.get("Content-Type"),
                    "payload": description, "error": None}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"label": label, "url": url, "status": None,
                "content_type": None, "payload": None,
                "error": type(exc).__name__ + ": " + str(exc)}


def main():
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert extraction["cid"] == "c130"
    assert len(extraction["estimates"]) == 18
    assert all(e["within_person"] is None for e in extraction["estimates"])
    expected = manifest["deposits"]["osf-t7an8"]["files"]
    validation = []
    for path in DATA_FILES:
        # SPS is read strictly as text/bytes, never imported or executed.
        description = inspect_payload(path.read_bytes())
        description["path"] = path.as_posix()
        description["manifest_match"] = (
            description["sha256"] == expected[path.name]["sha256"])
        if not description["manifest_match"]:
            raise RuntimeError("Input changed from the reviewed manifest: " + str(path))
        if not (description["html"] and description["title"] == "OSF | Sign in"
                and not description["is_zip"]):
            raise RuntimeError(
                "Input is no longer the reviewed sign-in HTML; inspect it "
                "before implementing analysis: " + str(path))
        validation.append(description)

    attempts = [try_source(label, url) for label, url in SOURCES]
    evidence = []
    for item in validation:
        evidence.append(
            Path(item["path"]).name + " is " + str(item["bytes"])
            + " bytes of HTML titled '" + item["title"]
            + "', not the named data/code file; SHA-256 " + item["sha256"]
            + " matches the download manifest")
    retrieval_evidence = []
    for attempt in attempts:
        if attempt["error"]:
            outcome = attempt["error"]
        else:
            outcome = ("HTTP " + str(attempt["status"])
                       + " returned HTML titled "
                       + repr(attempt["payload"]["title"]))
        retrieval_evidence.append(
            attempt["label"] + " (" + attempt["url"] + "): " + outcome)

    common_reason = (
        "Participant data unavailable. " + "; ".join(evidence) + ". "
        "The XLSX is not a ZIP workbook and contains no participant records. "
        "Retrieval using urllib with User-Agent atlas-screening/0.1: "
        + "; ".join(retrieval_evidence) + ". "
        "The full paper, including Appendices A-E, supplies methods, summary "
        "statistics and selected examples, but no complete participant dataset. "
        "Data rows, variable names, the excluded participant and analysis counts "
        "cannot be verified. No arm statistic or count was reproduced, so no "
        "difference, participant SD or HC2 standard error was computed."
    )
    result = {
        "cid": "c130",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in DATA_FILES],
        "results": [],
        "skipped": [
            {"slug": estimate["slug"],
             "reason": common_reason + " Requested outcome: "
                       + estimate["outcome"] + "; "
                       + estimate["treatment_arm"] + " minus "
                       + estimate["control_arm"] + "."}
            for estimate in extraction["estimates"]
        ],
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == result
    expected_slugs = {e["slug"] for e in extraction["estimates"]}
    assert {s["slug"] for s in parsed["skipped"]} == expected_slugs
    assert len(parsed["skipped"]) == len(expected_slugs)
    summary = {"cid": "c130", "n_results": len(parsed["results"]),
               "n_reproduced": 0, "n_skipped": len(parsed["skipped"])}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
