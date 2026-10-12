"""Independent analyst A reconstruction for c015.

Run with python -I -B A.py. The only output is A.json beside this script.
Deposited programs are read only as text; none are executed or imported.

All extracted outcomes are diversity measures. The two keyword outcomes
are raw set totals, so the job's rule 5 applies: retain the paper's units
and do not manufacture participant SDs or HC2 SEs for those totals.
"""

import sys

sys.dont_write_bytecode = True

import csv
import hashlib
import importlib.util
import io
import json
import re
from collections import Counter
from pathlib import Path


WORKSPACE = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA_ROOT = Path("D:/projects/ai-skill-atlas/creativity-data")
DEPOSIT = DATA_ROOT / "osf-zf3s2"
SCRIPT = WORKSPACE / "analysis/c015/A.py"
OUTPUT = WORKSPACE / "analysis/c015/A.json"
MODEL = "https://tfhub.dev/google/universal-sentence-encoder/4"
READ_FILES = set()


def read_bytes(path):
    path = Path(path)
    assert path.is_absolute()
    READ_FILES.add(path.as_posix())
    return path.read_bytes()


def read_text(path):
    return read_bytes(path).decode("utf-8-sig")


def read_json(path):
    return json.loads(read_text(path))


def read_rows(path):
    # Do not let a CSV parser turn the literal human-only label "None"
    # into a missing value.
    return list(csv.DictReader(io.StringIO(read_text(path), newline="")))


def read_pool(path):
    rows = list(csv.reader(io.StringIO(read_text(path), newline="")))
    assert rows and all(len(row) == 1 and row[0].strip() for row in rows)
    # Notebook cell 0 reads these CSVs with header=None, then strips each
    # complete first-column submission. It does not split multi-idea text.
    return [row[0].strip() for row in rows]


def text_counters_for_linking(raw_texts, pool_texts):
    """Link texts without changing any text used for the keyword count.

    Some pool CSVs contain UTF-8 bytes misdecoded as Windows-1252, with
    undefined Windows-1252 bytes retained as their Latin-1 code points.
    Generate repairs only from characters actually in the participant
    texts, then compare multisets after whitespace normalization.
    """
    repairs = {}
    for char in {c for text in raw_texts for c in text if ord(c) > 127}:
        pieces = []
        for byte in char.encode("utf-8"):
            try:
                pieces.append(bytes([byte]).decode("cp1252"))
            except UnicodeDecodeError:
                pieces.append(chr(byte))
        repairs["".join(pieces)] = char

    def normalize(text):
        for broken, original in sorted(repairs.items(), key=lambda x: -len(x[0])):
            text = text.replace(broken, original)
        return " ".join(text.split())

    return Counter(map(normalize, raw_texts)), Counter(map(normalize, pool_texts))


# Each arm specification is (CSV label, optional factorial column/value,
# headerless pool filename). The study IDs are from the extraction.
STUDIES = {
    "S1": ("exp_1", "Exp1.main.cleaned.csv", "idea_text_raw", {
        "ChatGPT-assisted": ("Chatbot", None, "chatbot_ideas.csv"),
        "Web-search-assisted": ("Control", None, "control_ideas.csv"),
    }),
    "S2": ("exp_2a", "Exp2A.main.full.csv", "idea_text_raw", {
        "ChatGPT-assisted": ("Chatbot", None, "gpt_ideas.csv"),
        "Web-search-assisted": ("Google", None, "google_ideas.csv"),
        "Human": ("None", None, "human_ideas.csv"),
    }),
    "S3": ("exp_2b", "Exp2B.main.cleaned.csv", "idea_text_raw", {
        "ChatGPT\u2013human": ("ChatbotHuman", None, "chatbot_human.csv"),
        "Human-only": ("HumanOnly", None, "human_only.csv"),
    }),
    "S4": ("exp_3", "Exp3.main.cleaned.csv", "idea_text_raw", {
        "ChatGPT-assisted": ("Chatbot", None, "chatbot_ideas.csv"),
        "Web-search-assisted": ("Google", None, "google_ideas.csv"),
    }),
    "S5": ("exp_4", "Exp4.main.cleaned.csv", "idea", {
        "ChatGPT (low)": ("Chatbot", ("NumCon", "Low"), "chatbot_ideas_low.csv"),
        "Web search (low)": ("Google", ("NumCon", "Low"), "google_ideas_low.csv"),
        "ChatGPT (high)": ("Chatbot", ("NumCon", "High"), "chatbot_ideas_high.csv"),
        "Web search (high)": ("Google", ("NumCon", "High"), "google_ideas_high.csv"),
    }),
    "S6": ("exp_5", "Exp5.main.cleaned.csv", "idea", {
        "ChatGPT (base)": ("Chatbot", ("Empathy", "Baseline"), "chatbot_empathy_base_ideas.csv"),
        "Web search (base)": ("Google", ("Empathy", "Baseline"), "google_empathy_base_ideas.csv"),
        "ChatGPT (high)": ("Chatbot", ("Empathy", "High"), "chatbot_empathy_high_ideas.csv"),
        "Web search (high)": ("Google", ("Empathy", "High"), "google_empathy_high_ideas.csv"),
    }),
}


def numeric(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def verify_exp2a_exclusions(cleaned_rows):
    """Independently implement the filters in the original Rmd as read text."""
    source_path = DATA_ROOT / "osf-rzn87/Exp2A/Exp2A.analyze.Rmd"
    source = read_text(source_path)
    block = source.split("# remove nonsensical responses", 1)[1].split("write.csv", 1)[0]
    excluded_ids = set(re.findall(r'"([a-f0-9]{24})"', block))
    assert len(excluded_ids) == 6
    raw = read_rows(DATA_ROOT / "osf-rzn87/Exp2A/Exp2A.main.qualtrics.csv")
    rows = [r for r in raw if len(r["PROLIFIC_PID"]) >= 13 and len(r["mturk"]) >= 13]
    flow = [len(rows)]
    rows = [r for r in rows if numeric(r["Finished"]) == 1
            and numeric(r["age"]) is not None and numeric(r["gender_f"]) is not None]
    flow.append(len(rows))
    rows = [r for r in rows if numeric(r["attention_check_2"]) == 2]
    flow.append(len(rows))
    rows = [r for r in rows if r["PROLIFIC_PID"] not in excluded_ids]
    flow.append(len(rows))

    def key(row, raw_input):
        return (row["Condition"], row["idea"] if raw_input else row["idea_text_raw"],
                row["PROLIFIC_PID"] if raw_input else row["workerId"])

    original = {r["ResponseId"]: key(r, True) for r in rows}
    deposited = {r["ResponseId"]: key(r, False) for r in cleaned_rows}
    assert len(original) == len(rows) == len(deposited) == len(cleaned_rows)
    assert original == deposited
    assert flow == [414, 298, 297, 291]
    return flow


def check(statistic, printed, computed):
    # All analyzed printed statistics are integer counts, so the comparison
    # at printed precision is exact. No tolerance or reconstructed rounding.
    return {"statistic": statistic, "printed": printed, "computed": computed,
            "match": computed == printed}


def main():
    extraction = read_json(WORKSPACE / "extraction/c015.json")
    manifest = read_json(DATA_ROOT / "manifest.json")
    notebook = read_json(DEPOSIT / "analysis.ipynb")
    notebook_source = "\n".join("".join(c.get("source", [])) for c in notebook["cells"])
    assert MODEL in notebook_source
    assert not any(c.get("outputs") for c in notebook["cells"])
    assert len(extraction["estimates"]) == 56
    assert all(e["construct"] == "diversity" and e["within_person"] is None
               for e in extraction["estimates"])

    # Verify the downloaded analysis deposit against its manifest. This
    # reads bytes only, including the notebook; no deposited code is run.
    for relative, metadata in manifest["deposits"]["osf-zf3s2"]["files"].items():
        path = DEPOSIT / relative
        assert path.resolve().is_relative_to(DEPOSIT.resolve())
        data = read_bytes(path)
        assert len(data) == metadata["bytes"]
        assert hashlib.sha256(data).hexdigest() == metadata["sha256"]

    missing_packages = [p for p in ["tensorflow", "tensorflow_hub"]
                        if importlib.util.find_spec(p) is None]
    assert missing_packages == ["tensorflow", "tensorflow_hub"], (
        "The embedding environment has changed; re-audit availability before rerunning.")

    arms = {}
    main_rows = {}
    for study, (folder, filename, text_column, specifications) in STUDIES.items():
        rows = read_rows(DEPOSIT / folder / filename)
        main_rows[study] = rows
        assert len({r["workerId"] for r in rows}) == len(rows)
        assert len({r["ResponseId"] for r in rows}) == len(rows)
        assert not any(re.search(r"embed|similar|cosine|centroid|mst|unique", c, re.I)
                       for c in rows[0])
        for arm, (condition, factor, pool_name) in specifications.items():
            selected = [r for r in rows if r["Condition"] == condition
                        and (factor is None or r[factor[0]] == factor[1])]
            pool_path = DEPOSIT / folder / pool_name
            texts = read_pool(pool_path)
            participant_texts = [r[text_column] for r in selected]
            left, right = text_counters_for_linking(participant_texts, texts)
            assert len(selected) == len(texts)
            assert left == right, (study, arm, "Participant/pool text mapping failed")
            arms[(study, arm)] = {
                "n": len(selected), "texts": texts, "raw_texts": participant_texts,
                "pool": pool_path.relative_to(DEPOSIT).as_posix(),
                "selection": "Condition=" + condition + (
                    " and " + factor[0] + "=" + factor[1] if factor else ""),
            }

    flow = verify_exp2a_exclusions(main_rows["S2"])
    for relative in ["Exp2A/Exp2A.main.qualtrics.csv", "Exp2A/Exp2A.analyze.Rmd"]:
        metadata = manifest["deposits"]["osf-rzn87"]["files"][relative]
        data = read_bytes(DATA_ROOT / "osf-rzn87" / relative)
        assert hashlib.sha256(data).hexdigest() == metadata["sha256"]

    results, skipped = [], []
    for estimate in extraction["estimates"]:
        slug, study = estimate["slug"], estimate["study_id"]
        treatment = arms[(study, estimate["treatment_arm"])]
        control = arms[(study, estimate["control_arm"])]
        if "_sprinkler_count_" not in slug:
            assert estimate["measure"] in ["category_count", "embedding_similarity"]
            reason = (
                "Cannot reproduce this embedding-based diversity outcome exactly. "
                "The authors' notebook (read as text only), cell 0, uses " + MODEL + ". "
                "The downloaded deposit contains the input texts but no saved embeddings "
                "or diversity scores; the notebook has no saved outputs. TensorFlow and "
                "TensorFlow Hub are not installed, and the required model weights are not "
                "among the supplied files. No substitute model or values inferred from "
                "published statistics were used. "
                "Mapped treatment input: osf-zf3s2/" + treatment["pool"] + " ("
                + treatment["selection"] + ", " + str(treatment["n"]) + " people); "
                "control input: osf-zf3s2/" + control["pool"] + " ("
                + control["selection"] + ", " + str(control["n"]) + " people). "
                "Each pool maps one-to-one to complete participant submissions after "
                "whitespace and character-encoding normalization used for linking only. "
            )
            differences = []
            for field, arm_data in [("n_treatment", treatment), ("n_control", control)]:
                printed = estimate[field]
                if printed is not None and printed != arm_data["n"]:
                    differences.append(field + " printed " + str(printed)
                                       + ", data " + str(arm_data["n"]))
            if differences:
                reason += "Reproduction also fails for the printed counts: " + "; ".join(differences) + ". "
                reason += "These reversed arm counts were checked in Supplementary Table 1, PDF p. 5. "
            elif estimate["n_treatment"] is None or estimate["n_control"] is None:
                reason += "The supplement does not print these two arm counts for comparison. "
            else:
                reason += "The arm counts reproduce, but outcome levels cannot be verified. "
            reason += "No outcome contrast or uncertainty was computed (rules 3 and 5)."
            skipped.append({"slug": slug, "reason": reason})
            continue

        # Reproduce the descriptive pool totals before deriving any contrast.
        # Count a submission once regardless of the number of keyword uses.
        # Case-insensitive substring matching includes the plural sprinklers.
        t_count = sum("sprinkler" in s.casefold() for s in treatment["texts"])
        c_count = sum("sprinkler" in s.casefold() for s in control["texts"])
        assert t_count == sum("sprinkler" in s.casefold() for s in treatment["raw_texts"])
        assert c_count == sum("sprinkler" in s.casefold() for s in control["raw_texts"])
        reproduction = [
            check("treatment_pool_count", estimate["stats"]["treatment_mean"], t_count),
            check("control_pool_count", estimate["stats"]["control_mean"], c_count),
            check("n_treatment", estimate["n_treatment"], treatment["n"]),
            check("n_control", estimate["n_control"], control["n"]),
        ]
        if not all(item["match"] for item in reproduction):
            skipped.append({"slug": slug, "reason": "Reproduction failed: " + json.dumps(reproduction)})
            continue

        computed = {
            "n_treatment": treatment["n"], "n_control": control["n"],
            "treatment_mean": t_count, "treatment_sd": None,
            "control_mean": c_count, "control_sd": None,
            "difference": t_count - c_count, "difference_se": None,
            "se_type": None, "n_clusters": None,
        }
        notes = (
            "Rule 5 set-diversity result, in raw numbers of submissions containing "
            "the keyword. As in the extraction, treatment_mean and control_mean "
            "store whole-pool counts, NOT participant-level means; difference is the "
            "treatment pool count minus the control pool count, not a difference "
            "in rates. Participant SDs, a randomization-level SE, and se_type are "
            "null because this extracted outcome is one total per set. No binary-rate "
            "outcome was substituted and no HC2, paired, or cluster SE is claimed. "
            "Printed totals checked against main PDF p. 1 (printed p. 1107); "
            "people counts checked against supplement PDF pp. 3-4, Table 1. "
            "Use exp_2a/Exp2A.main.full.csv, one unique workerId and ResponseId "
            "per person, selecting " + treatment["selection"] + " versus "
            + control["selection"] + ". Retain every supplied analyzed person. "
            "The original Exp2A Rmd was read as text only. Independently applying "
            "its valid-ID, completion/demographics, attention-check, and six explicit "
            "nonsensical-response exclusions to the raw Qualtrics CSV gives "
            + ", ".join(map(str, flow)) + " rows respectively; the final 291 "
            "identities, conditions and idea texts match the posted full dataset "
            "exactly. Human-only Condition is the literal string None, not missing. "
            "The headerless pool CSVs match these participant texts, with one "
            "ChatGPT apostrophe encoding artifact normalized only for linking. "
            "Keyword counts are computed on unmodified pool texts and independently "
            "checked on original participant texts. Case-insensitive substring "
            "matching recovers 20/96 ChatGPT, 7/100 web-search and 12/95 human-only. "
            "A case-sensitive substring would give 19 for ChatGPT; a singular-only "
            "whole-word search would give 11 for human-only. Including the plural "
            "and ignoring case recovers all three published totals. All input "
            "hashes match the download manifest. Between-person assignment; "
            "there is no within-person or first-round contrast."
        )
        results.append({"slug": slug, "round": "all", "reproduced": reproduction,
                        "computed": computed, "notes": notes})

    covered = [item["slug"] for item in results + skipped]
    assert len(covered) == len(set(covered)) == len(extraction["estimates"])
    assert set(covered) == {e["slug"] for e in extraction["estimates"]}
    obj = {"cid": "c015", "analyst": "A", "script": SCRIPT.as_posix(),
           "data_files": sorted(READ_FILES), "results": results, "skipped": skipped}
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
        fh.write("\n")
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({"cid": "c015", "n_results": len(results),
                      "n_reproduced": sum(all(c["match"] for c in r["reproduced"])
                                          for r in results),
                      "n_skipped": len(skipped)}))


if __name__ == "__main__":
    main()
