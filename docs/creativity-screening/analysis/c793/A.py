"""Independent analysis A for c793.

Run: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c793/A.py
Only A.json is written. Deposit notebooks are parsed as JSON/text, never executed.
The manuscript was read in full, including Supporting Information, and cited
PDF pages were checked with PyMuPDF. See each result's notes for provenance.
"""
import sys
sys.dont_write_bytecode = True

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data/dataverse-ATXBCK")
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
SCRIPT = ROOT / "analysis/c793/A.py"
OUTPUT = ROOT / "analysis/c793/A.json"
EXTRACTION = ROOT / "extraction/c793.json"
RATINGS = "Replication Data for Designing Human and Generative AI Collaboration.csv"
SUPPLEMENT = "Supplementary Material.ipynb"
FIGURE4 = "Fig. 4. Treatment effects on content diversity.ipynb"
NOTEBOOKS = [SUPPLEMENT, "Fig. 2. Effects on overall story quality.ipynb",
             FIGURE4, "Table 1. Descriptive statistics.ipynb"]
ARMS = ["Human Confirmation", "Human Creativity", "Copilot"]
GENRE_FILES = {
    "Human Confirmation": "genre_Confirmation.csv",
    "Human Creativity": "genre_Creativity.csv",
    "Copilot": "genre_Copilot.csv",
    "Without AI": "genre_day1.csv",
}
EMBEDDING_FILES = {
    "Human Confirmation": "3large_result_df_B.csv",
    "Human Creativity": "3large_result_df_A.csv",
    "Copilot": "3large_result_df_C.csv",
    "Without AI": "3large_result_df_Day1.csv",
}
GENRES = ["Horror Fiction", "Mystery/Crime Fiction", "Romance", "Sci-Fi",
          "Thriller/Suspense", "Western Fiction", "Historical Fiction",
          "Young Adult Fiction", "Fantasy"]
COVARIATES = ["DAT", "Experience", "Ability", "English"]
OUTCOMES = {"Overall story quality": "Overall", "Originality": "Originality",
            "Interestingness": "Interestingness", "Writing quality": "Writing",
            "Coherence": "Coherence"}
TABLE1 = {"Overall": (4.91, 1.35), "Originality": (4.97, 1.38),
          "Interestingness": (4.87, 1.46), "Writing": (5.21, 1.37),
          "Coherence": (5.20, 1.36)}


def check(statistic, printed, computed, digits=0):
    """Compare to the number of decimal places actually printed, not float repr."""
    computed = float(computed)
    assert np.isfinite(computed)
    matches = format(computed, f".{digits}f") == format(float(printed), f".{digits}f")
    return {"statistic": statistic, "printed": printed,
            "computed": int(computed) if digits == 0 and computed.is_integer() else computed,
            "match": bool(matches)}


def bound_check(statistic, printed, computed):
    assert printed.startswith("<")
    return {"statistic": statistic, "printed": printed, "computed": float(computed),
            "match": bool(computed < float(printed[1:]))}


def arm_summary(values):
    a = np.asarray(values, dtype=float)
    assert a.ndim == 1 and len(a) > 1 and np.isfinite(a).all()
    mean = float(a.mean())
    margin = float(stats.sem(a) * stats.t.ppf(0.975, len(a) - 1))
    return {"n": len(a), "mean": mean, "ci_lower": mean - margin,
            "ci_upper": mean + margin}


def participant_contrast(treatment, control):
    """Unadjusted OLS on one value per randomized person; HC2 covariance."""
    treatment = np.asarray(treatment, dtype=float)
    control = np.asarray(control, dtype=float)
    assert np.isfinite(treatment).all() and np.isfinite(control).all()
    nt, nc = len(treatment), len(control)
    assert min(nt, nc) > 1
    y = np.concatenate([control, treatment])
    indicator = np.concatenate([np.zeros(nc), np.ones(nt)])
    design = np.column_stack([np.ones(nt + nc), indicator])
    fit = sm.OLS(y, design).fit(cov_type="HC2")
    mt, mc = float(treatment.mean()), float(control.mean())
    st, sc = float(treatment.std(ddof=1)), float(control.std(ddof=1))
    difference = mt - mc
    se = float(fit.bse[1])
    # An intercept plus a binary arm indicator gives this same HC2 variance.
    assert np.isclose(fit.params[1], difference, atol=1e-12)
    assert np.isclose(se, np.sqrt(st * st / nt + sc * sc / nc), atol=1e-12)
    return {"n_treatment": nt, "n_control": nc, "treatment_mean": mt,
            "treatment_sd": st, "control_mean": mc, "control_sd": sc,
            "difference": difference, "difference_se": se,
            "se_type": "HC2", "n_clusters": None}


def notebook_text_output(notebook, cell):
    parts = []
    for output in notebook["cells"][cell].get("outputs", []):
        if "text" in output:
            parts.append("".join(output["text"]))
        else:
            parts.append("".join(output.get("data", {}).get("text/plain", [])))
    return "\n".join(parts)


def notebook_nobs(notebook, cell):
    text = notebook_text_output(notebook, cell)
    match = re.search(r"No\. Observations:\s+(\d+)", text)
    assert match is not None
    return int(match.group(1))


def rating_model(data, outcome, adjusted):
    columns = [outcome] + (COVARIATES if adjusted else [])
    selected = data.loc[data["Day"].eq(2)].dropna(subset=columns).copy()
    x = pd.DataFrame({"const": 1.0,
                      "creativity": selected.Group.eq("Human Creativity").astype(float),
                      "copilot": selected.Group.eq("Copilot").astype(float)},
                     index=selected.index)
    if adjusted:
        for name in COVARIATES:
            x[name] = selected[name].astype(float)
    fit = sm.OLS(selected[outcome].astype(float), x).fit()
    return selected, x, fit


def contrast_vector(treatment, control, columns):
    vector = np.zeros(len(columns))
    names = {"Human Creativity": "creativity", "Copilot": "copilot"}
    if treatment in names:
        vector[list(columns).index(names[treatment])] += 1
    if control in names:
        vector[list(columns).index(names[control])] -= 1
    return vector


def means_and_intervals_checks(estimate, treatment, control, digits):
    s = estimate["stats"]
    return [check("treatment_mean", s["treatment_mean"], treatment["mean"], digits),
            check("control_mean", s["control_mean"], control["mean"], digits),
            check("treatment_mean_ci_lower", s["ci_lower"], treatment["ci_lower"], digits),
            check("treatment_mean_ci_upper", s["ci_upper"], treatment["ci_upper"], digits),
            check("control_mean_ci_lower", s["control_ci_lower"], control["ci_lower"], digits),
            check("control_mean_ci_upper", s["control_ci_upper"], control["ci_upper"], digits)]


def failed_reproduction(estimate, checks):
    bad = [c for c in checks if not c["match"]]
    return {"slug": estimate["slug"],
            "reason": "Reproduction failed; no participant or set contrast computed. "
                      + json.dumps(bad, ensure_ascii=True)}


def main():
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    file_manifest = manifest["deposits"]["dataverse-ATXBCK"]["files"]
    filenames = [RATINGS] + list(GENRE_FILES.values()) + list(EMBEDDING_FILES.values()) + NOTEBOOKS
    assert len(filenames) == len(set(filenames))
    for name in filenames:
        payload = (DEPOSIT / name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == file_manifest[name]["sha256"], name
    # JSON parsing and plain-text inspection only; no notebook code is executed.
    notebooks = {name: json.loads((DEPOSIT / name).read_text(encoding="utf-8"))
                 for name in NOTEBOOKS}
    supplementary = notebooks[SUPPLEMENT]
    figure4 = notebooks[FIGURE4]
    pair_source = "".join(figure4["cells"][4]["source"])
    assert "for j in range(i + 1, len(genre_vectors))" in pair_source
    assert "similarities.append(0)" in pair_source

    ratings = pd.read_csv(DEPOSIT / RATINGS)
    assert ratings["ID"].notna().all()
    assert set(ratings.Group) == set(ARMS)
    assert ratings.groupby("ID").Group.nunique().eq(1).all()
    assert ratings.groupby(["ID", "Day"]).size().eq(4).all()
    assert ratings.groupby("ID")[COVARIATES].nunique().le(1).all().all()
    assert ratings["unique_id"].eq(ratings.ID.astype(str) + "_" + ratings.Day.astype(str)).all()
    assert ratings[list(OUTCOMES.values())].notna().all().all()
    assert ratings[list(OUTCOMES.values())].ge(1).all().all()
    assert ratings[list(OUTCOMES.values())].le(7).all().all()
    day2 = ratings.loc[ratings.Day.eq(2)]

    # These are counts explicitly printed for the rating corpus, not arm Ns.
    rating_counts = [
        check("cohort_people_all_days (PDF pp. 4,18,21)", 285, ratings.ID.nunique()),
        check("rated_stories_all_days (PDF pp. 4,21)", 549,
              ratings.groupby(["ID", "Day"]).ngroups),
        check("rated_stories_day1 (PDF p. 21)", 278,
              ratings.loc[ratings.Day.eq(1), "ID"].nunique()),
        check("rated_stories_day2_before_covariate_exclusions (PDF p. 21)", 271,
              day2.ID.nunique()),
        check("ratings_all_days (PDF pp. 4,11,21)", 2196, len(ratings)),
        check("ratings_per_story (PDF pp. 4,21)", 4,
              ratings.groupby(["ID", "Day"]).size().min()),
    ]
    assert all(c["match"] for c in rating_counts)

    models = {}
    for outcome in OUTCOMES.values():
        for adjusted in ([False, True] if outcome == "Overall" else [True]):
            models[(outcome, adjusted)] = rating_model(ratings, outcome, adjusted)

    # All text files retain the authors' complete rows. There is no additional
    # selection rule in the posted Figure 4 notebook. Counts are story rows;
    # the documented design has one final story per person per day.
    genres, embeddings, genre_counts, genre_pair, semantic = {}, {}, {}, {}, {}
    caption_genre, caption_semantic, semantic_max_error = {}, {}, {}
    for arm in GENRE_FILES:
        g = pd.read_csv(DEPOSIT / GENRE_FILES[arm])
        e = pd.read_csv(DEPOSIT / EMBEDDING_FILES[arm])
        assert g.Story.notna().all() and e.Story.notna().all()
        assert not g.Story.duplicated().any() and not e.Story.duplicated().any()
        assert set(g.Story) == set(e.Story)
        genres[arm], embeddings[arm] = g, e
        a = g[GENRES].to_numpy(dtype=float)
        assert np.isfinite(a).all() and np.isin(a, [0, 1]).all()
        genre_counts[arm] = a.sum(axis=1)
        norms = np.linalg.norm(a, axis=1, keepdims=True)
        unit = np.divide(a, norms, out=np.zeros_like(a), where=norms != 0)
        # Exact posted genre procedure: unordered distinct pairs; a zero vector
        # makes its pairs zero, rather than removing that story.
        pairs = (unit @ unit.T)[np.triu_indices(len(a), k=1)]
        genre_pair[arm] = arm_summary(pairs)
        genre_pair[arm]["n_stories"] = len(a)
        other = (a.sum(axis=0) - a) / (len(a) - 1)
        denom = np.linalg.norm(a, axis=1) * np.linalg.norm(other, axis=1)
        # Only a diagnostic for the caption, retaining the authors' zero rule.
        caption_values = np.divide((a * other).sum(axis=1), denom,
                                   out=np.zeros(len(a)), where=denom != 0)
        caption_genre[arm] = float(caption_values.mean())

        # Reuse original text-embedding-3-large vectors and their exact texts.
        # json.loads parses arrays as data; no eval or model/API substitution.
        matrix = np.asarray([json.loads(s) for s in e.Embedding], dtype=float)
        assert matrix.shape == (len(e), 3072) and np.isfinite(matrix).all()
        assert np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=2e-7)
        centroid = matrix.mean(axis=0)
        similarities = ((matrix @ centroid) /
                        (np.linalg.norm(matrix, axis=1) * np.linalg.norm(centroid)))
        error = float(np.max(np.abs(similarities - e.Similarity.to_numpy(dtype=float))))
        assert error < 1e-12
        semantic_max_error[arm] = error
        semantic[arm] = arm_summary(similarities)
        other = (matrix.sum(axis=0) - matrix) / (len(matrix) - 1)
        leave_one_out = ((matrix * other).sum(axis=1) /
                         (np.linalg.norm(matrix, axis=1) * np.linalg.norm(other, axis=1)))
        caption_semantic[arm] = float(leave_one_out.mean())
    assert not pd.concat([genres[a].Story for a in ARMS]).duplicated().any()

    text_count_note = (
        "The text/genre corpus has 93 Human Creativity, 91 Human Confirmation, and 91 Copilot "
        "stories (275 Day 2 stories), plus 282 Day 1 stories. The rating CSV instead has "
        "93, 88, and 90 Day 2 writers (271), plus 278 Day 1 stories, matching PDF p. 21. "
        "The paper does not print genre/embedding-specific arm counts, so 271 is not substituted "
        "for the separate text-analysis corpus. No exclusion can be inferred to reconcile the "
        "extra text rows: these CSVs contain unique full story texts but no writer IDs or link "
        "to the rating file. n_treatment/n_control for text analyses count unique stories under "
        "the paper's one-final-story-per-writer-per-day protocol (PDF pp. 4,18-20); this mapping "
        "cannot be independently checked by participant ID. All deposited text rows are retained "
        "as in the Figure 4 notebook, which reproduces the printed means and intervals. "
    )
    randomization_note = (
        "Individual randomization among Day 2 AI modes (PDF p. 4). Day 1 was a fixed-order "
        "unassisted baseline, so round='all' denotes the single eligible Day 2 contrast; "
        "no paired or first_round result is applicable. Difference is treatment minus control "
        "in raw outcome units. "
    )
    results, skipped = [], []
    notebook_cells = {"Originality": 4, "Interestingness": 5, "Writing": 6, "Coherence": 7}

    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        treatment, control = estimate["treatment_arm"], estimate["control_arm"]
        outcome = estimate["outcome"]
        if slug == "s1_overall_quality_human_creativity_vs_copilot":
            skipped.append({"slug": slug, "reason":
                "The paper prints only 'No significant differences emerged' (PDF p. 5), "
                "with no numeric arm means or pairwise coefficient for this contrast. "
                "Table S7 prints coefficients against Human Confirmation, not this pairwise "
                "contrast. Under the reproduce-first rule there is no directly printed "
                "numeric target for this estimate; no contrast was computed."})
            continue
        if "genre_composition" in slug:
            skipped.append({"slug": slug, "reason":
                "This estimate is a nine-component vector of genre percentages, with no "
                "scalar arm outcome, scalar difference, or numerical target in the extraction. "
                "Values are confined to Figure 4A (PDF p. 15). Producing a single mean, SD, "
                "or difference would require defining a new outcome. The genre-count outcome "
                "is analyzed separately."})
            continue

        if outcome in OUTCOMES:
            variable = OUTCOMES[outcome]
            adjusted = not slug.endswith("_unadjusted")
            selected, design, fit = models[(variable, adjusted)]
            vector = contrast_vector(treatment, control, design.columns)
            # Preserve the manuscript's coefficient orientation only in checks.
            # The requested output below always uses treatment minus control.
            orientation = -1 if estimate["stats"]["difference_is"].startswith("control minus treatment") else 1
            printed_fit = fit.t_test(vector * orientation)
            coefficient = float(np.asarray(printed_fit.effect).ravel()[0])
            se = float(np.asarray(printed_fit.sd).ravel()[0])
            cell = (22 if adjusted else 21) if variable == "Overall" else notebook_cells[variable]
            checks = list(rating_counts)
            checks += [
                check("regression.coef (paper orientation)", estimate["stats"]["regression"]["coef"], coefficient, 4),
                check("regression.se (paper conventional evaluation-level SE)", estimate["stats"]["regression"]["se"], se, 3),
                check(f"regression_rating_n (posted Supplementary Material notebook cell {cell}; absent from paper)",
                      notebook_nobs(supplementary, cell), fit.nobs),
                check("pooled_all_days_mean (Table 1; diagnostic only)", TABLE1[variable][0], ratings[variable].mean(), 2),
                check("pooled_all_days_sd (Table 1; diagnostic only)", TABLE1[variable][1], ratings[variable].std(ddof=1), 2),
            ]
            if estimate["stats"]["difference"] is not None:
                checks.append(check("main_text_difference (paper orientation)",
                                    estimate["stats"]["difference"], coefficient, 2))
            if estimate["stats"]["p_value"] is not None:
                checks.append(bound_check("paper_p_value_bound", estimate["stats"]["p_value"],
                                          float(printed_fit.pvalue)))
            if not all(c["match"] for c in checks):
                skipped.append(failed_reproduction(estimate, checks))
                continue
            # Only after the printed regression, its count, and Table 1 match.
            people = selected.groupby(["ID", "Group"], as_index=False)[variable].mean()
            treatment_y = people.loc[people.Group.eq(treatment), variable]
            control_y = people.loc[people.Group.eq(control), variable]
            computed = participant_contrast(treatment_y, control_y)
            counts = people.groupby("Group").ID.nunique().to_dict()
            notes = (
                f"{variable} from the replication rating CSV, Day==2. "
                "Authors' Supplementary Material notebook read only as text; Tables S4/S7 "
                "use evaluation-level OLS with an intercept and both arm indicators, "
                "conventional SEs, and numeric DAT/Experience/Ability/English controls "
                "when adjusted. Source: PDF p. 48 (Table S4) or p. 51 (Table S7); "
                f"reproduction sample: {int(fit.nobs)} ratings, {len(people)} people, "
                f"arm counts {json.dumps(counts, sort_keys=True)}. "
            )
            if adjusted:
                notes += (
                    "Complete-case exclusion for the four baseline covariates removes "
                    "four people (three Human Confirmation, one Human Creativity), or 16 ratings. "
                    "Participant statistics use these same model-sample people. "
                )
            else:
                notes += "All 271 Day 2 writers are retained; missing baseline covariates do not exclude anyone. "
            notes += (
                "The four ratings of each person's single story are averaged within ID. "
                "Arm SDs use denominator n-1. The requested difference and HC2 SE come from "
                "a new, unadjusted two-arm OLS on those participant means, even when the slug "
                "names an adjusted published regression. Thus the raw difference need not equal "
                "the reproduced adjusted coefficient. HC2 is also checked against "
                "sqrt(treatment_sd^2/n_treatment + control_sd^2/n_control). "
                "Table 1 pooled statistics are used only to verify the data and are never "
                "used as arm statistics. " + randomization_note
            )
            results.append({"slug": slug, "round": "all", "reproduced": checks,
                            "computed": computed, "notes": notes})
            continue

        if "genres_per_story" in slug:
            ts, cs = arm_summary(genre_counts[treatment]), arm_summary(genre_counts[control])
            checks = means_and_intervals_checks(estimate, ts, cs, 2)
            if not all(c["match"] for c in checks):
                skipped.append(failed_reproduction(estimate, checks))
                continue
            computed = participant_contrast(genre_counts[treatment], genre_counts[control])
            notes = (
                "Sum the nine binary genre columns per final story, using the posted GPT-4o "
                "classifications. PDF p. 6 means and all 95% CI endpoints reproduce with "
                "mean +/- t(0.975,n-1)*sample_SD/sqrt(n), as in Figure 4 notebook cell 5. "
                "No genre reassignment, text generation, missing-rating filter, or baseline "
                "covariate exclusion is applied. The one all-zero genre vector in Human "
                "Confirmation is retained as a genre count of zero, matching the authors. "
                "One final story per writer supplies a participant value; SDs use n-1 and "
                "the two-arm OLS standard error is HC2. " + text_count_note + randomization_note
            )
            results.append({"slug": slug, "round": "all", "reproduced": checks,
                            "computed": computed, "notes": notes})
            continue

        if "semantic_similarity" in slug or "genre_similarity" in slug:
            semantic_outcome = "semantic_similarity" in slug
            measures = semantic if semantic_outcome else genre_pair
            ts, cs = measures[treatment], measures[control]
            checks = means_and_intervals_checks(estimate, ts, cs, 3)
            if not all(c["match"] for c in checks):
                skipped.append(failed_reproduction(estimate, checks))
                continue
            # Rule 5 exception: retain the paper's measure of sets in its own
            # units. There is no participant-level SD or valid HC2/paired SE.
            computed = {
                "n_treatment": len(genres[treatment]), "n_control": len(genres[control]),
                "treatment_mean": ts["mean"], "treatment_sd": None,
                "control_mean": cs["mean"], "control_sd": None,
                "difference": ts["mean"] - cs["mean"], "difference_se": None,
                "se_type": None, "n_clusters": None,
            }
            if semantic_outcome:
                notes = (
                    "Set-level semantic similarity; original posted 3,072-dimensional "
                    "text-embedding-3-large embeddings and the exact associated story texts "
                    "are used, with no substitute model or regenerated embeddings. Recompute "
                    "cosine(embedding_i, mean of all embeddings in its arm). This matches "
                    "every saved Similarity value within 1e-12 and reproduces PDF p. 7 means "
                    "and CIs; Figure 4 notebook cell 8 summarizes that saved Similarity column "
                    "using a t interval over stories. IMPORTANT PROCEDURE DISCREPANCY: the "
                    "average includes the focal story. The caption on PDF p. 16 incorrectly "
                    "says 'other stories'. Its literal leave-one-out procedure gives "
                    f"{treatment}={caption_semantic[treatment]:.12f} and "
                    f"{control}={caption_semantic[control]:.12f}, which do not match the "
                    "printed values. This result reports the exact numerical measure "
                    "implemented by the saved embeddings and similarities, not the caption's "
                    "leave-one-out variant. "
                )
            else:
                notes = (
                    "Set-level genre similarity; use the nine original posted GPT-4o binary "
                    "genre columns, with no new classifications. Follow Figure 4 notebook "
                    "cells 4 and 6 exactly: cosine similarity for every unordered pair of "
                    "distinct stories; pairs involving an all-zero vector receive zero. "
                    f"There are {ts['n']} treatment pairs and {cs['n']} control pairs. "
                    "The pair mean and mean +/- t(0.975,n_pairs-1)*SD_pairs/sqrt(n_pairs) "
                    "reproduce all PDF p. 6 means and CI endpoints. IMPORTANT PROCEDURE "
                    "DISCREPANCY: the implemented method is pairwise, whereas PDF p. 16 "
                    "describes comparison with the average genre vector of other stories. "
                    "That literal caption method (with the same zero-vector convention) gives "
                    f"{treatment}={caption_genre[treatment]:.12f} and "
                    f"{control}={caption_genre[control]:.12f}, not the printed values. "
                    "The reproduced measure follows the authors' posted analysis procedure. "
                )
            notes += (
                "Under rule 5, only the recomputed set measure, its descriptive difference, "
                "and the paper's arm CIs in reproduced are retained. These are raw cosine "
                "similarities; a positive difference means greater similarity. Shared "
                "stories/centroids create dependence. The paper's arm CIs are not contrast "
                "CIs and do not establish uncertainty at the level of randomization. "
                "treatment_sd, control_sd, difference_se, and se_type are null: there is "
                "no independent participant-level outcome or appropriate HC2/paired SE "
                "for this set measure. " + text_count_note + randomization_note
            )
            results.append({"slug": slug, "round": "all", "reproduced": checks,
                            "computed": computed, "notes": notes})
            continue
        raise ValueError("Unmapped estimate: " + slug)

    all_slugs = [e["slug"] for e in extraction["estimates"]]
    result_slugs = [r["slug"] for r in results]
    skipped_slugs = [s["slug"] for s in skipped]
    assert len(result_slugs) == len(set(result_slugs))
    assert not set(result_slugs) & set(skipped_slugs)
    assert sorted(result_slugs + skipped_slugs) == sorted(all_slugs)
    assert all(r["round"] == "all" for r in results)
    assert all(all(c["match"] for c in r["reproduced"]) for r in results)
    output = {
        "cid": "c793", "analyst": "A", "script": SCRIPT.as_posix(),
        "data_files": [(DEPOSIT / name).as_posix() for name in filenames],
        "results": results, "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == output
    summary = {"cid": "c793", "n_results": len(results),
               "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
               "n_skipped": len(skipped)}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
