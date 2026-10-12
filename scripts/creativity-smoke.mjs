import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync, mkdirSync, existsSync, rmSync, realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve, relative, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { buildCreativity, combinedArms, computeEstimate, validateSource, readSources, DEFAULT_PAPERS_DIR, OUTPUT_FILES } from "./build-creativity.mjs";
import { validateMetadataRelease } from "../src/evidence-metadata.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const FIXTURES = join(ROOT, "scripts", "fixtures", "creativity");
const builder = join(ROOT, "scripts", "build-creativity.mjs");
const readJSON = file => JSON.parse(readFileSync(file, "utf8"));
const clone = structuredClone;
const keyOf = row => JSON.stringify([row.sample_id, row.question, row.comparison_type]);
const signs = { more_creative: 1, more_diverse: 1, more_ideas: 1, more_accurate: 1, less_creative: -1, more_similar: -1, other: null };
let checks = 0;

function near(actual, expected, label) {
  assert.ok(Number.isFinite(actual), `${label}: expected finite number, got ${actual}`);
  assert.ok(Math.abs(actual - expected) <= 1e-9, `${label}: ${actual} != ${expected}`);
  checks++;
}

function run(args, expectedStatus = 0) {
  const result = spawnSync(process.execPath, [builder, ...args], { cwd: ROOT, encoding: "utf8" });
  if (result.error) throw result.error;
  assert.equal(result.status, expectedStatus, `${args.join(" ")}\n${result.stdout}\n${result.stderr}`);
  checks++;
  return result;
}

function loadBuild(out) {
  const [papers, estimates, metadata] = OUTPUT_FILES.map(file => readJSON(join(out, file)));
  return { papers, estimates, metadata };
}

function invariants(build, sources) {
  const { papers, estimates, metadata } = build;
  assert.equal(new Set(estimates.map(row => row.estimate_id)).size, estimates.length, "Estimate IDs must be unique");
  const groups = new Map();
  const inputs = new Map(sources.flatMap(({ source }) => source.estimates.map(e => [`${source.paper_key}__${e.slug}`, e])));
  for (const row of estimates) {
    const key = keyOf(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
    assert.equal(row.pooled, row.eligible && row.is_primary, `${row.estimate_id}: pooled means eligible and primary`);
    if (row.construct === "other") assert.equal(row.is_primary, false, `${row.estimate_id}: other outcomes are never primary`);
    if (row.pooled) {
      assert.ok(Number.isFinite(row.effect_size_sd) && Number.isFinite(row.se) && row.se > 0, row.estimate_id);
      assert.ok(["participant", "cluster"].includes(row.se_basis), row.estimate_id);
      assert.ok(!["diversity", "convergent"].includes(row.construct), row.estimate_id);
      assert.notEqual(row.standardizer, "output_level_sd", row.estimate_id);
    }
    if (row.construct === "diversity") for (const field of ["effect_size_sd", "se", "ci_lower", "ci_upper"]) assert.equal(row[field], null, `${row.estimate_id}.${field}`);
    if (row.construct === "convergent") assert.equal(row.is_primary, false, row.estimate_id);
    const input = inputs.get(row.estimate_id);
    assert.ok(input, `Missing source for ${row.estimate_id}`);
    // Independently follow the specified delta precedence; do not reuse the
    // builder's deltaOf or a builder-produced intermediate as the oracle.
    const st = input.stats;
    // A printed difference or coefficient may run control minus treatment; the extraction says so in difference_is (or,
    // for a coefficient, in the regression model text), and delta runs treatment minus control.
    const runsBackward = (...texts) => texts.some(text => /control minus treatment/i.test(String(text || "")));
    const delta = st.regression?.outcome_scale === "raw" && Number.isFinite(st.regression.coef) ? (runsBackward(st.regression.model, st.difference_is) ? -1 : 1) * st.regression.coef
      : Number.isFinite(st.difference) ? (runsBackward(st.difference_is) ? -1 : 1) * st.difference
        : Number.isFinite(st.treatment_mean) && Number.isFinite(st.control_mean) ? st.treatment_mean - st.control_mean : null;
    const sign = signs[input.higher_is];
    if (Number.isFinite(row.effect_size_sd) && Number.isFinite(delta) && sign !== null) assert.ok(Math.sign(row.effect_size_sd) === Math.sign(sign * delta), `${row.estimate_id}: effect disagrees with signed delta`);
    // JSON cannot carry -0 (a printed "-0.00"), so compare with the statistics as JSON stores them.
    assert.deepEqual(row.raw, JSON.parse(JSON.stringify(st)), "The paper's own statistics must be retained without rewriting");
    const printedLocator = input.sources.map(s => s.locator).join("; ");
    const locator = metadata.estimates[row.estimate_id].provenance.source_locator;
    // A record derived from posted data alone (no printed source) names the analysis output even when its statistics are not used.
    if (row.computed_from_posted_data || !input.sources.length) assert.ok(locator.includes("posted data"), `${row.estimate_id}: posted-data locator`);
    else assert.equal(locator, printedLocator);
  }
  for (const [key, rows] of groups) {
    // The explicit ban on primary convergent outcomes takes precedence when
    // a pool key contains only convergent outcomes: it has zero primaries.
    const expected = rows.some(row => !["convergent", "other"].includes(row.construct)) ? 1 : 0;
    assert.equal(rows.filter(row => row.is_primary).length, expected, `Primary count for ${key}`);
  }
  for (const { source } of sources.filter(({ source }) => papers.some(p => p.paper_key === source.paper_key))) {
    for (const study of source.studies) {
      // The 50-person rule counts the people analyzed when the paper prints that count, otherwise the people randomized.
      const people = Number.isInteger(study.n_analyzed) ? study.n_analyzed : study.n_randomized;
      assert.ok(Number.isInteger(people) && people >= 50, `${source.paper_key}/${study.study_id}: randomized study must have at least 50 people (analyzed, else randomized)`);
      if (["team", "class", "session"].includes(study.assignment_unit)) {
        for (const row of estimates.filter(row => row.sample_id === study.sample_id && row.pooled)) assert.equal(row.se_basis, "cluster", row.estimate_id);
      }
    }
  }
  for (const section of [metadata.studies, metadata.estimates]) for (const annotation of Object.values(section)) {
    for (const part of [annotation.sample, annotation.provenance]) for (const [field, value] of Object.entries(part)) if (value === null) assert.ok(part.missing_reasons[field], `Missing null explanation for ${field}`);
  }
  const release = validateMetadataRelease({ papers, estimates, previousEstimates: [], metadata });
  assert.equal(release.valid, true, release.errors.join("\n"));
  checks++;
}

const tempRoot = mkdtempSync(join(tmpdir(), "atlas-creativity-smoke-"));
try {
  const alpha = readJSON(join(FIXTURES, "alpha.json"));
  const beta = readJSON(join(FIXTURES, "beta.json"));
  const draft = readJSON(join(FIXTURES, "draft.json"));
  const untouched = JSON.stringify([alpha, beta, draft]);
  const fixtureOut = join(tempRoot, "fixtures");
  run(["--papers-dir", FIXTURES, "--out", fixtureOut]);
  const built = loadBuild(fixtureOut);
  const rows = new Map(built.estimates.map(e => [e.estimate_id.split("__")[1], e]));
  const row = slug => { assert.ok(rows.has(slug), `Missing ${slug}`); return rows.get(slug); };
  const input = slug => [...alpha.estimates, ...beta.estimates].find(e => e.slug === slug);
  const alternative = (slug, change) => { const e = clone(input(slug)); change(e); return computeEstimate(e); };

  // Rank 1, rule a: raw regression delta 1 outranks printed 5 and means 16-10;
  // control SD 2 outranks pooled sqrt((49*4^2 + 49*2^2)/98) = sqrt(10).
  near(row("s1_regression_a").effect_size_sd, 0.5, "rank 1 d = 1/2");
  near(row("s1_regression_a").se, 0.1, "rule a SE = 0.2/2");
  near(row("s1_regression_a").ci_lower, 0.304, "CI lower = 0.5 - 1.96*0.1");
  near(row("s1_regression_a").ci_upper, 0.696, "CI upper = 0.5 + 1.96*0.1");
  assert.equal(row("s1_regression_a").standardizer, "control_sd");
  assert.match(row("s1_regression_a").derivation_notes, /rule a/);
  assert.match(row("s1_regression_a").derivation_notes, /Synthetic PDF p\. 10/);
  assert.equal(row("s1_regression_a").is_primary, false, "Explicit override outranks preregistration");

  // Rank 1, rule b: (12-10)/4 = 0.5; 0.8/4 = 0.2, before CI or counts.
  near(row("s1_override_b").effect_size_sd, 0.5, "mean-difference d");
  near(row("s1_override_b").se, 0.2, "rule b SE");
  assert.match(row("s1_override_b").derivation_notes, /rule b/);
  assert.equal(row("s1_override_b").is_primary, true);

  // Rank 2 is reachable with a zero (unusable) control SD. Pooled variance =
  // (49*6^2 + 49*0^2)/98 = 1764/98 = 18. d = (13-10)/sqrt(18).
  near(row("s1_pooled_c").effect_size_sd, 3 / Math.sqrt(18), "rank 2 d");
  // Rule c: (4.96-1.04)/3.92 = 1, so SE = 1/sqrt(18); ci_level 0.95.
  near(row("s1_pooled_c").se, 1 / Math.sqrt(18), "rule c SE, fractional confidence level");
  assert.equal(row("s1_pooled_c").standardizer, "pooled_sd");
  assert.match(row("s1_pooled_c").derivation_notes, /49|50 - 1/);
  const percentCI = alternative("s1_pooled_c", e => { e.stats.ci_level = 95; });
  // 95 and 0.95 represent the same interval: 3.92/3.92/sqrt(18).
  near(percentCI.se, 1 / Math.sqrt(18), "percent confidence level");

  // Rank 3: +1*printed d 0.4 = 0.4. No numeric SD is known. Only rule e
  // qualifies: sqrt(100/(50*50) + 0.4^2/(2*100)) = sqrt(0.04+0.0008).
  near(row("s1_paper_d").effect_size_sd, 0.4, "rank 3 printed d");
  near(row("s1_paper_d").se, Math.sqrt(0.0408), "rank 3 rule e");
  assert.equal(row("s1_paper_d").standardizer, "paper_control_sd");
  assert.match(row("s1_paper_d").derivation_notes, /rule e/);
  const g = alternative("s1_paper_d", e => { e.stats.paper_effect.type = "g"; e.stats.paper_effect.standardizer = "Pooled participant-level SD"; });
  // A printed g is retained per rank 3, without inventing a small-sample
  // correction: +1*0.4 = 0.4, and the same rule-e arithmetic applies.
  near(g.effect_size_sd, 0.4, "rank 3 printed g");
  near(g.se, Math.sqrt(0.0408), "rank 3 g uncertainty");
  assert.equal(g.standardizer, "paper_pooled_sd");
  const paperWithSD = alternative("s1_paper_d", e => { Object.assign(e.stats, { difference: null, control_sd: 2, sd_level: "participant" }); });
  // Delta is unavailable, but printed d=0.4 and its numeric control SD=2
  // are known: rule b SE=0.5/2=0.25 (no SD reconstructed from d).
  near(paperWithSD.effect_size_sd, 0.4, "paper d without delta");
  near(paperWithSD.se, 0.25, "paper d with known control SD");
  const paperWithPooledSD = alternative("s1_paper_d", e => {
    Object.assign(e.stats, { difference: null, treatment_sd: 6, control_sd: 0, sd_level: "participant" });
    e.stats.paper_effect.standardizer = "Pooled participant-level SD";
  });
  // Pooled variance=(49*36+49*0)/98=18; rule b SE=0.5/sqrt(18).
  near(paperWithPooledSD.se, 0.5 / Math.sqrt(18), "paper d with known pooled SD");

  // Rank 4: less_creative means s=-1. d=(-1)*(-0.6)=0.6;
  // standardized outcome has SD=1, so rule a SE=0.12/1=0.12.
  near(row("s1_standardized").effect_size_sd, 0.6, "rank 4 signed coefficient");
  near(row("s1_standardized").se, 0.12, "rank 4 regression SE");
  assert.equal(row("s1_standardized").standardizer, "standardized_outcome");

  // Rank 5: delta/SD_output = -1/2 = -0.5. Rule d: |-1|/|-2|/2=0.25.
  near(row("s1_output_t").effect_size_sd, -0.5, "rank 5 output SD");
  near(row("s1_output_t").se, 0.25, "rule d with negative t");
  assert.equal(row("s1_output_t").standardizer, "output_level_sd");
  assert.equal(row("s1_output_t").pooled, false);
  assert.match(row("s1_output_t").derivation_notes, /rule d/);
  const rating = alternative("s1_pooled_c", e => { e.stats.sd_level = "rating"; });
  // Rating fallback uses the same pooled variance 18 and interval width 3.92.
  near(rating.effect_size_sd, 3 / Math.sqrt(18), "rank 5 pooled rating SD");
  near(rating.se, 1 / Math.sqrt(18), "rank 5 pooled rating SE");
  assert.equal(rating.standardizer, "output_level_sd");

  // more_similar flips s to -1: (-1)*(-0.2)/0.4=0.5; SE=0.04/0.4=0.1.
  near(row("s1_similarity_flip").effect_size_sd, 0.5, "similarity sign flip");
  near(row("s1_similarity_flip").se, 0.1, "similarity SE remains positive");
  assert.equal(row("s1_paper_disagrees").effect_size_sd, null);
  assert.match(row("s1_paper_disagrees").derivation_notes, /printed sign.*disagrees/);
  assert.equal(row("s1_unknown_sign").effect_size_sd, null);
  assert.match(row("s1_unknown_sign").derivation_notes, /higher_is is other/);
  assert.equal(row("s1_unknown_standardizer").effect_size_sd, null);
  const reversedPaper = alternative("s1_paper_d", e => { e.higher_is = "more_similar"; });
  // Printed d 0.4 and delta 2 share a sign (both treatment minus control), so the paper d is used and flipped:
  // s * 0.4 = -1 * 0.4 = -0.4, the sign of s * delta = -2. No SD is known, so rule e:
  // sqrt(100/2500 + (-0.4)^2/200) = sqrt(0.04 + 0.0008) = sqrt(0.0408).
  near(reversedPaper.effect_size_sd, -0.4, "reversed-scale paper d is flipped by s");
  near(reversedPaper.se, Math.sqrt(0.0408), "reversed-scale paper d, rule e");
  const reversedConverted = alternative("s1_paper_d", e => { e.higher_is = "more_similar"; e.stats.paper_effect.value = -0.4; });
  // Printed d -0.4 against delta +2: opposite signs, so the paper d is not used.
  assert.equal(reversedConverted.effect_size_sd, null, "A printed d whose sign disagrees with delta is not used");
  assert.match(reversedConverted.derivation_notes, /printed sign disagrees/);
  const fallback = alternative("s1_paper_disagrees", e => { e.stats.control_sd = 2; e.stats.sd_level = "output"; });
  // Reject -0.5 paper d; continue to output SD: +1*1/2=0.5.
  near(fallback.effect_size_sd, 0.5, "sign mismatch permits lower-ranked standardizer");
  assert.equal(fallback.standardizer, "output_level_sd");

  // Paired d=(12-10)/4=0.5; rule c SE=(2.784-1.216)/3.92/4
  // =1.568/3.92/4=0.4/4=0.1. Paired counts are never added together.
  near(row("s1_paired_ci").effect_size_sd, 0.5, "paired d");
  near(row("s1_paired_ci").se, 0.1, "paired printed-interval SE");
  assert.equal(row("s1_paired_ci").n_total, 80); // Printed 80 people, not 80+80.
  // Eligible, but the first-round record is the primary record of this pool key, so only it is pooled.
  assert.equal(row("s1_paired_ci").eligible, true);
  assert.equal(row("s1_paired_ci").pooled, false);
  assert.match(row("s1_paired_ci").not_pooled_reason, /not the primary record/);
  assert.equal(row("s1_first_round").pooled, true);
  assert.equal(row("s1_paired_ci").is_primary, false, "First round takes priority");
  // First round: same d=0.5, independent counts 40+40=80;
  // rule e variance=80/1600+0.25/160=0.05+0.0015625=33/640.
  near(row("s1_first_round").effect_size_sd, 0.5, "first-round d");
  near(row("s1_first_round").se, Math.sqrt(33 / 640), "first-round SE");
  assert.equal(row("s1_first_round").is_primary, true);
  // A paired t serves rule d: d = 2/4 = 0.5; SE = |2| / |4| / 4 = 0.5 / 4 = 0.125. Rule e is never used for a
  // paired contrast.
  near(row("s1_paired_no_se").effect_size_sd, 0.5, "paired d from control SD");
  near(row("s1_paired_no_se").se, 0.125, "paired rule d SE");
  assert.match(row("s1_paired_no_se").derivation_notes, /rule d/);
  assert.match(row("s1_paired_no_se").derivation_notes, /paired t/);
  const pairedNoT = alternative("s1_paired_no_se", e => { e.stats.test = null; });
  assert.equal(pairedNoT.se, null, "Without a t, a paired contrast has no SE: rule e does not apply");
  // The confidence level, the unit count, and the delay may go without a source, but never in two sources.
  const optionalSource = clone(beta);
  const paired = optionalSource.estimates.find(e => e.slug === "s1_paired_ci");
  for (const src of paired.sources) src.fields = src.fields.filter(f => f !== "ci_level");
  paired.delay_days = 7;
  paired.n_units = 160;
  assert.doesNotThrow(() => validateSource(optionalSource, "optional-source.json"));
  paired.sources.push({ fields: ["delay_days"], locator: "Synthetic p. 1", quote: "7 days" }, { fields: ["delay_days"], locator: "Synthetic p. 2", quote: "seven days (7)" });
  assert.throws(() => validateSource(optionalSource, "doubled-source.json"), /delay_days: must appear in at most one source/);
  checks += 2;

  for (const slug of ["s2_participant_se", "s2_cluster_se", "s3_output_basis"]) {
    // Each fixture prints delta=1, SD=2, difference SE=0.2: d=1/2,
    // SE=0.2/2. Pooling differs only in assignment or precision unit.
    near(row(slug).effect_size_sd, 0.5, `${slug} d`);
    near(row(slug).se, 0.1, `${slug} SE`);
  }
  assert.equal(row("s2_participant_se").pooled, false);
  assert.match(row("s2_participant_se").not_pooled_reason, /cluster randomization/);
  assert.equal(row("s2_cluster_se").eligible, true);
  assert.equal(row("s2_cluster_se").pooled, row("s2_cluster_se").is_primary);
  assert.equal(row("s3_output_basis").pooled, false);
  assert.match(row("s3_output_basis").not_pooled_reason, /se_basis is output/);
  // Convergent: 2/4=0.5 and 0.8/4=0.2 are displayable but never pooled/primary.
  near(row("s3_convergent").effect_size_sd, 0.5, "convergent d");
  near(row("s3_convergent").se, 0.2, "convergent SE");
  assert.equal(row("s3_convergent").pooled, false);
  assert.equal(row("s3_convergent").is_primary, false);
  assert.equal(row("s3_f_statistic").se, null, "F is never converted");
  assert.equal(row("s3_regression_t").se, null, "A regression excludes t rule d");
  const non95 = alternative("s3_f_statistic", e => { Object.assign(e.stats, { ci_lower: -1, ci_upper: 3, ci_level: 90, ci_of: "difference" }); });
  assert.equal(non95.se, null, "Do not use a non-95 interval as rule c");
  const armCI = alternative("s3_f_statistic", e => { Object.assign(e.stats, { ci_lower: -1, ci_upper: 3, ci_level: 95, ci_of: "treatment_mean" }); });
  assert.equal(armCI.se, null, "An arm interval is not an interval of the difference");

  // Similarity: (-1)*(0.3-0.5)=+0.2 => less alike; [-0.3,-0.1]
  // excludes 0 and p<0.001 implies p<0.05, hence clear.
  assert.equal(row("s3_less_alike").direction, "less_alike clear");
  // (-1)*(0.6-0.5)=-0.1 => more alike; [-0.1,0.3] includes 0,
  // p=0.2 is not below 0.05, hence no_clear_difference.
  assert.equal(row("s3_more_alike").direction, "more_alike no_clear_difference");
  assert.equal(row("s3_not_tested").direction, "not_tested");
  for (const slug of ["s3_less_alike", "s3_more_alike", "s3_not_tested"]) {
    for (const field of ["effect_size_sd", "se", "ci_lower", "ci_upper"]) assert.equal(row(slug)[field], null);
    assert.equal(row(slug).pooled, false);
  }
  const ciOnly = alternative("s3_less_alike", e => { e.stats.p_value = null; });
  assert.equal(ciOnly.direction, "less_alike clear");
  for (const p of ["<0.001", "<.001", "<0.05", "<=0.01", 0.049]) {
    const bound = alternative("s3_less_alike", e => { Object.assign(e.stats, { ci_lower: null, ci_upper: null, ci_level: null, ci_of: null, p_value: p }); });
    assert.equal(bound.direction, "less_alike clear", `p=${p}`);
  }
  for (const p of [">0.001", "<=0.05", "<0.1", 0.05]) {
    const bound = alternative("s3_less_alike", e => { Object.assign(e.stats, { ci_lower: null, ci_upper: null, p_value: p }); });
    assert.equal(bound.direction, "less_alike no_clear_difference", `p=${p} does not prove p<0.05`);
  }
  const positiveDiversity = alternative("s3_more_alike", e => { e.higher_is = "more_diverse"; e.stats.p_value = 0.01; });
  assert.equal(positiveDiversity.direction, "less_alike clear", "+1*(0.6-0.5)>0 and p=0.01<0.05");
  const zero = alternative("s3_more_alike", e => { e.stats.treatment_mean = 0.5; });
  assert.equal(zero.direction, "no_clear_difference", "Signed delta=-1*(0.5-0.5)=0");
  const missing = alternative("s3_more_alike", e => { e.stats.treatment_mean = null; });
  assert.equal(missing.direction, null, "Cannot assign more/less direction to an unreported contrast");

  // Posted-data route (gamma.json). Printed statistics come first; data statistics fill only what they cannot give.
  // s1_data_route: printed difference 0.5 has no SD and a rating-level basis; data: d = (5.5 - 5.0) / 1.0 = 0.5,
  // SE = 0.1 / 1.0 = 0.1, counts 100 + 100 = 200, basis participant (HC2), so it pools.
  const gammaRow = slug => { const r = built.estimates.find(e => e.estimate_id === `gamma_etal_2026__${slug}`); assert.ok(r, `Missing gamma ${slug}`); return r; };
  near(gammaRow("s1_data_route").effect_size_sd, 0.5, "posted-data d");
  near(gammaRow("s1_data_route").se, 0.1, "posted-data SE");
  assert.equal(gammaRow("s1_data_route").n_total, 200);
  assert.equal(gammaRow("s1_data_route").se_basis, "participant");
  // Eligible through the posted data; s1_printed_kept is the primary record of this pool key (override).
  assert.equal(gammaRow("s1_data_route").eligible, true);
  assert.equal(gammaRow("s1_data_route").pooled, false);
  assert.equal(gammaRow("s1_printed_kept").pooled, true);
  assert.equal(gammaRow("s1_data_route").computed_from_posted_data, true);
  assert.equal(built.metadata.estimates["gamma_etal_2026__s1_data_route"].provenance.review_basis, "analysis_output");
  assert.equal(built.metadata.estimates["gamma_etal_2026__s1_data_route"].sample.n, 200);
  // s1_printed_kept: printed d = 1 / 2 = 0.5, SE = 0.2 / 2 = 0.1; the data (0.6 / 2 = 0.3) are not used.
  near(gammaRow("s1_printed_kept").effect_size_sd, 0.5, "printed route kept");
  near(gammaRow("s1_printed_kept").se, 0.1, "printed SE kept");
  assert.equal(gammaRow("s1_printed_kept").computed_from_posted_data, false);
  assert.equal(built.metadata.estimates["gamma_etal_2026__s1_printed_kept"].provenance.review_basis, "primary_source");
  // s1_first_round_data: d = (3.2 - 3.0) / 0.5 = 0.4, SE = 0.1 / 0.5 = 0.2, counts 40 + 40 = 80.
  near(gammaRow("s1_first_round_data").effect_size_sd, 0.4, "first round from data");
  near(gammaRow("s1_first_round_data").se, 0.2, "first-round SE from data");
  assert.equal(gammaRow("s1_first_round_data").n_total, 80);
  // s2_cluster_data: class-randomized; data clustered by 12 classes: d = 0.3 / 1.5 = 0.2, SE = 0.15 / 1.5 = 0.1.
  near(gammaRow("s2_cluster_data").effect_size_sd, 0.2, "cluster data d");
  near(gammaRow("s2_cluster_data").se, 0.1, "cluster data SE");
  assert.equal(gammaRow("s2_cluster_data").se_basis, "cluster");
  assert.equal(gammaRow("s2_cluster_data").pooled, true);
  // Data statistics are validated: cluster SEs need a cluster-randomized study, and first-round data need a
  // first-round estimate.
  const gamma = readJSON(join(FIXTURES, "gamma.json"));
  const badCluster = clone(gamma);
  badCluster.estimates[0].data_stats.se_type = "cluster";
  assert.throws(() => validateSource(badCluster, "bad-cluster.json"), /cluster standard errors require a study that randomized clusters/);
  const badRound = clone(gamma);
  badRound.estimates[0].data_stats.round = "first_round";
  assert.throws(() => validateSource(badRound, "bad-round.json"), /first-round statistics belong/);
  checks += 2;

  // Paper counts sum study people, not estimate samples: alpha=100;
  // beta=80+100+100=280, despite overlapping contrasts and paired arm counts.
  near(built.papers.find(p => p.paper_key === alpha.paper_key).n_total, 100, "alpha paper count");
  near(built.papers.find(p => p.paper_key === beta.paper_key).n_total, 280, "beta paper count");
  near(built.metadata.studies[beta.paper_key].sample.n, 280, "metadata paper count");
  const unknownSample = built.metadata.estimates[`${alpha.paper_key}__s1_standardized`];
  assert.equal(unknownSample.sample.n, null);
  assert.ok(unknownSample.sample.missing_reasons.n);
  assert.equal(unknownSample.provenance.statement, alpha.provenance.statement);
  assert.equal(unknownSample.provenance.review_status, "reviewed");
  assert.equal(unknownSample.sample.unit, "participants");
  assert.equal(built.papers.some(p => p.paper_key === draft.paper_key), false);
  invariants(built, readSources(FIXTURES));

  // Mutation checks protect the publication gate, including excluded drafts.
  function invalid(change, field) {
    const source = clone(alpha);
    change(source);
    assert.throws(() => validateSource(source, "invalid.json"), error => {
      assert.match(error.message, /^invalid\.json: /);
      assert.ok(error.message.includes(field), error.message);
      assert.ok(error.message.includes("<paper>") || source.estimates.some(e => error.message.includes(e.slug)), error.message);
      return true;
    });
    checks++;
  }
  invalid(s => { s.schema = 2; }, "schema");
  invalid(s => { delete s.paper.title; }, "paper.title");
  invalid(s => { s.estimates[0].n_total = -1; }, "n_total");
  invalid(s => { s.estimates[0].n_treatment = 1.5; }, "n_treatment");
  invalid(s => { s.studies[0].n_randomized = -1; }, "n_randomized");
  invalid(s => { s.studies[0].clusters_per_arm = { AI: 1.5 }; }, "clusters_per_arm.AI");
  invalid(s => { s.estimates[0].measure = "wrong"; }, "measure");
  invalid(s => { s.estimates[0].se_basis = "people"; }, "se_basis");
  invalid(s => { s.estimates[0].higher_is = "negative"; }, "higher_is");
  // Alpha's study S1 randomized individuals, so standard errors clustered by anything cannot be se_basis cluster.
  invalid(s => { s.estimates[0].se_basis = "cluster"; }, "cluster requires a study that randomized clusters");
  invalid(s => { s.estimates[0].primary_override = "true"; }, "primary_override");
  invalid(s => { s.estimates[0].slug = "Bad slug"; }, "slug");
  invalid(s => { s.estimates[1].slug = s.estimates[0].slug; }, "duplicate slug");
  invalid(s => { s.estimates[0].study_id = "S9"; s.estimates[0].slug = "s9_missing"; }, "study_id");
  invalid(s => { s.estimates[0].treatment_arm = "Absent"; }, "treatment_arm");
  // A combined arm must say combined or pooled and name at least two arms of the study.
  const combined = clone(alpha);
  const armNames = combined.studies[0].arms.map(a => a.name);
  combined.estimates[0].treatment_arm = `${armNames[0]} and ${armNames[1]} (combined)`;
  assert.doesNotThrow(() => validateSource(combined, "combined.json"));
  invalid(s => { s.estimates[0].treatment_arm = `${s.studies[0].arms[0].name} (combined)`; }, "treatment_arm");
  invalid(s => { s.estimates[0].treatment_arm = `${s.studies[0].arms[0].name} and ${s.studies[0].arms[1].name}`; }, "treatment_arm");
  checks++;
  invalid(s => { s.provenance.review_date = "2026-02-30"; }, "review_date");
  invalid(s => { s.provenance.extraction_date = "2026-10-09T12:00:00Z"; }, "extraction_date");
  invalid(s => { delete s.estimates[0].stats.control_sd; }, "stats.control_sd");
  invalid(s => { s.estimates[0].stats.control_sd = Infinity; }, "stats.control_sd");
  invalid(s => { s.estimates[0].stats.ci_lower = 10; }, "stats.ci_lower");
  invalid(s => { s.estimates[0].stats.p_value = "probably significant"; }, "stats.p_value");
  invalid(s => { s.estimates[0].sources[0].fields = s.estimates[0].sources[0].fields.filter(f => f !== "regression.coef"); }, "stats.regression.coef");
  invalid(s => { s.estimates[0].sources.push(clone(s.estimates[0].sources[0])); }, "exactly one source");
  invalid(s => { s.estimates[0].sources[0].fields.push("regression"); }, "stats.regression.coef");
  invalid(s => { s.estimates[0].sources[0].fields.push("misspelled_stat"); }, "unknown field");
  // Citing the passage behind a coding choice is allowed.
  const codingCitation = clone(alpha);
  codingCitation.estimates[0].sources.push({ fields: ["se_basis", "unit"], locator: "Synthetic p. 3", quote: "standard errors are clustered by participant" });
  assert.doesNotThrow(() => validateSource(codingCitation, "coding-citation.json"));
  checks++;
  const parentCitation = clone(alpha);
  parentCitation.estimates[0].sources[0].fields = parentCitation.estimates[0].sources[0].fields.filter(f => !f.startsWith("regression."));
  parentCitation.estimates[0].sources[0].fields.push("regression");
  assert.doesNotThrow(() => validateSource(parentCitation, "parent-citation.json"));

  const mutations = join(tempRoot, "mutations");
  mkdirSync(mutations);
  function buildMutation(source) {
    writeFileSync(join(mutations, "source.json"), JSON.stringify(source));
    return buildCreativity({ papersDir: mutations, includeDrafts: true });
  }
  const prereg = clone(alpha);
  prereg.estimates.find(e => e.primary_override === true).primary_override = false;
  assert.equal(buildMutation(prereg).estimates.find(e => e.is_primary && e.question === "with_ai").estimate_id, `${alpha.paper_key}__s1_regression_a`);
  const tie = clone(alpha);
  tie.estimates[1].primary_override = false;
  tie.estimates[0].preregistered_primary = "no";
  tie.estimates[7].construct = "overall_creativity";
  assert.throws(() => buildMutation(tie), /unresolved primary tie/);
  // Rule 3 extended: with no preregistration and equal outcome ranks, the contrast of all AI arms combined wins.
  const combinedTie = clone(tie);
  const ai = combinedTie.studies[0].arms.filter(a => a.ai === "generative_ai").map(a => a.name);
  if (ai.length >= 2) {
    const winner = combinedTie.estimates[7];
    winner.treatment_arm = `${ai[0]} and ${ai[1]} (combined)`;
    const built7 = buildMutation(combinedTie);
    assert.equal(built7.estimates.find(e => e.estimate_id === `${alpha.paper_key}__${winner.slug}`).is_primary, true, "combined AI arms break the tie");
    checks++;
  }
  // combinedArms reads the longest arm names first, so "T&AI" is not also read as the arm "T" (2026-10-11).
  const cells = { arms: ["T", "PR", "T&AI", "PR&AI"].map(name => ({ name })) };
  assert.deepEqual(combinedArms(cells, "T&AI and PR&AI (combined)"), ["T&AI", "PR&AI"]);
  assert.deepEqual(combinedArms(cells, "T and PR (combined)"), ["T", "PR"]);
  assert.equal(combinedArms(cells, "T&AI"), null);
  checks += 3;
  // Outcome order below overall creativity and novelty (codebook section 8, added 2026-10-11): usefulness, flexibility,
  // fluency, elaboration.
  const outcomeOrder = clone(alpha);
  outcomeOrder.estimates.forEach(e => {
    if (e.question !== "with_ai") return;
    e.construct = "other";
    e.preregistered_primary = "not_stated";
    delete e.primary_override;
  });
  const [first, second] = [outcomeOrder.estimates[0], outcomeOrder.estimates[2]];
  const primaryWithAI = source => buildMutation(source).estimates.find(e => e.is_primary && e.question === "with_ai").estimate_id;
  first.construct = "fluency";
  second.construct = "flexibility";
  assert.equal(primaryWithAI(outcomeOrder), `${alpha.paper_key}__${second.slug}`, "flexibility before fluency");
  second.construct = "elaboration";
  assert.equal(primaryWithAI(outcomeOrder), `${alpha.paper_key}__${first.slug}`, "fluency before elaboration");
  first.construct = "usefulness";
  second.construct = "flexibility";
  assert.equal(primaryWithAI(outcomeOrder), `${alpha.paper_key}__${first.slug}`, "usefulness before flexibility");
  checks += 3;
  const duplicateOverride = clone(alpha);
  duplicateOverride.estimates[0].primary_override = true;
  assert.throws(() => buildMutation(duplicateOverride), /multiple true overrides/);
  const noPrimary = clone(alpha);
  noPrimary.estimates.forEach(e => { e.primary_override = false; });
  assert.throws(() => buildMutation(noPrimary), /no eligible primary/);
  const missingStudyCount = clone(alpha);
  missingStudyCount.studies[0].n_analyzed = null;
  assert.equal(buildMutation(missingStudyCount).papers[0].n_total, null, "Unknown study count must not become a partial or zero paper total");
  const analysis = clone(alpha);
  analysis.provenance.review_basis = "analysis_output";
  analysis.provenance.extraction_date = null;
  const analysisBuild = buildMutation(analysis);
  assert.equal(analysisBuild.metadata.estimates[`${alpha.paper_key}__s1_regression_a`].provenance.review_basis, "analysis_output");
  assert.ok(analysisBuild.metadata.estimates[`${alpha.paper_key}__s1_regression_a`].provenance.missing_reasons.extraction_date);
  const badReview = clone(alpha);
  badReview.provenance.review_date = null;
  writeFileSync(join(mutations, "source.json"), JSON.stringify(badReview));
  const gatedOut = join(tempRoot, "must-not-write");
  assert.match(run(["--papers-dir", mutations, "--out", gatedOut], 1).stderr, /Metadata release validation failed/);
  assert.equal(existsSync(gatedOut), false, "Metadata failure must precede any write");

  const invalidDraft = clone(draft);
  invalidDraft.estimates[0].n_control = -1;
  writeFileSync(join(mutations, "source.json"), JSON.stringify(invalidDraft));
  // An invalid draft fails the strict (release) build before anything is written; the default build reports and skips it.
  assert.match(run(["--papers-dir", mutations, "--out", gatedOut, "--strict"], 1).stderr, /source\.json: s1_draft: n_control/);
  assert.equal(existsSync(gatedOut), false);
  const lenientOut = join(tempRoot, "lenient");
  assert.match(run(["--papers-dir", mutations, "--out", lenientOut]).stderr, /Draft not valid \(skipped\): .*s1_draft: n_control/);
  const draftOut = join(tempRoot, "including-drafts");
  run(["--papers-dir", FIXTURES, "--out", draftOut, "--include-drafts"]);
  const withDrafts = loadBuild(draftOut);
  assert.ok(withDrafts.papers.some(p => p.paper_key === draft.paper_key));
  invariants(withDrafts, readSources(FIXTURES));

  // Filenames cannot control paper ordering; estimates retain source order.
  const unsorted = join(tempRoot, "unsorted");
  mkdirSync(unsorted);
  const gammaSource = readJSON(join(FIXTURES, "gamma.json"));
  writeFileSync(join(unsorted, "z.json"), JSON.stringify(alpha));
  writeFileSync(join(unsorted, "a.json"), JSON.stringify(beta));
  writeFileSync(join(unsorted, "m.json"), JSON.stringify(gammaSource));
  const sorted = buildCreativity({ papersDir: unsorted });
  const order = [alpha, beta, gammaSource].sort((a, b) => a.paper_key < b.paper_key ? -1 : 1);
  assert.deepEqual(sorted.papers.map(p => p.paper_key), order.map(p => p.paper_key));
  assert.deepEqual(sorted.estimates.map(e => e.estimate_id), order.flatMap(p => p.estimates.map(e => `${p.paper_key}__${e.slug}`)));
  writeFileSync(join(unsorted, "duplicate.json"), JSON.stringify(alpha));
  assert.throws(() => buildCreativity({ papersDir: unsorted }), /duplicate paper key/);
  for (const filename of OUTPUT_FILES) {
    const onDisk = readFileSync(join(fixtureOut, filename), "utf8");
    assert.equal(onDisk, `${JSON.stringify(JSON.parse(onDisk), null, 2)}\n`, "Two spaces and one final newline");
    assert.equal(onDisk, sorted.files[filename], "Builds must be deterministic");
  }
  run(["--papers-dir", FIXTURES, "--out", fixtureOut, "--check"]);
  const corrupted = join(fixtureOut, OUTPUT_FILES[1]);
  writeFileSync(corrupted, `${readFileSync(corrupted, "utf8")}\n`);
  const unchanged = readFileSync(corrupted, "utf8");
  assert.match(run(["--papers-dir", FIXTURES, "--out", fixtureOut, "--check"], 1).stderr, /creativity_estimates\.json: differs at line/);
  assert.equal(readFileSync(corrupted, "utf8"), unchanged, "--check must not write");
  const absent = join(tempRoot, "absent-output");
  assert.match(run(["--papers-dir", FIXTURES, "--out", absent, "--check"], 1).stderr, /missing/);
  assert.equal(existsSync(absent), false, "--check must not create directories");
  assert.match(run(["--papers-dir"], 1).stderr, /requires a directory/);
  assert.match(run(["--unknown"], 1).stderr, /Unknown argument/);

  // CREATIVITY_SMOKE_FIXTURES_ONLY=1 skips the real papers while extraction is in progress (open primary decisions fail it).
  const fixturesOnly = process.env.CREATIVITY_SMOKE_FIXTURES_ONLY === "1";
  let real = { papers: [], estimates: [] };
  if (!fixturesOnly) {
    const realOut = join(tempRoot, "real");
    run(["--out", realOut]);
    real = loadBuild(realOut);
    invariants(real, readSources(DEFAULT_PAPERS_DIR));
    run(["--papers-dir", resolve("code/creativity/papers"), "--out", realOut, "--check"]);
  }
  assert.equal(JSON.stringify([alpha, beta, draft]), untouched, "Checks must not mutate fixture sources");
  console.log(`Creativity smoke checks passed (${built.estimates.length} fixture estimates, drafts validated/excluded/included; ranks 1-5, SE rules a-e, validation/metadata/CLI checks; ${fixturesOnly ? "real papers skipped" : `${real.papers.length} real papers, ${real.estimates.length} real estimates`}; ${checks} numerical, gate and CLI checks).`);
} catch (error) {
  console.error(`Creativity smoke checks failed: ${error.stack || error.message}`);
  process.exitCode = 1;
} finally {
  // Delete only this process's freshly created directory beneath OS temp.
  const resolved = realpathSync(tempRoot);
  const withinTemp = relative(realpathSync(tmpdir()), resolved);
  if (!withinTemp || isAbsolute(withinTemp) || withinTemp.startsWith("..")) throw new Error(`Unsafe temporary cleanup path: ${resolved}`);
  rmSync(resolved, { recursive: true, force: true });
}
