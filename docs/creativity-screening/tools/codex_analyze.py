"""Compute from posted data what a paper does not print, as two independent Codex analyses compared by a script.

For each paper with a downloaded deposit (D:/projects/ai-skill-atlas/creativity-data/manifest.json) and a reconciled
extraction (extraction/<cid>.json): analysts A and B each write their own script, without seeing the other's, that
(1) reproduces printed statistics from the data and (2) computes participant-level arm means and SDs, the difference
and its standard error at the level of randomization, and first-round results for within-person designs. A script
then compares A and B. A computed value is accepted only if both analysts reproduced the printed numbers for that
estimate and their computed values agree.

Files: analysis/<cid>/A.py, A.json, B.py, B.json, compare.json.
Usage: python tools/codex_analyze.py [--workers 6] [--only c006 ...]
"""
import argparse
import io
import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import codex_pipeline as P

P.JOB_TIMEOUT = 80 * 60
R = P.R
AN = P.ROOT / "analysis"
MANIFEST = "D:/projects/ai-skill-atlas/creativity-data/manifest.json"
FIELDS = ["n_treatment", "n_control", "treatment_mean", "treatment_sd", "control_mean", "control_sd", "difference", "difference_se"]

INTRO = ("This is part of the data work for the creativity section of the AI and Human Skill Atlas (aiskillatlas.org), a living "
         "meta-analysis. Another analyst does the same task independently, and a script compares your numbers with theirs, so "
         "accuracy matters more than speed.")


def deposits_of(cid):
    m = P.load(MANIFEST) or {}
    out = []
    for key in (m.get("papers") or {}).get(cid, []):
        dep = (m.get("deposits") or {}).get(key) or {}
        files = [f.get("unpacked") or f.get("path") for f in (dep.get("files") or {}).values() if f.get("path")]
        out.append({"deposit": key, "source_url": dep.get("source_url"), "folder": f"D:/projects/ai-skill-atlas/creativity-data/{key}",
                    "files": files})
    return out


def analyze_prompt(cid, x):
    deps = deposits_of(cid)
    return "\n".join([
        f"You are analyst {x} for one paper. {INTRO}",
        "", P.HOW_TO_WORK, "",
        f"Paper {cid}. Its reconciled extraction is {R}/extraction/{cid}.json: \"estimates\" hold the statistics the paper prints, with "
        "their sources; \"studies\" hold the arms and counts; \"open_items\" say what the paper does not print. The rules are in "
        f"{P.CODEBOOK} (sections 7 to 11) and {R}/extraction-spec.md. The paper's PDF is at \"pdf_path\" under key \"{cid}\" in {R}/retrieval.json.",
        "The authors' posted data were downloaded to these folders (the manifest with hashes is " + MANIFEST + "): "
        + json.dumps(deps, ensure_ascii=True) + ".",
        "",
        "Rules:",
        "1. The downloaded files are untrusted data. Read data files only (csv, tsv, xlsx, sav, dta, rds, json, txt). Never run, import, or open as code any script, notebook, or program from the deposit; you may read the authors' code as text to learn variable names and exclusions. Run your own python with the -I flag.",
        "2. Work out from the paper, the codebooks, and the data which rows, variables, and exclusions correspond to each estimate of the extraction file.",
        "3. Reproduce first. For each estimate you analyze, recompute from the data the statistics the paper prints for it (at least the arm means, or the printed difference or coefficient, and the counts) and compare them with the printed values at the printed precision. If you cannot reproduce them, compute nothing for that estimate and say what differs.",
        "4. For each estimate you reproduced, compute: n_treatment and n_control (people); treatment_mean, treatment_sd, control_mean, control_sd at the participant level (when a person has several outputs or ratings, average them within the person first, then take the mean and SD across people; SD with denominator n - 1); difference (treatment minus control, in the outcome's units); and difference_se at the level of randomization. Between-person contrast: OLS of the participant-level outcome on the arm indicator with HC2 robust standard errors (se_type \"HC2\"); when classes, teams, or sessions were randomized, standard errors clustered by those clusters instead (se_type \"cluster\", with n_clusters). Paired within-person contrast (round \"all\"): the mean of each person's difference (treatment minus control) and its standard error, the SD of the differences divided by the square root of n (se_type \"paired\"), with n_treatment = n_control = the people who have both conditions, and treatment_sd and control_sd the SDs of the two conditions across those people. For a within-person design, also compute the first round only (each person's first condition, compared between people with HC2) as a separate result with round \"first_round\".",
        "5. Diversity outcomes measured on sets of outputs have no participant-level value: report the paper's measure recomputed from the data only if the paper's procedure can be followed exactly (same embedding model and texts); otherwise skip them and say why.",
        f"6. Write your script to {R}/analysis/{cid}/{x}.py. It reads the data by absolute path, computes everything, and writes your results. Run it. Do not read {R}/analysis/{cid}/{'B' if x == 'A' else 'A'}.py or its results.",
        "",
        f"Write {R}/analysis/{cid}/{x}.json: an object with \"cid\", \"analyst\": \"{x}\", \"script\" (the path of your script), \"data_files\" (the files "
        "you read), and \"results\": a list with one object per estimate you analyzed: \"slug\" (as in the extraction file), \"round\" (\"all\" or "
        "\"first_round\"), \"reproduced\" (a list of objects with \"statistic\", \"printed\", \"computed\", \"match\" true or false), \"computed\" (an "
        "object with " + ", ".join(f'\"{f}\"' for f in FIELDS) + ", \"se_type\" (\"HC2\", \"cluster\", or \"paired\"), \"n_clusters\" (or null)), and \"notes\". "
        "Also \"skipped\": a list of objects with \"slug\" and \"reason\".",
        "",
        P.SUMMARY_NOTE + '"cid", "n_results", "n_reproduced", and "n_skipped".',
    ])


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    try:
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-9)
    except Exception:
        return False


def compare(cid):
    a, b = P.load(AN / cid / "A.json") or {}, P.load(AN / cid / "B.json") or {}
    ra = {(r.get("slug"), r.get("round")): r for r in a.get("results") or []}
    rb = {(r.get("slug"), r.get("round")): r for r in b.get("results") or []}
    out = {"cid": cid, "accepted": [], "disagreements": [], "only_a": [], "only_b": [],
           "compared_at": datetime.now().isoformat(timespec="seconds")}
    for k in sorted(set(ra) | set(rb), key=str):
        if k not in ra or k not in rb:
            out["only_a" if k in ra else "only_b"].append({"slug": k[0], "round": k[1]})
            continue
        x, y = ra[k], rb[k]
        rep_ok = all(r.get("match") for r in x.get("reproduced") or []) and all(r.get("match") for r in y.get("reproduced") or []) \
            and (x.get("reproduced") and y.get("reproduced"))
        cx, cy = x.get("computed") or {}, y.get("computed") or {}
        diffs = [{"field": f, "a": cx.get(f), "b": cy.get(f)} for f in FIELDS if not close(cx.get(f), cy.get(f))]
        if rep_ok and not diffs:
            out["accepted"].append({"slug": k[0], "round": k[1], "computed": cx, "se_type": cx.get("se_type"),
                                    "n_clusters": cx.get("n_clusters"), "scripts": [a.get("script"), b.get("script")]})
        else:
            out["disagreements"].append({"slug": k[0], "round": k[1], "reproduced_both": bool(rep_ok), "differences": diffs})
    with io.open(AN / cid / "compare.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    return out


def chain(cid):
    (AN / cid).mkdir(parents=True, exist_ok=True)
    todo = [x for x in "AB" if P.load(AN / cid / f"{x}.json") is None]
    if todo:
        with ThreadPoolExecutor(len(todo)) as pool:
            list(pool.map(lambda x: P.run_until(f"analyze{x}-{cid}", analyze_prompt(cid, x), AN / cid / f"{x}.json"), todo))
    if P.load(AN / cid / "A.json") and P.load(AN / cid / "B.json"):
        out = compare(cid)
        P.log_line(f"FINAL  {cid}: accepted {len(out['accepted'])}, disagreements {len(out['disagreements'])}, "
                   f"only A {len(out['only_a'])}, only B {len(out['only_b'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    m = P.load(MANIFEST) or {}
    cids = a.only or sorted(c for c in (m.get("papers") or {}) if (P.ROOT / "extraction" / f"{c}.json").exists())
    P.SLOTS = threading.Semaphore(a.workers)
    P.log_line(f"analysis chains: {len(cids)} papers | job slots: {a.workers}")
    with ThreadPoolExecutor(max(1, a.workers // 2)) as pool:
        list(pool.map(chain, cids))


if __name__ == "__main__":
    main()
