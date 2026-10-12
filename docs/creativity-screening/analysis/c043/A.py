"""c043, analyst A. Run with python -I and write only the adjacent A.json.

Reproduce the publication using the deposited participant analysis workbooks.
Then compute the requested raw participant statistics from the idea ratings,
averaging the two raters and then all ideas within each participant. These
steps are deliberately separate: Exp2_model.xlsx disagrees with its rating
workbook for one participant. Both versions and their consequences are
documented in the JSON notes; no source value is altered or guessed.

The adjusted records are reproduced on their standardized analysis scale.
Their computed fields contain the unadjusted raw contrast required by the
brief, not the mediator-adjusted coefficient. They duplicate the pooled
records' sample/outcome and must not be treated as independent effects.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from scipy import stats
import statsmodels.api as sm


BASE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
ROOT = Path(r"D:/projects/ai-skill-atlas/creativity-data/osf-9ckra")
MANIFEST = ROOT.parent / "manifest.json"
EXTRACTION = BASE / "extraction/c043.json"
SCRIPT = BASE / "analysis/c043/A.py"
OUTPUT = BASE / "analysis/c043/A.json"
DATA_FILES = [
    ROOT / "Exp1/Exp1_survey.xlsx",
    ROOT / "Exp1/Exp1_model.xlsx",
    ROOT / "Exp1/Exp1_creativity_rating.xlsx",
    ROOT / "Exp1/Exp1_idea.xlsx",
    ROOT / "Exp1/Exp1_fixation_rating.xlsx",
    ROOT / "Exp2/Exp2_survey.xlsx",
    ROOT / "Exp2/Exp2_model.xlsx",
    ROOT / "Exp2/Exp2_fixation_rating.xlsx",
    ROOT / "Exp2/Exp2_creativity_rating.xlsx",
    ROOT / "Exp2/Exp2_idea .xlsx",
]


def read_workbook(path):
    """Read cached cell data only; never evaluate workbook formulas or links."""
    workbook = openpyxl.load_workbook(
        path, read_only=True, data_only=True, keep_links=False
    )
    try:
        assert workbook.sheetnames == ["Sheet1"]
        rows = list(workbook["Sheet1"].values)
    finally:
        workbook.close()
    header = rows[0]
    columns = [(i, str(v).strip()) for i, v in enumerate(header) if v is not None]
    values = [[row[i] for i, _ in columns] for row in rows[1:]]
    frame = pd.DataFrame(values, columns=[name for _, name in columns])
    return frame.dropna(how="all").reset_index(drop=True)


def normalize_id(value):
    if not isinstance(value, str):
        return value
    value = value.strip().replace("\uff08", "(").replace("\uff09", ")")
    # Complex-task IDs are prefixed in ratings/surveys and suffixed in models.
    return value[3:] + "C" if value.startswith("(C)") else value


def check(statistic, printed, computed, decimals=3):
    computed = float(computed)
    if decimals == 0:
        computed = int(computed) if computed.is_integer() else computed
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(round(computed, decimals) == round(printed, decimals)),
    }


def factorial_fit(frame, outcome, treatment):
    x = pd.DataFrame({
        "const": 1.0,
        "treatment": frame[treatment],
        "complex_task": frame["TC"],
        "interaction": frame[treatment] * frame["TC"],
    }, index=frame.index)
    fit = sm.OLS(frame[outcome], x, missing="raise").fit()
    # Type III / equal-weight main effect in the full 2 x 2 model.
    # Both arms have equal numbers in their two task cells, so this equals
    # the pooled arm difference; its conventional factorial SE differs.
    test = fit.t_test([0.0, 1.0, 0.0, 0.5])
    return fit, float(np.asarray(test.tvalue).item() ** 2), float(test.pvalue)


def direct_fit(frame, outcome, treatment):
    continuous = frame[[outcome, "CF", "IS"]]
    z = (continuous - continuous.mean()) / continuous.std(ddof=1)
    x = sm.add_constant(z[["CF", "IS"]].assign(treatment=frame[treatment]))
    return sm.OLS(z[outcome], x, missing="raise").fit()


def load_experiment(exp):
    folder = ROOT / f"Exp{exp}"
    treatment = "PT" if exp == 1 else "NC"
    model = read_workbook(folder / f"Exp{exp}_model.xlsx")
    assert model["user_name"].is_unique
    assert not model.isna().any().any()
    model = model.set_index("user_name")
    assert set(model[treatment]) == {0, 1} and set(model["TC"]) == {0, 1}

    ratings = read_workbook(folder / f"Exp{exp}_creativity_rating.xlsx")
    idea_name = "Exp1_idea.xlsx" if exp == 1 else "Exp2_idea .xlsx"
    ideas = read_workbook(folder / idea_name)
    idea_fields = ["idea", "user_name", "created_at", "room_name"]
    assert ratings[idea_fields].equals(ideas[idea_fields])
    assert not ratings[idea_fields].isna().any().any()
    assert not ratings.duplicated(idea_fields).any()
    rating_columns = ["Rating1", "Rating2"] if exp == 1 else ["Rating 1", "Rating 2"]
    assert not ratings[rating_columns].isna().any().any()
    assert ratings[rating_columns].isin([1, 2, 3, 4, 5]).all().all()
    ratings["pid"] = ratings["user_name"].map(normalize_id)
    ratings["idea_score"] = ratings[rating_columns].mean(axis=1)
    participant = ratings.groupby("pid")["idea_score"].agg(["mean", "size"])
    assert set(participant.index) == set(model.index)
    model["C_from_ratings"] = participant["mean"].reindex(model.index)
    model["n_ideas"] = participant["size"].reindex(model.index)
    joined_ratings = ratings.join(model[[treatment, "TC"]], on="pid")
    assert joined_ratings.loc[joined_ratings.TC == 1, "room_name"].str.contains("VR").all()
    assert not joined_ratings.loc[joined_ratings.TC == 0, "room_name"].str.contains("VR").any()

    fixation = read_workbook(folder / f"Exp{exp}_fixation_rating.xlsx")
    fixation["pid"] = fixation["user_name"].map(normalize_id)
    fixation_columns = ["Rating1", "Rating2"]
    fixation[fixation_columns] = fixation[fixation_columns].apply(pd.to_numeric)
    # Partner messages have no ratings; no participant idea is discarded.
    scored_fixation = fixation[fixation["pid"].isin(model.index)].copy()
    assert not scored_fixation[fixation_columns].isna().any().any()
    assert scored_fixation[fixation_columns].isin([0, 1, 2]).all().all()
    assert len(scored_fixation) == len(ratings)
    scored_fixation["idea_score"] = scored_fixation[fixation_columns].mean(axis=1)
    cf = scored_fixation.groupby("pid")["idea_score"].mean()
    assert set(cf.index) == set(model.index)
    assert np.allclose(model["CF"], cf.reindex(model.index), atol=1e-12, rtol=0)

    survey = read_workbook(folder / f"Exp{exp}_survey.xlsx")
    summary_rows = int(survey.ID.isna().sum())
    survey = survey[survey.ID.notna()].copy()
    survey["pid"] = survey.ID.map(normalize_id)
    is_columns = [f"IS{i}" for i in range(1, 6)]
    assert not survey[is_columns].isna().any().any()
    survey["IS_from_items"] = survey[is_columns].mean(axis=1)
    missing_survey_ids = sorted(set(model.index) - set(survey.pid))
    duplicate_survey_ids = sorted(survey.loc[survey.pid.duplicated(False), "pid"].unique())
    assert set(survey.pid).issubset(model.index)
    for pid, group in survey.groupby("pid"):
        assert np.isclose(group.IS_from_items, model.loc[pid, "IS"], atol=1e-12).any()
    if exp == 2:
        survey_joined = survey.join(model[treatment], on="pid")
        manipulation_means = survey_joined.groupby(treatment)["Perceived output constraints"].mean()
        assert round(manipulation_means[0], 3) == 4.040
        assert round(manipulation_means[1], 3) == 3.058

    mismatch = model.loc[
        ~np.isclose(model.C, model.C_from_ratings, atol=1e-12, rtol=0),
        ["C", "C_from_ratings", "n_ideas"],
    ]
    audit = {
        "n_ideas": len(ratings),
        "model_rating_mismatch": mismatch.to_dict(orient="index"),
        "summary_rows": summary_rows,
        "missing_survey_ids": missing_survey_ids,
        "duplicate_survey_ids": duplicate_survey_ids,
    }
    return model, treatment, audit


def reproduce(estimate, frame, treatment, pooled_estimate, study):
    is_direct = estimate["slug"].endswith("direct_adjusted")
    count_prefix = "experiment_" if is_direct else ""
    checks = [
        check(count_prefix + "n_treatment", pooled_estimate["n_treatment"], (frame[treatment] == 1).sum(), 0),
        check(count_prefix + "n_control", pooled_estimate["n_control"], (frame[treatment] == 0).sum(), 0),
        check(count_prefix + "n_total", study["n_analyzed"], len(frame), 0),
    ]
    printed = estimate["stats"]
    if is_direct:
        fit = direct_fit(frame, "C", treatment)
        checks.append(check("regression.coef", printed["regression"]["coef"], fit.params["treatment"]))
        # S7/S8 Model 4: these additional checks identify the exact equation.
        exp1 = estimate["study_id"] == "S1"
        checks.extend([
            check("Model_4.CF_coefficient", -0.222 if exp1 else -0.259, fit.params["CF"]),
            check("Model_4.IS_coefficient", 0.401 if exp1 else 0.256, fit.params["IS"]),
            check("Model_4.R_squared", 0.113 if exp1 else 0.126, fit.rsquared),
            check("Model_4.F", 8.470 if exp1 else 9.595, fit.fvalue),
        ])
    elif estimate["study_id"] == "S1":
        t = frame.loc[frame[treatment] == 1, "C"]
        c = frame.loc[frame[treatment] == 0, "C"]
        for name, value, decimals in [
            ("treatment_mean", t.mean(), 2), ("control_mean", c.mean(), 3),
            ("treatment_sd", t.std(ddof=1), 3), ("control_sd", c.std(ddof=1), 3),
        ]:
            checks.append(check(name, printed[name], value, decimals))
        test = stats.ttest_ind(c, t, equal_var=True)
        checks.extend([
            check("test.value_control_minus_treatment", printed["test"]["value"], test.statistic),
            check("test.df", printed["test"]["df"], test.df, 0),
            check("p_value", printed["p_value"], test.pvalue),
        ])
    else:
        fit, f_value, p_value = factorial_fit(frame, "C", treatment)
        checks.extend([
            check("test.value_factorial_main_effect_F", printed["test"]["value"], f_value),
            check("test.df_numerator", printed["test"]["df"][0], 1, 0),
            check("test.df_denominator", printed["test"]["df"][1], fit.df_resid, 0),
            check("p_value", printed["p_value"], p_value),
            check("paper_effect.partial_eta_squared", printed["paper_effect"]["value"], f_value / (f_value + fit.df_resid)),
        ])
        for arm, task, value in [(0, 0, 2.466), (0, 1, 2.139), (1, 0, 2.171), (1, 1, 2.520)]:
            cell = frame.loc[(frame[treatment] == arm) & (frame.TC == task), "C"]
            label = f"main_p7.cell_mean_treatment_{arm}_complexity_{task}"
            checks.append(check(label, value, cell.mean()))
    return checks


def participant_contrast(frame, treatment):
    """One equally weighted observation per participant, in raw rating units."""
    outcome = frame["C_from_ratings"]
    t = outcome[frame[treatment] == 1]
    c = outcome[frame[treatment] == 0]
    fit = sm.OLS(outcome, sm.add_constant(frame[[treatment]]), missing="raise").fit(cov_type="HC2")
    difference = float(t.mean() - c.mean())
    se = float(fit.bse[treatment])
    # Independent numerical identities for binary-treatment, intercept-only OLS.
    assert np.isclose(fit.params[treatment], difference, atol=1e-12, rtol=0)
    assert np.isclose(se, np.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c)), atol=1e-12, rtol=0)
    return {
        "n_treatment": len(t), "n_control": len(c),
        "treatment_mean": float(t.mean()), "treatment_sd": float(t.std(ddof=1)),
        "control_mean": float(c.mean()), "control_sd": float(c.std(ddof=1)),
        "difference": difference, "difference_se": se,
        "se_type": "HC2", "n_clusters": None,
    }


def make_notes(estimate, frame, treatment, audit):
    exp1 = estimate["study_id"] == "S1"
    exp = 1 if exp1 else 2
    direct = estimate["slug"].endswith("direct_adjusted")
    control = "human partner" if exp1 else "batch-responsive LLM"
    treated = "LLM partner" if exp1 else "constrained-responsive LLM"
    n_t = int((frame[treatment] == 1).sum())
    n_c = int((frame[treatment] == 0).sum())
    notes = [
        f"Reproduction source: Exp{exp}_model.xlsx, Sheet1, Excel rows 2-205; {treatment}=1 is {treated} (n={n_t}), {treatment}=0 is {control} (n={n_c}). TC=0 is the simple tire task and TC=1 is the complex VR task. The treatment task cells contain 52 people each and control cells contain 50 each. All 204 analysis-file participants have outcome and both mediators; no participant exclusions or imputations were made.",
        f"Arm counts are printed in supplement PDF p. {10 if exp1 else 11}, Table S{5 if exp1 else 6}; study N=204 is also in main-paper Fig. {2 if exp1 else 4}. The ten deposited workbooks were verified against their manifest SHA-256 hashes and byte sizes.",
        f"The computed object uses Exp{exp}_creativity_rating.xlsx: average the two expert ratings on each idea, then average all of a participant's ideas with equal idea weights. There are {audit['n_ideas']} ideas and 204 participants, all with two complete ratings per idea. The idea-only workbook matches the rating workbook's idea, user, timestamp and room columns exactly. IDs such as (C)NAI31 are normalized to NAI31C; the full-width opening parenthesis in survey IDs is normalized as well. These IDs denote distinct between-person task cells, not repeat rounds.",
        "Computed means and sample SDs weight people equally; SD uses n-1. Difference is treatment minus control on the original 1-5 creativity scale. Difference SE is from OLS of the participant outcome on an intercept and the arm indicator with HC2, independently checked against sqrt(s_t^2/n_t + s_c^2/n_c). Individual randomization requires no clusters. There is no paired or first-round estimate.",
        f"Reconstructed mean fixation ratings agree with every analysis-file CF value. Partner-message rows without participant ratings are omitted from this covariate audit. The survey has {audit['summary_rows']} trailing demographic-summary rows without IDs; these are not people. The complete author-provided IS covariate is used for publication-model reproduction.",
    ]
    if exp1:
        notes.append(
            "Every C value in Exp1_model.xlsx agrees with the participant mean independently reconstructed from the ratings (absolute discrepancy below 1e-12). Survey IDs contain HH39C twice and omit HH40C; one HH39C row agrees with its model IS=2.4 and the other has IS=2.0. The model carries IS=2.0 for HH40C, but that survey-ID repair cannot be confirmed and is not performed here. No survey rows are used to exclude people from the complete model or the ratings."
        )
    else:
        _, raw_f, raw_p = factorial_fit(frame, "C_from_ratings", treatment)
        raw_direct = direct_fit(frame, "C_from_ratings", treatment)
        discrepancy = audit["model_rating_mismatch"]
        notes.append(
            "Raw-rating discrepancy: " + json.dumps(discrepancy, ensure_ascii=True, sort_keys=True) + ". "
            "Specifically, Exp2_model.xlsx F82 gives NAI31C C=2.07142857142857. "
            "Its 14 ideas in creativity-rating Excel rows 449-462 have thirteen (2,2) rating pairs and one (3,2), "
            "so the required two-rater/within-person average is 2.0357142857142856. The other 203 C values agree. "
            "All publication checks in reproduced use the supplied model C; the computed object uses the actual rating averages, "
            "without changing any posted rating or copying the discrepant aggregate. "
            f"Using the reconstructed ratings instead, the original factorial F is {raw_f:.15g} (p={raw_p:.15g}), "
            f"and the standardized direct coefficient is {raw_direct.params['treatment']:.15g}; "
            "these would round to 0.824, 0.365 and 0.030 rather than the printed 0.811, 0.369 and 0.029. "
            "Thus publication reproduction succeeds on the authors' deposited analysis table, but exact reconstruction of its outcome from the ratings fails for one person. "
            "All 204 survey IS item means match model IS. Arm coding is additionally confirmed by the response-quantity manipulation means: NC=0 gives 4.040 and NC=1 gives 3.058, as printed on main PDF p. 6."
        )
    if direct:
        fit = direct_fit(frame, "C", treatment)
        notes.append(
            f"Adjusted reproduction: supplement PDF p. 12, Table S{7 if exp1 else 8}, Model 4. "
            "OLS z(C) on intercept, the unstandardized 0/1 assigned-arm indicator, z(CF), and z(IS) reproduces "
            "the treatment coefficient, both mediator coefficients, model R-squared and model F at their printed precision. "
            "Each continuous variable is centered and divided by its sample SD across the 204 complete cases. "
            "This scaling is an inference supported by the numerical reproduction; the supplement itself does not specify it. "
            "Task complexity and its interaction are absent from this outcome equation. "
            f"The conventional OLS treatment SE is {fit.bse['treatment']:.15g}, which numerically rounds to the printed "
            f"{estimate['stats']['regression']['se']:.3f}; however, the table note calls the SE bootstrapped with 10,000 replications. "
            "The original bootstrap draws/seed are not provided, so bootstrap precision is not claimed as reproduced and is not in the reproduced list. "
            "The count checks are explicitly experiment-level printed counts; this table prints no model-specific n. "
            "The deposited complete-case model has exactly those 204 people. "
            "Per the brief's requested OLS-on-arm computation, computed contains raw unadjusted means and their HC2 difference, "
            "not the mediator-adjusted coefficient. Its computed fields duplicate the corresponding pooled record; do not count them as an independent effect."
        )
    elif exp1:
        notes.append(
            "Publication checks use main PDF p. 5: pooled expert-creativity means, participant SDs, equal-variance t with df=202 and its two-sided p. "
            "The printed t is human minus LLM, opposite the positive treatment-minus-control sign in computed. "
            "The paper does not identify the d standardizer or the confidence-interval estimand; neither is guessed or used in this reanalysis."
        )
    else:
        notes.append(
            "Publication checks use main PDF p. 6 factorial response-type F, p, df and partial eta-squared, "
            "plus main PDF p. 7 task-cell means to confirm the arm and complexity mapping. "
            "The F is the equally weighted main effect from the full treatment-by-complexity model, "
            "not the simple pooled t-test squared. Its partial eta-squared is F/(F+200). "
            "The new HC2 difference is the pooled contrast requested in the brief, not the factorial model's conventional SE."
        )
    return " ".join(notes)


def main():
    with MANIFEST.open(encoding="utf-8") as fh:
        manifest = json.load(fh)["deposits"]["osf-9ckra"]["files"]
    for path in DATA_FILES:
        entry = manifest[path.relative_to(ROOT).as_posix()]
        data = path.read_bytes()
        assert len(data) == entry["bytes"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    studies = {study["study_id"]: study for study in extraction["studies"]}
    pooled = {e["study_id"]: e for e in extraction["estimates"] if not e["slug"].endswith("direct_adjusted")}
    datasets = {"S1": load_experiment(1), "S2": load_experiment(2)}
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        frame, treatment, audit = datasets[estimate["study_id"]]
        checks = reproduce(estimate, frame, treatment, pooled[estimate["study_id"]], studies[estimate["study_id"]])
        # The publication gate precedes computing the requested new contrast.
        passed = all(item["match"] for item in checks)
        computed = participant_contrast(frame, treatment) if passed else None
        notes = make_notes(estimate, frame, treatment, audit)
        if not passed:
            failed = [item for item in checks if not item["match"]]
            reason = "Publication reproduction failed: " + json.dumps(failed, ensure_ascii=True)
            notes += " " + reason + ". No new contrast computed."
            skipped.append({"slug": estimate["slug"], "reason": reason})
        results.append({
            "slug": estimate["slug"], "round": "all", "reproduced": checks,
            "computed": computed, "notes": notes,
        })
    obj = {
        "cid": "c043", "analyst": "A", "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in DATA_FILES],
        "results": results, "skipped": skipped,
    }
    # Reject NaNs or other non-JSON values before the sole result-file write.
    json.dumps(obj, ensure_ascii=False, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({
        "cid": "c043", "n_results": len(results),
        "n_reproduced": sum(r["computed"] is not None for r in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
