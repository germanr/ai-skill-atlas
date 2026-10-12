"""Independent analyst B audit for c123.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c123/B.py

The full 742-line manuscript conversion, including Appendix 1, was read.
PDF pages 10, 11, 13, 16, 17 and 40 were independently text-extracted.
The sole supplied SAV is a different study's idea-level/model-scoring data.
Consequently no extracted contrast passes the prerequisite data-mapping and
replication checks. No outcome means, SDs, differences or SEs are estimated.

Only B.json is written by this script. No deposit code is executed. Python
bytecode writing is disabled, including when this script is run without -B.
"""

import sys
sys.dont_write_bytecode = True

import hashlib
import json
from pathlib import Path

import pyreadstat


ROOT = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = ROOT / "analysis/c123/B.py"
OUTPUT = ROOT / "analysis/c123/B.json"
EXTRACTION = ROOT / "extraction/c123.json"
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DATA = Path(
    r"D:/projects/ai-skill-atlas/creativity-data/osf-rn62y/"
    r"Stylistic Bias in Automated Assessment of Creativity in Large Language Models/"
    r"Stylistic Bias in Automated Assessment of Creativity in LLMs_Urban et al. 2025.sav"
)
EXPECTED_SHA256 = "38cb0fe6d2a28ef99377a4f204cbd2965d64b44890c775d1fb6ab98a949a2fcf"
EXPECTED_COLUMNS = {
    "ID", "Model", "Verbatim_Idea", "Humanized_Idea", "Ocsai_LLM",
    "Ocsai_Semantic", "CAP_CLAUS", "CAP_SemDis", "Ocsai_LLM_Humanized",
    "Ocsai_Semantic_Humanized", "CAP_CLAUS_Humanized",
    "CAP_SemDis_Humanized", "XXXXXXXXXXXXXXX", "Model_dist",
    "HUMANIZED_dist", "Distance",
}
EXPECTED_SLUGS = {
    "s1_quality_chatgpt_vs_control_unadjusted",
    "s1_elaboration_chatgpt_vs_control_unadjusted",
    "s1_originality_chatgpt_vs_control_unadjusted",
    "s1_quality_chatgpt_vs_control_ancova",
    "s1_elaboration_chatgpt_vs_control_ancova",
    "s1_originality_chatgpt_vs_control_ancova",
    "s1_originality_chatgpt_vs_control_group_by_task",
}


def read_json(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def printed_target(estimate):
    """Describe the printed target; these numbers are not recomputed results."""
    slug = estimate["slug"]
    stats = estimate["stats"]
    if slug.endswith("_unadjusted"):
        outcome = slug.split("_")[1]
        return (
            f"PDF p. 16, Table 2, PIT {outcome}: printed treatment M = "
            f"{stats['treatment_mean']:.2f}, SD = {stats['treatment_sd']:.2f}; "
            f"control M = {stats['control_mean']:.2f}, "
            f"SD = {stats['control_sd']:.2f}; "
            f"t({stats['test']['df']}) = {stats['test']['value']:.2f}; "
            f"d = {stats['paper_effect']['value']:.2f}. "
            f"There is no corresponding expert-rated {outcome} variable or "
            "valid arm subset from which these statistics can be reproduced."
        )
    df1, df2 = stats["test"]["df"]
    printed_test = (
        f"F({df1},{df2}) = {stats['test']['value']:.2f}, "
        f"partial eta squared = {stats['paper_effect']['value']:.2f}"
    )
    if slug.endswith("_ancova"):
        outcome = slug.split("_")[1]
        return (
            f"PDF p. 16 reports the PIT {outcome} ANCOVA adjusted for prior "
            f"ChatGPT experience: {printed_test}. Neither the expert-rated "
            f"{outcome} outcome nor the prior-experience covariate is present, "
            "so the printed adjusted effect cannot be reproduced."
        )
    return (
        f"PDF p. 17 reports the group-by-task originality interaction: "
        f"{printed_test}. Linked expert-rated baseline UUT and endpoint PIT "
        "originality scores, randomized group membership, and the "
        "prior-experience covariate are absent. The manuscript also does not "
        "fully specify its repeated-measures model or z-score reference "
        "distribution. The printed interaction cannot be reproduced. The "
        "fixed UUT-then-PIT task order is not a randomized-order crossover "
        "(PDF p. 10), so it does not justify paired or first-round AI results."
    )


def main():
    extraction = read_json(EXTRACTION)
    assert extraction["cid"] == "c123"
    assert {e["slug"] for e in extraction["estimates"]} == EXPECTED_SLUGS
    manifest = read_json(MANIFEST)
    entries = manifest["deposits"]["osf-rn62y"]["files"].values()
    entry = next(e for e in entries if Path(e["path"]) == DATA)
    digest = hashlib.sha256(DATA.read_bytes()).hexdigest()
    assert digest == entry["sha256"] == EXPECTED_SHA256, "Data changed; review required."
    assert DATA.stat().st_size == entry["bytes"]

    # Read only the SAV's data and metadata, never author-supplied code.
    data, meta = pyreadstat.read_sav(str(DATA))
    assert set(data.columns) == EXPECTED_COLUMNS
    assert data.shape == (6958, 16)
    idea_rows = data.loc[data["ID"].notna()]
    counts = idea_rows.groupby("Model")["ID"].count()
    assert idea_rows["ID"].is_unique
    assert len(idea_rows) == 240
    assert set(counts.index) == set(range(8))
    assert all(int(n) == 30 for n in counts)
    assert meta.variable_value_labels["Model"][0.0] == "human"
    assert meta.column_names_to_labels["XXXXXXXXXXXXXXX"] == (
        "= continues long form data for cosine distance"
    )
    assert data["Model_dist"].notna().all()
    assert data["Distance"].notna().all()
    assert int(data["Verbatim_Idea"].str.strip().ne("").sum()) == 240
    assert int(data["Humanized_Idea"].str.strip().ne("").sum()) == 210

    n_human_ideas = int(counts.loc[0.0])
    n_model_ideas = int(counts.drop(index=0.0).sum())
    n_models = len(counts) - 1
    common = (
        "Supplied data do not correspond to the c123 randomized PIT experiment. "
        f"The 2025 stylistic-bias SAV has {len(data):,} rows and "
        f"{len(data.columns)} columns: {len(idea_rows)} idea records with IDs "
        f"({n_human_ideas} labeled Model=0, human, and {n_model_ideas} labeled "
        f"with {n_models} LLM sources, 30 per model), alongside "
        f"{int(data['Distance'].notna().sum()):,} cosine-distance entries. "
        "Model identifies the source of an idea, not randomized ChatGPT "
        "assistance. Ocsai_LLM, Ocsai_Semantic, CAP_CLAUS, CAP_SemDis and "
        "their Humanized variants are automated scores, not the paper's "
        "expert PIT quality, elaboration or originality ratings. No "
        "participant-to-arm mapping, required expert ratings or "
        "prior-ChatGPT-experience variable is available. "
        f"The SAV SHA256 ({digest}) matches the download manifest. "
    )
    access_note = (
        " Direct lookups attempted during this audit at "
        "https://api.osf.io/v2/nodes/rn62y/, "
        "https://api.osf.io/v2/nodes/rn62y/files/osfstorage/, and the "
        "manuscript's named preregistration source "
        "https://api.osf.io/v2/registrations/q6wtu/ all failed with "
        "URLError/WinError 10013 (socket access forbidden). No additional "
        "data were retrieved."
    )
    skipped = []
    for estimate in extraction["estimates"]:
        assert estimate["n_treatment"] == 77
        assert estimate["n_control"] == 68
        counts_note = (
            f"The paper's {estimate['n_treatment']} treatment people and "
            f"{estimate['n_control']} control people (PDF p. 11) cannot be "
            "reconstructed from these idea/model records. The paper reports "
            "individual assignment and no exclusions (PDF p. 10); there is "
            "no supported exclusion or aggregation that maps this SAV to "
            "those arms. "
        )
        skipped.append({
            "slug": estimate["slug"],
            "reason": common + counts_note + printed_target(estimate)
            + " No participant-level treatment-control statistics were computed."
            + access_note,
        })

    # There is no valid analysis sample, so none of these estimates enters
    # results. This avoids fabricating replication comparisons from unrelated
    # automated scores or treating model outputs as randomized people.
    result = {
        "cid": "c123",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": [DATA.as_posix()],
        "results": [],
        "skipped": skipped,
    }
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    parsed = read_json(OUTPUT)
    assert parsed == result
    assert {e["slug"] for e in parsed["skipped"]} == EXPECTED_SLUGS
    summary = {
        "cid": parsed["cid"],
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            bool(r["reproduced"]) and all(x["match"] for x in r["reproduced"])
            for r in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
