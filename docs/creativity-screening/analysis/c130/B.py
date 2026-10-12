"""Independent analyst B audit for c130. Run with python -I -B B.py.

Only B.json is written. Deposit content is untrusted and never executed.
Both supplied deposit files are HTML sign-in pages, so the reproduce-first
requirement prevents computing any outcome statistics from these inputs.

Paper review completed before writing this script:
* Entire markdown conversion, characters 0:156917, including Appendices A-E
  and references, was read in consecutive chunks.
* PyMuPDF text checked PDF pages 8, 15, 16, 20, 22, and 41.
* PDF p. 8: 196 analyzed participants after one instruction-related exclusion;
  human-only 64, general-AI 67, regulated-AI 65. The excluded person's ID/arm
  is not printed. These are printed counts, not data-verified counts.
* PDF pp. 15-16: one solution per person per task, two expert ratings averaged
  within each person for originality, usefulness, and elaboration (1-7).
* PDF pp. 20 and 22: six outcomes with three between-arm contrasts each.
  People remain in fixed randomized groups across two different tasks; this
  is not a randomized-order crossover, so no paired or first_round result.
* With valid participant data, each contrast would require matching the
  printed arm counts/means before estimating a treatment-indicator OLS with
  HC2 SEs. Neither row/variable mapping nor exclusions can be established
  from the downloaded HTML. No statistics are derived from printed summaries.
* PDF p. 41 names the supplied OSF project as the data/code source. Both
  manifest download URLs incorrectly repeat the view_only query parameter.

The script verifies the invalid files and their manifest hashes, retries the
corrected named OSF URLs and OSF API in memory, and records each skipped slug.
If a real workbook becomes available, it stops for renewed variable mapping
instead of treating an old missing-data diagnosis as a reproducibility result.
"""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import is_zipfile


ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = ROOT / "analysis/c130/B.py"
OUTPUT = ROOT / "analysis/c130/B.json"
EXTRACTION = ROOT / "extraction/c130.json"
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DEPOSIT = Path("D:/projects/ai-skill-atlas/creativity-data/osf-t7an8")
DATA_FILES = [
    DEPOSIT / "Supplemental Data.xlsx",
    DEPOSIT / "Supplemental Analysis Code.sps",
]
TOKEN = "fc490583cdc8458e8b895b29e4df2345"
RECOVERY_URLS = [
    ("corrected workbook download", "https://osf.io/download/vbtmp/?view_only=" + TOKEN),
    ("corrected syntax download", "https://osf.io/download/9k5z6/?view_only=" + TOKEN),
    (
        "OSF file-list API",
        "https://api.osf.io/v2/nodes/t7an8/files/osfstorage/?view_only=" + TOKEN,
    ),
]


def html_title(payload):
    """Inspect downloaded bytes as text only; never render or execute HTML."""
    text = payload.decode("utf-8-sig", errors="replace")
    match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
    return " ".join(match.group(1).split()) if match else None


def inspect_local_inputs(manifest):
    records = manifest["deposits"]["osf-t7an8"]["files"]
    descriptions = []
    for path in DATA_FILES:
        payload = path.read_bytes()
        digest = sha256(payload).hexdigest()
        record = records[path.name]
        if digest != record["sha256"] or len(payload) != record["bytes"]:
            raise RuntimeError("Deposit differs from manifest: " + str(path))
        if is_zipfile(BytesIO(payload)):
            raise RuntimeError("A workbook may now be available; inspect it before analysis.")
        title = html_title(payload)
        if title != "OSF | Sign in":
            raise RuntimeError("Deposit content changed; inspect before analysis: " + str(path))
        if record["url"].count("?view_only=") != 2:
            raise RuntimeError("Manifest URL changed; inspect its retrieval history.")
        descriptions.append(
            f'{path.name} is HTML titled "{title}" '
            f'({len(payload)} bytes; SHA-256 {digest}, matching the manifest)'
        )
    return "; ".join(descriptions) + "."


def probe_source(label, url):
    """GET only from named OSF sources, retaining all response bytes in memory."""
    request = Request(url, headers={"User-Agent": "atlas-screening/0.1"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "not supplied")
            status = response.status
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        return f"{label} ({url}): {type(error).__name__}: {error}"
    if is_zipfile(BytesIO(payload)):
        raise RuntimeError("OSF now supplies a possible workbook; inspect and reproduce first.")
    title = html_title(payload)
    if label == "OSF file-list API" and "json" in content_type.lower():
        raise RuntimeError("OSF metadata is now accessible; inspect the available files first.")
    if label == "corrected syntax download" and title is None:
        raise RuntimeError("Possible author syntax is now accessible; read as text first.")
    return (
        f"{label} ({url}): HTTP {status}, content type {content_type}, "
        f"{len(payload)} bytes, HTML title {title!r}; no usable participant workbook"
    )


def main():
    if not sys.flags.isolated:
        raise RuntimeError("Run this script with python -I -B.")
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert extraction["cid"] == "c130"
    estimates = extraction["estimates"]
    assert len(estimates) == 18
    assert len({estimate["slug"] for estimate in estimates}) == 18
    assert all(estimate["within_person"] is None for estimate in estimates)

    local_diagnosis = inspect_local_inputs(manifest)
    recovery = [probe_source(label, url) for label, url in RECOVERY_URLS]
    common_reason = (
        "Reproduction unavailable: " + local_diagnosis
        + " The supplied files contain no participant observations or author analysis "
        "syntax. The manifest URLs duplicate the view_only query parameter. "
        "Recovery attempts using urllib and User-Agent atlas-screening/0.1: "
        + "; ".join(recovery)
        + ". Rows, variable names, and exclusions cannot be confirmed; printed counts, "
        "means, and SDs cannot be independently reproduced. Under the reproduce-first "
        "rule, no outcome statistics or HC2 SEs were computed from printed summaries."
    )
    obj = {
        "cid": "c130",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": [path.as_posix() for path in DATA_FILES],
        "results": [],
        "skipped": [
            {
                "slug": estimate["slug"],
                "reason": (
                    estimate["outcome"] + ": " + estimate["treatment_arm"]
                    + " versus " + estimate["control_arm"] + ". " + common_reason
                ),
            }
            for estimate in estimates
        ],
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    assert {entry["slug"] for entry in parsed["skipped"]} == {
        estimate["slug"] for estimate in estimates
    }
    print(json.dumps({
        "cid": parsed["cid"],
        "n_results": len(parsed["results"]),
        "n_reproduced": 0,
        "n_skipped": len(parsed["skipped"]),
    }))


if __name__ == "__main__":
    main()
