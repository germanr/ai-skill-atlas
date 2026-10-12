"""Independent analyst B reanalysis of c392.

Run with: python -I -B B.py
The only output is the absolute B.json path below. No deposited code is run.
The complete 116,133-character paper conversion, including Appendices A-L,
was reviewed. Printed reproduction targets were checked using PyMuPDF on
PDF pages 14-16, 19, 21-22, 46-49, 51-52; Table B was also recovered using
text-based find_tables. The paper is arXiv:2503.18238v3, February 2026.
"""

import sys

sys.dont_write_bytecode = True

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


WORKSPACE = Path(
    "C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening"
)
DATA_ROOT = Path(
    "D:/projects/ai-skill-atlas/creativity-data/osf-qr5ae/"
    "personality-pairing-osf-unpacked/personality-pairing-osf"
)
SCRIPT = WORKSPACE / "analysis/c392/B.py"
OUTPUT = WORKSPACE / "analysis/c392/B.json"
EXTRACTION = WORKSPACE / "extraction/c392.json"
TARGET = "s1_productivity_unadjusted_human_ai_vs_human_human"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rounded_check(statistic, printed, computed, digits):
    """Compare at the precision actually printed, not an arbitrary tolerance."""
    computed = float(computed)
    if digits == 0 and computed.is_integer():
        computed = int(computed)
    require(math.isfinite(computed), "Nonfinite reproduction statistic")
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": format(computed, f".{digits}f") == format(printed, f".{digits}f"),
    }


def main():
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    estimates = {row["slug"]: row for row in extraction["estimates"]}
    study = extraction["studies"][0]
    require(study["assignment_unit"] == "individual", "Assignment unit changed")
    require(all(row["within_person"] is None for row in estimates.values()),
            "Unexpected within-person estimate")

    # Read the posted data as data, never as executable material. Inspect all
    # CSV schemas so the reasons for unavailable estimates cover the deposit.
    csv_paths = sorted(DATA_ROOT.glob("*.csv"))
    data = {p.name: pd.read_csv(p) for p in csv_paths}
    readme_path = DATA_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    require("no ad copy or image URLs" in readme, "Recheck deposit documentation")
    require("cannot be re-linked" in readme, "Recheck balance-file documentation")
    require(set(data) == {
        "ad_ratings.csv", "chat_labels.csv", "field_docsend.csv", "field_x.csv",
        "hh_benchmark.csv", "manipulation_markers.csv", "participants.csv",
        "process_metrics.csv", "randomization_balance.csv", "submissions.csv",
    }, "Deposit file inventory changed; review newly available inputs")

    benchmark = data["hh_benchmark.csv"]
    ratings = data["ad_ratings.csv"]
    submissions = data["submissions.csv"]
    participants = data["participants.csv"]
    balance = data["randomization_balance.csv"]
    require(benchmark.participant_id.notna().all(), "Missing participant identifier")
    require(benchmark.participant_id.is_unique, "Benchmark is not one row per person")
    require(set(benchmark.treatment) == {"human-ai", "human-human"}, "Unexpected arms")
    require(benchmark.submission_count.dropna().ge(0).all(), "Negative count")
    require((benchmark.submission_count.dropna() % 1 == 0).all(), "Noninteger count")
    require(benchmark.submission_count.isna().equals(benchmark.ad_quality_index.isna()),
            "Missing-count pattern differs from the posted benchmark")

    ai_ids = set(benchmark.loc[benchmark.treatment == "human-ai", "participant_id"])
    hh_ids = set(benchmark.loc[benchmark.treatment == "human-human", "participant_id"])
    require(set(participants.participant_id) == ai_ids, "Participant-file scope changed")
    require(set(ratings.participant_id).issubset(ai_ids), "Recheck ratings-file coverage")
    require(set(submissions.participant_id).issubset(ai_ids), "Recheck submissions coverage")
    require(submissions.submission_id.is_unique, "Duplicate submission identifier")
    require("participant_id" not in balance.columns, "Balance data now have join keys")
    require("age" not in benchmark and "sex" not in benchmark,
            "Recheck availability of adjusted-model covariates")
    require("session_id" not in benchmark and "team_id" not in benchmark,
            "Recheck availability of human-human team identifiers")

    rated_ads = ratings[["submission_id", "participant_id"]].drop_duplicates()
    require(rated_ads.submission_id.is_unique, "Rated ad has multiple creator mappings")
    mapping = rated_ads.merge(
        submissions, on="submission_id", how="left", validate="one_to_one",
        suffixes=("_rating", "_submission")
    )
    require(mapping.participant_id_rating.equals(mapping.participant_id_submission),
            "Rated-ad creator mapping disagrees with submissions.csv")
    rated_counts = rated_ads.groupby("participant_id").size()
    ai_benchmark = benchmark[benchmark.treatment == "human-ai"].set_index("participant_id")
    require(np.array_equal(
        ai_benchmark.submission_count.fillna(0).to_numpy(),
        rated_counts.reindex(ai_benchmark.index, fill_value=0).to_numpy(),
    ), "AI benchmark counts differ from counts of distinct rated ads")
    require(set(ai_benchmark.index[ai_benchmark.submission_count.isna()]).isdisjoint(
        set(submissions.participant_id)
    ), "A missing AI count has posted submissions")
    for name in ["chat_labels.csv", "manipulation_markers.csv", "process_metrics.csv",
                 "field_x.csv", "field_docsend.csv"]:
        require(set(data[name].participant_id).issubset(ai_ids),
                f"Recheck full-sample coverage in {name}")

    # The paper's productivity analysis includes every retained participant.
    # Blank count fields therefore represent zero counted submissions in that
    # analysis. This reconstruction is checked against the printed intercept,
    # coefficient, both SEs, sample sizes, percent increase, and corpus count.
    # For AI participants it is also independently checked against both posted
    # creator maps above. Do not replace this outcome with raw submissions.csv:
    # that file has 7,537 AI ads, versus 7,266 in the benchmark/rating universe.
    outcome = benchmark.submission_count.fillna(0).astype(float)
    treatment = (benchmark.treatment == "human-ai").astype(float).rename("human_ai")
    design = sm.add_constant(treatment, has_constant="add")
    replication = sm.OLS(outcome, design).fit(cov_type="HC2")
    estimate = estimates[TARGET]
    paper_regression = estimate["stats"]["regression"]
    nt = int(treatment.sum())
    nc = int(len(treatment) - nt)
    checks = [
        rounded_check("n_treatment", estimate["n_treatment"], nt, 0),
        rounded_check("n_control", estimate["n_control"], nc, 0),
        rounded_check("n_total", estimate["n_total"], replication.nobs, 0),
        rounded_check("regression.coef", paper_regression["coef"],
                      replication.params["human_ai"], 3),
        rounded_check("regression.se", paper_regression["se"],
                      replication.bse["human_ai"], 3),
        rounded_check("regression.intercept", 3.850, replication.params["const"], 3),
        rounded_check("regression.intercept_se", 0.129, replication.bse["const"], 3),
        rounded_check("paper_effect.value_percent_increase",
                      estimate["stats"]["paper_effect"]["value"],
                      100 * replication.params["human_ai"] / replication.params["const"], 0),
        rounded_check("total_counted_ads", 11024, outcome.sum(), 0),
        {
            "statistic": "p_value",
            "printed": estimate["stats"]["p_value"],
            "computed": float(replication.pvalues["human_ai"]),
            "match": bool(replication.pvalues["human_ai"] < 0.001),
        },
    ]

    computed = {key: None for key in [
        "n_treatment", "n_control", "treatment_mean", "treatment_sd", "control_mean",
        "control_sd", "difference", "difference_se", "se_type", "n_clusters",
    ]}
    # Only after all reproduction checks pass compute the requested summaries.
    if all(check["match"] for check in checks):
        treated = outcome[treatment == 1]
        control = outcome[treatment == 0]
        difference = float(treated.mean() - control.mean())
        difference_se = float(replication.bse["human_ai"])
        require(math.isclose(difference, replication.params["human_ai"], abs_tol=1e-12),
                "OLS coefficient disagrees with the difference of means")
        # An independent algebraic verification of HC2 for an intercept and
        # binary arm indicator: sample variance / arm n, summed across arms.
        expected_se = math.sqrt(treated.var(ddof=1) / nt + control.var(ddof=1) / nc)
        require(math.isclose(difference_se, expected_se, abs_tol=1e-12),
                "HC2 sandwich disagrees with its two-group variance formula")
        computed = {
            "n_treatment": nt,
            "n_control": nc,
            "treatment_mean": float(treated.mean()),
            "treatment_sd": float(treated.std(ddof=1)),
            "control_mean": float(control.mean()),
            "control_sd": float(control.std(ddof=1)),
            "difference": difference,
            "difference_se": difference_se,
            "se_type": "HC2",
            "n_clusters": None,
        }

    blank_treatment = int(ai_benchmark.submission_count.isna().sum())
    blank_control = int(benchmark.loc[benchmark.treatment == "human-human", "submission_count"].isna().sum())
    notes = (
        "Reproduces Table B, PDF p. 47, first Individual column (Demographics No): "
        "coefficient 1.925, SE 0.197, intercept 3.850, intercept SE 0.129, N=2234. "
        "Arm counts are from Table 1, PDF p. 16; 11,024 ads are reported on p. 16; "
        "the 50% increase is reported on p. 22. The paper specifies only robust SEs; "
        "HC2 reproduces both printed SEs at three decimals. "
        "Use hh_benchmark.csv, one row per retained randomized participant, with no "
        "additional exclusions. Outcome is the supplied submission_count. "
        f"Blank counts ({blank_treatment} Human-AI and {blank_control} Human-Human) "
        "are reconstructed as zero counted submissions to implement the paper's "
        "full-cohort count analysis. This treatment of blanks reproduces every "
        "listed numerical check. Dropping blanks would give only 2,045 participants "
        "and fails the paper's sample definition. For the AI arm, all blank-count "
        "participants have no submissions in the posted creator map, and every "
        "benchmark count equals the number of distinct rated ads for that participant. "
        "The benchmark totals are 7,266 Human-AI and 3,758 Human-Human counted ads. "
        "The raw submissions.csv contains 7,537 Human-AI ads, including 271 absent "
        "from the ratings; substituting those raw counts would not reproduce Table B. "
        "Human-human attribution follows the supplied participant counts; no team "
        "totals or partner allocation are inferred. Each count is already a single "
        "participant-level fluency outcome. SDs use denominator n-1. Difference is "
        "the treatment mean minus the control mean; difference_se is from OLS of "
        "that participant outcome on an intercept and the Human-AI indicator with "
        "HC2 covariance. It is independently checked against sqrt(s_t^2/n_t+s_c^2/n_c). "
        "Randomization preceded team formation (PDF p. 14), so the requested "
        "individual-level HC2 is used. Shared human-human teamwork may induce "
        "dependence; the release does not identify human-human teams. This is a "
        "between-person experiment: round=all, with no first-round contrast. "
        "The deposit README is titled Personality Pairing Improves Human-AI "
        "Collaboration and identifies hh_benchmark.csv as the both-arm benchmark. "
        "The linked GitHub API and the OSF API were attempted read-only via urllib "
        "with User-Agent atlas-screening/0.1; both failed with socket error "
        "WinError 10013. No external code was obtained or executed."
    )
    failed = [check["statistic"] for check in checks if not check["match"]]
    if failed:
        notes += " REPRODUCTION FAILED: " + ", ".join(failed) + "; all requested computed fields are null."

    human_reason = (
        f"Table 2 (PDF p. 22; repeated in Table G, p. 51) uses 45,803 ratings. "
        f"The release contains {len(ratings):,} human ratings of "
        f"{rated_ads.submission_id.nunique():,} ads from "
        f"{ratings.participant_id.nunique():,} Human-AI creators only, with no "
        "Human-Human component ratings. hh_benchmark.csv supplies a combined "
        "ad_quality_index, not separate text/image/click scores. The linked age "
        "and sex covariates for the full sample are also unavailable. The printed "
        "analysis sample and adjusted coefficient therefore cannot be reproduced; "
        "no participant-level contrast is computed."
    )
    ai_reason = (
        "Table H (PDF p. 52) analyzes 11,024 ads evaluated by "
        "gpt-4o-mini-2024-07-18. The deposit has no file of those AI evaluations. "
        "ad_ratings.csv contains repeated human-rater evaluations of Human-AI ads; "
        "it is not the paper's AI-rating outcome. Neither the combined benchmark "
        "quality index nor the human field-rating columns can recover the three "
        "AI-rated dimensions. The output sample and adjusted coefficient cannot "
        "be reproduced; no participant-level contrast is computed."
    )
    completion_reason = (
        "Table E (PDF p. 49) reports participant-level ad-copy completion for "
        "2,234 people. The release omits ad copy, per-element completion "
        "indicators, and participant completion rates. submissions.csv supplies "
        "only submission_id and participant_id, and only for Human-AI ads; "
        "hh_benchmark.csv has no completion variables. The paper also leaves "
        "the completion numerator/denominator and coding procedure unspecified. "
        "The printed adjusted coefficient cannot be reproduced, so no contrast "
        "is computed."
    )
    reasons = {
        "s1_diversity_human_ai_vs_human_human": (
            "The procedure on PDF p. 21 requires the original ad-copy texts and "
            "text-embedding-3-small embeddings to construct each arm's centroid "
            "and cosine distances (printed N=2034, coefficient -0.094). The "
            "release explicitly omits ad copy and contains no embeddings, "
            "centroids, or diversity scores. The same text sets and embedding "
            "procedure cannot be reconstructed. Skipped under the set-diversity "
            "rule; no replacement measure or participant-level SD is computed."
        ),
        "s1_productivity_adjusted_human_ai_vs_human_human": (
            "The adjusted productivity model in Table 2 (PDF p. 22) and Table B "
            "(p. 47) requires age, gender, and Big Five covariates (Equation 1, "
            "pp. 19-20). hh_benchmark.csv has counts and Big Five scores but no "
            "age or sex. participants.csv has only the Human-AI participants, "
            "with coarsened age bands. randomization_balance.csv contains full "
            "sample age/sex but no participant key; its README explicitly says "
            "these covariates cannot be re-linked. Row order is not a join key. "
            "Thus the adjusted coefficient 1.954 (SE 0.197, N=2234) cannot be "
            "reproduced. The separately reproduced unadjusted result is not "
            "substituted for this specification."
        ),
        "s1_team_productivity_human_ai_vs_human_human": (
            "Table B (PDF p. 47) requires 1,751 team observations and reports "
            "coefficient -1.847 (SE 0.315). hh_benchmark.csv has participant "
            "counts but no team/session identifiers, and the posted submissions "
            "and session-linked files contain only Human-AI participants. There "
            "is no Human-Human team membership or submission map with which to "
            "reconstruct team totals, the team regression, or corresponding "
            "person-level outcomes. The printed 976 Human-Human people and "
            "493 teams do not themselves establish membership. No arithmetic "
            "pairing, deduplication by equal counts, or team-to-person conversion "
            "is inferred."
        ),
    }
    for component in ["text_quality", "image_quality", "click_likelihood"]:
        reasons[f"s1_human_{component}_human_ai_vs_human_human"] = human_reason
        reasons[f"s1_ai_rated_{component}_human_ai_vs_human_human"] = ai_reason
    for component in ["headline", "primary_text", "description"]:
        reasons[f"s1_{component}_completion_human_ai_vs_human_human"] = completion_reason

    require(set(reasons) | {TARGET} == set(estimates), "An extracted estimate is unaccounted for")
    skipped = [
        {"slug": row["slug"], "reason": reasons[row["slug"]]}
        for row in extraction["estimates"] if row["slug"] != TARGET
    ]
    payload = {
        "cid": "c392",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in csv_paths] + [readme_path.as_posix()],
        "results": [{
            "slug": TARGET,
            "round": "all",
            "reproduced": checks,
            "computed": computed,
            "notes": notes,
        }],
        "skipped": skipped,
    }
    # Validate all numeric fields before serializing with the requested format.
    json.dumps(payload, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    require(parsed == payload, "Written JSON failed round-trip validation")
    summary = {
        "cid": "c392",
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            all(check["match"] for check in row["reproduced"])
            and row["computed"]["difference"] is not None
            for row in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
