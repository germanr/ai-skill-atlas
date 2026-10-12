"""Independent analyst B reanalysis of c159.

Run with: python -I -B <absolute path to this file>
Reads the named local inputs and writes only analysis/c159/B.json.
Deposited programs are never executed or imported. The R file is read as text.
"""

import sys

sys.dont_write_bytecode = True

import csv
import hashlib
import json
import math
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import mean, stdev

from scipy.stats import t as student_t


BASE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA_ROOT = Path(r"D:/projects/ai-skill-atlas/creativity-data")
SCRIPT = BASE / "analysis/c159/B.py"
OUTPUT = BASE / "analysis/c159/B.json"
MANIFEST = DATA_ROOT / "manifest.json"
EXTRACTION = BASE / "extraction/c159.json"
PRIMARY = DATA_ROOT / "osf-nz6ag/CoCreativityDF.csv"
SECONDARY = DATA_ROOT / "osf-b4ztn/Study1/study1_ai_creativity_with_header.csv"
AUTHOR_CODE = DATA_ROOT / "osf-b4ztn/Study1/Corrs_Study1.R"

# These CSVs were inspected for usable variables, condition order, and texts.
# Only PRIMARY supplies the c159 estimates. SECONDARY is a data cross-check.
CSV_INPUTS = [
    PRIMARY,
    DATA_ROOT / "osf-b4ztn/Study1/study1_ai_creativity_noheader.csv",
    SECONDARY,
    DATA_ROOT / "osf-b4ztn/Study2/s2_metaphor_llm_ratings.csv",
    DATA_ROOT / "osf-b4ztn/Study2/study2_ai_creativity_with_header.csv",
    DATA_ROOT / "osf-b4ztn/Study2/s2_co-writing_llm_ratings.csv",
    DATA_ROOT / "osf-b4ztn/Study2/study2_ai_creativity_noheader.csv",
    DATA_ROOT / "osf-b4ztn/Study2/SensitivityAnalysis/study2_human_product_ratings.csv",
    DATA_ROOT / "osf-b4ztn/Study2/SensitivityAnalysis/study2_ai_literacy.csv",
    DATA_ROOT / "osf-b4ztn/Study2/SensitivityAnalysis/study2_llm_items.csv",
    DATA_ROOT / "osf-b4ztn/Study2/SensitivityAnalysis/study2_participants.csv",
]


def read_json(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def path_key(path):
    return str(path).replace("\\", "/").casefold()


def manifest_hashes(obj):
    found = {}
    if isinstance(obj, dict):
        if isinstance(obj.get("path"), str) and isinstance(obj.get("sha256"), str):
            found[path_key(obj["path"])] = obj["sha256"]
        for value in obj.values():
            found.update(manifest_hashes(value))
    elif isinstance(obj, list):
        for value in obj:
            found.update(manifest_hashes(value))
    return found


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames), list(reader)


def rounded(value, places):
    return Decimal(str(value)).quantize(
        Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP
    )


def check(statistic, printed, computed, places=None):
    if isinstance(printed, str) and printed.startswith("<"):
        matches = computed < float(printed[1:])
    elif places is None:
        matches = computed == printed
    else:
        matches = rounded(computed, places) == rounded(printed, places)
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(matches),
    }


def column(rows, name):
    values = [float(row[name]) for row in rows]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Non-finite value in " + name)
    return values


def main():
    extraction = read_json(EXTRACTION)
    estimates = {row["slug"]: row for row in extraction["estimates"]}
    originality_slug = "s1_originality_ai_help_vs_no_ai_paired"
    diversity_slug = "s1_diversity_contribution_ai_help_vs_no_ai_paired"
    assert set(estimates) == {originality_slug, diversity_slug}

    expected_hashes = manifest_hashes(read_json(MANIFEST))
    actual_hashes = {}
    for path in CSV_INPUTS + [AUTHOR_CODE]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected_hashes[path_key(path)], "Input hash mismatch: " + str(path)
        actual_hashes[path_key(path)] = digest

    tables = {path: read_csv(path) for path in CSV_INPUTS}
    # Static inspection only: no eval, exec, subprocess, or import of this file.
    author_code_text = AUTHOR_CODE.read_text(encoding="utf-8")
    assert "orig_ai" in author_code_text and "orig" in author_code_text

    primary_columns, rows = tables[PRIMARY]
    secondary_columns, secondary_rows = tables[SECONDARY]
    assert len(rows) == len({row["ID"] for row in rows}) == 263
    assert len(secondary_rows) == len({row["id"] for row in secondary_rows}) == 263

    # Compare multisets of paired outcomes without assuming IDs are shared.
    # The deposits recode IDs: none of the same-position labels agree.
    primary_names = [
        "Originality_AIhelp", "Originality_noAI", "WordCount_AIhelp", "WordCount_noAI"
    ]
    secondary_names = ["orig_ai", "orig", "elab_ai", "elab"]
    primary_pairs = [tuple(float(row[name]) for name in primary_names) for row in rows]
    secondary_pairs = [
        tuple(float(row[name]) for name in secondary_names) for row in secondary_rows
    ]
    assert Counter(primary_pairs) == Counter(secondary_pairs)
    assert primary_pairs == secondary_pairs
    assert not any(a["ID"] == b["id"] for a, b in zip(rows, secondary_rows))

    # One story score per participant per condition; no averaging across raters
    # or outputs is necessary. The deposited 263-row analysis sample is used
    # intact, without prompt-count outlier or self-assessment exclusions.
    treatment = column(rows, "Originality_AIhelp")
    control = column(rows, "Originality_noAI")
    deltas = [a - b for a, b in zip(treatment, control)]
    stored_deltas = column(rows, "Originality_DifferenceScore")
    assert all(abs(a - b) < 1e-12 for a, b in zip(deltas, stored_deltas))
    n = len(deltas)
    t_mean, c_mean = mean(treatment), mean(control)
    delta_mean = mean(deltas)
    delta_sd = stdev(deltas)  # denominator n - 1
    paired_se = delta_sd / math.sqrt(n)
    paired_t = delta_mean / paired_se
    paired_p = float(2 * student_t.sf(abs(paired_t), df=n - 1))
    critical_t = float(student_t.ppf(0.975, df=n - 1))
    interval = [delta_mean - critical_t * paired_se, delta_mean + critical_t * paired_se]
    printed = estimates[originality_slug]
    stats = printed["stats"]
    reproduction = [
        check("n_treatment", printed["n_treatment"], n),
        check("n_control", printed["n_control"], n),
        check("n_total_unique_people", printed["n_total"], n),
        check("treatment_mean", stats["treatment_mean"], t_mean, 2),
        check("control_mean", stats["control_mean"], c_mean, 2),
        check("paired_t", stats["test"]["value"], paired_t, 2),
        check("paired_t_df", stats["test"]["df"], n - 1),
        check("p_value", stats["p_value"], paired_p),
        check("paper_d_if_paired_difference_sd", stats["paper_effect"]["value"],
              delta_mean / delta_sd, 2),
        check("ci_lower_if_paired_mean_difference", stats["ci_lower"], interval[0], 3),
        check("ci_upper_if_paired_mean_difference", stats["ci_upper"], interval[1], 3),
    ]

    notes = (
        "Sources: c159 PDF pp. 8-12 and 14; the complete 444-line markdown, including "
        "references and Appendices A-D, was read. All 263 rows in CoCreativityDF.csv "
        "have distinct ID values and both originality scores. Originality_AIhelp is "
        "treatment and Originality_noAI is control; each is one MAoSS score for one "
        "participant's story, on the deposited 0-1 scale. The posted sample matches "
        "the final sample after the paper's exclusions (68 external-aid reports, "
        "53 attention-check failures, and 7 low intelligence-test scores from 391 "
        "recruited people). Exclusion flags and pre-exclusion rows are unavailable, "
        "so those exclusions cannot be independently reconstructed. No additional "
        "exclusions were applied. Prompt-count outlier removals concern separate "
        "correlational analyses, and missing self-assessments do not exclude story "
        "scores. Originality_DifferenceScore agrees with treatment minus control "
        "for every row to floating-point tolerance. The paired score/word-count "
        "tuples exactly match orig_ai, orig, elab_ai, and elab in the 263-row "
        "osf-b4ztn Study1 table, both as multisets and in row order. IDs differ "
        "between deposits and were not joined. Study2 files concern a different "
        "study and supply no c159 observations. Every audited deposit file was "
        "checked against its SHA-256 in manifest.json; the primary CSV hash is "
        + actual_hashes[path_key(PRIMARY)] + ". "
        "The PDF literally prints both originality SDs as '08'; those ambiguous "
        "strings are not interpreted as numerical SDs for a reproduction check. "
        "The SDs below are computed directly across participants with denominator "
        "n-1. Difference = mean(AI-help_i - No-AI_i); difference_se = "
        "sd(AI-help_i - No-AI_i, ddof=1)/sqrt(263). The paired t, its degrees of "
        "freedom and its two-sided p-value reproduce the printed test. The d and "
        "CI checks are explicitly conditional arithmetic checks: d_z and the "
        "paired mean-difference t interval round to the printed numbers, but the "
        "paper does not specify the standardizer or interval target. This does "
        "not resolve those labels in the reconciled extraction. Scores in the "
        "deposited originality columns are rounded to at most two decimal places; "
        "derived quantities reflect those available values. Both arm counts "
        "represent the same 263 people, not 526 independent people. Condition "
        "order was randomized, but it is absent from the relevant data, so "
        "first_round is explicitly skipped. All participants had an AI-available "
        "practice story before the scored conditions (PDF pp. 10-11)."
    )

    results = []
    skipped = []
    if all(item["match"] for item in reproduction):
        computed = {
            "n_treatment": n,
            "n_control": n,
            "treatment_mean": t_mean,
            "treatment_sd": stdev(treatment),
            "control_mean": c_mean,
            "control_sd": stdev(control),
            "difference": delta_mean,
            "difference_se": paired_se,
            "se_type": "paired",
            "n_clusters": None,
        }
    else:
        # A changed input must never yield an effect after failed reproduction.
        computed = None
        skipped.append({
            "slug": originality_slug,
            "reason": "all: reproduction failed; inspect the false checks in results.",
        })
    results.append({
        "slug": originality_slug,
        "round": "all",
        "reproduced": reproduction,
        "computed": computed,
        "notes": notes,
    })

    # No condition-order field exists in either c159-sample table. In particular,
    # ID order and the secondary study's task_num must not stand in for order.
    order_tokens = ("order", "round", "sequence", "first", "condition", "task_num")
    assert not any(
        token in name.lower()
        for name in primary_columns + secondary_columns
        for token in order_tokens
    )
    skipped.append({
        "slug": originality_slug,
        "reason": (
            "first_round only: the 17-column CoCreativityDF.csv and the related "
            "12-column osf-b4ztn Study1 tables contain no randomized condition "
            "order, round identifier, timestamp, or first-condition assignment. "
            "The paper reports no first-round arm counts or results. Participant "
            "IDs and row order cannot establish who received AI first. The task_num "
            "fields in osf-b4ztn Study2 belong to a different study. Therefore "
            "first-round arm membership and the requested HC2 contrast are "
            "unidentifiable from the supplied data. No first-round values are imputed."
        ),
    })

    # Diagnostic summaries only: these columns cannot regenerate the set-based
    # measure. Do not compute a diversity treatment effect or standard error.
    diversity_t = column(rows, "Diversity_AIhelp")
    diversity_c = column(rows, "Diversity_noAI")
    diversity_t_mean = mean(diversity_t)
    diversity_c_mean = mean(diversity_c)
    diversity_t_sd = stdev(diversity_t)
    diversity_c_sd = stdev(diversity_c)
    div_stats = estimates[diversity_slug]["stats"]
    skipped.append({
        "slug": diversity_slug,
        "reason": (
            "all and first_round: this is a leave-one-out contribution to a "
            "prompt-specific set of stories, not an independent participant "
            "outcome. Under rule 5 it can be reported only if regenerated using "
            "the same texts and embedding procedure. PDF pp. 11-12 require "
            "paraphrase-multilingual-MiniLM-L12-v2 final-layer embeddings, "
            "removal of each prompt's three words, and all pairwise cosine "
            "distances in the two prompt-specific story pools. The c159 data "
            "contain only precomputed diversity scores, with no c159 story "
            "texts, story-to-prompt assignments, embeddings, or pairwise "
            "distance matrices. The related Study1 CSVs also lack these inputs; "
            "Study2 texts cannot substitute for the c159 texts. Moreover, even "
            "a diagnostic summary of the posted scores does not fully reproduce "
            "the printed precision: AI-help mean "
            f"{diversity_t_mean:.16g} rounds to {rounded(diversity_t_mean, 6)} "
            f"rather than the printed {div_stats['treatment_mean']:.6f}; AI-help SD "
            f"{diversity_t_sd:.16g} rounds to {rounded(diversity_t_sd, 5)} "
            f"rather than the printed {div_stats['treatment_sd']:.5f}. "
            f"No-AI mean {diversity_c_mean:.16g} and SD {diversity_c_sd:.16g} "
            f"do round to the printed {div_stats['control_mean']:.6f} and "
            f"{div_stats['control_sd']:.5f}, and both columns contain 263 values. "
            "These diagnostics do not constitute reproduction of the embedding "
            "measure. No diversity effect, participant SD record, or standard "
            "error is supplied. First-round condition order is also unavailable."
        ),
    })

    output = {
        "cid": "c159",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": [path.as_posix() for path in CSV_INPUTS + [AUTHOR_CODE, MANIFEST]],
        "results": results,
        "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1)
    # Explicit parsing confirmation; reject NaN/Infinity if ever introduced.
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError("Nonstandard JSON constant: " + value)
        ))
    assert parsed == output
    summary = {
        "cid": "c159",
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            result["computed"] is not None
            and all(item["match"] for item in result["reproduced"])
            for result in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
