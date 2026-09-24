// Pure data helpers shared by the app (ai-skill-atlas-explorer.jsx) and the
// smoke tests (scripts/smoke.mjs). No React, no DOM.

export const isPoolableEstimate = (e) =>
  Number.isFinite(e.effect_size_sd) && Number.isFinite(e.se) && e.se > 0;

export const isPlottableEstimate = (e) =>
  Number.isFinite(e.effect_size_sd) && (isPoolableEstimate(e) ||
    (Number.isFinite(e.ci_lower) && Number.isFinite(e.ci_upper) && e.ci_lower <= e.ci_upper));

// The browse view contains full-sample effects. Subgroup effects remain in
// study records and the full export, where they cannot enter the pooled mean.
export function filterEstimates(estimates, {
  paperKeys, designMode = "rct", comparisonType = "ai_vs_bau",
  outcomeMode = "without_ai", activeDomains = new Set(),
}) {
  const designClasses = { lab: "lab_rct", field: "field_rct", online: "online_rct", obs: "observational" };
  return estimates.filter(e => {
    const design = e.design_class || "field_rct";
    return paperKeys.has(e.paper_key) && e.is_subgroup !== true &&
      (designMode === "rct" ? design !== "observational" : design === designClasses[designMode]) &&
      (e.comparison_type || "ai_vs_bau") === comparisonType &&
      (outcomeMode !== "without_ai" || e.outcome_with_ai !== true) &&
      (activeDomains.size === 0 || activeDomains.has(e.learning_domain));
  });
}

// DerSimonian–Laird random-effects meta-analysis
// (same formula as the paper's 4-figures.do)
export function randomEffectsMean(estimates) {
  const valid = estimates.filter(isPoolableEstimate);
  if (valid.length === 0) return null;
  if (valid.length === 1) {
    const e = valid[0];
    return { mean: e.effect_size_sd, se: e.se, lo: e.effect_size_sd - 1.96 * e.se, hi: e.effect_size_sd + 1.96 * e.se, k: 1, tau2: 0, Q: 0 };
  }

  const w = valid.map(e => 1 / (e.se ** 2));
  const sumW = w.reduce((a, b) => a + b, 0);
  const muFE = valid.reduce((acc, e, i) => acc + w[i] * e.effect_size_sd, 0) / sumW;
  const Q = valid.reduce((acc, e, i) => acc + w[i] * (e.effect_size_sd - muFE) ** 2, 0);
  const k = valid.length;
  const sumW2 = w.reduce((a, b) => a + b * b, 0);
  const tau2 = Math.max(0, (Q - (k - 1)) / (sumW - sumW2 / sumW));

  const wRE = valid.map(e => 1 / (e.se ** 2 + tau2));
  const sumWRE = wRE.reduce((a, b) => a + b, 0);
  const grandMean = valid.reduce((acc, e, i) => acc + wRE[i] * e.effect_size_sd, 0) / sumWRE;
  const grandSE = 1 / Math.sqrt(sumWRE);

  return { mean: grandMean, se: grandSE, lo: grandMean - 1.96 * grandSE, hi: grandMean + 1.96 * grandSE, k, tau2, Q };
}

// One CI definition for the whole site: the stored interval when present,
// otherwise effect ± 1.96·SE, otherwise nulls.
export function ciOf(e) {
  const lo = e.ci_lower != null ? e.ci_lower
    : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd - 1.96 * e.se : null);
  const hi = e.ci_upper != null ? e.ci_upper
    : (e.effect_size_sd != null && e.se != null ? e.effect_size_sd + 1.96 * e.se : null);
  return { lo, hi };
}

// Turn a human author list ("A, B, & C" or "Xu, X., Qiao, L.") into a valid
// BibTeX author field ("A and B and C" / "Xu, X. and Qiao, L.").
export function bibtexAuthors(s) {
  if (!s) return "";
  const normalized = s.replace(/\s*&\s*/g, ", ").replace(/,?\s+and\s+/gi, ", ");
  const parts = normalized.split(/,\s*/).map(x => x.trim()).filter(Boolean);
  const isInitials = (x) => /^[A-Z]\.?(\s*-?\s*[A-Z]\.?)*$/.test(x) && x.length <= 8;
  const names = [];
  for (let i = 0; i < parts.length; i++) {
    if (i + 1 < parts.length && isInitials(parts[i + 1]) && !isInitials(parts[i])) {
      names.push(parts[i] + ", " + parts[i + 1]);
      i++;
    } else {
      names.push(parts[i]);
    }
  }
  return names.join(" and ");
}
