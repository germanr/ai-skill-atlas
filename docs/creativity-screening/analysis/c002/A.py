"""Audit and analyze c002 using only the supplied deposit.

Run with: python -I C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c002/A.py

The supplied archive contains the Organisciak classifier benchmark cited in
Appendix A, not the Ashkinaze randomized experiment. This script verifies that
finding against the complete data archive and paper before recording each
extraction estimate as skipped. It deliberately computes no experiment effect
from unrelated benchmark scores. No repository code is read as executable code,
imported, or run. CSV members are read in memory without extracting files.
The only file written by this script is the requested A.json.
"""

import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

import pymupdf


ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = ROOT / "analysis/c002/A.py"
OUTPUT = ROOT / "analysis/c002/A.json"
EXTRACTION = ROOT / "extraction/c002.json"
RETRIEVAL = ROOT / "retrieval.json"
CODEBOOK = ROOT.parent / "creativity-codebook.md"
SPEC = ROOT / "extraction-spec.md"
SOURCE_REVIEW = ROOT / "forms/data/c002.json"
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DEPOSIT_ID = "github-massivetexts-llm_aut_study"
DEPOSIT = MANIFEST.parent / DEPOSIT_ID
OUTER = DEPOSIT / "llm_aut_study.zip"
REPOSITORY = DEPOSIT / "llm_aut_study-unpacked/llm_aut_study-HEAD"
README = REPOSITORY / "README.md"
EVALUATION = REPOSITORY / "results/evaluation.zip"
BENCHMARK_MEMBER = "evaluation/gt_main2/gpt-ft-davinci-1.csv"
ITEMS = {"tire", "pants", "shoe", "table", "bottle"}
BENCHMARK_SOURCES = {
    "betal18", "bs12", "dod20", "hmsl", "motesf", "motesp",
    "setal08", "snb17", "snbmo09",
}
KNOWN_COLUMNS = {
    "", "id", "model", "participant", "prompt", "target", "predicted",
    "src", "total_tokens", "proportion", "split", "question", "response",
    "response_num", "nexamples", "ncompletions",
}
INPUTS = []


def register(path):
    value = path.as_posix()
    if value not in INPUTS:
        INPUTS.append(value)
    return path


def read_text(path):
    return register(path).read_text(encoding="utf-8")


def read_json(path):
    return json.loads(read_text(path))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def count_people(rows):
    return len({r["participant"] for r in rows if r["participant"]})


def main():
    require(sys.flags.isolated == 1, "Run this script with python -I.")
    extraction = read_json(EXTRACTION)
    retrieval = read_json(RETRIEVAL)["c002"]
    codebook = read_text(CODEBOOK)
    specification = read_text(SPEC)
    # This earlier source-availability review is contextual metadata only.
    # No other analyst's analysis script or results are read.
    read_json(SOURCE_REVIEW)
    require("## 7. Signs and counts" in codebook, "Unexpected codebook.")
    require("## 11. Diversity effects" in codebook, "Diversity rules absent.")
    require("Counts are people" in specification, "Unexpected extraction spec.")
    require(extraction["cid"] == "c002", "Unexpected extraction paper.")

    markdown = read_text(Path(retrieval["md_path"]))
    require("SI 11.3" in markdown, "Paper supplement missing.")
    with pymupdf.open(register(Path(retrieval["pdf_path"]))) as doc:
        require(len(doc) == 29, "Unexpected PDF version.")
        pdf_pages = [page.get_text() for page in doc]
    p7, p13, p18, p21, p25, p26 = [
        pdf_pages[i - 1] for i in (7, 13, 18, 21, 25, 26)
    ]
    require("Unique Participants\n844" in p7, "Study count changed.")
    require("gt_main2/gpt-ft-davinci-1.csv" in p13,
            "Benchmark provenance footnote missing.")
    require("20,121" in p13 and "2,025" in p13,
            "Prior-study provenance changed.")
    require("3414" in p18 and "3452" in p18, "Exclusion counts changed.")
    require("50 Monte Carlo runs" in p21, "Global procedure changed.")
    require("362" in p25 and "3,271" in p26, "Model counts changed.")

    manifest = read_json(MANIFEST)
    require(DEPOSIT_ID in manifest["papers"]["c002"],
            "Manifest mapping changed; review required.")
    metadata = manifest["deposits"][DEPOSIT_ID]["files"]["llm_aut_study.zip"]
    outer_bytes = register(OUTER).read_bytes()
    require(hashlib.sha256(outer_bytes).hexdigest() == metadata["sha256"],
            "Supplied archive does not match the manifest hash.")
    require(len(outer_bytes) == metadata["bytes"],
            "Supplied archive does not match the manifest size.")
    evaluation_bytes = register(EVALUATION).read_bytes()
    with zipfile.ZipFile(io.BytesIO(outer_bytes)) as repository_zip:
        candidates = [n for n in repository_zip.namelist()
                      if n.endswith("/results/evaluation.zip")]
        require(len(candidates) == 1, "Ambiguous evaluation archive.")
        require(repository_zip.read(candidates[0]) == evaluation_bytes,
                "Unpacked evaluation archive differs from the verified archive.")

    readme = read_text(README)
    require("Organisciak" in readme, "Repository identity changed.")
    require("Beyond Semantic Distance: Automated Scoring of Divergent Thinking"
            in readme, "Repository no longer identifies the benchmark study.")

    inventory = []
    all_columns = set()
    all_sources = set()
    benchmark_rows = None
    with zipfile.ZipFile(io.BytesIO(evaluation_bytes)) as archive:
        members = sorted(n for n in archive.namelist() if not n.endswith("/"))
        require(len(members) == 55, "Archive inventory changed; review required.")
        require(all(n.endswith(".csv") for n in members),
                "Unexpected archive member; no executable files are read.")
        for name in members:
            raw = archive.read(name)
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            columns = set(reader.fieldnames or [])
            rows = list(reader)
            require({"id", "participant", "prompt", "target", "predicted", "src"}
                    <= columns, "Unexpected benchmark schema: " + name)
            require(columns <= KNOWN_COLUMNS, "New fields require review: " + name)
            require(all(None not in row for row in rows), "Malformed CSV: " + name)
            all_columns.update(columns)
            all_sources.update(row["src"] for row in rows)
            inventory.append({
                "member": name,
                "rows": len(rows),
                "participants": count_people(rows),
                "columns": sorted(columns),
            })
            # Archive-qualified paths identify every CSV actually inspected.
            INPUTS.append(EVALUATION.as_posix() + "::" + name)
            if name == BENCHMARK_MEMBER:
                benchmark_rows = rows

    require(all_sources == BENCHMARK_SOURCES, "Unexpected source-study identifiers.")
    require(benchmark_rows is not None, "Cited benchmark member missing.")
    require(len(benchmark_rows) == 3030 and count_people(benchmark_rows) == 1384,
            "Cited benchmark sample changed; review required.")
    require(len({row["prompt"] for row in benchmark_rows}) == 21,
            "Cited benchmark prompts changed.")
    chosen = [row for row in benchmark_rows if row["prompt"] in ITEMS]
    require(len(chosen) == 358 and count_people(chosen) == 142,
            "Five-item benchmark subset changed; review required.")
    experimental_fields = {
        "condition", "condition_order", "trial_no", "ParticipantID",
        "ResponseChainID", "ItemCondition", "creativity_human", "ai_rel_create",
        "interest_group", "ai_feeling", "log_duration", "n_seeds",
    }
    require(not (all_columns & experimental_fields),
            "Potential experiment fields found; manual mapping required.")

    estimates = extraction["estimates"]
    require(len(estimates) == 46, "Extraction inventory changed; review required.")
    slugs = [e["slug"] for e in estimates]
    require(len(set(slugs)) == len(slugs), "Duplicate extraction slugs.")
    common = (
        "The supplied massivetexts/llm_aut_study deposit is the Organisciak "
        "classifier-validation dataset, as identified by its README and by "
        "c002 Appendix A.1, PDF p. 13, footnotes 6-7. All "
        f"{len(inventory)} CSV members of evaluation.zip were inspected; "
        "they contain earlier AUT benchmark scores, not c002 randomized "
        "experiment records. Their model field identifies scoring methods and "
        "src identifies earlier studies; neither supplies treatment assignment. "
    )
    diversity_common = (
        "The c002 participant texts, exposure/disclosure assignments, chain "
        "positions and corresponding SBERT embeddings are absent. The paper "
        "does not identify the exact SBERT checkpoint. Consequently the same "
        "texts and embedding procedure cannot be recovered, and rule 5 "
        "precludes computing this set-level outcome from a substitute corpus "
        "or treating it as a participant-level score. "
    )
    skipped = []
    family_counts = {"originality": 0, "global": 0, "slope": 0}
    for e in estimates:
        slug = e["slug"]
        locator = e["sources"][0]["locator"]
        stats = e["stats"]
        if slug.startswith("s1_originality_"):
            family_counts["originality"] += 1
            coefficient = stats["regression"]["coef"]
            reason = common + (
                f"Cannot reproduce the coefficient {coefficient:.3f} or the "
                f"{e['n_units']:,} model observations at {locator}. The cited "
                f"{BENCHMARK_MEMBER} instead has {len(benchmark_rows):,} "
                f"benchmark responses from {count_people(benchmark_rows):,} "
                "distinct benchmark participants across 21 prompts and nine "
                "source studies; its five matching AUT prompts contain "
                f"{len(chosen)} responses from {count_people(chosen)} people. "
                "These are unrelated sample inventories, not reproduced c002 "
                "counts. Table 2 (PDF p. 7) reports 844 c002 participants and "
                "3,414 retained responses; SI 3 (PDF pp. 17-18) excludes two "
                "incorrectly shown responses and 36 confirmed profane responses "
                "from 3,452. Those records and exclusion flags are unavailable, "
                "as are the model covariates and randomized condition order. "
                "No matching model sample, arm statistics, complete pairs or "
                "first-round sample can be constructed. The reproduction "
                "prerequisite is unmet; both all-round paired and first-round "
                "HC2 results are skipped without computing effects."
            )
        elif slug.startswith("s1_global_"):
            family_counts["global"] += 1
            reason = common + diversity_common + (
                f"Cannot reproduce the printed difference {stats['difference']:.6f} "
                f"at {locator}. SI 8.1 (PDF p. 21) requires actual experiment "
                "ideas after response-chain trial six, 50 samples of 50 ideas "
                "per condition-item combination, cosine distances scaled by "
                "100, and tests paired on item and Monte Carlo seed. Neither "
                "these eligible response sets nor their saved diversity values "
                "are present. Counts, arm levels and the reported difference "
                "cannot be reproduced from the supplied deposit."
            )
        elif slug.startswith("s1_diversity_slope_"):
            family_counts["slope"] += 1
            coefficient = stats["regression"]["coef"]
            reason = common + diversity_common + (
                f"Cannot reproduce the slope coefficient {coefficient:.3f} "
                f"or the {e['n_units']} pooled-set observations at {locator}. "
                "SI 8.3 (PDF p. 25) requires pooling actual submitted ideas by "
                "item, condition and response-chain trial number after trial "
                "six, then fitting a condition-by-trial mixed model controlling "
                "for pool size with item random intercepts. Missing experiment "
                "texts, chain/trial assignments and exclusion flags prevent "
                "constructing those pools. No diversity slope or uncertainty "
                "is computed from the unrelated benchmark rows."
            )
        else:
            raise ValueError("Unrecognized estimate: " + slug)
        skipped.append({"slug": slug, "reason": reason})

    require(family_counts == {"originality": 4, "global": 30, "slope": 12},
            "Unexpected estimate families.")
    result = {
        "cid": "c002",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": INPUTS,
        "results": [],
        "skipped": skipped,
    }
    # Empty results are intentional: no extracted estimate cleared reproduction.
    # Unknown experimental statistics are not replaced by benchmark numbers.
    require(OUTPUT.parent.is_dir(), "The requested output directory is missing.")
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    require(parsed == result, "Written JSON failed round-trip validation.")
    require(set(slugs) == {s["slug"] for s in parsed["skipped"]},
            "Not every estimate has been accounted for.")
    summary = {
        "cid": "c002",
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            bool(r["reproduced"]) and all(s["match"] for s in r["reproduced"])
            for r in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
