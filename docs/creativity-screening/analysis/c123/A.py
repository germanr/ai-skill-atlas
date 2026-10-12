"""Audit the supplied data for paper c123 and write analyst A's results.

Run with: python -I -B <absolute path to this file>

The full 742-line markdown conversion (including references and Appendix 1)
was read. PDF pages 10, 11, 12, 13, 16, 17, and 40 were checked with PyMuPDF.
The extraction contains three unadjusted PIT contrasts, three ANCOVAs, and
one group-by-task interaction, all for the same individually randomized
77 ChatGPT-assisted and 68 control participants. No participants were
excluded (PDF p. 10). This is not a randomized-order within-person design.

The sole supplied SAV instead contains ideas from human/model source
categories, automated scores, and pairwise distances. There is no defensible
mapping to the original participants, randomized arms, or expert ratings.
Consequently reproduction cannot begin, all seven slugs are skipped, and
no outcome means, differences, SDs, or SEs are computed from unrelated data
or reverse-engineered from the printed statistics. Audit counts below are
counts of data records, never claimed to be counts of study participants.

Only this analyst's A.json is written. No deposit code or analyst B files
are read or executed. The SAV is parsed solely as data with pyreadstat.
"""

import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

import pyreadstat


ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = ROOT / "analysis/c123/A.py"
OUTPUT = ROOT / "analysis/c123/A.json"
EXTRACTION = ROOT / "extraction/c123.json"
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DATA = Path(
    "D:/projects/ai-skill-atlas/creativity-data/osf-rn62y/"
    "Stylistic Bias in Automated Assessment of Creativity in Large Language Models/"
    "Stylistic Bias in Automated Assessment of Creativity in LLMs_Urban et al. 2025.sav"
)
REVIEWED_SHA256 = "38cb0fe6d2a28ef99377a4f204cbd2965d64b44890c775d1fb6ab98a949a2fcf"
REVIEWED_COLUMNS = [
    "ID", "Model", "Verbatim_Idea", "Humanized_Idea", "Ocsai_LLM",
    "Ocsai_Semantic", "CAP_CLAUS", "CAP_SemDis", "Ocsai_LLM_Humanized",
    "Ocsai_Semantic_Humanized", "CAP_CLAUS_Humanized", "CAP_SemDis_Humanized",
    "XXXXXXXXXXXXXXX", "Model_dist", "HUMANIZED_dist", "Distance",
]
REVIEWED_SLUGS = {
    "s1_quality_chatgpt_vs_control_unadjusted",
    "s1_elaboration_chatgpt_vs_control_unadjusted",
    "s1_originality_chatgpt_vs_control_unadjusted",
    "s1_quality_chatgpt_vs_control_ancova",
    "s1_elaboration_chatgpt_vs_control_ancova",
    "s1_originality_chatgpt_vs_control_ancova",
    "s1_originality_chatgpt_vs_control_group_by_task",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_json(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def audit_supplied_data():
    manifest = load_json(MANIFEST)
    entries = manifest["deposits"]["osf-rn62y"]["files"]
    records = [v for v in entries.values() if Path(v["path"]) == DATA]
    require(len(records) == 1, "The supplied SAV must have one manifest entry.")
    digest = hashlib.sha256(DATA.read_bytes()).hexdigest()
    require(
        digest == records[0]["sha256"] == REVIEWED_SHA256,
        "Data bytes differ from the reviewed deposit; reassessment is required.",
    )
    require(DATA.stat().st_size == records[0]["bytes"], "Manifest size mismatch.")

    data, metadata = pyreadstat.read_sav(str(DATA), apply_value_formats=False)
    require(list(data.columns) == REVIEWED_COLUMNS, "Unexpected SAV variables.")
    require(data.shape == (6958, 16), "Unexpected SAV shape.")
    require(metadata.missing_ranges == {}, "Unexpected user-defined missing values.")

    idea_mask = data["Model"].notna()
    require(idea_mask.equals(data["ID"].notna()), "Idea IDs and source rows differ.")
    require(
        idea_mask.equals(data["Verbatim_Idea"].str.strip().ne("")),
        "Idea text and source rows differ.",
    )
    ideas = data.loc[idea_mask]
    require(len(ideas) == 240, "Unexpected number of idea records.")
    require(ideas["ID"].nunique() == len(ideas), "Unexpected repeated idea IDs.")
    counts = {int(k): int(v) for k, v in ideas["Model"].value_counts().items()}
    require(counts == {k: 30 for k in range(8)}, "Unexpected source counts.")
    labels = metadata.variable_value_labels["Model"]
    require(labels[0.0] == "human", "The human source label changed.")
    require(set(labels) == set(range(8)), "Unexpected source labels.")
    require(
        data["Humanized_Idea"].str.strip().ne("").sum() == 210,
        "Unexpected number of humanized model ideas.",
    )
    require(data["XXXXXXXXXXXXXXX"].str.strip().eq("").all(), "Separator changed.")
    require(data["Distance"].notna().all(), "Distance block changed.")
    require(
        data[["Model_dist", "HUMANIZED_dist"]].notna().all().all(),
        "Distance source identifiers changed.",
    )

    # The idea and distance blocks are stored side by side in the SAV.
    # The 6,958 physical rows must not be interpreted as 6,958 people.
    return {
        "physical_rows": len(data),
        "idea_records": len(ideas),
        "human_idea_records": counts[0],
        "model_categories": len(counts) - 1,
        "ideas_per_model": counts[1],
        "distance_records": int(data["Distance"].notna().sum()),
    }


def reason_for(estimate, audit):
    stats = estimate["stats"]
    slug = estimate["slug"]
    dimension = slug.split("_")[1]
    counts = (
        f"The paper requires {estimate['n_treatment']} ChatGPT-assisted people and "
        f"{estimate['n_control']} control people (PDF p. 11); neither arm can be "
        "identified or counted in this file. "
    )
    mismatch = (
        "The supplied osf-rn62y SAV matches its manifest SHA-256 but contains a "
        "different dataset: "
        f"{audit['physical_rows']:,} physical rows, with "
        f"{audit['idea_records']} idea records ({audit['human_idea_records']} "
        f"labeled human and {audit['ideas_per_model']} from each of "
        f"{audit['model_categories']} model-source categories) alongside "
        f"{audit['distance_records']:,} pairwise-distance records. "
        "Model identifies idea sources, not human assignment to ChatGPT "
        "assistance. The ID field identifies idea records, without a verified "
        "link to c123 participants. "
    )
    if slug.endswith("_unadjusted"):
        target = (
            f"Cannot reproduce Table 2 (PDF p. 16): PIT {dimension}, "
            f"treatment M={stats['treatment_mean']:.2f}, "
            f"SD={stats['treatment_sd']:.2f}; "
            f"control M={stats['control_mean']:.2f}, "
            f"SD={stats['control_sd']:.2f}. "
            f"The expert-rated PIT {dimension} outcome is absent. "
        )
    elif slug.endswith("_ancova"):
        target = (
            f"Cannot reproduce the PIT {dimension} ANCOVA (PDF p. 16), "
            f"F(1,142)={stats['test']['value']:.2f}, "
            f"partial eta2={stats['paper_effect']['value']:.2f}. "
            f"Both expert-rated PIT {dimension} and the prior-ChatGPT-experience "
            "covariate are absent. "
        )
    else:
        require(slug.endswith("_group_by_task"), "Unrecognized estimate.")
        target = (
            "Cannot reproduce the group-by-task originality interaction "
            f"(PDF p. 17), F(1,142)={stats['test']['value']:.2f}, "
            f"p={stats['p_value']:.3f}, "
            f"partial eta2={stats['paper_effect']['value']:.2f}. "
            "There are no linked baseline UUT and experimental PIT expert "
            "ratings, original randomized arm indicators, or prior-experience "
            "covariates. Verbatim and humanized idea versions do not identify "
            "the paper's baseline and experimental tasks. "
        )
    return (
        target + counts + mismatch
        + "Ocsai/CAP automated scores and pairwise distances cannot replace the "
        "paper's expert ratings. No eligible rows or exclusions can be justified, "
        "so the reproduction prerequisite fails and no participant-level "
        "contrast, SD, or SE is computed."
    )


def main():
    extraction = load_json(EXTRACTION)
    require(extraction["cid"] == "c123", "Wrong extraction file.")
    estimates = extraction["estimates"]
    require(
        len(estimates) == 7 and {e["slug"] for e in estimates} == REVIEWED_SLUGS,
        "Extraction estimate set changed; reassessment is required.",
    )
    require(
        all(e["n_treatment"] == 77 and e["n_control"] == 68 for e in estimates),
        "The original printed arm counts changed.",
    )
    audit = audit_supplied_data()
    result = {
        "cid": "c123",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": [DATA.as_posix()],
        "results": [],
        "skipped": [
            {"slug": e["slug"], "reason": reason_for(e, audit)} for e in estimates
        ],
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    # Parse the actual file and verify full, nonduplicated estimate coverage.
    saved = load_json(OUTPUT)
    require(saved == result, "Written JSON did not round-trip.")
    covered = [r["slug"] for r in saved["results"] + saved["skipped"]]
    require(len(covered) == len(set(covered)) == 7, "Duplicate or missing slugs.")
    require(set(covered) == REVIEWED_SLUGS, "Estimate coverage mismatch.")
    print(json.dumps({
        "cid": saved["cid"],
        "n_results": len(saved["results"]),
        "n_reproduced": 0,
        "n_skipped": len(saved["skipped"]),
    }))


if __name__ == "__main__":
    main()
