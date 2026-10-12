"""Reproduce the supported c392 estimate from the supplied OSF deposit.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c392/A.py
Only A.json is written. Deposited files are read strictly as data or documentation;
no deposited or remote code is executed. Analyst B's files are never accessed.
The complete 116133-character paper markdown, including Appendices A-L, was
read in consecutive chunks. PDF pages 15, 16, 21, 22, 47, 49, and 52 were
checked using pymupdf. All paths below are absolute.
"""

import sys
sys.dont_write_bytecode = True

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA = Path("D:/projects/ai-skill-atlas/creativity-data/osf-qr5ae/personality-pairing-osf-unpacked/personality-pairing-osf")
SCRIPT = BASE / "analysis/c392/A.py"
OUTPUT = BASE / "analysis/c392/A.json"
EXTRACTION = BASE / "extraction/c392.json"
CSV_NAMES = [
    "participants.csv", "submissions.csv", "ad_ratings.csv",
    "hh_benchmark.csv", "randomization_balance.csv", "process_metrics.csv",
    "field_x.csv", "field_docsend.csv", "chat_labels.csv",
    "manipulation_markers.csv",
]
SUFFIX = "_human_ai_vs_human_human"
UNADJUSTED = "s1_productivity_unadjusted" + SUFFIX


def comparison(statistic, printed, computed, digits=None):
    """Compare at printed precision, without rounding the saved computation."""
    value = float(computed)
    if digits is None:
        value = int(value)
        matched = value == printed
    else:
        matched = (
            math.isfinite(value)
            and format(value, f".{digits}f") == format(printed, f".{digits}f")
        )
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": value,
        "match": bool(matched),
    }


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    assert extraction["cid"] == "c392"
    assert extraction["studies"][0]["assignment_unit"] == "individual"
    estimates = {item["slug"]: item for item in extraction["estimates"]}
    assert all(item["within_person"] is None for item in estimates.values())

    readme_path = DATA / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    assert "Personality Pairing Improves Human-AI Collaboration" in readme
    assert "cannot be re-linked" in readme
    frames = {name: pd.read_csv(DATA / name) for name in CSV_NAMES}
    benchmark = frames["hh_benchmark.csv"]
    participants = frames["participants.csv"]
    submissions = frames["submissions.csv"]
    ratings = frames["ad_ratings.csv"]
    balance = frames["randomization_balance.csv"]

    # The benchmark contains the complete analyzed cohort, including nonproducers.
    assert benchmark["participant_id"].is_unique
    assert benchmark["participant_id"].notna().all()
    assert set(benchmark["treatment"]) == {"human-ai", "human-human"}
    is_treatment = benchmark["treatment"].eq("human-ai")
    ai_ids = set(benchmark.loc[is_treatment, "participant_id"])
    hh_ids = set(benchmark.loc[~is_treatment, "participant_id"])
    assert participants["participant_id"].is_unique
    assert set(participants["participant_id"]) == ai_ids
    assert set(submissions["participant_id"]) <= ai_ids
    assert set(ratings["participant_id"]) <= ai_ids
    assert not set(ratings["participant_id"]) & hh_ids
    assert "participant_id" not in balance.columns
    assert "age" not in benchmark.columns and "sex" not in benchmark.columns
    assert "session_id" not in benchmark.columns and "team_id" not in benchmark.columns

    # Establish which submissions the analysis-ready benchmark counts.
    # The broader creator map includes 271 additional, unrated ad records.
    # All AI benchmark counts equal unique RATED ads, not rows in submissions.csv.
    assert submissions["submission_id"].is_unique
    assert ratings.groupby("submission_id")["participant_id"].nunique().eq(1).all()
    assert set(ratings["submission_id"]) <= set(submissions["submission_id"])
    creator_map = ratings[["submission_id", "participant_id"]].drop_duplicates()
    creator_map = creator_map.merge(
        submissions, on="submission_id", suffixes=("_rating", "_submission"),
        validate="one_to_one",
    )
    assert creator_map["participant_id_rating"].eq(
        creator_map["participant_id_submission"]
    ).all()
    ai_benchmark = benchmark.loc[is_treatment].set_index("participant_id")
    rated_ad_counts = ratings.groupby("participant_id")["submission_id"].nunique()
    assert ai_benchmark["submission_count"].fillna(0).eq(
        rated_ad_counts.reindex(ai_benchmark.index, fill_value=0)
    ).all()

    missing_counts = benchmark["submission_count"].isna()
    assert benchmark.loc[missing_counts, "ad_quality_index"].isna().all()
    observed_counts = benchmark["submission_count"].dropna()
    assert observed_counts.ge(1).all()
    assert observed_counts.mod(1).eq(0).all()
    missing_ai = int((missing_counts & is_treatment).sum())
    missing_hh = int((missing_counts & ~is_treatment).sum())

    # Productivity is a participant's count, so participants absent from the
    # submission aggregation contribute zero; ratings/quality are NOT filled.
    # This preserves all 2,234 analyzed people (36 AI and 153 HH zero counts).
    # As a check, the counts sum to the paper's 11,024 ads and reproduce the
    # unadjusted intercept, coefficient, SEs, and narrative percentage.
    y = benchmark["submission_count"].fillna(0).astype(float)
    x = sm.add_constant(is_treatment.astype(float).rename("human_ai"))
    paper_model = sm.OLS(y, x, missing="raise").fit(cov_type="HC1")
    estimate = estimates[UNADJUSTED]
    reproduction = [
        comparison("n_treatment", estimate["n_treatment"], is_treatment.sum()),
        comparison("n_control", estimate["n_control"], (~is_treatment).sum()),
        comparison("n_total", estimate["n_total"], paper_model.nobs),
        comparison("total_ads_PDF_p16", 11024, y.sum()),
        comparison("regression.intercept_Table_B", 3.850, paper_model.params["const"], 3),
        comparison("regression.intercept_se_Table_B", 0.129, paper_model.bse["const"], 3),
        comparison("regression.coef", estimate["stats"]["regression"]["coef"],
                   paper_model.params["human_ai"], 3),
        comparison("regression.se", estimate["stats"]["regression"]["se"],
                   paper_model.bse["human_ai"], 3),
        comparison("paper_effect.value_percent", estimate["stats"]["paper_effect"]["value"],
                   100.0 * paper_model.params["human_ai"] / paper_model.params["const"], 0),
        {
            "statistic": "p_value",
            "printed": estimate["stats"]["p_value"],
            "computed": float(paper_model.pvalues["human_ai"]),
            "match": bool(paper_model.pvalues["human_ai"] < 0.001),
        },
    ]

    reasons = {}
    reasons["s1_diversity" + SUFFIX] = (
        "The deposit omits ad copy and embeddings. PDF p. 21 requires the original "
        "headline, primary text, and description embedded with text-embedding-3-small, "
        "distances to each arm's centroid, and a text-submitting sample of 2,034 people. "
        "Neither those texts nor the vectors nor the published diversity scores are "
        "available. The exact set-based procedure cannot be reproduced; no substitute "
        "embedding model, participant SD, or diversity effect is computed."
    )
    for outcome, column in [
        ("human_text_quality", "text"),
        ("human_image_quality", "image"),
        ("human_click_likelihood", "click"),
    ]:
        item = estimates["s1_" + outcome + SUFFIX]
        reasons[item["slug"]] = (
            f"Table 2 (PDF p. 22) reports {item['n_units']:,} human-rating observations "
            f"and an adjusted {column} coefficient of {item['stats']['regression']['coef']:.3f}. "
            f"ad_ratings.csv contains only {len(ratings):,} ratings on "
            f"{ratings['submission_id'].nunique():,} ads from "
            f"{ratings['participant_id'].nunique():,} Human-AI creators; there are no "
            "Human-Human ratings. hh_benchmark.csv contains only a combined "
            "ad_quality_index, not the separate text/image/click outcomes. Full-sample "
            "linked age and sex covariates are also unavailable. The published contrast "
            "cannot be reproduced, and the composite is not substituted for this outcome."
        )
    reasons["s1_productivity_adjusted" + SUFFIX] = (
        "The complete participant counts and submission outcome are available, but the "
        "Table 2/Table B model requires linked age, gender, and Big Five covariates. "
        "hh_benchmark.csv lacks age and sex. participants.csv has sex and coarsened "
        "age_band for Human-AI only. randomization_balance.csv has age and sex_male "
        "but no participant key; the deposit README explicitly states these covariates "
        "cannot be re-linked. Row order is not a valid linkage. Consequently the printed "
        "adjusted coefficient 1.954 cannot be reproduced. The separately reproduced "
        "unadjusted coefficient 1.925 is not used to claim reproduction of this model."
    )
    reasons["s1_team_productivity" + SUFFIX] = (
        "Table B (PDF p. 47) analyzes 1,751 teams (Table 1: 1,258 Human-AI and "
        "493 Human-Human). The deposit has no Human-Human team/session membership "
        "or Human-Human submission-to-team mapping; the session identifiers in other "
        "files cover Human-AI only. Participant submission totals alone cannot recover "
        "team outcomes or the allocation of joint team outcomes to participants. The "
        "paper's 976 Human-Human people also do not equal twice its 493 teams. Thus "
        "team counts, the team regression, and participant-level dispersion cannot be "
        "independently reproduced from this deposit. No synthetic pairing or doubling "
        "of individual counts is used."
    )
    for outcome in ["ai_rated_text_quality", "ai_rated_image_quality", "ai_rated_click_likelihood"]:
        item = estimates["s1_" + outcome + SUFFIX]
        reasons[item["slug"]] = (
            f"Table H (PDF p. 52) uses {item['n_units']:,} evaluations by "
            "gpt-4o-mini-2024-07-18. The deposit supplies human rater IDs and repeated "
            "human ratings, but no AI-rating dataset for either arm, and omits the ad "
            "copy and images needed to evaluate the original mockups. The available "
            "human ratings/composite cannot reproduce the printed AI-rating "
            f"coefficient {item['stats']['regression']['coef']:.3f}; no replacement "
            "model evaluations are generated."
        )
    for outcome, element in [
        ("headline_completion", "headline"),
        ("primary_text_completion", "primary text"),
        ("description_completion", "description"),
    ]:
        reasons["s1_" + outcome + SUFFIX] = (
            f"The deposit omits {element} content and completion indicators/rates. "
            "submissions.csv contains only creator and ad identifiers. The paper's "
            "Table E (PDF p. 49) does not specify the rate denominator or coding "
            "procedure, and full-sample demographic covariates cannot be linked. "
            "The completion variable in field_docsend.csv measures subsequent report "
            "viewing, not completion of ad copy. This estimate cannot be reproduced."
        )

    results = []
    if all(check["match"] for check in reproduction):
        # Only after reproduction: requested participant-level summaries and HC2.
        treatment = y.loc[is_treatment]
        control = y.loc[~is_treatment]
        hc2 = sm.OLS(y, x, missing="raise").fit(cov_type="HC2")
        difference = float(treatment.mean() - control.mean())
        difference_se = float(hc2.bse["human_ai"])
        formula_se = math.sqrt(
            float(treatment.var(ddof=1)) / len(treatment)
            + float(control.var(ddof=1)) / len(control)
        )
        assert np.isclose(difference, hc2.params["human_ai"], atol=1e-12, rtol=0)
        assert np.isclose(difference_se, formula_se, atol=1e-12, rtol=0)
        result = {
            "slug": UNADJUSTED,
            "round": "all",
            "reproduced": reproduction,
            "computed": {
                "n_treatment": int(len(treatment)),
                "n_control": int(len(control)),
                "treatment_mean": float(treatment.mean()),
                "treatment_sd": float(treatment.std(ddof=1)),
                "control_mean": float(control.mean()),
                "control_sd": float(control.std(ddof=1)),
                "difference": difference,
                "difference_se": difference_se,
                "se_type": "HC2",
                "n_clusters": None,
            },
            "notes": (
                "Source: Ju and Aral, Collaborating with AI Agents, arXiv "
                "2503.18238v3, February 2026; complete paper and Appendices A-L read. "
                "Printed benchmarks were checked directly in PDF p. 16 (Table 1 and "
                "11,024 ads), p. 22 (50% increase), and p. 47 (Table B, Individual, "
                "Demographics No). The control level printed as Intercept is compared "
                "as an intercept, not relabeled as a printed descriptive mean. "
                "The supplied OSF deposit is titled Personality Pairing Improves "
                "Human-AI Collaboration; its hh_benchmark.csv covers both arms of "
                "this experiment, whereas most other files cover Human-AI only. "
                "Outcome: hh_benchmark.csv submission_count, one row per unique "
                "participant_id; treatment is human-ai and control is human-human. "
                "Retain the complete analyzed cohort, with the paper's exclusions "
                "already reflected in these rows; introduce no additional exclusions. "
                f"Missing submission counts ({missing_ai} Human-AI, {missing_hh} "
                "Human-Human) are zero counts for people absent from the submission "
                "aggregation, not grounds to remove them. Every such row also lacks "
                "ad_quality_index. This zero interpretation is supported by exact "
                "equality between all Human-AI benchmark counts and distinct rated "
                "ads per creator, including zeros, and reproduces the full-sample "
                "intercept, coefficient, standard errors, total ads, and percentage. "
                "Dropping missing counts instead would leave only 2,045 people. "
                "The broader submissions.csv has 7,537 Human-AI ad records, including "
                "271 absent from the 7,266 distinct ads in ad_ratings.csv; use the "
                "benchmark's analysis counts, not that broader creator-map count. "
                "The original filter explaining these 271 records is not included in "
                "the deposit. Preserve the posted attribution of submissions to each "
                "person; do not assign each jointly made ad to both human partners. "
                "Productivity is already a participant total, so no output/rater "
                "averaging is appropriate. Sample SDs use denominator n-1. "
                "Reproduction uses OLS with intercept and arm indicator; HC1 matches "
                "the paper's robust SE at three decimals, although the paper does "
                "not identify a specific HC variant. The requested difference is "
                "the unadjusted Human-AI minus Human-Human mean, with HC2 OLS SE. "
                "HC2 was independently checked against sqrt(s1^2/n1 + s0^2/n0). "
                "Assignment was individual before partner matching (PDF p. 14), "
                "so n_clusters is null. HC2 does not additionally model dependence "
                "between Human-Human partners; their membership identifiers are "
                "unavailable. This is a between-person experiment, so there is no "
                "paired or first_round result."
            ),
        }
        results.append(result)
    else:
        # No participant-level effect is computed if the reproduction gate fails.
        failures = [check for check in reproduction if not check["match"]]
        reasons[UNADJUSTED] = "Failed reproduction; no effect computed: " + json.dumps(failures)

    assert set(estimates) == {result["slug"] for result in results} | set(reasons)
    assert not ({result["slug"] for result in results} & set(reasons))
    skipped = [{"slug": slug, "reason": reasons[slug]} for slug in estimates if slug in reasons]
    obj = {
        "cid": "c392",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": [readme_path.as_posix()] + [(DATA / name).as_posix() for name in CSV_NAMES],
        "results": results,
        "skipped": skipped,
    }
    # Refuse non-finite JSON numbers before writing the only output file.
    json.dumps(obj, ensure_ascii=False, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded == obj
    summary = {
        "cid": "c392",
        "n_results": len(results),
        "n_reproduced": sum(all(check["match"] for check in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
