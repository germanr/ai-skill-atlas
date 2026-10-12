"""Independent analyst B audit for c002.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c002/B.py

The supplied repository contains the historical Organisciak scoring-model
evaluation data cited in Appendix A.1, footnote 7, not the randomized
Ashkinaze experiment. Reproduction is therefore unavailable for every
extracted estimate. This script audits all 55 CSV members, checks the archive
against the download manifest, verifies the printed source quotations in the
PDF, and records each estimate as skipped. PDF quotation checks are not
counted as reproduction from data. Historical participant counts are not
substituted for experimental participant counts.

No deposited code is read, imported, or executed. ZIP members are read into
memory, never extracted. Only B.json is written. In data_files, '::' separates
an absolute archive path from a CSV member read within that archive.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True

import pymupdf


BASE = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = BASE / "analysis/c002/B.py"
OUTPUT = BASE / "analysis/c002/B.json"
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
DEPOSIT_KEY = "github-massivetexts-llm_aut_study"
DEPOSIT = MANIFEST.parent / DEPOSIT_KEY
REPOSITORY_ZIP = DEPOSIT / "llm_aut_study.zip"
EVALUATION_ZIP = (
    DEPOSIT / "llm_aut_study-unpacked/llm_aut_study-HEAD/results/evaluation.zip"
)
DAVINCI_MEMBER = "evaluation/gt_main2/gpt-ft-davinci-1.csv"


def main():
    data_files = []

    def register(path):
        name = path.as_posix()
        if name not in data_files:
            data_files.append(name)

    def read_text(path):
        register(path)
        return path.read_text(encoding="utf-8")

    def read_bytes(path):
        register(path)
        return path.read_bytes()

    def compact(text):
        return re.sub(r"\s+", "", text)

    # Read the governing documents and the reconciled inventory only.
    codebook = read_text(BASE.parent / "creativity-codebook.md")
    specification = read_text(BASE / "extraction-spec.md")
    extraction = json.loads(read_text(BASE / "extraction/c002.json"))
    retrieval = json.loads(read_text(BASE / "retrieval.json"))["c002"]
    markdown = read_text(Path(retrieval["md_path"]))
    assert "## 7. Signs and counts" in codebook
    assert "## 11. Diversity effects" in codebook
    assert "Counts are people" in specification
    assert "SI 11.3" in markdown, "The supplementary ending must be present."
    assert extraction["cid"] == "c002"
    estimates = extraction["estimates"]
    assert len(estimates) == 46
    assert len({e["slug"] for e in estimates}) == len(estimates)

    # Verify study identity and all primary printed quotations against the PDF.
    # This is a provenance check, not a statistical reproduction.
    pdf_path = Path(retrieval["pdf_path"])
    register(pdf_path)
    with pymupdf.open(pdf_path) as pdf:
        pdf_pages = [page.get_text() for page in pdf]
    assert len(pdf_pages) == 29
    assert (
        "massivetexts/llm_aut_study/blob/main/results/evaluation.zip"
        in compact(pdf_pages[12])
    )
    assert "gt_main2/gpt-ft-davinci-1.csv" in pdf_pages[12]
    study_people = int(
        re.search(r"Unique Participants\s+(\d+)", pdf_pages[6]).group(1)
    )
    study_responses = int(
        re.search(r"Total Responses\s+(\d+)", pdf_pages[6]).group(1)
    )
    originality_observations = int(
        re.search(r"Observations\s+([\d,]+)", pdf_pages[25])
        .group(1)
        .replace(",", "")
    )
    evolution_observations = int(
        re.search(r"Observations\s+(\d+)", pdf_pages[24]).group(1)
    )
    assert (study_people, study_responses) == (844, 3414)
    assert (originality_observations, evolution_observations) == (3271, 362)
    for estimate in estimates:
        source = estimate["sources"][0]
        page = int(re.search(r"PDF p\. (\d+)", source["locator"]).group(1))
        assert compact(source["quote"]) in compact(pdf_pages[page - 1]), (
            estimate["slug"],
            "Printed source quotation differs from the supplied PDF.",
        )

    # Check the original repository ZIP and its already-unpacked data archive.
    manifest = json.loads(read_text(MANIFEST))
    expected = manifest["deposits"][DEPOSIT_KEY]["files"]["llm_aut_study.zip"]
    repository_bytes = read_bytes(REPOSITORY_ZIP)
    repository_sha256 = hashlib.sha256(repository_bytes).hexdigest()
    assert repository_sha256 == expected["sha256"]
    assert len(repository_bytes) == expected["bytes"]
    evaluation_bytes = read_bytes(EVALUATION_ZIP)
    with zipfile.ZipFile(io.BytesIO(repository_bytes)) as repository:
        nested = repository.read("llm_aut_study-HEAD/results/evaluation.zip")
        assert nested == evaluation_bytes
        # There are no separate experimental data files in the repository.
        allowed_data_suffixes = {
            ".csv", ".tsv", ".xlsx", ".sav", ".dta", ".rds", ".json", ".txt"
        }
        other_data = [
            item.filename
            for item in repository.infolist()
            if not item.is_dir()
            and Path(item.filename).suffix.lower() in allowed_data_suffixes
        ]
        assert other_data == [], "New data files require a fresh mapping audit."

    # Inspect every data row as data. Do not treat model names, corpus source
    # codes, few-shot nexamples, or response_num as randomized conditions/order.
    columns = set()
    row_count_distribution = Counter()
    member_profiles = []
    arm_label_hits = set()
    expected_arm_labels = {
        "control", "loexposure_disclosed", "loexposure_undisclosed",
        "hiexposure_disclosed", "hiexposure_undisclosed",
        "lowexposuredisclosed", "lowexposureundisclosed",
        "highexposuredisclosed", "highexposureundisclosed",
    }
    davinci = None
    with zipfile.ZipFile(io.BytesIO(evaluation_bytes)) as evaluation:
        members = sorted(
            item.filename for item in evaluation.infolist() if not item.is_dir()
        )
        assert len(members) == 55
        assert all(member.endswith(".csv") for member in members)
        for member in members:
            payload = evaluation.read(member)
            data_files.append(EVALUATION_ZIP.as_posix() + "::" + member)
            reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
            rows = list(reader)
            assert rows and reader.fieldnames
            assert {"id", "participant", "prompt", "target", "predicted", "src"}.issubset(
                reader.fieldnames
            )
            columns.update(reader.fieldnames)
            row_count_distribution[len(rows)] += 1
            for row in rows:
                assert None not in row, "CSV contains unexpected surplus fields."
                for value in row.values():
                    label = re.sub(r"[\s,]+", "", value or "").lower()
                    if label in expected_arm_labels:
                        arm_label_hits.add((member, label))
            profile = {
                "member": member,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "rows": len(rows),
                "participants": len({row["participant"] for row in rows}),
                "prompts": len({row["prompt"] for row in rows}),
                "sources": len({row["src"] for row in rows}),
                "columns": reader.fieldnames,
            }
            member_profiles.append(profile)
            if member == DAVINCI_MEMBER:
                davinci = profile

    assert columns == {
        "", "id", "model", "ncompletions", "nexamples", "participant",
        "predicted", "prompt", "proportion", "question", "response",
        "response_num", "split", "src", "target", "total_tokens",
    }, "Changed data schema requires a fresh mapping audit."
    assert not arm_label_hits
    assert davinci is not None
    assert (
        davinci["rows"], davinci["participants"], davinci["prompts"], davinci["sources"]
    ) == (3030, 1384, 21, 9)

    provenance = (
        "The supplied massivetexts/llm_aut_study deposit is the historical "
        "Organisciak classifier-evaluation dataset cited in PDF p. 13, "
        "Appendix A.1, footnotes 6-7, not this randomized experiment. "
        f"All {len(member_profiles)} CSV members were read. The cited "
        f"gt_main2/gpt-ft-davinci-1.csv has {davinci['rows']:,} responses from "
        f"{davinci['participants']:,} historical participants, "
        f"{davinci['prompts']} prompts and {davinci['sources']} source studies; "
        f"the experiment instead reports {study_people} people and "
        f"{study_responses:,} retained responses (PDF p. 7, Table 2). "
        "No CSV has the experimental arm assignments, response-chain IDs, "
        "or participant condition order. "
    )
    exclusions = (
        "The experiment's exclusions (two incorrectly shown responses and "
        "36 profane responses removed from 3,452, PDF pp. 17-18, SI 3) "
        "cannot be applied to this historical corpus. "
    )
    embedding_gap = (
        "The experimental response texts with their condition/item/chain "
        "positions and original SBERT embeddings are absent. The paper does "
        "not name the exact SBERT checkpoint. Scalar predictions from the "
        "historical scoring-model evaluations cannot replace those embeddings. "
        "The same texts and embedding procedure required by rule 5 cannot "
        "be recovered; this set-level outcome has no participant-level value. "
    )
    metric_names = {
        "median_pairwise": "median pairwise cosine distance",
        "mean_pairwise": "mean pairwise cosine distance",
        "mean_centroid": "mean cosine distance to the set centroid",
    }
    skipped = []
    for estimate in estimates:
        slug = estimate["slug"]
        stats = estimate["stats"]
        locator = estimate["sources"][0]["locator"]
        if slug.startswith("s1_originality_"):
            regression = stats["regression"]
            assert estimate["n_units"] == originality_observations
            reason = (
                f"Not reproduced: {locator} prints coefficient "
                f"{regression['coef']:.3f}, SE {regression['se']:.3f}, "
                f"t = {stats['test']['value']:.3f}; the full Table 18 model "
                f"has {originality_observations:,} output observations. "
                + provenance + exclusions
                + "The experimental originality scores, participant IDs, "
                "covariates and nested/crossed grouping variables needed "
                "for the printed mixed model are unavailable. The paper "
                "prints no arm means as an alternative reproduction target. "
                "The historical counts are a dataset-identity diagnostic, "
                "not recomputed experimental counts. No paired all-round "
                "or HC2 first_round result is computed: neither complete "
                "condition pairs nor each person's first condition can be "
                "identified. The historical response_num field is not "
                "experimental condition_order."
            )
        elif slug.startswith("s1_global_"):
            metric = next(name for name in metric_names if slug.startswith("s1_global_" + name + "_"))
            reason = (
                f"Not reproduced: {locator} prints a difference of "
                f"{stats['difference']:.6f} in {metric_names[metric]} "
                "multiplied by 100. "
                + provenance + embedding_gap
                + "SI 8.1 (PDF p. 21) requires retained experimental responses "
                "after chain trial six, 50 sampled ideas per condition/item "
                "in each of 50 Monte Carlo runs, and 10,000 paired sign "
                "permutations with Holm adjustment. The necessary input "
                "sets and original sampling information are unavailable. "
                "No arm levels, contrast, participant SD or SE is computed."
            )
        elif slug.startswith("s1_diversity_slope_"):
            metric = next(name for name in metric_names if slug.startswith("s1_diversity_slope_" + name + "_"))
            regression = stats["regression"]
            assert estimate["n_units"] == evolution_observations
            reason = (
                f"Not reproduced: {locator} prints a condition-by-chain-trial "
                f"coefficient of {regression['coef']:.3f} "
                f"(SE {regression['se']:.3f}) for {metric_names[metric]} "
                f"multiplied by 100, using {evolution_observations} idea pools. "
                + provenance + embedding_gap
                + "SI 8.3 (PDF p. 25) requires pooling retained experimental "
                "ideas by condition, item and response-chain trial, keeping "
                "trials after six, and fitting condition, trial, their "
                "interaction and pool size with an item random intercept. "
                "Those pools and their counts cannot be constructed. The "
                "printed observations are sets, not people; the interaction "
                "is a slope contrast, not a participant mean contrast. "
                "No substitute participant-level or first-round estimate "
                "is computed."
            )
        else:
            raise ValueError("Unmapped estimate: " + slug)
        skipped.append({"slug": slug, "reason": reason})

    # Nothing passes the required reproduction gate. Omit unidentifiable
    # results rather than manufacturing missing-value contrasts or claiming
    # that unrelated corpus counts are failed experimental replications.
    output = {
        "cid": "c002",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        "data_files": data_files,
        "results": [],
        "skipped": skipped,
    }
    assert {row["slug"] for row in skipped} == {e["slug"] for e in estimates}
    assert len(skipped) == len(estimates)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == output

    print(json.dumps({
        "archive_sha256_verified": repository_sha256,
        "csv_members_audited": len(member_profiles),
        "csv_row_count_distribution": dict(sorted(row_count_distribution.items())),
        "printed_source_quotes_verified_in_pdf": len(estimates),
        "experimental_results_reproduced": 0,
        "json_parses": True,
    }, ensure_ascii=True))
    print(json.dumps({
        "cid": "c002", "n_results": 0, "n_reproduced": 0, "n_skipped": len(skipped)
    }))


if __name__ == "__main__":
    main()
