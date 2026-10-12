"""Independent analyst B reproduction and participant-level analysis for c096.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c096/B.py

The complete 57,080-character paper markdown, including methods, references,
and end matter, was read in consecutive chunks. There is no appendix in it.
Printed quantities and design details were checked against PDF pages 2-7 and 9;
Tables 1 and 2 were also extracted with PyMuPDF find_tables(). The deposited
SPSS syntax PDF was read only as text, never executed. No other analyst's
script or results are inputs. This script writes only the adjacent B.json.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pymupdf
import pyreadstat
from scipy import stats
import statsmodels.api as sm


ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path("D:/projects/ai-skill-atlas/creativity-data/osf-3jqga")
SCRIPT = ROOT / "analysis/c096/B.py"
OUTPUT = ROOT / "analysis/c096/B.json"
EXTRACTION = ROOT / "extraction/c096.json"
MANIFEST = DEPOSIT.parent / "manifest.json"
SYNTAX = DEPOSIT / "Syntax_NHB_CreativeCollabAI.pdf"
STUDY_FILES = {
    "S1": DEPOSIT / "CreativeCollabAI_Study1.sav",
    "S2": DEPOSIT / "CreativeCollabAI_Study2.sav",
}
ARM_CODES = {
    "Human condition": 1,
    "Human-AI condition (editor)": 2,
    "Co-creator human-AI condition": 3,
}
EXPECTED_SLUGS = {
    "s1_expert_creativity_editor_vs_human",
    "s2_expert_creativity_editor_vs_human",
    "s2_expert_creativity_cocreator_vs_human",
    "s2_expert_creativity_cocreator_vs_editor",
}


def verify_deposit():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest["deposits"]["osf-3jqga"]["files"]
    for path in [*STUDY_FILES.values(), SYNTAX]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entries[path.name]["sha256"], path.name
    # Extracting text does not execute any of the authors' SPSS commands.
    with pymupdf.open(SYNTAX) as doc:
        syntax_text = "\n".join(page.get_text() for page in doc)
    assert "UNIANOVA Expert_creativity BY condition_coded" in syntax_text
    assert "UNIANOVA expert_creativity BY condition" in syntax_text
    assert "/POSTHOC=condition_coded(LSD)" in syntax_text
    assert "/POSTHOC=condition(LSD)" in syntax_text


def load_study(study_id):
    data, metadata = pyreadstat.read_sav(str(STUDY_FILES[study_id]))
    arm_column = "condition_coded" if study_id == "S1" else "condition"
    outcome = "Expert_creativity" if study_id == "S1" else "expert_creativity"
    # S1 is numeric; S2 stores the condition as the strings '1', '2', '3'.
    numeric_arm = data[arm_column].astype(float)
    assert np.isfinite(numeric_arm).all()
    assert (numeric_arm == np.floor(numeric_arm)).all()
    data = data.copy()
    data["_arm"] = numeric_arm.astype(int)
    assert set(data["_arm"]) == {1, 2, 3}
    assert data[outcome].notna().all()
    assert np.isfinite(data[outcome]).all()
    assert data[outcome].between(1, 40).all()
    assert not data.duplicated().any()
    assert not data["poem"].duplicated().any()
    assert data["poem"].str.strip().ne("").all()

    # Each human row is one person with one poem and one stored expert score.
    # S1 code 3 consists of autonomous AI benchmark poems, not participants.
    human_mask = data["_arm"].isin([1, 2]) if study_id == "S1" else np.ones(len(data), dtype=bool)
    people = data.loc[human_mask].copy()
    attention = people["AC"].astype(str).str.strip().str.strip("'\"").str.strip().str.casefold()
    assert attention.eq("study").all()
    assert people["age"].notna().all()
    if study_id == "S1":
        assert data.loc[~human_mask, "age"].isna().all()
        assert data.loc[~human_mask, "self_creativity"].isna().all()
    else:
        # Independently anchor the mapping with indicator coding on PDF p. 7.
        assert data.loc[data["_arm"].eq(2), "dummy_1"].eq(0).all()
        assert data.loc[data["_arm"].eq(3), "dummy_1"].eq(1).all()
        assert data.loc[data["_arm"].eq(3), "dummy_2"].eq(0).all()
        assert data.loc[data["_arm"].eq(1), "dummy_2"].eq(1).all()
    return {"data": data, "people": people, "outcome": outcome, "arm_column": arm_column}


def paper_anova(study):
    """Reproduce the authors' three-arm ANOVA and its LSD error term."""
    data, outcome = study["data"], study["outcome"]
    groups = [group[outcome].to_numpy(dtype=float) for _, group in data.groupby("_arm")]
    df_error = sum(len(group) for group in groups) - len(groups)
    sse = sum(float(np.sum((group - group.mean()) ** 2)) for group in groups)
    anova = stats.f_oneway(*groups)
    return {"mse": sse / df_error, "df_error": df_error, "f": float(anova.statistic)}


def decimal_round(value, places):
    # Remove only binary floating-point noise before comparing printed decimals.
    # In particular, S1 human mean 18.225 rounds half-up to the printed 18.23.
    decimal_value = Decimal(str(round(float(value), 12)))
    return decimal_value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def reproduction_check(statistic, printed, computed, places=None):
    if isinstance(printed, str) and printed.startswith("<"):
        match = computed < float(printed[1:])
    elif places is None:
        match = computed == printed
    else:
        match = decimal_round(computed, places) == Decimal(str(printed))
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(match),
    }


def reproduce(estimate, study, anova):
    people, outcome = study["people"], study["outcome"]
    treatment_code = ARM_CODES[estimate["treatment_arm"]]
    control_code = ARM_CODES[estimate["control_arm"]]
    treatment = people.loc[people["_arm"].eq(treatment_code), outcome].to_numpy(dtype=float)
    control = people.loc[people["_arm"].eq(control_code), outcome].to_numpy(dtype=float)
    assert len(treatment) > 1 and len(control) > 1
    checks = []
    for arm, values in [("treatment", treatment), ("control", control)]:
        checks.append(reproduction_check("n_" + arm, estimate["n_" + arm], len(values)))
        checks.append(reproduction_check(arm + "_mean", estimate["stats"][arm + "_mean"], float(values.mean()), 2))
        checks.append(reproduction_check(arm + "_sd", estimate["stats"][arm + "_sd"], float(values.std(ddof=1)), 2))
    if estimate["n_total"] is not None:
        checks.append(reproduction_check("n_total", estimate["n_total"], len(treatment) + len(control)))

    # Reproduce the printed p-value using LSD and all three arms' pooled MSE,
    # as specified by the deposited syntax. This is not the requested HC2 SE.
    lsd_se = math.sqrt(anova["mse"] * (1 / len(treatment) + 1 / len(control)))
    t_value = (float(treatment.mean()) - float(control.mean())) / lsd_se
    p_value = float(2 * stats.t.sf(abs(t_value), anova["df_error"]))
    checks.append(reproduction_check("p_value", estimate["stats"]["p_value"], p_value, 3))
    return treatment, control, checks


def participant_contrast(treatment, control):
    """Fit OLS at the unit of individual randomization with HC2 covariance."""
    outcome = np.concatenate([control, treatment])
    arm_indicator = np.concatenate([np.zeros(len(control)), np.ones(len(treatment))])
    design = np.column_stack([np.ones(len(outcome)), arm_indicator])
    fit = sm.OLS(outcome, design).fit(cov_type="HC2")
    treatment_sd = float(treatment.std(ddof=1))
    control_sd = float(control.std(ddof=1))
    difference = float(treatment.mean() - control.mean())
    difference_se = float(fit.bse[1])
    # For an intercept and a binary arm indicator only, HC2 also equals this
    # independent-groups sample-variance expression; verify the fitted result.
    check_se = math.sqrt(treatment_sd ** 2 / len(treatment) + control_sd ** 2 / len(control))
    assert math.isclose(float(fit.params[1]), difference, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(difference_se, check_se, rel_tol=1e-12, abs_tol=1e-12)
    return {
        "n_treatment": len(treatment),
        "n_control": len(control),
        "treatment_mean": float(treatment.mean()),
        "treatment_sd": treatment_sd,
        "control_mean": float(control.mean()),
        "control_sd": control_sd,
        "difference": difference,
        "difference_se": difference_se,
        "se_type": "HC2",
        "n_clusters": None,
    }


def provenance_notes(estimate, study, anova):
    study_id = estimate["study_id"]
    treatment_code = ARM_CODES[estimate["treatment_arm"]]
    control_code = ARM_CODES[estimate["control_arm"]]
    notes = [
        f"Input: {STUDY_FILES[study_id].as_posix()}; outcome {study['outcome']}; "
        f"arm variable {study['arm_column']}, treatment={treatment_code} "
        f"({estimate['treatment_arm']}), control={control_code} ({estimate['control_arm']}).",
        "The deposited file has one row and one already aggregated expert score per poem; "
        "the paper specifies one poem per person. Use the stored poem score as the "
        "participant-level outcome. Individual poets' ratings and participant IDs are not "
        "included, so the upstream rater aggregation cannot be independently reconstructed. "
        "There are no missing outcome scores, duplicated rows, or duplicated poem texts; "
        "poem text was checked for uniqueness, not used to exclude observations.",
        "All retained human rows pass the attention check after normalizing capitalization "
        "and surrounding quotes. No additional exclusions, imputation, outcome rescaling, "
        "or covariate adjustment were applied.",
        "Individual between-person randomization (PDF pp. 2, 4-5, 9); one assigned condition "
        "per person, so round='all' and no first_round result is applicable. SDs use n-1. "
        "Difference is treatment minus control in the original 1-40 creativity units. "
        "OLS includes an intercept and the binary treatment indicator for these two arms "
        "only; HC2 SE is verified against sqrt(s_treatment^2/n_treatment + "
        "s_control^2/n_control). There are no randomized clusters.",
        "Reproduction compares counts exactly, means/SDs to two decimal places and exact "
        "p-values to three decimal places, using decimal half-up rounding after removing "
        "binary floating-point noise. The printed p-values are reproduced with the "
        "three-arm ANOVA residual variance and two-sided LSD t-tests, following "
        "Syntax_NHB_CreativeCollabAI.pdf (read only as text). The new difference_se "
        "uses the requested pair-specific HC2 covariance. All three deposited files "
        "were SHA-256 verified against the supplied manifest.",
    ]
    if study_id == "S1":
        notes.extend([
            "Table 1 and the results on PDF p. 4 provide the matching means/SDs and "
            "p<0.001; PDF pp. 2 and 4 provide 48 people in each human arm and 96 total. "
            "condition_coded=1 is human, 2 is editor, and 3 comprises 50 AI-only poems. "
            "The benchmark has no human demographics and is omitted from participant "
            "counts and the HC2 contrast, but retained in the original LSD error term. "
            "The human-arm mapping also reproduces the self-rating means in Table 1.",
            "The deposited file contains 96 human records and 50 benchmark poems, "
            "consistent with the paper's analyzed sample. It contains no excluded "
            "attention-check failures. The reported 101 recruits minus six exclusions "
            "does not equal 96; recruitment counts and the original excluded records "
            "cannot be recovered from this deposit.",
            f"Separate diagnostic: the non-extracted three-arm omnibus is F(2, "
            f"{anova['df_error']})={anova['f']:.12f}, whereas PDF p. 4 prints "
            "F(2,145)=63.48. That omnibus does not reproduce. The extracted two-arm "
            "means, SDs, people counts and pairwise p-value do reproduce, and are "
            "the reproduction gate for this result.",
        ])
    else:
        data = study["data"]
        human_sd = float(data.loc[data["_arm"].eq(1), study["outcome"]].std(ddof=1))
        human_self_sd = float(data.loc[data["_arm"].eq(1), "creativity_self"].std(ddof=1))
        notes.extend([
            "Table 2 (PDF p. 7) supplies the matching creativity means and SDs; "
            "PDF pp. 4-5 supply counts (human=51, editor=50, co-creator=51; total=152). "
            "All 152 deposited rows are analyzed. The stored dummy_1 and dummy_2 "
            "variables agree with the arm mapping described on PDF p. 7: "
            "dummy_1 is 0 for editor and 1 for co-creator; dummy_2 is 0 for "
            "co-creator and 1 for human.",
            f"The human expert-score SD is {human_sd:.12f}, reproducing Table 2's 4.98. "
            f"The conflicting 9.24 on PDF p. 6 instead matches the human self-rating "
            f"SD ({human_self_sd:.12f}); it is not the expert-score SD. "
            f"The three-arm omnibus reproduces F(2,{anova['df_error']})="
            f"{anova['f']:.12f}, printed as 5.77.",
        ])
        if estimate["slug"] == "s2_expert_creativity_cocreator_vs_human":
            notes.append(
                "The explicitly identified co-creator versus human LSD p-value on "
                "PDF p. 6 reproduces as 0.278 at printed precision. The separate "
                "0.280 in the descriptive parenthesis has no specified comparator "
                "and does not match this contrast; the reconciled extraction uses 0.278."
            )
    return " ".join(notes)


def main():
    verify_deposit()
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    assert extraction["cid"] == "c096"
    assert {estimate["slug"] for estimate in extraction["estimates"]} == EXPECTED_SLUGS
    studies = {study_id: load_study(study_id) for study_id in STUDY_FILES}
    anovas = {study_id: paper_anova(study) for study_id, study in studies.items()}
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        assert estimate["within_person"] is None
        study_id = estimate["study_id"]
        study, anova = studies[study_id], anovas[study_id]
        treatment, control, checks = reproduce(estimate, study, anova)
        notes = provenance_notes(estimate, study, anova)
        # Gate all requested new statistics on successful reproduction first.
        if all(check["match"] for check in checks):
            computed = participant_contrast(treatment, control)
        else:
            computed = None
            failures = "; ".join(
                f"{check['statistic']}: printed {check['printed']}, computed {check['computed']}"
                for check in checks if not check["match"]
            )
            notes += " Reproduction failed; no new contrast was computed. " + failures
            skipped.append({"slug": estimate["slug"], "reason": failures})
        results.append({
            "slug": estimate["slug"],
            "round": "all",
            "reproduced": checks,
            "computed": computed,
            "notes": notes,
        })
    payload = {
        "cid": "c096",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": [path.as_posix() for path in [*STUDY_FILES.values(), SYNTAX]],
        "results": results,
        "skipped": skipped,
    }
    # Check JSON finiteness before opening the only output file.
    json.dumps(payload, ensure_ascii=False, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == payload
    print(json.dumps({
        "cid": "c096",
        "n_results": len(results),
        "n_reproduced": sum(all(check["match"] for check in row["reproduced"]) for row in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
