"""Independent analyst B reanalysis for c489.

Run with: python -I -B <absolute path to this file>
Writes only B.json, next to this script. No deposited code is executed.

The entire main-article markdown (69,821 characters) and supplement markdown
(60,667 characters, including all 49 supplement pages) were read in successive
chunks. Main PDF pp. 3-8 and supplement PDF pp. 2, 5-7 were checked with
PyMuPDF. Rules: creativity-codebook.md sections 7-11 and extraction-spec.md.

Results contain nine successful participant-level analyses and six failed
reproduction attempts. For failed attempts every computed field is null.
Skipped contains the other 18 estimates, for which the measurement pipeline
cannot be reproduced exactly from the available files. These lists are disjoint
and cover all 33 reconciled extraction slugs. n_reproduced counts results for
which every reproduction check passes and participant statistics are supplied.

All writer assignments are between people. The paired recipient tests below
only reproduce the paper's tests; recipients are not treated as the people
randomized to AI. Consequently there are no paired or first-round writer
estimates. Set-level diversity scores are never used as participant outcomes.
"""

import sys

sys.dont_write_bytecode = True

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from rapidfuzz.distance import Levenshtein
from scipy import stats


BASE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA_ROOT = Path(r"D:/projects/ai-skill-atlas/creativity-data/osf-jx2es")
EXTRACTION = BASE / "extraction/c489.json"
MANIFEST = DATA_ROOT.parent / "manifest.json"
SCRIPT = BASE / "analysis/c489/B.py"
OUTPUT = BASE / "analysis/c489/B.json"

DATA_PATHS = {
    "S1": DATA_ROOT / "Experiment 1/data.csv",
    "S2": DATA_ROOT / "Experiment 2/data.csv",
    "S3": DATA_ROOT / "Experiment 3/data.csv",
    "ratings": DATA_ROOT / "Experiment 4/S4_data.csv",
    "S5": DATA_ROOT / "SI Appendix/SI_study1/SA1_data.csv",
    "S6": DATA_ROOT / "SI Appendix/SI_study2/SA2_data.csv",
}

ARM_MAP = {
    "S1": {"ChatGPT": "gpt", "Google": "google"},
    "S2": {"ChatGPT (simulated)": "gpt", "Google (simulated)": "google"},
    "S3": {"Google LLM (AI Overview)": "AI", "Google standard": "Google"},
    "S5": {"LLM": "gpt", "LLM + real-time web links": "link", "Web search": "google"},
    "S6": {"ChatGPT": "gpt", "Google": "google"},
}

COMPUTED_KEYS = (
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se",
    "se_type", "n_clusters",
)


def check(statistic, printed, computed, decimals=None):
    """Compare only at the precision printed in the paper, not with a loose tolerance."""
    if isinstance(computed, np.generic):
        computed = computed.item()
    if isinstance(printed, str) and printed.startswith("<"):
        match = math.isfinite(computed) and computed < float(printed[1:])
    elif decimals is not None:
        match = math.isfinite(computed) and round(float(computed), decimals) == float(printed)
    else:
        match = computed == printed
    return {
        "statistic": statistic, "printed": printed, "computed": computed,
        "match": bool(match),
    }


def numbers(rows, column):
    """No imputation or undisclosed dropping of missing observations."""
    values = np.asarray([float(r[column]) for r in rows], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"Missing/nonfinite value in {column}")
    return values


def mean(values):
    return float(np.mean(values))


def arm_rows(rows, condition):
    return [r for r in rows if r["condition"] == condition]


def contrast_rows(estimate, datasets):
    sid = estimate["study_id"]
    mapping = ARM_MAP[sid]
    rows = datasets[sid]
    return (
        arm_rows(rows, mapping[estimate["treatment_arm"]]),
        arm_rows(rows, mapping[estimate["control_arm"]]),
    )


def hc2_summary(treatment, control):
    """OLS on an intercept and arm indicator; full HC2 sandwich covariance."""
    n1, n0 = len(treatment), len(control)
    if min(n1, n0) < 2:
        raise ValueError("At least two independent people per arm are required")
    y = np.concatenate((treatment, control))
    indicator = np.concatenate((np.ones(n1), np.zeros(n0)))
    design = np.column_stack((np.ones(n1 + n0), indicator))
    bread = np.linalg.inv(design.T @ design)
    coefficients = bread @ design.T @ y
    residual = y - design @ coefficients
    leverage = np.einsum("ij,jk,ik->i", design, bread, design)
    weights = residual ** 2 / (1.0 - leverage)
    covariance = bread @ (design.T @ (weights[:, None] * design)) @ bread
    sd1 = float(np.std(treatment, ddof=1))
    sd0 = float(np.std(control, ddof=1))
    difference = mean(treatment) - mean(control)
    se = math.sqrt(float(covariance[1, 1]))
    # Independent algebraic identity for two-group HC2; not a pooled-variance SE.
    assert math.isclose(se, math.sqrt(sd1 ** 2 / n1 + sd0 ** 2 / n0), rel_tol=1e-11)
    assert math.isclose(float(coefficients[1]), difference, rel_tol=1e-11, abs_tol=1e-11)
    return {
        "n_treatment": n1, "n_control": n0,
        "treatment_mean": mean(treatment), "treatment_sd": sd1,
        "control_mean": mean(control), "control_sd": sd0,
        "difference": difference, "difference_se": se,
        "se_type": "HC2", "n_clusters": None,
    }


def empty_computed():
    return dict.fromkeys(COMPUTED_KEYS)


def result(estimate, checks, notes, computed=None):
    if computed is not None:
        assert all(c["match"] for c in checks), estimate["slug"]
    else:
        assert any(not c["match"] for c in checks), estimate["slug"]
    return {
        "slug": estimate["slug"], "round": "all", "reproduced": checks,
        "computed": computed if computed is not None else empty_computed(),
        "notes": notes,
    }


def direct_score_result(estimate, datasets, studies):
    sid = estimate["study_id"]
    tr, cr = contrast_rows(estimate, datasets)
    is_words = estimate["measure"] == "length"
    column = "wordcount" if is_words else ("n_unique_entities" if sid == "S5" else "num_unique_entities")
    t, c = numbers(tr, column), numbers(cr, column)
    decimals = 3 if sid in ("S1", "S3") else 2
    printed = estimate["stats"]
    checks = [
        check("treatment_mean", printed["treatment_mean"], mean(t), decimals),
        check("control_mean", printed["control_mean"], mean(c), decimals),
        check("study_n_analyzed", studies[sid]["n_analyzed"], len(datasets[sid])),
    ]
    if sid == "S5":
        link_arm = next(a for a in studies[sid]["arms"] if a["name"] == "LLM + real-time web links")
        checks.append(check("study_links_arm_n_analyzed", link_arm["n_analyzed"], len(arm_rows(datasets[sid], "link"))))
        groups = [numbers(arm_rows(datasets[sid], arm), column) for arm in ("gpt", "google", "link")]
        anova = stats.f_oneway(*groups)
        checks.extend([
            check("study_omnibus_F", 0.43 if is_words else 15.44, float(anova.statistic), 2),
            check("study_omnibus_df", [2, 2399], [len(groups) - 1, sum(map(len, groups)) - len(groups)]),
            check("study_omnibus_p", 0.648 if is_words else "<.001", float(anova.pvalue), 3),
        ])
    else:
        anova = stats.f_oneway(t, c)
        checks.extend([
            check("F", printed["test"]["value"], float(anova.statistic), 2),
            check("F_df", printed["test"]["df"], [1, len(t) + len(c) - 2]),
            check("p_value", printed["p_value"], float(anova.pvalue), 3),
        ])

    if sid == "S6":
        notes = (
            f"FAILED REPRODUCTION. SA2_data.csv has {len(datasets[sid])} complete data rows "
            f"({len(t)} ChatGPT, {len(c)} Google), whereas supplement PDF p. 6 states "
            f"{studies[sid]['n_analyzed']} analyzed people. No attention-check or exclusion flag "
            "is supplied. On all posted rows num_unique_entities averages "
            f"{mean(t):.12f} (ChatGPT; rounds to {mean(t):.2f}, printed 2.91) and "
            f"{mean(c):.12f} (Google; printed 2.83). The F statistic and p-value round "
            "to the printed values, but the available-data residual df is 1997, not the "
            "printed 1971. Neither the sample nor both arm means reproduce; no post-hoc "
            "exclusions, truncation of the treatment mean, SDs, or effects are supplied. "
            "All computed fields are null, including se_type because no SE was estimated."
        )
        return result(estimate, checks, notes)

    assert all(k["match"] for k in checks), (estimate["slug"], checks)
    exclusions = {
        "S1": "All 1,104 posted rows; the file matches the final sample after the paper's 32 attention-check exclusions (main PDF p. 3).",
        "S2": "All 1,979 posted rows; the file matches the final sample after the paper's 37 attention-check exclusions (main PDF p. 6).",
        "S3": "All 250 posted rows; the file matches the final sample after the paper's three attention-check exclusions (main PDF p. 7).",
        "S5": "All 2,402 posted rows across three arms; the file matches the final sample after five unrelated-advice exclusions and 98 technical exclusions (supplement PDF p. 2).",
    }
    notes = (
        f"{exclusions[sid]} No additional exclusions or missing-value drops. "
        f"Outcome column: {column}; treatment condition={ARM_MAP[sid][estimate['treatment_arm']]}, "
        f"control condition={ARM_MAP[sid][estimate['control_arm']]}. Each data row is one "
        "writer with one advice output; the posted numeric score is used directly, without "
        "rerunning spaCy or substituting a different tokenizer. Sample SDs use n - 1. "
        "Difference is treatment minus control in the original outcome units. SE is from "
        "OLS of the writer outcome on an intercept and treatment indicator with HC2 "
        "covariance. No standardized effect or sign reversal is applied. The conventional "
        "ANOVA checks reproduce the printed test only; that ANOVA is not used for the new SE. "
    )
    if sid == "S5":
        notes += (
            "The study_n_analyzed and omnibus checks cover all three arms, not the "
            "two-arm contrast; only the named two arms enter the computed HC2 result. "
            "Google has 787 people, plain GPT has 803, and GPT-links has 812. "
            "All pairwise contrasts share their corresponding original arm samples. "
            "Printed means have two decimal places (supplement PDF p. 5)."
        )
    else:
        notes += f"Printed means have {decimals} decimal places."
    return result(estimate, checks, notes, hc2_summary(t, c))


def normalize_advice(text):
    """Link only by exact characters after removing whitespace; no fuzzy matching."""
    return "".join(text.split())


def audit_rating_corpus(datasets):
    writers = datasets["S3"]
    recipients = datasets["ratings"]
    lookup = {}
    for data_row, writer in enumerate(writers, start=1):
        key = normalize_advice(writer["advice"])
        assert key not in lookup, "Nonunique writer advice would make linkage ambiguous"
        lookup[key] = (data_row, "gpt" if writer["condition"] == "AI" else "google")
    unique = defaultdict(set)
    matched_rows = defaultdict(list)
    matched_writers = defaultdict(set)
    unmatched = defaultdict(lambda: defaultdict(list))
    for data_row, recipient in enumerate(recipients, start=1):
        assert {recipient["0.key"], recipient["1.key"]} == {"google", "gpt"}
        for slot in (0, 1):
            arm = recipient[f"{slot}.key"]
            key = normalize_advice(recipient[f"{slot}.advice"])
            unique[arm].add(key)
            if key in lookup:
                writer_row, writer_arm = lookup[key]
                assert writer_arm == arm
                matched_rows[arm].append(recipient)
                matched_writers[arm].add(writer_row)
            else:
                unmatched[arm][key].append(data_row)
    assert sum(map(len, matched_writers.values())) == len(writers)
    return {
        "unique": unique, "matched_rows": matched_rows,
        "matched_writers": matched_writers, "unmatched": unmatched,
    }


def corpus_checks(audit):
    # Main PDF p. 8 explicitly says the sampling corpus contains 125 texts per arm.
    # These are text counts, not asserted counts of randomized people.
    return [
        check("source_corpus_treatment_texts", 125, len(audit["unique"]["gpt"])),
        check("source_corpus_control_texts", 125, len(audit["unique"]["google"])),
    ]


def corpus_note(audit):
    unmatched_t = sum(map(len, audit["unmatched"]["gpt"].values()))
    unmatched_c = sum(map(len, audit["unmatched"]["google"].values()))
    matched_t = len(audit["matched_writers"]["gpt"])
    matched_c = len(audit["matched_writers"]["google"])
    return (
        f"After exact matching with whitespace removed, all {matched_t + matched_c} "
        f"included Experiment 3 writers ({matched_t} AI, {matched_c} Google) have ratings. "
        f"However, the recipient file contains {len(audit['unique']['gpt'])} unique AI "
        f"texts and {len(audit['unique']['google'])} unique Google texts, versus 125 "
        "per arm stated on main PDF p. 8. Three additional advice texts cannot be linked "
        f"to any included writer and account for {unmatched_t} AI and {unmatched_c} "
        "Google ratings. It cannot be established from these files that these are three "
        "additional independent randomized writers or that they should be included "
        "after the reported writer exclusions. They are not silently counted as people. "
    )


def rating_result(estimate, datasets, audit):
    slug = estimate["slug"]
    metric = next(v for k, v in {
        "helpfulness": "helpful", "informativeness": "informative",
        "trustworthiness": "trust", "apparent_effort": "effort",
    }.items() if f"s3_{k}_" in slug)
    recipients = datasets["ratings"]
    t, c = numbers(recipients, f"gpt_{metric}"), numbers(recipients, f"google_{metric}")
    paired = stats.ttest_rel(t, c)
    printed = estimate["stats"]
    checks = [
        check("treatment_mean_all_posted_ratings", printed["treatment_mean"], mean(t), 3),
        check("control_mean_all_posted_ratings", printed["control_mean"], mean(c), 3),
        check("n_recipients", 1493, len(recipients)),
        check("repeated_measures_F", printed["test"]["value"], float(paired.statistic ** 2), 3),
        check("repeated_measures_F_df", printed["test"]["df"], [1, len(recipients) - 1]),
        check("p_value", printed["p_value"], float(paired.pvalue)),
    ] + corpus_checks(audit)
    matched_t = numbers(audit["matched_rows"]["gpt"], f"gpt_{metric}")
    matched_c = numbers(audit["matched_rows"]["google"], f"google_{metric}")
    checks.extend([
        check("treatment_mean_ratings_of_confirmed_writers_only", printed["treatment_mean"], mean(matched_t), 3),
        check("control_mean_ratings_of_confirmed_writers_only", printed["control_mean"], mean(matched_c), 3),
    ])
    notes = (
        "FAILED WRITER-SAMPLE REPRODUCTION. All 1,493 posted recipients reproduce "
        "both published rating-weighted means and the repeated-measures F test at "
        "printed precision (main PDF p. 8). " + corpus_note(audit) +
        f"Restricting to the verified writer sample leaves {len(matched_t)} AI ratings "
        f"and {len(matched_c)} Google ratings, with respective means {mean(matched_t):.12f} "
        f"and {mean(matched_c):.12f}; these do not jointly reproduce the printed means. "
        "The reported rating analysis therefore cannot be reproduced on the confirmed "
        "writer sample. In accordance with the reproduce-first rule, no participant "
        "SD, effect, or SE is computed and all computed fields are null. The paired "
        "recipient test above is a reproduction diagnostic, not an eligible paired "
        "AI-assistance design: writer assignment is between people. No first-round "
        "writer result is appropriate."
    )
    return result(estimate, checks, notes)


def choice_result(estimate, datasets, audit):
    recipients = datasets["ratings"]
    counts = Counter(r["choice"] for r in recipients)
    assert set(counts) == {"google", "gpt", "similar"}
    for r in recipients:
        compare = r["compare"]
        if "1st" in compare:
            assert r["choice"] == r["0.key"]
        elif "2nd" in compare:
            assert r["choice"] == r["1.key"]
        else:
            assert "similarly" in compare and r["choice"] == "similar"
    n = len(recipients)
    chi = stats.chisquare([counts["google"], counts["gpt"], counts["similar"]])
    printed = estimate["stats"]
    checks = [
        check("treatment_choice_percent", printed["treatment_mean"], 100 * counts["gpt"] / n, 1),
        check("control_choice_percent", printed["control_mean"], 100 * counts["google"] / n, 1),
        check("n_recipients", 1493, n),
        check("treatment_choice_count", 756, counts["gpt"]),
        check("control_choice_count", 367, counts["google"]),
        check("chi2", printed["test"]["value"], float(chi.statistic), 3),
        check("chi2_df", printed["test"]["df"], len(counts) - 1),
        check("p_value", printed["p_value"], float(chi.pvalue)),
    ] + corpus_checks(audit)
    notes = (
        "FAILED REPRODUCTION OF THE PRINTED ARM LABELS. Main PDF p. 8 labels "
        "50.6% (756 choices) as LLM and 24.6% (367 choices) as web search. The "
        f"posted choice column instead has {counts['gpt']} gpt choices "
        f"({100 * counts['gpt'] / n:.12f}%), {counts['google']} google choices "
        f"({100 * counts['google'] / n:.12f}%), and {counts['similar']} ties. The "
        "compare and 0.key/1.key columns confirm the mapping. The paper's chi-square "
        "statistic reproduces because exchanging the arm labels leaves it unchanged. "
        "The published labels are not silently reversed. " + corpus_note(audit) +
        "No participant-level effect or SE is computed; all computed fields are null."
    )
    return result(estimate, checks, notes)


def skip_missing_words(estimate, datasets):
    tr, cr = contrast_rows(estimate, datasets)
    mt = mean([len(r["advice"].split()) for r in tr])
    mc = mean([len(r["advice"].split()) for r in cr])
    printed = estimate["stats"]
    reason = (
        "LIWC 2022 is the specified scorer (main PDF p. 4), but this study's CSV "
        "contains no word-count variable and the original LIWC scoring output or "
        "exact tokenizer is not supplied. Simple whitespace counts are only a "
        f"diagnostic: treatment mean {mt:.12f}, control mean {mc:.12f}, versus "
        f"printed {printed['treatment_mean']} and {printed['control_mean']}. They "
        "do not reproduce the printed means, so an approximate tokenizer is not "
        f"substituted. Posted rows: {len(tr)} treatment and {len(cr)} control."
    )
    if estimate["study_id"] == "S6":
        reason += (
            " The file additionally has 1,999 people versus the reported final "
            "sample of 1,976; no attention-check/exclusion indicator identifies "
            "the required rows."
        )
    return {"slug": estimate["slug"], "reason": reason}


def skip_diversity(estimate, datasets, distance_diagnostics):
    tr, cr = contrast_rows(estimate, datasets)
    cosine = estimate["measure"] == "embedding_similarity"
    column = "cosine_similarity" if cosine else "edit_distance"
    mt, mc = mean(numbers(tr, column)), mean(numbers(cr, column))
    prefix = (
        "Set-level diversity has no independent participant outcome. "
        f"The saved {column} column averages to {mt:.12f} in treatment and "
        f"{mc:.12f} in control, with {len(tr)} and {len(cr)} posted writers. "
    )
    if cosine:
        reason = (
            prefix + "The paper uses separate condition-specific LDA models followed "
            "by PCA, not a named neural embedding model (main PDF p. 4). The trained "
            "models, topic counts, preprocessing, fitting seeds, and PCA settings "
            "or topic vectors are not supplied in the deposit. Averaging precomputed "
            "scalar scores does not reproduce that procedure from the same texts. "
            "Skipped under rule 5; the saved scores are not treated as independent "
            "participant values for SDs or HC2."
        )
    else:
        sid = estimate["study_id"]
        details = []
        for label, rows in (("treatment", tr), ("control", cr)):
            arm = rows[0]["condition"]
            key = (sid, arm)
            if key not in distance_diagnostics:
                texts = [r["advice"] for r in rows]
                # All other texts in the same arm are included in this exact
                # first-row diagnostic. No model or text-normalization guess.
                raw = sum(Levenshtein.distance(texts[0], text) for text in texts[1:]) / (len(texts) - 1)
                stored = float(rows[0]["edit_distance"])
                distance_diagnostics[key] = (raw, stored)
            raw, stored = distance_diagnostics[key]
            details.append(f"{label}: raw {raw:.12f}, saved {stored:.12f}")
        reason = (
            prefix + "The paper states average pairwise Levenshtein distance, but "
            "does not supply its exact text preprocessing or pairwise inputs. Exact "
            "character-level Levenshtein distance on the deposited advice does not "
            "recover even the first saved row average within either arm (" +
            "; ".join(details) + "). Thus the saved scalar scores cannot establish "
            "an exact reproduction of the set measure from the same processed "
            "texts. Skipped under rule 5; no participant SD or SE is constructed "
            "from these mutually dependent row averages."
        )
    if estimate["study_id"] == "S6":
        reason += (
            " The 1,999-row file also differs from the stated analyzed sample of "
            "1,976 and contains no exclusion/attention-check flags; the paper's "
            "analysis subset cannot be identified."
        )
    return {"slug": estimate["slug"], "reason": reason}


def main():
    with EXTRACTION.open(encoding="utf-8") as fh:
        extraction = json.load(fh)
    with MANIFEST.open(encoding="utf-8") as fh:
        manifest = json.load(fh)["deposits"]["osf-jx2es"]["files"]
    datasets = {}
    for study, path in DATA_PATHS.items():
        relative = path.relative_to(DATA_ROOT).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == manifest[relative]["sha256"], f"Hash mismatch: {path}"
        with path.open(encoding="utf-8-sig", newline="") as fh:
            datasets[study] = list(csv.DictReader(fh))
        assert datasets[study]
        assert not any(None in row for row in datasets[study]), f"Malformed CSV: {path}"
        if study != "ratings":
            assert all(r["advice"].strip() for r in datasets[study])
            assert set(r["condition"] for r in datasets[study]) == set(ARM_MAP[study].values())
            assert len({tuple(r.values()) for r in datasets[study]}) == len(datasets[study])

    studies = {s["study_id"]: s for s in extraction["studies"]}
    audit = audit_rating_corpus(datasets)
    results, skipped = [], []
    distance_diagnostics = {}
    for estimate in extraction["estimates"]:
        assert estimate["within_person"] is None
        if estimate["construct"] == "diversity":
            skipped.append(skip_diversity(estimate, datasets, distance_diagnostics))
        elif estimate["measure"] == "length" and estimate["study_id"] != "S5":
            skipped.append(skip_missing_words(estimate, datasets))
        elif "relative_helpfulness_choice" in estimate["slug"]:
            results.append(choice_result(estimate, datasets, audit))
        elif estimate["measure"] == "human_raters":
            results.append(rating_result(estimate, datasets, audit))
        else:
            assert estimate["measure"] in ("length", "text_features")
            results.append(direct_score_result(estimate, datasets, studies))

    result_slugs = {r["slug"] for r in results}
    skipped_slugs = {r["slug"] for r in skipped}
    assert not result_slugs & skipped_slugs
    assert result_slugs | skipped_slugs == {e["slug"] for e in extraction["estimates"]}
    assert len(result_slugs) == len(results) and len(skipped_slugs) == len(skipped)
    for r in results:
        passed = all(c["match"] for c in r["reproduced"])
        assert passed == (r["computed"]["difference"] is not None)
        if not passed:
            assert all(value is None for value in r["computed"].values())

    obj = {
        "cid": "c489", "analyst": "B", "script": SCRIPT.as_posix(),
        "data_files": [path.as_posix() for path in DATA_PATHS.values()],
        "results": results, "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
        fh.write("\n")
    with OUTPUT.open(encoding="utf-8") as fh:
        confirmed = json.load(fh)
    assert confirmed == obj
    print(json.dumps({
        "cid": "c489", "n_results": len(results),
        "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
