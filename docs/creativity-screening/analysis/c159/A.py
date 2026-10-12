"""Reproduce c159 and derive the authorized participant-level contrast.

Run with: python -I -B <absolute path to this script>
The only file written by this script is its sibling A.json. Deposit programs
are read solely as text; none are imported or executed.
"""

import csv
import hashlib
import io
import json
import math
import statistics
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pymupdf
from scipy import stats


ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA_ROOT = Path(r"D:/projects/ai-skill-atlas/creativity-data")
SCRIPT = ROOT / "analysis/c159/A.py"
OUTPUT = ROOT / "analysis/c159/A.json"
ORIGINALITY = "s1_originality_ai_help_vs_no_ai_paired"
DIVERSITY = "s1_diversity_contribution_ai_help_vs_no_ai_paired"
READ_FILES = []


def read_bytes(path):
    path = Path(path)
    content = path.read_bytes()
    name = path.as_posix()
    if name not in READ_FILES:
        READ_FILES.append(name)
    return content


def read_text(path):
    return read_bytes(path).decode("utf-8-sig")


def read_deposit(manifest, deposit, relative_path):
    entry = manifest["deposits"][deposit]["files"][relative_path]
    content = read_bytes(Path(entry["path"]))
    if hashlib.sha256(content).hexdigest() != entry["sha256"]:
        raise ValueError("Manifest hash mismatch: " + entry["path"])
    return content.decode("utf-8-sig")


def csv_records(text):
    return list(csv.DictReader(io.StringIO(text, newline="")))


def compare(statistic, printed, computed, places=0):
    quantum = Decimal(1).scaleb(-places)
    rounded = Decimal(str(computed)).quantize(quantum, rounding=ROUND_HALF_UP)
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": rounded == Decimal(str(printed)),
    }


def main():
    extraction = json.loads(read_text(ROOT / "extraction/c159.json"))
    retrieval = json.loads(read_text(ROOT / "retrieval.json"))["c159"]
    read_text(ROOT.parent / "creativity-codebook.md")
    read_text(ROOT / "extraction-spec.md")
    # The complete markdown, including Appendices A-D, was reviewed in chunks.
    read_text(Path(retrieval["md_path"]))
    pdf_bytes = read_bytes(Path(retrieval["pdf_path"]))
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        verified_pages = {
            index + 1: document[index].get_text()
            for index in [7, 8, 9, 10, 11, 13, 16, 31, 32, 33]
        }
    assert "263 participants" in verified_pages[9]
    assert "t(262) = 5.56" in verified_pages[14]
    manifest = json.loads(read_text(DATA_ROOT / "manifest.json"))

    primary = csv_records(read_deposit(manifest, "osf-nz6ag", "CoCreativityDF.csv"))
    # The shared-sample release supplies the same outcomes, but no order or text.
    shared = csv_records(read_deposit(
        manifest, "osf-b4ztn", "Study1/study1_ai_creativity_with_header.csv"
    ))
    shared_generic = csv_records(read_deposit(
        manifest, "osf-b4ztn", "Study1/study1_ai_creativity_noheader.csv"
    ))
    for relative in ["Study1/s1_cfa.inp", "Study1/s1_sem.inp", "Study1/Corrs_Study1.R"]:
        read_deposit(manifest, "osf-b4ztn", relative)  # Text only.

    # Inspect the other supplied CSV schemas and row counts. These are Study 2,
    # not the 263-person, two-condition sample for c159; no values are pooled.
    study2_inventory = {}
    for relative in manifest["deposits"]["osf-b4ztn"]["files"]:
        if relative.startswith("Study2/") and relative.endswith(".csv"):
            text = read_deposit(manifest, "osf-b4ztn", relative)
            rows = list(csv.reader(io.StringIO(text, newline="")))
            has_header = not relative.endswith("study2_ai_creativity_noheader.csv")
            study2_inventory[relative] = {
                "rows": len(rows) - int(has_header),
                "columns": rows[0] if has_header else None,
            }
    assert study2_inventory["Study2/study2_ai_creativity_with_header.csv"]["rows"] == 184

    assert len({row["ID"] for row in primary}) == len(primary)
    assert len(shared) == len(shared_generic) == len(primary)
    for row, other, generic in zip(primary, shared, shared_generic):
        for original, later, anonymous in [
            ("Originality_AIhelp", "orig_ai", "X8"),
            ("Originality_noAI", "orig", "X7"),
            ("WordCount_AIhelp", "elab_ai", "X10"),
            ("WordCount_noAI", "elab", "X9"),
        ]:
            assert float(row[original]) == float(other[later]) == float(generic[anonymous])
    assert not any(row["id"] == "109087" for row in shared)
    assert not any(row["X1"] == "109087" for row in shared_generic)

    estimates = {estimate["slug"]: estimate for estimate in extraction["estimates"]}
    estimate = estimates[ORIGINALITY]
    printed = estimate["stats"]
    treatment = [float(row["Originality_AIhelp"]) for row in primary]
    control = [float(row["Originality_noAI"]) for row in primary]
    assert all(math.isfinite(x) and 0 <= x <= 1 for x in treatment + control)
    differences = [t - c for t, c in zip(treatment, control)]
    assert all(
        math.isclose(d, float(row["Originality_DifferenceScore"]), abs_tol=1e-12)
        for d, row in zip(differences, primary)
    )
    n = len(primary)
    treatment_mean = statistics.mean(treatment)
    control_mean = statistics.mean(control)

    # Reproduction comes first. Counts and arm means are the required gate.
    reproduced = [
        compare("n_treatment", estimate["n_treatment"], n),
        compare("n_control", estimate["n_control"], n),
        compare("n_total_unique_people", estimate["n_total"], n),
        compare("treatment_mean", printed["treatment_mean"], treatment_mean, 2),
        compare("control_mean", printed["control_mean"], control_mean, 2),
    ]
    # Also reproduce the reported paired test, p bound, and interval endpoints.
    paired_test = stats.ttest_rel(treatment, control)
    interval = paired_test.confidence_interval(confidence_level=0.95)
    dz = float(paired_test.statistic) / math.sqrt(n)
    reproduced.extend([
        compare("paired_t", printed["test"]["value"], float(paired_test.statistic), 2),
        compare("paired_t_df", printed["test"]["df"], n - 1),
        {
            "statistic": "paired_t_p_value",
            "printed": printed["p_value"],
            "computed": float(paired_test.pvalue),
            "match": bool(paired_test.pvalue < 0.001),
        },
        compare("paper_d_if_standardized_by_paired_difference_sd", printed["paper_effect"]["value"], dz, 2),
        compare("paired_t_95ci_lower", printed["ci_lower"], float(interval.low), 3),
        compare("paired_t_95ci_upper", printed["ci_upper"], float(interval.high), 3),
    ])

    computed = {
        key: None for key in [
            "n_treatment", "n_control", "treatment_mean", "treatment_sd",
            "control_mean", "control_sd", "difference", "difference_se",
            "se_type", "n_clusters",
        ]
    }
    notes = (
        "Sources: PDF pp. 8-12 and 14; full markdown and Appendices A-D reviewed. "
        "CoCreativityDF.csv has 263 unique IDs, with one scored story per condition "
        "and no missing originality scores. Use every released row, without further "
        "exclusions. The paper removed 68 external-aid users, 53 attention-check "
        "failures, and 7 intelligence-test outliers before reporting this final sample; "
        "the release does not contain the 128 excluded participants or their flags. "
        "Prompt-count outlier exclusions on PDF pp. 15-16 concern correlational "
        "analyses and do not apply to this paired contrast. "
        "Treatment is Originality_AIhelp; control is Originality_noAI. "
        "Originality_DifferenceScore equals treatment minus control to numerical "
        "precision. All originality and word-count values also match row for row "
        "in both Study1 CSVs from osf-b4ztn, despite different ID labels. The latter "
        "release's Mplus exclusion of ID 109087 removes no supplied row. Study2 "
        "contains different tasks and samples and is not used for this contrast. "
        "Arm SDs use denominator n-1 across people. The paired difference is "
        "mean(treatment_i-control_i), and its SE is "
        "SD(treatment_i-control_i, ddof=1)/sqrt(n). Counts refer to the same 263 "
        "people in both conditions, not 526 independent people. "
        "The PDF literally prints both arm SDs as '08'; no numeric printed-SD "
        "comparison is made. The SDs below are computed from posted scores. "
        "The printed d matches paired d_z, but its intended standardizer is "
        "not identified by the paper. Likewise, a paired-t confidence interval "
        "reproduces the printed bounds without establishing their unstated target. "
        "No scores were rescaled. Condition order is absent, preventing a "
        "first_round contrast; participant IDs and CSV row positions are not "
        "treated as order. All participants had a practice task with AI available "
        "before the two scored conditions, and the all-round estimate may include "
        "order or carryover effects."
    )
    skipped = [
        {
            "slug": ORIGINALITY,
            "reason": (
                "round first_round: the full-sample paired result is reproduced, "
                "but neither CoCreativityDF.csv nor either shared-sample Study1 "
                "CSV contains randomized condition order, first-condition labels, "
                "or story timestamps. PDF p. 9 reports randomized order but no "
                "participant-level mapping or analyzed counts by order. A first-round "
                "HC2 contrast and its arm counts cannot be recovered without guessing."
            ),
        },
        {
            "slug": DIVERSITY,
            "reason": (
                "Rounds all and first_round skipped under rule 5. PDF pp. 11-12 "
                "define a leave-one-story-out change in the mean pairwise semantic "
                "distance of each prompt-specific pool, using final-layer "
                "paraphrase-multilingual-MiniLM-L12-v2 embeddings after removal "
                "of prompt words. CoCreativityDF.csv supplies only stored "
                "Diversity_AIhelp, Diversity_noAI, and Diversity_DifferenceScore "
                "values; it supplies no story texts, prompt assignments, or "
                "embeddings. Both shared-sample Study1 CSVs also lack these "
                "inputs. Texts in the supplied Study2 release belong to a different "
                "study. Consequently the original embedding and reference-pool "
                "procedure cannot be recomputed exactly. Stored contributions "
                "are not substituted for a recomputed set-diversity measure or "
                "treated as independent participant outcomes. First-round "
                "condition order is also unavailable."
            ),
        },
    ]
    if all(check["match"] for check in reproduced):
        computed.update({
            "n_treatment": n,
            "n_control": n,
            "treatment_mean": treatment_mean,
            "treatment_sd": statistics.stdev(treatment),
            "control_mean": control_mean,
            "control_sd": statistics.stdev(control),
            "difference": statistics.mean(differences),
            "difference_se": statistics.stdev(differences) / math.sqrt(n),
            "se_type": "paired",
            "n_clusters": None,
        })
    else:
        failures = [check for check in reproduced if not check["match"]]
        notes += " Reproduction failed; requested derived statistics withheld: " + json.dumps(failures)

    result = {
        "cid": "c159",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": READ_FILES,
        "results": [{
            "slug": ORIGINALITY,
            "round": "all",
            "reproduced": reproduced,
            "computed": computed,
            "notes": notes,
        }],
        "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    # Confirm the written file parses; the main program also reports its counts.
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == result
    print(json.dumps({
        "cid": parsed["cid"],
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            all(check["match"] for check in record["reproduced"])
            and record["computed"]["difference"] is not None
            for record in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }))


if __name__ == "__main__":
    main()
