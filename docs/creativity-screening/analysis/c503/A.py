"""Independent c503 analysis, analyst A. Run with python -I -B A.py.

Only this script and A.json are written. Deposited programs are never executed.
Sample and rating rules are translated from the authors' Stata code, including
the July 21 correction to grade cleaning, into the Python functions below.
"""

from collections import defaultdict
from itertools import combinations, product
from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data/osf-xd7qw")
RAW = DEPOSIT / "raw"
SCRIPT = ROOT / "analysis/c503/A.py"
OUTPUT = ROOT / "analysis/c503/A.json"
EXTRACTION = ROOT / "extraction/c503.json"
MANIFEST = DEPOSIT.parent / "manifest.json"
ALTERNATIVE = DEPOSIT.parent / "osf-q3gdu"

DATA_FILES = [
    RAW / "fullsurvey.csv",
    RAW / "grading_long_complete.csv",
    RAW / "grading_wide_complete.csv",
    RAW / "grading.xlsx",
    RAW / "grading_retry.xlsx",
    ALTERNATIVE / "fullsurvey.csv",
    ALTERNATIVE / "grading_long_complete.csv",
]

TEST_GRADER = "043a718774c572bd8a25adbeb1bfcd5c0256ae11cecf9f9c3f925d0e52beaf89"
MANUAL_EXCLUSIONS = {
    "484d7e16cdcac3774e045744722ecd4610f01d40069b05c9affb00499e8f3731",
    "727c882101c4438387011b92398c999d46e76b0f3c59bb45b17e6ea1c64e4561",
    "8b0833b266be60de6278a28d4ae8052236ecac85b248710ac6efaf57420ee11a",
    "174207d4312d46b6b908d28dc34c9f6dbe62d22844b6b9b8b875ac4de272b275",
    "f9a1e36ff890a83c3dc1634403f02e0d250e66cf08218f197b7127f2993892ec",
    "bee7a8f1c3bdc0c2a6e6303ab33a8253a69894569927a633222bd5e3a6d244ff",
}


def read_csv(path, usecols=None):
    # These Stata-exported files are not valid UTF-8. Latin-1 preserves bytes;
    # the identifiers, labels and numeric variables used here are ASCII.
    data = pd.read_csv(path, encoding="latin1", low_memory=False, usecols=usecols)
    data.columns = data.columns.str.lower()
    return data


def calendar_day(series):
    # Stata date(startdate, "YMD###") ignores the within-day time.
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def clean_participants(survey, grades):
    """Relevant rules in 2 - clean.do, lines 28-174."""
    counts = [("raw_survey_rows", len(survey))]
    sample = survey.loc[
        survey.finished.ne(0)
        & survey.consent.ne(2)
        & survey.consent_exact.ne(2)
    ].copy()
    counts.append(("finished_and_not_declining_consent", len(sample)))
    sample["datetasked"] = calendar_day(sample.startdate)
    task_dates = sample.groupby("prolific_pid").datetasked.min()
    sample = sample.sort_values(["prolific_pid", "startdate"], kind="stable")
    sample = sample.drop_duplicates("prolific_pid", keep="first")
    counts.append(("unique_survey_participants", len(sample)))
    sample = sample.loc[~sample.prolific_pid.isin(MANUAL_EXCLUSIONS)].copy()
    counts.append(("after_manual_exclusions", len(sample)))

    checks = []
    for name in ("grading.xlsx", "grading_retry.xlsx"):
        quality = pd.read_excel(RAW / name, sheet_name=0)
        quality["qcheck"] = quality.qcheck.replace(3, 1)
        by_id = quality.groupby("prolific_pid").qcheck.agg(["min", "max"])
        by_id = by_id.loc[~by_id.index.astype(str).isin(["", "1", "2", "3", "4"])]
        checks.append(by_id)
    quality = pd.concat(checks)
    duplicates = quality.loc[quality.index.duplicated(keep=False)]
    if len(duplicates):
        assert duplicates.groupby(level=0).nunique(dropna=False).le(1).all().all()
    quality = quality.loc[~quality.index.duplicated(keep="first")]
    sample = sample.merge(quality, left_on="prolific_pid", right_index=True, how="left", validate="one_to_one")
    sample = sample.loc[~(sample["max"].gt(1) | sample["min"].lt(1))].copy()
    counts.append(("after_quality_checks", len(sample)))

    earliest_grade = calendar_day(grades.startdate).groupby(grades.grader_id).min()
    sample["dategraded"] = sample.prolific_pid.map(earliest_grade)
    sample = sample.loc[~sample.datetasked.gt(sample.dategraded)].copy()
    counts.append(("after_prior_grading_exclusion", len(sample)))
    assert sample.prolific_pid.is_unique
    assert sample.treatment.isin([0, 1]).all()
    assert sample.a_first.isin([0, 1]).all()
    assert sample.incentive_arm.isin(["linear", "convex", "exact"]).all()
    return sample, task_dates, counts


def identify_bad_graders(grades):
    """3 - grade cleaning_jul21.do: grader-on-other-grader OLS slope < 0.1.

    Each pair of ratings for the same human essay occurs once. For each grader,
    regress that grader's score on the other score, with an intercept. This is
    the authors' slope criterion, not a Pearson correlation threshold.
    """
    human = grades.loc[~grades.prolific_pid.isin(["chatGPT", "ChatGPT"])]
    pairs = defaultdict(list)
    same_grader_pairs = defaultdict(list)
    for _, essay in human.groupby(["prolific_pid", "essaynum"]):
        entries = list(essay[["grader_id", "overall"]].itertuples(index=False, name=None))
        for (g1, y1), (g2, y2) in combinations(entries, 2):
            pairs[g1].append((y2, y1))
            # The Stata conditional replacement includes a same-grader pair
            # only once, with the earlier indexed rating as the outcome.
            if g2 != g1:
                pairs[g2].append((y1, y2))
            else:
                same_grader_pairs[g1].append(len(pairs[g1]) - 1)
    slopes = {}
    for grader, xy in pairs.items():
        x, y = np.asarray(xy, dtype=float).T
        assert len(x) > 1
        denominator = np.dot(x - x.mean(), x - x.mean())
        slopes[grader] = (float(np.dot(x - x.mean(), y - y.mean()) / denominator)
                          if denominator > 0 else 0.0)
        # Stata does not specify the order of tied essay records. Exhaustively
        # check every orientation of the few same-grader pairs. All possible
        # orderings must give the same include/exclude decision.
        indices = same_grader_pairs.get(grader, [])
        if indices:
            assert len(indices) <= 16
            for flips in product([False, True], repeat=len(indices)):
                alternate = np.asarray(xy, dtype=float).copy()
                for index, flip in zip(indices, flips):
                    if flip:
                        alternate[index] = alternate[index, ::-1]
                ax, ay = alternate.T
                acx, acy = ax - ax.mean(), ay - ay.mean()
                alt_slope = float(np.dot(acx, acy) / np.dot(acx, acx))
                assert (alt_slope < 0.1) == (slopes[grader] < 0.1)
    assert set(human.grader_id) == set(slopes)
    bad = {g for g, slope in slopes.items() if slope < 0.1}
    return bad, slopes


def clean_grades(raw_grades, task_dates):
    """July 21 corrected grade cleaning, without the obsolete private merge."""
    grades = raw_grades.loc[
        raw_grades.grader_id.ne(TEST_GRADER) & raw_grades.retry.ne(1)
    ].copy()
    dategraded = calendar_day(grades.startdate)
    datetasked = grades.grader_id.map(task_dates)
    grades = grades.loc[~dategraded.gt(datetasked) & grades.overall.notna()].copy()
    bad, slopes = identify_bad_graders(grades)
    cleaned = grades.loc[~grades.grader_id.isin(bad)].copy()
    return cleaned, bad, slopes


def attach_participants(grades, participants):
    # Stata's merge preserves shared variables (notably occupation) in the
    # master grading dataset. All participant metadata here are from the survey.
    shared = [c for c in participants if c in grades and c != "prolific_pid"]
    return grades.merge(participants.drop(columns=shared), on="prolific_pid", how="inner", validate="many_to_one")


def task_scores(grades, participants):
    scores = attach_participants(grades, participants)
    scores["post"] = ((scores.a_first.eq(1) & scores.essaynum.eq("B"))
                      | (scores.a_first.eq(0) & scores.essaynum.eq("A")))
    return scores


def paper_regressions(wide, participants, bad):
    """Figure 1B uses wide participant-evaluator data, per main code 35-173."""
    wide = wide.loc[wide.grader_id.ne(TEST_GRADER)
                    & wide.retry_a.ne(1) & wide.retry_b.ne(1)
                    & ~wide.grader_id.isin(bad)].copy()
    wide = attach_participants(wide, participants)
    wide["pre"] = np.where(wide.a_first.eq(1), wide.overall_a, wide.overall_b)
    wide["post"] = np.where(wide.a_first.eq(1), wide.overall_b, wide.overall_a)
    wide["change"] = wide.post - wide.pre
    output = {}
    for name, frame in [("linear_convex", wide.loc[wide.incentive_arm.ne("exact")]), ("all_incentives", wide)]:
        baseline_sd = float(frame.pre.std(ddof=1))
        complete = frame.dropna(subset=["change", "treatment", "grader_id", "occupation", "a_first", "incentive_arm"])
        fit = smf.ols("change ~ treatment + C(grader_id) + C(occupation)*C(a_first) + C(incentive_arm)", data=complete).fit()
        # Use full-rank design for Stata's finite-sample clustered correction.
        x = fit.model.exog
        resid = np.asarray(fit.resid)
        groups = complete.prolific_pid.to_numpy()
        cluster_sums = pd.DataFrame(x * resid[:, None]).groupby(groups).sum().to_numpy()
        bread = np.linalg.pinv(x.T @ x)
        n, k = len(complete), np.linalg.matrix_rank(x)
        n_cluster = len(np.unique(groups))
        covariance = bread @ (cluster_sums.T @ cluster_sums) @ bread
        covariance *= n_cluster / (n_cluster - 1) * (n - 1) / (n - k)
        j = fit.model.exog_names.index("treatment")
        beta = float(fit.params["treatment"])
        se = float(np.sqrt(covariance[j, j]))
        display_coefficient = round(round(beta, 3) / baseline_sd, 2)
        display_se = round(round(se, 3) / baseline_sd, 2)
        output[name] = {
            "coefficient": beta, "se": se, "baseline_rating_sd": baseline_sd,
            "standardized_coefficient": beta / baseline_sd,
            "display_coefficient": display_coefficient,
            "display_se": display_se,
            "display_ci_lower": round(display_coefficient - 1.96 * display_se, 2),
            "display_ci_upper": round(display_coefficient + 1.96 * display_se, 2),
            "n_ratings": n, "n_people": n_cluster,
            "n_by_arm": {int(a): int(z.prolific_pid.nunique()) for a, z in complete.groupby("treatment")},
        }
    return output


def verify_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {
        str(Path(item["path"])).casefold(): item
        for deposit in manifest["deposits"].values()
        for item in deposit.get("files", {}).values()
        if item.get("path")
    }
    for path in DATA_FILES:
        entry = entries[str(path).casefold()]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], f"Manifest hash mismatch: {path}"


def check(statistic, printed, computed, digits=0):
    value = int(computed) if digits == 0 and float(computed).is_integer() else float(computed)
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": value,
        "match": bool(round(value, digits) == printed),
    }


def participant_summary(post):
    # The reproduction gate in main() precedes this function. One second-task
    # score per person is the mean of all retained ratings for that person.
    people = post.groupby(["prolific_pid", "treatment"], as_index=False).overall.mean()
    assert people.prolific_pid.is_unique
    treatment = people.loc[people.treatment.eq(1), "overall"]
    control = people.loc[people.treatment.eq(0), "overall"]
    assert len(treatment) > 1 and len(control) > 1
    design = sm.add_constant(people.treatment, has_constant="add")
    fit = sm.OLS(people.overall, design).fit(cov_type="HC2")
    difference = float(treatment.mean() - control.mean())
    difference_se = float(fit.bse["treatment"])
    # In a two-arm regression with an intercept, HC2 reduces exactly to this
    # independent-groups variance formula using sample variances (ddof=1).
    algebraic_se = math.sqrt(treatment.var(ddof=1) / len(treatment)
                             + control.var(ddof=1) / len(control))
    assert math.isclose(difference, float(fit.params["treatment"]), abs_tol=1e-12)
    assert math.isclose(difference_se, algebraic_se, abs_tol=1e-12)
    return {
        "n_treatment": len(treatment),
        "n_control": len(control),
        "treatment_mean": float(treatment.mean()),
        "treatment_sd": float(treatment.std(ddof=1)),
        "control_mean": float(control.mean()),
        "control_sd": float(control.std(ddof=1)),
        "difference": difference,
        "difference_se": difference_se,
        "se_type": "HC2",
        "n_clusters": None,
    }


def source_files_read():
    # Include the source documents and deposited programs consulted as TEXT in
    # the input inventory; no deposited program is imported or executed.
    retrieval = ROOT / "retrieval.json"
    record = json.loads(retrieval.read_text(encoding="utf-8"))["c503"]
    sources = [
        MANIFEST, EXTRACTION, retrieval,
        ROOT.parent / "creativity-codebook.md",
        ROOT / "extraction-spec.md",
        Path(record["pdf_path"]), Path(record["md_path"]),
        DEPOSIT / "ReadMe for Replication Pkg.pdf",
        DEPOSIT / "ReadMe - update 07-21-2023.pdf",
    ]
    sources.extend(DEPOSIT / "code" / name for name in [
        "0 - Master.do", "00 - grade formatting.py", "2 - clean.do",
        "3 - grade cleaning.do", "3 - grade cleaning_jul21.do",
        "4 - main text figures.do", "5 - appendix figures.do",
    ])
    for path in sources:
        if path.suffix.lower() == ".pdf":
            # PDF text was inspected with pymupdf during source reconciliation.
            assert path.read_bytes().startswith(b"%PDF")
        else:
            path.read_text(encoding="utf-8-sig")
    return sources


def main():
    verify_manifest()
    sources = source_files_read()
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    estimates = {estimate["slug"]: estimate for estimate in extraction["estimates"]}
    figure_slug = "s1_average_grade_chatgpt_vs_control_figure1"
    text_slug = "s1_average_grade_chatgpt_vs_control_text"
    figure = estimates[figure_slug]["stats"]

    survey = read_csv(RAW / "fullsurvey.csv")
    long = read_csv(RAW / "grading_long_complete.csv")
    wide = read_csv(RAW / "grading_wide_complete.csv")
    alternative_survey = read_csv(ALTERNATIVE / "fullsurvey.csv", usecols=["prolific_pid"])
    alternative_grades = read_csv(ALTERNATIVE / "grading_long_complete.csv", usecols=["prolific_pid"])
    sample, task_dates, flow = clean_participants(survey, long)
    grades, bad, slopes = clean_grades(long, task_dates)
    scores = task_scores(grades, sample)
    post = scores.loc[scores.post & scores.incentive_arm.ne("exact")].copy()
    baseline = scores.loc[~scores.post].groupby(["prolific_pid", "treatment"]).overall.mean().reset_index()
    models = paper_regressions(wide, sample, bad)
    model = models["linear_convex"]
    arm_means = post.groupby("treatment").overall.mean()
    full_counts = sample.groupby("treatment").size()
    baseline_stats = baseline.groupby("treatment").overall.agg(["count", "mean"])

    # Printed references checked directly against PDF pp. 3, 12, 18.
    # Table 1 counts validate the FULL sample; they are not Figure 1 analysis Ns.
    reproduced = [
        check("Figure 1D treatment_mean (individual evaluator ratings)", figure["treatment_mean"], arm_means[1], 2),
        check("Figure 1D control_mean (individual evaluator ratings)", figure["control_mean"], arm_means[0], 3),
        check("Figure 1B standardized adjusted grade-change coefficient", figure["paper_effect"]["value"], model["standardized_coefficient"], 2),
        check("Figure 1B displayed 95% CI lower (authors' rounding procedure)", figure["ci_lower"], model["display_ci_lower"], 2),
        check("Figure 1B displayed 95% CI upper (authors' rounding procedure)", figure["ci_upper"], model["display_ci_upper"], 2),
        check("Method full-sample participant count", 453, len(sample)),
        check("Table 1 full-sample treatment participant count (occupation rows)", 218, full_counts[1]),
        check("Table 1 full-sample control participant count (occupation rows)", 235, full_counts[0]),
        check("Table 1 baseline average-grade treatment participant count", 211, baseline_stats.loc[1, "count"]),
        check("Table 1 baseline average-grade control participant count", 233, baseline_stats.loc[0, "count"]),
        check("Table 1 baseline average-grade treatment mean", 3.77, baseline_stats.loc[1, "mean"], 2),
        check("Table 1 baseline average-grade control mean", 3.63, baseline_stats.loc[0, "mean"], 2),
    ]

    results, skipped = [], []
    if all(item["match"] for item in reproduced):
        computed = participant_summary(post)
        notes = (
            "Source is the saved 19-page NBER Summer Institute author manuscript: "
            "PDF pp. 3-4, 12-13 and 18-19, with the entire markdown conversion read. "
            "The OSF deposit named on PDF p. 11 is osf-xd7qw. All seven inspected "
            "data files match their manifest SHA-256 hashes. The older osf-q3gdu "
            f"files contain {len(alternative_survey)} survey rows and {len(alternative_grades)} "
            f"grading rows, versus {len(survey)} and {len(long)} in osf-xd7qw; they are "
            "not combined. Participant exclusions follow 2 - clean.do, lines 28-174: "
            "completion/consent, earliest response per participant, six explicitly "
            "listed IDs, Excel quality checks (3 recoded to 1), and having graded "
            "before doing the task survey. Row counts after these successive stages "
            f"are {', '.join(str(n) for _, n in flow)}. Grading follows the corrected "
            "3 - grade cleaning_jul21.do specified in the July 21 ReadMe: exclude "
            "the tester, retry submissions, graders who previously completed the "
            "task survey, missing overall grades, and graders whose own-score "
            "regression on other evaluators' scores has slope below 0.1. This "
            f"excludes {len(bad)} of {len(slopes)} evaluators with human-essay pairs. "
            "All possible orderings of repeated same-grader pairs yield the same "
            "exclusion decisions. The authors retain repeated grading-session "
            "records; this analysis does likewise.\n\n"
            "4 - main text figures.do, lines 556-588, establishes that Figure 1D "
            "uses the overall grade, not an average of overall, writing, content "
            "and originality. Keep linear and convex incentive arms, join cleaned "
            "long ratings to the cleaned participant sample, and select essay B "
            "when a_first=1 and essay A when a_first=0. The printed means are "
            f"rating-weighted: {len(post.loc[post.treatment.eq(1)])} treatment and "
            f"{len(post.loc[post.treatment.eq(0)])} control ratings. The paper does "
            "not print Figure 1 analysis participant counts; the new counts are "
            f"{computed['n_treatment']} treatment and {computed['n_control']} control. "
            "The reproduced Table 1 counts and baseline means verify the cleaning "
            "pipeline but refer to all three incentive arms, not the Figure 1 sample.\n\n"
            "Figure 1B separately uses the authors' wide participant-evaluator "
            "dataset: regress post-minus-pre overall grade on treatment, grader "
            "fixed effects, occupation-by-task-order fixed effects and incentive "
            "fixed effects, with participant-clustered SEs. This uses "
            f"{model['n_ratings']} records from {model['n_people']} people "
            f"({model['n_by_arm'][1]} treatment, {model['n_by_arm'][0]} control); "
            f"raw coefficient={model['coefficient']:.12g}, clustered SE={model['se']:.12g}, "
            f"and pre-treatment rating SD={model['baseline_rating_sd']:.12g}. "
            "As in code lines 155-172 and 298-300, round the raw coefficient/SE "
            "to 0.001, divide by the pre-treatment rating SD, round to 0.01, "
            "and form/round the displayed interval using 1.96. This reproduces "
            "0.41 and [0.23, 0.59]. These are replication checks, not the new "
            "participant-level effect or SE.\n\n"
            "Computed fields use the Figure 1D post-treatment sample, averaging "
            "all retained overall ratings within each person before taking equally "
            "weighted arm means and sample SDs (ddof=1). Difference is the raw "
            "post-treatment treatment-minus-control mean difference on the 1-7 "
            "scale. Its SE is from OLS of this participant mean on an intercept "
            "and treatment indicator with HC2; independently checked against "
            "sqrt(s_treatment^2/n_treatment + s_control^2/n_control). Individual "
            "randomization justifies HC2 and n_clusters=null. The first task is "
            "a common baseline, not a randomized alternate AI condition; there "
            "is no paired crossover or first_round contrast. round=all denotes "
            "the sole post-intervention between-person comparison."
        )
        results.append({"slug": figure_slug, "round": "all", "reproduced": reproduced,
                        "computed": computed, "notes": notes})
    else:
        discrepancies = [item for item in reproduced if not item["match"]]
        skipped.append({"slug": figure_slug,
                        "reason": "Reproduction failed; no participant-level effect computed. "
                                  + json.dumps(discrepancies, ensure_ascii=False)})

    prose_effect = estimates[text_slug]["stats"]["paper_effect"]["value"]
    skipped.append({
        "slug": text_slug,
        "reason": (
            f"PDF p. 4 prints {prose_effect:.2f} SD (p<0.001), but does not identify "
            "a separate sample/model/standardizer or analysis counts for that prose "
            "record. The documented main linear/convex grade-change model reproduces "
            f"{model['standardized_coefficient']:.12g} SD, which rounds to "
            f"{model['display_coefficient']:.2f}, not {prose_effect:.2f}. Its estimation "
            f"sample has {model['n_by_arm'][1]} treated and {model['n_by_arm'][0]} "
            "control people. The authors' same documented model pooling all incentive "
            f"arms gives {models['all_incentives']['standardized_coefficient']:.12g} SD "
            f"(rounded {models['all_incentives']['display_coefficient']:.2f}; "
            f"{models['all_incentives']['n_by_arm'][1]} treated and "
            f"{models['all_incentives']['n_by_arm'][0]} control people), also not "
            f"{prose_effect:.2f}. No separate participant statistics are computed "
            "for this unreproduced record; Figure 1's numbers are not substituted."
        ),
    })
    variables = {
        "s1_originality_chatgpt_vs_control": "originality",
        "s1_overall_grade_chatgpt_vs_control": "overall",
        "s1_writing_quality_chatgpt_vs_control": "writing",
        "s1_content_quality_chatgpt_vs_control": "content",
    }
    for slug, variable in variables.items():
        estimate = estimates[slug]
        assert all(value is None for value in estimate["stats"].values())
        reason = (
            f"The deposited grades contain the {variable} variable, but the saved "
            "paper and reconciled extraction report only a qualitative similar "
            "increase for this record (PDF p. 4). No record-specific arm means, "
            "difference/coefficient or analysis counts are printed. Therefore the "
            "required estimate-specific numerical reproduction cannot be performed, "
            "and no participant-level statistics are computed under rule 3."
        )
        if variable == "overall":
            reason += (
                " The authors' code uses overall for Figure 1, which is verified "
                "under the separate figure slug; the paper supplies no distinct "
                "numerical contrast for this additional extraction record."
            )
        skipped.append({"slug": slug, "reason": reason})

    covered = [item["slug"] for item in results + skipped]
    assert set(covered) == set(estimates)
    assert len(covered) == len(set(covered))
    output = {
        "cid": "c503", "analyst": "A", "script": SCRIPT.as_posix(),
        "data_files": [path.as_posix() for path in DATA_FILES + sources],
        "results": results, "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        reparsed = json.load(fh)
    assert reparsed == output
    assert not any(ord(character) > 127 for character in SCRIPT.read_text(encoding="utf-8"))
    summary = {
        "cid": "c503", "n_results": len(results),
        "n_reproduced": sum(all(stat["match"] for stat in result["reproduced"])
                            for result in results),
        "n_skipped": len(skipped),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
