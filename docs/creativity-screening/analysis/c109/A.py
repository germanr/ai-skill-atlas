"""Reproduce c109's printed descriptives, then estimate supported raw contrasts.

Run with python -I -B and this script's absolute path. The sole output is A.json.
No deposited program is imported or executed. All input paths are absolute.

The three eligible non-homogenization outcomes are jointly scored dyad outputs.
Individual outcomes cannot be recovered. Accordingly, participant SDs are null;
the supported raw means and differences retain the original dyad-outcome units.
Counts are people (two per observed dyad); OLS uncertainty is clustered by dyad.
"""

import sys

sys.dont_write_bytecode = True

import csv
import io
import json
import math
import statistics
from pathlib import Path

import numpy as np
import pymupdf
import statsmodels.api as sm


BASE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(
    r"D:/projects/ai-skill-atlas/creativity-data/osf-nmqd5/"
    r"Supplemental Material-unpacked/Supplemental Material"
)
SCRIPT = BASE / "analysis/c109/A.py"
OUTPUT = BASE / "analysis/c109/A.json"
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
CODEBOOK = BASE.parent / "creativity-codebook.md"

READ_FILES = []


def register(path):
    path = Path(path)
    assert path.is_absolute()
    name = path.as_posix()
    if name not in READ_FILES:
        READ_FILES.append(name)
    return path


def read_text(path, encoding="utf-8"):
    return register(path).read_text(encoding=encoding)


def read_json(path):
    return json.loads(read_text(path))


def read_csv(name, encoding="utf-8-sig"):
    return list(csv.DictReader(io.StringIO(read_text(DEPOSIT / name, encoding))))


def as_float(value):
    return float(value) if value.strip() else None


def check(statistic, printed, computed, digits=None):
    if printed is None or computed is None:
        raise ValueError("Unknown printed values cannot be called matches or failures.")
    comparison = round(computed, digits) if digits is not None else computed
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(comparison == printed),
    }


def null_computed():
    return dict.fromkeys(
        [
            "n_treatment", "n_control", "treatment_mean", "treatment_sd",
            "control_mean", "control_sd", "difference", "difference_se",
            "se_type", "n_clusters",
        ]
    )


def observed(rows, outcome):
    return [row for row in rows if as_float(row[outcome]) is not None]


def covariate_complete(rows):
    return [row for row in rows if row["dsgn"].strip() and row["know"].strip()]


def values_by_arm(rows, outcome):
    return {
        arm: [float(row[outcome]) for row in rows if row["cue"] == arm]
        for arm in ("cue", "no cue")
    }


def describe(rows, outcome):
    arms = values_by_arm(rows, outcome)
    return {
        arm: {
            "n_dyads": len(values),
            "mean": statistics.mean(values),
            "sd": statistics.stdev(values),
        }
        for arm, values in arms.items()
    }


def sample_note(rows):
    cells = {}
    for row in rows:
        key = row["cue"] + "/" + row["modality"]
        cells[key] = cells.get(key, 0) + 1
    return ", ".join(f"{key}={value}" for key, value in sorted(cells.items()))


def cluster_ols(rows, outcome):
    """OLS on observed dyad outputs, with Session clusters and CR1 correction.

    Each cluster has one jointly produced, scored observation. No individual
    observations are fabricated by duplicating the dyad score. The sandwich is
    (X'X)^-1 [sum_g X_g'u_g u_g'X_g] (X'X)^-1 multiplied by
    G/(G-1) * (N-1)/(N-K), where N=G is the observed dyad count and K=2.
    """
    x = np.asarray([[1.0, float(row["cue"] == "cue")] for row in rows])
    y = np.asarray([float(row[outcome]) for row in rows])
    groups = np.asarray([row["Session"] for row in rows])
    fit = sm.OLS(y, x).fit(
        cov_type="cluster",
        cov_kwds={"groups": groups, "use_correction": True},
    )
    n, k = x.shape
    g = len(set(groups))
    assert g == n and g > k
    bread = np.linalg.inv(x.T @ x)
    residual = y - x @ fit.params
    cluster_scores = np.asarray(
        [x[groups == label].T @ residual[groups == label] for label in sorted(set(groups))]
    )
    correction = (g / (g - 1)) * ((n - 1) / (n - k))
    covariance = bread @ (cluster_scores.T @ cluster_scores) @ bread * correction
    assert np.allclose(covariance, fit.cov_params(), rtol=1e-10, atol=1e-12)
    return float(fit.params[1]), math.sqrt(float(covariance[1, 1]))


def reproduced_topic(estimate, raw_rows, outcome, roster_checks, specific_note):
    # Reproduction precedes computation of any contrast or uncertainty.
    rows = observed(raw_rows, outcome)
    desc = describe(rows, outcome)
    checks = [dict(item) for item in roster_checks]
    for arm, prefix in (("cue", "treatment"), ("no cue", "control")):
        for statistic in ("mean", "sd"):
            key = prefix + "_" + statistic
            checks.append(check(key, estimate["stats"][key], desc[arm][statistic], 1))

    common_note = (
        "Reproduction is of the printed, unadjusted arm descriptives at one decimal "
        "place, using the authors' deposited dyad scores; the original text-to-score "
        "pipeline is not rerun. Both meeting modalities are pooled, cue is treatment, "
        "and no cue is control. The reproduced SDs are across dyads, with denominator "
        "n_dyads-1. No participant-attributed ideas, topic labels, or individual "
        "scores are deposited. Therefore the requested participant-level SD fields "
        "are null: copying each shared dyad score to two invented individual records "
        "would not recover those scores. The reported means and difference are in "
        "the original shared-dyad outcome units. All dyads contain two people "
        "(PDF p. 5, printed p. 300, section 4.1.1), so equal-dyad and "
        "equal-person weighting of the shared outcome yield identical means. "
        "People counts are twice the observed dyad counts, not counts of ideas, "
        "ratings, or post-survey responses. Study roster checks compare the 86 "
        "distinct session rows and their 172 dyad members with the printed study "
        "totals; they do not establish the paper's outcome-specific analysis counts, "
        "which are not printed. The post surveys have a missing response and "
        "duplicate participant labels (S67P1 and S22P1) and are not used as an "
        "exclusion rule or as a unique-person roster. No missing score or background "
        "covariate is imputed. Missing design/recycling covariates are retained "
        "for these outcome-available descriptives and the new unadjusted contrast. "
        "The paper's REML models instead exclude missing covariates and use cue, "
        "modality, and their interaction as fixed effects plus design and recycling "
        "knowledge as random effects. The REML F statistics, denominator degrees "
        "of freedom, and p values are not claimed reproduced. Standard errors below "
        "come from OLS of one shared dyad score on an intercept and cue indicator, "
        "clustered by Session with CR1 correction G/(G-1)*(N-1)/(N-2), N=G. "
        "These are new raw contrasts on the samples reproducing the descriptives, "
        "not the paper's covariate-complete adjusted model. This is a between-dyad "
        "design, so no first_round result applies. "
    )
    notes = common_note + specific_note + " Observed cells: " + sample_note(rows) + "."
    result = {
        "slug": estimate["slug"],
        "round": "all",
        "reproduced": checks,
        "computed": null_computed(),
        "notes": notes,
    }
    if not all(item["match"] for item in checks):
        result["notes"] += " Reproduction failed; no contrast or standard error computed."
        return result

    coefficient, se = cluster_ols(rows, outcome)
    difference = desc["cue"]["mean"] - desc["no cue"]["mean"]
    assert math.isclose(coefficient, difference, rel_tol=1e-12, abs_tol=1e-12)
    result["computed"].update(
        n_treatment=2 * desc["cue"]["n_dyads"],
        n_control=2 * desc["no cue"]["n_dyads"],
        treatment_mean=desc["cue"]["mean"],
        control_mean=desc["no cue"]["mean"],
        difference=difference,
        difference_se=se,
        se_type="cluster",
        n_clusters=len(rows),
    )
    return result


def main():
    extraction = read_json(BASE / "extraction/c109.json")
    retrieval = read_json(BASE / "retrieval.json")["c109"]
    manifest = read_json(MANIFEST)
    read_text(CODEBOOK)
    read_text(BASE / "extraction-spec.md")
    markdown = read_text(retrieval["md_path"])
    assert "19.4 ideas" in markdown
    with pymupdf.open(register(retrieval["pdf_path"])) as doc:
        pdf_text = {i + 1: doc[i].get_text() for i in (4, 6, 8, 10, 15, 16)}
    assert "19.4 ideas" in pdf_text[7]
    assert "172 participants" in pdf_text[5]
    assert "86 dyads" in pdf_text[5]
    assert "osf-nmqd5" in manifest["deposits"]

    read_text(DEPOSIT / "Supplementary Data README.txt", "utf-8-sig")
    idea = read_csv("Idea_012-use-correct.csv")
    conversation = read_csv("conversation-final-use-correct.csv")
    # These are read only as survey data to audit roster limitations; their
    # self-report outcomes are outside the extraction and are never analyzed.
    cue_survey = read_csv("cue_condition_post.csv")
    nocue_survey = read_csv("nocue_condition_post.csv", "cp1252")
    assert len(cue_survey) == 83 and len(nocue_survey) == 88

    for rows in (idea, conversation):
        assert len(rows) == len({row["Session"] for row in rows})
        assert {row["cue"] for row in rows} == {"cue", "no cue"}
        assert {row["modality"] for row in rows} == {"inperson", "virtual"}
    by_session = {row["Session"]: row for row in idea}
    for row in conversation:
        assert row["Session"] in by_session
        for column in ("cue", "modality", "dsgn", "know", "# of all ideas", "AttendedCues"):
            assert row[column] == by_session[row["Session"]][column]

    study = extraction["studies"][0]
    assert study["assignment_unit"] == "team"
    estimates = {entry["slug"]: entry for entry in extraction["estimates"]}
    roster_checks = [
        check("study_dyads_listed", 86, len(by_session)),
        check("study_people_represented", study["n_randomized"], 2 * len(by_session)),
    ]

    idea_rows = observed(idea, "Topic diversity")
    idea_complete = covariate_complete(idea_rows)
    idea_complete_desc = describe(idea_complete, "Topic diversity")
    missing_ideas = [row["Session"] for row in idea if not row["Topic diversity"].strip()]
    missing_idea_covariates = [row["Session"] for row in idea if not row["dsgn"].strip() or not row["know"].strip()]
    idea_note = (
        "Source: PDF p. 7 (printed p. 302), sections 4.1.4 and 5.1.1; "
        "Supplementary Data README.txt defines Topic diversity as Shannon entropy "
        "of topics from the dyad's ideas. The source file has 86 distinct session "
        f"rows. Missing outcomes are {', '.join(missing_ideas)}, leaving "
        f"{len(idea_rows)} dyads (41 cue, 43 no cue; 82 and 86 people). "
        "The source includes sessions S1-S88 except S51 and S86; no outcome or "
        "participant is invented for missing identifiers. The paper's descriptions "
        "of technical/echo exclusions cannot be linked to additional session IDs, "
        "so no further sessions are dropped. Missing background covariates occur "
        f"in {len(missing_idea_covariates)} dyad rows: {', '.join(missing_idea_covariates)}. "
        "Section 4.1.1 refers to 13 participants rather than 13 dyads; this file "
        "does not identify which member lacked covariates. Restricting to complete "
        f"covariates would leave {len(idea_complete)} dyads (34 cue, 38 no cue) "
        f"with means {idea_complete_desc['cue']['mean']:.12f} and "
        f"{idea_complete_desc['no cue']['mean']:.12f}, SDs "
        f"{idea_complete_desc['cue']['sd']:.12f} and "
        f"{idea_complete_desc['no cue']['sd']:.12f}. Those also round to the printed "
        "descriptives, so the printed precision cannot uniquely identify the idea "
        "descriptive sample. The result uses all observed scores, consistently with "
        "the conversation descriptives; it is explicitly not asserted to recover "
        "the REML sample. No individual topic assignments or embedding model are "
        "in the deposit, so only the supplied entropy scores and their arm summaries "
        "are verified. This within-dyad flexibility outcome is distinct from the "
        "unavailable across-dyad homogenization measure."
    )

    conversation_complete = covariate_complete(conversation)
    conv_complete_desc = describe(conversation_complete, "Topic_diversity")
    missing_conversation_covariates = [row["Session"] for row in conversation if not row["dsgn"].strip() or not row["know"].strip()]
    conversation_note = (
        "Source: PDF p. 9 (printed p. 304), section 5.1.2; PDF p. 7 (printed "
        "p. 302), section 4.1.4 and footnote 12; Supplementary Data README.txt. "
        "Topic_diversity is the number of distinct broad IAB topics across the "
        "entire dyad conversation. All 66 deposited conversation rows have scores: "
        "29 cue and 37 no cue dyads, representing 58 and 74 people. The 66 rows "
        "are compatible with footnote 12's 70 recordings and 4 echo exclusions, "
        "but the footnote's additional 16 recordings and the exclusions in section "
        "4.1.1 do not establish an unambiguous complete flow of participants; "
        "counts here come from the deposited sessions, not subtraction from the "
        "recruited total or model degrees of freedom. Missing covariates occur in "
        f"{len(missing_conversation_covariates)} rows: {', '.join(missing_conversation_covariates)}. "
        f"Complete-covariate analysis would use {len(conversation_complete)} dyads "
        "(22 cue, 33 no cue; 44 and 66 people), with means "
        f"{conv_complete_desc['cue']['mean']:.12f} and "
        f"{conv_complete_desc['no cue']['mean']:.12f}, SDs "
        f"{conv_complete_desc['cue']['sd']:.12f} and "
        f"{conv_complete_desc['no cue']['sd']:.12f}; these round to 9.7, 8.1, "
        "2.3, and 2.6 and do not reproduce the printed 9.6, 8.0, 2.2, and 2.5. "
        "The descriptives therefore identify the outcome-available sample rather "
        "than the sample excluding missing background covariates. No transcription "
        "or IAB classification is rerun because only the final scores are posted."
    )

    results = [
        reproduced_topic(
            estimates["s1_idea_topic_diversity_cue_vs_nocue"], idea, "Topic diversity",
            roster_checks, idea_note,
        ),
        reproduced_topic(
            estimates["s1_conversation_topics_cue_vs_nocue"], conversation,
            "Topic_diversity", roster_checks, conversation_note,
        ),
    ]

    # The paper provides neither arm descriptives nor a numerical contrast for
    # fluency. Its only quantitative outcome check, the overall mean, also fails.
    # Do not calculate any arm contrast, arm SD, or uncertainty for this estimate.
    count_rows = observed(idea, "# of all ideas")
    count_complete = covariate_complete(count_rows)
    overall_count_mean = statistics.mean(float(row["# of all ideas"]) for row in count_rows)
    complete_count_mean = statistics.mean(float(row["# of all ideas"]) for row in count_complete)
    count_checks = [dict(item) for item in roster_checks] + [
        check("overall_idea_count_mean_all_available_dyads", 19.4, overall_count_mean, 1),
        check("overall_idea_count_mean_complete_covariates", 19.4, complete_count_mean, 1),
    ]
    results.append({
        "slug": "s1_idea_count_cue_vs_nocue",
        "round": "all",
        "reproduced": count_checks,
        "computed": null_computed(),
        "notes": (
            "Reproduction failed; no requested effect statistics are calculated. "
            "The '# of all ideas' column is the README-defined dyad idea count. "
            "PDF p. 7 (printed p. 302), section 5, prints an overall mean of 19.4 "
            f"ideas. The {len(count_rows)} nonmissing rows (S5 and S15 missing) "
            f"sum to {sum(int(row['# of all ideas']) for row in count_rows)} ideas "
            f"and give {overall_count_mean:.12f}, rounding to 19.7 rather than "
            f"19.4. Applying the stated covariate exclusion leaves {len(count_complete)} "
            f"dyads and gives {complete_count_mean:.12f}, rounding to 19.9. "
            "No additional exclusion IDs or analysis code are supplied that "
            "resolve the mismatch. PDF p. 9 (printed p. 304), section 5.1.3, "
            "prints only a verbal non-significance conclusion, with no arm means, "
            "difference/coefficient, test statistic, p value, or analyzed arm "
            "counts; thus even the minimum arm-contrast reproduction check has "
            "no numerical target. The failed checks are retained as an analyzed "
            "result for audit, with every computed field null. This record is not "
            "counted as a reproduced estimate and is not duplicated in skipped."
        ),
    })

    skipped = [{
        "slug": "s1_idea_homogenization_cue_vs_nocue",
        "reason": (
            "Cannot follow the paper's semantic-diversity procedure exactly. "
            "The deposit contains only dyad summary outcomes and post-survey "
            "responses; it has no human idea texts, idea embeddings, cosine "
            "distances, or text-to-dyad mapping. The embedding model is not named, "
            "and PDF p. 11 (printed p. 306), section 6.3, describes condition-specific "
            "centroids whereas PDF p. 16 (printed p. 311), Appendix A.4.1, describes "
            "an average across Cue and NoCue ideas. PDF p. 17 (printed p. 312), "
            "Figure 6, has distributions only, with no printed human-arm means, "
            "counts, Wilcoxon statistic, or numerical uncertainty to reproduce. "
            "No embedding model or centroid convention is guessed, no values "
            "are taken from plotted positions, and no participant-level values "
            "or standardized effect are assigned to this set-based measure."
        ),
    }]

    assert {row["slug"] for row in results + skipped} == set(estimates)
    assert len(results + skipped) == len(estimates)
    obj = {
        "cid": "c109",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": READ_FILES,
        "results": results,
        "skipped": skipped,
    }
    # User-prescribed JSON serialization, with no auxiliary files.
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    n_reproduced = sum(
        bool(result["reproduced"])
        and all(item["match"] for item in result["reproduced"])
        and result["computed"]["difference"] is not None
        for result in results
    )
    print(json.dumps({
        "cid": "c109", "n_results": len(results),
        "n_reproduced": n_reproduced, "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
