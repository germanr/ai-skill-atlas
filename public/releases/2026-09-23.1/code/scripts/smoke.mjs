// Smoke tests for the atlas data and shared logic. Run with `npm test`.
// Guards the exact failure modes found in the July 2026 stress test.
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { randomEffectsMean, ciOf, bibtexAuthors, filterEstimates, isPlottableEstimate, isPoolableEstimate } from "../src/shared.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const papers = JSON.parse(readFileSync(join(root, "src", "papers.json"), "utf-8"));
const estimates = JSON.parse(readFileSync(join(root, "src", "estimates.json"), "utf-8"));

let failures = 0;
const check = (ok, msg) => {
  if (!ok) { failures += 1; console.error("FAIL:", msg); }
};

// ── data invariants ─────────────────────────────────────────────────────────
const ids = estimates.map(e => e.estimate_id);
check(new Set(ids).size === ids.length, "duplicate estimate_ids");

const paperKeys = new Set(papers.map(p => p.paper_key));
check(estimates.every(e => paperKeys.has(e.paper_key)), "estimate with unknown paper_key");

const DESIGNS = new Set(["lab_rct", "field_rct", "online_rct", "observational"]);
const TIMINGS = new Set(["immediate", "delayed"]);
const COMPARISONS = new Set(["ai_vs_bau", "ai_vs_active", "ai_design"]);
check(estimates.every(e => DESIGNS.has(e.design_class)), "invalid design_class");
check(estimates.every(e => TIMINGS.has(e.outcome_timing)), "invalid outcome_timing");
check(estimates.every(e => COMPARISONS.has(e.comparison_type || "ai_vs_bau")), "invalid comparison_type");

for (const p of papers) {
  const n = estimates.filter(e => e.paper_key === p.paper_key).length;
  check(p.n_estimates === n, `${p.paper_key}: n_estimates ${p.n_estimates} != actual ${n}`);
}

// CI consistency where fully populated (0.02 tolerance for rounded inputs)
for (const e of estimates) {
  if (e.effect_size_sd != null && e.se != null && e.ci_lower != null && e.ci_upper != null) {
    const wide = Math.abs(e.ci_upper - e.ci_lower - 2 * 1.96 * e.se) > 0.05 + 0.02 * Math.abs(e.se);
    if (wide && !(e.notes || "").match(/CI|interval|paper's exact/i)) {
      check(false, `${e.estimate_id}: CI width inconsistent with SE and no note explains it`);
    }
  }
}

// ── assets used by the site must exist ─────────────────────────────────────
// Historical image_filename values are not rendered by the typographic cards.
for (const p of papers) {
  if (p.pdf_filename) check(existsSync(join(root, "public", "pdfs", p.pdf_filename)), `missing PDF: ${p.pdf_filename}`);
}
check(existsSync(join(root, "public", "images", "og-card.png")), "missing og-card.png");

// ── domain palette must cover every domain in the data ──────────────────────
const jsx = readFileSync(join(root, "ai-skill-atlas-explorer.jsx"), "utf-8");
const paletteBlock = jsx.slice(jsx.indexOf("const DOMAIN = {"), jsx.indexOf("const DOMAIN_ORDER"));
const domains = new Set([
  ...estimates.map(e => e.learning_domain),
  ...papers.map(p => p.learning_domain_primary),
].filter(Boolean));
for (const d of domains) check(paletteBlock.includes(`"${d}"`), `DOMAIN palette missing "${d}"`);

// ── pooling: k=0 / k=1 / k=2 behaviors ──────────────────────────────────────
check(randomEffectsMean([]) === null, "RE mean of empty set should be null");
const one = randomEffectsMean([{ effect_size_sd: -0.067, se: 0.228 }]);
check(one && one.k === 1 && one.tau2 === 0 && Number.isFinite(one.mean) && Number.isFinite(one.se), "RE k=1 must be finite with tau2=0");
const two = randomEffectsMean([{ effect_size_sd: 0.2, se: 0.1 }, { effect_size_sd: 0.4, se: 0.1 }]);
check(two && Number.isFinite(two.mean) && Number.isFinite(two.tau2), "RE k=2 must be finite");
const mixed = randomEffectsMean([{ effect_size_sd: 0.3, se: null }, { effect_size_sd: 0.2, se: 0.1 }]);
check(mixed && mixed.k === 1, "RE must ignore SE-less rows");

// ── regression cases from the September 2026 chart/filter audit ─────────────
const screenshotKeys = new Set(["hausman_etal_2025", "lehmann_etal_2024", "stromberg_etal_2026"]);
const observational = filterEstimates(estimates, { paperKeys: screenshotKeys, designMode: "obs" });
const observationalPlot = observational.filter(isPlottableEstimate);
check(observational.length === 9 && observationalPlot.length === 3, "observational slice must distinguish matching and plotted records");
check(new Set(observationalPlot.map(e => e.paper_key)).size === 1, "observational plot has one study, not three");
const observationalMean = randomEffectsMean(observationalPlot);
check(observationalMean?.lo < -1 && observationalMean?.hi > 0, "screenshot regression must exercise pooled interval below the axis");
check(observationalPlot.some(e => e.effect_size_sd < -1), "screenshot regression must exercise an off-axis point");

const math = filterEstimates(estimates, { paperKeys, comparisonType: "ai_design", activeDomains: new Set(["Math"]) });
check(math.some(e => e.paper_key === "chung_etal_2025"), "Math must include Chung math outcomes despite the paper's Coding category");
check(math.every(e => e.learning_domain === "Math" && e.is_subgroup !== true), "domain filter must select estimate subjects and exclude subgroups");
const coding = filterEstimates(estimates, { paperKeys, comparisonType: "ai_design", activeDomains: new Set(["Coding"]) });
check(!coding.some(e => e.learning_domain === "Math"), "Coding must not include Math outcomes from Coding papers");
const ciOnly = estimates.filter(e => Number.isFinite(e.effect_size_sd) && e.se == null && Number.isFinite(e.ci_lower) && Number.isFinite(e.ci_upper));
check(ciOnly.length > 0 && ciOnly.every(e => isPlottableEstimate(e) && !isPoolableEstimate(e)), "CI-only records must be plotted but not pooled");
for (const designMode of ["rct", "lab", "field", "online", "obs"]) {
  for (const comparisonType of COMPARISONS) {
    const slice = filterEstimates(estimates, { paperKeys, designMode, comparisonType, outcomeMode: "all" });
    check(slice.every(e => e.is_subgroup !== true), `${designMode}/${comparisonType}: subgroup leaked into primary plot`);
    const immediate = filterEstimates(estimates, { paperKeys, designMode, comparisonType, outcomeMode: "all", timingMode: "immediate" });
    const delayed = filterEstimates(estimates, { paperKeys, designMode, comparisonType, outcomeMode: "all", timingMode: "delayed" });
    check(immediate.every(e => e.outcome_timing === "immediate"), `${designMode}/${comparisonType}: immediate filter includes a delayed outcome`);
    check(delayed.every(e => e.outcome_timing === "delayed"), `${designMode}/${comparisonType}: delayed filter includes an immediate outcome`);
    check(immediate.length + delayed.length === slice.length, `${designMode}/${comparisonType}: timing partitions do not recover all records`);
    const partitionIds = new Set([...immediate, ...delayed].map(e => e.estimate_id));
    check(partitionIds.size === slice.length && slice.every(e => partitionIds.has(e.estimate_id)), `${designMode}/${comparisonType}: timing partitions changed membership`);
  }
}

// ── ciOf fallbacks ──────────────────────────────────────────────────────────
const c1 = ciOf({ effect_size_sd: 0.5, se: 0.1, ci_lower: null, ci_upper: null });
check(Math.abs(c1.lo - 0.304) < 1e-9 && Math.abs(c1.hi - 0.696) < 1e-9, "ciOf derived CI wrong");
const c2 = ciOf({ effect_size_sd: 0.5, se: null, ci_lower: 0.1, ci_upper: 0.9 });
check(c2.lo === 0.1 && c2.hi === 0.9, "ciOf must prefer stored CI");
const c3 = ciOf({ effect_size_sd: 0.5, se: null, ci_lower: null, ci_upper: null });
check(c3.lo === null && c3.hi === null, "ciOf with nothing must be null");

// ── BibTeX authors: valid for every paper ───────────────────────────────────
for (const p of papers) {
  const out = bibtexAuthors(p.authors_full || p.authors_short);
  check(out.length > 0, `${p.paper_key}: empty BibTeX authors`);
  check(!out.includes("&"), `${p.paper_key}: '&' left in BibTeX authors: ${out}`);
  // any comma must belong to a "Surname, F." token, i.e. be followed by initials
  const tokens = out.split(" and ");
  for (const t of tokens) {
    if (t.includes(",")) {
      const after = t.split(",")[1].trim();
      check(/^[A-Z]\.?(\s*-?\s*[A-Z]\.?)*$/.test(after), `${p.paper_key}: suspicious BibTeX token "${t}"`);
    }
  }
}
check(bibtexAuthors("Zara Contractor and Germán Reyes") === "Zara Contractor and Germán Reyes", "and-form roundtrip");
check(bibtexAuthors("Xu, X., Qiao, L., & Zhao, W.") === "Xu, X. and Qiao, L. and Zhao, W.", "surname-initial pairing");

if (failures > 0) {
  console.error(`\n${failures} smoke check(s) FAILED`);
  process.exit(1);
}
console.log(`All smoke checks passed (${papers.length} papers, ${estimates.length} estimates).`);
