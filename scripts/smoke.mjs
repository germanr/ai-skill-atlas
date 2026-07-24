// Smoke tests for the atlas data and shared logic. Run with `npm test`.
// Guards the exact failure modes found in the July 2026 stress test.
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { randomEffectsMean, ciOf, bibtexAuthors } from "../src/shared.mjs";

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

// ── assets referenced by the data must exist ────────────────────────────────
for (const p of papers) {
  if (p.pdf_filename) check(existsSync(join(root, "public", "pdfs", p.pdf_filename)), `missing PDF: ${p.pdf_filename}`);
  if (p.image_filename) check(existsSync(join(root, "public", "images", p.image_filename)), `missing image: ${p.image_filename}`);
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
