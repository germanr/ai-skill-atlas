"""Independent analyst B audit for paper c132.

Run with: python -I -B B.py
Only B.json is written. The supplied repository snapshot has no observational
study data. All 16 estimates must be skipped under the reproduce-first rule.
The data_files field is an audit trail of the files read; it includes source
and metadata documents, NOT a claim that participant data were available.
Authors' programs/notebooks are read solely as text and never executed/imported.
No other analyst's script or results are accessed.
"""

import json
from pathlib import Path

CID = "c132"
BASE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = BASE / "analysis/c132/B.py"
OUTPUT = BASE / "analysis/c132/B.json"
DEPOSIT_ID = "github-sarahhannahwu-idea_generation"
DEPOSIT = Path(r"D:/projects/ai-skill-atlas/creativity-data") / DEPOSIT_ID
REPO = DEPOSIT / "idea_generation-unpacked/idea_generation-HEAD"
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DATA_SUFFIXES = {".csv", ".tsv", ".xlsx", ".sav", ".dta", ".rds", ".json", ".txt"}
READ_FILES = []


def read_text(path):
    """Read UTF-8 source material without evaluating any deposited code."""
    path = Path(path)
    result = path.read_text(encoding="utf-8")
    name = path.as_posix()
    if name not in READ_FILES:
        READ_FILES.append(name)
    return result


def audit_inputs():
    extraction = json.loads(read_text(BASE / "extraction/c132.json"))
    retrieval = json.loads(read_text(BASE / "retrieval.json"))[CID]
    manifest = json.loads(read_text(MANIFEST))
    deposit_metadata = manifest["deposits"][DEPOSIT_ID]
    assert deposit_metadata["files"]["idea_generation.zip"]["sha256"] == (
        "f4352e62c614969ec0c7d6603362f17e2875e46301ab2ced3dc8baa39a149701"
    ), "The manifest now describes a different repository snapshot."

    # The complete markdown (including both appendices) was read in chunks
    # during the audit. Re-read it here to record this script's source inputs.
    paper_text = read_text(retrieval["md_path"])
    assert "Appendix A" in paper_text and "Appendix B" in paper_text
    assert "Transformational and Combinational" in paper_text
    read_text(BASE.parent / "creativity-codebook.md")
    read_text(BASE / "extraction-spec.md")

    # Read programs strictly as text, to establish variable mappings and the
    # missing inputs. In particular, neither R nor notebook code is evaluated.
    source_names = [
        ".gitignore",
        "requirements.txt",
        "analyses/iriss/README.md",
        "analyses/iriss.qmd",
        "analyses/iriss/tables.Rmd",
        "analyses/iriss/embeddings.py",
        "analyses/iriss/doshi_analysis.py",
        "analyses/iriss/clustering.ipynb",
    ]
    source_text = {name: read_text(REPO / name) for name in source_names}
    assert "*.csv" in source_text[".gitignore"].splitlines()
    qmd = source_text["analyses/iriss.qmd"]
    assert "compliant_trials_demographics" in qmd
    assert "doshi_centroid_analysis.csv" in qmd
    assert "cluster_stats_summary.csv" in qmd

    # Scan the entire supplied deposit, not merely the nominal data folder.
    # No archive is extracted and no additional files are created.
    all_files = sorted(p for p in DEPOSIT.rglob("*") if p.is_file())
    data_candidates = [p for p in all_files if p.suffix.lower() in DATA_SUFFIXES]
    study_data = [p for p in data_candidates if p != REPO / "requirements.txt"]
    if study_data:
        raise RuntimeError(
            "Study-data candidates are now present; this missing-data audit "
            "must be revisited before reporting skipped estimates: "
            + ", ".join(p.as_posix() for p in study_data)
        )

    required_names = {
        "iriss.csv",
        "iriss_manual_ratings.csv",
        "iriss_manual_ratings_metrics.csv",
        "iriss_trial_data.csv",
        "pilot_no_first_message.csv",
        "passenger_no_first_message.csv",
        "compliant_trials_demographics.csv",
        "evaluated_compliant_ideas.csv",
        "evaluated_compliant_ideas_with_embeddings.csv",
        "doshi_centroid_analysis.csv",
        "iriss_semantic_similarities.csv",
        "cluster_stats_summary.csv",
    }
    available_names = {p.name for p in all_files}
    assert not required_names.intersection(available_names)
    assert extraction["cid"] == CID and len(extraction["estimates"]) == 16
    return extraction


def reason_for(estimate):
    """State why each extracted contrast cannot pass reproduction."""
    slug = estimate["slug"]
    common = (
        "The supplied deposit contains no participant/rating datasets in the "
        "permitted data formats. Its only such file is requirements.txt, a "
        "software dependency list, and .gitignore excludes *.csv. The paths "
        "in data_files document source/metadata files read for this audit; "
        "they are not observed participant data. "
    )
    if estimate["question"] == "with_ai":
        metric = {"overall_creativity": "creativity", "novelty": "originality",
                  "usefulness": "usefulness"}[estimate["construct"]]
        reason = (
            "Missing compliant_trials_demographics.csv, the rating-level input "
            "identified in analyses/iriss.qmd (lines 1484-1585), including "
            f"submitter_id, condition, object, rater_id, and {metric}. The raw "
            "iriss.csv, iriss_manual_ratings.csv, pilot_no_first_message.csv "
            "and passenger_no_first_message.csv are also absent, so the "
            "analysis cannot be rebuilt. The code maps Pilot/GuidedInstructions "
            "to High-Agency and Passenger/UnguidedInstructions to Low-Agency; "
            "the Control condition is the human-only arm. It filters attention "
            "checks, completion and evaluator logging failures, then excludes "
            "AI-arm submitter-object trials without chat data and retains "
            "evaluated ideas (PDF pp. 13-15). "
        )
        regression = estimate["stats"]["regression"]
        if regression is not None:
            printed = f"{regression['coef']:.3f}"
            direction = (
                "Control minus Low-Agency" if "low_agency_vs_control" in slug
                else "High-Agency minus Low-Agency"
            )
            reason += (
                f"Cannot recompute the Table A2 coefficient {printed} "
                f"({direction}), its SE, or the full-model count of 1709 "
                "rating rows. "
            )
        else:
            reason += (
                "Table A2 prints no direct High-Agency-versus-Control "
                "coefficient or observed arm means; its full-model count "
                "of 1709 rating rows cannot be recomputed. "
            )
        return common + reason + (
            "No analyzed arm counts, participant means/SDs, or HC2 contrast "
            "are computed without the observations. Table random-effect and "
            "residual SDs are not participant-level outcome SDs."
        )

    if "centroid_similarity" in slug:
        return common + (
            "Missing doshi_centroid_analysis.csv (the Table A3 input named "
            "in analyses/iriss.qmd, lines 1309-1322, and "
            "analyses/iriss/tables.Rmd), with submitter_id, condition, object "
            "and similarity_to_cond_obj. The idea-text and embedding inputs "
            "are also absent. The paper uses all-MiniLM-L6-v2 and one randomly "
            "sampled idea per submitter-object with leave-one-out "
            "condition-object centroids (PDF pp. 14-16). Without those exact "
            "texts and sampled rows, the measure cannot be recomputed "
            "following the same procedure. The 337 observations and the "
            "Table A3 coefficient/pairwise comparison cannot be reproduced. "
            "No participant-level SD or HC2 SE is substituted for this "
            "set-dependent diversity outcome."
        )

    if estimate["construct"] == "diversity" and estimate["unit"] == "set":
        reason = (
            "Missing iriss_manual_ratings_metrics.csv, the idea-text input "
            "named in analyses/iriss/clustering.ipynb, and "
            "cluster_stats_summary.csv. Notebook source was inspected only "
            "as text. The procedure embeds stripped, lowercased use strings "
            "with all-MiniLM-L6-v2, normalizes embeddings and clusters each "
            "condition-object set with HDBSCAN. PDF p. 17 specifies "
            "min_cluster_size=6, min_samples=1 and "
            "cluster_selection_epsilon=0.25, followed by 5000 permutations "
            "of the maximum-minus-minimum condition-mean statistic. Exact "
            "texts, input rows and embeddings are absent, so the procedure "
            "cannot be reproduced under the diversity rule. "
        )
        difference = estimate["stats"]["difference"]
        if difference is not None:
            reason += (
                f"The printed difference {difference:.2f} and its permutation "
                "p-value remain unverified, and arm levels cannot be "
                "recomputed. "
            )
        else:
            reason += (
                "This High-Agency-versus-Low-Agency CV contrast is qualitative "
                "in the Discussion; no pair-specific numerical result is "
                "printed to reproduce. "
            )
        return common + reason + (
            "These condition-object set metrics have no participant-level "
            "outcome, so participant SDs and HC2 SEs are not applicable."
        )
    raise ValueError("Unclassified extraction estimate: " + slug)


def main():
    extraction = audit_inputs()
    result = {
        "cid": CID,
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": READ_FILES,
        "results": [],
        "skipped": [
            {"slug": estimate["slug"], "reason": reason_for(estimate)}
            for estimate in extraction["estimates"]
        ],
    }
    assert len({item["slug"] for item in result["skipped"]}) == 16
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == result
    print(json.dumps({
        "cid": CID,
        "n_results": len(parsed["results"]),
        "n_reproduced": 0,
        "n_skipped": len(parsed["skipped"]),
    }))


if __name__ == "__main__":
    main()
