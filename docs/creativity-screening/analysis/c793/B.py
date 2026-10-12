"""Independent c793 analysis B. Run with python -I -B B.py.

Only B.json is written. Deposited notebooks are parsed as inert JSON/text,
never imported, executed, or evaluated. All numeric analyses below are our own.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
from scipy import stats
import statsmodels.api as sm


ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data/dataverse-ATXBCK")
MANIFEST = DEPOSIT.parent / "manifest.json"
SCRIPT = ROOT / "analysis/c793/B.py"
OUTPUT = ROOT / "analysis/c793/B.json"
CSV_NAME = "Replication Data for Designing Human and Generative AI Collaboration.csv"
CONTROLS = ["DAT", "Experience", "Ability", "English"]
GENRES = [
    "Horror Fiction", "Mystery/Crime Fiction", "Romance", "Sci-Fi",
    "Thriller/Suspense", "Western Fiction", "Historical Fiction",
    "Young Adult Fiction", "Fantasy",
]
ARM_FILES = {
    "Human Creativity": ("genre_Creativity.csv", "3large_result_df_A.csv"),
    "Human Confirmation": ("genre_Confirmation.csv", "3large_result_df_B.csv"),
    "Copilot": ("genre_Copilot.csv", "3large_result_df_C.csv"),
}
QUALITY_COLUMNS = {
    "Overall story quality": "Overall",
    "Originality": "Originality",
    "Interestingness": "Interestingness",
    "Writing quality": "Writing",
    "Coherence": "Coherence",
}
NOTEBOOK_CELLS = {
    "Originality": 4, "Interestingness": 5, "Writing": 6,
    "Coherence": 7, "Overall_adjusted": 22, "Overall_unadjusted": 21,
}
COMPUTED_KEYS = [
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se",
    "se_type", "n_clusters",
]
READ_FILES = []


def register(path):
    path = Path(path)
    assert path.is_absolute()
    value = path.as_posix()
    if value not in READ_FILES:
        READ_FILES.append(value)
    return path


def read_json(path):
    with register(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path):
    return register(path).read_text(encoding="utf-8")


def read_csv(name):
    return pd.read_csv(register(DEPOSIT / name))


def check(statistic, printed, computed, decimals=0):
    """Compare at the printed precision, keeping the unrounded computation."""
    value = float(computed)
    assert math.isfinite(value)
    if decimals == 0:
        match = value == float(printed)
        value = int(value) if value.is_integer() else value
    else:
        match = format(value, f".{decimals}f") == format(float(printed), f".{decimals}f")
    return {"statistic": statistic, "printed": printed,
            "computed": value, "match": bool(match)}


def bound_check(statistic, printed, computed):
    assert isinstance(printed, str) and printed.startswith("<")
    return {"statistic": statistic, "printed": printed,
            "computed": float(computed), "match": bool(computed < float(printed[1:]))}


def mean_interval(values):
    """The deposited Figure 4 notebook's t interval, for reproduction only."""
    values = np.asarray(values, dtype=float)
    assert len(values) > 1 and np.isfinite(values).all()
    mean = float(values.mean())
    margin = float(stats.sem(values) * stats.t.ppf(0.975, len(values) - 1))
    return mean, mean - margin, mean + margin


def arm_checks(estimate, treatment_values, control_values, decimals):
    tm, tl, tu = mean_interval(treatment_values)
    cm, cl, cu = mean_interval(control_values)
    printed = estimate["stats"]
    return [
        check("treatment_mean", printed["treatment_mean"], tm, decimals),
        check("control_mean", printed["control_mean"], cm, decimals),
        check("treatment_mean_ci_lower", printed["ci_lower"], tl, decimals),
        check("treatment_mean_ci_upper", printed["ci_upper"], tu, decimals),
        check("control_mean_ci_lower", printed["control_ci_lower"], cl, decimals),
        check("control_mean_ci_upper", printed["control_ci_upper"], cu, decimals),
    ]


def participant_contrast(treatment_values, control_values):
    """One value per person; no covariates in the requested new HC2 contrast."""
    a = np.asarray(treatment_values, dtype=float)
    b = np.asarray(control_values, dtype=float)
    assert len(a) > 1 and len(b) > 1
    assert np.isfinite(a).all() and np.isfinite(b).all()
    y = np.concatenate([a, b])
    indicator = np.concatenate([np.ones(len(a)), np.zeros(len(b))])
    design = np.column_stack([np.ones(len(y)), indicator])
    fit = sm.OLS(y, design).fit(cov_type="HC2")
    difference = float(a.mean() - b.mean())
    se = float(fit.bse[1])
    # Independent algebraic check of HC2 for a two-arm saturated regression.
    variance_check = float(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    assert math.isclose(float(fit.params[1]), difference, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(se * se, variance_check, rel_tol=1e-12, abs_tol=1e-12)
    return {
        "n_treatment": len(a), "n_control": len(b),
        "treatment_mean": float(a.mean()), "treatment_sd": float(a.std(ddof=1)),
        "control_mean": float(b.mean()), "control_sd": float(b.std(ddof=1)),
        "difference": difference, "difference_se": se,
        "se_type": "HC2", "n_clusters": None,
    }


def set_contrast(a, b, n_treatment, n_control):
    """Rule 5: original-unit set measures only; no independent-person SD or SE."""
    tm, cm = float(np.mean(a)), float(np.mean(b))
    return {
        "n_treatment": n_treatment, "n_control": n_control,
        "treatment_mean": tm, "treatment_sd": None,
        "control_mean": cm, "control_sd": None,
        "difference": tm - cm, "difference_se": None,
        "se_type": None, "n_clusters": None,
    }


def notebook_output_text(notebook, cell_index):
    texts = []
    for output in notebook["cells"][cell_index].get("outputs", []):
        text = output.get("text", output.get("data", {}).get("text/plain", ""))
        texts.append("".join(text) if isinstance(text, list) else text)
    return "\n".join(texts)


def quality_model(data, outcome, adjusted):
    required = [outcome] + (CONTROLS if adjusted else [])
    sample = data.loc[data["Day"].eq(2)].dropna(subset=required).copy()
    design = pd.DataFrame({
        "constant": 1.0,
        "Human Creativity": sample["Group"].eq("Human Creativity").astype(float),
        "Copilot": sample["Group"].eq("Copilot").astype(float),
    }, index=sample.index)
    if adjusted:
        for name in CONTROLS:
            design[name] = sample[name]
    # Conventional rating-level OLS is used ONLY to reproduce the authors' model.
    fit = sm.OLS(sample[outcome].astype(float), design).fit()
    return sample, design, fit


def printed_contrast(fit, design, estimate):
    weights = np.zeros(design.shape[1])
    treatment = estimate["treatment_arm"]
    control = estimate["control_arm"]
    direction = estimate["stats"]["difference_is"]
    sign = -1.0 if direction.startswith("control minus treatment") else 1.0
    for arm, weight in [(treatment, sign), (control, -sign)]:
        if arm != "Human Confirmation":
            weights[design.columns.get_loc(arm)] += weight
    result = fit.t_test(weights)
    return (float(np.asarray(result.effect).item()),
            float(np.asarray(result.sd).item()),
            float(np.asarray(result.pvalue).item()))


def main():
    extraction = read_json(ROOT / "extraction/c793.json")
    retrieval = read_json(ROOT / "retrieval.json")["c793"]
    manifest = read_json(MANIFEST)
    assert extraction["cid"] == "c793"
    assert manifest["papers"]["c793"] == ["dataverse-ATXBCK"]

    # These sources were read in full during analysis, including all appendices.
    read_text(ROOT.parent / "creativity-codebook.md")
    read_text(ROOT / "extraction-spec.md")
    read_text(retrieval["md_path"])
    pdf_path = register(retrieval["pdf_path"])
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == (
        "793350dfb72d449e5b3bd21823ee395305a6bfdab61bf7d7acd210edafc982bc"
    )
    with pymupdf.open(pdf_path) as doc:
        assert len(doc) == 57
        # Numeric sources, design/count sources, and similarity-method caption.
        for page_index in [3, 4, 5, 6, 10, 15, 17, 18, 20, 22, 47, 50]:
            assert doc[page_index].get_text().strip()

    files = manifest["deposits"]["dataverse-ATXBCK"]["files"]
    notebooks = {}
    notebook_names = [
        "Supplementary Material.ipynb",
        "Fig. 2. Effects on overall story quality.ipynb",
        "Fig. 4. Treatment effects on content diversity.ipynb",
        "Table 1. Descriptive statistics.ipynb",
    ]
    for name, entry in files.items():
        if name.endswith(".csv") or name in notebook_names:
            path = register(DEPOSIT / name)
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], name
    for name in notebook_names:
        notebooks[name] = read_json(DEPOSIT / name)
    supplementary = notebooks["Supplementary Material.ipynb"]

    data = read_csv(CSV_NAME)
    assert set(data["Group"].unique()) == set(ARM_FILES)
    assert data.groupby("ID")["Group"].nunique().eq(1).all()
    assert data.groupby(["ID", "Day"]).size().eq(4).all()
    assert data.groupby(["ID", "Day"])["unique_id"].nunique().eq(1).all()
    assert data.groupby("unique_id")["ID"].nunique().eq(1).all()
    assert data.groupby("unique_id")["Day"].nunique().eq(1).all()
    for variable in CONTROLS:
        assert data.groupby(["ID", "Day"])[variable].nunique(dropna=False).le(1).all()

    # Paper p. 21: 285 people, 549 stories, 278/271 by day, 2,196 ratings.
    source_checks = [
        check("source_data_unique_people_both_days", 285, data["ID"].nunique()),
        check("source_data_stories_both_days", 549, data["unique_id"].nunique()),
        check("source_data_day1_stories", 278, data.loc[data.Day.eq(1), "unique_id"].nunique()),
        check("source_data_day2_stories", 271, data.loc[data.Day.eq(2), "unique_id"].nunique()),
        check("source_data_ratings_both_days", 2196, len(data)),
        check("ratings_per_story", 4, data.groupby(["ID", "Day"]).size().min()),
    ]
    assert all(item["match"] for item in source_checks)

    # Table 1 validates the complete rating data, not an arm-specific SD.
    pooled_printed = {
        "Overall": (4.91, 1.35), "Originality": (4.97, 1.38),
        "Interestingness": (4.87, 1.46), "Writing": (5.21, 1.37),
        "Coherence": (5.20, 1.36),
    }
    for outcome, (mean, sd) in pooled_printed.items():
        assert check("pooled_mean", mean, data[outcome].mean(), 2)["match"]
        assert check("pooled_sd", sd, data[outcome].std(ddof=1), 2)["match"]

    genre_data, genre_counts = {}, {}
    pair_similarities, semantic_similarities = {}, {}
    genre_leaveout_means, semantic_leaveout_means = {}, {}
    embedding_max_errors = {}
    for arm, (genre_name, embedding_name) in ARM_FILES.items():
        genre = read_csv(genre_name)
        embedding_frame = read_csv(embedding_name)
        assert genre["Story"].notna().all() and genre["Story"].is_unique
        assert genre["Story"].equals(embedding_frame["Story"])
        vectors = genre[GENRES].to_numpy(dtype=float)
        assert np.isin(vectors, [0, 1]).all()
        genre_data[arm] = genre
        genre_counts[arm] = vectors.sum(axis=1)

        # Actual published-number procedure: all unordered pairs, including
        # similarity zero when either genre vector is zero (notebook cell 4).
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        normalized = np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms > 0)
        pair_similarities[arm] = (normalized @ normalized.T)[np.triu_indices(len(vectors), k=1)]
        # Caption's different method is checked and disclosed, not substituted.
        other_genres = (vectors.sum(axis=0) - vectors) / (len(vectors) - 1)
        genre_leaveout_means[arm] = float(np.mean(np.einsum(
            "ij,ij->i", normalized,
            other_genres / np.linalg.norm(other_genres, axis=1, keepdims=True),
        )))

        # Parse numeric lists as JSON. No eval, deposited code, model call, or
        # regenerated embeddings: these are the authors' original stored vectors.
        embeddings = np.asarray([json.loads(value) for value in embedding_frame["Embedding"]], dtype=float)
        assert embeddings.shape == (len(genre), 3072)
        assert np.isfinite(embeddings).all()
        lengths = np.linalg.norm(embeddings, axis=1)
        center = embeddings.mean(axis=0)
        similarity = embeddings @ center / (lengths * np.linalg.norm(center))
        stored = embedding_frame["Similarity"].to_numpy(dtype=float)
        error = float(np.max(np.abs(similarity - stored)))
        assert error < 1e-12
        embedding_max_errors[arm] = error
        semantic_similarities[arm] = similarity
        other_embeddings = (embeddings.sum(axis=0) - embeddings) / (len(embeddings) - 1)
        semantic_leaveout_means[arm] = float(np.mean(
            np.einsum("ij,ij->i", embeddings, other_embeddings)
            / (lengths * np.linalg.norm(other_embeddings, axis=1))
        ))

    # Baseline files are inspected only for corpus auditing, never analyzed as a
    # randomized no-AI comparison. The Day 1 corpus also differs from ratings.
    baseline_genre = read_csv("genre_day1.csv")
    baseline_embedding = read_csv("3large_result_df_Day1.csv")
    assert baseline_genre["Story"].equals(baseline_embedding["Story"])

    results, skipped = [], []
    model_cache = {}
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        treatment = estimate["treatment_arm"]
        control = estimate["control_arm"]
        printed = estimate["stats"]
        assert estimate["within_person"] is None

        if slug == "s1_overall_quality_human_creativity_vs_copilot":
            skipped.append({
                "slug": slug,
                "reason": (
                    "PDF p. 5 reports only no significant difference. This exact contrast has no "
                    "printed numeric arm means, coefficient, difference, or exact test to satisfy "
                    "the reproduction-first gate. Table S7 prints the two arms' coefficients "
                    "against Human Confirmation, not this pairwise coefficient. No new effect "
                    "is calculated for this qualitative-only extraction record."
                ),
            })
            continue

        if "_genre_composition_" in slug:
            skipped.append({
                "slug": slug,
                "reason": (
                    "Figure 4A is a nine-component genre-percentage vector, with no single "
                    "scalar outcome or printed numerical arm mean/difference in this extraction. "
                    "The reconciled extraction leaves all statistics null under its figure-only "
                    "rule. No scalar participant effect can be reproduced for this record; "
                    "the category-count outcome is handled separately."
                ),
            })
            continue

        if printed.get("regression") is not None:
            outcome = QUALITY_COLUMNS[estimate["outcome"]]
            adjusted = not slug.endswith("_unadjusted")
            key = (outcome, adjusted)
            if key not in model_cache:
                model_cache[key] = quality_model(data, outcome, adjusted)
            sample, design, fit = model_cache[key]
            coefficient, paper_se, p_value = printed_contrast(fit, design, estimate)
            checks = list(source_checks)
            checks.extend([
                check("regression.coef_as_printed", printed["regression"]["coef"], coefficient, 4),
                check("regression.se_rating_level_conventional", printed["regression"]["se"], paper_se, 3),
            ])
            if printed.get("difference") is not None:
                checks.append(check("rounded_main_text_difference_as_printed", printed["difference"], coefficient, 2))
            if printed.get("p_value") is not None:
                checks.append(bound_check("regression.p_value_bound", printed["p_value"], p_value))
            cell_key = f"Overall_{'adjusted' if adjusted else 'unadjusted'}" if outcome == "Overall" else outcome
            cell_index = NOTEBOOK_CELLS[cell_key]
            output_text = notebook_output_text(supplementary, cell_index)
            matches = re.findall(r"No\. Observations:\s+(\d+)", output_text)
            assert len(matches) == 1
            checks.append(check("regression_rating_count_in_posted_notebook", int(matches[0]), fit.nobs))

            if not all(item["match"] for item in checks):
                failed = [item for item in checks if not item["match"]]
                results.append({"slug": slug, "round": "all", "reproduced": checks,
                                "computed": {key: None for key in COMPUTED_KEYS},
                                "notes": "Reproduction failed; no new participant statistics computed. " + json.dumps(failed)})
                continue

            person = sample.groupby(["ID", "Group"], as_index=False)[outcome].mean()
            a = person.loc[person.Group.eq(treatment), outcome].to_numpy()
            b = person.loc[person.Group.eq(control), outcome].to_numpy()
            counts = sample.groupby("Group")["ID"].nunique().to_dict()
            exclusions = (
                "Complete cases for DAT, Experience, Ability and English: 267 writers and "
                "1,068 ratings across three arms. Four Day 2 writers are omitted for missing "
                "baseline covariates (three Human Confirmation, one Human Creativity). "
                if adjusted else
                "All 271 Day 2 writers and 1,084 ratings are retained; baseline covariates "
                "are not used for exclusion. "
            )
            results.append({
                "slug": slug, "round": "all", "reproduced": checks,
                "computed": participant_contrast(a, b),
                "notes": (
                    f"Outcome column {outcome}; Day == 2. Individual randomized AI-design "
                    "comparison. Source counts reproduced from PDF p. 21; coefficient and SE "
                    f"from {'Table S7, PDF p. 51' if outcome == 'Overall' else 'Table S4, PDF p. 48'}. "
                    f"The extra regression-rating count is printed in the deposited Supplementary "
                    f"Material notebook, zero-based cell {cell_index}, not in the paper. "
                    "Its text identifies conventional, nonrobust OLS; all three treatment arms "
                    "enter the reproduction model. " + exclusions +
                    "Observed writer counts in that model: " + json.dumps(counts, sort_keys=True) + ". "
                    "Arm-specific people counts are not printed in the paper. Each writer has "
                    "one Day 2 story with four ratings. Average the four ratings by ID first; "
                    "then compute means and sample SDs (ddof=1). The new difference is the "
                    "unadjusted participant mean for the listed treatment minus the listed "
                    "control within this model's analysis sample. HC2 comes from OLS with "
                    "only an intercept and the pairwise arm indicator. Thus the new difference "
                    "is not the paper's covariate-adjusted coefficient. Printed-coefficient "
                    "orientation is preserved only in reproduced, and corrected to treatment "
                    "minus control in computed. No cluster randomization is reported. "
                    "Round all denotes the Day 2 between-person contrast; the fixed-order "
                    "Day 1 baseline is excluded and supplies no paired or first-round estimate."
                ),
            })
            continue

        count_a, count_b = len(genre_data[treatment]), len(genre_data[control])
        corpus_note = (
            "The protocol supplies one final story per writer on Day 2 (PDF pp. 4, 19); "
            "people counts therefore use one writer per story row, not rating or pair counts. "
            "The content files have no participant-ID linkage to the ratings CSV. Their "
            "Day 2 corpus has Human Creativity 93, Human Confirmation 91 and Copilot 91 "
            "stories (275 total), whereas the ratings file/paper's evaluated corpus has "
            "93, 88 and 90 (271 total). These are distinct analysis pools; no invented "
            "cross-file exclusions are applied. The printed content arm means and CIs "
            "reproduce using the content corpus. Arm-specific content counts are not "
            "printed, so no unavailable count benchmark is asserted to match. "
        )

        if "_genres_per_story_" in slug:
            a, b = genre_counts[treatment], genre_counts[control]
            checks = arm_checks(estimate, a, b, 2)
            notes = (
                "PDF p. 6; Figure 4 notebook zero-based cell 5 (read as text). Outcome is "
                "the sum of the nine deposited binary genre columns per story. Retain all "
                "rows, including the Human Confirmation story with nine zero indicators, "
                "as the authors' code does. Published CIs are sample-SEM times a t critical "
                "value with n-1 degrees of freedom. " + corpus_note +
                "Each one-story-per-writer genre count is a participant-level flexibility "
                "outcome. SD uses n-1. New difference is treatment minus control and its "
                "SE is HC2 from OLS on the arm indicator. Day 1 is not a randomized "
                "control or a first treatment round."
            )
            calculation = lambda: participant_contrast(a, b)
        elif "_genre_similarity_" in slug:
            a, b = pair_similarities[treatment], pair_similarities[control]
            checks = arm_checks(estimate, a, b, 3)
            notes = (
                "PDF p. 6; authors' Figure 4 notebook zero-based cells 4 and 6, read as "
                "text. All unordered distinct-story pairs of the original nine binary "
                "genre vectors are compared by cosine similarity. A zero vector gives "
                "similarity zero. This exactly reproduces the published means and t CIs; "
                f"treatment/control pair counts are {len(a)}/{len(b)}. METHOD DISCREPANCY: "
                "the Figure 4B caption on PDF p. 16 describes similarity to the average "
                "of other stories, which is not what the supplied code computes. That "
                f"caption formula instead gives treatment/control means "
                f"{genre_leaveout_means[treatment]:.12f}/{genre_leaveout_means[control]:.12f} "
                "using the same zero-vector convention. The result here retains the "
                "exactly reproducible procedure that generated the published numbers, "
                "not the conflicting caption formula. " + corpus_note +
                "Rule 5: these are set-defined diversity measures. Arm SDs, difference SE "
                "and se_type are null; pairwise observations are not independent people. "
                "The reproduced published CIs treat pairs as observations and are not "
                "new participant-level precision. The difference is only the raw difference "
                "between the two set summaries; higher values mean more similarity."
            )
            calculation = lambda: set_contrast(a, b, count_a, count_b)
        elif "_semantic_similarity_" in slug:
            a, b = semantic_similarities[treatment], semantic_similarities[control]
            checks = arm_checks(estimate, a, b, 3)
            notes = (
                "PDF p. 7; original 3large_result_df_A/B/C.csv embeddings and exact saved "
                "story texts; A = Human Creativity, B = Human Confirmation, C = Copilot "
                "as mapped in the Figure 4 notebook, zero-based cell 8 (read as text). "
                "Use the authors' saved 3,072-dimensional text-embedding-3-large vectors; "
                "no model substitution or new API call. Every story text matches its genre "
                "file. Recompute cosine similarity to the full within-arm mean embedding. "
                "This reproduces every saved Similarity value to floating-point precision "
                f"(maximum errors {embedding_max_errors[treatment]:.3g} and "
                f"{embedding_max_errors[control]:.3g}) and all published means/CIs. "
                "The notebook plots saved Similarity and uses t intervals over stories. "
                "METHOD DISCREPANCY: the Figure 4C caption on PDF p. 16 says the average "
                "of other stories. Excluding each focal story instead gives treatment/control "
                f"means {semantic_leaveout_means[treatment]:.12f}/"
                f"{semantic_leaveout_means[control]:.12f}, which do not match. The exact "
                "saved-output reproduction establishes that the published values use a "
                "self-inclusive centroid. This is disclosed rather than silently adopting "
                "the caption's different procedure. " + corpus_note +
                "Rule 5: retain only the original-unit set measure and raw difference "
                "(treatment minus control; higher means more similar). Shared centroids "
                "create dependence. No participant-level SD, HC2/paired/cluster SE or "
                "standardized effect is supplied; those fields, including se_type, are null."
            )
            calculation = lambda: set_contrast(a, b, count_a, count_b)
        else:
            raise AssertionError("Unhandled extraction estimate: " + slug)

        if all(item["match"] for item in checks):
            computed = calculation()
        else:
            computed = {key: None for key in COMPUTED_KEYS}
            notes = "Reproduction failed; no new effect computed. " + notes
        results.append({"slug": slug, "round": "all", "reproduced": checks,
                        "computed": computed, "notes": notes})

    all_slugs = [record["slug"] for record in results + skipped]
    assert len(all_slugs) == len(set(all_slugs)) == len(extraction["estimates"])
    assert set(all_slugs) == {estimate["slug"] for estimate in extraction["estimates"]}
    for record in results:
        assert set(record["computed"]) == set(COMPUTED_KEYS)
        assert all(item["match"] for item in record["reproduced"]), record["slug"]
        values = record["computed"]
        assert math.isclose(values["difference"], values["treatment_mean"] - values["control_mean"], abs_tol=1e-12)
        if "_similarity_" in record["slug"]:
            assert values["difference_se"] is None and values["se_type"] is None
        else:
            assert values["se_type"] == "HC2" and values["difference_se"] > 0

    obj = {"cid": "c793", "analyst": "B", "script": SCRIPT.as_posix(),
           "data_files": READ_FILES, "results": results, "skipped": skipped}
    # The only data output. All characters in this source are ASCII.
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
        fh.write("\n")
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({
        "cid": "c793", "n_results": len(results),
        "n_reproduced": sum(bool(r["reproduced"]) and all(c["match"] for c in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
