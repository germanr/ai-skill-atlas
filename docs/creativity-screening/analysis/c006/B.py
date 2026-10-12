"""Independent analyst B reanalysis of Doshi and Hauser (2024), paper c006.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c006/B.py

Only B.json is written by this script. Deposit programs are never imported or
executed. The authors' Stata and Python programs were inspected as plain text.
The complete article and supplement markdown were read, and the numerical
sources were checked with PyMuPDF against main PDF pp. 3, 5, 7, 8 and
supplement PDF pp. 5, 6, 7, 10, 12, 14.

Analysis mapping:
- Individual writers were randomized. Each writer supplied one story.
- Raw writers: retain participant._current_page_name == Finally; exclude
  Human-only writers admitting AI use, using follow_up.1 then follow_up.2.
  This gives 95 Human-only, 100 one-idea, and 98 five-idea writers.
- Raw evaluators: retain Finally; reshape nonempty story_id slots 1..10.
  This gives 3600 rows. Inner-join eligible writers on story_id to obtain
  3519 ratings of 293 stories by 600 evaluators.
- Novelty = mean(novel, original, rare); usefulness =
  mean(appropriate, feasible, publishable), all on the 1..9 scale.
  The field tt_badly_written actually asks about "well written" in this study.
- Table S4 order is the consecutive order of RETAINED ratings for each
  evaluator, not the original story_number when an earlier story was excluded.
- First reproduce rating-level regressions, evaluator-clustered standard
  errors, arm counts, and other printed statistics. Table S4 is reproduced
  using evaluator demeaning and its specified additional covariates.
- Only after every checked printed statistic for an estimate matches, average
  ratings within the randomized writer and fit a two-arm OLS with HC2.
  Adjusted slugs retain their adjusted reproduction checks, but their computed
  block is the requested unadjusted participant-level contrast, so it repeats
  the corresponding main-specification computed block.
- sim_idea is an existing participant-level outcome (100 * cosine similarity).
  Its original saved values and assigned AI ideas are used, not new embeddings.
- Set-based sim_cstories outcomes are skipped: original embeddings are absent
  and the posted implementation includes the focal story in its condition
  centroid, whereas the paper specifies the other stories. No independent
  participant-level SD or HC2 SE is assigned to this set-based outcome.
"""

import sys
sys.dont_write_bytecode = True

from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import json
import math

import numpy as np
import pandas as pd
import statsmodels.api as sm


WORKSPACE = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = WORKSPACE / "analysis/c006/B.py"
OUTPUT = WORKSPACE / "analysis/c006/B.json"
EXTRACTION = WORKSPACE / "extraction/c006.json"
DEPOSIT = Path(
    "D:/projects/ai-skill-atlas/creativity-data/zenodo-11654403/"
    "GenAI_creativity_scripts-unpacked/GenAI_creativity_scripts"
)
WRITERS_DTA = DEPOSIT / "already_processed_data/creators.dta"
EVALUATORS_DTA = DEPOSIT / "already_processed_data/evaluators_stories.dta"
WRITERS_CSV = DEPOSIT / "raw_data/writers-2023-06-28.csv"
EVALUATORS_CSV = DEPOSIT / "raw_data/evaluators-2023-07-06.csv"
DATA_FILES = [WRITERS_DTA, EVALUATORS_DTA, WRITERS_CSV, EVALUATORS_CSV]

ARM_CODES = {
    "Human-only": (1,),
    "Human with one GenAI idea": (2,),
    "Human with five GenAI ideas": (3,),
    "Human with one GenAI idea and Human with five GenAI ideas (combined)": (2, 3),
}
RAW_ARMS = {"human": 1, "human_1AI": 2, "human_5AI": 3}
ITEMS = {
    "novel": "novel",
    "original": "original",
    "rare": "rare",
    "appropriate": "appropriate",
    "feasible": "feasible",
    "publishable": "publishable",
    "tt_enjoyed": "tt_enjoyed",
    "tt_well_written": "tt_badly_written",
    "tt_boring": "tt_boring",
    "tt_funny": "tt_funny",
    "tt_twist": "tt_twist",
    "tt_future": "tt_future",
}
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
INDEX_COMPONENTS = {
    "eval_novel_index": ["eval_novel", "eval_original", "eval_rare"],
    "eval_useful_index": ["eval_appropriate", "eval_feasible", "eval_publishable"],
}
SET_OUTCOME_REASON = (
    "Set-based diversity outcome: the paper specifies 100 times the cosine "
    "similarity of a focal story to the average embedding of all OTHER stories "
    "in its randomized condition. The deposit has story texts and saved scalar "
    "sim_cstories values, but no original embeddings. The authors' "
    "ai_human_story_similarity.py, inspected only as text, identifies "
    "text-embedding-ada-002 and averages all embeddings in the condition, "
    "including the focal story. Therefore the paper's stated leave-one-out "
    "procedure cannot be verified or reconstructed exactly from the deposited "
    "scalars. No replacement embeddings, participant SDs, or HC2 errors were "
    "computed for this set-based measure."
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_record(statistic, printed, computed, places=None):
    """Compare to the printed precision, keeping unrounded computed values."""
    require(printed is not None, "Cannot verify an unprinted statistic")
    if computed is None or not math.isfinite(float(computed)):
        return {
            "statistic": statistic, "printed": printed,
            "computed": None, "match": False,
        }
    if isinstance(printed, str) and printed.startswith("<"):
        match = float(computed) < float(printed[1:])
    else:
        if places is None:
            places = max(0, -Decimal(str(printed)).as_tuple().exponent)
        quantum = Decimal(1).scaleb(-places)
        rounded = Decimal(str(float(computed))).quantize(
            quantum, rounding=ROUND_HALF_UP
        )
        match = rounded == Decimal(str(printed))
    value = int(computed) if places == 0 else float(computed)
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": value,
        "match": bool(match),
    }


def read_and_validate_data():
    writers = pd.read_stata(WRITERS_DTA, convert_categoricals=False)
    evaluations = pd.read_stata(EVALUATORS_DTA, convert_categoricals=False)
    raw_writers = pd.read_csv(WRITERS_CSV, dtype=str, keep_default_na=False)
    raw_evaluators = pd.read_csv(EVALUATORS_CSV, dtype=str, keep_default_na=False)

    # Independently verify the exclusions rather than assuming the processed
    # files contain the correct analysis sample.
    page = raw_writers["participant._current_page_name"]
    require(len(raw_writers) == 500, "Writer starter count differs")
    require(int(page.eq("").sum()) == 169, "Pre-consent count differs")
    require(int(page.eq("ConsentDropout").sum()) == 22, "Consent exclusions differ")
    require(int((~page.isin(["", "ConsentDropout", "Finally"])).sum()) == 13,
            "Writer noncompletion count differs")
    eligible = raw_writers.loc[page.eq("Finally")].copy()
    require(len(eligible) == 296, "Writer completion count differs")
    used1 = pd.to_numeric(eligible["follow_up.1.player.used_ai_tool"], errors="coerce")
    used2 = pd.to_numeric(eligible["follow_up.2.player.used_ai_tool"], errors="coerce")
    admitted = eligible["participant.condition"].eq("human") & used1.fillna(used2).eq(1)
    require(int(admitted.sum()) == 3, "Human-only AI-use exclusions differ")
    eligible = eligible.loc[~admitted].copy()
    require(len(eligible) == 293, "Eligible writer count differs")
    require(not writers["human_admitted"].astype(bool).any(),
            "Processed writers contain excluded AI users")
    require(writers["writer_id"].is_unique and writers["story_id"].is_unique,
            "Expected one story per randomized writer")
    require(set(eligible["participant.code"]) == set(writers["writer_id"]),
            "Eligible raw writers differ from processed writers")
    raw_map = eligible.set_index("participant.code")
    processed_map = writers.set_index("writer_id")
    raw_map = raw_map.loc[processed_map.index]
    require(np.array_equal(
        raw_map["participant.condition"].map(RAW_ARMS).to_numpy(),
        processed_map["condition"].to_numpy()
    ), "Writer arm assignments differ between raw and processed data")
    require(np.array_equal(
        raw_map["ai_story_gen.1.player.story_id"].to_numpy(),
        processed_map["story_id"].to_numpy()
    ), "Writer story identifiers differ")
    raw_text = raw_map["ai_story_gen.1.player.story"]
    processed_text = processed_map["writer_story"]
    # Two stories contain typographic apostrophes imported into Stata as
    # UTF-8 bytes decoded as Latin-1. Validate this exact encoding difference;
    # do not modify either text or any stored similarity outcome.
    require(int(raw_text.ne(processed_text).sum()) == 2,
            "Unexpected raw/processed story text differences")
    require(raw_text.map(lambda text: text.encode("utf-8").decode("latin-1"))
            .eq(processed_text).all(),
            "Writer texts differ beyond the documented import encoding")
    require(writers.groupby("condition").size().to_dict() == {1: 95, 2: 100, 3: 98},
            "Processed writer arm counts differ")

    raw_evaluators = raw_evaluators.loc[
        raw_evaluators["participant._current_page_name"].eq("Finally")
    ].copy()
    require(len(raw_evaluators) == 600, "Evaluator completion count differs")
    require(set(raw_evaluators["participant.code"]) == set(evaluations["eval_id"]),
            "Raw and processed evaluator IDs differ")
    parts = []
    for number in range(1, 11):
        prefix = "evaluator." + str(number) + ".player."
        part = pd.DataFrame({
            "eval_id": raw_evaluators["participant.code"],
            "story_id": raw_evaluators[prefix + "story_id"],
            "story_number": number,
        })
        for target, source in ITEMS.items():
            part["eval_" + target] = pd.to_numeric(
                raw_evaluators[prefix + source], errors="coerce"
            )
        parts.append(part.loc[part["story_id"].ne("")])
    raw_long = pd.concat(parts, ignore_index=True)
    require(len(raw_long) == 3600, "Raw evaluator rating count differs")
    compare = raw_long.merge(
        evaluations, on=["eval_id", "story_id", "story_number"],
        how="outer", validate="one_to_one", indicator=True,
        suffixes=("_raw", "_processed"),
    )
    require(compare["_merge"].eq("both").all(), "Raw/processed rating keys differ")
    for name in ITEMS:
        require(compare["eval_" + name + "_raw"].eq(
            compare["eval_" + name + "_processed"]).all(),
            "Raw/processed rating values differ: " + name)

    ratings = evaluations.merge(
        writers[["story_id", "writer_id", "condition", "conditionAI",
                 "used_ai", "writer_topic"]],
        on="story_id", how="inner", validate="many_to_one",
    )
    require(len(evaluations) - len(ratings) == 81, "Rating exclusions differ")
    require(len(ratings) == 3519, "Analyzed rating count differs")
    require(ratings["writer_id"].nunique() == 293, "Rated writer count differs")
    require(ratings["eval_id"].nunique() == 600, "Analyzed evaluator count differs")
    require(ratings.groupby("writer_id").size().value_counts().to_dict()
            == {9: 1, 10: 9, 11: 61, 12: 141, 13: 77, 14: 4},
            "Ratings per story differ from main PDF p. 8")
    require(ratings.groupby("eval_id").size().value_counts().to_dict()
            == {4: 5, 5: 71, 6: 524},
            "Ratings per evaluator differ from main PDF p. 8")
    require(ratings["writer_topic"].eq(ratings["eval_topic"]).all(),
            "Writer/evaluator topic coding differs")

    for outcome, components in INDEX_COMPONENTS.items():
        rebuilt = ratings[components].astype(float).mean(axis=1)
        require(np.allclose(rebuilt, ratings[outcome].astype(float), rtol=0,
                            atol=4e-7), "Stored index does not match its components")
        # Recompute in double precision; the deposit stores these row means
        # as Stata floats. The maximum rounding discrepancy is under 4e-7.
        ratings[outcome] = rebuilt

    columns = [v for v in OUTCOMES.values() if v != "sim_idea"]
    require(ratings[columns].notna().all().all(), "Missing eligible rating outcome")
    require(((ratings[columns] >= 1) & (ratings[columns] <= 9)).all().all(),
            "Rating outside the documented 1..9 scale")
    require(writers["sim_idea"].notna().all(), "Missing story-to-idea outcome")
    ratings = ratings.sort_values(["eval_id", "story_number"]).reset_index(drop=True)
    ratings["story_order"] = ratings.groupby("eval_id").cumcount() + 1
    return writers, ratings


def outcome_for_slug(slug):
    matches = [value for key, value in OUTCOMES.items()
               if slug.startswith("s1_" + key + "_")]
    require(len(matches) == 1, "Unknown or ambiguous estimate: " + slug)
    return matches[0]


def reproduce_paper_model(estimate, writers, ratings):
    slug = estimate["slug"]
    outcome = outcome_for_slug(slug)
    is_similarity = outcome == "sim_idea"
    data = writers if is_similarity else ratings
    adjusted = "_evaluator_" in slug
    combined = "(combined)" in estimate["treatment_arm"]
    design = pd.DataFrame(index=data.index)
    if combined:
        design["combined"] = data["condition"].isin([2, 3]).astype(float)
    else:
        design["one"] = data["condition"].eq(2).astype(float)
        design["five"] = data["condition"].eq(3).astype(float)
    if adjusted:
        if "_order_" in slug:
            design = pd.concat([
                design,
                pd.get_dummies(data["story_order"], prefix="order",
                               drop_first=True, dtype=float)
            ], axis=1)
        if "_topic_" in slug:
            design = pd.concat([
                design,
                pd.get_dummies(data["writer_topic"], prefix="topic",
                               drop_first=True, dtype=float)
            ], axis=1)
        if slug.endswith("_used_ai"):
            design["used_ai"] = data["used_ai"].astype(float)
        response = data[outcome].astype(float)
        # Within transformation reproduces the authors' xtreg, fe slopes.
        # Cluster correction counts slope regressors plus the common constant,
        # excluding absorbed evaluator indicators, as in xtreg with nested FE.
        design = design - design.groupby(data["eval_id"]).transform("mean")
        response = response - response.groupby(data["eval_id"]).transform("mean")
    else:
        response = data[outcome].astype(float)
    design = sm.add_constant(design, has_constant="add")

    if is_similarity:
        fit = sm.OLS(response, design).fit(cov_type="HC1", use_t=True)
    else:
        fit = sm.OLS(response, design).fit(
            cov_type="cluster",
            cov_kwds={"groups": data["eval_id"], "use_correction": True,
                      "df_correction": True},
            use_t=True,
        )

    treat_codes = ARM_CODES[estimate["treatment_arm"]]
    control_codes = ARM_CODES[estimate["control_arm"]]
    treatment = data.loc[data["condition"].isin(treat_codes)]
    control = data.loc[data["condition"].isin(control_codes)]
    reproduced = []
    for name, value in [
        ("n_treatment", treatment["writer_id"].nunique()),
        ("n_control", control["writer_id"].nunique()),
        ("n_total", treatment["writer_id"].nunique() + control["writer_id"].nunique()),
        ("n_units", len(data)),
    ]:
        if estimate.get(name) is not None:
            reproduced.append(check_record(name, estimate[name], value, 0))
    # Main PDF pp. 7-8; Table S1.
    reproduced.append(check_record("full_sample_writers", 293,
                                   data["writer_id"].nunique(), 0))
    if not is_similarity:
        reproduced.append(check_record("n_evaluators", 600,
                                       data["eval_id"].nunique(), 0))

    stats = estimate["stats"]
    coefficient_name = "combined" if combined else (
        "five" if treat_codes == (3,) else "one"
    )
    if control_codes == (2,):
        weights = np.zeros(len(fit.params))
        weights[fit.params.index.get_loc("five")] = 1
        weights[fit.params.index.get_loc("one")] = -1
        contrast = fit.t_test(weights)
        paper_p = float(np.asarray(contrast.pvalue).item())
    else:
        paper_p = float(fit.pvalues[coefficient_name])

    if stats["regression"] is not None:
        regression = stats["regression"]
        reproduced.append(check_record("regression.coef", regression["coef"],
                                       fit.params[coefficient_name],
                                       2 if is_similarity else 3))
        reproduced.append(check_record("regression.se", regression["se"],
                                       fit.bse[coefficient_name], 3))
    for arm_name, arm_rows in [("treatment", treatment), ("control", control)]:
        printed = stats.get(arm_name + "_mean")
        if printed is not None:
            # Only the main-text one-idea usefulness mean and story-to-idea
            # mean use 2 decimals; table intercepts use 3, including 4.810.
            places = 2 if is_similarity or (
                outcome == "eval_useful_index" and
                ((arm_name == "treatment" and treat_codes == (2,)) or
                 (arm_name == "control" and control_codes == (2,)))
            ) else 3
            reproduced.append(check_record(
                arm_name + "_mean", printed,
                arm_rows[outcome].astype(float).mean(), places,
            ))
    if stats.get("control_se") is not None:
        require(not adjusted and control_codes == (1,),
                "Unexpected adjusted constant recorded as arm SE")
        reproduced.append(check_record("control_se", stats["control_se"],
                                       fit.bse["const"], 3))
    if stats.get("control_sd") is not None:
        require(is_similarity, "Unexpected printed rating-level SD")
        reproduced.append(check_record("control_sd", stats["control_sd"],
                                       control[outcome].astype(float).std(ddof=1), 2))
    if stats.get("p_value") is not None:
        reproduced.append(check_record("p_value", stats["p_value"], paper_p))
    if stats.get("test") is not None:
        require(combined and stats["test"]["type"] == "F",
                "Unexpected printed contrast test")
        reproduced.append(check_record("test.value", stats["test"]["value"],
                                       float(fit.fvalue)))
    if stats.get("paper_effect") is not None:
        effect = stats["paper_effect"]
        require(effect["type"] == "other", "Unexpected paper effect scale")
        tm = treatment[outcome].astype(float).mean()
        cm = control[outcome].astype(float).mean()
        reproduced.append(check_record("paper_effect.value", effect["value"],
                                       100 * (tm - cm) / cm, 1))
    if is_similarity:
        # Check the finer precision printed in supplementary Table S11 too.
        table_coefficient = 4.288 if treat_codes == (2,) else 4.105
        reproduced.append(check_record("table_s11.regression.coef",
                                       table_coefficient,
                                       fit.params[coefficient_name], 3))
        reproduced.append(check_record("table_s11.control_mean", 82.850,
                                       control[outcome].astype(float).mean(), 3))
    return reproduced, outcome, data, treat_codes, control_codes


def participant_contrast(data, outcome, treat_codes, control_codes):
    # This function is called only after the estimate passes reproduction.
    people = (
        data.groupby(["writer_id", "condition"], as_index=False)[outcome]
        .mean()
    )
    require(people["writer_id"].is_unique, "Writer assigned to multiple arms")
    people = people.loc[people["condition"].isin(treat_codes + control_codes)].copy()
    people[outcome] = people[outcome].astype(float)
    indicator = people["condition"].isin(treat_codes).astype(float)
    design = pd.DataFrame({"const": 1.0, "treatment": indicator}, index=people.index)
    fit = sm.OLS(people[outcome], design).fit(cov_type="HC2")
    treatment = people.loc[indicator.eq(1), outcome]
    control = people.loc[indicator.eq(0), outcome]
    difference = float(treatment.mean() - control.mean())
    se = float(fit.bse["treatment"])
    require(math.isclose(float(fit.params["treatment"]), difference,
                         rel_tol=1e-12, abs_tol=1e-12),
            "OLS slope differs from the participant mean contrast")
    # For an intercept-plus-binary-indicator model, HC2 equals the square root
    # of the sum of the two sample-variance-over-n terms.
    independent_se = math.sqrt(
        float(treatment.var(ddof=1)) / len(treatment)
        + float(control.var(ddof=1)) / len(control)
    )
    require(math.isclose(se, independent_se, rel_tol=1e-10, abs_tol=1e-12),
            "HC2 differs from its independent two-arm variance identity")
    return {
        "n_treatment": int(len(treatment)),
        "n_control": int(len(control)),
        "treatment_mean": float(treatment.mean()),
        "treatment_sd": float(treatment.std(ddof=1)),
        "control_mean": float(control.mean()),
        "control_sd": float(control.std(ddof=1)),
        "difference": difference,
        "difference_se": se,
        "se_type": "HC2",
        "n_clusters": None,
    }


def result_notes(estimate, outcome):
    common = (
        "Between-person randomization of writers; round=all. Retained all assigned "
        "AI-arm writers, including those who requested no idea. Raw CSV exclusions "
        "were independently verified: 500 writer starters, 169 before consent, "
        "22 consent refusals, 13 noncompleters, and 3 Human-only AI users excluded; "
        "293 eligible writers remain. Arm codes: 1=Human-only, 2=one idea, 3=five "
        "ideas. SDs use n-1. Computed difference is treatment minus control in "
        "the original units, without reversing the sign. HC2 uses OLS with an "
        "intercept and the treatment indicator on exactly the two contrasted "
        "arms; SE also checked against sqrt(sd_t^2/n_t + sd_c^2/n_c). "
    )
    if outcome == "sim_idea":
        detail = (
            "Outcome sim_idea in creators.dta is the authors' saved 100*cosine "
            "similarity of each writer's story to its actual first available or "
            "randomly assigned same-topic AI idea. It has one value per writer. "
            "The posted code names text-embedding-ada-002; original embeddings "
            "were not regenerated. Two saved writer texts contain a verified "
            "UTF-8-as-Latin-1 apostrophe encoding difference from the raw CSV; "
            "all 293 texts agree after that import-encoding transformation. "
            "The saved similarity scores are preserved without re-embedding. "
            "This is the extracted with_ai/other anchoring "
            "outcome, not diversity of a set of stories. The paper's three-arm "
            "OLS and HC1 robust SEs were reproduced before computing the requested "
            "two-arm HC2 contrast. Both main-text and finer supplementary Table "
            "S11 coefficients, the control mean, and Table S12 control SD match. "
            "Sources: main PDF p. 5; supplement pp. 5, 10, 12. "
        )
    else:
        detail = (
            "Outcome " + outcome + ". All 12 item ratings and the row identifiers "
            "in evaluators_stories.dta were verified against the raw CSV. Keeping "
            "completed evaluators gives 3600 ratings; joining the eligible writers "
            "on story_id removes 81 and leaves 3519 ratings by 600 evaluators. "
            "Novelty and usefulness indices are recomputed as the arithmetic "
            "means of their three component items in double precision; deposited "
            "Stata floats differ by at most 3.18e-7. The tt_badly_written raw field "
            "is the final study's well-written question, as explained in the "
            "authors' processing comments; no reversal is applied. Reproduced "
            "statistics use the paper's individual-rating weighting and evaluator "
            "clustered uncertainty. Computed statistics instead give each writer "
            "one value: the average of all ratings of that writer's single story. "
            "Unequal numbers of ratings per writer can therefore make computed "
            "arm means and differences differ from reproduced rating-level values. "
            "Sources: main PDF pp. 3, 7-8; supplement Tables S1, S3, S4, S6, S13. "
        )
    if "_evaluator_" in estimate["slug"]:
        detail += (
            "This slug's Table S4 specification is reproduced by removing "
            "evaluator means, adding the specified order/topic/use indicators, "
            "and clustering by evaluator. Order is numbered consecutively after "
            "the 81 exclusions. The computed block is the brief's unadjusted "
            "writer-level contrast, not the adjusted coefficient; it intentionally "
            "equals the corresponding main-specification computed block. "
        )
        if estimate["slug"].endswith("_used_ai"):
            detail += "Voluntary AI use is a post-randomization covariate only in the reproduction model. "
    if "(combined)" in estimate["treatment_arm"]:
        detail += (
            "The combined treatment contains all 198 AI-arm writers and is "
            "weighted by writers, not by an equal-weight average of arm means. "
        )
    if estimate["control_arm"] == "Human with one GenAI idea":
        detail += (
            "The five-versus-one reproduction checks the one-idea mean 5.21, "
            "the 5.1 percent gain, and the p=0.0012 contrast from the full "
            "three-arm model. "
        )
    return common + detail + (
        "Comparisons share writers and controls; repeated slugs/specifications "
        "are not independent samples. Author programs were read only as text."
    )


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    require(extraction["cid"] == "c006", "Wrong extraction")
    writers, ratings = read_and_validate_data()
    output = {
        "cid": "c006",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in DATA_FILES],
        "results": [],
        "skipped": [],
    }
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        if estimate["question"] == "across_people":
            output["skipped"].append({"slug": slug, "reason": SET_OUTCOME_REASON})
            continue
        reproduced, outcome, data, treatment, control = reproduce_paper_model(
            estimate, writers, ratings
        )
        failed = [r for r in reproduced if not r["match"]]
        if failed:
            # No participant-level summary is calculated for an unreproduced
            # estimate. Retain the failed printed/computed checks for diagnosis.
            output["results"].append({
                "slug": slug, "round": "all", "reproduced": reproduced,
                "computed": None,
                "notes": "Reproduction failed; no participant-level statistics "
                         "computed. Differences: " + json.dumps(failed, ensure_ascii=True),
            })
            continue
        computed = participant_contrast(data, outcome, treatment, control)
        output["results"].append({
            "slug": slug,
            "round": "all",
            "reproduced": reproduced,
            "computed": computed,
            "notes": result_notes(estimate, outcome),
        })

    expected = {e["slug"] for e in extraction["estimates"]}
    actual = [r["slug"] for r in output["results"] + output["skipped"]]
    require(set(actual) == expected and len(actual) == len(expected),
            "Estimates missing or duplicated")
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        confirmed = json.load(fh)
    require(confirmed == output, "Written JSON does not round-trip")
    summary = {
        "cid": "c006",
        "n_results": len(output["results"]),
        "n_reproduced": sum(
            r["computed"] is not None and all(c["match"] for c in r["reproduced"])
            for r in output["results"]
        ),
        "n_skipped": len(output["skipped"]),
    }
    print(json.dumps(summary))
    for result in output["results"]:
        if result["computed"] is None:
            print(json.dumps({"slug": result["slug"],
                              "failed": [c for c in result["reproduced"]
                                         if not c["match"]]}))


if __name__ == "__main__":
    main()
