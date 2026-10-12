"""Independent analyst B reanalysis of c526. Run with python -I -B B.py.

Only B.json is written. Deposit programs are read as text, never executed.
The beta mixed models are independently implemented with a Laplace likelihood,
matching the authors' reader-intercept glmmTMB specification. Participant-level
contrasts are calculated only after the published model benchmarks reproduce.
"""

import sys

sys.dont_write_bytecode = True

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
from scipy.optimize import minimize
from scipy.special import digamma, expit, gammaln, logit, polygamma
from scipy.stats import norm


BASE = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEPOSIT = Path(
    "D:/projects/ai-skill-atlas/creativity-data/"
    "github-paul-rottger-ai-distortion/ai-distortion-unpacked/ai-distortion-HEAD"
)
SCRIPT = BASE / "analysis/c526/B.py"
OUTPUT = BASE / "analysis/c526/B.json"
ARMS = ["writer", "none", "prompting", "reranking"]
KEYS = ["writer_id", "proposition_id"]
FILES_READ = []


def remember(path):
    path = Path(path)
    name = path.as_posix()
    if name not in FILES_READ:
        FILES_READ.append(name)
    return path


def text_file(path):
    return remember(path).read_text(encoding="utf-8")


def csv_file(relative_path):
    return pd.read_csv(remember(DEPOSIT / relative_path))


def check(statistic, printed, computed, digits=None):
    if isinstance(computed, (np.integer, np.floating)):
        computed = computed.item()
    if digits is None:
        match = computed == printed
    else:
        match = format(computed, f".{digits}f") == format(printed, f".{digits}f")
    return {
        "statistic": statistic,
        "printed": printed,
        "computed": computed,
        "match": bool(match),
    }


class ReaderBetaModel:
    """Beta logit model with four cell intercepts and a normal reader intercept.

    For each outer parameter vector, Newton iterations find the independent
    scalar random-intercept modes. Integrating them by Laplace approximation
    gives sum(log beta density) - sum(b^2)/(2*sigma^2) - G*log(sigma)
    - sum(log(H))/2, where H is the random-effects negative Hessian.
    This is the same ML approximation used by glmmTMB, not a beta GLM or OLS.
    """

    def __init__(self, frame, outcome):
        self.arm = pd.Categorical(frame["analysis_arm"], categories=ARMS).codes
        self.group, readers = pd.factorize(frame["rater_id"], sort=True)
        self.n_groups = len(readers)
        y = frame[outcome].to_numpy(dtype=float) / 100
        n = len(y)
        assert np.isfinite(y).all() and ((y >= 0) & (y <= 1)).all()
        # Authors' squeeze01 is applied to the entire preferred analysis sample.
        self.y = (np.clip(y, 0, 1) * (n - 1) + 0.5) / n
        self.log_y = np.log(self.y)
        self.log_1my = np.log1p(-self.y)
        self.log_odds = self.log_y - self.log_1my

    def objective(self, theta):
        phi = np.exp(theta[4])
        sigma = np.exp(theta[5])
        precision = 1 / sigma**2
        fixed = theta[self.arm]
        b = np.zeros(self.n_groups)
        for _ in range(100):
            mu = expit(fixed + b[self.group])
            alpha, beta = mu * phi, (1 - mu) * phi
            t = phi * mu * (1 - mu)
            score_mu = self.log_odds - digamma(alpha) + digamma(beta)
            d1 = t * score_mu
            d2 = t * (1 - 2 * mu) * score_mu - t**2 * (
                polygamma(1, alpha) + polygamma(1, beta)
            )
            h = precision - np.bincount(
                self.group, weights=d2, minlength=self.n_groups
            )
            if not np.isfinite(h).all():
                return np.inf
            # Conditional beta likelihoods need not be concave away from the
            # mode. Use a positive curvature floor while approaching it; a
            # negative intermediate curvature must not truncate the outer
            # likelihood's domain. At convergence the true Hessian is used.
            step = (
                np.bincount(self.group, weights=d1, minlength=self.n_groups)
                - precision * b
            ) / np.maximum(h, precision)
            b += np.clip(step, -0.5, 0.5)
            if np.max(np.abs(step)) < 1e-11:
                break
        else:
            raise RuntimeError("Reader random-intercept mode did not converge")
        if np.any(h <= 0):
            return np.inf
        mu = expit(fixed + b[self.group])
        alpha, beta = mu * phi, (1 - mu) * phi
        log_density = (
            gammaln(phi)
            - gammaln(alpha)
            - gammaln(beta)
            + (alpha - 1) * self.log_y
            + (beta - 1) * self.log_1my
        )
        return -float(
            log_density.sum()
            - 0.5 * precision * np.dot(b, b)
            - self.n_groups * np.log(sigma)
            - 0.5 * np.log(h).sum()
        )

    def fit(self):
        start = np.r_[
            logit([self.y[self.arm == i].mean() for i in range(4)]),
            np.log(3),
            np.log(0.5),
        ]
        fit = minimize(
            # Rescaling improves line searches; the maximizer is unchanged.
            lambda theta: self.objective(theta) / len(self.y),
            start,
            method="BFGS",
            jac="3-point",
            options={"gtol": 1e-9, "maxiter": 200, "finite_diff_rel_step": 1e-4},
        )
        self.fit_result = fit
        self.theta = fit.x
        self.gradient_max = float(np.max(np.abs(fit.jac)) * len(self.y))
        if (
            not np.isfinite(fit.fun)
            or not np.isfinite(fit.x).all()
            or not np.isfinite(self.gradient_max)
            or self.gradient_max > 1e-3
        ):
            raise RuntimeError(
                f"Outer optimization not converged: {fit.message}; "
                f"max absolute gradient {self.gradient_max}"
            )
        self.predictions = expit(self.theta[:4]) * 100
        self.ame = self.predictions - self.predictions[0]
        self.odds_ratio = np.exp(self.theta[:4] - self.theta[0])
        return self

    def contrast_p_value(self):
        # Observed Hessian of the same marginal likelihood, including nuisance
        # parameters. The contrast is log odds for reranking minus none.
        theta = self.theta
        step = 2e-4
        basis = np.eye(len(theta)) * step
        hessian = np.zeros((len(theta), len(theta)))
        f0 = self.objective(theta)
        for i in range(len(theta)):
            hessian[i, i] = (
                self.objective(theta + basis[i])
                - 2 * f0
                + self.objective(theta - basis[i])
            ) / step**2
            for j in range(i):
                value = (
                    self.objective(theta + basis[i] + basis[j])
                    - self.objective(theta + basis[i] - basis[j])
                    - self.objective(theta - basis[i] + basis[j])
                    + self.objective(theta - basis[i] - basis[j])
                ) / (4 * step**2)
                hessian[i, j] = hessian[j, i] = value
        assert np.linalg.eigvalsh(hessian).min() > 0
        contrast = np.array([0, -1, 0, 1, 0, 0], dtype=float)
        variance = contrast @ np.linalg.solve(hessian, contrast)
        z = (contrast @ theta) / np.sqrt(variance)
        return float(2 * norm.sf(abs(z)))


def participant_contrasts(frame, outcome):
    # The outcome is the final AI-assisted paragraph rating, on the original
    # 0-100 scale. The shared unaided reference belongs to the reproduction
    # model; it is not subtracted separately from each participant's outcome.
    ai = frame.loc[frame["analysis_arm"].isin(["none", "reranking"])]
    paragraphs = ai.groupby(
        KEYS + ["analysis_arm", "proposition_number"], as_index=False
    )[outcome].mean()
    assert paragraphs.groupby(["writer_id", "analysis_arm"]).size().max() == 1
    people = paragraphs.groupby(["writer_id", "analysis_arm"])[outcome].mean()
    paired = people.unstack("analysis_arm")[["reranking", "none"]].dropna()
    treatment = paired["reranking"].to_numpy()
    control = paired["none"].to_numpy()
    delta = treatment - control
    n = len(paired)
    all_result = {
        "n_treatment": n,
        "n_control": n,
        "treatment_mean": float(treatment.mean()),
        "treatment_sd": float(treatment.std(ddof=1)),
        "control_mean": float(control.mean()),
        "control_sd": float(control.std(ddof=1)),
        "difference": float(delta.mean()),
        "difference_se": float(delta.std(ddof=1) / np.sqrt(n)),
        "se_type": "paired",
        "n_clusters": None,
    }

    # First round means actual first proposition, including participants whose
    # other conditions later fail the preference restriction. It is not the
    # earliest retained proposition, nor restricted to the paired sample.
    first = paragraphs.loc[paragraphs["proposition_number"].eq(1)].copy()
    assert first["writer_id"].is_unique
    indicator = first["analysis_arm"].eq("reranking").to_numpy(dtype=float)
    y = first[outcome].to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(y)), indicator])
    bread = np.linalg.inv(x.T @ x)
    coef = bread @ x.T @ y
    residual = y - x @ coef
    leverage = np.einsum("ij,jk,ik->i", x, bread, x)
    meat = x.T @ ((residual**2 / (1 - leverage))[:, None] * x)
    vcov_hc2 = bread @ meat @ bread
    treatment = y[indicator == 1]
    control = y[indicator == 0]
    nt, nc = len(treatment), len(control)
    assert np.isclose(coef[1], treatment.mean() - control.mean(), atol=1e-10)
    assert np.isclose(
        vcov_hc2[1, 1],
        treatment.var(ddof=1) / nt + control.var(ddof=1) / nc,
        atol=1e-10,
    )
    first_result = {
        "n_treatment": nt,
        "n_control": nc,
        "treatment_mean": float(treatment.mean()),
        "treatment_sd": float(treatment.std(ddof=1)),
        "control_mean": float(control.mean()),
        "control_sd": float(control.std(ddof=1)),
        "difference": float(coef[1]),
        "difference_se": float(np.sqrt(vcov_hc2[1, 1])),
        "se_type": "HC2",
        "n_clusters": None,
    }
    return all_result, first_result


def main():
    extraction = json.loads(text_file(BASE / "extraction/c526.json"))
    retrieval = json.loads(text_file(BASE / "retrieval.json"))["c526"]
    text_file(retrieval["md_path"])
    for path in [
        BASE.parent / "creativity-codebook.md",
        BASE / "extraction-spec.md",
        Path("D:/projects/ai-skill-atlas/creativity-data/manifest.json"),
        DEPOSIT / "README.md",
        DEPOSIT / "data/README.md",
        DEPOSIT / "analysis/utils_r/data_loading.R",
        DEPOSIT / "analysis/3_mitigation_study/phase_2_distortion_scale_variables.R",
        DEPOSIT / "analysis/3_mitigation_study/phase_2_distortion_side_effects.R",
        DEPOSIT / "analysis/data_aggregation.py",
    ]:
        text_file(path)

    with pymupdf.open(remember(retrieval["pdf_path"])) as main_pdf:
        main_clarity_text = main_pdf[7].get_text()
        main_counts_text = main_pdf[10].get_text()
        assert "-26.9%" in main_clarity_text
        assert "769 writers and 2,543 readers" in main_counts_text
        assert "5,016 paragraphs in Study 3" in main_pdf[11].get_text()

    with pymupdf.open(remember(DEPOSIT / "supplementary_materials.pdf")) as supplement:
        supplement_title = supplement[0].get_text()
        assert "October 8, 2026" in supplement_title
        assert "19,102 observations" in supplement[195].get_text()
        assert "mitigation_condition + (1 | reader_id)" in supplement[195].get_text()
        tables = [table.extract() for table in supplement[199].find_tables().tables]
        assert len(tables) == 6
    table_map = {
        "paragraph_formality": (0, "S286"),
        "paragraph_clarity": (1, "S287"),
        "paragraph_informativeness": (2, "S288"),
        "paragraph_relevance": (4, "S290"),
    }

    writers = csv_file("data/followup_mitigation_phase_1/participants.csv")
    responses = csv_file("data/followup_mitigation_phase_1/proposition_responses.csv")
    paragraph_pool = csv_file("data/followup_mitigation_phase_1/paragraphs.csv")
    readers = csv_file("data/followup_mitigation_phase_2/participants.csv")
    ratings = csv_file("data/followup_mitigation_phase_2/annotations.csv")
    aggregated = csv_file("data/followup_mitigation_phase_2/annotations_aggregated.csv")
    # These deposited summaries were inspected as provenance, not substituted
    # for independently fitting the model or aggregating the participant data.
    for outcome in table_map:
        csv_file(
            "results/followup_mitigation_phase_2_distortion/preferred/"
            + outcome + "_by_mitigation.csv"
        )
    csv_file(
        "results/followup_mitigation_phase_2_distortion/preferred/"
        "mitigation_significance_details.csv"
    )

    assert writers["writer_id"].is_unique and readers["rater_id"].is_unique
    assert not responses.duplicated(KEYS).any()
    assert not ratings.duplicated(["rater_id"] + KEYS + ["paragraph_type"]).any()
    assert set(ratings["writer_id"]) == set(writers["writer_id"])
    assert set(ratings["rater_id"]) == set(readers["rater_id"])
    assert responses.groupby("writer_id")["model_mitigation_condition"].nunique().eq(3).all()
    assert responses.groupby("writer_id")["proposition_number"].apply(
        lambda x: set(x) == {1, 2, 3}
    ).all()
    timestamp_order = responses.groupby("writer_id")["finishedIntroTimestamp"].rank(
        method="dense"
    )
    assert timestamp_order.eq(responses["proposition_number"]).all()
    assert responses["writer_preference"].isin(["edited", "equal", "original"]).all()

    # Replace model paragraphs with edited paragraphs where an edited version
    # exists, then remove both paragraphs from pairs preferring the original.
    has_edit = ratings["paragraph_type"].eq("edited").groupby(
        [ratings["writer_id"], ratings["proposition_id"]]
    ).transform("any")
    edited = ratings.loc[~(ratings["paragraph_type"].eq("model") & has_edit)].copy()
    edited = edited.merge(
        responses[KEYS + ["writer_preference", "proposition_number"]],
        on=KEYS, how="left", validate="many_to_one",
    )
    assert edited["writer_preference"].notna().all()
    preferred = edited.loc[edited["writer_preference"].ne("original")].copy()
    preferred["analysis_arm"] = np.where(
        preferred["paragraph_type"].eq("writer"),
        "writer", preferred["model_mitigation_condition"],
    )
    assert preferred[list(table_map)].notna().all().all()
    assert set(preferred["analysis_arm"]) == set(ARMS)

    count_checks = [
        check("study_writer_completers (main PDF p.11)", 769, writers["writer_id"].nunique()),
        check("study_reader_completers (main PDF p.11)", 2543, readers["rater_id"].nunique()),
        check("paragraph_pool (main PDF p.12)", 5016, len(paragraph_pool)),
        check("preferred_rating_rows (supplement p.196, Section 8.5)", 19102, len(preferred)),
    ]
    report = {
        "cid": "c526", "analyst": "B", "script": SCRIPT.as_posix(),
        "data_files": FILES_READ, "results": [], "skipped": [],
    }
    for estimate in extraction["estimates"]:
        slug = estimate["slug"]
        outcome = "paragraph_" + slug.split("_")[1]
        print("Refitting " + slug, flush=True)
        checks = copy.deepcopy(count_checks)
        table_index, table_number = table_map[outcome]
        model = ReaderBetaModel(preferred, outcome).fit()
        for i, row in enumerate(tables[table_index], start=1):
            assert ARMS[i] in row[0]
            checks.extend([
                check(
                    f"beta_model_{ARMS[i]}_vs_writer_OR (supplement p.200, Table {table_number})",
                    float(row[1]), float(model.odds_ratio[i]), 3,
                ),
                check(
                    f"beta_model_{ARMS[i]}_vs_writer_AME (supplement p.200, Table {table_number})",
                    float(row[5]), float(model.ame[i]), 3,
                ),
            ])
        if outcome == "paragraph_clarity":
            percent = float(100 * (model.ame[3] - model.ame[1]) / model.ame[1])
            checks.append(check(
                "relative_change_in_distortion_percent (main PDF p.8, Section 2.5)",
                estimate["stats"]["paper_effect"]["value"], percent, 1,
            ))
            p_value = model.contrast_p_value()
            checks.append({
                "statistic": "reranking_vs_no_intervention_beta_model_p (main PDF p.8)",
                "printed": estimate["stats"]["p_value"],
                "computed": p_value, "match": bool(p_value < 0.001),
            })

        if not all(item["match"] for item in checks):
            failed = [item for item in checks if not item["match"]]
            reason = "Published values did not reproduce; no participant contrast computed. " + json.dumps(failed)
            report["results"].append({
                "slug": slug, "round": "all", "reproduced": checks,
                "computed": None, "notes": reason,
            })
            report["skipped"].append({"slug": slug, "reason": reason})
            continue

        # Independently validate the paragraph aggregation against the deposited
        # summary only after reproducing this outcome's published model.
        recomputed = ratings.groupby(KEYS + ["paragraph_type"])[outcome].mean()
        supplied = aggregated.set_index(KEYS + ["paragraph_type"])[outcome]
        assert np.allclose(recomputed.sort_index(), supplied.sort_index(), rtol=0, atol=1e-12)
        paired, first = participant_contrasts(preferred, outcome)
        full_counts = preferred.groupby("analysis_arm").agg(
            ratings=("writer_id", "size"), writers=("writer_id", "nunique")
        )
        common_notes = (
            f"Outcome {outcome}; treatment=reranking, control=none. "
            "All computed means, SDs, differences and SEs use the original 0-100 paragraph-rating scale. "
            "The reported percent attenuation is a reproduction benchmark, not the unit of the new contrast. "
            "No unaided-paragraph score is subtracted from the participant outcome. "
            "Reader ratings are averaged within the final AI paragraph, then within writer and condition; "
            "each writer has one proposition per condition, and every writer receives equal weight. "
            "SDs use n-1. The paper's preferred subset replaces unedited AI text with edited text wherever "
            "available and excludes writer-proposition pairs with writer_preference='original'; equal and "
            "edited preferences are retained. These are post-treatment preference restrictions, so these "
            "contrasts describe the retained sample rather than all randomized writers. "
            f"The reproduction sample has {len(preferred)} reader-paragraph rows, "
            f"{preferred['writer_id'].nunique()} distinct writers, and "
            f"{preferred['rater_id'].nunique()} readers. Reranking has "
            f"{int(full_counts.loc['reranking', 'ratings'])} ratings of "
            f"{int(full_counts.loc['reranking', 'writers'])} writers; none has "
            f"{int(full_counts.loc['none', 'ratings'])} ratings of "
            f"{int(full_counts.loc['none', 'writers'])} writers before pair completion. "
            "Reproduction uses an independently fitted beta/logit mixed model with reader random intercepts, "
            "all four categories (unaided writer, none, prompting, reranking), and "
            "y=((rating/100)*(N-1)+0.5)/N. Average marginal effects use random effects set to zero, "
            "as in the authors' marginaleffects re.form=NA specification. "
            f"Maximum absolute likelihood gradient={model.gradient_max:.8g}. "
            "The downloaded supplement is dated October 8, 2026 and has a changed title; "
            "it is later than the saved arXiv v2 of June 29, 2026. Its Study 3 sample, models, "
            "interventions, counts, and reader-only regression specification match the saved main paper "
            "and posted data. Its Section 8.5 and Tables S286-S290 provide numerical benchmarks "
            "where the main paper has only figures. The main-paper clarity effect also reproduces "
            "at -26.9 percent, providing a direct version cross-check. No figure values are used. "
            f"This outcome's benchmarks come from supplement PDF p.200, Table {table_number}; "
            "all counts and model checks refer to the full published analysis. "
            "No printed outcome-specific distinct-writer counts or first-round statistics are available."
        )
        report["results"].append({
            "slug": slug, "round": "all", "reproduced": copy.deepcopy(checks),
            "computed": paired,
            "notes": common_notes + " Paired analysis retains only writers with both eligible "
            "reranking and none outcomes. The difference is the mean within-writer difference; "
            "its SE is SD(within-writer differences)/sqrt(number of complete pairs). "
            "Both arm SDs are computed over exactly those same paired writers.",
        })
        report["results"].append({
            "slug": slug, "round": "first_round", "reproduced": copy.deepcopy(checks),
            "computed": first,
            "notes": common_notes + " First round is proposition_number=1, verified against "
            "the chronological rank of finishedIntroTimestamp for all 769 writers. Retain the "
            "writer's actual first condition only if it is reranking or none and passes the same "
            "preference restriction; do not condition on later-round eligibility. The contrast "
            "is OLS of one outcome per writer on an intercept and treatment indicator, with "
            "HC2 covariance (residual squared divided by 1 minus leverage). Reproduction entries "
            "validate the full published model before deriving this new first-round result; "
            "they are not claims that the paper printed first-round statistics.",
        })
        print("Reproduced " + slug + "; paired and first-round contrasts computed.", flush=True)

    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    with OUTPUT.open("r", encoding="utf-8") as fh:
        parsed = json.load(fh)
    assert parsed == report
    print(json.dumps({
        "cid": "c526",
        "n_results": len(parsed["results"]),
        "n_reproduced": sum(
            bool(result["reproduced"]) and all(item["match"] for item in result["reproduced"])
            for result in parsed["results"]
        ),
        "n_skipped": len(parsed["skipped"]),
    }), flush=True)


if __name__ == "__main__":
    main()
