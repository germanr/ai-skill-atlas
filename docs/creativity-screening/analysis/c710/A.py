"""Audit and reproduction gate for c710, analyst A.

Run with python -I -B using this file's absolute path. The only output file
is A.json. The deposit is parsed as JSON data; no deposited program is run
or imported. The repository README is inventoried but is not read.

The full 805-line manuscript conversion, including references and all
appendices, was read during the analysis. Relevant PDF pages were checked
with pymupdf. There are three eligible estimates, all requiring model
scores absent from the supplied deposit. Matching participant/task counts
alone does not reproduce any of these outcomes. Consequently the script
does not calculate surrogate outcomes, effect sizes, or standard errors.
"""

import sys

sys.dont_write_bytecode = True

from collections import Counter
import json
from pathlib import Path
import re

import pymupdf


WORKSPACE = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = WORKSPACE / "analysis/c710/A.py"
OUTPUT = WORKSPACE / "analysis/c710/A.json"
DEPOSIT = Path(
    "D:/projects/ai-skill-atlas/creativity-data/"
    "github-ctbaumler-personal_style_postedit/"
    "personal_style_postedit-unpacked/personal_style_postedit-HEAD"
)
MANIFEST = Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json")
EXTRACTION = WORKSPACE / "extraction/c710.json"
RETRIEVAL = WORKSPACE / "retrieval.json"
CODEBOOK = WORKSPACE.parent / "creativity-codebook.md"
SPEC = WORKSPACE / "extraction-spec.md"

LUAR = "s1_style_similarity_luar_postedited_vs_unassisted"
CISR = "s1_style_similarity_cisr_postedited_vs_unassisted"
COLA = "s1_cola_acceptability_postedited_vs_unassisted"

# Every input actually opened by this script is recorded, including the
# documents establishing the mapping, not just the participant data files.
read_files = []


def read_text(path):
    assert path.is_absolute()
    read_files.append(path.as_posix())
    return path.read_text(encoding="utf-8")


def read_json(path):
    return json.loads(read_text(path))


def nested_keys(value):
    """Inspect field names, without treating participants' text as code."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from nested_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_keys(child)


def main():
    extraction = read_json(EXTRACTION)
    retrieval = read_json(RETRIEVAL)["c710"]
    manifest = read_json(MANIFEST)
    assert "github-ctbaumler-personal_style_postedit" in manifest["deposits"]
    read_text(CODEBOOK)
    read_text(SPEC)
    markdown = read_text(Path(retrieval["md_path"]))
    assert "B.7.1 Linguistic Acceptability" in markdown
    assert "D User Study Interface" in markdown
    pdf_path = Path(retrieval["pdf_path"])
    read_files.append(pdf_path.as_posix())
    with pymupdf.open(pdf_path) as document:
        assert len(document) == 29
        pages = {
            number: document[number - 1].get_text()
            for number in (4, 5, 6, 13, 14, 16, 20, 21, 24)
        }

    estimates = {item["slug"]: item for item in extraction["estimates"]}
    assert set(estimates) == {LUAR, CISR, COLA}
    assert len(estimates) == len(extraction["estimates"])

    # Inventory names only. No archive, README, executable, model weights,
    # notebook, or author-written program is opened.
    inventory = sorted(path for path in DEPOSIT.rglob("*") if path.is_file())
    log_files = sorted((DEPOSIT / "logs").glob("*.json"))
    assert set(inventory) == set(log_files) | {DEPOSIT / "README.md"}
    assert len(log_files) == 81

    people = set()
    scenario_counts = Counter()
    output_counts = Counter()
    first_condition_counts = Counter()
    sequence_counts = Counter()
    ignored_response_records = 0
    unchanged_final_participants = 0
    response_field_names = set()
    possible_score_fields = set()
    participant_checks = []

    for path in log_files:
        record = read_json(path)
        person = record["user_info"]["id"]
        assert person == path.stem and person not in people
        people.add(person)
        conditions = record["user_info"]["conditions"]
        scenarios = record["user_info"]["scenarios"]
        assert len(conditions) == len(scenarios) == 6
        assert tuple(conditions) in ((1, 1, 1, 1, 0, 0), (0, 0, 1, 1, 1, 1))
        sequence_counts[tuple(conditions)] += 1

        rows = []
        for index, response in record["responses"].items():
            response_field_names.update(response)
            if "final_version" not in response:
                # One extra index 7 is a start-time event with no task,
                # condition, output, or score. It is not a seventh output.
                assert set(response) == {"start_time"}
                ignored_response_records += 1
                continue
            index = int(index)
            condition = response["model_generation_shown"]
            assert condition in (0, 1)
            assert conditions[index] == condition
            assert scenarios[index] == response["scenario"]
            assert isinstance(response["final_version"], str)
            assert response["final_version"].strip()
            assert isinstance(response["model_generation"], str)
            rows.append((index, response))
            scenario_counts[(response["scenario"], condition)] += 1
            output_counts[condition] += 1

        rows.sort(key=lambda pair: pair[0])
        assert [index for index, _ in rows] == list(range(6))
        chronological = sorted(rows, key=lambda pair: pair[1]["start_time"])
        assert [index for index, _ in chronological] == list(range(6))
        counts = Counter(response["model_generation_shown"] for _, response in rows)
        assert counts == {0: 2, 1: 4}
        first_condition_counts[conditions[0]] += 1
        assert record["mid_survey_1"]["condition"] == conditions[0]
        assert record["mid_survey_2"]["condition"] == conditions[-1]
        assert "submit_time" in record["post_survey"]

        treatment_rows = [r for _, r in rows if r["model_generation_shown"] == 1]
        # Appendix A.1 excludes never editing any draft, not individual
        # unchanged outputs. Every deposited writer has a nonempty treatment
        # edit event. One writer's saved final drafts equal the original
        # drafts despite recorded edits; retain that writer, consistent with
        # the deposited N=81 and every Table 9 task count.
        has_edit = any(
            event["added"] or event["removed"]
            for response in treatment_rows
            for event in response["edits"]
        )
        assert has_edit
        if all(r["final_version"] == r["model_generation"] for r in treatment_rows):
            unchanged_final_participants += 1
        participant_checks.append(counts)
        for key in nested_keys(record):
            if re.search(r"cola|luar|cisr|embedding|similarity|acceptab|cosine|score", key, re.I):
                possible_score_fields.add(key)

    assert possible_score_fields == set()
    assert response_field_names == {
        "start_time", "scenario", "model_generation_shown", "details",
        "model_generation", "submit_details_time", "final_version", "edits",
        "submit_final_text_time", "likert",
    }
    assert ignored_response_records == 1
    assert unchanged_final_participants == 1

    # Reproduce the printed sample composition directly against PDF Table 9.
    # These are count checks only, not successful outcome reproductions.
    labels = {
        "thank": "Thank-you letter",
        "apology": "Apology letter",
        "speech": "Wedding or birthday speech",
        "letter": "Catch-up letter",
        "condolence": "Letter of condolence",
        "reassurance": "Message of reassurance or encouragement",
        "wedding": "Wedding vows",
        "eulogy": "Eulogy, obituary, or tribute",
    }
    table_text = re.sub(r"\s+", " ", pages[24])
    count_checks = []
    for scenario, label in labels.items():
        match = re.search(re.escape(label) + r"\s+(\d+)\s+(\d+)", table_text)
        assert match is not None, label
        for condition, printed in enumerate(map(int, match.groups())):
            computed = scenario_counts[(scenario, condition)]
            count_checks.append({
                "statistic": f"Table 9: {label}, condition {condition}",
                "printed": printed,
                "computed": computed,
                "match": computed == printed,
            })
    assert all(check["match"] for check in count_checks)
    for estimate in estimates.values():
        assert estimate["n_total"] == len(people)
        assert estimate["n_treatment"] == len(people)
        assert estimate["n_control"] == len(people)

    n_people = len(people)
    mapping = (
        f"Count checks only, not outcome reproduction: {n_people} distinct user_info.id values "
        f"match the paper's {n_people} analyzed writers (PDF p. 13, Appendix A.1). "
        "responses[*].final_version is the completed text; model_generation_shown=1 "
        "identifies post-editing and =0 identifies unassisted writing, agreeing with "
        "user_info.conditions. All writers have four treatment and two control texts "
        f"({output_counts[1]} and {output_counts[0]} outputs); all 16 condition-by-task "
        "counts exactly match PDF p. 24, Table 9. No participant is additionally excluded. "
        "One start-time-only response is ignored; all writers completed six outputs and "
        "have recorded treatment edits. One writer has unchanged final drafts despite "
        "edit events and is retained. Response order agrees with start_time and the "
        f"mid-survey condition: {first_condition_counts[1]} writers had the AI block first "
        f"and {first_condition_counts[0]} had the control block first. "
    )
    skipped = []
    for slug, model, page in ((LUAR, "LUAR-MUD", 6), (CISR, "CISR", 16)):
        effect = estimates[slug]["stats"]["paper_effect"]
        reason = (
            f"Cannot reproduce H2a with {model}: the deposit contains only raw participant "
            "JSON logs and a README, with no saved style embeddings, pairwise cosine "
            "similarities, model weights, or analysis code. The texts are available and "
            "the model is identified (PDF p. 16), but the exact H2a text aggregation, "
            "pair selection/weighting, and effect-size standardization are not fully "
            "specified by Sections 5.2/6.2 and Appendix A.2. "
            f"The printed outcome check g={effect['value']:.2f}, 95% CI "
            f"[{effect['ci_lower']:.2f}, {effect['ci_upper']:.2f}], p=0.0002 "
            f"(PDF p. {page}) therefore cannot be recomputed; this is unavailable "
            "outcome data, not an observed numerical mismatch. No arm means are printed. "
            "Under the exact-procedure requirement for set-level diversity, both all "
            "and first_round are skipped; no participant SD or paired/HC2 SE is defined "
            "for this set-level measure. " + mapping
        )
        skipped.append({"slug": slug, "reason": reason})

    effect = estimates[COLA]["stats"]["paper_effect"]
    reason = (
        "Cannot reproduce the CoLA outcome: no linguistic-acceptability scores are "
        "stored in any of the 81 JSON logs, and the deposit supplies no scoring or "
        "analysis code. The likert fields are participants' self-reports about style "
        "and usability, not the model's CoLA outcome. PDF p. 21, Appendix B.7.1 cites "
        "Morris et al. (2020)/TextAttack but does not identify the exact fine-tuned "
        "checkpoint or scoring preprocessing. Neither arm means nor the standardizer "
        "and subtraction order for Hedges' g are specified. "
        f"Thus printed g={effect['value']:.2f}, 95% CI "
        f"[{effect['ci_lower']:.2f}, {effect['ci_upper']:.2f}], p<.0001 cannot be "
        "recomputed; this is unavailable outcome data, not an observed numerical "
        "mismatch. The negative printed g remains unresolved against the prose saying "
        "post-edited text is more acceptable. Matching counts does not pass the outcome "
        "reproduction gate. All participant means, SDs, differences and SEs are therefore "
        "unavailable, and both the paired all-round and HC2 first-block analyses are "
        "skipped. " + mapping
    )
    skipped.append({"slug": COLA, "reason": reason})

    result = {
        "cid": "c710",
        "analyst": "A",
        "script": SCRIPT.as_posix(),
        "data_files": list(dict.fromkeys(read_files)),
        "results": [],
        "skipped": skipped,
    }
    assert {entry["slug"] for entry in skipped} == set(estimates)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == result

    print(json.dumps({
        "audit": {
            "participants": n_people,
            "treatment_outputs": output_counts[1],
            "control_outputs": output_counts[0],
            "first_block_treatment_people": first_condition_counts[1],
            "first_block_control_people": first_condition_counts[0],
            "table9_counts_matched": len(count_checks),
            "ignored_start_only_records": ignored_response_records,
            "writers_with_unchanged_finals_but_edit_events": unchanged_final_participants,
            "outcome_score_fields_found": sorted(possible_score_fields),
        }
    }, ensure_ascii=True))
    print(json.dumps({
        "cid": "c710",
        "n_results": len(parsed["results"]),
        "n_reproduced": 0,
        "n_skipped": len(parsed["skipped"]),
    }))


if __name__ == "__main__":
    main()
