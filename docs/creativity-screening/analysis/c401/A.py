"""Independent analyst A calculations for c401.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c401/A.py
Only A.json is written. Deposit programs are never run or imported.

The complete 151,997-character manuscript markdown, including the supplement,
was read in eight consecutive chunks. Printed values were checked against PDF
pages 10, 19, 23, 32, 51, and 52 (including Table S2 with find_tables).

Author code inspected AS TEXT establishes the following mappings:
* preprocessing/preprocessing.R, lines 26-93: exclusions; lines 123-131:
  marketing_answer is each person's final campaign.
* figures/fig4_causal_mediation/compute_CI_measures.R, lines 266-268:
  campaign_wc is the final campaign word count.
* preprocessing/extract_campaign_edits.R, lines 218-336: tokenize lowercase
  words, compute Jaccard overlap with AI responses identified as campaigns,
  retain each person's maximum overlap, and assign zero overlap when no
  campaign is identified. Lines 373-378: use ORIGINAL ROW POSITION (not the
  anonymized participant_id), and regress 1-overlap on three arm indicators
  plus msg_count, without a separate intercept.
* figures/fig2_quality_creativity/creativity_analysis.R, lines 160-212:
  GPT-4o themes, text-embedding-3-large, human and simulated campaigns pooled,
  1-cosine similarity, then percentile rank on a 0-100 scale.
* figures/fig_s2_elo_ratings/sensitivity_elo_creativity.R, lines 175-192:
  the cached sensitivity creativity variable is an empirical CDF, not the
  main manuscript's saved percentile scores.
* figures/fig_s1_sensitivity/intraclass_correlation_ratings.R, lines 13-47:
  the available human ratings are five separate Likert dimensions; these
  are not the expert-human pairwise Elo validation.

The editing percentage reproduction reveals post-treatment adjustment not
identified in the reconciled extraction. Preserve this eligibility issue in
the result notes. The requested new statistics are unadjusted; do not label
the printed adjusted levels as observed participant means.
"""

import sys

sys.dont_write_bytecode = True

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t


SCREENING = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data/osf-kzuge")
PACKAGE = DEPOSIT / "osf_package"
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
SCRIPT = SCREENING / "analysis/c401/A.py"
OUTPUT = SCREENING / "analysis/c401/A.json"
EXTRACTION = SCREENING / "extraction/c401.json"


def read_json(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


manifest = read_json(MANIFEST)
extraction = read_json(EXTRACTION)
estimates = {e["slug"]: e for e in extraction["estimates"]}
deposited_files = manifest["deposits"]["osf-kzuge"]["files"]
data_files = [MANIFEST.as_posix()]


def read_csv(relative):
    """Read untrusted tabular data and verify its recorded download hash."""
    path = PACKAGE / relative
    expected_hash = deposited_files["osf_package/" + relative]["sha256"]
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError("Manifest hash mismatch: " + path.as_posix())
    data_files.append(path.as_posix())
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def check(statistic, printed, computed, decimals=0):
    """Compare at the printed precision; keep unrounded computed values."""
    if computed is None or not math.isfinite(float(computed)):
        match = False
        computed = None
    else:
        computed = int(computed) if decimals == 0 else float(computed)
        quantum = Decimal(1).scaleb(-decimals)
        match = (
            Decimal(str(computed)).quantize(quantum, rounding=ROUND_HALF_UP)
            == Decimal(str(printed)).quantize(quantum, rounding=ROUND_HALF_UP)
        )
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(match),
    }


def ols_classical(y, x):
    """OLS coefficients and conventional t p-values, for reproduction only."""
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ beta
    df = len(y) - x.shape[1]
    covariance = (resid @ resid / df) * np.linalg.inv(x.T @ x)
    standard_errors = np.sqrt(np.diag(covariance))
    p_values = 2 * student_t.sf(np.abs(beta / standard_errors), df)
    return beta, p_values


def participant_contrast(rows, outcome, treatment, control="basegpt"):
    """Average within participant, then use two-arm OLS with HC2 variance."""
    grouped = defaultdict(list)
    assignments = {}
    for row, value in zip(rows, outcome, strict=True):
        arm = row["randomization"]
        if arm not in (treatment, control):
            continue
        participant = row["participant_id"]
        if participant in assignments:
            assert assignments[participant] == arm
        assignments[participant] = arm
        grouped[participant].append(float(value))
    participant_values = {pid: float(np.mean(v)) for pid, v in grouped.items()}
    treatment_values = np.array([
        participant_values[pid] for pid in grouped if assignments[pid] == treatment
    ])
    control_values = np.array([
        participant_values[pid] for pid in grouped if assignments[pid] == control
    ])
    n_t = len(treatment_values)
    n_c = len(control_values)
    assert n_t > 1 and n_c > 1
    y = np.concatenate([control_values, treatment_values])
    x = np.column_stack([
        np.ones(n_c + n_t), np.concatenate([np.zeros(n_c), np.ones(n_t)])
    ])
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    bread = np.linalg.inv(x.T @ x)
    residuals = y - x @ beta
    leverage = np.sum((x @ bread) * x, axis=1)
    meat = x.T @ (x * (residuals**2 / (1 - leverage))[:, None])
    covariance = bread @ meat @ bread
    difference_se = math.sqrt(float(covariance[1, 1]))
    sd_t = float(np.std(treatment_values, ddof=1))
    sd_c = float(np.std(control_values, ddof=1))
    difference = float(np.mean(treatment_values) - np.mean(control_values))
    # This identity independently checks HC2 for an intercept and arm indicator.
    assert math.isclose(difference_se, math.sqrt(sd_t**2 / n_t + sd_c**2 / n_c), rel_tol=1e-12)
    assert math.isclose(float(beta[1]), difference, rel_tol=1e-11, abs_tol=1e-10)
    return {
        "n_treatment": n_t,
        "n_control": n_c,
        "treatment_mean": float(np.mean(treatment_values)),
        "treatment_sd": sd_t,
        "control_mean": float(np.mean(control_values)),
        "control_sd": sd_c,
        "difference": difference,
        "difference_se": difference_se,
        "se_type": "HC2",
        "n_clusters": None,
    }


codebook = read_csv("data/codebook.csv")
participants = read_csv("data/processed/creativity_df_CI.csv")
overlap = read_csv("data/processed/campaign_text_overlap.csv")
human_subset = read_csv("data/supplementary/human_expertise_campaigns.csv")
other_campaigns = read_csv("data/supplementary/all_campaigns.csv")
raw_likert = read_csv("data/processed/Batch_5322742_batch_results.csv")
mean_likert = read_csv("data/evaluations/human/human_campaign_evaluations.csv")
llm_elo = read_csv("data/evaluations/elo_ratings/elo_ratings_gpt-4o-mini.csv")
cached_diversity = read_csv("data/evaluations/elo_ratings/elo_real_vs_simulated.csv")
llm_scores = read_csv("data/supplementary/creativity_df_evaluated_scored.csv")
llm_evaluations = read_csv("data/evaluations/llm_scores/campaign_evaluations_gpt-4o-mini.csv")

assert len({r["participant_id"] for r in participants}) == len(participants) == 331
arm_counts = Counter(r["randomization"] for r in participants)
assert arm_counts == {"basegpt": 116, "creativegpt": 114, "creativegpt_rand": 101}
for row in participants:
    # These criteria were already applied to the archived 331-person dataset.
    assert row["BFI_44_30"] == "Agree a Little"
    assert row["PANAS_9"] == "A Little"
    assert row["LLM_check"] == "No"
    assert float(row["duration_seconds"]) >= 1800
    assert float(row["msg_count_interview"]) > 0
    assert float(row["response_count"]) > 0
    assert math.isfinite(float(row["campaign_wc"]))

study = extraction["studies"][0]
assert study["assignment_unit"] == "individual"
assert all(e["within_person"] is None for e in estimates.values())
assert {r["column_name"] for r in codebook} >= {"participant_id", "randomization", "campaign_wc"}

results = []
skipped = []


def add_result(slug, reproduced, outcome, treatment, notes):
    """Never calculate participant SDs/SEs if required reproduction fails."""
    if not all(item["match"] for item in reproduced):
        failures = [item for item in reproduced if not item["match"]]
        results.append({
            "slug": slug,
            "round": "all",
            "reproduced": reproduced,
            "computed": {key: None for key in [
                "n_treatment", "n_control", "treatment_mean", "treatment_sd",
                "control_mean", "control_sd", "difference", "difference_se",
                "se_type", "n_clusters",
            ]},
            "notes": notes + " Required reproduction failed; no new effect statistics calculated.",
        })
        skipped.append({"slug": slug, "reason": "Reproduction failure: " + json.dumps(failures)})
        return
    results.append({
        "slug": slug,
        "round": "all",
        "reproduced": reproduced,
        "computed": participant_contrast(participants, outcome, treatment),
        "notes": notes,
    })


# Expert Elo: verify the available files describe a different rating exercise.
assert len(human_subset) == 100
assert Counter(r["condition"] for r in human_subset) == {"basegpt": 50, "creativegpt": 50}
assert "elo" not in " ".join(human_subset[0]).lower()
assert len(raw_likert) == 1655
assert Counter(Counter(r["participant_id"] for r in raw_likert).values()) == {5: 331}
assert len(mean_likert) == 331
assert {"run_1", "run_2", "run_3", "run_4", "run_5"} <= set(llm_elo[0])
skipped.append({
    "slug": "s1_quality_expert_elo_personalized_vs_generic",
    "reason": (
        "Cannot reproduce the expert-human Elo coefficient 158.2 (p=0.14; PDF p.32). "
        "human_expertise_campaigns.csv contains 100 campaign records (50 personalized, "
        "50 generic), but only metadata and marketing_score (6-8), with no expert Elo "
        "scores or pairwise judgments/order. all_campaigns.csv likewise has no expert Elo. "
        "The available Batch_5322742_batch_results.csv has 1,655 Likert ratings across "
        "331 participants (five ratings per campaign on five 1-5 dimensions), and "
        "human_campaign_evaluations.csv has their participant summaries; these are "
        "not the reported 100-campaign Prolific expert pairwise validation. The saved "
        "Elo rating runs are from LLM judges. The paper also omits the complete expert "
        "regression specification. No outcome or standard error is substituted."
    ),
})


# Diversity: the saved sensitivity ranks cannot replace the missing main analysis.
assert "marketing_answer" not in participants[0]
assert not (PACKAGE / "data/processed/campaign_themes.rds").exists()
assert not (PACKAGE / "data/processed/Creativity_Data.csv").exists()
assert not (PACKAGE / "data/simulation/personalized_campaigns_simulated.csv").exists()
cached_counts = Counter(r["randomization"] for r in cached_diversity)
assert cached_counts == dict(arm_counts, sim=100)
cached_means_100 = {
    arm: float(np.mean([float(r["creativity"]) * 100 for r in cached_diversity if r["randomization"] == arm]))
    for arm in arm_counts
}
for treatment, suffix in [
    ("creativegpt", "personalized"),
    ("creativegpt_rand", "partially_personalized"),
]:
    slug = "s1_theme_diversity_" + suffix + "_vs_generic"
    stats = estimates[slug]["stats"]
    skipped.append({
        "slug": slug,
        "reason": (
            "Cannot reproduce the same GPT-4o theme extraction and text-embedding-3-large "
            "pooled-centroid procedure. The downloaded data lack the human final campaign "
            "texts, saved campaign_themes.rds, theme embeddings, the referenced "
            "personalized_campaigns_simulated.csv, and main Creativity_Data.csv. Author "
            "creativity_analysis.R lines 160-212 pools human and 100 simulated campaigns, "
            "computes 1-cosine similarity, and converts to 0-100 percentile ranks. "
            "elo_real_vs_simulated.csv supplies a different sensitivity-analysis empirical "
            "CDF score (sensitivity_elo_creativity.R lines 175-192). Multiplying that "
            "stored CDF by 100 gives treatment/control means "
            f"{cached_means_100[treatment]:.12f}/{cached_means_100['basegpt']:.12f}, "
            f"not the printed {stats['treatment_mean']:.1f}/{stats['control_mean']:.1f} "
            "(PDF p.10), despite matching the arm counts. These are diagnostic checks "
            "of the available cache, not a re-estimation of the published diversity "
            "measure. Per task rule 5, no replacement embeddings, participant SDs, "
            "or HC2 diversity effect are calculated."
        ),
    })


# Reproduce both length coefficients and p-values using all three randomized arms.
word_count = np.array([float(r["campaign_wc"]) for r in participants])
x_length = np.array([
    [1.0, float(r["randomization"] == "creativegpt"), float(r["randomization"] == "creativegpt_rand")]
    for r in participants
])
length_beta, length_p = ols_classical(word_count, x_length)
for treatment, suffix, coefficient_index in [
    ("creativegpt", "personalized", 1),
    ("creativegpt_rand", "partially_personalized", 2),
]:
    slug = "s1_campaign_word_count_" + suffix + "_vs_generic"
    estimate = estimates[slug]
    reproduced = [
        check("n_treatment", estimate["n_treatment"], arm_counts[treatment]),
        check("n_control", estimate["n_control"], arm_counts["basegpt"]),
        check("study_n_analyzed", study["n_analyzed"], len(participants)),
        check("regression.coef", estimate["stats"]["regression"]["coef"], length_beta[coefficient_index], 1),
        check("p_value", estimate["stats"]["p_value"], length_p[coefficient_index], 2),
        check("all_three_arms_mean_PDF_p19", 355.4, float(np.mean(word_count)), 1),
        check("all_three_arms_sd_PDF_p19", 148.0, float(np.std(word_count, ddof=1)), 1),
    ]
    add_result(
        slug, reproduced, word_count, treatment,
        "Source: creativity_df_CI.csv; one final campaign per unique participant_id; "
        "campaign_wc is the final submitted campaign word count (data/codebook.csv; "
        "compute_CI_measures.R lines 266-268). All 331 rows already satisfy the "
        "published attention-check, external-AI-use, engagement and >=30-minute "
        "duration exclusions (preprocessing.R lines 45-93); no additional exclusions "
        "or missing word counts. basegpt=Generic AI, creativegpt=Personalized AI, "
        "creativegpt_rand=Partially personalized AI. Counts: PDF pp.19,52/Table S2. "
        "The printed coefficients and p-values (PDF p.19) reproduce with unadjusted "
        "OLS campaign_wc ~ arm using all three arms and conventional t tests "
        "(328 residual degrees of freedom). The pooled descriptive mean/SD also "
        "reproduce, but that pooled SD is not used as either arm's SD. The computed "
        "object uses only the named two arms, averages within participant first "
        "(one observation here), uses sample SDs with n-1 denominators, and fits "
        "OLS on an intercept plus treatment indicator with HC2 robust covariance. "
        "Individual randomization; no clusters or paired rounds. Difference is "
        "treatment minus generic, in words; more words does not necessarily imply "
        "greater creativity. Both length contrasts share the same generic control."
    )


# Editing: establish the exact join before estimating either the paper's model
# or the requested unadjusted participant comparison. Anonymized IDs are shuffled.
assert len(overlap) == 331
overlap_by_row = {int(r["row_index"]): r for r in overlap}
assert set(overlap_by_row) == set(range(1, 332))
for position, row in enumerate(participants, start=1):
    saved = overlap_by_row[position]
    assert (saved["is_base"] == "TRUE") == (row["randomization"] == "basegpt")
    assert 0 <= float(saved["overlap_score"]) <= 1
edits = np.array([
    100 * (1 - float(overlap_by_row[i + 1]["overlap_score"])) for i in range(len(participants))
])
x_edits = np.array([
    [float(r["randomization"] == arm) for arm in ["basegpt", "creativegpt", "creativegpt_rand"]]
    + [float(r["msg_count"])] for r in participants
])
edit_beta = np.linalg.lstsq(x_edits, edits, rcond=None)[0]
slug = "s1_final_campaign_word_changes_personalized_vs_generic"
estimate = estimates[slug]
study_arm_n = {r["name"]: r["n_analyzed"] for r in study["arms"]}
edit_reproduction = [
    check("n_treatment_from_Table_S2", study_arm_n["Personalized AI"], arm_counts["creativegpt"]),
    check("n_control_from_Table_S2", study_arm_n["Generic AI"], arm_counts["basegpt"]),
    check("study_n_analyzed", study["n_analyzed"], len(participants)),
    check("adjusted_treatment_level_at_zero_messages", estimate["stats"]["treatment_mean"], edit_beta[1], 1),
    check("adjusted_control_level_at_zero_messages", estimate["stats"]["control_mean"], edit_beta[0], 1),
]
no_campaign_t = sum(
    overlap_by_row[i + 1]["column_name"] in ("", "NA")
    for i, r in enumerate(participants) if r["randomization"] == "creativegpt"
)
no_campaign_c = sum(
    overlap_by_row[i + 1]["column_name"] in ("", "NA")
    for i, r in enumerate(participants) if r["randomization"] == "basegpt"
)
add_result(
    slug, edit_reproduction, edits, "creativegpt",
    "IMPORTANT EXTRACTION CORRECTION: the printed 64.5% personalized and 80.5% "
    "generic values (PDF p.51) are not observed arm means. They reproduce as "
    "arm coefficients at msg_count=0 from the Gaussian identity model "
    "100*(1-overlap_score) ~ randomization + msg_count - 1, fit to all 331 people "
    "(extract_campaign_edits.R lines 373-378). The message-count coefficient "
    f"is {float(edit_beta[3]):.12f} percentage points per message. msg_count is "
    "post-treatment: extraction-spec rule 5 excludes the paper's adjusted "
    "comparison. Flag the reconciled extraction for correction. As explicitly "
    "requested by the data-analysis brief, the computed object supplies the "
    "UNADJUSTED participant-level replacement, not the adjusted printed levels. "
    "Construct other is descriptive and must never be pooled as creativity. "
    "Source: campaign_text_overlap.csv joined by one-based row_index to the "
    "original row order of creativity_df_CI.csv, as in the authors' code; "
    "row_index is not participant_id. All 331 mappings agree with the saved "
    "generic-arm flags. The saved participant outcome is 100*(1-maximum "
    "Jaccard overlap) between final campaign and identified AI campaign "
    "responses, using unique lowercase word sets; it is not a token edit "
    "distance or pooled fraction of individual words changed. There is one "
    "saved maximum-overlap score per participant. The authors assign overlap "
    "zero when no AI campaign is identified; preserve these rows as 100% "
    f"difference ({no_campaign_t} personalized, {no_campaign_c} generic). "
    "No new exclusions; counts reproduce Table S2's general analyzed sample "
    "because every participant has a stored outcome (no editing-specific "
    "counts are printed). The final campaign and AI response texts are not "
    "available to re-audit the original LLM campaign detection or tokenization. "
    "Participant-level sample SDs and two-arm OLS HC2 standard errors are "
    "computed only after reproducing the printed adjusted levels. Difference "
    "is personalized minus generic in percentage points, with no sign reversal. "
    "Individual between-person design; only round all applies."
)


assert set(estimates) == {r["slug"] for r in results} | {r["slug"] for r in skipped}
assert len({(r["slug"], r["round"]) for r in results}) == len(results)
output = {
    "cid": "c401",
    "analyst": "A",
    "script": SCRIPT.as_posix(),
    "data_files": data_files,
    "results": results,
    "skipped": skipped,
}
with OUTPUT.open("w", encoding="utf-8") as fh:
    json.dump(output, fh, ensure_ascii=False, indent=1)

# Re-open the exact output with Python to verify a complete, valid JSON file.
parsed = read_json(OUTPUT)
assert parsed == output
assert parsed["cid"] == "c401" and parsed["analyst"] == "A"
print(json.dumps({
    "cid": "c401",
    "n_results": len(results),
    "n_reproduced": sum(bool(r["reproduced"]) and all(c["match"] for c in r["reproduced"]) for r in results),
    "n_skipped": len(skipped),
}))
