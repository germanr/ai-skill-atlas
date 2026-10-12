"""Independent participant-level reanalysis of c194 (analyst A).

Run with python -I -B A.py. The only file this script writes is A.json.
Deposited programs are read as text and are never executed or imported.
"""

import sys

sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
import statsmodels.api as sm


ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA_ROOT = Path("D:/projects/ai-skill-atlas/creativity-data")
SCRIPT = ROOT / "analysis/c194/A.py"
OUTPUT = ROOT / "analysis/c194/A.json"
EXTRACTION = ROOT / "extraction/c194.json"
MANIFEST = DATA_ROOT / "manifest.json"
FIG = DATA_ROOT / "figshare-32132980"
MEN = DATA_ROOT / "mendeley-t93pf5r6fp-v2"
FIG_DTA = FIG / "Final Dataset Human AI creativity, ACMPS 2026.dta"
MEN_DTA = MEN / "Final Dataset Human AI creativity, ACMPS 2026 - Sept 2026.dta"
FIG_DO = FIG / "Analysis Human AI creativity, ACMPS 2026.do"
MEN_DO = MEN / "Analysis Human AI creativity, ACMPS 2026 - Sept 2026.do"
README = FIG / "README.txt"

ARM_CODES = {
    "T": "T_NoAI",
    "PR": "PR_NoAI",
    "L": "LOT_NoAI",
    "T&AI": "T_AI",
    "PR&AI": "PR_AI",
    "L&AI": "LOT_AI",
}
AI_ARMS = {"T_AI", "PR_AI", "LOT_AI"}
OUTCOMES = {
    "s1_creativity_": "participant_creativity",
    "s1_characters_": "n_characters",
    "s1_dat_": "dat_score",
}
COMPUTED_FIELDS = (
    "n_treatment", "n_control", "treatment_mean", "treatment_sd",
    "control_mean", "control_sd", "difference", "difference_se",
    "se_type", "n_clusters",
)


def check(statistic, printed, computed, decimals=None):
    """Compare at the precision printed in the source tables (three decimals)."""
    if isinstance(computed, np.generic):
        computed = computed.item()
    if isinstance(printed, str) and printed.startswith("<"):
        match = float(computed) < float(printed[1:])
    elif decimals is None:
        match = computed == printed
    else:
        match = format(float(computed), f".{decimals}f") == format(
            float(printed), f".{decimals}f"
        )
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(match),
    }


def arm_summary(sample, outcome):
    t = sample.loc[sample["AI"].eq(1), outcome].to_numpy(dtype=np.float64)
    c = sample.loc[sample["AI"].eq(0), outcome].to_numpy(dtype=np.float64)
    return {
        "n_treatment": int(t.size),
        "n_control": int(c.size),
        "treatment_mean": float(t.mean()),
        "treatment_sd": float(t.std(ddof=1)),
        "control_mean": float(c.mean()),
        "control_sd": float(c.std(ddof=1)),
    }


def reproduce(estimate, sample, outcome, combined):
    """Reproduce the paper before calculating the requested new contrast."""
    checks = []
    observed = arm_summary(sample, outcome)
    for field in ("n_treatment", "n_control"):
        checks.append(check(field, estimate[field], observed[field]))
    if estimate["n_total"] is not None:
        checks.append(check("n_total", estimate["n_total"], int(len(sample))))

    if combined:
        # Table 5: Stata regress ..., robust uses HC1, not HC2 or clustering.
        x = pd.DataFrame({
            "constant": np.ones(len(sample)),
            "AI": sample["AI"].to_numpy(dtype=np.float64),
            "tournament": sample["treatment"].isin(
                ["T_AI", "T_NoAI"]
            ).to_numpy(dtype=np.float64),
            "piece_rate": sample["treatment"].isin(
                ["PR_AI", "PR_NoAI"]
            ).to_numpy(dtype=np.float64),
        })
        fit = sm.OLS(sample[outcome].to_numpy(dtype=np.float64), x).fit(
            cov_type="HC1", use_t=True
        )
        printed = estimate["stats"]["regression"]
        checks.append(check("regression.coef", printed["coef"], fit.params["AI"], 3))
        checks.append(check("regression.se", printed["se"], fit.bse["AI"], 3))
        if estimate["stats"]["p_value"] is not None:
            checks.append(check(
                "p_value", estimate["stats"]["p_value"], fit.pvalues["AI"]
            ))
    else:
        # Table 1 supplies unadjusted participant means and sample SDs.
        for field in ("treatment_mean", "treatment_sd", "control_mean", "control_sd"):
            checks.append(check(field, estimate["stats"][field], observed[field], 3))
    return checks


def calculate(sample, outcome):
    """Participant-weighted OLS, with covariance clustered by recorded session."""
    values = arm_summary(sample, outcome)
    x = np.column_stack((np.ones(len(sample)), sample["AI"].to_numpy(dtype=np.float64)))
    y = sample[outcome].to_numpy(dtype=np.float64)
    clusters = sample["session"].to_numpy()
    fit = sm.OLS(y, x).fit(
        cov_type="cluster",
        cov_kwds={"groups": clusters, "use_correction": True, "df_correction": True},
        use_t=True,
    )
    difference = values["treatment_mean"] - values["control_mean"]
    assert np.isclose(fit.params[1], difference, rtol=1e-11, atol=1e-10)
    values.update({
        "difference": float(difference),
        "difference_se": float(fit.bse[1]),
        "se_type": "cluster",
        "n_clusters": int(sample["session"].nunique()),
    })
    return values


def notes_for(estimate, sample, outcome, combined):
    tclusters = int(sample.loc[sample["AI"].eq(1), "session"].nunique())
    cclusters = int(sample.loc[sample["AI"].eq(0), "session"].nunique())
    notes = [
        "Sources: saved working-paper PDF pp. 14, 16, and 23 (printed pp. 11, 13, "
        "and 20), Tables 1, 2, and 5; read the complete 119358-character markdown, "
        "including Appendices A-C. Numeric cells checked against PDF page text. "
        "All table means, SDs, coefficients, and SEs are compared at three decimals; "
        "counts are compared exactly.",
        "The Figshare and Mendeley deposits contain the same 360 participants and "
        "identical values in all 57 shared columns, verified after aligning id_prog; "
        "the deposits are not pooled. Both DTA files match their manifest SHA-256 "
        "hashes. id_prog and id_code are complete and unique. All deposited "
        "participants have all three outcomes and are retained, including those "
        "assigned AI who made no queries. No additional exclusions are applied. "
        "Original randomized counts and exclusions before deposition remain unknown.",
    ]
    if outcome == "participant_creativity":
        notes.append(
            "Outcome: mean of grade_1, grade_2, grade_3, and grade_4 within each "
            "participant in Mendeley v2. This equals grade_mean exactly for all "
            "360 participants in both deposits. Each person contributes one "
            "composition; SDs are across participant means, with denominator n-1."
        )
    elif outcome == "n_characters":
        notes.append(
            "Outcome: deposited n_characters for the participant's single "
            "composition. Raw unit is characters; no length normalization or "
            "transformation. SDs use denominator n-1."
        )
    else:
        notes.append(
            "Outcome: deposited dat_score, a participant-level score on the "
            "stated 0-100 scale. This recomputes statistics of the supplied score; "
            "raw DAT word lists and the original embedding implementation are "
            "not supplied. DAT measures association distances within one person's "
            "words, not diversity across people. It was administered after the "
            "writing task and after AI access ended (PDF pp. 8 and 31). "
            "SDs use denominator n-1."
        )
    if combined:
        notes.append(
            "Comparison: T_AI, PR_AI, and LOT_AI versus T_NoAI, PR_NoAI, and "
            "LOT_NoAI. Reproduction uses Table 5 OLS with intercept, AI, tournament, "
            "and piece-rate indicators, with Lottery omitted, and HC1 covariance "
            "to reproduce Stata's robust SE. The requested computed.difference "
            "is the unadjusted participant-weighted mean difference, estimated by "
            "OLS on intercept and AI alone; it is not the adjusted Table 5 coefficient."
        )
    else:
        notes.append(
            f"Comparison: {ARM_CODES[estimate['treatment_arm']]} versus "
            f"{ARM_CODES[estimate['control_arm']]}, retaining the complete two arms. "
            "Reproduction uses Table 1 participant means, sample SDs, and counts. "
            "The computed contrast is OLS of the participant outcome on an "
            "intercept and AI indicator. These arms also enter the combined record."
        )
    notes.append(
        "Session uncertainty: the paper states random assignment but does not "
        "explicitly identify whether people or sessions were randomized. The "
        "deposited session variable has 21 distinct values and every session "
        "contains exactly one treatment arm. PDF p. 8 refers to sessions "
        "conducted under a treatment, and Appendix A instructions (PDF p. 30) "
        "apply the same rules to everyone in the session. Therefore this analysis "
        "uses session-clustered uncertainty for the observed treatment delivery "
        "structure; this is an analytical decision, not confirmation of the "
        "unreported allocation protocol. "
        f"This contrast contains {tclusters} AI sessions and {cclusters} no-AI "
        "sessions; n_clusters is their observed total, not a claimed randomized "
        "count. CR1 covariance uses sum_g[(X_g' u_g)(X_g' u_g)'] between two "
        "(X'X)^(-1) matrices, multiplied by G/(G-1)*(N-1)/(N-K), with K=2. "
        "Participant means and SDs weight people equally; session means are not "
        "used as outcomes. Three recorded sessions contain 24 participants, "
        "despite the paper saying sessions had up to 20; recorded session IDs "
        "are retained without speculative splitting. The six arms each contain "
        "3 no-AI or 4 AI sessions."
    )
    notes.append(
        "Between-subjects design: round=all refers to the single writing task "
        "and its post-task questionnaire. Later stages reuse the same writing; "
        "there is no paired AI/no-AI outcome or first-round crossover result. "
        "No across-person diversity estimate occurs in the reconciled extraction. "
        "The deposited Stata programs were consulted only as text."
    )
    return " ".join(notes)


def main():
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    retrieval_path = ROOT / "retrieval.json"
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))["c194"]
    pdf_path = Path(retrieval["pdf_path"])
    md_path = Path(retrieval["md_path"])
    codebook_path = ROOT.parent / "creativity-codebook.md"
    spec_path = ROOT / "extraction-spec.md"

    # Read documents as inert source material. Never import deposited code.
    for path in (md_path, codebook_path, spec_path, FIG_DO, MEN_DO, README):
        path.read_text(encoding="utf-8-sig")
    with pymupdf.open(pdf_path) as pdf:
        assert len(pdf) == 54
        # The analyst has read the full markdown in consecutive chunks.
        # Preserve checks that these are the PDF tables used for reproduction.
        assert "5.615" in pdf[13].get_text() and "83.705" in pdf[13].get_text()
        assert "148" in pdf[15].get_text() and "212" in pdf[15].get_text()
        assert "84.268" in pdf[22].get_text() and "-0.064" in pdf[22].get_text()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["deposits"]
    for folder, path in (("figshare-32132980", FIG_DTA),
                         ("mendeley-t93pf5r6fp-v2", MEN_DTA)):
        expected = manifest[folder]["files"][path.name]["sha256"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected

    fig = pd.read_stata(FIG_DTA, convert_categoricals=False)
    men = pd.read_stata(MEN_DTA, convert_categoricals=False)
    fig = fig.sort_values("id_prog").reset_index(drop=True)
    men = men.sort_values("id_prog").reset_index(drop=True)
    assert set(fig.columns).issubset(men.columns)
    for column in fig:
        assert fig[column].equals(men[column]), f"Deposit difference: {column}"
    for column in ("id_prog", "id_code"):
        assert fig[column].notna().all() and fig[column].is_unique
    ratings = men[["grade_1", "grade_2", "grade_3", "grade_4"]].astype(np.float64)
    assert ratings.notna().all().all()
    participant_creativity = ratings.mean(axis=1)
    assert np.array_equal(participant_creativity, fig["grade_mean"])

    # One row per person. Average the four ratings first, then summarize people.
    d = fig[["id_prog", "session", "treatment", "n_characters", "dat_score"]].copy()
    d["participant_creativity"] = participant_creativity
    for column in OUTCOMES.values():
        d[column] = d[column].astype(np.float64)
        assert np.isfinite(d[column]).all()
    assert d["session"].notna().all()
    assert set(d["treatment"]) == set(ARM_CODES.values())
    assert d.groupby("session")["treatment"].nunique().eq(1).all()
    assert d["session"].nunique() == 21
    d["AI"] = d["treatment"].isin(AI_ARMS).astype(float)

    results, skipped = [], []
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        outcome = next((value for key, value in OUTCOMES.items() if slug.startswith(key)), None)
        if outcome is None:
            skipped.append({"slug": slug, "reason": "No confirmed deposited outcome mapping."})
            continue
        assert estimate["within_person"] is None
        combined = slug.endswith("ai_combined_vs_no_ai_combined")
        if combined:
            sample = d.copy()
        else:
            arms = [ARM_CODES[estimate["treatment_arm"]], ARM_CODES[estimate["control_arm"]]]
            sample = d.loc[d["treatment"].isin(arms)].copy()
        sample = sample.reset_index(drop=True)

        checks = reproduce(estimate, sample, outcome, combined)
        notes = notes_for(estimate, sample, outcome, combined)
        if all(item["match"] for item in checks):
            computed = calculate(sample, outcome)
        else:
            # Never calculate a new contrast after a failed reproduction gate.
            computed = dict.fromkeys(COMPUTED_FIELDS)
            failed = [item for item in checks if not item["match"]]
            reason = "Reproduction failed; no derived contrast computed: " + json.dumps(failed)
            notes += " " + reason
            skipped.append({"slug": slug, "reason": reason})
        results.append({
            "slug": slug,
            "round": "all",
            "reproduced": checks,
            "computed": computed,
            "notes": notes,
        })

    obj = {
        "cid": "c194",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": [path.as_posix() for path in (
            FIG_DTA, MEN_DTA, FIG_DO, MEN_DO, README, MANIFEST,
            EXTRACTION, retrieval_path, pdf_path, md_path, codebook_path, spec_path,
        )],
        "results": results,
        "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
        fh.write("\n")
    # Confirm that the exact written UTF-8 file parses and round-trips.
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({
        "cid": "c194",
        "n_results": len(results),
        "n_reproduced": sum(all(x["match"] for x in r["reproduced"]) for r in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
