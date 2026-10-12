"""Audit the supplied c132 deposit and write analyst A's results.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c132/A.py

The supplied GitHub snapshot contains no participant/idea/rating data files.
Consequently no estimate passes the required reproduce-first gate. Published
coefficients, rendered tables, figures, and notebook previews are not treated as
observations. Author programs are read as text only, never imported or executed.
Only A.json is written by this script. No network requests or cache files are
needed. If data are later added, this audit stops instead of retaining stale skips.
"""

import sys

sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

import pymupdf


SCREENING = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = SCREENING / "analysis/c132/A.py"
OUTPUT = SCREENING / "analysis/c132/A.json"
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DEPOSIT_ID = "github-sarahhannahwu-idea_generation"
DEPOSIT = MANIFEST.parent / DEPOSIT_ID
REPOSITORY = DEPOSIT / "idea_generation-unpacked/idea_generation-HEAD"
DATA_SUFFIXES = {".csv", ".tsv", ".xlsx", ".sav", ".dta", ".rds", ".json", ".txt"}

# These are inputs or intermediate datasets identified by reading author code.
# No file with any of these names occurs anywhere in the supplied deposit.
EXPECTED_DATA_NAMES = {
    "iriss.csv",
    "iriss_trial_data.csv",
    "iriss_manual_ratings.csv",
    "iriss_manual_ratings_metrics.csv",
    "pilot_no_first_message.csv",
    "passenger_no_first_message.csv",
    "evaluated_compliant_conversations.csv",
    "evaluated_compliant_ideas.csv",
    "compliant_trials_demographics.csv",
    "evaluated_compliant_ideas_with_embeddings.csv",
    "doshi_centroid_analysis.csv",
    "iriss_semantic_similarities.csv",
    "compliant_semantic_similarities.csv",
    "cluster_stats_summary.csv",
    "cluster_stats_itt.csv",
}


def main():
    # data_files records files actually read, including the provenance and
    # author-source text used to establish why there are no analyzable data.
    files_read = []

    def remember(path):
        name = path.as_posix()
        if name not in files_read:
            files_read.append(name)

    def read_text(path):
        value = path.read_text(encoding="utf-8")
        remember(path)
        return value

    extraction = json.loads(read_text(SCREENING / "extraction/c132.json"))
    retrieval = json.loads(read_text(SCREENING / "retrieval.json"))["c132"]
    manifest = json.loads(read_text(MANIFEST))
    read_text(SCREENING.parent / "creativity-codebook.md")
    read_text(SCREENING / "extraction-spec.md")

    # Read the complete supplied markdown, including both appendices.
    markdown = read_text(Path(retrieval["md_path"]))
    assert "Appendix A" in markdown and "Appendix B" in markdown
    assert extraction["cid"] == "c132"
    assert manifest["papers"]["c132"] == [DEPOSIT_ID]
    deposit_record = manifest["deposits"][DEPOSIT_ID]
    assert deposit_record["source_url"] == (
        "https://github.com/sarahhannahwu/idea_generation/tree/main/analyses/iriss"
    )

    # Confirm the relevant printed sources independently of the markdown.
    pdf_path = Path(retrieval["pdf_path"])
    with pymupdf.open(str(pdf_path)) as document:
        assert len(document) == 42
        page_text = {
            number: document[number - 1].get_text()
            for number in (11, 13, 14, 15, 16, 17, 18, 35, 36)
        }
    remember(pdf_path)
    assert "1709" in page_text[35]
    assert "337" in page_text[36]
    assert "all-MiniLM-L6-v2" in page_text[14]

    sources = {}
    for relative in (
        ".gitignore",
        "requirements.txt",
        "analyses/iriss/README.md",
        "analyses/iriss.qmd",
        "analyses/iriss/tables.Rmd",
        "analyses/iriss/embeddings.py",
        "analyses/iriss/doshi_analysis.py",
        "analyses/iriss/clustering.ipynb",
        "analyses/iriss/monte_carlo.py",
        "analyses/iriss/cross_validation.py",
    ):
        sources[relative] = read_text(REPOSITORY / relative)

    # Parse notebook JSON only to read its source strings, not its code or
    # cached output as executable instructions or as participant observations.
    notebook = json.loads(sources["analyses/iriss/clustering.ipynb"])
    clustering_source = "\n".join(
        "".join(cell.get("source", [])) for cell in notebook["cells"]
    )
    assert "*.csv" in sources[".gitignore"].splitlines()
    assert "compliant_trials_demographics.csv" in sources["analyses/iriss/tables.Rmd"]
    assert "doshi_centroid_analysis.csv" in sources["analyses/iriss.qmd"]
    assert "iriss_manual_ratings_metrics.csv" in clustering_source
    assert "all-MiniLM-L6-v2" in clustering_source

    # Path.rglob includes ignored and hidden files, so .gitignore cannot hide
    # an actual downloaded CSV from this availability check.
    inventory = sorted(path for path in DEPOSIT.rglob("*") if path.is_file())
    candidates = [path for path in inventory if path.suffix.lower() in DATA_SUFFIXES]
    unexpected = [path for path in candidates if path != REPOSITORY / "requirements.txt"]
    if unexpected:
        raise RuntimeError(
            "The deposit now contains additional possible data files; inspect "
            "and reproduce the estimates before replacing this audit: "
            + ", ".join(path.as_posix() for path in unexpected)
        )
    present_expected = [path for path in inventory if path.name in EXPECTED_DATA_NAMES]
    if present_expected:
        raise RuntimeError("Previously missing analysis inputs are now present.")
    assert candidates == [REPOSITORY / "requirements.txt"]

    common = (
        "The supplied github-sarahhannahwu-idea_generation download has no "
        "participant, rating, or idea data: the only file with an allowed data "
        "extension is requirements.txt, a dependency list. The repository's "
        ".gitignore explicitly excludes *.csv. "
    )
    ratings = (
        "Missing data/compliant_trials_demographics.csv, the input named by "
        "analyses/iriss/tables.Rmd. The raw alternatives iriss.csv, "
        "iriss_manual_ratings.csv, pilot_no_first_message.csv, and "
        "passenger_no_first_message.csv are also absent. The intended outcome "
        "column is {outcome}; submitter_id identifies people, condition identifies "
        "High-Agency/Low-Agency/Control, and object and rater_id identify repeated "
        "tasks and ratings. analyses/iriss.qmd applies the submitter attention "
        "check and completion filter, the evaluator attention/logging filters, "
        "and excludes noncompliant submitter-object trials before retaining "
        "evaluated ideas (lines 86-95, 636-639, 1087-1121, 1485-1493). "
        "This matches the exclusions described on PDF pp. 13-14. Table A2 "
        "(PDF p. 35) reports 1709 rating observations across all three arms, "
        "not participant counts. Neither those rows nor the printed model "
        "results can be reproduced from the download. No participant means, "
        "SDs, counts, differences, or HC2 SEs are computed. The three objects "
        "are repeated tasks within a between-person assignment (PDF p. 11); "
        "a paired or first_round treatment contrast does not apply."
    )
    centroid = (
        "Missing data/doshi_centroid_analysis.csv, the similarity_to_cond_obj "
        "input named in analyses/iriss.qmd and analyses/iriss/tables.Rmd. "
        "The source idea texts, submitter IDs, arm/object labels, compliance "
        "records, and stored embeddings are also absent. PDF pp. 14-16 specify "
        "all-MiniLM-L6-v2, one sampled idea per person per object, and a "
        "leave-one-out condition-object centroid. The exact sampled texts and "
        "centroid pool cannot be reconstructed. Table A3's 337 observations "
        "and its coefficients, and the pairwise results on p. 16, cannot be "
        "reproduced. This diversity measure depends on a set of outputs; "
        "no substitute embedding model, participant-level SD, or HC2 effect "
        "is computed."
    )
    clustering = (
        "Missing data/iriss_manual_ratings_metrics.csv, the input named in "
        "analyses/iriss/clustering.ipynb; the underlying idea texts, arm/object "
        "labels, and embeddings are absent. Reading that notebook as text "
        "identifies stripped/lowercased use strings, all-MiniLM-L6-v2 "
        "embeddings, normalized vectors, and HDBSCAN separately by condition "
        "and object with min_cluster_size=6, min_samples=1, "
        "cluster_selection_epsilon=0.25, Euclidean distance, and eom selection. "
        "Without the exact texts the paper's set-level procedure and the "
        "maximum-minus-minimum permutation statistic (PDF pp. 16-17) cannot "
        "be reproduced. This outcome has no participant-level value; no "
        "participant SD or HC2 effect is computed."
    )

    skipped = []
    family_counts = Counter()
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        if estimate["construct"] in {"overall_creativity", "novelty", "usefulness"}:
            outcome = {
                "overall_creativity": "creativity",
                "novelty": "originality",
                "usefulness": "usefulness",
            }[estimate["construct"]]
            reason = common + ratings.format(outcome=outcome)
            family_counts["ratings"] += 1
        elif slug.startswith("s1_centroid_similarity_"):
            reason = common + centroid
            family_counts["centroid"] += 1
        elif estimate["unit"] == "set" and estimate["construct"] == "diversity":
            reason = common + clustering
            if slug == "s1_cluster_size_cv_high_agency_vs_low_agency":
                reason += (
                    " In addition, this pair is described only qualitatively "
                    "on PDF p. 18; no pair-specific numerical statistic is printed."
                )
            family_counts["clustering"] += 1
        else:
            raise RuntimeError("Unreviewed estimate: " + slug)
        skipped.append({"slug": slug, "reason": reason})

    assert family_counts == {"ratings": 9, "centroid": 3, "clustering": 4}
    assert len({row["slug"] for row in skipped}) == len(extraction["estimates"])
    result = {
        "cid": "c132",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": files_read,
        "results": [],
        "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as handle:
        validated = json.load(handle)
    assert validated == result
    print(json.dumps({
        "cid": "c132",
        "n_results": len(validated["results"]),
        "n_reproduced": 0,
        "n_skipped": len(validated["skipped"]),
    }))


if __name__ == "__main__":
    main()
