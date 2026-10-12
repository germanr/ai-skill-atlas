"""Independent analyst A reanalysis of c006.

Run with python -I and this file's absolute path. The only output is A.json.
No deposited program is executed or imported. The authors' Stata/Python
sources were read as text to establish exclusions, variable mappings, model
specifications, and the limitations of the stored diversity scores.

The complete article and supplementary markdown were read in consecutive
chunks. Numerical sources were checked with PyMuPDF: article pp. 3, 5, 7-8;
supplement pp. 5-7, 10, 12, 14 (Tables S1, S3, S4, S6, S11, S12, S13).
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = ROOT / "analysis/c006/A.py"
OUTPUT = ROOT / "analysis/c006/A.json"
EXTRACTION = ROOT / "extraction/c006.json"
DEPOSIT = Path(
    r"D:/projects/ai-skill-atlas/creativity-data/zenodo-11654403/"
    r"GenAI_creativity_scripts-unpacked/GenAI_creativity_scripts"
)
WRITERS = DEPOSIT / "already_processed_data/creators.dta"
EVALUATORS = DEPOSIT / "already_processed_data/evaluators_stories.dta"
RAW_WRITERS = DEPOSIT / "raw_data/writers-2023-06-28.csv"
RAW_EVALUATORS = DEPOSIT / "raw_data/evaluators-2023-07-06.csv"

ITEMS = [
    "novel", "original", "rare", "appropriate", "feasible", "publishable",
    "tt_enjoyed", "tt_well_written", "tt_boring", "tt_funny", "tt_twist",
    "tt_future",
]
OUTCOMES = {
    "novelty": "eval_novel_index",
    "usefulness": "eval_useful_index",
    "well_written": "eval_tt_well_written",
    "enjoyable": "eval_tt_enjoyed",
    "surprising_twist": "eval_tt_twist",
    "changed_expectations": "eval_tt_future",
    "boring": "eval_tt_boring",
    "funny": "eval_tt_funny",
    "novel": "eval_novel",
    "original": "eval_original",
    "rare": "eval_rare",
    "appropriate": "eval_appropriate",
    "feasible": "eval_feasible",
    "publishable": "eval_publishable",
    "similarity_ai_idea": "sim_idea",
}
COMPUTED_KEYS = [
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se", "se_type",
    "n_clusters",
]


def read_and_validate_data():
    """Independently apply the paper's exclusions and verify processed files."""
    writers = pd.read_stata(WRITERS, convert_categoricals=False)
    evaluators = pd.read_stata(EVALUATORS, convert_categoricals=False)
    raw_w = pd.read_csv(RAW_WRITERS, low_memory=False)
    raw_e = pd.read_csv(RAW_EVALUATORS, low_memory=False)

    # Article p. 7: 500 starters; 169 before consent, 22 no consent,
    # 13 incomplete, and three Human-only writers admitting outside AI use.
    page = raw_w["participant._current_page_name"]
    assert len(raw_w) == 500
    assert int(page.isna().sum()) == 169
    assert int(page.eq("ConsentDropout").sum()) == 22
    assert int((page.notna() & ~page.isin(["Finally", "ConsentDropout"])).sum()) == 13
    completed = raw_w.loc[page.eq("Finally")].copy()
    admitted = completed["follow_up.1.player.used_ai_tool"].fillna(
        completed["follow_up.2.player.used_ai_tool"]
    )
    outside_ai = completed["participant.condition"].eq("human") & admitted.eq(1)
    assert len(completed) == 296 and int(outside_ai.sum()) == 3
    retained = completed.loc[~outside_ai].copy()
    retained["condition"] = retained["participant.condition"].map(
        {"human": 1, "human_1AI": 2, "human_5AI": 3}
    )
    assert retained["condition"].notna().all()
    assert retained["condition"].value_counts().to_dict() == {1: 95, 2: 100, 3: 98}

    # The deposited creators.dta already has these exclusions applied.
    assert len(writers) == 293 and writers["human_admitted"].eq(0).all()
    assert writers["writer_id"].is_unique and writers["story_id"].is_unique
    assert set(retained["participant.code"]) == set(writers["writer_id"])
    wr = retained.set_index("participant.code").loc[writers["writer_id"]]
    np.testing.assert_array_equal(wr["condition"], writers["condition"])
    np.testing.assert_array_equal(
        wr["ai_story_gen.1.player.story_id"], writers["story_id"]
    )
    topics = wr["participant.topic"].map(
        {
            "an adventure in the jungle": 1,
            "an adventure on a different planet": 2,
            "an adventure on the open seas": 3,
        }
    )
    np.testing.assert_array_equal(topics, writers["writer_topic"])
    ideas = [f"ai_story_gen.1.player.ai_idea{i}" for i in range(5)]
    requested = wr[ideas].fillna("").ne("").any(axis=1).astype(int)
    np.testing.assert_array_equal(requested, writers["used_ai"])
    assert writers.groupby("condition")["used_ai"].sum().to_dict() == {1: 0, 2: 82, 3: 93}

    # Reconstruct all item ratings directly from the raw evaluator CSV.
    # The database name tt_badly_written is historical: the final survey
    # actually asked whether the story was WELL written. Do not reverse it.
    raw_e = raw_e.loc[raw_e["participant._current_page_name"].eq("Finally")]
    assert len(raw_e) == 600
    parts = []
    for number in range(1, 11):
        part = pd.DataFrame({
            "eval_id": raw_e["participant.code"],
            "story_number": number,
            "story_id": raw_e[f"evaluator.{number}.player.story_id"],
        })
        for item in ITEMS:
            raw_item = "tt_badly_written" if item == "tt_well_written" else item
            part["eval_" + item] = pd.to_numeric(
                raw_e[f"evaluator.{number}.player.{raw_item}"], errors="raise"
            ).astype(float)
        parts.append(part.loc[part["story_id"].notna()])
    ratings = pd.concat(parts, ignore_index=True)
    assert len(ratings) == len(evaluators) == 3600
    keys = ["eval_id", "story_number", "story_id"]
    joined = ratings.merge(
        evaluators, on=keys, how="outer", validate="one_to_one",
        suffixes=("_raw", "_dta"), indicator=True,
    )
    assert joined["_merge"].eq("both").all()
    for item in ITEMS:
        np.testing.assert_array_equal(
            joined["eval_" + item + "_raw"], joined["eval_" + item + "_dta"]
        )

    # Compute indices in float64 from the three constituent items. Stored
    # Stata indices agree within their single-precision storage error.
    for index, components in [
        ("eval_novel_index", ["novel", "original", "rare"]),
        ("eval_useful_index", ["appropriate", "feasible", "publishable"]),
    ]:
        raw_index = joined[["eval_" + v + "_raw" for v in components]].mean(axis=1)
        np.testing.assert_array_equal(raw_index.to_numpy().astype(np.float32), joined[index])
        ratings[index] = ratings[["eval_" + v for v in components]].mean(axis=1)

    # Inner join drops the 81 ratings of writers excluded from the analysis.
    ratings = ratings.merge(
        writers[["story_id", "writer_id", "condition", "writer_topic", "used_ai"]],
        on="story_id", how="inner", validate="many_to_one",
    ).sort_values(["eval_id", "story_number"]).reset_index(drop=True)
    assert len(ratings) == 3519
    assert ratings["writer_id"].nunique() == 293
    assert ratings["eval_id"].nunique() == 600
    assert ratings.groupby("condition").size().to_dict() == {1: 1150, 2: 1187, 3: 1182}
    assert ratings.groupby("writer_id").size().value_counts().to_dict() == {
        9: 1, 10: 9, 11: 61, 12: 141, 13: 77, 14: 4,
    }
    assert ratings.groupby("eval_id").size().value_counts().to_dict() == {
        4: 5, 5: 71, 6: 524,
    }
    rating_outcomes = [v for v in OUTCOMES.values() if v != "sim_idea"]
    assert not ratings[rating_outcomes].isna().any().any()
    assert ratings[rating_outcomes].ge(1).all().all()
    assert ratings[rating_outcomes].le(9).all().all()
    # This is the author's post-exclusion order, not original story_number.
    ratings["story_order"] = ratings.groupby("eval_id").cumcount() + 1
    writers["sim_idea"] = writers["sim_idea"].astype(float)
    assert writers["sim_idea"].notna().all()
    return writers, ratings


def paper_model(data, outcome, combined=False, fixed_effects=""):
    """Reproduce rating-level OLS or the writer-level anchoring regression."""
    if combined:
        x = pd.DataFrame({"constant": 1.0, "AI": data["condition"].ne(1).astype(float)})
    else:
        x = pd.DataFrame({
            "constant": 1.0,
            "one": data["condition"].eq(2).astype(float),
            "five": data["condition"].eq(3).astype(float),
        })
    y = data[outcome].astype(float)
    if not fixed_effects:
        if outcome == "sim_idea":
            model = sm.OLS(y, x).fit(cov_type="HC1", use_t=True)
            df = len(data) - x.shape[1]
        else:
            model = sm.OLS(y, x).fit(
                cov_type="cluster", cov_kwds={"groups": data["eval_id"]}, use_t=True
            )
            df = data["eval_id"].nunique() - 1
        return list(x.columns), np.asarray(model.params), np.asarray(model.cov_params()), df

    # Within-evaluator transformation reproduces Stata xtreg ..., fe.
    # Evaluator FE are nested in the evaluator clusters. The finite-sample
    # correction counts the slopes and one constant, not 600 evaluator FE.
    x = x.drop(columns="constant")
    if "order" in fixed_effects:
        x = pd.concat([
            x, pd.get_dummies(data["story_order"], prefix="order", drop_first=True, dtype=float)
        ], axis=1)
    if "topic" in fixed_effects:
        x = pd.concat([
            x, pd.get_dummies(data["writer_topic"], prefix="topic", drop_first=True, dtype=float)
        ], axis=1)
    if "used_ai" in fixed_effects:
        x["used_ai"] = data["used_ai"].astype(float)
    groups = data["eval_id"]
    xx = (x - x.groupby(groups).transform("mean")).to_numpy()
    yy = (y - y.groupby(groups).transform("mean")).to_numpy()
    assert np.linalg.matrix_rank(xx) == xx.shape[1]
    beta = np.linalg.lstsq(xx, yy, rcond=None)[0]
    residuals = yy - xx @ beta
    scores = pd.DataFrame(xx * residuals[:, None]).groupby(groups).sum().to_numpy()
    bread = np.linalg.inv(xx.T @ xx)
    n, k = xx.shape
    g = groups.nunique()
    covariance = bread @ (scores.T @ scores) @ bread
    covariance *= (g / (g - 1)) * ((n - 1) / (n - k - 1))
    return list(x.columns), beta, covariance, g - 1


def comparison(slug):
    if "_combined_ai_vs_human_only" in slug:
        return [2, 3], [1]
    if "_five_ideas_vs_one_idea" in slug:
        return [3], [2]
    if "_one_idea_vs_human_only" in slug:
        return [2], [1]
    if "_five_ideas_vs_human_only" in slug:
        return [3], [1]
    raise ValueError("Unmapped contrast: " + slug)


def add_check(checks, name, printed, computed, decimals=3):
    if printed is None:
        return
    value = float(computed)
    assert math.isfinite(value)
    if isinstance(printed, str) and printed.startswith("<"):
        match = value < float(printed[1:])
    elif decimals == 0:
        match = value == float(printed)
        value = int(value) if value.is_integer() else value
    else:
        match = f"{value:.{decimals}f}" == f"{float(printed):.{decimals}f}"
    checks.append({
        "statistic": name, "printed": printed, "computed": value, "match": bool(match),
    })


def reproduce(estimate, data, outcome, model):
    slug = estimate["slug"]
    treatment, control = comparison(slug)
    names, beta, covariance, df = model
    contrast = np.zeros(len(names))
    if "AI" in names:
        contrast[names.index("AI")] = 1
    else:
        contrast[names.index("five" if treatment == [3] else "one")] = 1
        if control == [2]:
            contrast[names.index("one")] = -1
    coefficient = float(contrast @ beta)
    se = math.sqrt(float(contrast @ covariance @ contrast))
    p_value = float(2 * stats.t.sf(abs(coefficient / se), df))
    checks = []
    participants = data[["writer_id", "condition"]].drop_duplicates()
    nt = int(participants["condition"].isin(treatment).sum())
    nc = int(participants["condition"].isin(control).sum())
    for name, value in [("n_treatment", nt), ("n_control", nc), ("n_total", nt + nc)]:
        add_check(checks, name, estimate[name], value, 0)
    add_check(checks, "n_units_full_paper_model", estimate["n_units"], len(data), 0)
    add_check(checks, "n_writers_full_paper_model", 293, participants.shape[0], 0)
    if outcome != "sim_idea":
        add_check(checks, "n_evaluators_full_paper_model", 600, data["eval_id"].nunique(), 0)

    printed = estimate["stats"]
    if printed["regression"] is not None:
        add_check(
            checks, "regression.coef", printed["regression"]["coef"], coefficient,
            2 if outcome == "sim_idea" else 3,
        )
        add_check(checks, "regression.se", printed["regression"]["se"], se, 3)
    for arm, conditions in [("treatment", treatment), ("control", control)]:
        values = data.loc[data["condition"].isin(conditions), outcome].astype(float)
        mean_dp = 2 if outcome == "sim_idea" or printed[arm + "_mean"] == 5.21 else 3
        add_check(checks, arm + "_mean", printed[arm + "_mean"], values.mean(), mean_dp)
        if printed[arm + "_sd"] is not None:
            add_check(checks, arm + "_sd", printed[arm + "_sd"], values.std(ddof=1), 2)
    if printed["control_se"] is not None:
        assert control == [1] and "constant" in names
        position = names.index("constant")
        add_check(checks, "control_se", printed["control_se"], math.sqrt(covariance[position, position]))
    if printed["p_value"] is not None:
        p_dp = 4 if slug == "s1_usefulness_five_ideas_vs_one_idea" else 3
        add_check(checks, "p_value", printed["p_value"], p_value, p_dp)
    if printed["test"] is not None:
        assert printed["test"]["type"] == "F" and treatment == [2, 3]
        f_dp = 1 if printed["test"]["value"] >= 10 else 2
        add_check(checks, "test.F", printed["test"]["value"], (coefficient / se) ** 2, f_dp)
    if printed["paper_effect"] is not None:
        control_mean = data.loc[data["condition"].isin(control), outcome].astype(float).mean()
        add_check(
            checks, "paper_effect.percent_increase", printed["paper_effect"]["value"],
            100 * coefficient / control_mean, 1,
        )
    if outcome == "sim_idea":
        # The extraction preserves the less precise main-text coefficients;
        # independently check Table S11's additional printed digits as well.
        add_check(checks, "Table_S11.regression.coef", 4.288 if treatment == [2] else 4.105, coefficient)
        add_check(checks, "Table_S11.control_mean", 82.850, data.loc[data.condition.eq(1), outcome].mean())
    return checks


def participant_statistics(data, outcome, treatment, control):
    # Called ONLY after every reported-statistic reproduction check passes.
    # A writer contributes one story. Average all its ratings within writer.
    people = data.groupby(["writer_id", "condition"], as_index=False)[outcome].mean()
    people = people.loc[people["condition"].isin(treatment + control)].copy()
    indicator = people["condition"].isin(treatment).astype(float)
    y = people[outcome].astype(float)
    x = np.column_stack([np.ones(len(people)), indicator])
    model = sm.OLS(y.to_numpy(), x).fit(cov_type="HC2")
    tv, cv = y.loc[indicator.eq(1)], y.loc[indicator.eq(0)]
    difference = float(tv.mean() - cv.mean())
    difference_se = float(model.bse[1])
    np.testing.assert_allclose(model.params[1], difference, rtol=0, atol=1e-12)
    # For an intercept and binary arm indicator, the HC2 variance is exactly
    # the sum of the two sample variances divided by their respective n.
    np.testing.assert_allclose(
        difference_se, math.sqrt(tv.var(ddof=1) / len(tv) + cv.var(ddof=1) / len(cv)),
        rtol=0, atol=1e-12,
    )
    return {
        "n_treatment": int(len(tv)), "n_control": int(len(cv)),
        "treatment_mean": float(tv.mean()), "treatment_sd": float(tv.std(ddof=1)),
        "control_mean": float(cv.mean()), "control_sd": float(cv.std(ddof=1)),
        "difference": difference, "difference_se": difference_se,
        "se_type": "HC2", "n_clusters": None,
    }


def result_notes(estimate, outcome, fixed_effects):
    common = (
        "One between-person RCT with individual writers randomized, one story per writer; "
        "round=all. Evaluators are a separate sample, so their repeated assessments do not "
        "make this a within-writer or first-round design. Counts are writers. Raw CSV "
        "exclusions independently reproduce 500 starters, 169 before consent, 22 without "
        "consent, 13 noncompleters, and 3 Human-only writers admitting outside AI use. "
        "All 293 included writer IDs and all 3600 pre-exclusion evaluator records and item "
        "ratings match the processed Stata files. Linking eligible stories removes 81 "
        "ratings, leaving 3519 ratings from 600 evaluators. Assigned AI access is the "
        "treatment even when no idea was requested; 82/100 and 93/98 requested an idea. "
    )
    if outcome == "sim_idea":
        detail = (
            "Outcome is creators.dta:sim_idea, the deposited writer-specific story-to-AI-idea "
            "cosine similarity times 100. This is an anchoring outcome, not the set-level "
            "other-stories diversity outcome. The original assigned reference idea is "
            "ai_idea_combined0: the first available requested idea, or the authors' random "
            "same-topic idea for nonusers. Original stored scores are used without a new "
            "embedding call or random reassignment. Reproduction uses all 293 writers, "
            "both assigned-arm indicators, and HC1 as in the paper's Stata reg, vce(r). "
            "Checks include the main-text coefficient (2 decimal places), Table S11 "
            "coefficient and intercept (3 places), and Table S12 control SD (2 places). "
            "Source: article p. 5; supplement pp. 10 and 12, Tables S11-S12. Higher values "
            "mean greater similarity; difference is in original units without sign reversal. "
        )
    else:
        detail = (
            "Outcome variable: " + outcome + ". Each evaluator's novelty index is the "
            "arithmetic mean of novel, original, rare; usefulness is the mean of appropriate, "
            "feasible, publishable. Indices are rebuilt from integer items in float64; "
            "stored Stata indices match exactly after float32 rounding. All included ratings have "
            "complete outcomes on the 1-9 scale. The database's tt_badly_written column "
            "is the final survey's well-written question and is not reversed. Paper "
            "reproduction uses individual ratings and SEs clustered by 600 evaluators "
            "with the Stata small-sample correction and t reference distribution, df=599. "
            "n_units is the full paper model's 3519, not a two-arm subtotal. Table "
            "coefficients, SEs and intercepts are compared at 3 decimal places; the "
            "main-text mean 5.21 at 2 places, percentage changes at 1 place, and p/F "
            "values at their printed precision (or their stated bound). Sources: "
            "article pp. 3, 7-8; supplement Tables S1, S3, S4, S6, S13. "
        )
    if fixed_effects:
        detail += (
            "The Table S4 specification reproduced here is " + fixed_effects + ". "
            "Evaluator effects are removed by within-evaluator demeaning. Story order "
            "is reindexed after exclusions, exactly as in the authors' text code; topic "
            "is writer_topic, and used_ai indicates requesting an idea. Assigned-arm "
            "coefficients are checked in the full model including these controls. "
            "The requested computed object then reports the unadjusted writer-level "
            "arm comparison; it intentionally repeats the corresponding main-specification "
            "participant summary and does not treat adjusted coefficients as raw means. "
        )
    elif "combined_ai" in estimate["slug"]:
        detail += "The combined treatment pools all 198 AI-assigned writers with equal writer weight. "
    elif "five_ideas_vs_one_idea" in estimate["slug"]:
        detail += (
            "The printed 5.1% and p=0.0012 are reproduced as a linear contrast of the "
            "two AI coefficients in the full three-arm rating model; the new participant "
            "contrast uses only the 98 five-idea and 100 one-idea writers. "
        )
    return common + detail + (
        "After successful reproduction, average ratings within writer before computing "
        "arm means and sample SDs (denominator n-1); each writer has equal weight. "
        "For anchoring there is already one score per writer. Difference is treatment "
        "minus control in original outcome units. difference_se is from OLS on a constant "
        "and arm indicator with HC2, checked against sqrt(s_t^2/n_t + s_c^2/n_c). "
        "Randomization was not clustered, so n_clusters=null. Shared controls, pooled "
        "contrasts, and robustness specifications reuse participants."
    )


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    assert extraction["cid"] == "c006" and len(extraction["estimates"]) == 57
    writers, ratings = read_and_validate_data()
    models = {}
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        if slug.startswith("s1_similarity_other_stories_"):
            skipped.append({
                "slug": slug,
                "reason": (
                    "Set-level diversity outcome: exact recomputation from the original "
                    "texts and embeddings is not possible with the posted data. The "
                    "authors' ai_human_story_similarity.py (read as text only) identifies "
                    "text-embedding-ada-002, but the original vectors are not deposited. "
                    "creators.dta contains derived sim_cstories scores only. Moreover, "
                    "that code's condition-average embedding includes the focal story, "
                    "whereas article pp. 4 and 8 describe all OTHER stories in the same "
                    "condition. Neither substituting an embedding model nor treating "
                    "stored set-dependent scores as independent participant outcomes "
                    "would follow the requested exact procedure. No arm statistics or "
                    "participant-level HC2 SE are computed for this outcome."
                ),
            })
            continue
        mapped = [v for name, v in OUTCOMES.items() if slug.startswith("s1_" + name + "_")]
        assert len(mapped) == 1, slug
        outcome = mapped[0]
        data = writers if outcome == "sim_idea" else ratings
        fixed_effects = slug.split("_evaluator_", 1)[1] if "_evaluator_" in slug else ""
        if fixed_effects:
            fixed_effects = "evaluator_" + fixed_effects
        combined = "_combined_ai_" in slug
        key = (outcome, combined, fixed_effects)
        if key not in models:
            models[key] = paper_model(data, outcome, combined, fixed_effects)
        checks = reproduce(estimate, data, outcome, models[key])
        passed = all(check["match"] for check in checks)
        if passed:
            treatment, control = comparison(slug)
            computed = participant_statistics(data, outcome, treatment, control)
            notes = result_notes(estimate, outcome, fixed_effects)
        else:
            computed = dict.fromkeys(COMPUTED_KEYS)
            differences = [
                f"{c['statistic']}: printed={c['printed']}, recomputed={c['computed']}"
                for c in checks if not c["match"]
            ]
            notes = "Reproduction failed; no participant statistics computed. " + "; ".join(differences)
        results.append({
            "slug": slug, "round": "all", "reproduced": checks,
            "computed": computed, "notes": notes,
        })
    assert len(results) + len(skipped) == len(extraction["estimates"])
    obj = {
        "cid": "c006", "analyst": "A", "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in [WRITERS, EVALUATORS, RAW_WRITERS, RAW_EVALUATORS]],
        "results": results, "skipped": skipped,
    }
    # Reject NaN/Infinity before writing; then use the requested JSON encoding.
    json.dumps(obj, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    summary = {
        "cid": "c006", "n_results": len(results),
        "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
