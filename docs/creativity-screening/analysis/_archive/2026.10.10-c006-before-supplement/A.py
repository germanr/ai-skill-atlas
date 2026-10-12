"""Independent analyst A reanalysis of c006.

Run: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c006/A.py

Only A.json is written. Deposited programs are never executed or imported.
The full local markdown was read, including its references and publisher page;
the separate supplement is absent. Main-paper PDF pages 2-5, 7-8 were checked
with pymupdf. The other local copy has the same nine-page article, no appendix.
Direct publisher-supplement and Zenodo API requests both failed with Windows
socket error 10013. This script therefore has no network dependency.

For each result, reproduction uses the paper's observation level and covariance
estimator. Only after all its printed checks pass are participant-level means,
sample SDs, and a two-arm OLS HC2 standard error calculated. Data files include
the statistical inputs and the documentary files read during preparation.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t


ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path("D:/projects/ai-skill-atlas/creativity-data/zenodo-11654403")
DATA = DEPOSIT / "GenAI_creativity_scripts-unpacked/GenAI_creativity_scripts"
SCRIPT = ROOT / "analysis/c006/A.py"
OUTPUT = ROOT / "analysis/c006/A.json"
EXTRACTION = ROOT / "extraction/c006.json"
RAW_WRITERS = DATA / "raw_data/writers-2023-06-28.csv"
RAW_EVALUATORS = DATA / "raw_data/evaluators-2023-07-06.csv"
PROCESSED_WRITERS = DATA / "already_processed_data/creators.dta"
PROCESSED_EVALUATORS = DATA / "already_processed_data/evaluators_stories.dta"
PAPER_STEM = (
    "C:/Dropbox/Research/ai-lab/literature/creativity/"
    "Doshi and Hauser (2024) - Generative AI Enhances Individual Creativity"
)

CONSULTED_FILES = [
    RAW_WRITERS,
    RAW_EVALUATORS,
    PROCESSED_WRITERS,
    PROCESSED_EVALUATORS,
    DEPOSIT / "README.md",
    DATA / "readme.txt",
    DATA / "scripts/01_writer_process_output.do",
    DATA / "scripts/02_evaluator_process_output.do",
    DATA / "scripts/03_analysis.do",
    DATA / "scripts/ai_human_story_similarity.py",
    Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json"),
    EXTRACTION,
    ROOT / "retrieval.json",
    ROOT / "extraction-spec.md",
    ROOT.parent / "creativity-codebook.md",
    Path(PAPER_STEM + ".md"),
    Path(PAPER_STEM + ".pdf"),
    Path(
        "C:/Dropbox/Research/ai-lab/literature/productivity/"
        "Doshi and Hauser (2024) - GenAI Enhances Creativity Reduces Diversity.pdf"
    ),
]

ITEMS = [
    "novel", "original", "rare", "appropriate", "feasible", "publishable",
    "tt_enjoyed", "tt_badly_written", "tt_boring", "tt_funny", "tt_twist",
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

SUFFIXES = {
    "_one_idea_vs_human_only": ([2], [1]),
    "_five_ideas_vs_human_only": ([3], [1]),
    "_combined_ai_vs_human_only": ([2, 3], [1]),
    "_five_ideas_vs_one_idea": ([3], [2]),
}


def item_name(item):
    # Authors' processing file explains that the survey changed the question to
    # well written, retaining its old database name. Do not reverse this item.
    return "eval_tt_well_written" if item == "tt_badly_written" else "eval_" + item


def read_and_validate_data():
    raw_writers = pd.read_csv(RAW_WRITERS, low_memory=False)
    raw_evaluators = pd.read_csv(RAW_EVALUATORS, low_memory=False)
    stored_writers = pd.read_stata(PROCESSED_WRITERS, convert_categoricals=False)
    stored_ratings = pd.read_stata(PROCESSED_EVALUATORS, convert_categoricals=False)

    pages = raw_writers["participant._current_page_name"]
    assert len(raw_writers) == 500
    assert int(pages.isna().sum()) == 169
    assert int(pages.eq("ConsentDropout").sum()) == 22
    assert int((pages.notna() & ~pages.isin(["ConsentDropout", "Finally"])).sum()) == 13
    writers = raw_writers.loc[pages.eq("Finally")].copy()
    outside_ai = writers["follow_up.1.player.used_ai_tool"].fillna(
        writers["follow_up.2.player.used_ai_tool"]
    )
    exclude = writers["participant.condition"].eq("human") & outside_ai.eq(1)
    assert int(exclude.sum()) == 3
    writers = writers.loc[~exclude].rename(columns={
        "participant.code": "writer_id",
        "ai_story_gen.1.player.story_id": "story_id",
    })
    writers["condition"] = writers["participant.condition"].map({
        "human": 1, "human_1AI": 2, "human_5AI": 3,
    })
    assert writers.writer_id.is_unique and writers.story_id.is_unique
    assert not writers.condition.isna().any()
    assert writers.condition.value_counts().to_dict() == {2: 100, 3: 98, 1: 95}

    stored_writers = stored_writers.loc[stored_writers.human_admitted.eq(0)].copy()
    assert set(writers.writer_id) == set(stored_writers.writer_id)
    joined_writers = writers[["writer_id", "story_id", "condition"]].merge(
        stored_writers[["writer_id", "story_id", "condition"]],
        on="writer_id", suffixes=("_raw", "_stored"), validate="one_to_one",
    )
    assert joined_writers.story_id_raw.equals(joined_writers.story_id_stored)
    assert np.array_equal(joined_writers.condition_raw, joined_writers.condition_stored)

    # AI access, rather than actual uptake, defines the treatment groups.
    idea_columns = [f"ai_story_gen.1.player.ai_idea{i}" for i in range(5)]
    used_ai = writers[idea_columns].notna().any(axis=1)
    assert int(used_ai[writers.condition.eq(2)].sum()) == 82
    assert int(used_ai[writers.condition.eq(3)].sum()) == 93

    evaluators = raw_evaluators.loc[
        raw_evaluators["participant._current_page_name"].eq("Finally")
    ].copy()
    assert len(evaluators) == 600
    parts = []
    for number in range(1, 11):
        mapping = {"participant.code": "eval_id"}
        mapping.update({f"evaluator.{number}.player.{v}": item_name(v) for v in ITEMS})
        mapping[f"evaluator.{number}.player.story_id"] = "story_id"
        part = evaluators[list(mapping)].rename(columns=mapping).copy()
        part["story_number"] = number
        parts.append(part.loc[part.story_id.notna()])
    ratings = pd.concat(parts, ignore_index=True)
    keys = ["eval_id", "story_number", "story_id"]
    assert not ratings.duplicated(keys).any()
    assert len(ratings) == len(stored_ratings) == 3600
    compared = ratings.merge(
        stored_ratings, on=keys, validate="one_to_one", suffixes=("_raw", "_stored"),
    )
    assert len(compared) == len(ratings)
    for item in ITEMS:
        variable = item_name(item)
        assert np.array_equal(
            compared[variable + "_raw"].to_numpy(dtype=float),
            compared[variable + "_stored"].to_numpy(dtype=float), equal_nan=True,
        )

    # Rebuild both three-item indices in float64 from the original integer
    # ratings, avoiding the Stata float32 rounding of the stored indices.
    for variable, items in {
        "eval_novel_index": ["novel", "original", "rare"],
        "eval_useful_index": ["appropriate", "feasible", "publishable"],
    }.items():
        ratings[variable] = ratings[["eval_" + v for v in items]].astype(float).mean(axis=1)
        joined = ratings[keys + [variable]].merge(
            stored_ratings[keys + [variable]], on=keys, validate="one_to_one",
            suffixes=("_raw", "_stored"),
        )
        assert np.allclose(
            joined[variable + "_raw"], joined[variable + "_stored"], rtol=0, atol=3.2e-7,
        )

    ratings = ratings.merge(
        writers[["writer_id", "story_id", "condition"]],
        on="story_id", how="inner", validate="many_to_one",
    )
    assert len(ratings) == 3519  # 81 ratings of ineligible writers removed.
    assert ratings.writer_id.nunique() == 293
    assert ratings.eval_id.nunique() == 600
    assert ratings.groupby("eval_id").size().value_counts().to_dict() == {6: 524, 5: 71, 4: 5}
    assert ratings.groupby("writer_id").size().value_counts().to_dict() == {
        12: 141, 13: 77, 11: 61, 10: 9, 14: 4, 9: 1,
    }
    variables = [item_name(v) for v in ITEMS] + ["eval_novel_index", "eval_useful_index"]
    assert not ratings[variables].isna().any().any()
    assert ratings[variables].ge(1).all().all() and ratings[variables].le(9).all().all()

    # This is a single story/idea outcome for each writer, classified as other,
    # not set diversity. Preserve the deposited outcome rather than re-embedding
    # or redrawing comparison ideas. sim_idea is already on the 0-100 scale.
    writers = writers[["writer_id", "story_id", "condition"]].merge(
        stored_writers[["writer_id", "sim_idea"]], on="writer_id", validate="one_to_one",
    )
    writers["sim_idea"] = writers["sim_idea"].astype(float)
    assert not writers.sim_idea.isna().any()
    return writers, ratings


def printed_check(statistic, printed, computed, digits=None):
    if isinstance(printed, str) and printed.startswith("<"):
        matched = float(computed) < float(printed[1:])
    elif digits is None:
        matched = computed == printed
    else:
        matched = f"{float(computed):.{digits}f}" == f"{float(printed):.{digits}f}"
    return {"statistic": statistic, "printed": printed, "computed": computed, "match": bool(matched)}


def reproduce_model(frame, variable, evaluator_clusters):
    y = frame[variable].to_numpy(dtype=float)
    condition = frame.condition.to_numpy()
    x = np.column_stack([np.ones(len(frame)), condition == 2, condition == 3]).astype(float)
    bread = np.linalg.inv(x.T @ x)
    beta = bread @ (x.T @ y)
    residuals = y - x @ beta
    n, k = x.shape
    if evaluator_clusters:
        groups, levels = pd.factorize(frame.eval_id)
        g = len(levels)
        scores = np.zeros((g, k))
        np.add.at(scores, groups, x * residuals[:, None])
        # Stata regress, vce(cluster eval_id), including its finite-sample factor.
        covariance = bread @ (scores.T @ scores) @ bread * (g / (g - 1)) * ((n - 1) / (n - k))
        degrees_freedom = g - 1
    else:
        # Stata regress, vce(robust), for reproducing the printed anchoring test.
        covariance = bread @ (x.T @ ((residuals ** 2)[:, None] * x)) @ bread * n / (n - k)
        degrees_freedom = n - k
    return beta, covariance, degrees_freedom


def compare_printed(estimate, writers, frame, variable, treatment_codes, control_codes):
    stats = estimate["stats"]
    checks = []
    for field, codes in [("n_treatment", treatment_codes), ("n_control", control_codes)]:
        if estimate.get(field) is not None:
            checks.append(printed_check(field, estimate[field], int(writers.condition.isin(codes).sum())))
    if estimate.get("n_total") is not None:
        checks.append(printed_check(
            "n_total", estimate["n_total"], int(writers.condition.isin(treatment_codes + control_codes).sum()),
        ))
    checks.append(printed_check("study_n_analyzed_all_three_arms", 293, len(writers)))
    checks.append(printed_check("n_units_all_three_arms", estimate["n_units"], len(frame)))
    is_rating = variable != "sim_idea"
    if is_rating:
        checks.append(printed_check("n_evaluators_all_three_arms", 600, int(frame.eval_id.nunique())))

    beta, covariance, df = reproduce_model(frame, variable, evaluator_clusters=is_rating)
    assert len(treatment_codes) == len(control_codes) == 1
    level_vectors = {1: np.array([1., 0., 0.]), 2: np.array([1., 1., 0.]), 3: np.array([1., 0., 1.])}
    contrast = level_vectors[treatment_codes[0]] - level_vectors[control_codes[0]]
    coefficient = float(contrast @ beta)
    se = math.sqrt(float(contrast @ covariance @ contrast))
    p_value = float(2 * student_t.sf(abs(coefficient / se), df))
    if stats.get("regression") is not None:
        checks.append(printed_check(
            "regression.coef", stats["regression"]["coef"], coefficient, 3 if is_rating else 2,
        ))
    for field, codes in [("treatment_mean", treatment_codes), ("control_mean", control_codes)]:
        if stats.get(field) is not None:
            mean = float(frame.loc[frame.condition.isin(codes), variable].to_numpy(dtype=float).mean())
            checks.append(printed_check(field, stats[field], mean, 2))
    if stats.get("p_value") is not None:
        # The five-versus-one usefulness comparison prints four decimal places.
        digits = 4 if estimate["slug"] == "s1_usefulness_five_ideas_vs_one_idea" else 3
        checks.append(printed_check("p_value", stats["p_value"], p_value, digits))
    if stats.get("paper_effect") is not None:
        control_mean = float(level_vectors[control_codes[0]] @ beta)
        percent_increase = coefficient / control_mean * 100
        checks.append(printed_check("paper_effect.value_percent", stats["paper_effect"]["value"], percent_increase, 1))
    return checks


def participant_statistics(frame, variable, treatment_codes, control_codes):
    # One row per randomized writer. Each writer produced one story; evaluators
    # are measurement replicates, never the participants counted here.
    participant = frame.groupby(["writer_id", "condition"], as_index=False)[variable].mean()
    participant = participant.loc[participant.condition.isin(treatment_codes + control_codes)]
    treatment = participant.loc[participant.condition.isin(treatment_codes), variable].to_numpy(dtype=float)
    control = participant.loc[participant.condition.isin(control_codes), variable].to_numpy(dtype=float)
    n1, n0 = len(treatment), len(control)
    m1, m0 = float(treatment.mean()), float(control.mean())
    s1, s0 = float(treatment.std(ddof=1)), float(control.std(ddof=1))

    y = participant[variable].to_numpy(dtype=float)
    x = np.column_stack([
        np.ones(len(participant)), participant.condition.isin(treatment_codes).to_numpy(dtype=float),
    ])
    bread = np.linalg.inv(x.T @ x)
    beta = bread @ (x.T @ y)
    residuals = y - x @ beta
    leverage = np.einsum("ij,jk,ik->i", x, bread, x)
    covariance = bread @ (x.T @ ((residuals ** 2 / (1 - leverage))[:, None] * x)) @ bread
    difference_se = math.sqrt(float(covariance[1, 1]))
    # For an intercept and binary treatment indicator, HC2 equals this identity.
    assert math.isclose(difference_se, math.sqrt(s1 * s1 / n1 + s0 * s0 / n0), rel_tol=1e-12)
    assert math.isclose(float(beta[1]), m1 - m0, rel_tol=1e-10, abs_tol=1e-12)
    return {
        "n_treatment": n1, "n_control": n0,
        "treatment_mean": m1, "treatment_sd": s1,
        "control_mean": m0, "control_sd": s0,
        "difference": m1 - m0, "difference_se": difference_se,
        "se_type": "HC2", "n_clusters": None,
    }


def result_notes(variable, treatment_codes, control_codes):
    common = (
        "Randomized unit: individual writer; between-person design, so round=all and no first_round result. "
        "Condition coding: 1=Human-only, 2=Human with one GenAI idea, 3=Human with five GenAI ideas; "
        f"this contrast uses treatment={treatment_codes}, control={control_codes}. "
        "Keep writer records with participant._current_page_name=Finally; exclude the three human-condition "
        "writers reporting AI use in follow_up.1.player.used_ai_tool or its follow_up.2 fallback. "
        "This gives 95/100/98 writers. Retain all assigned AI-arm writers regardless of actual AI uptake. "
        "The two missing DAT scores do not exclude writers from these unconditional analyses. "
    )
    if variable == "sim_idea":
        detail = (
            "Outcome: creators.dta sim_idea, the original stored cosine similarity times 100 for each "
            "writer's one story and its assigned AI idea. These are participant-level observations, "
            "not the across-people diversity measure sim_cstories. The printed control mean and coefficient "
            "are reproduced from float64 copies of the stored scores; the printed p-value uses the paper's "
            "three-arm HC1 model (Stata vce(robust)). Original comparison-idea assignments and scores are "
            "preserved; embeddings are not regenerated. Authors' code names text-embedding-ada-002. "
            "Two story texts differ between raw CSV and processed DTA through UTF-8/Latin-1 mojibake; "
            "using the deposited scores avoids changing the texts or sampling a new comparison idea. "
            "Higher scores mean stronger anchoring to the AI idea. "
        )
    else:
        detail = (
            "Keep evaluator records with participant._current_page_name=Finally, reshape their first-pass "
            "evaluator.{story_number}.player ratings, and inner join story_id to eligible writers. "
            "This drops 81 of 3600 ratings, retaining 3519 ratings from 600 evaluators; ratings were "
            "collected before AI-use disclosure. Every raw item rating, writer identifier, story identifier "
            "and condition matches the processed DTA. "
            f"Outcome variable: {variable}. "
            "Printed statistics are reproduced using rating-level OLS with both AI-arm indicators and "
            "Human-only reference; p-values use Stata's evaluator-clustered covariance correction "
            "G/(G-1)*(N-1)/(N-3) with G=600 and Student t with 599 df. The five-versus-one contrast "
            "uses the difference between the two coefficients in that same model. The reproduction "
            "n_units and study_n_analyzed refer to all three arms, not the pairwise contrast. "
            "For computed results, average all 9-14 ratings within each writer first, then weight writers "
            "equally. Thus computed participant means/differences can differ from printed rating-level values. "
        )
        if variable == "eval_novel_index":
            detail += "The novelty index is the arithmetic mean of novel, original and rare, rebuilt in float64. "
        if variable == "eval_useful_index":
            detail += "The usefulness index is the arithmetic mean of appropriate, feasible and publishable, rebuilt in float64. "
        if variable.endswith("_index"):
            detail += "Rebuilt indices match stored Stata indices within 3.2e-7 (float32 rounding). "
        if variable == "eval_tt_well_written":
            detail += "The raw field tt_badly_written was retained after the question changed to well written; it is not reversed. "
        if variable == "eval_tt_boring":
            detail += "Higher means more boring; the raw treatment-minus-control difference is retained, without sign reversal. "
    return common + detail + (
        "All printed checks must match at the printed precision before participant statistics are computed. "
        "SDs use denominator n-1. Difference is treatment mean minus control mean in the original units. "
        "Final difference_se is the HC2 sandwich SE from pairwise participant-level OLS on an intercept "
        "and treatment indicator; it equals sqrt(treatment_sd^2/n_treatment + control_sd^2/n_control). "
        "No clusters were randomized, so n_clusters is null."
    )


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    writers, ratings = read_and_validate_data()
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        if estimate["construct"] == "diversity":
            skipped.append({"slug": slug, "reason": (
                "Set-dependent story-to-condition similarity cannot be recomputed exactly. creators.dta "
                "provides sim_cstories scalars but no original embedding vectors. The deposited text-only "
                "code names text-embedding-ada-002; its lines 53-57 include the focal story in the condition "
                "centroid, whereas paper pp. 4 and 8 specify all OTHER stories. Neither the original "
                "embeddings nor a faithful reconstruction of the paper's leave-one-out procedure is "
                "available. Raw and processed texts also contain two encoding differences. Per rule 5, "
                "stored scalar scores are not treated as a recomputed set measure or as independent "
                "participant outcomes; no participant SD or HC2 SE is calculated for this diversity estimate."
            )})
            continue
        outcome = None
        for suffix, (treatment_codes, control_codes) in SUFFIXES.items():
            if slug.endswith(suffix):
                outcome = slug[3:-len(suffix)]
                break
        assert outcome in OUTCOMES, slug
        variable = OUTCOMES[outcome]
        stats = estimate["stats"]
        point_reported = (
            (stats.get("regression") or {}).get("coef") is not None
            or stats.get("treatment_mean") is not None
            or stats.get("control_mean") is not None
            or stats.get("difference") is not None
        )
        if not point_reported:
            skipped.append({"slug": slug, "reason": (
                f"Data mapping is available ({variable}; treatment condition {treatment_codes}, "
                f"control condition {control_codes}), but the reconciled extraction and available main "
                "article print no numerical arm mean, difference, or coefficient for this exact contrast. "
                "Only qualitative results or unlabeled figure points are available. Sections S1-S9 and "
                "tables S1-S18 are absent from both local article PDFs and the posted-data folders; direct "
                "publisher and Zenodo requests failed with socket error 10013. Counts alone do not meet "
                "the reproduce-first rule. No participant-level effect, SD, or SE is computed."
            )})
            continue
        frame = writers if variable == "sim_idea" else ratings
        checks = compare_printed(estimate, writers, frame, variable, treatment_codes, control_codes)
        passed = all(c["match"] for c in checks)
        computed = participant_statistics(frame, variable, treatment_codes, control_codes) if passed else {
            field: None for field in [
                "n_treatment", "n_control", "treatment_mean", "treatment_sd", "control_mean",
                "control_sd", "difference", "difference_se", "se_type", "n_clusters",
            ]
        }
        notes = result_notes(variable, treatment_codes, control_codes)
        if not passed:
            failures = [{k: c[k] for k in ["statistic", "printed", "computed"]} for c in checks if not c["match"]]
            notes += " Reproduction failed; no participant statistics calculated: " + json.dumps(failures)
        results.append({
            "slug": slug, "round": "all", "reproduced": checks, "computed": computed, "notes": notes,
        })

    assert len(results) + len(skipped) == len(extraction["estimates"])
    assert len({r["slug"] for r in results + skipped}) == len(extraction["estimates"])
    output = {
        "cid": "c006", "analyst": "A", "script": SCRIPT.as_posix(),
        "data_files": [p.as_posix() for p in CONSULTED_FILES],
        "results": results, "skipped": skipped,
    }
    # Validate serialization before writing, so NaN/Infinity cannot enter JSON.
    json.dumps(output, ensure_ascii=False, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == output
    print(json.dumps({
        "cid": parsed["cid"], "n_results": len(parsed["results"]),
        "n_reproduced": sum(all(v["match"] for v in r["reproduced"]) for r in parsed["results"]),
        "n_skipped": len(parsed["skipped"]),
    }))


if __name__ == "__main__":
    main()
