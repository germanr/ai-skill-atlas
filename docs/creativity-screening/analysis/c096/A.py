"""Reproduce c096's extracted arm summaries, then estimate participant contrasts.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c096/A.py
Only A.json is written. Deposited syntax is read as PDF text, never executed.
Reproduction targets the arm means, sample SDs, and people counts in the
reconciled extraction, as permitted by the analysis brief. Paper LSD p-values
and omnibus tests are not the requested two-arm HC2 analysis.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pyreadstat
import pymupdf
import statsmodels.api as sm


ROOT = Path(r"C:\Dropbox\Admin\website\ai-skill-atlas\docs\creativity-screening")
DEPOSIT = Path(r"D:\projects\ai-skill-atlas\creativity-data\osf-3jqga")
MANIFEST = Path(r"D:\projects\ai-skill-atlas\creativity-data\manifest.json")
SCRIPT = ROOT / "analysis/c096/A.py"
OUTPUT = ROOT / "analysis/c096/A.json"
SYNTAX = DEPOSIT / "Syntax_NHB_CreativeCollabAI.pdf"
SAV = {
    "S1": DEPOSIT / "CreativeCollabAI_Study1.sav",
    "S2": DEPOSIT / "CreativeCollabAI_Study2.sav",
}
VARIABLES = {
    "S1": ("condition_coded", "Expert_creativity"),
    "S2": ("condition", "expert_creativity"),
}
ARM_CODES = {
    "Human condition": "1",
    "Human-AI condition (editor)": "2",
    "Co-creator human-AI condition": "3",
}


def load_json(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def exact_decimal_mean(values):
    """Avoid a binary floating-point rounding error at S1's 18.225 mean."""
    total = sum((Decimal(str(float(v))) for v in values), Decimal(0))
    return float(total / Decimal(len(values)))


def summarize(values):
    values = np.asarray(values, dtype=float)
    assert len(values) > 1 and np.isfinite(values).all()
    return {
        "n": int(len(values)),
        "mean": exact_decimal_mean(values),
        "sd": float(np.std(values, ddof=1)),
    }


def compare(statistic, printed, computed):
    if statistic.startswith("n_"):
        match = computed == printed
    else:
        # Both tables print every expert mean and SD to two decimals,
        # including 14.70, whose trailing zero is lost in extraction JSON.
        rounded = Decimal(str(computed)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        match = rounded == Decimal(str(printed))
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(match),
    }


def reproduction_checks(estimate, treatment, control):
    checks = []
    for role, summary in [("treatment", treatment), ("control", control)]:
        key = "n_" + role
        checks.append(compare(key, estimate[key], summary["n"]))
        for stat in ["mean", "sd"]:
            key = role + "_" + stat
            checks.append(compare(key, estimate["stats"][key], summary[stat]))
    if estimate["n_total"] is not None:
        checks.append(compare(
            "n_total", estimate["n_total"], treatment["n"] + control["n"]
        ))
    return checks


def hc2_contrast(treatment_values, control_values, treatment, control):
    """Unadjusted OLS on an intercept and a treatment indicator, with HC2."""
    y = np.concatenate([control_values, treatment_values])
    indicator = np.concatenate([
        np.zeros(control["n"]), np.ones(treatment["n"])
    ])
    x = np.column_stack([np.ones(len(y)), indicator])
    fit = sm.OLS(y, x, missing="raise").fit(cov_type="HC2")
    difference = treatment["mean"] - control["mean"]
    se = float(fit.bse[1])
    # In this saturated two-group regression, HC2 equals this closed form.
    independent_se = np.sqrt(
        treatment["sd"] ** 2 / treatment["n"]
        + control["sd"] ** 2 / control["n"]
    )
    assert np.isclose(float(fit.params[1]), difference, rtol=0, atol=1e-12)
    assert np.isclose(se, independent_se, rtol=0, atol=1e-12)
    assert int(fit.nobs) == treatment["n"] + control["n"]
    return {
        "n_treatment": treatment["n"],
        "n_control": control["n"],
        "treatment_mean": treatment["mean"],
        "treatment_sd": treatment["sd"],
        "control_mean": control["mean"],
        "control_sd": control["sd"],
        "difference": float(difference),
        "difference_se": se,
        "se_type": "HC2",
        "n_clusters": None,
    }


def main():
    extraction = load_json(ROOT / "extraction/c096.json")
    manifest = load_json(MANIFEST)["deposits"]["osf-3jqga"]["files"]
    data_files = [SAV["S1"], SAV["S2"], SYNTAX]
    for path in data_files:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == manifest[path.name]["sha256"], str(path)

    # This is text inspection of authors' syntax, not execution of that syntax.
    with pymupdf.open(SYNTAX) as doc:
        syntax_text = "\n".join(page.get_text() for page in doc)
    assert "UNIANOVA Expert_creativity BY condition_coded" in syntax_text
    assert "UNIANOVA expert_creativity BY condition" in syntax_text
    assert "POSTHOC=condition_coded(LSD)" in syntax_text
    assert "POSTHOC=condition(LSD)" in syntax_text

    datasets = {}
    for study_id, path in SAV.items():
        df, metadata = pyreadstat.read_sav(str(path), apply_value_formats=False)
        condition, outcome = VARIABLES[study_id]
        assert not metadata.missing_ranges
        assert not metadata.missing_user_values
        if study_id == "S1":
            df[condition] = df[condition].astype(int).astype(str)
            expected_counts = {"1": 48, "2": 48, "3": 50}
            human = df[df[condition].isin(["1", "2"])]
            assert df.loc[df[condition] == "3", "age"].isna().all()
        else:
            df[condition] = df[condition].str.strip()
            expected_counts = {"1": 51, "2": 50, "3": 51}
            human = df
            # Paper p. 7 explicitly defines these mediation dummy variables.
            for code, dummy1, dummy2 in [("1", None, 1), ("2", 0, None), ("3", 1, 0)]:
                group = df[df[condition] == code]
                for column, value in [("dummy_1", dummy1), ("dummy_2", dummy2)]:
                    assert (group[column].isna().all() if value is None
                            else group[column].eq(value).all())
        assert df[condition].value_counts().to_dict() == expected_counts
        assert not df[outcome].isna().any()
        assert df[outcome].between(1, 40).all()
        assert df["poem"].str.strip().ne("").all()
        assert not df["poem"].duplicated().any()
        assert human["age"].notna().all()
        # Check spelling/case/punctuation only; do not impose new exclusions.
        answers = human["AC"].str.strip().str.strip("\"'").str.casefold()
        assert answers.eq("study").all()
        datasets[study_id] = df

    common_notes = (
        "Reproduction criteria are the extracted table arm means and sample SDs "
        "(two decimal places, decimal half-up rounding) and printed participant "
        "counts (exact). All must match before the contrast is estimated. "
        "The full 11-page markdown, including Methods, references and end matter, "
        "was read; it contains no appendix. Cited PDF text and Tables 1 and 2 "
        "were checked with pymupdf, including find_tables(). The two-page "
        "deposited syntax was read as text only and identifies the expert outcome "
        "variables. Each human row represents one participant's sole poem. "
        "The SAV files provide one expert-creativity score per poem, without "
        "individual-rater scores or participant IDs; the underlying aggregation "
        "over raters cannot be independently reconstructed. The supplied score "
        "is the participant-level outcome, and there are no repeated outputs to "
        "average. SDs use n - 1. Difference is the treatment mean minus the "
        "control mean in the original 1-40 creativity-score units. Individual "
        "randomization is reported on PDF p. 9. OLS uses only the two contrasted "
        "arms, with an intercept and treatment indicator; HC2 standard errors "
        "are verified against sqrt(s_t^2/n_t + s_c^2/n_c). The paper's original "
        "LSD p-values use a three-condition ANOVA error term and are not the "
        "reproduction target or the source of the new standard error. Both "
        "studies are between-person designs, so round is all and no first_round "
        "or paired result applies. No diversity outcome occurs in the extraction."
    )
    study_notes = {
        "S1": (
            "Study 1: CreativeCollabAI_Study1.sav, condition_coded 1 = Human, "
            "2 = Human-AI editor, 3 = AI-only benchmark; outcome = "
            "Expert_creativity. Mapping follows the paper's condition ordering "
            "and reproduces Table 1 (PDF p. 4) and counts (PDF pp. 2, 4). "
            "The file contains 146 rows: 48 human, 48 editor and 50 AI-only "
            "poems. Exclude condition 3 from the participant contrast. Retain "
            "all 96 human rows, whose AC entries are study or Study; the single "
            "missing user_time value is unrelated to this outcome. The deposit "
            "already contains the reported analyzed sample; there are no "
            "additional attention-check exclusions to apply. The inconsistent "
            "printed recruitment arithmetic (101 recruited, six excluded, "
            "96 analyzed) and omnibus error df of 145 cannot be resolved from "
            "the posted participant sample. The exact human mean is 18.225, "
            "which rounds half-up to the printed 18.23. "
        ),
        "S2": (
            "Study 2: CreativeCollabAI_Study2.sav, string condition 1 = Human, "
            "2 = Human-AI editor, 3 = Co-creator human-AI; outcome = "
            "expert_creativity. Mapping is independently corroborated by "
            "dummy_1 and dummy_2 and the paper's explicit dummy definitions "
            "(PDF p. 7). All 152 rows are retained (51 human, 50 editor, "
            "51 co-creator), matching counts on PDF pp. 4-5. No attention-check "
            "exclusions were reported; study, Study and the quoted 'study' "
            "response are retained. Each contrast selects only its named two "
            "arms. Arm summaries reproduce Table 2 (PDF p. 7). The data support "
            "the expert human SD of 4.98 in that table; the conflicting prose "
            "value 9.24 (PDF p. 6) belongs to self-reported creativity. The "
            "paper also prints both 0.278 and 0.280 around the co-creator/human "
            "comparison; neither is used to derive the requested HC2 SE. "
            "The three Study 2 results share participants and are not "
            "independent estimates. "
        ),
    }

    results = []
    skipped = []
    for estimate in extraction["estimates"]:
        study_id = estimate["study_id"]
        assert estimate["within_person"] is None
        assert estimate["construct"] == "overall_creativity"
        condition, outcome = VARIABLES[study_id]
        df = datasets[study_id]
        treatment_code = ARM_CODES[estimate["treatment_arm"]]
        control_code = ARM_CODES[estimate["control_arm"]]
        if study_id == "S1":
            assert {treatment_code, control_code} == {"1", "2"}
        treatment_values = df.loc[df[condition].eq(treatment_code), outcome].to_numpy()
        control_values = df.loc[df[condition].eq(control_code), outcome].to_numpy()
        treatment = summarize(treatment_values)
        control = summarize(control_values)
        reproduced = reproduction_checks(estimate, treatment, control)
        notes = (
            "Treatment: " + estimate["treatment_arm"] + "; control: "
            + estimate["control_arm"] + ". " + study_notes[study_id] + common_notes
        )
        failed = [x for x in reproduced if not x["match"]]
        if failed:
            reason = "Reproduction failed: " + json.dumps(failed, ensure_ascii=True)
            computed = None
            notes += " " + reason + ". No contrast was computed."
            skipped.append({"slug": estimate["slug"], "reason": reason})
        else:
            computed = hc2_contrast(
                treatment_values, control_values, treatment, control
            )
        results.append({
            "slug": estimate["slug"],
            "round": "all",
            "reproduced": reproduced,
            "computed": computed,
            "notes": notes,
        })

    result = {
        "cid": "c096",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": [path.as_posix() for path in data_files],
        "results": results,
        "skipped": skipped,
    }
    # Check JSON serializability and disallow NaN before opening the output.
    json.dumps(result, ensure_ascii=False, allow_nan=False)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    parsed = load_json(OUTPUT)
    assert parsed == result
    print(json.dumps({
        "cid": "c096",
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            r["computed"] is not None and all(v["match"] for v in r["reproduced"])
            for r in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }))


if __name__ == "__main__":
    main()
