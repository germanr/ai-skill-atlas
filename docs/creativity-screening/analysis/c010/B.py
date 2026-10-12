"""Independent c010 analyst B reconstruction. Run with python -I B.py.

Only this script and B.json are written. Deposited R code is read as text only;
all transformations below are an independent Python implementation.

Reproduction requires all recorded checks to pass: the printed means and SDs
(using the authors' display sequence), study/available contrast counts, and
the original t, F, or likelihood-ratio statistic where applicable. The three
newness outcomes are validated by their two printed percentages and counts;
their judge-random-intercept logistic models are not refitted. Discrepancies
are retained in results with null numeric computed fields and also in skipped.
The new HC2 calculations run only after this gate passes.
"""

from pathlib import Path
import hashlib
import json
import math
import re
import sys

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

BASE = Path(r"C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DATA = Path(r"D:/projects/ai-skill-atlas/creativity-data/osf-rzn87")
SCRIPT = BASE / "analysis/c010/B.py"
OUTPUT = BASE / "analysis/c010/B.json"
MANIFEST = Path(r"D:/projects/ai-skill-atlas/creativity-data/manifest.json")
READ_FILES = []
AUDIT = {}
EXPS = ["Exp1", "Exp2A", "Exp2B", "Exp3", "Exp4", "Exp5"]
TOTALS = dict(zip(EXPS, [233, 291, 200, 194, 400, 383]))
JUDGES = dict(zip(EXPS, [331, 232, 241, 158, 321, 310]))
EXCLUDED = {
    "Exp1": "A2XUJD9Z7ZDLB5 A1OPV8D0GG5Z32 AQ9DVGD3J7MD4 A1TEVUU2U1VYYV "
    "AWKP0M7G5BBCC A1KIL2V6SMJBGX AYMR8UTKYJ2D4 A29N5E8YC6DB9Q "
    "A3PZASM0C12I57 A1U52239IPV7IO A1AB1BMULT9JLE A3TH6B3RUD1MUQ "
    "A15DXD3Z1AHK6C A3BP24ZY0OA5TR A3SQV2L85UE5BK A2LEBJWW395FST "
    "A3HAERGD8FL7WX A8FAQQHLVROLG A3AHD1NV5XCOF A1J9VZ372FV2QZ "
    "A2GZNOA5CIVKUB A30UQ017N4PML5 A1RP17F7OXV0IW A106QH27FETZ88 "
    "A2C4R0TBPZGWTD A212P9LUF0URRZ A1RQUOVV8PCXBM",
    "Exp2A": "5a9ab4944eecca0001dd806a 59949236c825cf0001d7dcdc "
    "63d7e54a90879dee84dffb32 62b0cd459238d178b6300581 "
    "5f80bc44efa2c013099af460 63c4a90d09909e33d5e82f21",
    "Exp2B": "6572fd344d1080cd9c53a005 5c78b032419dcc0014119082 "
    "60ddc7abdf6661b9c294691f 6361b032a20001fc86b0ff1b "
    "63e52f8ab3688f45f842114c 5de5496937e1d50ca63e0fa5 "
    "613aad30bcfed65155a026ec 5f47f39d57500a24ca3bbc89 "
    "6400e3697879c55c323f34d0 62b20c0065e9809e66d13fa5 "
    "5f084a7987a3fe028ff65b8a 610898813e48dc2864965122 "
    "627e71af3701230cdc757652 5da25f04c8c2de00139ed46b "
    "643883e97bc73c8245bc31d3",
    "Exp3": "A3SQV2L85UE5BK",
    "Exp4": "61549a2caa92d84f392000e9 58dcfe010674970001e928e5 "
    "5c0fc9645096c60001f15b12 5ea07a44234e0304542e1c50 "
    "62b473736986d2b27c1427d2",
    "Exp5": "5a4d194c87c6f8000137d680 5cb4e2e8dde4050015779d17 "
    "643ff216b732bb345c8403e2 63da5521f23372b30f4f0b77 "
    "5c1d234d89f035000172aeb7 62e02b26e879244a99e852fa "
    "602471c97db8951797cef086 5f0f6ef654ae12126762bd4e",
}


def register(path):
    path = Path(path)
    name = path.as_posix()
    if name not in READ_FILES:
        READ_FILES.append(name)
    return path


def text_file(path):
    return register(path).read_text(encoding="utf-8")


def read_csv(path):
    path = register(path)
    # R read.csv preserves the literal experimental condition "None".
    return pd.read_csv(path, keep_default_na=False, na_values=["", "NA"],
                       low_memory=False)


def strict_mean(values):
    return values.mean(skipna=False)


def r_round(value, digits):
    """R 4.2 fround: compare distances to adjacent decimal grid values.

    Verified against Rf_fround in the installed R 4.2.2 runtime. Python's
    built-in round has different behavior for some binary ties.
    """
    sign = -1 if value < 0 else 1
    value = abs(float(value))
    scale = 10.0 ** digits
    lower_int = math.floor(value * scale)
    lower = lower_int / scale
    upper = (lower_int + 1) / scale
    dist_lower, dist_upper = value - lower, upper - value
    up = dist_upper < dist_lower or (dist_upper == dist_lower and lower_int % 2 == 1)
    return sign * (upper if up else lower)


def displayed_summary(value, digits=2):
    # Deposited analysis: get_summary_stats() (three decimal summaries),
    # followed by mutate(mean=round(mean,2), sd=round(sd,2)).
    return r_round(r_round(value, 3), digits)


def clean_main(exp):
    x = read_csv(DATA / exp / (exp + ".main.qualtrics.csv"))
    if exp not in ["Exp1", "Exp3"]:
        x["workerId"] = x["PROLIFIC_PID"]
    x = x.loc[x.workerId.str.len().ge(13)].copy()
    if exp == "Exp2A":
        x = x.loc[x.mturk.str.len().ge(13)].copy()
    x = x.loc[x.Finished.eq(1)].dropna(subset=["gender_f"])
    if exp != "Exp2B":
        x = x.dropna(subset=["age"])
    if exp == "Exp1":
        x = x.dropna(subset=["idea", "idea_count"])
        x = x.loc[x.idea.str.len().gt(0)]
    audit = {"complete": len(x)}
    if exp in ["Exp2A", "Exp2B", "Exp3", "Exp5"]:
        x = x.loc[x.attention_check_2.eq(2)].copy()
    audit["after_attention"] = len(x)
    x = x.loc[~x.workerId.isin(EXCLUDED[exp].split())].copy()
    audit["after_named_exclusions"] = len(x)
    assert x.ResponseId.is_unique and x.workerId.is_unique, exp
    if exp == "Exp1":
        counts = read_csv(DATA / exp / "Exp1.main.qualtrics.handcoded.csv")
        x = x.merge(counts[["ResponseId", "idea_count_jc"]],
                    on="ResponseId", how="left", validate="one_to_one")
    if exp == "Exp2B":
        # These rows reproduce the original three-arm error term only; they
        # never count as people in any requested two-human-arm result.
        model_only = read_csv(DATA / exp / "Exp2B.main.ChatbotOnly.csv")
        model_only["ResponseId"] = [f"R_AAAAAAAAAA{i}" for i in range(1, len(model_only)+1)]
        model_only["workerId"] = [f"wwwwwwwww{i}" for i in range(1, len(model_only)+1)]
        x = pd.concat([x, model_only], ignore_index=True)
    AUDIT[exp] = audit
    return x


def links(exp, expert=False):
    suffixes = [("_Baseline", "B"), ("_EmpathyHigh", "H")] if exp == "Exp5" else [("", "")]
    rows = []
    for suffix, prefix in suffixes:
        x = read_csv(DATA / exp / (exp + ".rating.link" + suffix + ".csv"))
        source_id = "idea_text_id" if exp == "Exp1" and not expert else x.columns[0]
        x["key"] = prefix + x[source_id].astype(int).astype(str)
        rows.append(x[["workerId", "ResponseId", "key"]])
    out = pd.concat(rows, ignore_index=True)
    assert out.key.is_unique
    return out


def lay_scores(exp, main):
    r = read_csv(DATA / exp / (exp + ".rating.qualtrics.csv"))
    id_col = "workerId" if exp in ["Exp1", "Exp3"] else "PROLIFIC_PID"
    if exp == "Exp2B":
        r = r.loc[r[id_col].str.len().gt(11)].dropna(subset=["age"])
    else:
        second_id = "mturk" if exp in ["Exp1", "Exp3", "Exp4"] else "prolific"
        r = r.loc[r[id_col].str.len().gt(11) & r[second_id].str.len().gt(11)
                  & r.Finished.eq(1)].dropna(subset=["gender_f"])
    AUDIT[exp]["raters"] = len(r)
    assert r.ResponseId.is_unique
    cols = [c for c in r if re.match(r"^\d+_", c)]
    long = r.melt(id_vars=["ResponseId"], value_vars=cols,
                  var_name="item", value_name="value").dropna(subset=["value"])
    parts = long.item.str.split("_", expand=True)
    if exp == "Exp5":
        long["key"] = parts[2] + parts[0]
        long["dimension"] = parts[1] + "_" + parts[3]
    else:
        long["key"] = parts[0]
        long["dimension"] = parts[1] + parts[2].fillna("").map(lambda v: "_" + v if v else "")
    long = long[["ResponseId", "key", "dimension", "value"]].drop_duplicates()
    assert not long.duplicated(["ResponseId", "key", "dimension"]).any()
    wide = long.pivot(index=["ResponseId", "key"], columns="dimension", values="value")
    AUDIT[exp]["incomplete_rating_rows"] = int(wide.isna().any(axis=1).sum())
    idea = wide.groupby(level="key").agg(strict_mean)
    idea["originality"] = idea[[f"creative_{i}" for i in [1,2,3]]].mean(axis=1, skipna=False)
    idea["appropriateness"] = idea[[f"practical_{i}" for i in [1,2,3]]].mean(axis=1, skipna=False)
    idea["creativity"] = idea[["originality", "appropriateness"]].mean(axis=1, skipna=False)
    outcomes = ["originality", "appropriateness", "creativity"]
    if exp == "Exp3":
        idea["clarity"] = idea[[f"clarity_{i}" for i in [1,2,3]]].mean(axis=1, skipna=False)
        idea["thoughtfulness"] = idea["thought"]
        idea["articulateness"] = idea[["clarity_1", "clarity_2", "clarity_3", "complexity", "thought"]].mean(axis=1, skipna=False)
        outcomes += ["clarity", "complexity", "thoughtfulness", "articulateness"]
    joined = links(exp).merge(idea[outcomes], on="key", how="left", validate="one_to_one")
    by_person = joined.groupby(["workerId", "ResponseId"])[outcomes].agg(strict_mean).reset_index()
    x = main.merge(by_person, on=["workerId", "ResponseId"], how="left", validate="one_to_one")
    required = ["originality", "appropriateness", "creativity"]
    if exp == "Exp3":
        required += ["articulateness"]
    x = x.dropna(subset=required)
    AUDIT[exp]["lay_people"] = len(x.loc[x.Condition.ne("ChatbotOnly")])
    AUDIT[exp]["lay_arms"] = x.groupby("Condition").size().to_dict()
    if exp == "Exp1":
        x["fluency"] = x["idea_count_jc"]
        cutoff = x.creativity.quantile(0.8, interpolation="linear")
        x["top_ranked_creativity_share"] = 100.0 * (x.creativity > cutoff)
        AUDIT[exp]["top20_cutoff"] = float(cutoff)
    return x


def expert_scores(exp, main):
    suffixes = [("_Baseline", "B"), ("_High", "H")] if exp == "Exp5" else [("", "")]
    rows = []
    for suffix, prefix in suffixes:
        r = read_csv(DATA / "Robustness_Experts" / (exp + ".rating.experts" + suffix + ".csv"))
        r["key"] = prefix + r.idea_id.astype(int).astype(str)
        rows.append(r)
    ratings = pd.concat(rows, ignore_index=True)
    measures = {"originality": "Novelty_", "appropriateness": "Practicality_",
                "articulateness": "Articulate_", "verbosity": "Verbosity_",
                "not_new": "notnew_", "incrementally_new": "incnew_", "radically_new": "radnew_"}
    outcomes = []
    for name, prefix in measures.items():
        cols = [c for c in ratings if c.startswith(prefix)]
        if cols:
            assert len(cols) == 3
            ratings[name] = ratings[cols].mean(axis=1, skipna=False)
            if name.endswith("_new"):
                ratings[name] *= 100.0
            outcomes.append(name)
    ratings["creativity"] = ratings[["originality", "appropriateness"]].mean(axis=1, skipna=False)
    outcomes += ["creativity"]
    joined = links(exp, expert=True).merge(ratings[["key"] + outcomes],
                                         on="key", how="left", validate="one_to_one")
    by_person = joined.groupby(["workerId", "ResponseId"])[outcomes].agg(strict_mean).reset_index()
    x = main.merge(by_person, on=["workerId", "ResponseId"], how="left", validate="one_to_one")
    AUDIT[exp]["expert_people"] = len(x.loc[x.Condition.ne("ChatbotOnly")].dropna(subset=["creativity"]))
    return x


def select_estimate(e, datasets):
    exp = EXPS[int(e["study_id"][1:])-1]
    slug = e["slug"]
    kind = "expert" if "_expert_" in slug else "lay"
    name = slug.split("_", 1)[1].split("_" + kind + "_", 1)[0]
    if kind == "lay" and "_lay_" not in slug:
        name = slug.split("_", 1)[1].split("_chatgpt_", 1)[0]
    data = datasets[(exp, kind)].copy()
    if "high_constraints" in slug:
        data = data.loc[data.NumCon.eq("High")]
    elif "low_constraints" in slug:
        data = data.loc[data.NumCon.eq("Low")]
    elif "high_empathy" in slug:
        data = data.loc[data.Empathy.eq("High")]
    elif "baseline_empathy" in slug:
        data = data.loc[data.Empathy.eq("Baseline")]
    t_arm = "ChatbotHuman" if exp == "Exp2B" else "Chatbot"
    c_arm = "HumanOnly" if exp == "Exp2B" else (
        "None" if e["control_arm"] == "Human-only" else ("Control" if exp == "Exp1" else "Google"))
    return exp, kind, name, data, data.loc[data.Condition.eq(t_arm), name].dropna(), data.loc[data.Condition.eq(c_arm), name].dropna()


def original_test(e, datasets):
    exp, kind, name, selected, t, c = select_estimate(e, datasets)
    test_type = e["stats"]["test"]["type"]
    if test_type == "z":
        return None  # These are reproduced through the two printed percentages.
    if test_type == "chi2":
        counts = np.array([[np.count_nonzero(t), len(t)-np.count_nonzero(t)],
                           [np.count_nonzero(c), len(c)-np.count_nonzero(c)]])
        value, p, df, _ = stats.chi2_contingency(counts, correction=False, lambda_="log-likelihood")
        return float(value), int(df), float(p)
    full = datasets[(exp, kind)].dropna(subset=[name])
    group_cols = ["Condition"]
    factor = "NumCon" if exp == "Exp4" else "Empathy" if exp == "Exp5" else None
    if factor:
        group_cols.append(factor)
    cells = full.groupby(group_cols)[name]
    sums = cells.agg(["mean", "count", "var"])
    df = len(full) - len(sums)
    mse = float(((sums["count"] - 1) * sums["var"]).sum() / df)
    if test_type == "F":
        # car::Anova(type=3) under R's default treatment contrasts tests
        # Condition at the reference factor level, not the marginal EMM.
        level = "High" if exp == "Exp4" else "Baseline"
        tt, cc = sums.loc[("Chatbot", level)], sums.loc[("Google", level)]
        value = (tt["mean"] - cc["mean"]) ** 2 / (mse * (1/tt["count"]+1/cc["count"]))
        return float(value), [1, df], float(stats.f.sf(value, 1, df))
    if factor and len(selected) == len(full):
        # emmeans averages the two task cells with equal weights.
        weights = np.array([0.5 if idx[0] == "Chatbot" else -0.5 for idx in sums.index])
        delta = float(weights @ sums["mean"].to_numpy())
        se = math.sqrt(mse * (weights ** 2 / sums["count"].to_numpy()).sum())
    else:
        delta = float(t.mean() - c.mean())
        se = math.sqrt(mse * (1/len(t) + 1/len(c)))
    value = delta / se
    return value, df, float(2 * stats.t.sf(abs(value), df))


def audit_only(extraction, datasets):
    print(json.dumps(AUDIT, indent=1))
    for e in extraction["estimates"]:
        exp, kind, name, data, t, c = select_estimate(e, datasets)
        st = e["stats"]
        observed = [t.mean(), c.mean(), t.std(ddof=1), c.std(ddof=1)]
        printed = [st[k] for k in ["treatment_mean", "control_mean", "treatment_sd", "control_sd"]]
        precision = 1 if name.endswith("_new") or name == "top_ranked_creativity_share" else 2
        okay = [None if p is None else (r_round(float(v), precision) if precision == 1 else displayed_summary(v)) == p for v,p in zip(observed, printed)]
        print(e["slug"], "n", len(t), len(c), "printed", printed,
              "computed", [round(float(v), 8) for v in observed], "matches", okay)
        original = original_test(e, datasets)
        if original:
            test, df, p = original
            match = r_round(test, 1 if st["test"]["type"] == "chi2" else 2) == st["test"]["value"]
            if not match:
                print("TEST MISMATCH",st["test"],"computed",test,df,p)
        if name == "fluency":
            test = stats.ttest_ind(t,c,equal_var=True)
            print("FLUENCY", "overall_mean", data.fluency.mean(), "t", test.statistic, "p", test.pvalue)


def check(statistic, printed, computed, *, digits=None, descriptive=False):
    if descriptive:
        compared = displayed_summary(computed, digits or 2)
        # Show the result of the authors' presentation calculation here.
        # The unrounded participant summaries are in the computed block.
        recorded = compared
    elif digits is not None:
        compared = r_round(computed, digits)
        recorded = float(computed)
    else:
        compared = computed
        recorded = computed
    return {"statistic": statistic, "printed": printed, "computed": recorded,
            "match": bool(compared == printed)}


def hc2_summary(t, c):
    """Between-person OLS with HC2, checked against its two-arm identity."""
    t, c = t.to_numpy(dtype=float), c.to_numpy(dtype=float)
    assert len(t) > 1 and len(c) > 1
    y = np.r_[t, c]
    indicator = np.r_[np.ones(len(t)), np.zeros(len(c))]
    x = np.column_stack([np.ones(len(y)), indicator])
    fitted = sm.OLS(y, x).fit(cov_type="HC2")
    delta = float(t.mean() - c.mean())
    se = float(fitted.bse[1])
    identity_se = float(np.sqrt(t.var(ddof=1)/len(t) + c.var(ddof=1)/len(c)))
    assert np.isclose(float(fitted.params[1]), delta, rtol=1e-12, atol=1e-12)
    assert np.isclose(se, identity_se, rtol=1e-12, atol=1e-12)
    return {"n_treatment": len(t), "n_control": len(c),
            "treatment_mean": float(t.mean()), "treatment_sd": float(t.std(ddof=1)),
            "control_mean": float(c.mean()), "control_sd": float(c.std(ddof=1)),
            "difference": delta, "difference_se": se,
            "se_type": "HC2", "n_clusters": None}


def withheld_summary():
    out = dict.fromkeys(["n_treatment", "n_control", "treatment_mean", "treatment_sd",
                         "control_mean", "control_sd", "difference", "difference_se"])
    # This is the specified method, not a computed standard error.
    out.update(se_type="HC2", n_clusters=None)
    return out


def source_provenance():
    """Read protocol/code as text; verify deposited files against the manifest."""
    text_file(BASE.parent / "creativity-codebook.md")
    text_file(BASE / "extraction-spec.md")
    retrieval = json.loads(text_file(BASE / "retrieval.json"))["c010"]
    text_file(retrieval["md_path"])
    supplement = Path(r"D:/projects/ai-skill-atlas/creativity-supplements/c010")
    for name in ["41562_2024_1953_MOESM1_ESM", "41562_2024_1953_MOESM2_ESM"]:
        text_file(supplement / (name + ".md"))
    # Read cited PDF text, without rendering or writing intermediary files.
    import pymupdf
    for path in [Path(retrieval["pdf_path"]),
                 supplement / "41562_2024_1953_MOESM1_ESM.pdf",
                 supplement / "41562_2024_1953_MOESM2_ESM.pdf"]:
        with pymupdf.open(register(path)) as doc:
            assert all(page.get_text().strip() for page in doc)
    for exp in EXPS:
        code_text = text_file(DATA / exp / (exp + ".analyze.Rmd"))
        assert all(identifier in code_text for identifier in EXCLUDED[exp].split())
    text_file(DATA / "Robustness_Experts/experts_analyze.Rmd")
    manifest = json.loads(text_file(MANIFEST))["deposits"]["osf-rzn87"]["files"]
    for name in READ_FILES:
        path = Path(name)
        if path.is_relative_to(DATA):
            key = path.relative_to(DATA).as_posix()
            expected = manifest[key]
            content = path.read_bytes()
            assert len(content) == expected["bytes"], key
            assert hashlib.sha256(content).hexdigest() == expected["sha256"], key


def make_results(extraction, datasets):
    results, skipped = [], []
    studies = {s["study_id"]: s for s in extraction["studies"]}
    estimate_by_slug = {e["slug"]: e for e in extraction["estimates"]}
    complete = dict(zip(EXPS, [260, 298, 216, 208, 405, 394]))
    removed = {"Exp1": 27, "Exp2A": 7, "Exp3": 14, "Exp4": 5, "Exp5": 11}
    for e in extraction["estimates"]:
        exp, kind, name, selected, t, c = select_estimate(e, datasets)
        full = datasets[(exp, kind)]
        human = full.loc[full.Condition.ne("ChatbotOnly")].dropna(subset=[name])
        assert human.workerId.is_unique
        assert len(t) + len(c) == selected.loc[selected.Condition.isin(
            ["ChatbotHuman", "HumanOnly"] if exp == "Exp2B" else
            ["Chatbot", "None" if e["control_arm"] == "Human-only" else
             "Control" if exp == "Exp1" else "Google"])].dropna(subset=[name]).shape[0]
        checks = [check("study_n_analyzed_people", studies[e["study_id"]]["n_analyzed"], len(human)),
                  check("study_complete_responses", complete[exp], AUDIT[exp]["complete"])]
        if exp in removed:
            checks.append(check("study_excluded_people", removed[exp],
                                AUDIT[exp]["complete"] - AUDIT[exp]["after_named_exclusions"]))
        if kind == "lay":
            checks.append(check("lay_judges", JUDGES[exp], AUDIT[exp]["raters"]))
        else:
            checks.append(check("expert_judges", 3, 3))
        if e["n_total"] is not None:
            checks.append(check("contrast_n_total_people", e["n_total"], len(t)+len(c)))
        st = e["stats"]
        summary_source = e
        if st["test"]["type"] == "F":
            # The F record has no means: validate the same sample's printed
            # descriptive means in Supplementary Table 1 as well as the F.
            summary_source = estimate_by_slug[e["slug"].replace("_anova_main_effect", "_pooled")]
        summaries = {"treatment_mean": float(t.mean()), "control_mean": float(c.mean()),
                     "treatment_sd": float(t.std(ddof=1)), "control_sd": float(c.std(ddof=1))}
        percentage = name in ["not_new", "incrementally_new", "radically_new",
                               "top_ranked_creativity_share"]
        for field, value in summaries.items():
            printed = summary_source["stats"][field]
            if printed is not None:
                checks.append(check(field, printed, value, digits=1 if percentage else 2,
                                    descriptive=not percentage))
        original = original_test(e, datasets)
        if original is not None:
            value, df, p = original
            checks.append(check("original_test_" + st["test"]["type"], st["test"]["value"], value,
                                digits=1 if st["test"]["type"] == "chi2" else 2))
            if st["test"]["df"] is not None:
                checks.append(check("original_test_df", st["test"]["df"], df))
        if name == "fluency":
            checks.append(check("overall_mean_ideas", 1.69, float(full.fluency.mean()), digits=2))
            checks.append(check("original_test_p", 0.149, original[2], digits=3))
        notes = [
            f"{exp}; source variables reconstructed from {exp}.main.qualtrics.csv and its analysis Rmd read as text.",
            f"Exclusions: {AUDIT[exp]['complete']} complete eligible responses, "
            f"{AUDIT[exp]['after_attention']} after the specified attention check, "
            f"{AUDIT[exp]['after_named_exclusions']} after the named exclusions. "
            "Participant IDs and survey ResponseIds are unique in the retained human sample.",
            f"Data identify {len(t)} treatment and {len(c)} control people; the paper does not print these arm counts.",
            "Means/SD reproduction uses the deposited get_summary_stats then round sequence: "
            "three-decimal summaries followed by R-compatible two-decimal rounding. "
            "The reproduced descriptive entries show that display calculation; computed fields retain full precision.",
        ]
        if kind == "lay":
            notes.append("Each rating item is averaged over eligible judges within idea; creativity is the mean "
                         "of three originality and three appropriateness items. Idea scores are then averaged "
                         "within participant. No included judge-by-idea row has a missing rating item.")
        else:
            notes.append("Novelty_ha/ya/ak and Practicality_ha/ya/ak are averaged across the three experts; "
                         "creativity averages those six ratings. Other outcomes use their three corresponding "
                         "Articulate_, Verbosity_, notnew_, incnew_, or radnew_ columns. "
                         "Multiple ideas are averaged within participant before arm summaries.")
        if exp == "Exp1":
            notes.append("Lay ratings join idea_text_id; expert ratings join the first CSV index column "
                         "(R name X), following the respective deposited code. Fluency uses idea_count_jc.")
        if exp == "Exp2A":
            notes.append("The literal condition None is Human-only and is preserved when reading CSV. "
                         "Original t tests use the residual variance from all three randomized arms; "
                         "the requested HC2 contrast includes only the two named arms.")
        if exp == "Exp2B":
            notes.append("ChatbotHuman and HumanOnly identify the 200 people. The 100 ChatbotOnly rows "
                         "enter only reproduction of the paper's three-arm residual variance and never "
                         "enter human counts or the requested HC2 effect.")
        if exp in ["Exp4", "Exp5"]:
            notes.append("Original t tests use the four-cell model residual variance. Pooled original t "
                         "tests use equal-weight marginal cell means; requested computed pooled arm "
                         "means weight each participant equally and OLS includes only the arm indicator.")
        if exp == "Exp5":
            notes.append("The deposited file Exp5.rating.link_EmpathyHigh.csv corresponds to "
                         "Exp5.rating.link_High.csv named in the Rmd. H and B prefixes distinguish "
                         "overlapping idea IDs across the High and Baseline rating links.")
        if st["test"]["type"] == "F":
            level = "High constraints" if exp == "Exp4" else "Baseline empathy"
            notes.append(f"The reported type-III F reproduces as the technology simple effect at {level} "
                         "under default R treatment contrasts, despite being labelled a main effect. "
                         "The means/SD checks come from the same sample in Supplementary Table 1. "
                         "As required by the named combined arms, the new computed HC2 result is the "
                         "pooled unadjusted contrast, identical to the corresponding pooled record; "
                         "these are shared-sample results, not independent evidence.")
        if percentage:
            notes.append("Outcome units are percent (0-100), and difference and SE are percentage points; "
                         "no direction reversal is applied to treatment minus control.")
        if name == "top_ranked_creativity_share":
            notes.append(f"A participant scores 100 when their mean lay creativity exceeds the pooled "
                         f"80th percentile ({AUDIT[exp]['top20_cutoff']:.15g}; R type-7 quantile), otherwise 0. "
                         f"This gives {np.count_nonzero(t)}/{len(t)} and {np.count_nonzero(c)}/{len(c)}. "
                         "The printed chi-square reproduces as the binomial likelihood-ratio test. "
                         "The code establishes a participant outcome despite the extraction's provisional output unit.")
        if name in ["not_new", "incrementally_new", "radically_new"]:
            notes.append("For each participant, average the three binary expert classifications and multiply "
                         "by 100. Reproduction checks the printed percentages and human sample count. "
                         "The original judge-random-intercept logistic z tests are not refitted; the new "
                         "HC2 SE accounts for all three ratings belonging to one randomized person.")
        locators = list(dict.fromkeys([studies[e["study_id"]]["counts_source"]["locator"]] +
                                     [s["locator"] for s in summary_source["sources"]] +
                                     [s["locator"] for s in e["sources"]]))
        notes.append("Printed sources: " + "; ".join(locators) + ".")
        failed = [item for item in checks if not item["match"]]
        if failed:
            discrepancies = []
            for item in failed:
                field = item["statistic"]
                detail = f"{field}: printed {item['printed']}, reproduced {item['computed']}"
                if field in summaries:
                    detail += f" (unrounded {summaries[field]})"
                discrepancies.append(detail)
            reason = "Reproduction failed at printed precision: " + "; ".join(discrepancies) + "."
            if name == "fluency":
                reason += " The overall mean, n=233, and p=0.149 reproduce, but the printed t=1.42 does not."
            notes.append(reason + " No derived participant summaries, difference, or HC2 SE are released. "
                         "The se_type field records the specified method only.")
            computed = withheld_summary()
            skipped.append({"slug": e["slug"], "reason": reason})
        else:
            computed = hc2_summary(t, c)
            notes.append("The computed block uses one outcome per randomized person, SD denominator n-1, "
                         "and OLS(outcome ~ intercept + treatment) with HC2. "
                         "Its SE is independently checked against sqrt(s_t^2/n_t + s_c^2/n_c). "
                         "Assignment is individual, so n_clusters is null; no within-person first round applies.")
        results.append({"slug": e["slug"], "round": "all", "reproduced": checks,
                        "computed": computed, "notes": " ".join(notes)})
    return results, skipped


def main():
    extraction_text = text_file(BASE / "extraction/c010.json")
    extraction = json.loads(extraction_text)
    datasets = {}
    for exp in EXPS:
        sample = clean_main(exp)
        datasets[(exp, "lay")] = lay_scores(exp, sample)
        datasets[(exp, "expert")] = expert_scores(exp, sample)
    if "--audit" in sys.argv:
        audit_only(extraction, datasets)
        return
    source_provenance()
    results, skipped = make_results(extraction, datasets)
    assert len(results) == len(extraction["estimates"])
    assert len({r["slug"] for r in results}) == len(results)
    assert (BASE / "extraction/c010.json").read_text(encoding="utf-8") == extraction_text, "Extraction changed during run"
    obj = {"cid": "c010", "analyst": "B", "script": SCRIPT.as_posix(),
           "data_files": READ_FILES, "results": results, "skipped": skipped}
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with OUTPUT.open(encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == obj
    print(json.dumps({"cid": "c010", "n_results": len(results),
                      "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
                      "n_skipped": len(skipped)}))
    for item in skipped:
        print(item["slug"], item["reason"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
