"""Independent analyst B reproduction for c094.
Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c094/B.py
Only B.json is written. Deposited programs are never executed or imported.
The full paper, including Appendices A-I, was read before this script was written.
"""

import sys
sys.dont_write_bytecode = True

import csv
import itertools
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import mean, stdev

import numpy as np
from scipy import stats

ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data/github-SM2982-replication-creativity-CHI2026/replication-creativity-CHI2026-unpacked/replication-creativity-CHI2026-HEAD")
STUDY = DEPOSIT / "analysis/Study1"
DATA = STUDY / "data/data_clean.csv"
GROUP_SUMMARY = STUDY / "data/data_group_summary.csv"
EXTRACTION = ROOT / "extraction/c094.json"
R_SOURCE = STUDY / "analysisR/Analysis_Study.Rmd"
EMBED_SOURCE = STUDY / "embeddings/refined_idea_similarity_analysis.py"
STORAGE_SOURCE = STUDY / "embeddings/improved_embedding_storage.py"
SCRIPT = ROOT / "analysis/c094/B.py"
OUTPUT = ROOT / "analysis/c094/B.json"

ARM_CODES = {
    "Question-mode (Q)": "feedback",
    "Suggestion-mode (S)": "suggestion",
    "Model-led (M)": "improvement",
    "Vanilla (V)": "vanilla",
    "Control (C)": "control",
}
ORDER = list(ARM_CODES.values())


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def holm(pvalues):
    """Holm's step-down adjustment, retaining the input ordering."""
    indices = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted = [0.0] * len(pvalues)
    running_max = 0.0
    for rank, i in enumerate(indices):
        running_max = max(running_max, min(1.0, (len(indices) - rank) * pvalues[i]))
        adjusted[i] = float(running_max)
    return adjusted


def printed_check(statistic, printed, computed, places=None):
    """Compare at the actual PDF precision, including trailing zeroes."""
    computed = int(computed) if places == 0 else float(computed)
    if isinstance(printed, str) and printed.startswith("<"):
        match = computed < float(printed[1:])
    elif places == 0:
        match = computed == printed
    else:
        unit = Decimal(1).scaleb(-places)
        rounded = Decimal(str(computed)).quantize(unit, rounding=ROUND_HALF_UP)
        match = rounded == Decimal(str(printed))
    return {"statistic": statistic, "printed": printed, "computed": computed, "match": bool(match)}


def hc2_contrast(treatment, control):
    """Participant-level OLS with intercept, binary arm indicator and HC2."""
    y = np.asarray(control + treatment, dtype=float)
    indicator = np.asarray([0.0] * len(control) + [1.0] * len(treatment))
    design = np.column_stack((np.ones(len(y)), indicator))
    bread = np.linalg.inv(design.T @ design)
    beta = bread @ design.T @ y
    residuals = y - design @ beta
    leverage = np.einsum("ij,jk,ik->i", design, bread, design)
    meat = design.T @ ((residuals ** 2 / (1.0 - leverage))[:, None] * design)
    covariance = bread @ meat @ bread
    difference = mean(treatment) - mean(control)
    se = math.sqrt(float(covariance[1, 1]))
    # For an intercept and a binary indicator, HC2 has this exact identity.
    independent_se = math.sqrt(stdev(treatment) ** 2 / len(treatment) + stdev(control) ** 2 / len(control))
    assert math.isclose(float(beta[1]), difference, rel_tol=1e-11, abs_tol=1e-12)
    assert math.isclose(se, independent_se, rel_tol=1e-11, abs_tol=1e-12)
    return {
        "n_treatment": len(treatment),
        "n_control": len(control),
        "treatment_mean": mean(treatment),
        "treatment_sd": stdev(treatment),
        "control_mean": mean(control),
        "control_sd": stdev(control),
        "difference": difference,
        "difference_se": se,
        "se_type": "HC2",
        "n_clusters": None,
    }


COMPUTED_KEYS = [
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se",
    "se_type", "n_clusters",
]


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    with (ROOT / "retrieval.json").open(encoding="utf-8") as fh:
        retrieval = json.load(fh)["c094"]

    # Documentation is inspected as inert text only, never as executable code.
    r_text = R_SOURCE.read_text(encoding="utf-8")
    embedding_text = EMBED_SOURCE.read_text(encoding="utf-8")
    storage_text = STORAGE_SOURCE.read_text(encoding="utf-8")
    assert "lm(Average ~ bot_type, data = data_clean)" in r_text
    assert "r = statistic / sqrt(n1 + n2)" in r_text
    assert "text-embedding-3-large" in embedding_text
    assert "np.savez_compressed" in storage_text

    rows = read_csv(DATA)
    summary_rows = read_csv(GROUP_SUMMARY)
    assert len(rows) == 486
    assert len({r["participant_id"] for r in rows}) == 486
    assert Counter(r["bot_type"] for r in rows) == {
        "feedback": 96, "suggestion": 95, "improvement": 101,
        "vanilla": 95, "control": 99,
    }
    assert all(r["questionnaire_completed"] == "Yes" for r in rows)
    assert all(r["ac1"] == "2" and r["ac2"] == "5" for r in rows)
    assert all(r["honesty_question_answer"] == "no" for r in rows)

    # The released Average/Idea_quality is the mean of the four rater
    # composites rounded to 2 decimals. Reconstruct and verify that outcome.
    # No further exclusions: row_type='page_visit_only' is NOT an exclusion.
    by_participant = defaultdict(list)
    participant_arm = {}
    rounded_up = 0
    for row in rows:
        rater_mean = sum(Decimal(row[f"Rater{i}"]) for i in range(1, 5)) / 4
        paper_score = rater_mean.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert paper_score == Decimal(row["Average"]) == Decimal(row["Idea_quality"])
        assert paper_score - rater_mean in (Decimal("0"), Decimal("0.005"))
        rounded_up += int(paper_score != rater_mean)
        pid = row["participant_id"]
        if pid in participant_arm:
            assert participant_arm[pid] == row["bot_type"]
        participant_arm[pid] = row["bot_type"]
        by_participant[pid].append(float(paper_score))
    assert rounded_up == 246
    participant_score = {pid: mean(scores) for pid, scores in by_participant.items()}
    samples = {
        arm: [score for pid, score in participant_score.items() if participant_arm[pid] == arm]
        for arm in ORDER
    }
    arm_means = {arm: mean(y) for arm, y in samples.items()}
    arm_sds = {arm: stdev(y) for arm, y in samples.items()}
    counts = {arm: len(y) for arm, y in samples.items()}
    for row in summary_rows:
        arm = row["bot_type"]
        assert counts[arm] == int(row["Count_Observations"])
        assert math.isclose(arm_means[arm], float(row["IdeaQuality_mean"]), abs_tol=1e-12)
        assert math.isclose(arm_sds[arm], float(row["IdeaQuality_sd"]), abs_tol=1e-12)

    # Reproduce Table 3 using the original five-arm homoskedastic model.
    # HC2 estimates below are only computed after these checks pass.
    model_df = sum(counts.values()) - len(ORDER)
    sigma = math.sqrt(sum(sum((v - arm_means[a]) ** 2 for v in samples[a]) for a in ORDER) / model_df)
    t_values = {
        a: (arm_means[a] - arm_means["control"]) / (sigma * math.sqrt(1 / counts[a] + 1 / counts["control"]))
        for a in ORDER[:-1]
    }
    parametric_p = dict(zip(ORDER[:-1], holm([float(stats.t.sf(t_values[a], model_df)) for a in ORDER[:-1]])))

    # Dunn tests use pooled midranks and the usual tie-corrected variance.
    # As in the authors' Rmd, adjust all 10 TWO-sided p values by Holm,
    # THEN convert to the indicated one-sided tail (do not reverse this order).
    people = list(participant_score)
    y = np.asarray([participant_score[pid] for pid in people])
    ranks = stats.rankdata(y, method="average")
    ranks_by_arm = defaultdict(list)
    for pid, rank in zip(people, ranks):
        ranks_by_arm[participant_arm[pid]].append(float(rank))
    rank_means = {a: mean(ranks_by_arm[a]) for a in ORDER}
    n = len(y)
    tie_counts = Counter(y)
    rank_variance = n * (n + 1) / 12 - sum(t ** 3 - t for t in tie_counts.values()) / (12 * (n - 1))
    pairs = list(itertools.combinations(ORDER, 2))
    dunn_z = {
        (a, b): (rank_means[a] - rank_means[b]) / math.sqrt(rank_variance * (1 / counts[a] + 1 / counts[b]))
        for a, b in pairs
    }
    dunn_two_sided_adjusted = dict(zip(pairs, holm([float(2 * stats.norm.sf(abs(dunn_z[p]))) for p in pairs])))

    common_notes = (
        "Study 1, individually randomized between-person design; round=all. "
        "Use all 486 unique participants in analysis/Study1/data/data_clean.csv, with no additional exclusions. "
        "Section 4.3 (PDF p. 7) reports 502 recruited and 16 excluded: 10 attention-check failures, "
        "2 unauthorized AI use, 2 nonsense answers, 1 duplicate participation, and 1 incomplete questionnaire. "
        "The released file is already post-exclusion; excluded records are not available for an independent audit. "
        "All retained rows have questionnaire_completed=Yes, ac1=2, ac2=5 and honesty_question_answer=no. "
        "Retain the 97 rows labeled page_visit_only: they have complete quality ratings and belong to the published analyzed sample. "
        "Mapping from the deposited Rmd lines 38-47: feedback=Question-mode, suggestion=Suggestion-mode, "
        "improvement=Model-led, vanilla=Vanilla, control=Control. "
        "Each person has one scored final idea and four rater composites. PDF pp. 7 and 22 define the score "
        "as average originality/usefulness across raters, judging only the first idea if several were submitted. "
        "Average and Idea_quality are identical and equal the four-rater mean rounded half-up to two decimals; "
        "246 values are 0.005 above their unrounded rater mean. This script reconstructs and uses the published "
        "rounded participant outcome, because the Rmd analyzes Average (lines 476 and 1555). "
        "Using unrounded rater means would fail the printed Vanilla mean (2.693421 -> 2.69 rather than 2.70). "
        "Arm means, sample SDs (n-1), and counts are checked against Table 2, PDF p. 12, "
        "and also against the deposited data_group_summary.csv. "
        "Matching is evaluated at PDF precision: means/SDs/test statistics/effect sizes to two decimals, "
        "p values to three decimals, counts/df exactly, and inequality p values against the printed bound. "
        "This is not a randomized-order within-person study, so no first_round record is appropriate."
    )
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        if estimate["construct"] == "diversity":
            if "_change_" in slug:
                measure = (
                    "The randomized between-arm change outcome requires initial idea_div_condition and "
                    "refined_div_to_initial_centroid recomputed from initial/refined embedding sets, "
                    "using each condition's initial centroid (PDF pp. 8-9 and 24)."
                )
            else:
                measure = (
                    "The diversity outcome is cosine distance from each final idea to the leave-one-out "
                    "centroid of the other final ideas in its condition (refined_div_condition; PDF p. 7)."
                )
            reason = (
                measure + " Exact recomputation requires the original text-embedding-3-large vectors and matching texts. "
                "The permitted CSV inputs contain idea texts and supplied distance scores, but no embedding vectors. "
                "The deposit lists analysis/Study1/data/ideas_with_diversity_scores_embeddings.npz; NPZ is outside "
                "the brief's enumerated readable data formats, so that file was not opened. The matching "
                "ideas_with_diversity_scores_data.csv and embeddings_metadata.json named by the storage code "
                "are also absent from the deposited file inventory. Exact model/text-based reconstruction was "
                "therefore not established. Under rule 5, supplied distances were not substituted for a "
                "recomputed set measure, and no participant-level SD or HC2 SE was assigned to this set outcome."
            )
            skipped.append({"slug": slug, "reason": reason})
            continue

        assert estimate["construct"] == "overall_creativity"
        assert estimate["within_person"] is None
        treatment = ARM_CODES[estimate["treatment_arm"]]
        control = ARM_CODES[estimate["control_arm"]]
        assert control == "control"
        paper_stats = estimate["stats"]
        reproduced = [
            printed_check("n_treatment", estimate["n_treatment"], counts[treatment], 0),
            printed_check("n_control", estimate["n_control"], counts[control], 0),
            printed_check("treatment_mean", paper_stats["treatment_mean"], arm_means[treatment], 2),
            printed_check("treatment_sd", paper_stats["treatment_sd"], arm_sds[treatment], 2),
            printed_check("control_mean", paper_stats["control_mean"], arm_means[control], 2),
            printed_check("control_sd", paper_stats["control_sd"], arm_sds[control], 2),
        ]
        if slug.endswith("_dunn"):
            z = dunn_z[(treatment, control)]
            p2 = dunn_two_sided_adjusted[(treatment, control)]
            p1 = p2 / 2 if z > 0 else 1 - p2 / 2
            effect_r = z / math.sqrt(counts[treatment] + counts[control])
            reproduced.extend([
                printed_check("test.z", paper_stats["test"]["value"], z, 2),
                printed_check("p_value_Holm_one_sided", paper_stats["p_value"], p1, 3),
                printed_check("paper_effect.r", paper_stats["paper_effect"]["value"], effect_r, 2),
            ])
            method_notes = (
                "Table 14, PDF p. 25: Dunn z uses all 486 quality scores, pooled midranks and tie correction. "
                "The posted Rmd lines 1555-1559 applies Holm to all ten two-sided pairwise p values, "
                "then divides the adjusted p by two for the positive treatment-control z. "
                "Its r formula is z/sqrt(n_treatment+n_control). This robustness record reuses the same "
                "outcome and participants as the matching main record; it is not an independent sample."
            )
        else:
            reproduced.extend([
                printed_check("test.t", paper_stats["test"]["value"], t_values[treatment], 2),
                printed_check("test.df", paper_stats["test"]["df"], model_df, 0),
                printed_check("p_value_Holm_one_sided", paper_stats["p_value"], parametric_p[treatment], 3),
                printed_check("paper_effect.d", paper_stats["paper_effect"]["value"], (arm_means[treatment] - arm_means[control]) / sigma, 2),
            ])
            method_notes = (
                "Table 3, PDF p. 12: reproduce the five-arm linear model with df=481, "
                "common residual variance and Holm adjustment of the four one-sided quality contrasts. "
                "The posted Rmd lines 504-512 confirms that Cohen's d uses the residual SD of that full "
                "five-arm model. This original model is used only for reproduction."
            )

        failures = [check for check in reproduced if not check["match"]]
        if failures:
            # The user's strict reproduce-first rule also applies to a failed
            # secondary statistic. Do not call hc2_contrast for this record.
            computed = {key: None for key in COMPUTED_KEYS}
            details = "; ".join(
                f"{c['statistic']}: printed {c['printed']}, computed {c['computed']:.15g}"
                for c in failures
            )
            decision_notes = (
                "REPRODUCTION FAILED: " + details + ". For the model-led Dunn record, "
                "z/sqrt(101+99)=0.274665132743879, rounding to 0.27 rather than the printed 0.28. "
                "Counts, means, SDs, z and p all match. Nevertheless, no new contrast statistics are "
                "computed for this record under rule 3; all computed fields, including se_type, are null. "
                "It remains in results to retain the attempted reproduction rather than being silently dropped."
            )
        else:
            computed = hc2_contrast(samples[treatment], samples[control])
            decision_notes = (
                "All checked printed statistics reproduce. The requested new analysis is OLS of the "
                "participant quality score on an intercept and the treatment indicator, restricted to "
                "these two arms, with HC2 covariance (residual squared divided by 1 minus leverage). "
                "difference is treatment mean minus control mean; HC2 difference_se is equivalently "
                "sqrt(treatment_sd^2/n_treatment + control_sd^2/n_control). Randomization is individual; "
                "there are no randomized clusters."
            )
        results.append({
            "slug": slug,
            "round": "all",
            "reproduced": reproduced,
            "computed": computed,
            "notes": common_notes + " " + method_notes + " " + decision_notes,
        })

    # data_files lists the data plus documentary files read in the analyst's
    # audit. Only the CSVs supply participant observations; code is text only.
    input_files = [
        DATA, GROUP_SUMMARY, EXTRACTION, ROOT / "retrieval.json",
        ROOT.parent / "creativity-codebook.md", ROOT / "extraction-spec.md",
        Path(retrieval["md_path"]), Path(retrieval["pdf_path"]),
        Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json"),
        R_SOURCE, EMBED_SOURCE, STORAGE_SOURCE,
    ]
    result_slugs = [r["slug"] for r in results]
    skipped_slugs = [s["slug"] for s in skipped]
    all_slugs = [e["slug"] for e in extraction["estimates"]]
    assert len(set(result_slugs + skipped_slugs)) == len(all_slugs)
    assert set(result_slugs + skipped_slugs) == set(all_slugs)
    obj = {
        "cid": "c094", "analyst": "B", "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in input_files],
        "results": results, "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    summary = {
        "cid": "c094", "n_results": len(results),
        "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
