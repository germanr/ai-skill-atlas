"""Independent analysis B of c043; run with python -I -B B.py.

Only B.json is written. All source paths are absolute. Deposited workbooks
are read as data, never executed. No other analyst's files are accessed.

Reproduction uses the authors' participant-level model workbooks. The new
estimates follow the brief's explicit aggregation rule: average both posted
ratings of each idea, then average ideas within each participant. These two
sources differ for one participant in Experiment 2; that discrepancy is
preserved and disclosed, rather than silently replacing either source.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import math
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats


WORKSPACE = Path(
    "C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening"
)
DATA_ROOT = Path("D:/projects/ai-skill-atlas/creativity-data/osf-9ckra")
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
SCRIPT = WORKSPACE / "analysis/c043/B.py"
OUTPUT = WORKSPACE / "analysis/c043/B.json"
EXTRACTION = WORKSPACE / "extraction/c043.json"
READ_FILES = []


def manifest_hashes(obj):
    result = {}
    if isinstance(obj, dict):
        if isinstance(obj.get("path"), str) and "sha256" in obj:
            result[str(Path(obj["path"]).resolve()).casefold()] = obj["sha256"]
        for value in obj.values():
            result.update(manifest_hashes(value))
    elif isinstance(obj, list):
        for value in obj:
            result.update(manifest_hashes(value))
    return result


def read_workbook(path, expected_hashes):
    """Read cached cell values using openpyxl; never evaluate formulas."""
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = expected_hashes[str(path.resolve()).casefold()]
    assert actual_hash == expected, f"Source hash mismatch: {path}"
    READ_FILES.append(path.as_posix())
    return (
        pd.read_excel(path, sheet_name="Sheet1", engine="openpyxl")
        .dropna(how="all")
        .dropna(axis=1, how="all")
    )


def participant_id(value):
    if not isinstance(value, str):
        return None
    # NFKC handles the full-width opening parenthesis in Exp2_survey.xlsx.
    value = unicodedata.normalize("NFKC", value).strip()
    return value[3:] + "C" if value.startswith("(C)") else value


def rating_average(frame, participant_ids, minimum, maximum):
    frame = frame.copy()
    frame["id"] = frame["user_name"].map(participant_id)
    rating_cols = [
        column for column in frame.columns
        if column.replace(" ", "") in ("Rating1", "Rating2")
    ]
    assert len(rating_cols) == 2
    frame[rating_cols] = frame[rating_cols].apply(pd.to_numeric, errors="coerce")
    included = frame["id"].isin(participant_ids)
    # Partner-supplied ideas in the fixation files have no participant ratings.
    assert frame.loc[~included, rating_cols].isna().all().all()
    participant_rows = frame.loc[included].copy()
    assert participant_rows[rating_cols].notna().all().all()
    assert participant_rows[rating_cols].ge(minimum).all().all()
    assert participant_rows[rating_cols].le(maximum).all().all()
    participant_rows["idea_score"] = participant_rows[rating_cols].mean(axis=1)
    averaged = participant_rows.groupby("id")["idea_score"].mean()
    assert set(averaged.index) == set(participant_ids)
    return averaged, participant_rows, int((~included).sum())


def factorial_anova(model, arm, outcome):
    frame = pd.DataFrame({
        "y": outcome,
        "treatment": model[arm],
        "task": model["TC"],
    })
    fit = smf.ols(
        "y ~ C(treatment, Sum) * C(task, Sum)", data=frame
    ).fit()
    table = sm.stats.anova_lm(fit, typ=3)
    row = table.loc["C(treatment, Sum)"]
    return {
        "F": float(row["F"]),
        "p": float(row["PR(>F)"]),
        "df_numerator": int(row["df"]),
        "df_denominator": int(fit.df_resid),
        "partial_eta_squared": float(
            row["sum_sq"] / (row["sum_sq"] + fit.ssr)
        ),
    }


def adjusted_model(model, arm, outcome):
    continuous = model[["CF", "IS"]].copy()
    continuous["C"] = outcome
    standardized = (continuous - continuous.mean()) / continuous.std(ddof=1)
    design = sm.add_constant(pd.concat(
        [model[[arm]], standardized[["CF", "IS"]]], axis=1
    ))
    return sm.OLS(standardized["C"], design).fit()


def load_experiment(exp, expected_hashes):
    folder = DATA_ROOT / f"Exp{exp}"
    arm = "PT" if exp == 1 else "NC"
    model = read_workbook(folder / f"Exp{exp}_model.xlsx", expected_hashes)
    creativity = read_workbook(
        folder / f"Exp{exp}_creativity_rating.xlsx", expected_hashes
    )
    fixation = read_workbook(
        folder / f"Exp{exp}_fixation_rating.xlsx", expected_hashes
    )
    survey = read_workbook(folder / f"Exp{exp}_survey.xlsx", expected_hashes)
    ideas = read_workbook(
        folder / ("Exp1_idea.xlsx" if exp == 1 else "Exp2_idea .xlsx"),
        expected_hashes,
    )
    model = model.set_index("user_name")
    assert model.index.is_unique
    assert model[[arm, "TC", "C", "CF", "IS"]].notna().all().all()
    assert set(model[arm]) == {0, 1} and set(model["TC"]) == {0, 1}
    assert ideas[["idea", "user_name"]].reset_index(drop=True).equals(
        creativity[["idea", "user_name"]].reset_index(drop=True)
    )

    averaged, rating_rows, excluded_creativity = rating_average(
        creativity, model.index, 1, 5
    )
    fixation_average, _, excluded_fixation = rating_average(
        fixation, model.index, 0, 2
    )
    assert excluded_creativity == 0
    assert np.allclose(model["CF"], fixation_average.reindex(model.index),
                       rtol=0, atol=1e-12)
    averaged = averaged.reindex(model.index)
    mismatch = (model["C"] - averaged).abs() > 1e-12
    expected_mismatches = [] if exp == 1 else ["NAI31C"]
    assert list(model.index[mismatch]) == expected_mismatches
    if exp == 2:
        assert math.isclose(averaged.loc["NAI31C"], 57 / 28, abs_tol=1e-12)
        assert math.isclose(model.loc["NAI31C", "C"], 29 / 14, abs_tol=1e-12)

    # Survey rows without IDs are summary statistics, not extra participants.
    survey = survey.loc[survey["ID"].notna()].copy()
    survey["id"] = survey["ID"].map(participant_id)
    item_cols = [f"IS{i}" for i in range(1, 6)]
    assert survey[item_cols].notna().all().all()
    survey["survey_IS"] = survey[item_cols].mean(axis=1)
    unambiguous = survey.loc[~survey["id"].duplicated(keep=False)].set_index("id")
    joined = model.join(unambiguous[["survey_IS"]])
    observed = joined["survey_IS"].notna()
    assert np.allclose(joined.loc[observed, "IS"],
                       joined.loc[observed, "survey_IS"], rtol=0, atol=1e-12)
    unresolved = list(joined.index[~observed])
    assert unresolved == (["HH39C", "HH40C"] if exp == 1 else [])
    # Do not repair the duplicate HH39C survey ID by guessing. The deposited
    # model file separately identifies both people and their mediator scores.

    cell_counts = model.groupby([arm, "TC"]).size().to_dict()
    assert all(rating_rows.groupby("id")["room_name"].nunique() == 1)
    rooms = rating_rows.merge(model[["TC"]], left_on="id", right_index=True)
    # Some copies of the VR prompt append a space and an ideographic period.
    rooms["room_key"] = rooms["room_name"].str.rstrip(" .\u3002")
    assert all(rooms.groupby("TC")["room_key"].nunique() == 1)
    assert rooms["room_key"].nunique() == 2

    return {
        "exp": exp,
        "arm": arm,
        "model": model,
        "ratings": averaged,
        "rating_rows": len(rating_rows),
        "excluded_partner_rows": excluded_fixation,
        "cell_counts": cell_counts,
        "paper_anova": factorial_anova(model, arm, model["C"]),
        "ratings_anova": factorial_anova(model, arm, averaged),
        "paper_adjusted": adjusted_model(model, arm, model["C"]),
        "ratings_adjusted": adjusted_model(model, arm, averaged),
    }


def comparison(statistic, printed, computed, digits=3):
    computed = float(computed) if digits else int(computed)
    quantum = Decimal(1).scaleb(-digits)
    matches = (
        Decimal(str(computed)).quantize(quantum, rounding=ROUND_HALF_UP)
        == Decimal(str(printed))
    )
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(matches),
    }


def count_checks(data, cohort_estimate, adjusted=False):
    model, arm = data["model"], data["arm"]
    prefix = "experiment_" if adjusted else ""
    return [
        comparison(prefix + "n_treatment", cohort_estimate["n_treatment"],
                   (model[arm] == 1).sum(), 0),
        comparison(prefix + "n_control", cohort_estimate["n_control"],
                   (model[arm] == 0).sum(), 0),
        comparison(prefix + "n_total", cohort_estimate["n_total"], len(model), 0),
    ]


def pooled_checks(data, estimate):
    checks = count_checks(data, estimate)
    model, arm = data["model"], data["arm"]
    printed = estimate["stats"]
    if data["exp"] == 1:
        treatment = model.loc[model[arm] == 1, "C"]
        control = model.loc[model[arm] == 0, "C"]
        for name, actual, digits in [
            ("treatment_mean", treatment.mean(), 2),
            ("treatment_sd", treatment.std(ddof=1), 3),
            ("control_mean", control.mean(), 3),
            ("control_sd", control.std(ddof=1), 3),
        ]:
            checks.append(comparison(name, printed[name], actual, digits))
        test = stats.ttest_ind(control, treatment, equal_var=True)
        checks += [
            comparison("test.t_human_minus_llm", printed["test"]["value"],
                       test.statistic),
            comparison("test.df", printed["test"]["df"], test.df, 0),
            comparison("p_value", printed["p_value"], test.pvalue),
        ]
    else:
        anova = data["paper_anova"]
        checks += [
            comparison("test.F_response_type", printed["test"]["value"], anova["F"]),
            comparison("test.df_numerator", printed["test"]["df"][0],
                       anova["df_numerator"], 0),
            comparison("test.df_denominator", printed["test"]["df"][1],
                       anova["df_denominator"], 0),
            comparison("p_value", printed["p_value"], anova["p"]),
            comparison("partial_eta_squared", printed["paper_effect"]["value"],
                       anova["partial_eta_squared"]),
        ]
        # No pooled means are printed for S2. These four printed cell means
        # provide an additional signed check of both arm and task mappings.
        # They are validation checks, not added subgroup results.
        means = model.groupby([arm, "TC"])["C"].mean()
        for label, cell, value in [
            ("cell_mean_batch_simple_PDF_p7", (0, 0), 2.466),
            ("cell_mean_batch_complex_PDF_p7", (0, 1), 2.139),
            ("cell_mean_constrained_simple_PDF_p7", (1, 0), 2.171),
            ("cell_mean_constrained_complex_PDF_p7", (1, 1), 2.520),
        ]:
            checks.append(comparison(label, value, means.loc[cell]))
    return checks


def adjusted_checks(data, estimate, cohort_estimate):
    checks = count_checks(data, cohort_estimate, adjusted=True)
    fit, arm = data["paper_adjusted"], data["arm"]
    values = (
        (-0.222, 0.401, 0.113, 8.470) if data["exp"] == 1
        else (-0.259, 0.256, 0.126, 9.595)
    )
    checks += [
        comparison("regression.coef", estimate["stats"]["regression"]["coef"],
                   fit.params[arm]),
        comparison("model4.fixation_coefficient", values[0], fit.params["CF"]),
        comparison("model4.inspiration_coefficient", values[1], fit.params["IS"]),
        comparison("model4.r_squared", values[2], fit.rsquared),
        comparison("model4.F", values[3], fit.fvalue),
    ]
    assert fit.nobs == len(data["model"])
    return checks


def requested_contrast(data):
    """Only called after all essential published-statistic checks pass."""
    model, arm, outcome = data["model"], data["arm"], data["ratings"]
    treatment = outcome.loc[model[arm] == 1]
    control = outcome.loc[model[arm] == 0]
    design = sm.add_constant(model[[arm]].astype(float))
    fit = sm.OLS(outcome, design).fit(cov_type="HC2")
    difference = float(treatment.mean() - control.mean())
    expected_se = math.sqrt(
        treatment.var(ddof=1) / len(treatment)
        + control.var(ddof=1) / len(control)
    )
    assert math.isclose(float(fit.params[arm]), difference, abs_tol=1e-12)
    assert math.isclose(float(fit.bse[arm]), expected_se, abs_tol=1e-12)
    return {
        "n_treatment": int(len(treatment)),
        "n_control": int(len(control)),
        "treatment_mean": float(treatment.mean()),
        "treatment_sd": float(treatment.std(ddof=1)),
        "control_mean": float(control.mean()),
        "control_sd": float(control.std(ddof=1)),
        "difference": difference,
        "difference_se": float(fit.bse[arm]),
        "se_type": "HC2",
        "n_clusters": None,
    }


def provenance_notes(data, adjusted):
    exp, arm, model = data["exp"], data["arm"], data["model"]
    mapping = (
        "PT=1 is LLM partner (HAI), PT=0 is human partner (HH)"
        if exp == 1 else
        "NC=1 is constrained-responsive LLM (CAI), NC=0 is batch-responsive LLM (NAI)"
    )
    notes = [
        f"All five Exp{exp} source workbooks use Sheet1; their SHA-256 hashes "
        "were verified against the supplied manifest. " + mapping + ". "
        "TC=0 is the simple tire task and TC=1 is the complex VR task. "
        "The model workbook uses a trailing C for complex-task IDs; the rating "
        "workbooks use a leading (C). These labels were normalized before joining. "
        "The two task conditions contain distinct randomized people, not paired rounds. "
        "Both treatment task cells have 52 people and both control task cells have 50.",
        f"The creativity-rating file has {data['rating_rows']} rated participant ideas "
        "with two observed ratings each. Its idea texts and participant IDs agree "
        "with the separate idea workbook. Empty spreadsheet rows are discarded. "
        "No participants, rated ideas, or ratings are excluded. The new outcome "
        "is the mean of the two ratings per idea, then the mean across each person's "
        "ideas, giving each person equal weight. All SDs use n-1. Computed values "
        "are in raw 1-5 creativity units; difference is treatment minus control. "
        "Its SE is the treatment coefficient's HC2 SE in OLS with an intercept "
        "and treatment indicator only. Randomization was individual, so no "
        "cluster or paired correction is used. There is no first-round result.",
        f"Fixation averages rebuilt from the two expert ratings agree with model CF "
        f"for every participant; {data['excluded_partner_rows']} partner-idea rows "
        "in that workbook carry no participant ratings and are excluded from "
        "the mediator audit. The five survey IS items average to model IS for "
        + ("all 204 participants after normalizing full-width parentheses."
           if exp == 2 else
           "the 202 participants with unambiguous survey IDs. The survey repeats "
           "(C)HH39 and omits (C)HH40; neither survey row is reassigned. The "
           "complete model table supplies IS=2.4 for HH39C and IS=2.0 for HH40C. "
           "This survey-label issue causes no exclusion from the model or ratings."),
    ]
    if exp == 1:
        notes.append(
            "The model C scores agree with independently rebuilt participant "
            "rating averages to floating-point precision. Main PDF p. 5 arm "
            "means, SDs, t and p reproduce at their printed precision; Table S5 "
            "(supplement PDF p. 10) supplies the group counts. The published t "
            "is human minus LLM, whereas the requested difference is LLM minus human. "
            "The paper does not identify the standardizer of its d or the estimand "
            "of its confidence interval; neither is used to calculate the new SE."
        )
    else:
        author_control = model.loc[model[arm] == 0, "C"].mean()
        notes.append(
            "Reproduction and new aggregation use explicitly distinguished sources: "
            "the published results reproduce from Exp2_model.xlsx C, but its "
            "NAI31C score is 2.07142857142857, while averaging both raters across "
            "that person's 14 ideas in Exp2_creativity_rating.xlsx gives "
            "2.0357142857142856. Excel rows 449-461 have ratings (2,2), and row "
            "462 has (3,2). All other 203 model C values agree with the rebuilt "
            "averages. The discrepancy is not resolved by changing any source "
            "or guessing a rating. The reproduced list uses the deposited model "
            "C that generated the paper; computed uses the explicitly requested "
            "average of the posted ratings. "
            f"The author-model control mean is {author_control:.15g}; the new "
            "control mean is lower by 1/2800. With author C, the sum-coded "
            f"factorial ANOVA gives F={data['paper_anova']['F']:.15g}, matching "
            "0.811 (main PDF p. 6). Rebuilt ratings give "
            f"F={data['ratings_anova']['F']:.15g}, which does not round to 0.811. "
            "The four printed cell means on main PDF p. 7 provide validation "
            "of task and treatment coding, not additional subgroup estimates. "
            "The pooled counts are printed in Table S6 (supplement PDF p. 11)."
        )
    if adjusted:
        fit = data["paper_adjusted"]
        sd = model[["C", "CF", "IS"]].std(ddof=1)
        notes.append(
            f"Supplement PDF p. 12, Table S{6 + exp}, Model 4 is reproduced "
            "as OLS of standardized C on the unchanged 0/1 treatment indicator "
            "and standardized CF and IS, with an intercept and no task term. "
            "Each continuous variable is centered and divided by its full-sample "
            f"SD with n-1: SD(C)={sd['C']:.15g}, SD(CF)={sd['CF']:.15g}, "
            f"SD(IS)={sd['IS']:.15g}. This standardization is inferred from the "
            "joint reproduction of all three printed coefficients and model R2 "
            "and F; it is not explicitly documented in the paper. All 204 model "
            "rows have observed outcome, treatment and both mediators, so the "
            "complete-case model has 104 treatment and 100 control people. "
            "The experiment count checks compare to the demographic table, "
            "not a model-specific count printed in Model 4, which has no such "
            "count. The table calls its SE bootstrapped with 10,000 replications, "
            "but supplies no seed or resampling specification; that bootstrap "
            "SE is not claimed as reproduced. For orientation only, conventional "
            f"OLS gives treatment SE={float(fit.bse[arm]):.15g}, which rounds "
            "to the table's SE. The computed object reports the brief's "
            "unadjusted raw arm contrast and HC2 SE, not the mediator-adjusted "
            "direct coefficient; it intentionally shares the sample and computed "
            "values of the corresponding pooled record and is not independent evidence."
        )
        if exp == 2:
            notes.append(
                "Using the rebuilt ratings instead of author-model C in the "
                "standardized adjusted equation gives treatment coefficient "
                f"{float(data['ratings_adjusted'].params[arm]):.15g}, which rounds "
                "to 0.030 rather than the printed 0.029. The printed 0.029 is "
                "reproduced with the original model C, as recorded in reproduced."
            )
    return " ".join(notes)


def main():
    with MANIFEST.open(encoding="utf-8") as handle:
        expected_hashes = manifest_hashes(json.load(handle))
    with EXTRACTION.open(encoding="utf-8") as handle:
        extraction = json.load(handle)
    experiments = {
        exp: load_experiment(exp, expected_hashes) for exp in (1, 2)
    }
    cohorts = {
        row["study_id"]: row for row in extraction["estimates"]
        if not row["slug"].endswith("_direct_adjusted")
    }
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        exp = int(estimate["study_id"][1:])
        data = experiments[exp]
        adjusted = estimate["slug"].endswith("_direct_adjusted")
        checks = (
            adjusted_checks(data, estimate, cohorts[estimate["study_id"]])
            if adjusted else pooled_checks(data, estimate)
        )
        notes = provenance_notes(data, adjusted)
        if all(check["match"] for check in checks):
            computed = requested_contrast(data)
        else:
            computed = None
            failed = [check for check in checks if not check["match"]]
            reason = "Published-statistic reproduction failed: " + json.dumps(failed)
            skipped.append({"slug": estimate["slug"], "reason": reason})
            notes += " No new effect computed. " + reason
        results.append({
            "slug": estimate["slug"],
            "round": "all",
            "reproduced": checks,
            "computed": computed,
            "notes": notes,
        })
    obj = {
        "cid": "c043",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": READ_FILES,
        "results": results,
        "skipped": skipped,
    }
    # Reject any nonfinite numbers rather than writing nonstandard JSON.
    json.dumps(obj, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as handle:
        parsed = json.load(handle)
    assert parsed == obj
    print(json.dumps({
        "cid": "c043",
        "n_results": len(results),
        "n_reproduced": sum(
            all(check["match"] for check in result["reproduced"])
            for result in results
        ),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
