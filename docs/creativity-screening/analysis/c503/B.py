"""Independent analyst B reconstruction for c503.

Run with python -I -B B.py. Deposited programs are never executed or imported.
All transformations below are independently implemented from the paper and from
reading the authors' Stata files as plain text. No intermediate files are written.
"""

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
import scipy.linalg
import scipy.stats
import statsmodels.api as sm


WORKSPACE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSITS = Path(r"D:/projects/ai-skill-atlas/creativity-data")
RAW = DEPOSITS / "osf-xd7qw/raw"
SCRIPT = WORKSPACE / "analysis/c503/B.py"
OUTPUT = WORKSPACE / "analysis/c503/B.json"
DATA_FILES = []
AUDIT = {}

TEST_GRADER = "043a718774c572bd8a25adbeb1bfcd5c0256ae11cecf9f9c3f925d0e52beaf89"
MANUAL_EXCLUSIONS = {
    "484d7e16cdcac3774e045744722ecd4610f01d40069b05c9affb00499e8f3731",
    "727c882101c4438387011b92398c999d46e76b0f3c59bb45b17e6ea1c64e4561",
    "8b0833b266be60de6278a28d4ae8052236ecac85b248710ac6efaf57420ee11a",
    "174207d4312d46b6b908d28dc34c9f6dbe62d22844b6b9b8b875ac4de272b275",
    "f9a1e36ff890a83c3dc1634403f02e0d250e66cf08218f197b7127f2993892ec",
    "bee7a8f1c3bdc0c2a6e6303ab33a8253a69894569927a633222bd5e3a6d244ff",
}


def register(path):
    path = Path(path)
    name = path.as_posix()
    if name not in DATA_FILES:
        DATA_FILES.append(name)
    return path


def read_csv(path, usecols=None):
    # Some survey prose is not valid UTF-8. Latin-1 preserves every source byte;
    # all identifiers, variables, and numerical values used here are ASCII.
    result = pd.read_csv(register(path), encoding="latin-1", low_memory=False,
                         usecols=usecols)
    result.columns = result.columns.str.lower()
    return result


def dates(series):
    return pd.to_datetime(series.str.slice(0, 10), format="%Y-%m-%d", errors="coerce")


def clean_survey(long_grades):
    cols = ["prolific_pid", "startdate", "finished", "consent", "consent_exact",
            "occupation", "incentive_arm", "treatment", "a_first"]
    survey = read_csv(RAW / "fullsurvey.csv", usecols=cols)
    AUDIT["raw_survey_rows"] = len(survey)
    survey = survey.loc[survey.finished.ne(0) & survey.consent.ne(2)
                        & survey.consent_exact.ne(2)].copy()
    survey["datetasked"] = dates(survey.startdate)
    task_dates = survey.groupby("prolific_pid").datetasked.min()
    AUDIT["consenting_finished_rows"] = len(survey)
    survey = survey.sort_values(["prolific_pid", "startdate"], kind="stable")
    survey = survey.drop_duplicates("prolific_pid", keep="first")
    AUDIT["after_duplicate_removal"] = len(survey)
    survey = survey.loc[~survey.prolific_pid.isin(MANUAL_EXCLUSIONS)].copy()
    AUDIT["after_manual_exclusions"] = len(survey)

    checks = []
    for filename in ["grading.xlsx", "grading_retry.xlsx"]:
        table = pd.read_excel(register(RAW / filename))
        table["qcheck"] = pd.to_numeric(table.qcheck, errors="coerce").replace(3, 1)
        table = table.groupby("prolific_pid").qcheck.agg(minqcheck="min", maxqcheck="max")
        checks.append(table)
    overlap = checks[0].join(checks[1], how="inner", lsuffix="_a", rsuffix="_b")
    assert (overlap.minqcheck_a == overlap.minqcheck_b).all()
    assert (overlap.maxqcheck_a == overlap.maxqcheck_b).all()
    checks = pd.concat(checks)
    checks = checks.loc[~checks.index.duplicated(keep="first")]
    survey = survey.join(checks, on="prolific_pid", validate="one_to_one")
    survey = survey.loc[~(survey.maxqcheck.gt(1) | survey.minqcheck.lt(1))].copy()
    AUDIT["after_quality_checks"] = len(survey)

    earliest_grading = long_grades.assign(dategraded=dates(long_grades.startdate))
    earliest_grading = earliest_grading.groupby("grader_id").dategraded.min()
    survey["dategraded"] = survey.prolific_pid.map(earliest_grading)
    survey = survey.loc[~survey.datetasked.gt(survey.dategraded)].copy()
    assert survey.prolific_pid.is_unique
    assert survey.treatment.isin([0, 1]).all()
    assert survey.a_first.isin([0, 1]).all()
    AUDIT["clean_survey_people_by_arm"] = {
        str(int(k)): int(v) for k, v in survey.treatment.value_counts().items()
    }
    return survey, task_dates


def clean_graders(long_grades, task_dates):
    # July 21 corrected script removes an unavailable private anonymization-file
    # merge. The released identifiers already agree across the public data.
    grades = long_grades.loc[long_grades.grader_id.ne(TEST_GRADER)
                             & long_grades.retry.ne(1)].copy()
    grades["dategraded"] = dates(grades.startdate)
    grades["datetasked"] = grades.grader_id.map(task_dates)
    grades = grades.loc[~grades.dategraded.gt(grades.datetasked)]
    grades = grades.loc[grades.overall.notna()].copy()
    human = grades.loc[~grades.prolific_pid.isin(["chatGPT", "ChatGPT"])]
    # For each grader regress their grade on every other grade of the same
    # essay, exactly the oriented pairs constructed by grade cleaning_jul21.do.
    pairs_by_grader = {}
    self_pairs = {}
    for _, essay in human.groupby(["prolific_pid", "essaynum"], sort=True):
        essay = essay.sort_values("grader_id", kind="stable")
        ratings = list(essay[["grader_id", "overall"]].itertuples(index=False, name=None))
        for (grader_a, score_a), (grader_b, score_b) in itertools.combinations(ratings, 2):
            if grader_a == grader_b:
                # Stata's two replace commands make such a pair (score_a,
                # score_a). Sorting tied grader IDs can change score_a. Check
                # every possibility below so no exclusion depends on a guess
                # about the private Stata sort order.
                self_pairs.setdefault(grader_a, []).append(tuple(sorted({score_a, score_b})))
            else:
                pairs_by_grader.setdefault(grader_a, []).append((score_b, score_a))
                pairs_by_grader.setdefault(grader_b, []).append((score_a, score_b))
    slopes = {}
    tie_ranges = []
    for grader, values in pairs_by_grader.items():
        array = np.asarray(values, dtype=float)
        x, y = array[:, 0], array[:, 1]
        if len(x) <= 1:
            raise ValueError("Grader with fewer than two comparison pairs.")
        denominator = np.sum((x - x.mean()) ** 2)
        slopes[grader] = (np.sum((x - x.mean()) * (y - y.mean())) / denominator
                          if denominator > 0 else 0.0)
        if grader in self_pairs:
            possibilities = []
            for scores in itertools.product(*self_pairs[grader]):
                candidate = np.vstack([array, np.column_stack([scores, scores])])
                xx, yy = candidate[:, 0], candidate[:, 1]
                dd = np.sum((xx - xx.mean()) ** 2)
                possibilities.append(float(np.sum((xx - xx.mean()) * (yy - yy.mean())) / dd)
                                     if dd > 0 else 0.0)
            lo, hi = min(possibilities), max(possibilities)
            assert (lo < 0.1) == (hi < 0.1), "Ambiguous bad-grader status under tied sorting."
            tie_ranges.append([round(lo, 9), round(hi, 9)])
            slopes[grader] = possibilities[0]
    assert set(human.grader_id) <= set(slopes)
    bad = {grader for grader, slope in slopes.items() if slope < 0.1}
    # The Stata merge identifies bad graders using the first 15 characters.
    assert human.grader_id.nunique() == human.grader_id.str.slice(0, 15).nunique()
    AUDIT["graders_assessed"] = len(slopes)
    AUDIT["graders_excluded_low_slope"] = len(bad)
    AUDIT["self_pair_slope_bounds_same_exclusion_decision"] = tie_ranges
    AUDIT["grader_slopes_near_threshold"] = sorted(round(v, 9) for v in slopes.values()
                                                   if abs(v - 0.1) < 0.08)
    return grades.loc[~grades.grader_id.isin(bad)].copy(), bad


def prepare():
    long_grades = read_csv(RAW / "grading_long_complete.csv")
    survey, task_dates = clean_survey(long_grades)
    long_clean, bad = clean_graders(long_grades, task_dates)
    # Stata keeps the master dataset's occupation when merging survey fields.
    fields = ["prolific_pid", "treatment", "a_first", "incentive_arm"]
    long_clean = long_clean.merge(survey[fields], on="prolific_pid", how="inner",
                                  validate="many_to_one")
    long_clean["post"] = ((long_clean.a_first.eq(1) & long_clean.essaynum.eq("B"))
                           | (long_clean.a_first.eq(0) & long_clean.essaynum.eq("A")))
    post = long_clean.loc[long_clean.post & long_clean.incentive_arm.ne("exact")].copy()

    wide = read_csv(RAW / "grading_wide_complete.csv")
    wide = wide.loc[wide.grader_id.ne(TEST_GRADER) & wide.retry_a.ne(1)
                    & wide.retry_b.ne(1) & ~wide.grader_id.isin(bad)].copy()
    wide = wide.merge(survey[fields], on="prolific_pid", how="inner", validate="many_to_one")
    wide["overall1"] = np.where(wide.a_first.eq(1), wide.overall_a, wide.overall_b)
    wide["overall2"] = np.where(wide.a_first.eq(1), wide.overall_b, wide.overall_a)
    wide["overall_diff"] = wide.overall2 - wide.overall1
    return survey, long_clean, post, wide


def paper_regression(wide):
    restricted = wide.loc[wide.incentive_arm.ne("exact")].copy()
    pre_sd = float(restricted.overall1.std(ddof=1))
    sample = restricted.dropna(subset=["overall_diff", "treatment", "grader_id",
                                       "occupation", "a_first", "incentive_arm"])
    # Occupation by order cells span i.occupation##i.a_first. QR selects a
    # full-rank column set because occupation is nested in grader fixed effects.
    categories = pd.DataFrame({"grader": sample.grader_id,
                               "occupation_order": sample.occupation + "_" + sample.a_first.astype(str),
                               "incentive": sample.incentive_arm}, index=sample.index)
    effects = pd.get_dummies(categories, drop_first=True, dtype=float)
    design = pd.concat([pd.Series(1.0, index=sample.index, name="intercept"),
                        sample.treatment, effects], axis=1)
    _, r, pivots = scipy.linalg.qr(design.to_numpy(), mode="economic", pivoting=True)
    rank = int(np.linalg.matrix_rank(r))
    independent = sorted(pivots[:rank])
    design = design.iloc[:, independent]
    assert "treatment" in design.columns
    model = sm.OLS(sample.overall_diff.astype(float), design.astype(float)).fit(
        cov_type="cluster", cov_kwds={"groups": sample.prolific_pid,
                                     "use_correction": True}, use_t=True)
    coefficient = float(model.params["treatment"])
    se = float(np.sqrt(model.cov_params().loc["treatment", "treatment"]))
    # The authors first round raw coefficient/SE to .001, divide by baseline
    # rating SD, round to .01, then form CI endpoints from these rounded values.
    display_coefficient = round(round(coefficient, 3) / pre_sd, 2)
    display_se = round(round(se, 3) / pre_sd, 2)
    return {"coefficient_raw": coefficient, "se_raw": se, "baseline_rating_sd": pre_sd,
            "standardized_exact": coefficient / pre_sd,
            "display_coefficient": display_coefficient,
            "display_ci_lower": round(display_coefficient - 1.96 * display_se, 2),
            "display_ci_upper": round(display_coefficient + 1.96 * display_se, 2),
            "p_value": float(2 * scipy.stats.t.sf(abs(coefficient / se),
                               df=sample.prolific_pid.nunique() - 1)),
            "rating_rows": len(sample), "people": sample.prolific_pid.nunique(),
            "rank": rank}


def context_and_integrity():
    """Record all consulted inputs; deposited code is read solely as text."""
    extraction = json.loads(register(WORKSPACE / "extraction/c503.json").read_text(encoding="utf-8"))
    retrieval = json.loads(register(WORKSPACE / "retrieval.json").read_text(encoding="utf-8"))["c503"]
    for path in [WORKSPACE.parent / "creativity-codebook.md", WORKSPACE / "extraction-spec.md",
                 Path(retrieval["md_path"])]:
        register(path).read_text(encoding="utf-8")
    with pymupdf.open(register(retrieval["pdf_path"])) as pdf:
        figure_text = pdf[11].get_text()
        assert "Control: Mean 3.802" in figure_text
        assert "Treatment: Mean 4.53" in figure_text
        assert "[0.23, 0.59]" in figure_text
        for page in [0, 2, 3, 12, 17, 18]:
            pdf[page].get_text()
        # Confirm printed sample/baseline counts directly against Table 1.
        table = pdf[17].find_tables().tables[0].extract()
        normalized = {row[0].replace("\n", " "): row[1:] for row in table[1:]}
        assert normalized["Occupation: Manager"][0] == "235"
        assert normalized["Occupation: Manager"][2] == "218"
        assert normalized["Average Grade (Task 1)"][:4] == ["233", "3.63", "211", "3.77"]

    code_folder = DEPOSITS / "osf-xd7qw/code"
    for name in ["0 - Master.do", "2 - clean.do", "3 - grade cleaning.do",
                 "3 - grade cleaning_jul21.do", "4 - main text figures.do",
                 "5 - appendix figures.do", "00 - grade formatting.py", "8 - SM analysis.py"]:
        register(code_folder / name).read_text(encoding="utf-8-sig")

    # The second named deposit is inventoried, never pooled with the deposit
    # cited by the saved paper. Its files differ in rows and participant IDs.
    alternative = DEPOSITS / "osf-q3gdu"
    counts = {}
    for name in ["fullsurvey.csv", "grading_long_complete.csv", "grading_wide_complete.csv"]:
        columns = (["prolific_pid", "startdate", "finished", "consent", "consent_exact",
                    "occupation", "incentive_arm", "treatment", "a_first"]
                   if name == "fullsurvey.csv" else None)
        counts[name] = len(read_csv(alternative / name, usecols=columns))
    AUDIT["alternative_deposit_inventory_rows"] = counts

    manifest = json.loads(register(DEPOSITS / "manifest.json").read_text(encoding="utf-8"))
    checked = 0
    for name in DATA_FILES:
        path = Path(name)
        if path.is_relative_to(DEPOSITS) and path != DEPOSITS / "manifest.json":
            parts = path.relative_to(DEPOSITS).parts
            item = manifest["deposits"][parts[0]]["files"]["/".join(parts[1:])]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], name
            checked += 1
    AUDIT["deposit_files_with_verified_sha256"] = checked
    return extraction


def compare(statistic, printed, computed, places):
    """Compare at the printed precision, without rounding the saved raw value."""
    value = int(computed) if places == 0 else float(computed)
    return {"statistic": statistic, "printed": printed, "computed": value,
            "match": bool(round(value, places) == round(printed, places))}


def participant_statistics(post):
    people = post.groupby(["prolific_pid", "treatment"], as_index=False).overall.mean()
    assert people.prolific_pid.is_unique
    treatment = people.loc[people.treatment.eq(1), "overall"]
    control = people.loc[people.treatment.eq(0), "overall"]
    fit = sm.OLS(people.overall, sm.add_constant(people.treatment)).fit(cov_type="HC2")
    difference = float(treatment.mean() - control.mean())
    se = float(fit.bse["treatment"])
    # For an intercept plus binary arm, HC2 is exactly the unequal-variance
    # standard error of the difference in independent arm means.
    assert np.isclose(fit.params["treatment"], difference, rtol=1e-12, atol=1e-12)
    assert np.isclose(se, np.sqrt(treatment.var(ddof=1) / len(treatment)
                                 + control.var(ddof=1) / len(control)), rtol=1e-12)
    return {"n_treatment": len(treatment), "n_control": len(control),
            "treatment_mean": float(treatment.mean()), "treatment_sd": float(treatment.std(ddof=1)),
            "control_mean": float(control.mean()), "control_sd": float(control.std(ddof=1)),
            "difference": difference, "difference_se": se, "se_type": "HC2", "n_clusters": None}


def main():
    DATA_FILES.clear()
    AUDIT.clear()
    survey, long_clean, post, wide = prepare()
    extraction = context_and_integrity()
    estimates = {item["slug"]: item for item in extraction["estimates"]}
    figure_slug = "s1_average_grade_chatgpt_vs_control_figure1"
    figure = estimates[figure_slug]["stats"]
    regression = paper_regression(wide)
    baseline = long_clean.loc[~long_clean.post].groupby(["prolific_pid", "treatment"]).overall.mean()
    baseline_arm = baseline.groupby("treatment").agg(["mean", "count"])
    rating_means = post.groupby("treatment").overall.mean()
    sample_counts = survey.groupby("treatment").size()
    checks = [
        compare("Figure 1D treatment_mean (individual evaluator ratings)", figure["treatment_mean"], rating_means[1], 2),
        compare("Figure 1D control_mean (individual evaluator ratings)", figure["control_mean"], rating_means[0], 3),
        compare("Figure 1B standardized adjusted grade-change coefficient", figure["paper_effect"]["value"], regression["standardized_exact"], 2),
        compare("Figure 1B 95% CI lower (authors' sequential rounding)", figure["ci_lower"], regression["display_ci_lower"], 2),
        compare("Figure 1B 95% CI upper (authors' sequential rounding)", figure["ci_upper"], regression["display_ci_upper"], 2),
        compare("Table 1 descriptive sample n_treatment (all incentive arms)", 218, sample_counts[1], 0),
        compare("Table 1 descriptive sample n_control (all incentive arms)", 235, sample_counts[0], 0),
        compare("Paper sample N (PDF pp. 1 and 3; all incentive arms)", 453, len(survey), 0),
        compare("Table 1 baseline grade n_treatment (all incentive arms)", 211, baseline_arm.loc[1, "count"], 0),
        compare("Table 1 baseline grade n_control (all incentive arms)", 233, baseline_arm.loc[0, "count"], 0),
        compare("Table 1 baseline participant grade mean_treatment", 3.77, baseline_arm.loc[1, "mean"], 2),
        compare("Table 1 baseline participant grade mean_control", 3.63, baseline_arm.loc[0, "mean"], 2),
    ]
    results, skipped = [], []
    if all(check["match"] for check in checks):
        computed = participant_statistics(post)
        notes = (
            "Source: saved NBER manuscript, PDF pp. 12-13, Figure 1B/1D; Table 1, PDF pp. 18-19. "
            "The validated grade variable is overall, an evaluator's 1-7 overall-quality rating, "
            "not an arithmetic composite of writing, content, and originality. "
            "Treatment is randomized ChatGPT access (treatment=1), control is Overleaf signup "
            "(treatment=0); actual ChatGPT use does not determine inclusion. "
            "Reconstruction follows osf-xd7qw/code/2 - clean.do, "
            "3 - grade cleaning_jul21.do, and 4 - main text figures.do, read only as text. "
            "The July 21 grade-cleaning version removes the original script's unavailable "
            "private anonymization-file merge; all other grade-cleaning steps are identical. "
            "Survey exclusions: unfinished/nonconsenting responses; later duplicate submissions; "
            "six explicitly listed manual exclusions; qcheck outside 1 after recoding 3 to 1; "
            "and people who had graded before doing the task survey. These steps leave "
            "453 people (218 treatment, 235 control), matching the printed descriptive sample. "
            "The linear/convex restriction leaves 359 (172 treatment, 187 control). "
            "Long-form ratings exclude the named test grader, retry=1 edited/resubmitted "
            "first-task outputs, graders who graded after participating in the task survey, "
            "missing overall scores, and 23 of 118 assessed graders whose own-vs-other "
            "grade regression slope is below 0.1. Every possible orientation of tied "
            "same-grader pairs gives the same exclusion decisions. "
            "Post-treatment means essay B when a_first=1 and essay A when a_first=0. "
            "The Figure 1D reconstruction contains 462 treatment and 501 control ratings "
            "from 167 treatment and 186 control people. The paper does not print these "
            "Figure 1 analysis counts: reproduced count checks above concern the full "
            "descriptive/baseline samples, not inferred printed post-treatment Ns. "
            "For computed statistics each person's retained post-treatment overall ratings "
            "are averaged first; people then receive equal weight. SDs use n-1. The "
            "participant means consequently differ from the paper's rating-weighted means. "
            "difference is treatment_mean minus control_mean in 1-7 grade points. "
            "difference_se is OLS with an intercept and arm indicator, HC2, at the "
            "individually randomized participant level; it is also independently checked "
            "as sqrt(treatment_sd^2/n_treatment + control_sd^2/n_control). "
            f"Separately, Figure 1B is reproduced from 1000 participant-evaluator rows "
            f"and 352 people (166 treatment, 186 control) with both grades: raw adjusted "
            f"coefficient {regression['coefficient_raw']:.12g}, participant-clustered SE "
            f"{regression['se_raw']:.12g}, divided by baseline rating SD "
            f"{regression['baseline_rating_sd']:.12g}. This uses grader, "
            "occupation-by-task-order, and incentive fixed effects, and the authors' "
            "rounding sequence for the displayed CI. That adjusted change coefficient "
            "and clustered SE are validation quantities, not the unadjusted participant "
            "difference and HC2 SE requested here. The long- and wide-format analysis "
            "populations are intentionally distinguished. This is a between-person RCT "
            "with a pre-intervention baseline, not randomized condition order, so round "
            "is all and no first_round contrast is produced. The other supplied deposit, "
            "osf-q3gdu, was inventoried (769 survey rows, 3774 long rating rows, 1882 "
            "wide rows); it is a different dataset and is not pooled with osf-xd7qw. "
            "SHA256 checks against the supplied manifest pass for all consulted "
            "deposited files. data_files lists data and contextual sources actually read."
        )
        results.append({"slug": figure_slug, "round": "all", "reproduced": checks,
                        "computed": computed, "notes": notes})
    else:
        failed = [check for check in checks if not check["match"]]
        skipped.append({"slug": figure_slug, "reason": "Reproduction failed; participant statistics not computed. "
                         + json.dumps(failed, ensure_ascii=True)})

    text_slug = "s1_average_grade_chatgpt_vs_control_text"
    text_effect = estimates[text_slug]["stats"]["paper_effect"]["value"]
    skipped.append({"slug": text_slug, "reason": (
        f"PDF p. 4 prints {text_effect:.2f} SD (p<0.001), but does not identify a separate "
        "sample, standardizer, model, or analysis count. The documented main grade-change "
        f"specification recomputes to {regression['standardized_exact']:.12g} SD, "
        f"or {regression['display_coefficient']:.2f} at printed precision, matching Figure 1B "
        f"rather than the narrative's {text_effect:.2f}. Its p-value is "
        f"{regression['p_value']:.12g}, satisfying the prose bound but not reproducing "
        "the effect size. No independent statistics are computed for this unreproduced "
        "narrative record, and the Figure 1 result is not duplicated or assigned to it."
    )})
    for slug, variable in [
        ("s1_originality_chatgpt_vs_control", "originality"),
        ("s1_overall_grade_chatgpt_vs_control", "overall"),
        ("s1_writing_quality_chatgpt_vs_control", "writing"),
        ("s1_content_quality_chatgpt_vs_control", "content"),
    ]:
        assert estimates[slug]["stats"]["paper_effect"] is None
        reason = (
            f"The posted grading data contain the {variable} variable, but this separate "
            "extraction record has no printed arm means, difference/coefficient, "
            "uncertainty, or outcome-specific counts. PDF p. 4 says only that increases "
            "were similar. Supplementary grade results are not embedded in the saved "
            "19-page PDF. An estimate-specific numerical reproduction check is therefore "
            "unavailable; no participant statistics are computed under the reproduce-first rule."
        )
        if variable == "overall":
            reason += (" The overall variable is validated for Figure 1 and reported in that "
                       "record; the unquantified separate narrative label is not treated "
                       "as another independently reproduced estimate.")
        skipped.append({"slug": slug, "reason": reason})

    assert {item["slug"] for item in results + skipped} == set(estimates)
    assert len(results) + len(skipped) == len(estimates)
    output = {"cid": "c503", "analyst": "B", "script": SCRIPT.as_posix(),
              "data_files": DATA_FILES, "results": results, "skipped": skipped}
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == output
    print(json.dumps({"cid": "c503", "n_results": len(results),
                      "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
                      "n_skipped": len(skipped)}))


def diagnose():
    survey, long_clean, post, wide = prepare()
    print(json.dumps(AUDIT, indent=1))
    print("FIGURE 1D RATING MEANS AND COUNTS")
    print(post.groupby("treatment").agg(mean=("overall", "mean"),
          ratings=("overall", "count"), people=("prolific_pid", "nunique")).to_string())
    baseline = long_clean.loc[~long_clean.post].groupby(["prolific_pid", "treatment"]).overall.mean()
    print("TABLE 1 BASELINE PERSON MEANS AND COUNTS")
    print(baseline.groupby("treatment").agg(["mean", "count"]).to_string())
    print("FIGURE 1B REGRESSION")
    print(json.dumps(paper_regression(wide), indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()
    if args.diagnose:
        diagnose()
    else:
        main()
