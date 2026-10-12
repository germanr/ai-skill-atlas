"""Independent analyst-A reproduction audit for c450.

Run: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c450/A.py

The complete main-paper markdown (including references, figures and supplement
list), the complete four-page materials supplement, the reconciled extraction,
and the codebook/extraction rules were read. PDF pages 4-9 and 16-20 and every
supplement page were checked with PyMuPDF text extraction.

The two numerical overall-creativity estimates cannot be reproduced from the
posted, unimputed data. Complete-case ANCOVAs below are explicitly diagnostics,
not substitutes for the paper's unavailable five MICE datasets. They implement
the stated predictors and a single Cook's-distance exclusion pass. No new SD,
unadjusted treatment effect, or HC2 SE is calculated after reproduction fails.
The remaining estimates have no adequate printed numerical reproduction target
or no identified evaluator. All 54 extraction slugs are accounted for.

Only A.json is written by this script. No deposited code or analyst-B file is
read or executed. All source code is ASCII; source variable names are read from
the SPSS dictionary rather than typed through the console.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
import statsmodels.api as sm


ROOT = Path(
    "C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening"
)
SCRIPT = ROOT / "analysis/c450/A.py"
OUTPUT = ROOT / "analysis/c450/A.json"
EXTRACTION = ROOT / "extraction/c450.json"
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DEPOSIT = "researchsquare-rs-8774138"
SAV = Path(
    "D:/projects/ai-skill-atlas/creativity-data/"
    "researchsquare-rs-8774138/b9dc5dfe77302df009deb76e.sav"
)
EXPECTED_HASH = "5de17063af3604e2e8a92c49e8c235776127a9f2339c2d5efcff8c4cc3227ebc"

# PDF p. 4, Section 2.1. These are valid-pool counts, not final-model counts.
ARM_NAMES = {1: "AI-first", 2: "AI-follow", 3: "AI-parallel", 4: "Human-only"}
PRINTED_VALID_COUNTS = {1: 28, 2: 25, 3: 30, 4: 29}
COVARIATES = ["Age", "Gender", "AI I Literacy", "Creative Personality"]
DOMAIN_LABELS = {
    "originality": "Originality",
    "fluency": "Fluency",
    "flexibility": "Flexibility",
    "elaboration": "Elaboration",
}
COMPUTED_FIELDS = [
    "n_treatment", "n_control",
    "treatment_mean", "treatment_sd", "control_mean", "control_sd",
    "difference", "difference_se", "se_type", "n_clusters",
]


def comparison(statistic, printed, computed, decimals=0):
    """Compare at printed precision, never using a relaxed tolerance."""
    match = (
        printed is not None
        and computed is not None
        and format(float(printed), f".{decimals}f")
        == format(float(computed), f".{decimals}f")
    )
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(match),
    }


def counts_by_arm(frame):
    return {
        ARM_NAMES[code]: int((frame["Group"] == code).sum())
        for code in ARM_NAMES
    }


def fit_ancova(frame, baseline, outcome):
    """OLS point estimates for the four-group model in PDF pp. 7-8."""
    design = pd.DataFrame(
        {
            "const": 1.0,
            "AI-first": (frame["Group"] == 1).astype(float),
            "AI-follow": (frame["Group"] == 2).astype(float),
            "AI-parallel": (frame["Group"] == 3).astype(float),
        },
        index=frame.index,
    )
    for column in [baseline] + COVARIATES:
        design[column] = frame[column].astype(float)
    fitted = sm.OLS(frame[outcome].astype(float), design).fit()
    return fitted, design


def diagnose_ancova(data, baseline, outcome):
    """Available-case diagnostic; no imputation values are invented."""
    columns = ["Group", baseline, outcome] + COVARIATES
    complete = data.dropna(subset=columns).copy()
    initial, _ = fit_ancova(complete, baseline, outcome)
    threshold = 4.0 / len(complete)
    cooks = initial.get_influence().cooks_distance[0]
    keep = cooks <= threshold
    retained = complete.loc[keep].copy()
    final, design = fit_ancova(retained, baseline, outcome)

    # Evaluate each arm at the same means of retained participants' covariates.
    # This is a linear model, so it equals averaging predictions after setting
    # every retained participant's group to the relevant arm.
    adjusted = {}
    for arm in ARM_NAMES.values():
        at_means = design.mean().copy()
        for dummy in ["AI-first", "AI-follow", "AI-parallel"]:
            at_means[dummy] = float(arm == dummy)
        adjusted[arm] = float(at_means @ final.params)

    return {
        "n_before": len(complete),
        "n_after": len(retained),
        "counts_before": counts_by_arm(complete),
        "counts_after": counts_by_arm(retained),
        "threshold": threshold,
        "n_excluded": int((~keep).sum()),
        # Original SPSS row numbers, one-based; no participant names exported.
        "excluded_rows": [int(i + 1) for i in complete.index[~keep]],
        "adjusted_means": adjusted,
    }


def outcome_label(estimate):
    stage = (
        "Preliminary Draft"
        if estimate["slug"].startswith("s1_first_draft_")
        else "Final Draft"
    )
    domain = estimate["slug"].split("_draft_", 1)[1].split("_", 1)[0]
    suffix = (
        stage + " Average"
        if domain == "overall"
        else DOMAIN_LABELS[domain] + " (" + stage + ")"
    )
    if estimate["measure"] == "automated_score":
        return "Deepseek Evaluation - " + suffix
    if estimate["measure"] == "human_raters":
        return suffix
    raise ValueError("An evaluator must be identified before selecting a column.")


def main():
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_hash = manifest["deposits"][DEPOSIT]["files"][SAV.name]["sha256"]
    actual_hash = hashlib.sha256(SAV.read_bytes()).hexdigest()
    assert actual_hash == manifest_hash == EXPECTED_HASH

    raw, metadata = pyreadstat.read_sav(str(SAV))
    labels = {
        column: label.strip()
        for column, label in metadata.column_names_to_labels.items()
    }
    assert len(set(labels.values())) == len(labels)
    source_names = {label: column for column, label in labels.items()}
    assert metadata.variable_value_labels[source_names["Group"]] == {
        float(k): v for k, v in ARM_NAMES.items()
    }

    data = raw.rename(columns=labels)
    assert data.shape == (113, 28)
    numeric_columns = [column for column in data if column != "Name"]
    blank = data[numeric_columns].isna().all(axis=1) & data["Name"].eq("")
    assert [int(i + 1) for i in data.index[blank]] == [113]
    data = data.loc[~blank].copy()
    assert data["Name"].nunique() == len(data)
    assert data["Group"].isin(ARM_NAMES).all()
    # The dictionary and unique nonblank records identify one row per person.
    data = data.drop(columns="Name")
    assert len(data) == 112

    estimates = extraction["estimates"]
    assert len(estimates) == 54
    assert all(e["within_person"] is None for e in estimates)
    assert all(e["unit"] == "participant" for e in estimates)
    assert all(e["control_arm"] == "Human-only" for e in estimates)

    missing = data[COVARIATES].isna().any(axis=1)
    missing_rows = [int(i + 1) for i in data.index[missing]]
    assert int(missing.sum()) == 8
    assert data["Creative Personality"].isna().equals(data["AI I Literacy"].isna())

    common_checks = [
        comparison("valid_pool_n_total (PDF p. 4)", 112, len(data))
    ]
    for code, arm in ARM_NAMES.items():
        common_checks.append(comparison(
            "valid_pool_n_" + arm + " (PDF p. 4)",
            PRINTED_VALID_COUNTS[code],
            int((data["Group"] == code).sum()),
        ))
    common_checks.append(comparison(
        "people_with_missing_values (PDF p. 7)", 5, int(missing.sum())
    ))

    # Audit stored overall scores against equal-weight dimension averages.
    # These differences are documented, not silently repaired.
    aggregate_discrepancies = {}
    for prefix in ["", "Deepseek Evaluation - "]:
        for stage in ["Preliminary Draft", "Final Draft"]:
            overall = prefix + stage + " Average"
            dimension_columns = [
                prefix + domain + " (" + stage + ")"
                for domain in ["Fluency", "Flexibility", "Originality", "Elaboration"]
            ]
            discrepancy = (
                data[overall] - data[dimension_columns].mean(axis=1)
            ).abs() > 1e-9
            aggregate_discrepancies[overall] = int(discrepancy.sum())

    results = []
    skipped = []
    for estimate in estimates:
        slug = estimate["slug"]
        stats = estimate["stats"]

        if all(value is None for value in stats.values()):
            label = outcome_label(estimate)
            assert label in data
            assert data[label].notna().all()
            locator = estimate["sources"][0]["locator"]
            reason = (
                f"{locator} is an unlabeled graphical comparison. The extraction "
                "has no printed arm mean, numerical difference/coefficient, or "
                "pairwise numerical statistic for this estimate, and no "
                "figure-specific analysis counts. The corresponding stored "
                f"participant column is '{source_names[label]}' ({label}); "
                "group codes come directly from the SPSS value labels. The "
                "112-person valid pool and its arm counts match PDF p. 4, but "
                "matching those counts alone cannot meet brief rule 3. No "
                "values were digitized from the plots and no new effect or "
                "uncertainty was computed."
            )
            skipped.append({"slug": slug, "reason": reason})
            continue

        if estimate["measure"] is None:
            domain = slug.split("_draft_", 1)[1].split("_", 1)[0]
            human = DOMAIN_LABELS[domain] + " (Final Draft)"
            ai = "Deepseek Evaluation - " + human
            assert human in data and ai in data
            reason = (
                "PDF p. 9, Section 3.4 does not identify the evaluator for this "
                f"numerical subdomain result (printed Cohen's d = "
                f"{stats['paper_effect']['value']:.2f}). The deposit contains "
                f"both '{source_names[human]}' ({human}) and "
                f"'{source_names[ai]}' ({ai}), with no analysis specification "
                "that assigns this result to one. It prints neither arm means "
                "nor a raw difference/coefficient, does not define the d "
                "standardizer, and omits the subdomain exclusion counts and "
                "retained participant IDs. The five imputed datasets are also "
                "absent; the file instead has eight people with missing "
                "covariates. A target outcome, sample, and sufficient numerical "
                "reproduction anchor cannot be confirmed. No candidate was "
                "chosen by searching for a matching d; brief rule 3 prevents "
                "new participant-level effect calculations."
            )
            skipped.append({"slug": slug, "reason": reason})
            continue

        assert "final_draft_overall_" in slug
        assert estimate["treatment_arm"] == "AI-follow"
        outcome = outcome_label(estimate)
        baseline = outcome.replace("Final Draft", "Preliminary Draft")
        diagnostic = diagnose_ancova(data, baseline, outcome)
        printed_excluded = 7 if estimate["measure"] == "human_raters" else 8
        checks = [dict(item) for item in common_checks]
        checks.extend([
            comparison(
                "ANCOVA_n_before_Cook_exclusion "
                "(paper after MICE; diagnostic complete cases)",
                112, diagnostic["n_before"],
            ),
            comparison(
                "Cook_influential_cases_removed "
                "(complete-case diagnostic)", printed_excluded,
                diagnostic["n_excluded"],
            ),
            comparison(
                "treatment_adjusted_mean (complete-case ANCOVA diagnostic)",
                stats["treatment_mean"],
                diagnostic["adjusted_means"]["AI-follow"], 2,
            ),
            comparison(
                "control_adjusted_mean (complete-case ANCOVA diagnostic)",
                stats["control_mean"],
                diagnostic["adjusted_means"]["Human-only"], 2,
            ),
        ])

        raw_treatment = float(data.loc[data["Group"] == 2, outcome].mean())
        raw_control = float(data.loc[data["Group"] == 4, outcome].mean())
        notes = (
            "REPRODUCTION FAILED. This result records a diagnostic attempt; "
            "all requested computed fields are null under brief rule 3. "
            "Null se_type means that no new treatment-effect SE was computed. "
            "Round is 'all' because assignment was between people to four "
            "fixed AI-access schedules, not randomized within-person order; "
            "there is no paired or additional first_round analysis. "
            f"Source variables are '{source_names[outcome]}' ({outcome}) and "
            f"'{source_names[baseline]}' ({baseline}). The SPSS value labels "
            "map 1=AI-first, 2=AI-follow, 3=AI-parallel, 4=Human-only. "
            "The blank SPSS row 113 was removed; the other 112 rows are "
            "distinct people with both draft scores. The counts reproduced "
            "above are explicitly the pre-exclusion valid pool, not final-model "
            "denominators. Eight people lack both Creative Personality and "
            f"AI I Literacy (one-based SPSS rows {missing_rows}); PDF p. 7 "
            "states five people had missing values and five MICE datasets "
            "were generated. No imputation index, imputed dataset, model "
            "inclusion flag, or exclusion list is in this deposit. "
            "Consequently the paper's exact MICE analysis cannot be rerun. "
            "The diagnostic uses complete cases and the specified four-arm "
            "OLS ANCOVA: final score ~ arm + first-draft score + age + gender "
            "+ AI literacy + creative personality, with Human-only as reference. "
            f"It starts with {diagnostic['n_before']} people "
            f"({diagnostic['counts_before']}), applies one exclusion pass "
            f"at Cook's D > 4/n = {diagnostic['threshold']:.10f}, and refits. "
            f"It excludes SPSS rows {diagnostic['excluded_rows']}, retaining "
            f"{diagnostic['n_after']} people ({diagnostic['counts_after']}). "
            "Adjusted means are predictions with all covariates set to their "
            "retained-sample means, identical across arms. These diagnostic "
            "means are compared with the printed means at two decimal places; "
            "they fail. The complete-case procedure is not the reported "
            "multiple-imputation procedure, and its retained counts cannot be "
            "substituted for the unreported paper-specific arm counts. "
            f"For orientation, full-valid-pool unadjusted means are "
            f"{raw_treatment:.12g} (AI-follow) and {raw_control:.12g} "
            "(Human-only); these are not the paper's adjusted estimands and "
            "are not used as successful reproduction evidence. "
            "The paper does not identify the robust covariance estimator or "
            "the Cohen's-d standardizer, so the printed adjusted-mean SEs, "
            "pairwise p-values, and d are not labeled reproduced. "
            f"Stored overall scores differ from the equal-weight average "
            f"of their four component scores for "
            f"{aggregate_discrepancies[baseline]} first drafts and "
            f"{aggregate_discrepancies[outcome]} final drafts. The published "
            "aggregation rule and individual human-rater scores are absent; "
            "the supplied overall-score columns were used without repair. "
            "Full main markdown and materials supplement were read; the "
            "supplement contains task instructions and questionnaire excerpts, "
            "not imputation or analysis specifications. "
            f"Deposit SHA-256 verified against {MANIFEST.as_posix()}: "
            f"{actual_hash}. No across-person diversity outcome is present."
        )
        assert any(not item["match"] for item in checks)
        results.append({
            "slug": slug,
            "round": "all",
            "reproduced": checks,
            "computed": {field: None for field in COMPUTED_FIELDS},
            "notes": notes,
        })

    result_slugs = {item["slug"] for item in results}
    skipped_slugs = {item["slug"] for item in skipped}
    assert not (result_slugs & skipped_slugs)
    assert result_slugs | skipped_slugs == {e["slug"] for e in estimates}
    assert len(results) == 2 and len(skipped) == 52
    assert all(
        all(value is None for value in result["computed"].values())
        for result in results
    )

    obj = {
        "cid": "c450",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": [SAV.as_posix()],
        "results": results,
        "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
        fh.write("\n")
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    summary = {
        "cid": "c450",
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            all(item["match"] for item in result["reproduced"])
            and result["computed"]["difference"] is not None
            for result in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
