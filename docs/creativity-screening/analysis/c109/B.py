"""Independent analyst B reanalysis for c109.

Run with python -I -B B.py. Only B.json is written. No deposited code is run.
The two available outcome variables score joint dyad outputs, not individuals.
Consequently participant-level SDs remain null; the raw contrasts and their
uncertainty are estimated using one observation per randomized dyad.
"""

import csv
import io
import json
import math
import statistics
import sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = ROOT / "analysis/c109/B.py"
OUTPUT = ROOT / "analysis/c109/B.json"
DEPOSIT = Path(
    "D:/projects/ai-skill-atlas/creativity-data/osf-nmqd5/"
    "Supplemental Material-unpacked/Supplemental Material"
)
READ_FILES = []


def read_text(path, encoding="utf-8"):
    path = Path(path)
    text = path.read_text(encoding=encoding)
    if path.as_posix() not in READ_FILES:
        READ_FILES.append(path.as_posix())
    return text


def read_csv(name, encoding="utf-8-sig"):
    return list(csv.DictReader(io.StringIO(read_text(DEPOSIT / name, encoding))))


def check(statistic, printed, computed, digits):
    precision = Decimal(1).scaleb(-digits)
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": (
            Decimal(str(computed)).quantize(precision, rounding=ROUND_HALF_UP)
            == Decimal(str(printed))
        ),
    }


def grouped(rows, column):
    return {
        arm: [float(row[column]) for row in rows if row["cue"] == arm]
        for arm in ("cue", "no cue")
    }


def available(rows, column):
    return [row for row in rows if row[column].strip()]


def complete_cases(rows, column):
    return [
        row for row in available(rows, column)
        if row["dsgn"].strip() and row["know"].strip()
    ]


def arm_description(rows, column):
    parts = []
    for arm, values in grouped(rows, column).items():
        parts.append(
            f"{arm}: {len(values)} dyads, mean={statistics.mean(values):.12g}, "
            f"dyad SD={statistics.stdev(values):.12g}"
        )
    return "; ".join(parts)


def cluster_contrast(rows, column):
    """OLS y_dyad ~ 1 + cue, with CR1 covariance clustered by Session.

    With one observation per cluster, N=G and K=2. The usual correction
    G/(G-1) * (N-1)/(N-K) equals G/(G-2). For a two-arm saturated model,
    the uncorrected slope variance is SSE_t/G_t**2 + SSE_c/G_c**2.
    This is also the closed-form cluster sandwich calculation. It was
    independently checked against statsmodels OLS(cov_type='cluster',
    cov_kwds={'groups': Session, 'use_correction': True}).
    """
    values = grouped(rows, column)
    treatment, control = values["cue"], values["no cue"]
    gt, gc = len(treatment), len(control)
    g = gt + gc
    mt, mc = statistics.mean(treatment), statistics.mean(control)
    sset = math.fsum((value - mt) ** 2 for value in treatment)
    ssec = math.fsum((value - mc) ** 2 for value in control)
    variance = (g / (g - 2)) * (sset / gt**2 + ssec / gc**2)
    return {
        "n_treatment": 2 * gt,
        "n_control": 2 * gc,
        "treatment_mean": mt,
        "treatment_sd": None,
        "control_mean": mc,
        "control_sd": None,
        "difference": mt - mc,
        "difference_se": math.sqrt(variance),
        "se_type": "cluster",
        "n_clusters": g,
    }


def validate_sessions(rows):
    sessions = [row["Session"] for row in rows]
    assert len(sessions) == len(set(sessions)), "Repeated Session rows"
    assert set(row["cue"] for row in rows) == {"cue", "no cue"}
    assert set(row["modality"] for row in rows) == {"virtual", "inperson"}


def analyze(slug, rows, column, estimate, figure_values, roster, pdf_locator):
    selected = available(rows, column)
    values = grouped(selected, column)
    reproduction = []
    for arm, prefix in (("cue", "treatment"), ("no cue", "control")):
        vals = values[arm]
        reproduction.extend([
            check(
                prefix + "_mean_dyad", estimate["stats"][prefix + "_mean"],
                statistics.mean(vals), 1,
            ),
            check(
                prefix + "_sd_dyad", estimate["stats"][prefix + "_sd"],
                statistics.stdev(vals), 1,
            ),
        ])
        for label, operation in (("min", min), ("median", statistics.median),
                                 ("max", max)):
            printed, digits = figure_values[arm][label]
            reproduction.append(check(
                prefix + "_" + label + "_dyad_figure5",
                printed, operation(vals), digits,
            ))
    # The paper gives overall enrollment only, not outcome-specific arm Ns.
    # These checks refer to the full session roster, not to selected outcomes.
    reproduction.extend([
        check("overall_session_roster_vs_reported_dyads", 86, len(roster), 0),
        check("overall_roster_people_vs_reported_enrollment", 172,
              2 * len(roster), 0),
    ])
    if not all(item["match"] for item in reproduction):
        return None, {
            "slug": slug,
            "reason": "Reproduction failed; no contrast computed. "
            + json.dumps([item for item in reproduction if not item["match"]]),
        }

    # Only after matching the published descriptives do we derive a contrast.
    computed = cluster_contrast(selected, column)
    cc = complete_cases(rows, column)
    missing_outcome = [row["Session"] for row in rows if not row[column].strip()]
    missing_covariates = [
        row["Session"] for row in selected
        if not row["dsgn"].strip() or not row["know"].strip()
    ]
    cells = Counter((row["cue"], row["modality"]) for row in selected)
    cell_text = "; ".join(
        f"{arm}/{modality}: {n} dyads ({2*n} people)"
        for (arm, modality), n in sorted(cells.items())
    )
    notes = (
        f"Source variable: {column!r}; one row per Session/dyad. "
        "Treatment is cue, pooling virtual and inperson; control is no cue, "
        "pooling the same modalities. Between-dyad design, so round='all' "
        "and no first-round or paired result. "
        f"Published means and SDs: {pdf_locator}. Additional exact numerical "
        "labels (minimum, median, maximum) in Fig. 5, PDF p. 8 (printed p. 303), "
        "also match. They are printed figure labels, not values read from "
        "plotted positions. SDs in the reproduced list use denominator G_arm-1 "
        "across dyads. The deposited scores are the authors' already scored "
        "outcomes; original idea/transcript scoring was not rerun. "
        f"Analysis uses every nonmissing outcome: {len(selected)} dyads. "
        f"Arm/modality counts: {cell_text}. "
        f"Missing outcome rows excluded: {missing_outcome}. "
        f"Rows retained despite missing background covariates: {missing_covariates}. "
        "Section 4.1.1 excludes missing background values specifically from "
        "analyses accounting for those factors. The requested unadjusted "
        "arm-indicator contrast uses no such factors. "
        f"The complete-background-covariate alternative has {len(cc)} dyads "
        f"({arm_description(cc, column)}); it is not the sample used here. "
        "No additional exclusions were guessed from the narrative or session "
        "number gaps. n_treatment and n_control count people: two partners "
        "per observed dyad, as specified in PDF p. 5 (printed p. 300), "
        "Section 4.1.1. The overall 86-dyad/172-person roster checks do not "
        "establish paper-reported analysis counts, which are absent. "
        "The post-surveys contain self-reports only, including a missing Cue "
        "response and duplicate participant-ID labels; survey completion "
        "is not used as an outcome exclusion or as a participant roster. "
        "The posted outcome is jointly produced and scored at dyad level. "
        "Arm means are means of shared dyad outcomes, also the "
        "participant-weighted means of the shared outcome because every dyad "
        "has two people. They do not describe separately scored individual "
        "contributions. Participant-level SDs cannot be identified: "
        "treatment_sd and control_sd are null, and no dyad rows were "
        "duplicated to manufacture individual scores or a participant-level "
        "standardizer. The raw difference is treatment minus control in "
        "the original dyad-outcome units. difference_se is the OLS "
        "intercept-plus-cue slope SE, clustered on Session using CR1 with "
        "one observation per randomized dyad: SE^2 = G/(G-2) * "
        "[SSE_t/G_t^2 + SSE_c/G_c^2]. n_clusters=G counts all analyzed dyads. "
        "This is a new unadjusted contrast, not the paper's REML F test. "
        "The REML statistic, denominator degrees of freedom and p value "
        "are not claimed as reproduced."
    )
    if column == "Topic diversity":
        notes += (
            " The Cue minimum 1.494 printed in Fig. 5a is S9, which has "
            "missing dsgn/know, confirming that the published descriptives "
            "include background-incomplete dyads despite both candidate "
            "samples having the same one-decimal arm summaries."
        )
    else:
        notes += (
            " Complete-case means round to 9.7 and 8.1, and SDs to 2.3 "
            "and 2.6, which differ from the printed 9.6/8.0 and 2.2/2.5. "
            "The supplied conversation file already contains 66 sessions; "
            "recordings absent from it cannot be restored."
        )
    return {
        "slug": slug,
        "round": "all",
        "reproduced": reproduction,
        "computed": computed,
        "notes": notes,
    }, None


def main():
    extraction = json.loads(read_text(ROOT / "extraction/c109.json"))
    retrieval = json.loads(read_text(ROOT / "retrieval.json"))["c109"]
    read_text(ROOT.parent / "creativity-codebook.md")
    read_text(ROOT / "extraction-spec.md")
    read_text(retrieval["md_path"])
    # The PDF was independently inspected with PyMuPDF during the audit.
    # Read it again as PDF data, never as code, and record its provenance.
    import pymupdf
    with pymupdf.open(retrieval["pdf_path"]) as pdf:
        assert len(pdf) == 21
        assert "172" in pdf[4].get_text()
        assert "19.4" in pdf[6].get_text()
        assert "6.25" in pdf[8].get_text()
    READ_FILES.append(Path(retrieval["pdf_path"]).as_posix())
    manifest = json.loads(read_text(
        "D:/projects/ai-skill-atlas/creativity-data/manifest.json"
    ))
    assert "osf-nmqd5" in manifest["papers"]["c109"]
    read_text(DEPOSIT / "Supplementary Data README.txt")
    ideas = read_csv("Idea_012-use-correct.csv")
    conversations = read_csv("conversation-final-use-correct.csv")
    # Inspect survey IDs only; none of the survey measures is an eligible
    # scored-output outcome, and survey response is not an exclusion rule.
    surveys = [read_csv("cue_condition_post.csv"),
               read_csv("nocue_condition_post.csv", "cp1252")]
    assert [len(rows) for rows in surveys] == [83, 88]
    validate_sessions(ideas)
    validate_sessions(conversations)
    assert set(row["Session"] for row in conversations).issubset(
        set(row["Session"] for row in ideas)
    )
    roster = {row["Session"]: row for row in ideas}
    for row in conversations:
        for column in ("cue", "modality", "dsgn", "know", "# of all ideas"):
            assert row[column] == roster[row["Session"]][column]
    estimates = {estimate["slug"]: estimate for estimate in extraction["estimates"]}
    figure_idea = {
        "cue": {"min": (1.494, 3), "median": (2.351, 3), "max": (2.784, 3)},
        "no cue": {"min": (1.075, 3), "median": (2.098, 3), "max": (2.805, 3)},
    }
    figure_conversation = {
        "cue": {"min": (6.00, 2), "median": (9.00, 2), "max": (14.00, 2)},
        "no cue": {"min": (3.00, 2), "median": (8.00, 2), "max": (14.00, 2)},
    }
    results, skipped = [], []
    for slug, rows, column, figure, locator in [
        ("s1_idea_topic_diversity_cue_vs_nocue", ideas, "Topic diversity",
         figure_idea, "PDF p. 7 (printed p. 302), Section 5.1.1"),
        ("s1_conversation_topics_cue_vs_nocue", conversations, "Topic_diversity",
         figure_conversation, "PDF p. 9 (printed p. 304), Section 5.1.2"),
    ]:
        result, failure = analyze(slug, rows, column, estimates[slug],
                                  figure, ideas, locator)
        if result is not None:
            results.append(result)
        else:
            skipped.append(failure)

    # Reproduction-only diagnostics for idea count. Do not compute an arm
    # contrast when no numerical contrast can be verified against the paper.
    count_rows = available(ideas, "# of all ideas")
    count_cc = complete_cases(ideas, "# of all ideas")
    overall = statistics.mean(float(row["# of all ideas"]) for row in count_rows)
    overall_cc = statistics.mean(float(row["# of all ideas"]) for row in count_cc)
    count_check = check("overall_idea_count_mean", 19.4, overall, 1)
    skipped.append({
        "slug": "s1_idea_count_cue_vs_nocue",
        "reason": (
            "No printed arm means, difference, coefficient, numerical test "
            "or analyzed arm counts are available in Section 5.1.3 (PDF p. 9, "
            "printed p. 304), so the required numerical contrast reproduction "
            "cannot be performed. The only numerical idea-count summary is "
            "the overall mean 19.4 in Section 5 (PDF p. 7, printed p. 302). "
            f"The # of all ideas column has {len(count_rows)} observed dyads "
            f"and mean {overall:.15g}, rounding to {overall:.1f}; "
            f"match={str(count_check['match']).lower()}. Applying complete "
            f"dsgn/know cases leaves {len(count_cc)} dyads and mean "
            f"{overall_cc:.15g}, rounding to {overall_cc:.1f}, also not 19.4. "
            "S5 and S15 have missing idea counts. No further exclusions can "
            "be identified from the deposited files without guessing, and "
            "no treatment/control contrast or SE was computed for this outcome."
        ),
    })
    skipped.append({
        "slug": "s1_idea_homogenization_cue_vs_nocue",
        "reason": (
            "This across-group diversity measure has no participant-level "
            "outcome. The deposit contains only dyad aggregates and post-survey "
            "responses, not the idea texts, topic assignments, embeddings, "
            "centroids or cosine distances used in the analysis. The embedding "
            "model is not named, and Section 6.3 (PDF p. 11, printed p. 306) "
            "describes a within-condition centroid whereas Appendix A.4.1 "
            "(PDF p. 16, printed p. 311) describes an average across groups. "
            "The exact procedure cannot be reproduced with the same model "
            "and texts. Figure 6 (PDF p. 17, printed p. 312) has no numerical "
            "arm summaries or reported Wilcoxon result. No replacement "
            "embedding model, inferred figure values or participant-level "
            "statistics were used."
        ),
    })
    assert {item["slug"] for item in results + skipped} == set(estimates)
    assert len(results + skipped) == len(estimates)
    obj = {
        "cid": "c109",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": READ_FILES,
        "results": results,
        "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({
        "cid": obj["cid"],
        "n_results": len(results),
        "n_reproduced": sum(all(x["match"] for x in r["reproduced"])
                            for r in results),
        "n_skipped": len(skipped),
    }))


if __name__ == "__main__":
    main()
