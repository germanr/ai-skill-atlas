"""Independent analyst B audit for c450.

Run: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c450/B.py

Only B.json is written. No deposited code or analyst A file is read.
The full main markdown (20 PDF pages) and researchtools.md conversion
(4 supplementary PDF pages) were read during this audit. Numerical sources
were checked against PDF pages 4 and 7-9; figure captions against pages 16-19.

The two numerical overall-creativity comparisons fail reproduction. Their
requested participant-level statistics therefore remain null. Complete-case
ANCOVAs below are explicitly diagnostic; they do not replace the unavailable
five MICE datasets or establish the authors' retained analysis samples.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
import statsmodels.api as sm


BASE = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = BASE / "analysis/c450/B.py"
OUTPUT = BASE / "analysis/c450/B.json"
EXTRACTION = BASE / "extraction/c450.json"
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DATA = Path(
    "D:/projects/ai-skill-atlas/creativity-data/"
    "researchsquare-rs-8774138/b9dc5dfe77302df009deb76e.sav"
)
EXPECTED_SHA256 = "5de17063af3604e2e8a92c49e8c235776127a9f2339c2d5efcff8c4cc3227ebc"
ARM_LABELS = {1: "AI-first", 2: "AI-follow", 3: "AI-parallel", 4: "Human-only"}
# PDF p. 4, section 2.1: valid-case pool, before model-specific exclusions.
PRINTED_POOL_COUNTS = {1: 28, 2: 25, 3: 30, 4: 29}
COVARIATES = ["Age", "Gender", "AI I Literacy", "Creative Personality"]
DIMENSIONS = {
    "originality": "Originality",
    "fluency": "Fluency",
    "flexibility": "Flexibility",
    "elaboration": "Elaboration",
}
COMPUTED_KEYS = [
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se",
    "se_type", "n_clusters",
]


def comparison(statistic, printed, computed, decimals=0):
    """Compare at the printed precision, never equating null with null."""
    matched = False
    if printed is not None and computed is not None:
        if isinstance(printed, (int, float)):
            quantum = Decimal(1).scaleb(-decimals)
            matched = (
                Decimal(str(printed)).quantize(quantum, rounding=ROUND_HALF_UP)
                == Decimal(str(computed)).quantize(quantum, rounding=ROUND_HALF_UP)
            )
        else:
            matched = printed == computed
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(matched),
    }


def read_data():
    with MANIFEST.open(encoding="utf-8") as fh:
        manifest = json.load(fh)
    entry = manifest["deposits"]["researchsquare-rs-8774138"]["files"][DATA.name]
    digest = hashlib.sha256(DATA.read_bytes()).hexdigest()
    assert digest == entry["sha256"] == EXPECTED_SHA256
    raw, metadata = pyreadstat.read_sav(str(DATA), apply_value_formats=False)
    assert raw.shape == (113, 28)
    names_to_labels = {
        key: value.strip() for key, value in metadata.column_names_to_labels.items()
    }
    assert len(set(names_to_labels.values())) == len(raw.columns)
    group_variable = next(k for k, v in names_to_labels.items() if v == "Group")
    assert metadata.variable_value_labels[group_variable] == ARM_LABELS
    df = raw.rename(columns=names_to_labels)
    blank = df.drop(columns="Name").isna().all(axis=1)
    blank &= df["Name"].fillna("").str.strip().eq("")
    assert (df.index[blank] + 1).tolist() == [113]
    df = df.loc[~blank].copy()
    assert df["Group"].isin(ARM_LABELS).all()
    assert df["Name"].is_unique
    # Names are never printed or written; original row positions identify diagnostics.
    df = df.drop(columns="Name")
    counts = {int(k): int(v) for k, v in df.groupby("Group").size().items()}
    assert counts == PRINTED_POOL_COUNTS
    outcome_columns = [c for c in df.columns if "Draft" in c]
    assert len(outcome_columns) == 20
    assert not df[outcome_columns].isna().any().any()
    return df, names_to_labels, counts


def score_label(estimate):
    tokens = estimate["slug"].split("_")
    stage = "Preliminary" if tokens[1] == "first" else "Final"
    prefix = "Deepseek Evaluation - " if estimate["measure"] == "automated_score" else ""
    if tokens[3] == "overall":
        return prefix + stage + " Draft Average"
    return prefix + DIMENSIONS[tokens[3]] + " (" + stage + " Draft)"


def aggregation_mismatches(df, prefix, stage):
    """Check stored totals; never silently repair an author's score."""
    stored = df[prefix + stage + " Draft Average"]
    component_labels = [
        prefix + dim + " (" + stage + " Draft)" for dim in DIMENSIONS.values()
    ]
    component_average = df[component_labels].mean(axis=1)
    different = ~np.isclose(stored, component_average, rtol=0, atol=1e-8)
    return (df.index[different] + 1).tolist()


def complete_case_diagnostic(df, prefix):
    """OLS ANCOVA + one Cook exclusion pass; no guessed MICE specification."""
    pre = prefix + "Preliminary Draft Average"
    post = prefix + "Final Draft Average"
    cc = df[["Group", pre, post] + COVARIATES].dropna().copy()

    def fit(frame):
        x = pd.DataFrame({"intercept": 1.0}, index=frame.index)
        for group in (1, 2, 3):
            x["arm_" + str(group)] = (frame["Group"] == group).astype(float)
        for label in [pre] + COVARIATES:
            x[label] = frame[label]
        return sm.OLS(frame[post], x).fit()

    def describe(frame):
        fitted = fit(frame)
        reference = fitted.model.exog.mean(axis=0)
        adjusted_means = {}
        for group in ARM_LABELS:
            x = reference.copy()
            x[1:4] = [float(group == g) for g in (1, 2, 3)]
            adjusted_means[group] = float(x @ np.asarray(fitted.params))
        return {
            "n": len(frame),
            "arm_counts": {
                int(k): int(v) for k, v in frame.groupby("Group").size().items()
            },
            "adjusted_means": adjusted_means,
        }

    fitted = fit(cc)
    cutoff = 4.0 / len(cc)
    excluded = fitted.get_influence().cooks_distance[0] > cutoff
    return {
        "before": describe(cc),
        "after": describe(cc.loc[~excluded]),
        "cook_cutoff": cutoff,
        "n_excluded": int(excluded.sum()),
        "excluded_source_rows": (cc.index[excluded] + 1).tolist(),
    }


def failed_overall_result(estimate, df, counts):
    human = estimate["measure"] == "human_raters"
    prefix = "" if human else "Deepseek Evaluation - "
    label = score_label(estimate)
    stats = estimate["stats"]
    # Seven human-rating exclusions: PDF p. 8, section 3.2.
    # Eight DeepSeek-rating exclusions: PDF p. 9, section 3.3.
    printed_exclusions = 7 if human else 8
    missing = df[COVARIATES].isna().any(axis=1)
    diagnostic = complete_case_diagnostic(df, prefix)
    raw_means = df.groupby("Group")[label].mean()
    checks = [comparison("valid_case_pool_n_total (PDF p. 4)", 112, len(df))]
    checks.extend(
        comparison(
            "valid_case_pool_n_" + ARM_LABELS[group] + " (PDF p. 4)",
            PRINTED_POOL_COUNTS[group], counts[group],
        )
        for group in ARM_LABELS
    )
    checks.append(comparison(
        "participants_with_missing_data (PDF p. 7)", 5, int(missing.sum())
    ))
    # A rounding match of an unadjusted treatment mean is not a replication
    # of an adjusted mean from an unidentified, imputed, trimmed sample.
    for arm, group in (("treatment", 2), ("control", 4)):
        checks.append(comparison(
            arm + "_mean: unadjusted full-cohort diagnostic versus printed adjusted mean",
            stats[arm + "_mean"], float(raw_means[group]), 2,
        ))
    checks.append(comparison(
        "influential_case_count: complete-case Cook diagnostic versus paper MICE analysis",
        printed_exclusions, diagnostic["n_excluded"],
    ))
    for arm, group in (("treatment", 2), ("control", 4)):
        checks.append(comparison(
            arm + "_mean: complete-case ANCOVA after Cook exclusions (diagnostic)",
            stats[arm + "_mean"], diagnostic["after"]["adjusted_means"][group], 2,
        ))
    # Exact paper-model values cannot be confirmed from this deposit.
    for field in ("treatment_mean", "control_mean", "treatment_se", "control_se"):
        checks.append(comparison(
            field + ": exact paper MICE and exclusion procedure unavailable",
            stats[field], None, 2,
        ))
    checks.append(comparison("paper_Cohens_d: unspecified standardizer", stats["paper_effect"]["value"], None, 2))
    checks.append(comparison("paper_pairwise_p_value: exact analysis unavailable", stats["p_value"], None, 3))

    before = diagnostic["before"]
    after = diagnostic["after"]
    mismatch_pre = aggregation_mismatches(df, prefix, "Preliminary")
    mismatch_post = aggregation_mismatches(df, prefix, "Final")
    notes = (
        "NOT REPRODUCED. The printed arm means are adjusted ANCOVA means, not raw "
        "means. Exact paper-model reproduction is unavailable: PDF pp. 7-8 specifies "
        "five MICE datasets, baseline draft score, age, gender, AI literacy and creative "
        "personality, followed by model-specific Cook's D > 4/n exclusions. The only "
        "posted data file contains the original participant rows, with no imputation "
        "indicator, imputed copies, retained-case flags, imputation equations, seed, "
        "pooling details or analysis syntax. Eight people have both questionnaire "
        "covariates missing, rather than the five people reported on PDF p. 7. "
        "No missing value was imputed or inferred. Original one-based missing-data "
        f"rows: {(df.index[missing] + 1).tolist()}. "
        "One entirely empty trailing SAV row (113) was removed. The remaining 112 "
        "rows contain unique participant identifiers and complete draft outcomes; "
        "the group value labels explicitly map 1=AI-first, 2=AI-follow, 3=AI-parallel, "
        "4=Human-only. All four valid-case arm counts and male counts match PDF p. 4. "
        f"The outcome used for the diagnostic is the stored '{label}' field. "
        "These are participant draft scores, not independent rater observations. "
        f"Unadjusted full-pool treatment/control means are {raw_means[2]:.12g} and "
        f"{raw_means[4]:.12g}, versus printed adjusted means "
        f"{stats['treatment_mean']:.2f} and {stats['control_mean']:.2f}. "
        "The raw treatment mean's rounding match is insufficient: the control mean "
        "and analysis procedure do not match. "
        "As a transparent failure diagnostic only, an OLS ANCOVA using the paper's "
        "listed regressors was fitted on complete cases, with Human-only as reference "
        "and one pass excluding Cook's D > 4/n. Adjusted diagnostic means hold all "
        "five covariates at the fitted sample means. This is not a substitute for MICE. "
        f"Before exclusion: n={before['n']}, arm counts={before['arm_counts']}, "
        f"treatment/control adjusted means={before['adjusted_means'][2]:.12g}/"
        f"{before['adjusted_means'][4]:.12g}. "
        f"This diagnostic excludes {diagnostic['n_excluded']} people at "
        f"D > {diagnostic['cook_cutoff']:.12g}; original one-based rows="
        f"{diagnostic['excluded_source_rows']}. The paper reports {printed_exclusions} "
        "exclusions after imputation. Equal exclusion totals, if any, do not identify "
        "the same sample. "
        f"After exclusion: n={after['n']}, arm counts={after['arm_counts']}, "
        f"treatment/control adjusted means={after['adjusted_means'][2]:.12g}/"
        f"{after['adjusted_means'][4]:.12g}; these do not match at two decimals. "
        "No final paper-model arm counts are printed, and none were inferred from "
        "degrees of freedom or subtracted exclusions. The printed d standardizer and "
        "robust covariance implementation are unspecified. "
        f"Stored overall averages differ from the four subscale arithmetic averages "
        f"at preliminary rows {mismatch_pre} and final rows {mismatch_post}; scores "
        "were used as deposited without repairs. Participant-level SDs, unadjusted "
        "effects, and HC2 SEs were not computed because the required reproduction "
        "gate failed. Every field in 'computed', including se_type, is consequently "
        "null. 'round=all' refers to this between-person final-draft contrast. Fixed "
        "AI-access schedules do not establish a randomized-order within-person "
        "crossover, so no paired or additional first_round result is appropriate."
    )
    # Verify the otherwise purely descriptive male-count statement above.
    male_counts = {int(k): int(v) for k, v in df.groupby("Group")["Gender"].sum().items()}
    assert male_counts == {1: 16, 2: 17, 3: 17, 4: 14}
    return {
        "slug": estimate["slug"],
        "round": "all",
        "reproduced": checks,
        "computed": {key: None for key in COMPUTED_KEYS},
        "notes": notes,
    }


def skip_reason(estimate, df, names_to_labels):
    slug = estimate["slug"]
    if estimate["measure"] is None:
        domain = slug.split("_")[3]
        human_label = DIMENSIONS[domain] + " (Final Draft)"
        ai_label = "Deepseek Evaluation - " + human_label
        assert human_label in df and ai_label in df
        return (
            f"PDF p. 9, section 3.4 prints d={estimate['stats']['paper_effect']['value']:.2f} "
            "but does not identify the evaluator, the d standardizer, model-specific "
            "excluded people/counts, arm means or an unstandardized contrast. "
            f"The SAV contains both '{human_label}' and '{ai_label}'; choosing either "
            "would assume the outcome mapping. The five imputed datasets and "
            "retained-case flags are absent, and eight participants have missing "
            "covariates versus five reported. The adjusted statistic and its analysis "
            "counts cannot be reproduced. No participant-level effect was computed."
        )
    assert all(value is None for value in estimate["stats"].values())
    label = score_label(estimate)
    assert label in df
    source_name = next(key for key, value in names_to_labels.items() if value == label)
    locator = estimate["sources"][0]["locator"]
    treatment_group = next(k for k, v in ARM_LABELS.items() if v == estimate["treatment_arm"])
    return (
        f"{locator} supplies an unlabeled figure only: no printed numerical arm means, "
        "difference, coefficient or pairwise statistic, and no figure-specific "
        "analysis counts. Thus the required outcome-statistic reproduction check "
        f"cannot be performed. SAV variable '{source_name}' ('{label}') maps to this "
        f"outcome; group {treatment_group} is {estimate['treatment_arm']} and group 4 "
        "is Human-only. The valid-case pool counts match the paper, but counts alone "
        "do not reproduce an outcome or establish the figure's retained sample. "
        "No figure values were digitized and no effect or participant-level SD/SE "
        "was computed. Adjusted numerical results from a different specification "
        "are not substituted for this figure-only record."
    )


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    df, labels, counts = read_data()
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        if estimate["stats"]["treatment_mean"] is not None:
            assert estimate["treatment_arm"] == "AI-follow"
            assert estimate["control_arm"] == "Human-only"
            assert estimate["within_person"] is None
            results.append(failed_overall_result(estimate, df, counts))
        else:
            skipped.append({
                "slug": estimate["slug"],
                "reason": skip_reason(estimate, df, labels),
            })
    obj = {
        "cid": "c450",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": [DATA.as_posix()],
        "results": results,
        "skipped": skipped,
    }
    extraction_slugs = {e["slug"] for e in extraction["estimates"]}
    result_slugs = {r["slug"] for r in results}
    skipped_slugs = {s["slug"] for s in skipped}
    assert not result_slugs & skipped_slugs
    assert result_slugs | skipped_slugs == extraction_slugs
    assert len(results) == 2 and len(skipped) == 52 and len(extraction_slugs) == 54
    assert all(not all(c["match"] for c in r["reproduced"]) for r in results)
    assert all(value is None for r in results for value in r["computed"].values())
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({
        "cid": "c450",
        "n_results": len(results),
        "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
