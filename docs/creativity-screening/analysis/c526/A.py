"""Independent Analyst A reanalysis of c526.

Run: python -I -B C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/analysis/c526/A.py
Only A.json is written. No deposited code is executed or imported.
The beta mixed model is independently implemented with a scalar Laplace
integral for each reader, matching glmmTMB's random-intercept likelihood.
"""

import argparse
import copy
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd
import pymupdf
from scipy.optimize import minimize
from scipy.special import digamma, expit, gammaln, logit, polygamma
from scipy.stats import norm
import statsmodels.api as sm


ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path("D:/projects/ai-skill-atlas/creativity-data/"
               "github-paul-rottger-ai-distortion/ai-distortion-unpacked/ai-distortion-HEAD")
SCRIPT = ROOT / "analysis/c526/A.py"
OUTPUT = ROOT / "analysis/c526/A.json"
CONDITIONS = ["writer", "none", "prompting", "reranking"]
KEYS = ["writer_id", "proposition_id"]
OUTCOMES = ["clarity", "informativeness", "relevance", "formality"]
DATA_FILES = []


def record_path(path):
    path = Path(path)
    value = path.as_posix()
    if value not in DATA_FILES:
        DATA_FILES.append(value)
    return path


def read_csv(relative):
    return pd.read_csv(record_path(DEPOSIT / relative))


def read_text(path):
    return record_path(path).read_text(encoding="utf-8")


class ReaderBetaLaplace:
    """Beta(mu * phi, (1-mu) * phi), logit(mu)=cell_intercept+u_reader.

    u_reader ~ Normal(0, sigma**2). Parameters are four cell intercepts,
    log(phi), log(sigma). Integrate the reader intercept by Laplace's
    approximation at its conditional mode. This is a reader random effect,
    used ONLY to reproduce the paper, not for the final writer-level SE.
    """

    def __init__(self, data, outcome):
        n = len(data)
        y = np.clip(data[outcome].to_numpy(dtype=float) / 100.0, 0.0, 1.0)
        self.y = (y * (n - 1) + 0.5) / n
        self.ly = np.log(self.y)
        self.l1y = np.log1p(-self.y)
        self.c = pd.Categorical(data["condition"], categories=CONDITIONS).codes
        self.g, levels = pd.factorize(data["rater_id"], sort=True)
        self.ng = len(levels)
        self.n = n
        self.calls = 0

    def group_sum(self, values):
        return np.bincount(self.g, weights=values, minlength=self.ng)

    def derivatives(self, eta, phi):
        mu = expit(eta)
        v = mu * (1.0 - mu)
        v2 = v * (1.0 - 2.0 * mu)
        a, b = mu * phi, (1.0 - mu) * phi
        da, db = digamma(a), digamma(b)
        ta, tb = polygamma(1, a), polygamma(1, b)
        ell_mu = phi * (self.ly - self.l1y - da + db)
        ell_mumu = -phi**2 * (ta + tb)
        ell_eta = ell_mu * v
        ell_etaeta = ell_mumu * v**2 + ell_mu * v2
        return mu, v, v2, a, b, da, db, ta, tb, ell_mu, ell_mumu, ell_eta, ell_etaeta

    def value_gradient(self, theta):
        self.calls += 1
        phi = math.exp(theta[4])
        invvar = math.exp(-2.0 * theta[5])
        eta0 = theta[self.c]
        u = np.zeros(self.ng, dtype=float)
        lower = np.full(self.ng, -50.0)
        upper = np.full(self.ng, 50.0)
        for _ in range(100):
            parts = self.derivatives(eta0 + u[self.g], phi)
            score = self.group_sum(parts[-2]) - u * invvar
            h = invvar - self.group_sum(parts[-1])
            lower = np.where(score > 0.0, u, lower)
            upper = np.where(score < 0.0, u, upper)
            # Safeguarded Newton: extreme outer line-search trials can have
            # locally nonconcave beta likelihoods away from the reader mode.
            step = np.clip(score / np.maximum(h, 1e-10), -1.0, 1.0)
            candidate = u + step
            outside = (candidate < lower) | (candidate > upper)
            candidate = np.where(outside, (lower + upper) / 2.0, candidate)
            actual_step = candidate - u
            u = candidate
            if np.max(np.abs(actual_step)) < 2e-12:
                break
        else:
            raise ArithmeticError("Reader conditional modes did not converge")

        parts = self.derivatives(eta0 + u[self.g], phi)
        mu, v, v2, a, b, da, db, ta, tb, lm, lmm, le, lee = parts
        h = invvar - self.group_sum(lee)
        if np.any(h <= 0.0) or np.max(np.abs(self.group_sum(le) - u * invvar)) > 1e-6:
            raise ArithmeticError("Reader modes fail curvature/score check")
        ell = (gammaln(phi) - gammaln(a) - gammaln(b)
               + (a - 1.0) * self.ly + (b - 1.0) * self.l1y)
        # Gaussian normalization and the sqrt(2*pi) Laplace factor cancel.
        ll = (ell.sum() - 0.5 * invvar * np.dot(u, u)
              - self.ng * theta[5] - 0.5 * np.log(h).sum())

        p2a, p2b = polygamma(2, a), polygamma(2, b)
        lmmm = phi**3 * (-p2a + p2b)
        v3 = v * ((1.0 - 2.0 * mu)**2 - 2.0 * v)
        leee = lmmm * v**3 + 3.0 * lmm * v * v2 + lm * v3
        h_u = -self.group_sum(leee)
        grad = np.empty(6, dtype=float)
        for k in range(4):
            selected = (self.c == k)
            score_theta = self.group_sum(lee * selected)
            h_theta = -self.group_sum(leee * selected)
            du = score_theta / h
            grad[k] = (le[selected].sum()
                       - 0.5 * np.sum((h_theta + h_u * du) / h))

        l_logphi = phi * (digamma(phi) - mu * da - (1.0 - mu) * db
                         + mu * self.ly + (1.0 - mu) * self.l1y)
        lm_logphi = lm + phi**2 * (-mu * ta + (1.0 - mu) * tb)
        lmm_logphi = 2.0 * lmm - phi**3 * (mu * p2a + (1.0 - mu) * p2b)
        le_logphi = v * lm_logphi
        lee_logphi = v**2 * lmm_logphi + v2 * lm_logphi
        du = self.group_sum(le_logphi) / h
        h_theta = -self.group_sum(lee_logphi)
        grad[4] = l_logphi.sum() - 0.5 * np.sum((h_theta + h_u * du) / h)

        du = 2.0 * u * invvar / h
        grad[5] = (np.sum(u**2 * invvar - 1.0)
                   - 0.5 * np.sum((-2.0 * invvar + h_u * du) / h))
        return float(-ll), -grad

    def fit(self):
        start = np.r_[
            [logit(self.y[self.c == k].mean()) for k in range(4)],
            math.log(3.0), math.log(0.5)
        ]
        # Independently check the analytic Laplace gradient before optimizing.
        analytical = self.value_gradient(start)[1]
        eps = 1e-5
        numerical = np.empty(6)
        for j in range(6):
            delta = np.zeros(6)
            delta[j] = eps
            numerical[j] = (self.value_gradient(start + delta)[0]
                            - self.value_gradient(start - delta)[0]) / (2.0 * eps)
        if not np.allclose(analytical, numerical, rtol=2e-6, atol=2e-4):
            raise ArithmeticError(f"Laplace gradient check failed: {analytical} vs {numerical}")
        fitted = minimize(
            self.value_gradient, start, jac=True, method="L-BFGS-B",
            bounds=[(-7.0, 7.0)] * 4 + [(-5.0, 7.0), (-7.0, 2.0)],
            options={"ftol": 1e-14, "gtol": 1e-6, "maxiter": 250, "maxls": 40},
        )
        val, gradient = self.value_gradient(fitted.x)
        if not fitted.success or np.max(np.abs(gradient)) > 0.01:
            raise ArithmeticError(f"Beta model failed: {fitted.message}; gradient={gradient}")
        # Observed information is needed only to reproduce the paper's p bound.
        hessian = np.empty((6, 6))
        eps = 1e-4
        for j in range(6):
            delta = np.zeros(6)
            delta[j] = eps
            hessian[:, j] = (self.value_gradient(fitted.x + delta)[1]
                             - self.value_gradient(fitted.x - delta)[1]) / (2.0 * eps)
        hessian = (hessian + hessian.T) / 2.0
        if np.linalg.eigvalsh(hessian).min() <= 0:
            raise ArithmeticError("Nonpositive observed information")
        covariance = np.linalg.inv(hessian)
        prediction = expit(fitted.x[:4]) * 100.0
        contrast = np.array([0.0, -1.0, 0.0, 1.0, 0.0, 0.0])
        z = float(contrast @ fitted.x / np.sqrt(contrast @ covariance @ contrast))
        return {
            "predictions": dict(zip(CONDITIONS, map(float, prediction))),
            "ame_none": float(prediction[1] - prediction[0]),
            "ame_prompting": float(prediction[2] - prediction[0]),
            "ame_reranking": float(prediction[3] - prediction[0]),
            "or_none": float(np.exp(fitted.x[1] - fitted.x[0])),
            "or_reranking": float(np.exp(fitted.x[3] - fitted.x[0])),
            "relative_percent": float(100.0 * (prediction[3] - prediction[1])
                                      / (prediction[1] - prediction[0])),
            "reranking_vs_none_p": float(2.0 * norm.sf(abs(z))),
            "objective": val,
            "max_gradient": float(np.max(np.abs(gradient))),
            "calls": self.calls,
        }


def reproduction(statistic, printed, computed, digits=None, bound=None):
    if bound is not None:
        matched = computed < bound
    elif digits is None:
        matched = computed == printed
    else:
        matched = round(computed, digits) == printed
    return {"statistic": statistic, "printed": printed,
            "computed": computed, "match": bool(matched)}


def participant_contrasts(data, outcome):
    ai = data[data["condition"].isin(["none", "reranking"])].copy()
    # One paragraph per writer/condition; average its reader ratings first.
    by_person = ai.groupby(["writer_id", "condition"], observed=True)[outcome].mean()
    paired = by_person.unstack("condition")[["reranking", "none"]].dropna()
    treatment, control = paired["reranking"], paired["none"]
    differences = treatment - control
    n = len(paired)
    all_result = {
        "n_treatment": n, "n_control": n,
        "treatment_mean": float(treatment.mean()), "treatment_sd": float(treatment.std(ddof=1)),
        "control_mean": float(control.mean()), "control_sd": float(control.std(ddof=1)),
        "difference": float(differences.mean()),
        "difference_se": float(differences.std(ddof=1) / math.sqrt(n)),
        "se_type": "paired", "n_clusters": None,
    }
    # Actual first assigned task, not the earliest task surviving exclusion.
    first = ai[ai["proposition_number"] == 1].groupby(
        ["writer_id", "condition"], observed=True, as_index=False
    )[outcome].mean()
    assert not first["writer_id"].duplicated().any()
    t = first.loc[first["condition"] == "reranking", outcome]
    c = first.loc[first["condition"] == "none", outcome]
    indicator = (first["condition"] == "reranking").astype(float).to_numpy()
    design = np.column_stack([np.ones(len(first)), indicator])
    fitted = sm.OLS(first[outcome].to_numpy(), design).fit(cov_type="HC2")
    # With an intercept and a binary arm indicator, HC2 equals this identity.
    independent_se = math.sqrt(t.var(ddof=1) / len(t) + c.var(ddof=1) / len(c))
    assert np.isclose(fitted.bse[1], independent_se, rtol=1e-12)
    assert np.isclose(fitted.params[1], t.mean() - c.mean(), rtol=1e-12, atol=1e-12)
    first_result = {
        "n_treatment": len(t), "n_control": len(c),
        "treatment_mean": float(t.mean()), "treatment_sd": float(t.std(ddof=1)),
        "control_mean": float(c.mean()), "control_sd": float(c.std(ddof=1)),
        "difference": float(fitted.params[1]), "difference_se": float(fitted.bse[1]),
        "se_type": "HC2", "n_clusters": None,
    }
    return all_result, first_result


def load_inputs():
    extraction = json.loads(read_text(ROOT / "extraction/c526.json"))
    retrieval = json.loads(read_text(ROOT / "retrieval.json"))["c526"]
    read_text(retrieval["md_path"])  # Complete main paper, references included.
    read_text(ROOT.parent / "creativity-codebook.md")
    read_text(ROOT / "extraction-spec.md")
    read_text(Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json"))
    # These documents/scripts are read strictly as text for data provenance.
    for name in ["README.md", "data/README.md", "analysis/data_aggregation.py",
                 "analysis/utils_r/data_loading.R",
                 "analysis/3_mitigation_study/phase_2_distortion_scale_variables.R",
                 "analysis/3_mitigation_study/phase_2_distortion_side_effects.R"]:
        read_text(DEPOSIT / name)

    with pymupdf.open(record_path(retrieval["pdf_path"])) as doc:
        main_text = "\n".join(page.get_text() for page in doc)
        assert "-26.9%" in main_text and "769 writers" in main_text
    with pymupdf.open(record_path(DEPOSIT / "supplementary_materials.pdf")) as doc:
        assert "October 8, 2026" in doc[0].get_text()
        assert "19,102" in doc[195].get_text()
        table_text = doc[199].get_text()
        assert all(s in table_text for s in ["11.344", "8.297", "25.324", "22.164",
                                             "9.559", "7.872", "30.394", "29.035"])

    writer_participants = read_csv("data/followup_mitigation_phase_1/participants.csv")
    reader_participants = read_csv("data/followup_mitigation_phase_2/participants.csv")
    paragraphs = read_csv("data/followup_mitigation_phase_1/paragraphs.csv")
    writer = read_csv("data/followup_mitigation_phase_1/proposition_responses.csv")
    raw = read_csv("data/followup_mitigation_phase_2/annotations.csv")
    aggregated = read_csv("data/followup_mitigation_phase_2/annotations_aggregated.csv")
    assert not writer.duplicated(KEYS).any()
    assert not raw.duplicated(["rater_id"] + KEYS + ["paragraph_type"]).any()
    assert set(writer.writer_id) == set(writer_participants.writer_id) == set(raw.writer_id)
    assert set(raw.rater_id) == set(reader_participants.rater_id)
    assert writer.groupby("writer_id").model_mitigation_condition.nunique().eq(3).all()
    assert writer.groupby("writer_id").proposition_number.apply(
        lambda x: sorted(x) == [1, 2, 3]).all()
    assert raw[["paragraph_" + x for x in OUTCOMES]].notna().all().all()
    assert set(raw.model_input_condition) == {"bullets-based"}

    # Cross-check the posted paragraph-level aggregates against raw ratings.
    actual_aggregates = raw.groupby(KEYS + ["paragraph_type"])[
        ["paragraph_" + x for x in OUTCOMES]].mean().sort_index()
    deposited_aggregates = aggregated.set_index(KEYS + ["paragraph_type"])[
        ["paragraph_" + x for x in OUTCOMES]].sort_index()
    assert actual_aggregates.index.equals(deposited_aggregates.index)
    assert np.allclose(actual_aggregates, deposited_aggregates, rtol=1e-12, atol=1e-12)

    # Edited paragraph supersedes its unedited AI counterpart in each task.
    has_edit = raw.groupby(KEYS).paragraph_type.transform(lambda x: (x == "edited").any())
    edited = raw.loc[~((raw.paragraph_type == "model") & has_edit)].copy()
    edited = edited.merge(writer[KEYS + ["writer_preference", "proposition_number"]],
                          on=KEYS, how="left", validate="many_to_one")
    assert edited.writer_preference.notna().all()
    preferred = edited.loc[edited.writer_preference != "original"].copy()
    preferred["condition"] = preferred.model_mitigation_condition.where(
        preferred.paragraph_type != "writer", "writer")

    counts = [
        reproduction("Study 3 writer completers (main PDF p. 11)", 769, writer.writer_id.nunique()),
        reproduction("Study 3 reader completers (main PDF p. 11)", 2543, raw.rater_id.nunique()),
        reproduction("Study 3 paragraph pool (main PDF p. 12; supplement p. 193)",
                     5016, len(paragraphs)),
        reproduction("Study 3 writer-proposition assignments (supplement p. 10, Table S15)",
                     2307, len(writer)),
        reproduction("Study 3 raw paragraph-reader observations (supplement p. 194)",
                     25422, len(raw)),
        reproduction("Preferred-subset regression observations (supplement p. 196 and p. 200)",
                     19102, len(preferred)),
    ]
    return extraction, preferred, counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnose", action="store_true", help="Fit and print only; do not write JSON")
    parser.add_argument("--outcome", choices=OUTCOMES)
    args = parser.parse_args()
    if args.outcome and not args.diagnose:
        parser.error("--outcome requires --diagnose, to prevent writing partial results")

    extraction, preferred, counts = load_inputs()
    # Transcribed from supplement PDF p. 200, Tables S286, S287, S288, S290.
    # Its Study 3 specification is identical to main PDF pp. 12-14; its date
    # and title differ from the saved arXiv v2. The main-paper clarity effect
    # is an additional independent, version-specific reproduction check.
    targets = {
        "clarity": ("S287", 11.344, 8.297, 1.903, 1.564),
        "informativeness": ("S288", 25.324, 22.164, 2.817, 2.464),
        "relevance": ("S290", 9.559, 7.872, 1.828, 1.614),
        "formality": ("S286", 30.394, 29.035, 3.587, 3.359),
    }
    results, skipped = [], []
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        name = next(x for x in OUTCOMES if slug == f"s3_{x}_reranking_vs_no_intervention")
        if args.outcome and args.outcome != name:
            continue
        print(f"Fitting published model: {name}", flush=True)
        model = ReaderBetaLaplace(preferred, "paragraph_" + name).fit()
        print(json.dumps({"outcome": name, **model}, ensure_ascii=True), flush=True)
        table, none_ame, rerank_ame, none_or, rerank_or = targets[name]
        checks = copy.deepcopy(counts)
        for label, printed, value in [
            ("No Intervention vs unaided reference AME", none_ame, model["ame_none"]),
            ("Reranking vs unaided reference AME", rerank_ame, model["ame_reranking"]),
            ("No Intervention vs unaided reference odds ratio", none_or, model["or_none"]),
            ("Reranking vs unaided reference odds ratio", rerank_or, model["or_reranking"]),
        ]:
            checks.append(reproduction(f"{label} (supplement PDF p. 200, Table {table})",
                                       printed, value, digits=3))
        if name == "clarity":
            checks.append(reproduction("Relative attenuation percent (main PDF p. 8, Section 2.5)",
                                       -26.9, model["relative_percent"], digits=1))
            checks.append(reproduction("Reranking vs No Intervention p (main PDF p. 8)",
                                       "<.001", model["reranking_vs_none_p"], bound=0.001))

        # Read deposited outputs only AFTER independently estimating the model.
        # They document the version correspondence; they are not fitted inputs.
        for suffix in ["by_mitigation", "by_model_and_mitigation"]:
            read_csv("results/followup_mitigation_phase_2_distortion/preferred/"
                     f"paragraph_{name}_{suffix}.csv")

        failures = [x for x in checks if not x["match"]]
        if failures:
            reason = ("Reproduction gate failed; no participant contrasts computed. "
                      + json.dumps(failures, ensure_ascii=True))
            skipped.append({"slug": slug, "reason": reason})
            print(reason, flush=True)
            continue

        all_result, first_result = participant_contrasts(preferred, "paragraph_" + name)
        shared_notes = (
            f"Outcome is reader-rated paragraph_{name} on the original 0-100 scale. "
            "Treatment is Reranking (model_mitigation_condition='reranking'); control is No Intervention "
            "('none'). Data mapping and exclusions were established by the main paper, supplement "
            "Sections 5.2/8.5, and the authors' R files read as text only. Within writer_id/proposition_id, "
            "use paragraph_type='edited' when available, otherwise 'model'; exclude both AI and human "
            "paragraphs when writer_preference='original'. The edited subset has 23,412 rating rows; "
            "the preferred subset has 19,102 (9,576 unaided, 3,262 none, 3,179 prompting, 3,085 reranking), "
            "from 730 distinct writers and 2,543 readers. It includes 648 control and 603 treatment "
            "writers before restricting to paired or first-round samples. Each writer has one task "
            "per condition; ratings are averaged within writer/condition with equal weight per writer. "
            "The reproduction entries concern the published full-sample preferred-subset regression, "
            "before complete-pair or first-round restriction. Reproduction independently maximizes the "
            "reader-random-intercept beta-regression Laplace likelihood after transforming y to "
            "((y/100)*(N-1)+0.5)/N; AMEs use inverse-logit predictions with reader effect set to zero. "
            "Analytic likelihood gradients were checked by central differences. The supplement is dated "
            "2026-10-08 and titled 'How AI writing assistance distorts perceptions of AI users and their "
            "opinions', while the saved main paper is arXiv:2604.22503v2 dated 2026-06-29. "
            "For these Study 3 outcomes, sample, intervention, reader-only model, and the main-paper "
            "clarity percentage agree; newer Study 1 specifications are not substituted. "
            f"Supplement PDF p. 200, Table {table}, supplies numeric AMEs/odds ratios for this outcome. "
            "The requested computed fields are raw participant-level outcome levels and treatment-minus-"
            "control differences in rating points, not the paper's normalized attenuation percentage. "
            "No unaided baseline is subtracted from these computed fields. SDs use denominator n-1. "
            "Preference exclusions follow the paper and are post-treatment selection, so these are "
            "conditional-sample contrasts rather than intention-to-treat estimates. "
        )
        if name == "clarity":
            shared_notes += (
                "The printed -26.9 percent is reproduced as 100*(AME_reranking-AME_none)/AME_none; "
                f"independently computed value={model['relative_percent']:.10f}. "
            )
        if name == "formality":
            shared_notes += "Higher formality means a more formal style, without an intrinsic creativity direction. "
        results.append({
            "slug": slug, "round": "all", "reproduced": copy.deepcopy(checks),
            "computed": all_result,
            "notes": shared_notes + (
                "Paired analysis retains only writers with both eligible conditions. Difference is "
                "mean(treatment_i-control_i); SE is SD(treatment_i-control_i)/sqrt(n). "
                "Both condition SDs are across this identical set of paired writers."
            ),
        })
        results.append({
            "slug": slug, "round": "first_round", "reproduced": copy.deepcopy(checks),
            "computed": first_result,
            "notes": shared_notes + (
                "First round is proposition_number=1 in the posted writer responses, joined by "
                "writer_id/proposition_id; it is not the first retained observation after exclusion. "
                "Writers first assigned Prompting do not enter this contrast. Eligible first-round "
                "ratings are averaged within writer; OLS on an intercept and treatment indicator "
                "uses HC2 robust standard errors. The paper prints no first-round-only outcome "
                "statistic, so reproduction entries validate the parent full-sample analysis."
            ),
        })
        print(json.dumps({"outcome": name, "all": all_result, "first_round": first_result}), flush=True)

    read_csv("results/followup_mitigation_phase_2_distortion/preferred/mitigation_significance_details.csv")
    if args.diagnose:
        return
    output = {"cid": "c526", "analyst": "A", "script": SCRIPT.as_posix(),
              "data_files": DATA_FILES, "results": results, "skipped": skipped}
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with OUTPUT.open(encoding="utf-8") as fh:
        confirmed = json.load(fh)
    assert confirmed == output
    print(json.dumps({"cid": "c526", "n_results": len(results),
                      "n_reproduced": sum(all(c["match"] for c in r["reproduced"]) for r in results),
                      "n_skipped": len(skipped)}), flush=True)


if __name__ == "__main__":
    main()
