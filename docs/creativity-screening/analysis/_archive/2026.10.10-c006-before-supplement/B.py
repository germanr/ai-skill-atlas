# Analyst B, c006. Run with: python -I -B B.py
# This is independently written analysis code. Deposited programs were read
# only as text; none is executed, imported, evaluated, or used as a module.
# The only output of this script is the explicitly authorized B.json.
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data/zenodo-11654403")
DATA = DEPOSIT / "GenAI_creativity_scripts-unpacked/GenAI_creativity_scripts"
SCRIPT = ROOT / "analysis/c006/B.py"
OUTPUT = ROOT / "analysis/c006/B.json"
EXTRACTION = ROOT / "extraction/c006.json"
RAW_WRITERS = DATA / "raw_data/writers-2023-06-28.csv"
RAW_EVALUATORS = DATA / "raw_data/evaluators-2023-07-06.csv"
PROCESSED_WRITERS = DATA / "already_processed_data/creators.dta"
PROCESSED_EVALUATORS = DATA / "already_processed_data/evaluators_stories.dta"

# First twelve variables are individual pre-disclosure ratings. The raw
# tt_badly_written field is positively worded in the final experiment:
# 01_writer_process_output.do and 02_evaluator_process_output.do explicitly
# explain the obsolete database name. Do NOT reverse that field.
ITEMS = [
    "novel", "original", "rare", "appropriate", "feasible", "publishable",
    "tt_badly_written", "tt_enjoyed", "tt_twist", "tt_future", "tt_boring",
    "tt_funny",
]
RATING_COLUMNS = ["eval_" + item.replace("badly", "well") for item in ITEMS]
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
ARMS = {
    "Human-only": (1,),
    "Human with one GenAI idea": (2,),
    "Human with five GenAI ideas": (3,),
    "Human with one GenAI idea and Human with five GenAI ideas (combined)": (2, 3),
}
COMPUTED_FIELDS = [
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se", "se_type",
    "n_clusters",
]


def check(statistic, printed, computed, decimals=0):
    """Compare at the actual printed precision, never a loose tolerance."""
    if isinstance(printed, str) and printed.startswith("<"):
        match = float(computed) < float(printed[1:])
    elif decimals == 0:
        match = float(computed) == float(printed)
    else:
        match = (format(float(computed), f".{decimals}f") ==
                 format(float(printed), f".{decimals}f"))
    return {"statistic": statistic, "printed": printed,
            "computed": computed, "match": bool(match)}


def rebuild_data():
    raw_w = pd.read_csv(RAW_WRITERS, low_memory=False)
    pages = raw_w["participant._current_page_name"]
    assert len(raw_w) == 500
    assert int(pages.isna().sum()) == 169
    assert int(pages.eq("ConsentDropout").sum()) == 22
    assert int((pages.notna() & ~pages.isin(["Finally", "ConsentDropout"])).sum()) == 13
    completed = raw_w.loc[pages.eq("Finally")].copy()
    assert len(completed) == 296
    used_outside_ai = completed["follow_up.1.player.used_ai_tool"].combine_first(
        completed["follow_up.2.player.used_ai_tool"])
    excluded = completed["participant.condition"].eq("human") & used_outside_ai.eq(1)
    assert int(excluded.sum()) == 3
    retained = completed.loc[~excluded].copy()
    writers = retained[["participant.code", "ai_story_gen.1.player.story_id"]].rename(
        columns={"participant.code": "writer_id",
                 "ai_story_gen.1.player.story_id": "story_id"})
    writers["condition"] = retained["participant.condition"].map(
        {"human": 1, "human_1AI": 2, "human_5AI": 3})
    assert writers.notna().all().all()
    assert writers["writer_id"].is_unique and writers["story_id"].is_unique
    assert writers.groupby("condition").size().to_dict() == {1: 95, 2: 100, 3: 98}

    # The posted creators.dta is already restricted to these 293 writers.
    processed_w = pd.read_stata(PROCESSED_WRITERS, convert_categoricals=False)
    assert processed_w["human_admitted"].eq(0).all()
    raw_keys = writers.sort_values("writer_id").reset_index(drop=True)
    posted_keys = processed_w[raw_keys.columns].sort_values("writer_id").reset_index(drop=True)
    pd.testing.assert_frame_equal(raw_keys, posted_keys, check_dtype=False)
    writers = writers.merge(processed_w[["writer_id", "sim_idea"]],
                            on="writer_id", validate="one_to_one")
    writers["sim_idea"] = writers["sim_idea"].astype(float)
    assert writers["sim_idea"].notna().all()

    # No text correction or re-embedding is applied. Two strings in the posted
    # Stata file contain a UTF-8/Latin-1 encoding artifact relative to the CSV.
    raw_text = retained.set_index("participant.code")["ai_story_gen.1.player.story"]
    posted_text = processed_w.set_index("writer_id")["writer_story"]
    differing_texts = int((raw_text.reindex(posted_text.index) != posted_text).sum())
    assert differing_texts == 2

    raw_e = pd.read_csv(RAW_EVALUATORS, low_memory=False)
    completed_e = raw_e.loc[raw_e["participant._current_page_name"].eq("Finally")]
    assert len(completed_e) == 600
    parts = []
    for story_number in range(1, 11):
        stub = f"evaluator.{story_number}.player."
        names = {"participant.code": "eval_id", stub + "story_id": "story_id"}
        names.update({stub + item: variable for item, variable in zip(ITEMS, RATING_COLUMNS)})
        part = completed_e[list(names)].rename(columns=names).copy()
        part["story_number"] = story_number
        parts.append(part.dropna(subset=["story_id"]))
    raw_ratings = pd.concat(parts, ignore_index=True)
    assert len(raw_ratings) == 3600
    assert not raw_ratings.duplicated(["eval_id", "story_number"]).any()
    ratings = raw_ratings.merge(writers[["writer_id", "story_id", "condition"]],
                               on="story_id", how="inner", validate="many_to_one")
    assert len(raw_ratings) - len(ratings) == 81
    assert len(ratings) == 3519
    assert ratings["eval_id"].nunique() == 600
    assert ratings["writer_id"].nunique() == 293
    assert ratings.groupby("condition").size().to_dict() == {1: 1150, 2: 1187, 3: 1182}
    assert ratings.groupby("story_id").size().value_counts().to_dict() == {
        9: 1, 10: 9, 11: 61, 12: 141, 13: 77, 14: 4}
    assert ratings.groupby("eval_id").size().value_counts().to_dict() == {4: 5, 5: 71, 6: 524}
    assert ratings[RATING_COLUMNS].notna().all().all()
    assert ((ratings[RATING_COLUMNS] >= 1) & (ratings[RATING_COLUMNS] <= 9)).all().all()

    # Verify all relevant raw ratings against the deposited processed data.
    processed_r = pd.read_stata(PROCESSED_EVALUATORS, convert_categoricals=False)
    processed_r = processed_r.merge(writers[["writer_id", "story_id", "condition"]],
                                    on="story_id", how="inner", validate="many_to_one")
    # Stata stores story_number as int8; align storage types before checking keys.
    processed_r["story_number"] = processed_r["story_number"].astype("int64")
    keys = ["eval_id", "story_number", "story_id"]
    raw_sorted = ratings.set_index(keys).sort_index()
    posted_sorted = processed_r.set_index(keys).sort_index()
    pd.testing.assert_index_equal(raw_sorted.index, posted_sorted.index)
    pd.testing.assert_frame_equal(raw_sorted[RATING_COLUMNS], posted_sorted[RATING_COLUMNS],
                                  check_dtype=False, check_exact=True)
    for variable, components in [
        ("eval_novel_index", ["novel", "original", "rare"]),
        ("eval_useful_index", ["appropriate", "feasible", "publishable"]),
    ]:
        cols = ["eval_" + component for component in components]
        ratings[variable] = ratings[cols].astype(float).mean(axis=1)
        exact_sorted = ratings.set_index(keys).sort_index()[variable].to_numpy()
        # Stored Stata indices have float32 rounding; compute the arithmetic
        # means afresh in float64 for both replication and participant analyses.
        np.testing.assert_allclose(exact_sorted, posted_sorted[variable], rtol=0, atol=4e-7)
    return writers, ratings


def paper_fit(frame, variable, rating_level):
    available = frame.dropna(subset=[variable, "condition"])
    x = np.column_stack([np.ones(len(available)),
                         available["condition"].eq(2).astype(float),
                         available["condition"].eq(3).astype(float)])
    y = available[variable].to_numpy(dtype=float)
    if rating_level:
        # Stata reg ..., vce(cluster eval_id): CR1 finite-sample correction
        # G/(G-1) * (N-1)/(N-K), with t inference on G-1 degrees of freedom.
        fit = sm.OLS(y, x).fit(cov_type="cluster", cov_kwds={
            "groups": available["eval_id"], "use_correction": True,
            "df_correction": True}, use_t=True)
        assert fit.df_resid_inference == available["eval_id"].nunique() - 1
    else:
        # Stata vce(robust) is HC1, used ONLY to reproduce the paper's p-values.
        fit = sm.OLS(y, x).fit(cov_type="HC1", use_t=True)
    return fit, available


def contrast_vector(arm):
    assert len(arm) == 1
    return {1: np.array([1., 0., 0.]), 2: np.array([1., 1., 0.]),
            3: np.array([1., 0., 1.])}[arm[0]]


def reproduce(estimate, frame, variable, rating_level, writers):
    fit, available = paper_fit(frame, variable, rating_level)
    treatment = ARMS[estimate["treatment_arm"]]
    control = ARMS[estimate["control_arm"]]
    test = fit.t_test(contrast_vector(treatment) - contrast_vector(control))
    coefficient = float(np.asarray(test.effect).item())
    p_value = float(np.asarray(test.pvalue).item())
    means = available.groupby("condition")[variable].mean()
    treatment_mean, control_mean = float(means[treatment[0]]), float(means[control[0]])
    participants = available[["writer_id", "condition"]].drop_duplicates()
    checks = [check("n_writers_all_arms", 293, int(participants["writer_id"].nunique()))]
    for field, arm in [("n_treatment", treatment), ("n_control", control)]:
        if estimate[field] is not None:
            checks.append(check(field, estimate[field],
                                int(participants["condition"].isin(arm).sum())))
    if estimate["n_total"] is not None:
        checks.append(check("n_total", estimate["n_total"], int(len(participants))))
    if estimate["n_units"] is not None:
        checks.append(check("n_units", estimate["n_units"], int(len(available))))
    if rating_level:
        checks.append(check("n_evaluators", 600, int(available["eval_id"].nunique())))
    stats = estimate["stats"]
    if stats["regression"] is not None and stats["regression"]["coef"] is not None:
        checks.append(check("regression.coef", stats["regression"]["coef"], coefficient,
                            3 if rating_level else 2))
    for field, value in [("treatment_mean", treatment_mean), ("control_mean", control_mean)]:
        if stats[field] is not None:
            checks.append(check(field, stats[field], value, 2))
    if stats["p_value"] is not None:
        decimals = 4 if estimate["slug"].endswith("five_ideas_vs_one_idea") else 3
        checks.append(check("p_value", stats["p_value"], p_value, decimals))
    if stats["paper_effect"] is not None:
        checks.append(check("paper_effect.value", stats["paper_effect"]["value"],
                            100 * (treatment_mean - control_mean) / control_mean, 1))
    return checks


def participant_statistics(frame, variable, treatment, control):
    # This function is called only AFTER the printed-statistic gate passes.
    selected = frame.loc[frame["condition"].isin(treatment + control)].copy()
    assert selected.groupby("writer_id")["condition"].nunique().eq(1).all()
    # One story per writer, several ratings per story. Every writer receives
    # equal weight regardless of the number of ratings of that writer's story.
    person = selected.groupby(["writer_id", "condition"], as_index=False)[variable].mean()
    person = person.dropna(subset=[variable])
    assert person["writer_id"].is_unique
    indicator = person["condition"].isin(treatment).astype(float).to_numpy()
    y = person[variable].to_numpy(dtype=float)
    treated, controls = y[indicator == 1], y[indicator == 0]
    fit = sm.OLS(y, np.column_stack([np.ones(len(y)), indicator])).fit(cov_type="HC2")
    difference = float(treated.mean() - controls.mean())
    difference_se = float(fit.bse[1])
    # Independent algebraic check for an intercept and one binary indicator.
    # HC2 variance equals s_T^2/n_T + s_C^2/n_C in this two-arm design.
    formula_se = math.sqrt(float(treated.var(ddof=1) / len(treated) +
                                 controls.var(ddof=1) / len(controls)))
    assert math.isclose(difference, float(fit.params[1]), rel_tol=0, abs_tol=1e-12)
    assert math.isclose(difference_se, formula_se, rel_tol=1e-12, abs_tol=1e-12)
    return {
        "n_treatment": int(len(treated)), "n_control": int(len(controls)),
        "treatment_mean": float(treated.mean()), "treatment_sd": float(treated.std(ddof=1)),
        "control_mean": float(controls.mean()), "control_sd": float(controls.std(ddof=1)),
        "difference": difference, "difference_se": difference_se,
        "se_type": "HC2", "n_clusters": None,
    }


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    assert extraction["cid"] == "c006"
    assert extraction["studies"][0]["assignment_unit"] == "individual"
    with (ROOT / "retrieval.json").open(encoding="utf-8") as fh:
        retrieval = json.load(fh)["c006"]
    writers, ratings = rebuild_data()
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        slug, stats = estimate["slug"], estimate["stats"]
        assert estimate["within_person"] is None
        if estimate["question"] == "across_people":
            skipped.append({"slug": slug, "reason": (
                "Set-level diversity cannot be recomputed exactly from the deposited data. "
                "The deposit stores sim_cstories scores but no embedding vectors. The authors' "
                "ai_human_story_similarity.py (read as text only) names text-embedding-ada-002, "
                "but its condition centroid includes the focal story; PDF pp. 4 and 8 specify "
                "the average embedding of the other stories. Thus averaging the deposited "
                "scores would not independently reproduce the paper's stated embedding "
                "procedure. No fresh embeddings were generated and no participant-level "
                "SD or HC2 standard error is assigned to this set-based measure.")})
            continue
        has_numeric_anchor = (stats["treatment_mean"] is not None or
                              stats["control_mean"] is not None or
                              stats["difference"] is not None or
                              (stats["regression"] is not None and
                               stats["regression"]["coef"] is not None))
        if not has_numeric_anchor:
            if "combined_ai" in slug:
                reason = ("The saved paper describes the combined-AI effect qualitatively "
                          "and refers to supplementary section S4; the reconciled extraction "
                          "prints no mean, difference, or coefficient for this contrast. "
                          "The separate supplement is absent from the saved ten-page PDF, "
                          "its complete markdown, and the supplied deposits.")
            else:
                reason = ("This contrast appears only as an unlabeled plotted estimate in "
                          "Fig. 2; the reconciled extraction and available paper contain no "
                          "numerically printed arm mean, difference, or coefficient. The "
                          "separate supplementary tables are not available in the supplied files.")
            skipped.append({"slug": slug, "reason": reason +
                            " Counts or a reproduced related contrast alone cannot satisfy "
                            "the required estimate-specific reproduction gate. No participant "
                            "statistics were computed for this estimate."})
            continue
        outcome_key = next(key for key in OUTCOMES
                           if slug.startswith("s1_" + key + "_") and
                           slug[len("s1_" + key + "_"):].startswith(("one_idea", "five_ideas", "combined_ai")))
        variable = OUTCOMES[outcome_key]
        rating_level = variable != "sim_idea"
        frame = ratings if rating_level else writers
        checks = reproduce(estimate, frame, variable, rating_level, writers)
        treatment, control = ARMS[estimate["treatment_arm"]], ARMS[estimate["control_arm"]]
        common_notes = (
            "Between-writer randomized comparison; round=all. No paired or first-round "
            "contrast applies. Exclusions were independently rebuilt from raw CSVs: "
            "500 writer records, 169 exited before consent, 22 consent dropouts, 13 other "
            "non-completers, and 3 Human-only completers admitting AI use; 293 retained "
            "writers match creators.dta exactly by writer ID, story ID, and assignment. "
            "Observed writer counts are Human-only=95, one idea=100, five ideas=98; "
            "optional non-users in the AI arms are retained. Printed counts refer to PDF "
            "pp. 2, 7 and 8; n_units is the full three-arm count, not the pairwise count. "
        )
        if rating_level:
            specific_notes = (
                f"Outcome variable: {variable}. Reproduction checks use the paper's "
                "rating-level, three-arm OLS with an intercept and two assignment "
                "indicators, clustering by evaluator (CR1 correction and t inference "
                "with 599 df); means, coefficients, p-values and percentages are "
                "compared to PDF p. 3 at their printed precision. Completed evaluators "
                "supply 3600 ratings; dropping the 81 ratings of ineligible stories "
                "leaves 3519 ratings by 600 evaluators. All 12 relevant raw rating "
                "variables match evaluators_stories.dta exactly; no rating is missing. "
                "Arm rating counts are 1150, 1187, and 1182. Novelty is the mean of "
                "novel/original/rare; usefulness is the mean of appropriate/feasible/"
                "publishable, rederived in float64 (posted indices have only float32 "
                "rounding differences, maximum 3.18e-7). After successful reproduction, "
                "ratings are averaged within writer before means, sample SDs (ddof=1), "
                "and a two-arm participant-level OLS with HC2 are computed. Unequal "
                "numbers of ratings mean these equal-writer effects need not equal "
                "the paper's rating-weighted coefficients. "
            )
            if outcome_key == "well_written":
                specific_notes += ("Raw tt_badly_written is the final study's positively "
                                   "worded well-written item, as documented in both "
                                   "processing .do files; no reversal is applied. ")
            if slug.endswith("five_ideas_vs_one_idea"):
                specific_notes += ("The printed 5.21 mean, 5.1% improvement, and P=0.0012 "
                                   "are reproduced; the paper's p-value is the difference "
                                   "between the two AI coefficients in the three-arm model. ")
        else:
            specific_notes = (
                "Outcome is the deposited sim_idea score (cosine similarity multiplied "
                "by 100), one value per writer, including the deposited assigned "
                "comparison idea for non-users. This anchoring outcome is with_ai/other, "
                "not set-level diversity. The printed coefficient, Human-only mean, "
                "percentage and p-value on PDF p. 5 are reproduced using three-arm "
                "OLS, HC1 covariance and t inference with 290 df, matching the authors' "
                "Stata vce(robust) specification. The requested final two-arm uncertainty "
                "is HC2. Authors' code, read only as text, names text-embedding-ada-002 "
                "and assigns non-users an idea within topic (consistent with PDF p. 5; "
                "p. 8 instead says condition). No API was called, no idea resampled, and "
                "no embeddings regenerated: these statistics analyze the published "
                "per-writer scores. Two posted Stata story strings have encoding artifacts "
                "relative to raw CSV; neither texts nor published scores were altered. "
            )
        notes = common_notes + specific_notes + (
            "All final differences are treatment minus control in the original outcome "
            "units, with no sign reversal. HC2 SE is also checked against "
            "sqrt(s_treatment^2/n_treatment + s_control^2/n_control). No classes, "
            "teams, or sessions were randomized, so n_clusters is null. Author "
            "programs were consulted as text only. The .py and .json files for "
            "analyst A were not read."
        )
        if all(entry["match"] for entry in checks):
            computed = participant_statistics(frame, variable, treatment, control)
        else:
            computed = dict.fromkeys(COMPUTED_FIELDS)
            failures = [entry for entry in checks if not entry["match"]]
            notes += " REPRODUCTION FAILED; no participant statistics computed: " + json.dumps(failures)
        results.append({"slug": slug, "round": "all", "reproduced": checks,
                        "computed": computed, "notes": notes})

    # All source files inspected for this analysis, including documentary inputs.
    consulted = [
        RAW_WRITERS, RAW_EVALUATORS, PROCESSED_WRITERS, PROCESSED_EVALUATORS,
        EXTRACTION, ROOT / "retrieval.json", ROOT / "extraction-spec.md",
        ROOT.parent / "creativity-codebook.md", Path(retrieval["md_path"]),
        Path(retrieval["pdf_path"]),
        Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json"),
        DEPOSIT / "README.md", DATA / "readme.txt",
        DATA / "scripts/01_writer_process_output.do",
        DATA / "scripts/02_evaluator_process_output.do",
        DATA / "scripts/03_analysis.do",
        DATA / "scripts/ai_human_story_similarity.py",
    ]
    result_slugs = {row["slug"] for row in results}
    skipped_slugs = {row["slug"] for row in skipped}
    assert not result_slugs & skipped_slugs
    assert result_slugs | skipped_slugs == {row["slug"] for row in extraction["estimates"]}
    assert len(result_slugs) == len(results) and len(skipped_slugs) == len(skipped)
    for row in results:
        for value in row["computed"].values():
            if isinstance(value, (int, float)):
                assert math.isfinite(value)
    obj = {"cid": "c006", "analyst": "B", "script": SCRIPT.as_posix(),
           "data_files": [path.as_posix() for path in consulted],
           "results": results, "skipped": skipped}
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    summary = {"cid": "c006", "n_results": len(results),
               "n_reproduced": sum(all(item["match"] for item in row["reproduced"])
                                   for row in results), "n_skipped": len(skipped)}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
