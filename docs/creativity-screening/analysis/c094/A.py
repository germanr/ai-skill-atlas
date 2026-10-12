"""Independent analyst A reconstruction for c094.

Run with: python -I -B <absolute path to this script>
Only A.json is written. No deposited program is executed or imported.

The complete paper markdown, including appendices, was read. PDF pages
7, 12, 22 and 25 were checked with pymupdf. The posted Rmd and embedding
programs were inspected as text only. Absolute input paths are below.

Study 1 is an individually randomized, between-person experiment.
The downloaded data_clean.csv already contains the 486 analyzed people.
Use every row, including row_type=page_visit_only; that field is not an
exclusion flag (it includes all 95 vanilla participants and two controls).

Outcome: Average, identical to Idea_quality. Reconstruct it by averaging
Rater1..Rater4 within each participant and rounding that composite to two
decimals, half up, exactly as the posted analysis variable. Each of these
four columns is a rater-level score on the originality/usefulness composite.
The separate originality/usefulness ratings are not present in this CSV.

Reproduction: Table 2 means, SDs and counts; Table 3 five-arm homoskedastic
OLS contrasts with Holm adjustment of four right-tail t-test p-values;
Table 14 tie-corrected Dunn statistics, r=z/sqrt(n1+n2), and Holm-adjusted
TWO-sided p-values over all ten pairs, converted to one-sided AFTER Holm
as done by the posted Rmd. This ordering matters. All checks use printed
precision. Any failed check suppresses the new contrast for that record.

New contrasts: two-arm participant-level OLS with HC2, after reproduction.
The HC2 SE is checked against sqrt(s_t**2/n_t + s_c**2/n_c). SDs use n-1.

Diversity: skip all 18 extracted diversity specifications. CSVs contain
scalar distances, not embedding vectors; the posted vector archive is NPZ,
which is outside this task's permitted data-file types. No NPZ was opened.
Averaging supplied distances is not an independent recreation of the
specified embedding/centroid procedure. No substitute model is used.

A failed reproduction remains in results with every computed field null;
skipped lists estimates for which the analysis was not attempted. Thus
the two lists partition all 26 extracted slugs. n_reproduced in the console
summary counts records for which every reproduction check passes.
"""

import itertools
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

WORKSPACE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(
    r"D:/projects/ai-skill-atlas/creativity-data/"
    r"github-SM2982-replication-creativity-CHI2026/"
    r"replication-creativity-CHI2026-unpacked/"
    r"replication-creativity-CHI2026-HEAD"
)
STUDY1 = DEPOSIT / "analysis/Study1"
CLEAN = STUDY1 / "data/data_clean.csv"
GROUP_SUMMARY = STUDY1 / "data/data_group_summary.csv"
EXTRACTION = WORKSPACE / "extraction/c094.json"
SCRIPT = WORKSPACE / "analysis/c094/A.py"
OUTPUT = WORKSPACE / "analysis/c094/A.json"
PAPER_STEM = (
    r"C:/Dropbox/Research/ai-lab/literature/creativity/"
    r"Maier Schneider Feuerriegel (2026) - Partnering with Generative AI"
)

# Includes source documents and author code inspected as text by analyst A.
# Neither B.py nor B's results are read or enumerated.
READ_FILES = [
    CLEAN,
    GROUP_SUMMARY,
    STUDY1 / "analysisR/Analysis_Study.Rmd",
    STUDY1 / "embeddings/refined_idea_similarity_analysis.py",
    STUDY1 / "embeddings/improved_embedding_storage.py",
    EXTRACTION,
    WORKSPACE / "retrieval.json",
    WORKSPACE.parent / "creativity-codebook.md",
    WORKSPACE / "extraction-spec.md",
    Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json"),
    Path(PAPER_STEM + ".md"),
    Path(PAPER_STEM + ".pdf"),
]
ORDER = ["feedback", "suggestion", "improvement", "vanilla", "control"]
ARM_MAP = {
    "Question-mode (Q)": "feedback",
    "Suggestion-mode (S)": "suggestion",
    "Model-led (M)": "improvement",
    "Vanilla (V)": "vanilla",
    "Control (C)": "control",
}
COMPUTED_KEYS = [
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se",
    "se_type", "n_clusters",
]


def holm(values):
    """Holm step-down adjusted p-values, preserving original order."""
    p = np.asarray(values, dtype=float)
    order = np.argsort(p, kind="stable")
    adjusted_sorted = np.minimum(
        1.0, np.maximum.accumulate((len(p) - np.arange(len(p))) * p[order])
    )
    adjusted = np.empty_like(p)
    adjusted[order] = adjusted_sorted
    return adjusted


def reproduction_check(statistic, printed, computed, places):
    value = int(computed) if places == 0 else float(computed)
    if isinstance(printed, str) and printed.startswith("<"):
        match = value < float(printed[1:])
    elif printed is None:
        match = False
    else:
        quantum = Decimal(1).scaleb(-places)
        rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
        match = rounded == Decimal(str(printed))
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": value,
        "match": bool(match),
    }


def hc2_contrast(participants, treatment, control):
    subset = participants.loc[participants.bot_type.isin([treatment, control])]
    indicator = (subset.bot_type == treatment).to_numpy(dtype=float)
    y = subset.quality.to_numpy(dtype=float)
    model = sm.OLS(y, sm.add_constant(indicator)).fit(cov_type="HC2")
    t = subset.loc[subset.bot_type == treatment, "quality"].to_numpy()
    c = subset.loc[subset.bot_type == control, "quality"].to_numpy()
    diff = float(t.mean() - c.mean())
    se = float(model.bse[1])
    analytic_se = math.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c))
    assert math.isclose(float(model.params[1]), diff, abs_tol=1e-12)
    assert math.isclose(se, analytic_se, abs_tol=1e-12)
    return {
        "n_treatment": int(len(t)),
        "n_control": int(len(c)),
        "treatment_mean": float(t.mean()),
        "treatment_sd": float(t.std(ddof=1)),
        "control_mean": float(c.mean()),
        "control_sd": float(c.std(ddof=1)),
        "difference": diff,
        "difference_se": se,
        "se_type": "HC2",
        "n_clusters": None,
    }


def main():
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    assert extraction["cid"] == "c094"
    assert extraction["studies"][0]["assignment_unit"] == "individual"
    data = pd.read_csv(CLEAN)
    deposited_summary = pd.read_csv(GROUP_SUMMARY).set_index("bot_type")
    assert len(data) == extraction["studies"][0]["n_analyzed"] == 486
    assert data.participant_id.notna().all() and data.participant_id.is_unique
    assert set(data.bot_type) == set(ORDER)
    assert data.questionnaire_completed.eq("Yes").all()
    assert data.ac1.eq(2).all() and data.ac2.eq(5).all()
    assert data.honesty_question_answer.eq("no").all()
    assert data.refined_idea.notna().all()
    raters = data[["Rater1", "Rater2", "Rater3", "Rater4"]]
    assert raters.notna().all().all()
    assert ((raters >= 1) & (raters <= 7)).all().all()

    # Recreate the authors' participant-level composite, not rating-level rows.
    quality = np.array([
        float((sum(Decimal(str(v)) for v in row) / Decimal(4)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ))
        for row in raters.itertuples(index=False, name=None)
    ])
    assert np.array_equal(quality, data.Average.to_numpy())
    assert np.array_equal(quality, data.Idea_quality.to_numpy())
    participants = data[["participant_id", "bot_type"]].copy()
    participants["quality"] = quality
    # One row and one final scored output per person; all four ratings have
    # already been aggregated before any between-person SD or model is fitted.
    grouped = participants.groupby("bot_type").quality
    counts = grouped.size().to_dict()
    means = grouped.mean().to_dict()
    sds = grouped.std(ddof=1).to_dict()
    for arm in extraction["studies"][0]["arms"]:
        code = ARM_MAP[arm["name"]]
        assert counts[code] == arm["n_analyzed"]
    for code in ORDER:
        assert counts[code] == int(deposited_summary.loc[code, "Count_Observations"])
        assert math.isclose(means[code], deposited_summary.loc[code, "IdeaQuality_mean"], abs_tol=1e-12)
        assert math.isclose(sds[code], deposited_summary.loc[code, "IdeaQuality_sd"], abs_tol=1e-12)

    # Reproduce the five-arm model used for the paper's Table 3 comparisons.
    x = np.column_stack([(participants.bot_type == code).astype(float) for code in ORDER])
    paper_model = sm.OLS(participants.quality.to_numpy(), x).fit()
    df = int(paper_model.df_resid)
    assert df == 481
    sigma = math.sqrt(float(paper_model.mse_resid))
    main_stats = {}
    for code in ORDER[:-1]:
        contrast = means[code] - means["control"]
        tt = contrast / (sigma * math.sqrt(1 / counts[code] + 1 / counts["control"]))
        main_stats[code] = {"t": tt, "df": df, "d": contrast / sigma}
    adjusted_main = holm([stats.t.sf(main_stats[code]["t"], df) for code in ORDER[:-1]])
    for code, p in zip(ORDER[:-1], adjusted_main):
        main_stats[code]["p"] = float(p)

    # Independent implementation of Dunn's statistic with tied-rank correction.
    ranks = stats.rankdata(participants.quality, method="average")
    mean_ranks = participants.assign(rank=ranks).groupby("bot_type")["rank"].mean().to_dict()
    n = len(participants)
    _, ties = np.unique(quality, return_counts=True)
    rank_variance = n * (n + 1) / 12 - float(np.sum(ties**3 - ties)) / (12 * (n - 1))
    pairs = list(itertools.combinations(ORDER, 2))
    z_values = [
        (mean_ranks[a] - mean_ranks[b]) / math.sqrt(rank_variance * (1 / counts[a] + 1 / counts[b]))
        for a, b in pairs
    ]
    adjusted_two_sided = holm([2 * stats.norm.sf(abs(z)) for z in z_values])
    dunn_stats = {}
    for (a, b), z, p2_adj in zip(pairs, z_values, adjusted_two_sided):
        if b == "control":
            dunn_stats[a] = {
                "z": float(z),
                "r": float(z / math.sqrt(counts[a] + counts[b])),
                "p": float(p2_adj / 2 if z > 0 else 1 - p2_adj / 2),
                "p_unadjusted": float(stats.norm.sf(z)),
            }
    printed_dunn_unadjusted = {
        "feedback": 0.013, "suggestion": 0.143,
        "improvement": "<.001", "vanilla": 0.415,
    }

    common_notes = (
        "Study 1, individual randomization, final idea, round all; no randomized-order "
        "crossover or first-round record. Use all 486 rows of data_clean.csv with unique "
        "participant_id, including page_visit_only rows. The file is already the final "
        "analyzed sample: the paper (PDF p. 7, section 4.3) reports 16 exclusions from 502 "
        "recruited (10 attention checks, 2 unauthorized AI use, 2 nonsense, 1 duplicate, "
        "1 incomplete). The excluded raw rows are not supplied here, so their individual "
        "exclusion decisions cannot be independently audited. No further exclusions. "
        "bot_type mapping: feedback=Question-mode, suggestion=Suggestion-mode, "
        "improvement=Model-led, vanilla=Vanilla, control=Control. "
        "Average and Idea_quality are identical and equal mean(Rater1..Rater4) rounded "
        "half up to two decimals for every participant. That posted outcome is recreated "
        "and used consistently; without this participant-level rounding the vanilla "
        "mean is 2.6934210526, whereas the posted outcome mean is 2.6961052632 and "
        "reproduces Table 2's 2.70. One final idea per participant; four expert ratings "
        "are averaged within that participant before computing any arm statistics. "
        "Counts, means and SDs are checked against Table 2 (PDF p. 12), and against "
        "data_group_summary.csv. Sources for the rating rule: PDF pp. 7 and 22. "
    )
    results = []
    skipped = []
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        if estimate["construct"] == "diversity":
            if "_change_" in slug:
                procedure = (
                    "The change model needs both idea_div_condition (initial leave-one-out "
                    "centroid distance) and refined_div_to_initial_centroid (final distance "
                    "to the initial-condition centroid), recomputed from the original vectors. "
                    "These are fixed-order pre/post observations, not a randomized crossover. "
                )
            else:
                procedure = (
                    "This specification requires refined_div_condition, the final idea's "
                    "cosine distance to the leave-one-out centroid of other final ideas "
                    "in the same condition, using text-embedding-3-large. "
                )
                if slug.endswith("_logit"):
                    procedure += "The logit transformation also requires that exact underlying distance. "
                elif slug.endswith("_dunn"):
                    procedure += "Its Dunn test also requires that exact underlying distance. "
            skipped.append({
                "slug": slug,
                "reason": procedure + (
                    "The allowed CSV files supply texts and precomputed scalar diversity "
                    "scores, but no embedding vectors. The repository stores vectors in "
                    "analysis/Study1/data/ideas_with_diversity_scores_embeddings.npz; NPZ "
                    "is outside the brief's permitted data-file formats and was not opened. "
                    "Exact recreation of the embedding/centroid procedure is therefore "
                    "not established. Per rule 5, do not treat the stored set-dependent "
                    "distances as independently observed participant-level outcomes or "
                    "report HC2 contrasts from them. No substitute embeddings were used."
                ),
            })
            continue

        assert slug.startswith("s1_quality_")
        treatment = ARM_MAP[estimate["treatment_arm"]]
        control = ARM_MAP[estimate["control_arm"]]
        printed = estimate["stats"]
        checks = [
            reproduction_check("n_treatment", estimate["n_treatment"], counts[treatment], 0),
            reproduction_check("n_control", estimate["n_control"], counts[control], 0),
            reproduction_check("treatment_mean", printed["treatment_mean"], means[treatment], 2),
            reproduction_check("treatment_sd", printed["treatment_sd"], sds[treatment], 2),
            reproduction_check("control_mean", printed["control_mean"], means[control], 2),
            reproduction_check("control_sd", printed["control_sd"], sds[control], 2),
        ]
        notes = common_notes
        if slug.endswith("_dunn"):
            ds = dunn_stats[treatment]
            checks.extend([
                reproduction_check("test_z", printed["test"]["value"], ds["z"], 2),
                reproduction_check("p_value", printed["p_value"], ds["p"], 3),
                reproduction_check("unadjusted_p_value", printed_dunn_unadjusted[treatment], ds["p_unadjusted"], 3),
                reproduction_check("paper_effect_r", printed["paper_effect"]["value"], ds["r"], 2),
            ])
            notes += (
                "Table 14 (PDF p. 25) is checked with tie-corrected Dunn ranks over all "
                "five arms, Holm adjustment over all 10 two-sided pairwise p-values, then "
                "conversion to one-sided p-values. r=z/sqrt(n_treatment+n_control), as in "
                "Analysis_Study.Rmd lines 1545-1560. This is a robustness specification "
                "of the same sample and outcome as its Table 3 counterpart, not an "
                "additional independent effect. "
            )
        else:
            ms = main_stats[treatment]
            checks.extend([
                reproduction_check("test_t", printed["test"]["value"], ms["t"], 2),
                reproduction_check("test_df", printed["test"]["df"], ms["df"], 0),
                reproduction_check("p_value", printed["p_value"], ms["p"], 3),
                reproduction_check("paper_effect_d", printed["paper_effect"]["value"], ms["d"], 2),
            ])
            notes += (
                "Table 3 (PDF p. 12) is checked using the five-arm OLS residual SD, "
                "df=481, and Holm adjustment of four right-tailed t-tests, following "
                "Analysis_Study.Rmd lines 469-512. The posted code defines the paper's "
                "d denominator as the five-arm residual SD. "
            )

        # Enforce reproduction before computing any new contrast for this record.
        failures = [check for check in checks if not check["match"]]
        if failures:
            computed = dict.fromkeys(COMPUTED_KEYS)
            details = "; ".join(
                f"{check['statistic']}: printed {check['printed']}, computed {check['computed']:.12g}"
                for check in failures
            )
            notes += (
                "REPRODUCTION FAILED: " + details + ". All other checks passed. "
                "The model-led Dunn r=0.274665132744 rounds to 0.27 at two decimals, "
                "not the printed 0.28; no alternative denominator or double rounding "
                "is assumed. In accordance with rule 3, every computed field is null "
                "and no new contrast is supplied for this estimate. Null se_type means "
                "no SE was computed. This attempted estimate is in results, not skipped."
            )
        else:
            computed = hc2_contrast(participants, treatment, control)
            notes += (
                "All listed paper statistics reproduce at printed precision. The new "
                "raw difference is treatment minus control. Its SE is from two-arm "
                "OLS(quality ~ intercept + treatment) with HC2, using one row per "
                "randomized person; it is also verified as sqrt(s_t^2/n_t+s_c^2/n_c). "
                "Reported arm SDs use n-1. No assignment clusters."
            )
        results.append({
            "slug": slug,
            "round": "all",
            "reproduced": checks,
            "computed": computed,
            "notes": notes,
        })

    expected = {e["slug"] for e in extraction["estimates"]}
    result_slugs = {r["slug"] for r in results}
    skipped_slugs = {s["slug"] for s in skipped}
    assert result_slugs.isdisjoint(skipped_slugs)
    assert result_slugs | skipped_slugs == expected
    assert len(results) + len(skipped) == len(expected) == 26
    for result in results:
        passed = all(item["match"] for item in result["reproduced"])
        if not passed:
            assert all(v is None for v in result["computed"].values())
        else:
            assert result["computed"]["se_type"] == "HC2"
            assert result["computed"]["difference_se"] > 0

    obj = {
        "cid": "c094",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in READ_FILES],
        "results": results,
        "skipped": skipped,
    }
    # allow_nan=False prevents non-JSON NaN/Infinity in numeric results.
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with OUTPUT.open(encoding="utf-8") as fh:
        reparsed = json.load(fh)
    assert reparsed == obj
    print(json.dumps({
        "cid": "c094",
        "n_results": len(results),
        "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
