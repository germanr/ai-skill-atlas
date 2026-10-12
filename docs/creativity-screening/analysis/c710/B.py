"""Independent analyst B audit for c710.

Run with: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c710/B.py

Only B.json is written. Deposited JSON is parsed as data; no deposited code
is imported or executed. The full paper markdown was read in consecutive
chunks, including references and Appendices A-D. Relevant PDF pages were
checked with PyMuPDF. Matching sample counts alone is not outcome replication.
The supplied logs contain no eligible model scores, so no effects are imputed.
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

WORKSPACE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
SCRIPT = WORKSPACE / "analysis/c710/B.py"
OUTPUT = WORKSPACE / "analysis/c710/B.json"
DEPOSIT_ID = "github-ctbaumler-personal_style_postedit"
DATA_ROOT = Path(
    r"D:/projects/ai-skill-atlas/creativity-data/github-ctbaumler-personal_style_postedit/"
    r"personal_style_postedit-unpacked/personal_style_postedit-HEAD"
)
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
READ_FILES = set()


def read_text(path):
    path = Path(path)
    assert path.is_absolute()
    READ_FILES.add(path.as_posix())
    return path.read_text(encoding="utf-8")


def read_json(path):
    return json.loads(read_text(path))


# An exhaustive allowed schema documents why the survey ratings and edit logs
# cannot be mistaken for the extracted CoLA or embedding outcomes. Fail on an
# added field/file so a future deposit with derived scores is reviewed again.
ALLOWED_KEYS = {
    "root": {"user_info", "responses", "pre_survey", "mid_survey_1", "mid_survey_2", "post_survey"},
    "root.user_info": {"id", "start_time", "conditions", "scenarios"},
    "root.responses.*": {
        "start_time", "scenario", "model_generation_shown", "details",
        "model_generation", "submit_details_time", "final_version", "edits",
        "submit_final_text_time", "likert",
    },
    "root.responses.*.edits[]": {"type", "position", "removed", "added", "timestamp"},
    "root.responses.*.likert": {
        "original-useable", "original-capture", "original-friend", "original-content",
        "edited-useable", "edited-capture", "edited-friend", "written-before",
        "voice-important", "edit_type", "edit_type_other",
    },
    "root.pre_survey": {"conf", "likely_i", "likely_ni"},
    "root.mid_survey_1": {"mental", "hard", "insecure", "performance", "temporal", "condition", "submit_time"},
    "root.mid_survey_2": {"mental", "hard", "insecure", "performance", "temporal", "condition", "submit_time"},
    "root.post_survey": {
        "conf", "likely_i", "likely_ni", "future_pref", "rankings", "gender",
        "trans", "hisp", "race", "age", "loe", "gender_table", "race_table",
        "age_table", "loe_table", "present_other", "mask_other", "feedback", "submit_time",
    },
}
LIST_PATHS = {
    "root.user_info.conditions", "root.user_info.scenarios",
    "root.responses.*.edits", "root.responses.*.likert.edit_type",
}


def check_schema(value, path="root"):
    if isinstance(value, dict):
        if path == "root.responses":
            assert all(key.isdigit() for key in value), "Unexpected response key"
        else:
            assert path in ALLOWED_KEYS, "Unexpected nested data at " + path
            assert set(value) <= ALLOWED_KEYS[path], "New field at " + path
        for key, child in value.items():
            check_schema(child, path + "." + ("*" if path == "root.responses" else key))
    elif isinstance(value, list):
        assert path in LIST_PATHS, "Unexpected array at " + path
        for child in value:
            check_schema(child, path + "[]")
    else:
        assert value is None or isinstance(value, (str, int, float, bool))


def main():
    extraction = read_json(WORKSPACE / "extraction/c710.json")
    retrieval = read_json(WORKSPACE / "retrieval.json")["c710"]
    manifest = read_json(MANIFEST)
    read_text(WORKSPACE.parent / "creativity-codebook.md")
    read_text(WORKSPACE / "extraction-spec.md")
    markdown = read_text(retrieval["md_path"])
    assert "Figure 21" in markdown and "B.7.1" in markdown
    assert extraction["cid"] == "c710"
    assert DEPOSIT_ID in manifest["papers"]["c710"]
    manifest_deposit = manifest["deposits"][DEPOSIT_ID]
    assert manifest_deposit["source_url"] == "https://github.com/ctbaumler/personal_style_postedit"
    unpacked = manifest_deposit["files"]["personal_style_postedit.zip"]["unpacked"]
    assert Path(unpacked) == DATA_ROOT.parent

    pdf_path = Path(retrieval["pdf_path"])
    READ_FILES.add(pdf_path.as_posix())
    with pymupdf.open(str(pdf_path)) as doc:
        assert len(doc) == 29
        pdf_pages = {i + 1: page.get_text() for i, page in enumerate(doc)}
        pdf_links = {
            link["uri"] for page in doc for link in page.get_links() if link.get("uri")
        }
    assert "leaving 81 participants" in pdf_pages[13]
    assert "1.42" in pdf_pages[6] and "1.03" in pdf_pages[16]
    assert "\u22121.29" in pdf_pages[21]
    assert "https://huggingface.co/rrivera1849/LUAR-MUD" in pdf_links
    assert "https://huggingface.co/AnnaWegmann/Style-Embedding" in pdf_links

    # Table 9 is parsed directly from PDF p. 24, not inferred from task totals.
    table9_labels = {
        "thank": r"Thank-you letter",
        "apology": r"Apology letter",
        "speech": r"Wedding or birthday speech",
        "letter": r"Catch-up letter",
        "condolence": r"Letter of condolence",
        "reassurance": r"Message of reassurance or\s+encouragement",
        "wedding": r"Wedding vows",
        "eulogy": r"Eulogy, obituary, or tribute",
    }
    printed_task_counts = {}
    for scenario, label in table9_labels.items():
        match = re.search(label + r"\s+(\d+)\s+(\d+)", pdf_pages[24])
        assert match, "Cannot recover Table 9 row: " + scenario
        printed_task_counts[scenario] = {0: int(match[1]), 1: int(match[2])}

    inventory = sorted(p for p in DATA_ROOT.rglob("*") if p.is_file())
    logs = sorted((DATA_ROOT / "logs").glob("*.json"))
    assert len(logs) == 81
    assert set(inventory) == set(logs) | {DATA_ROOT / "README.md"}, "Deposit contents changed"
    # README.md is inventoried only; only deposited JSON data files are read.
    ids = set()
    task_counts = defaultdict(Counter)
    outputs = Counter()
    first_conditions = Counter()
    completed_people = 0
    edited_people = 0
    no_net_change_people = 0
    extra_nonoutputs = []
    sequences = Counter()

    for path in logs:
        data = read_json(path)
        check_schema(data)
        info = data["user_info"]
        assert info["id"] == path.stem and info["id"] not in ids
        ids.add(info["id"])
        assert len(info["conditions"]) == len(info["scenarios"]) == 6
        assigned_indices = [str(i) for i in range(6)]
        assert set(assigned_indices) <= set(data["responses"])
        for key in set(data["responses"]) - set(assigned_indices):
            row = data["responses"][key]
            assert set(row) == {"start_time"}, "Unexpected additional output"
            extra_nonoutputs.append((path.name, key))
        rows = [data["responses"][key] for key in assigned_indices]
        conditions = tuple(row["model_generation_shown"] for row in rows)
        assert list(conditions) == info["conditions"]
        assert [row["scenario"] for row in rows] == info["scenarios"]
        assert conditions in {(1, 1, 1, 1, 0, 0), (0, 0, 1, 1, 1, 1)}
        assert [row["start_time"] for row in rows] == sorted(row["start_time"] for row in rows)
        assert data["mid_survey_1"]["condition"] == conditions[0]
        assert data["mid_survey_2"]["condition"] == conditions[-1]
        assert all(isinstance(row["final_version"], str) and row["final_version"].strip()
                   and row["submit_final_text_time"] and row["likert"] for row in rows)
        assert data["post_survey"]["submit_time"]
        completed_people += 1
        treatment_rows = [row for row in rows if row["model_generation_shown"] == 1]
        # The paper excludes people who NEVER edited, not every unchanged output.
        # Edit events demonstrate participation even if final text equals draft.
        any_edit = any(event["added"] or event["removed"]
                       for row in treatment_rows for event in row["edits"])
        assert any_edit, "Published retained sample includes a person with no edit events"
        edited_people += 1
        no_net_change_people += not any(
            row["final_version"] != row["model_generation"] for row in treatment_rows
        )
        first_conditions[conditions[0]] += 1
        sequences[conditions] += 1
        for row in rows:
            arm = row["model_generation_shown"]
            outputs[arm] += 1
            task_counts[row["scenario"]][arm] += 1

    n = len(ids)
    assert n == completed_people == edited_people == extraction["studies"][0]["n_analyzed"] == 81
    assert dict(task_counts) == printed_task_counts
    assert outputs == Counter({1: 324, 0: 162})
    assert first_conditions == Counter({1: 31, 0: 50})
    assert no_net_change_people == 1
    assert extra_nonoutputs == [("417a64ff-e3b5-45c1-a926-83e8b3897840.json", "7")]

    estimates = extraction["estimates"]
    expected_slugs = {
        "s1_style_similarity_luar_postedited_vs_unassisted",
        "s1_style_similarity_cisr_postedited_vs_unassisted",
        "s1_cola_acceptability_postedited_vs_unassisted",
    }
    assert {e["slug"] for e in estimates} == expected_slugs
    for estimate in estimates:
        assert estimate["n_treatment"] == estimate["n_control"] == estimate["n_total"] == n
        assert estimate["within_person"] == "paired"

    task_check = "; ".join(
        f"{scenario}: control {task_counts[scenario][0]}, treatment {task_counts[scenario][1]}"
        for scenario in table9_labels
    )
    sample_note = (
        f"Sample-count reproduction succeeds: printed n=81, computed {n} unique people, "
        f"with {outputs[1]} treatment and {outputs[0]} control final texts. All eight "
        f"task rows reproduce PDF p. 24, Table 9 ({task_check}). Map user_info.id to person, "
        "responses.0 through responses.5 to assigned tasks, model_generation_shown=1 "
        "to treatment and =0 to control, and final_version to the analyzed text in both "
        "conditions. model_generation is the original draft, including drafts stored "
        "but not shown in control; it is not the control outcome. All 81 posted people "
        "completed six tasks and the post-survey and have at least one logged treatment "
        "edit, consistent with the retained-sample criteria in Appendix A.1 (PDF p. 13). "
        "One person has unchanged final drafts but has edit events; do not exclude that "
        "person or individual unchanged treatment outputs. The 19 excluded recruits "
        "are not supplied, so their exclusions cannot be independently reconstructed. "
        "Ignore the start_time-only response 7 in 417a64ff-e3b5-45c1-a926-83e8b3897840.json; "
        "it is outside the six assigned tasks and contains no output. Condition lists, "
        "task timestamps, and mid-survey condition flags agree. First-condition counts "
        f"are {first_conditions[1]} treatment-first and {first_conditions[0]} control-first "
        "(computed from logs; no first-round counts are printed). These count checks "
        "alone do not establish reproduction of an outcome. "
    )
    skipped = []
    for estimate in estimates:
        slug = estimate["slug"]
        effect = estimate["stats"]["paper_effect"]
        printed = (
            f"Printed Hedges' g={effect['value']:.2f}, 95% CI "
            f"[{effect['ci_lower']:.2f}, {effect['ci_upper']:.2f}], "
            f"p={estimate['stats']['p_value']}; computed outcome effect is unavailable. "
        )
        if estimate["construct"] == "diversity":
            model = "LUAR-MUD" if "_luar_" in slug else "CISR"
            checkpoint = (
                "rrivera1849/LUAR-MUD" if model == "LUAR-MUD"
                else "AnnaWegmann/Style-Embedding"
            )
            reason = (
                f"Skipped under the exact-procedure rule for set-level diversity. {printed}"
                f"The paper identifies {model} and links the {checkpoint} checkpoint "
                "(PDF p. 16), and the source final texts are available. However, the "
                "downloaded deposit contains only raw interaction/survey JSON logs and "
                "a README, with no stored embeddings, pairwise similarity scores, model "
                "files, or analysis scripts. The paper does not fully specify the H2a "
                "embedding input aggregation, encoding settings, and pair construction "
                "needed to establish an identical reconstruction. Appendix A.2 (PDF "
                "pp. 13-14) describes concatenated controls and task matching using H1a "
                "as its example; it does not provide a complete H2a implementation. "
                "Neither numerical arm means nor the exact number of analyzed pairs is "
                "printed (PDF pp. 6-7 and 16). Therefore the effect cannot be reproduced "
                "at printed precision and no replacement embedding metric is computed. "
                "This set/pair outcome has no participant-level value, so no participant "
                "SD or paired/HC2 standard error is fabricated. Neither all-round nor "
                "first-round outcome results can be reported. "
            )
        else:
            reason = (
                f"Skipped because the published CoLA outcome cannot be reproduced. {printed}"
                "No CoLA probabilities, logits, sentence scores, or other linguistic "
                "acceptability values occur anywhere in the 81 JSON logs, and the deposit "
                "contains no model or scoring/analysis scripts. Appendix B.7.1 (PDF p. 21) "
                "cites a Morris et al. (2020) model fine-tuned on CoLA but gives no exact "
                "checkpoint, scoring/preprocessing settings, or document/sentence "
                "aggregation procedure. The PDF contains model links for style "
                "embeddings but none identifying the CoLA classifier. Raw texts cannot "
                "be substituted for that missing scored outcome, and the available "
                "likert.edited-useable, edited-capture, and edited-friend variables are "
                "participant self-reports, not CoLA scores. No arm means or raw "
                "difference are printed. The negative g is retained as printed; the "
                "paper's prose says treatment is more acceptable, but subtraction order "
                "cannot be checked without the scoring/analysis inputs. The required "
                "outcome-reproduction gate therefore fails, so no paired all-round or "
                "HC2 first-round effect, mean, SD, or SE is computed. "
            )
        skipped.append({"slug": slug, "reason": reason + sample_note})

    result = {
        "cid": "c710",
        "analyst": "B",
        "script": SCRIPT.as_posix(),
        # Includes all source documents and raw data actually read, for provenance.
        "data_files": sorted(READ_FILES),
        "results": [],
        "skipped": skipped,
    }
    assert len(skipped) == len(estimates)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        confirmed = json.load(fh)
    assert confirmed == result
    print(json.dumps({
        "cid": confirmed["cid"],
        "n_results": len(confirmed["results"]),
        "n_reproduced": 0,
        "n_skipped": len(confirmed["skipped"]),
    }))


if __name__ == "__main__":
    main()
