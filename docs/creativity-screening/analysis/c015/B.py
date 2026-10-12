"""Independent c015 analyst B audit.

Run with python -I -B followed by this absolute script path.
Only B.json is written. Deposit scripts and notebooks are read as inert text;
none are run, imported, compiled, or evaluated. No network requests, package
installation, model downloads, or temporary files are needed.

The two keyword outcomes are raw SET COUNTS in the reconciled extraction.
Rule 5 preserves those units: the mean fields below hold the recomputed arm
levels (counts), while participant SDs and SEs remain null. A binary keyword
rate would be a different outcome. The other 54 outcomes cannot be reproduced
without the exact Universal Sentence Encoder v4 embeddings.
"""

import sys
sys.dont_write_bytecode = True

import csv
import hashlib
import importlib.util
import io
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

SCREEN = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA = Path(r"D:/projects/ai-skill-atlas/creativity-data")
ZF = DATA / "osf-zf3s2"
RZ = DATA / "osf-rzn87"
SUPPLEMENT = Path(r"D:/projects/ai-skill-atlas/creativity-supplements/c015/41562_2025_2173_MOESM1_ESM.pdf")
SCRIPT = SCREEN / "analysis/c015/B.py"
OUTPUT = SCREEN / "analysis/c015/B.json"
MODEL_URL = "https://tfhub.dev/google/universal-sentence-encoder/4"

READ_FILES = []
CONTENT = {}


def read_bytes(path):
    path = Path(path)
    assert path.is_absolute()
    name = path.as_posix()
    if name not in CONTENT:
        CONTENT[name] = path.read_bytes()
        READ_FILES.append(name)
    return CONTENT[name]


def read_text(path):
    return read_bytes(path).decode("utf-8-sig")


def read_json(path):
    return json.loads(read_text(path))


def read_csv(path, header=True):
    stream = io.StringIO(read_text(path), newline="")
    return list(csv.DictReader(stream) if header else csv.reader(stream))


def normalize_linkage(text):
    """Repair observed UTF-8/Windows-1252 artifacts for linkage ONLY.

    Headerless pool texts used for keyword counting retain their original
    characters. No normalized or corrected texts are used as model inputs.
    Counter comparison preserves multiplicity when two people submit the
    same idea. NFKC also equates an ellipsis with three full stops.
    """
    chars = "\u00a0\u2018\u2019\u2013\u2014\u2026\u201c\u201d\u00e9\U0001f60a"
    for char in chars:
        pieces = []
        for byte in char.encode("utf-8"):
            try:
                pieces.append(bytes([byte]).decode("cp1252"))
            except UnicodeDecodeError:
                pieces.append(chr(byte))
        text = text.replace("".join(pieces), char)
    return " ".join(unicodedata.normalize("NFKC", text).split())


def check(statistic, printed, computed):
    # All statistics reproduced here are exact integer counts, so no
    # rounding tolerance is appropriate.
    return {"statistic": statistic, "printed": printed,
            "computed": computed, "match": printed == computed}


def empty_computed():
    return {"n_treatment": None, "n_control": None,
            "treatment_mean": None, "treatment_sd": None,
            "control_mean": None, "control_sd": None,
            "difference": None, "difference_se": None,
            "se_type": None, "n_clusters": None}


extraction = read_json(SCREEN / "extraction/c015.json")
retrieval = read_json(SCREEN / "retrieval.json")["c015"]
manifest = read_json(DATA / "manifest.json")
read_text(SCREEN.parent / "creativity-codebook.md")
read_text(SCREEN / "extraction-spec.md")
read_text(retrieval["md_path"])
read_text(SUPPLEMENT.with_suffix(".md"))

# Main text and complete supplementary information were read in chunks during
# the audit. Check the PDF evidence used for the retained numerical results.
import pymupdf
with pymupdf.open(stream=read_bytes(retrieval["pdf_path"]), filetype="pdf") as doc:
    article_page = " ".join(doc[0].get_text().split())
    assert "20 out of 96" in article_page
    assert "only 7" in article_page and "12 in the human-only condition" in article_page
with pymupdf.open(stream=read_bytes(SUPPLEMENT), filetype="pdf") as doc:
    supplement_pages = [" ".join(page.get_text().split()) for page in doc]
    assert "100; GPT-aided n = 96" in supplement_pages[2].replace("GPT- aided", "GPT-aided")
    assert "n = 95; GPT-aided n = 96" in supplement_pages[3].replace("GPT- aided", "GPT-aided")
    assert "95; GPT-aided n = 99" in supplement_pages[4].replace("GPT- aided", "GPT-aided")

# Read the notebook solely as JSON/text to confirm model, preprocessing,
# source-file mapping, and absence of saved outputs. Never execute any cell.
notebook = read_json(ZF / "analysis.ipynb")
assert MODEL_URL in "".join(notebook["cells"][0]["source"])
assert all(not cell.get("outputs", []) for cell in notebook["cells"])
notebook_config = "".join(notebook["cells"][1]["source"])
missing_modules = [name for name in ("tensorflow", "tensorflow_hub")
                   if importlib.util.find_spec(name) is None]

# Inspect all supplied reanalysis CSVs. Only these CSVs and the original
# Exp2A CSV are read as data; the other deposits' unrelated ratings and CR6
# outcomes are not substituted for c015's diversity measures.
CSV = {}
for path in sorted(ZF.rglob("*.csv")):
    relative = path.relative_to(ZF).as_posix()
    CSV[relative] = read_csv(path, header=(".main." in path.name or ".link." in path.name))

CONFIG = {
    "S1": {
        "folder": "exp_1", "main": "Exp1.main.cleaned.csv", "text": "idea_text_raw",
        "pools": {
            "t": ("chatbot_ideas.csv", {"Condition": "Chatbot"}),
            "c": ("control_ideas.csv", {"Condition": "Control"}),
        },
    },
    "S2": {
        "folder": "exp_2a", "main": "Exp2A.main.full.csv", "text": "idea_text_raw",
        "pools": {
            "t": ("gpt_ideas.csv", {"Condition": "Chatbot"}),
            "web": ("google_ideas.csv", {"Condition": "Google"}),
            "human": ("human_ideas.csv", {"Condition": "None"}),
        },
    },
    "S3": {
        "folder": "exp_2b", "main": "Exp2B.main.cleaned.csv", "text": "idea_text_raw",
        "pools": {
            "t": ("chatbot_human.csv", {"Condition": "ChatbotHuman"}),
            "c": ("human_only.csv", {"Condition": "HumanOnly"}),
        },
    },
    "S4": {
        "folder": "exp_3", "main": "Exp3.main.cleaned.csv", "text": "idea_text_raw",
        "pools": {
            "t": ("chatbot_ideas.csv", {"Condition": "Chatbot"}),
            "c": ("google_ideas.csv", {"Condition": "Google"}),
        },
    },
    "S5": {
        "folder": "exp_4", "main": "Exp4.main.cleaned.csv", "text": "idea",
        "pools": {
            "t_low": ("chatbot_ideas_low.csv", {"Condition": "Chatbot", "NumCon": "Low"}),
            "c_low": ("google_ideas_low.csv", {"Condition": "Google", "NumCon": "Low"}),
            "t_high": ("chatbot_ideas_high.csv", {"Condition": "Chatbot", "NumCon": "High"}),
            "c_high": ("google_ideas_high.csv", {"Condition": "Google", "NumCon": "High"}),
        },
    },
    "S6": {
        "folder": "exp_5", "main": "Exp5.main.cleaned.csv", "text": "idea",
        "pools": {
            "t_base": ("chatbot_empathy_base_ideas.csv", {"Condition": "Chatbot", "Empathy": "Baseline"}),
            "c_base": ("google_empathy_base_ideas.csv", {"Condition": "Google", "Empathy": "Baseline"}),
            "t_high": ("chatbot_empathy_high_ideas.csv", {"Condition": "Chatbot", "Empathy": "High"}),
            "c_high": ("google_empathy_high_ideas.csv", {"Condition": "Google", "Empathy": "High"}),
        },
    },
}

POOLS = {}
for study, config in CONFIG.items():
    participants = CSV[config["folder"] + "/" + config["main"]]
    pooled_people = []
    for name, (file_name, criteria) in config["pools"].items():
        relative = config["folder"] + "/" + file_name
        assert "./" + relative in notebook_config
        selected = [row for row in participants
                    if all(row[key] == value for key, value in criteria.items())]
        source_rows = CSV[relative]
        assert all(len(row) == 1 for row in source_rows)
        texts = [row[0].strip() for row in source_rows]
        assert all(texts)
        worker_ids = [row["workerId"] for row in selected]
        response_ids = [row["ResponseId"] for row in selected]
        assert len(worker_ids) == len(set(worker_ids)) == len(texts)
        assert len(response_ids) == len(set(response_ids)) == len(texts)
        assert all(value not in ("", "NA") for value in worker_ids + response_ids)
        main_texts = [row[config["text"]] for row in selected]
        assert Counter(map(normalize_linkage, texts)) == Counter(map(normalize_linkage, main_texts)), relative
        pooled_people.extend(worker_ids)
        POOLS[(study, name)] = {
            "n": len(worker_ids), "texts": texts,
            "rows": selected, "file": relative,
        }
    # All analyzed human arms are between persons. In S3 the 100 model-only
    # rows are intentionally absent from this participant check.
    assert len(pooled_people) == len(set(pooled_people))

# Independently reconstruct Exp2A exclusions using the original raw survey.
# The six exclusion IDs are extracted as literal text, never evaluated.
rmd = read_text(RZ / "Exp2A/Exp2A.analyze.Rmd")
exclusion_section = rmd.split("# remove nonsensical responses", 1)[1].split("write.csv", 1)[0]
excluded_ids = set(re.findall(r'"([a-f0-9]{24})"', exclusion_section))
assert len(excluded_ids) == 6
raw = read_csv(RZ / "Exp2A/Exp2A.main.qualtrics.csv")
valid = [row for row in raw if len(row["PROLIFIC_PID"]) >= 13 and len(row["mturk"]) >= 13]
complete = [row for row in valid if row["Finished"] == "1"
            and row["age"] not in ("", "NA") and row["gender_f"] not in ("", "NA")]
attentive = [row for row in complete if row["attention_check_2"] == "2"]
retained = [row for row in attentive if row["PROLIFIC_PID"] not in excluded_ids]
posted = CSV["exp_2a/Exp2A.main.full.csv"]
assert len(retained) == len(posted) == 291
assert {row["PROLIFIC_PID"] for row in retained} == {row["workerId"] for row in posted}
assert {row["ResponseId"] for row in retained} == {row["ResponseId"] for row in posted}
posted_by_response = {row["ResponseId"]: row for row in posted}
for row in retained:
    matching = posted_by_response[row["ResponseId"]]
    assert row["PROLIFIC_PID"] == matching["workerId"]
    assert row["Condition"] == matching["Condition"]
    assert normalize_linkage(row["idea"]) == normalize_linkage(matching["idea_text_raw"])
assert all(row[key] not in ("", "NA") for row in posted
           for key in ("ORIGINALITY", "APPROPRIATENESS", "OVERALL"))

# Verify hashes of every deposit file actually read against the supplied
# manifest. Hash validation is data-integrity checking, not code execution.
hashed_files = 0
for deposit in ("osf-zf3s2", "osf-rzn87", "osf-835bg"):
    for entry in manifest["deposits"][deposit]["files"].values():
        name = Path(entry["path"]).as_posix()
        if name in CONTENT:
            assert hashlib.sha256(CONTENT[name]).hexdigest() == entry["sha256"], name
            assert len(CONTENT[name]) == entry["bytes"], name
            hashed_files += 1
assert hashed_files == len(CSV) + 3  # all CSVs, notebook, original raw CSV, Rmd


def pools_for(estimate):
    study = estimate["study_id"]
    slug = estimate["slug"]
    if study == "S2":
        return POOLS[(study, "t")], POOLS[(study, "human" if slug.endswith("_vs_human") else "web")]
    if study == "S5":
        cell = "low" if "_low_" in slug else "high"
        return POOLS[(study, "t_" + cell)], POOLS[(study, "c_" + cell)]
    if study == "S6":
        cell = "base" if "_base_" in slug else "high"
        return POOLS[(study, "t_" + cell)], POOLS[(study, "c_" + cell)]
    return POOLS[(study, "t")], POOLS[(study, "c")]


def skip_reason(estimate, treatment, control):
    slug = estimate["slug"]
    if "unique_fraction" in slug:
        threshold = {"075": "0.75", "080": "0.80", "085": "0.85"}[slug.split("_")[3]]
        procedure = (
            "The measure is the pool fraction of ideas not overlapping earlier rows "
            "at cosine similarity >= " + threshold + ". It is a set-level statistic "
            "and has no participant-level SD or HC2 SE under rule 5. "
        )
    elif "centroid_similarity" in slug:
        procedure = (
            "The outcome needs each idea's cosine similarity to the mean embedding "
            "of all other ideas in its condition. The required per-idea scores "
            "cannot be recovered from the rounded published arm means. "
        )
    elif "pairwise_similarity" in slug:
        procedure = (
            "The outcome needs each idea's mean cosine similarity to every other "
            "idea in its condition, excluding self-pairs. The required per-idea "
            "scores cannot be recovered from the rounded published arm means. "
        )
    elif "mst_distance" in slug:
        procedure = (
            "The outcome needs the mean MST edge weight using distances of one "
            "minus cosine similarity. Edges do not supply participant outcomes; "
            "participant SDs or HC2 SEs are not defined for this set statistic. "
        )
    else:
        raise AssertionError("Unmapped estimate: " + slug)
    unavailable = (
        "Exact reproduction requires " + MODEL_URL + " (analysis.ipynb, cell 0). "
        "The supplied reanalysis CSVs contain idea texts and survey/rating data, "
        "but no saved embeddings, similarity scores, or model weights; all "
        "notebook outputs are empty. "
    )
    if missing_modules:
        unavailable += "This Python environment lacks " + ", ".join(missing_modules) + ". "
    unavailable += (
        "The exact encoder was therefore not available for recomputation under "
        "the restriction to write only B.py and B.json. No substitute encoder "
        "or values inferred from the paper were used. "
    )
    count_note = (
        "Mapped one submission per distinct workerId/ResponseId: treatment "
        + treatment["file"] + " (" + str(treatment["n"]) + " people), control "
        + control["file"] + " (" + str(control["n"]) + " people). "
    )
    mismatches = []
    for arm, pool in (("treatment", treatment), ("control", control)):
        printed = estimate["n_" + arm]
        if printed is not None and printed != pool["n"]:
            mismatches.append(arm + " n printed " + str(printed) + ", data " + str(pool["n"]))
    if mismatches:
        count_note += (
            "Reproduction also fails on counts: " + "; ".join(mismatches)
            + ". The reversal is present in Supplementary Table 1, PDF p. 5, "
            "and was checked with PDF text and table extraction. "
        )
    elif estimate["n_treatment"] is None or estimate["n_control"] is None:
        count_note += (
            "These arm counts are not printed, so they cannot be marked as "
            "reproduced; the full experiment contains "
            + str(len(CSV[CONFIG[estimate["study_id"]]["folder"] + "/" + CONFIG[estimate["study_id"]]["main"]]))
            + " people, agreeing with the printed experiment total. "
        )
    else:
        count_note += "Both arm counts match the printed counts exactly. "
    return procedure + unavailable + count_note + "No outcome statistics were computed because the outcome could not be reproduced first."


results = []
skipped = []
for estimate in extraction["estimates"]:
    treatment, control = pools_for(estimate)
    if "sprinkler_count" not in estimate["slug"]:
        skipped.append({"slug": estimate["slug"],
                        "reason": skip_reason(estimate, treatment, control)})
        continue

    # Count submissions containing the case-insensitive literal substring.
    # This includes the plural 'sprinklers'. Each submission contributes at
    # most one count, regardless of repeated mentions. Exact singular-only
    # word matching would give 11, not the printed 12, in the human arm.
    treatment_count = sum("sprinkler" in text.lower() for text in treatment["texts"])
    control_count = sum("sprinkler" in text.lower() for text in control["texts"])
    for pool, count in ((treatment, treatment_count), (control, control_count)):
        assert count == sum("sprinkler" in row["idea_text_raw"].lower() for row in pool["rows"])
        condition = pool["rows"][0]["Condition"]
        assert count == sum("sprinkler" in row["idea"].lower()
                            for row in retained if row["Condition"] == condition)

    reproduction = [
        check("n_treatment", estimate["n_treatment"], treatment["n"]),
        check("n_control", estimate["n_control"], control["n"]),
        check("treatment_mean", estimate["stats"]["treatment_mean"], treatment_count),
        check("control_mean", estimate["stats"]["control_mean"], control_count),
    ]
    computed = empty_computed()
    if all(item["match"] for item in reproduction):
        computed.update({
            "n_treatment": treatment["n"], "n_control": control["n"],
            "treatment_mean": treatment_count, "control_mean": control_count,
            "difference": treatment_count - control_count,
        })
    notes = (
        "SET-LEVEL EXCEPTION (rule 5): treatment_mean and control_mean retain "
        "the extraction's raw arm totals of submissions containing 'sprinkler', "
        "not participant-level averages or percentages. Difference is treatment "
        "minus control in submissions; positive means more keyword convergence. "
        "There is one observed set per arm. Participant SDs, difference_se, "
        "se_type and n_clusters are null because a participant HC2 regression "
        "would estimate a different, binary-rate outcome. No HC2 SE is assigned "
        "to the raw set-count difference. "
        "Reproduction: main PDF p. 1 (printed p. 1107) gives the keyword totals; "
        "Supplementary Table 1, PDF pp. 3-4, gives the person counts. "
        "Headerless UTF-8 pool CSVs were read in their posted order, column 0, "
        "with outer whitespace stripped, as in the notebook. Each submission "
        "is counted once if its lowercase text includes 'sprinkler', including "
        "the plural 'sprinklers'. The notebook does not give a separate keyword "
        "routine; this transparent text rule reproduces every printed keyword "
        "count exactly. Case-sensitive matching misses one ChatGPT idea, and "
        "singular-only whole-word matching misses one human idea. "
        "Treatment source: " + treatment["file"] + "; control source: "
        + control["file"] + ". Both pools link to distinct participant rows in "
        "exp_2a/Exp2A.main.full.csv through Condition and idea_text_raw. The "
        "single ChatGPT linkage discrepancy is a mojibake right apostrophe; "
        "normalization was used only for linkage, not keyword counting. "
        "Original Exp2A exclusions were independently reconstructed from "
        "Exp2A.main.qualtrics.csv using Exp2A.analyze.Rmd as text: valid "
        "PROLIFIC_PID and mturk lengths >=13, Finished=1, nonmissing age and "
        "gender_f, attention_check_2=2, and the six explicitly listed "
        "nonsensical-response IDs removed. Counts after these steps are "
        + ", ".join(str(len(rows)) for rows in (valid, complete, attentive, retained))
        + ". The retained worker and response ID sets exactly match the "
        "posted 291-person reanalysis file; all posted creativity-rating "
        "composites are nonmissing. No further exclusions or averaging across "
        "ratings were used for these lexical counts. All read deposit files "
        "passed the manifest SHA-256 and byte-size checks. Between-person "
        "randomization; first_round is inapplicable."
    )
    if not all(item["match"] for item in reproduction):
        notes += " Reproduction failed; all requested computed fields are null."
    results.append({"slug": estimate["slug"], "round": "all",
                    "reproduced": reproduction, "computed": computed,
                    "notes": notes})

assert len(extraction["estimates"]) == 56
assert len(results) == 2 and len(skipped) == 54
assert {item["slug"] for item in results + skipped} == {item["slug"] for item in extraction["estimates"]}
assert len({item["slug"] for item in results + skipped}) == len(results) + len(skipped)

output = {"cid": "c015", "analyst": "B", "script": SCRIPT.as_posix(),
          "data_files": READ_FILES, "results": results, "skipped": skipped}
with OUTPUT.open("w", encoding="utf-8") as fh:
    json.dump(output, fh, ensure_ascii=False, indent=1)
with OUTPUT.open(encoding="utf-8") as fh:
    parsed = json.load(fh)
assert parsed == output
print(json.dumps({"cid": "c015", "n_results": len(parsed["results"]),
                  "n_reproduced": sum(bool(item["reproduced"]) and all(check["match"] for check in item["reproduced"])
                                      for item in parsed["results"]),
                  "n_skipped": len(parsed["skipped"])}))
