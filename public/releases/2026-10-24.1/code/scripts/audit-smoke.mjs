// Regression checks for the September 2026 primary-source numerical audit.
// Expected values below come from source tables or the documented Stata checks,
// not from the generated website JSON. Run with node scripts/audit-smoke.mjs.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ciOf, filterEstimates, isPlottableEstimate, isPoolableEstimate } from "../src/shared.mjs";
import { resolveEstimateMetadata, resolveStudyMetadata } from "../src/evidence-metadata.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const json = name => JSON.parse(readFileSync(join(root, name), "utf8"));
const papers = json("src/papers.json");
const estimates = json("src/estimates.json");
const metadata = json("src/evidence_metadata.json");
const pin = json("code/sources/contractor-reyes-2026-09.json");
const byId = new Map(estimates.map(row => [row.estimate_id, row]));
const byPaper = new Map(papers.map(row => [row.paper_key, row]));
let checks = 0;
const failures = [];
function check(value, message) { checks++; if (!value) failures.push(message); }
function near(actual, expected, label, tolerance = 1e-9) {
  check(Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance,
    `${label}: ${actual} differs from ${expected}`);
}
function row(id) {
  const found = byId.get(id);
  assert.ok(found, `Missing audited row ${id}`);
  return found;
}
function hash(path) {
  return createHash("sha256").update(readFileSync(join(root, path))).digest("hex");
}

// Contractor-Reyes: September PDF Tables 4/5/A5 and the matching OLS output.
// Test rows use the control-standardized score. Essay rows divide raw beta and
// robust SE by the recorded control SD, held fixed in this conversion.
const prefix = "contractor_reyes_2026__";
const contractorExpected = [
  ["contractor_and_reyes_2026_session_one_test", .2921569988904246, .1206987721922262, 210, 106, 104, .292, .121],
  ["contractor_and_reyes_2026_session_two_test", .202047007198674, .1156536671106937, 205, 103, 102, .202, .116],
  ["contractor_and_reyes_2026_session_one_essay", .1947852192051345, .1449083356337063, 210, 106, 104, .277, .206],
  ["contractor_and_reyes_2026_session_two_essay", .2040974536179515, .1315390434525418, 198, 101, 97, .312, .201],
  ["sg1", .2489013756162245, .1303559915125231, 198, 101, 97, .337, .176],
  ["sg2", .2353898284074848, .146964024709525, 198, 101, 97, .319, .199],
  ["sg3", .1279733962186383, .132014557745932, 198, 101, 97, .204, .211],
  ["sg4", .2099684703835788, .1311547780504176, 198, 101, 97, .325, .203],
  ["sg5", .1912583062153303, .1428938381721044, 196, null, null, .261, .195],
];
check(pin.estimates.length === 9, "Contractor source pin must contain all nine rows");
check(pin.source_version === "September 2026", "Contractor source version must be explicit");
check(pin.source_pdf_sha256 === "51470a61115adc438decacf062d340ca1302190e73341c9e7b78a70e99d6908a",
  "Contractor source pin changed its verified PDF hash");
check(pin.source_data_sha256 === "381cc9363d0d58ba124ac532bfd3fa678c222ca66c93a1db0fac2631775e0bd8",
  "Contractor source pin changed its verified regression-output hash");
check(hash(join("public/pdfs", pin.source_document)) === pin.source_pdf_sha256,
  "Contractor September PDF differs from the verified source");
check(hash("public/pdfs/Contractor & Reyes (2026) - AI Learning RCT.pdf") ===
  "7cde768e9afd5cc3312a17d627dcda2b062e3395aaaeba0f525d68da32d18ce1",
  "The original July Contractor PDF must remain unchanged");
const contractorPaper = byPaper.get("contractor_reyes_2026");
check(contractorPaper?.pdf_filename === pin.source_document, "Contractor paper must link the September PDF");
const contractorStudy = resolveStudyMetadata(contractorPaper, metadata);
check(contractorStudy.sample.n === 211 && contractorStudy.sample.randomized_n === 256,
  "Contractor must distinguish 211 Session One attendees from 256 assigned students");
for (const [suffix, effect, se, n, nt, nc, pdfBeta, pdfSE] of contractorExpected) {
  const id = prefix + suffix;
  const actual = row(id);
  const source = pin.estimates.find(item => item.estimate_id === id);
  check(Boolean(source), `${id}: absent from source pin`);
  near(source.raw_effect, pdfBeta, `${id} PDF coefficient`, .0005);
  near(source.raw_se, pdfSE, `${id} PDF SE`, .0005);
  check(source.sd_control > 0, `${id}: missing control SD`);
  near(source.raw_effect / source.sd_control, effect, `${id} source standardization`);
  near(source.raw_se / source.sd_control, se, `${id} source SE standardization`);
  near(actual.effect_size_sd, effect, `${id} website effect`);
  near(actual.se, se, `${id} website SE`);
  near(actual.ci_lower, effect - 1.96 * se, `${id} CI lower`);
  near(actual.ci_upper, effect + 1.96 * se, `${id} CI upper`);
  check(actual.n_total === n && actual.n_treatment === nt && actual.n_control === nc,
    `${id}: outcome-specific sample or arm counts changed`);
  const resolved = resolveEstimateMetadata(actual, contractorPaper, metadata);
  check(resolved.sample.n === n, `${id}: sample annotation overrides the verified count`);
  const annotatedVersion = String(resolved.provenance.source_version || "");
  check(resolved.provenance.source_document === pin.source_document &&
    annotatedVersion.startsWith("September 2026") &&
    annotatedVersion.toLowerCase().includes(pin.source_pdf_sha256) &&
    annotatedVersion.toLowerCase().includes(pin.source_data_sha256) &&
    resolved.provenance.review_status === "reviewed", `${id}: source/version review missing`);
  check(source.source_locator.includes("Table") && source.derivation_notes.includes("Stata"),
    `${id}: source or derivation locator missing`);
}
check(pin.estimates.find(item => item.estimate_id === prefix + "sg5").derivation_notes.includes("N=198"),
  "Accuracy extraction must disclose the PDF shared-N discrepancy");
check(row(prefix + "contractor_and_reyes_2026_session_one_essay").outcome_with_ai === true,
  "Session One essay is AI-assisted performance, not an unaided assessment");

// Bassner: observed within-person gain variance from the verified public data.
// These are AI-versus-control contrasts, not the separate Iris-versus-ChatGPT result.
const control = { n: 96, gain: .8541666666666666, gainSD: 1.56258333111123, preSD: 1.861898672502525 };
const normal975 = 1.959963984540054;
for (const [id, n, gain, gainSD, preSD] of [
  ["bassner_etal_2026__est59", 91, .7142857142857143, 1.249761882081847, 1.947039956180816],
  ["bassner_etal_2026__est60", 88, .8295454545454546, 1.391448355723549, 1.817675608737652],
]) {
  const actual = row(id);
  const denominator = Math.sqrt(((n - 1) * preSD ** 2 + (control.n - 1) * control.preSD ** 2) / (n + control.n - 2));
  const expectedEffect = (gain - control.gain) / denominator;
  const expectedSE = Math.sqrt(gainSD ** 2 / n + control.gainSD ** 2 / control.n) / denominator;
  near(actual.effect_size_sd, expectedEffect, `${id} observed-gain effect`);
  near(actual.se, expectedSE, `${id} observed-gain SE`);
  near(actual.ci_lower, expectedEffect - normal975 * expectedSE, `${id} lower CI`);
  near(actual.ci_upper, expectedEffect + normal975 * expectedSE, `${id} upper CI`);
  check(actual.n_total === n + control.n, `${id}: contrast N must exclude the other AI arm`);
}
for (const [suffix, n] of [["est61", 187], ["est62", 184], ["est63", 184], ["est84", 187]]) {
  check(row(`bassner_etal_2026__${suffix}`).n_total === n, `Bassner ${suffix}: wrong contrast N`);
}

// Franco Table 2 reports raw exam-point effects, not a verified outcome SD.
for (const [suffix, effect, se] of [["est85", .078, .192], ["est86", -.234, .189]]) {
  const actual = row(`franco_etal_2026__${suffix}`);
  for (const field of ["effect_size_sd", "se", "ci_lower", "ci_upper"])
    check(actual[field] === null, `${actual.estimate_id}: unsupported standardized ${field}`);
  check(!isPlottableEstimate(actual) && !isPoolableEstimate(actual), `${actual.estimate_id}: raw-scale result entered SD pooling`);
  const recorded = JSON.stringify(actual);
  check(recorded.includes(String(effect)) && recorded.includes(String(se)),
    `${actual.estimate_id}: verified raw effect/SE must remain accessible`);
}
check(/604/.test(byPaper.get("franco_etal_2026").summary), "Franco summary must report 604 randomized, not 572");
check(!/entirely through/i.test(byPaper.get("hou_etal_2026").summary), "Hou gain was not entirely on reasoning items");

// Corrections to outcome labels, uncertainty, sign orientation and eligibility.
const chung = estimates.filter(item => item.paper_key === "chung_etal_2025");
check(chung.length > 0 && chung.every(item => item.learning_domain === "Coding"), "Chung outcomes must be Coding, not Math");
const math = filterEstimates(estimates, { paperKeys: new Set(papers.map(item => item.paper_key)), comparisonType: "ai_design", activeDomains: new Set(["Math"]) });
check(!math.some(item => item.paper_key === "chung_etal_2025"), "Chung coding outcomes leaked into Math");
check(estimates.filter(item => item.paper_key === "learnlm_team_2025").every(item => item.learning_domain === "Math"),
  "LearnLM UK math outcomes must not be classified as Science");
const henkel = row("henkel_etal_2024__est15");
near(henkel.effect_size_sd, .36, "Henkel reported effect");
check(henkel.se === null && henkel.ci_lower === null && henkel.ci_upper === null && !isPoolableEstimate(henkel),
  "Henkel's school-randomized effect must not use individual-level precision for pooling");
near(row("lira_etal_2025__est38").se, .049, "Lira Table S20 SE");
check(row("lira_etal_2025__est38").n_total === null, "Lira full three-arm allocation is not a verified analyzed contrast N");
for (const suffix of ["est33", "est36"]) {
  const method = row(`lehmann_etal_2024__${suffix}`).estimation_method || "";
  check(!/ANCOVA/i.test(method) && /unadjusted|mean|Cohen/i.test(method), `Lehmann ${suffix}: post-test mean effect mislabeled as ANCOVA`);
}
for (const suffix of ["sg2", "sg4"]) {
  const actual = row(`lehmann_etal_2024__${suffix}`);
  check(actual.se === null && actual.ci_lower === null && actual.ci_upper === null,
    `${actual.estimate_id}: missing coefficient covariance cannot be replaced by interaction SE`);
}
for (const [suffix, effect, low, high] of [["sg4", -.25, -.48, -.02], ["sg5", -.42, -.72, -.11]]) {
  const actual = row(`liu_etal_2026__${suffix}`);
  near(actual.effect_size_sd, effect, `${actual.estimate_id} harm-oriented sign`);
  near(actual.ci_lower, low, `${actual.estimate_id} reversed lower CI`);
  near(actual.ci_upper, high, `${actual.estimate_id} reversed upper CI`);
}
near(row("liu_etal_2026__sg1").ci_lower, -.54, "Liu reported direct-user lower CI");
near(row("liu_etal_2026__sg1").ci_upper, -.17, "Liu reported direct-user upper CI");
check(!byPaper.has("kalam_etal_2025") && !estimates.some(item => item.paper_key === "kalam_etal_2025"),
  "Kalam study N=33 falls below the stated study-level minimum of 50");
// Dataset counts: 34 papers / 137 rows / 110 standardized after the September 23
// audit, plus five papers (27 rows, 26 standardized) added on October 3, 2026,
// plus three papers (6 rows, 4 standardized) added on October 5, 2026,
// plus Asirvatham (14 standardized point estimates) added on October 24, 2026.
check(papers.length === 43 && estimates.length === 184, "Dataset counts changed: expected 43 papers and 184 estimate rows");
check(estimates.filter(item => Number.isFinite(item.effect_size_sd)).length === 154,
  "Available standardized effects must be counted separately from estimate records");
for (const [id, annotation] of Object.entries(metadata.estimates)) {
  if (annotation.provenance?.review_status !== "reviewed") continue;
  const document = annotation.provenance.source_document;
  check(annotation.provenance.source_version.includes(hash(join("public/pdfs", document))),
    `${id}: reviewed source version no longer identifies its linked PDF`);
}

// Known source distinctions must survive the rebuild unchanged.
near(row("gan_etal_2024__est70").effect_size_sd, .398, "Gan internally consistent abstract effect");
near(row("gan_etal_2024__est71").effect_size_sd, .446, "Gan surgery effect");
for (const [suffix, effect, se, low, high] of [["est76", .258, .115, .027, .488], ["est77", .380, .169, .040, .719]]) {
  const actual = row(`learnlm_team_2026__${suffix}`);
  near(actual.effect_size_sd, effect, `Sierra Leone ${suffix} effect`);
  near(actual.se, se, `Sierra Leone ${suffix} SE`);
  check(actual.n_total === 1423, `Sierra Leone ${suffix} must retain the balanced panel`);
  const ci = ciOf(actual);
  near(ci.lo, low, `Sierra Leone ${suffix} source CI lower`);
  near(ci.hi, high, `Sierra Leone ${suffix} source CI upper`);
}
for (const [suffix, effect, se, n] of [["est80", -1.366, .0279, 26811], ["est81", -.324, .0236, 4034], ["est82", -.360, .0422, 4260], ["est83", 1.9, .0199, 18345]]) {
  const actual = row(`stromberg_etal_2026__${suffix}`);
  near(actual.effect_size_sd, effect, `Stromberg ${suffix} effect`);
  near(actual.se, se, `Stromberg ${suffix} SE`);
  check(actual.n_total === n, `Stromberg ${suffix} outcome-specific N changed`);
}

// October 2026 additions: values recomputed from the cited tables (see
// docs/ra-verification-queue.md for the derivations awaiting human review).
near(row("maier_etal_2026__est87").effect_size_sd, -.0257 / Math.sqrt((136 * .34 ** 2 + 145 * .32 ** 2) / 281), "Maier AI-only vs control (Table 8 difference / Table 2 pooled SD)", 1e-4);
near(row("maier_etal_2026__est87").se, (.0514 + .1028) / (2 * 1.96) / Math.sqrt((136 * .34 ** 2 + 145 * .32 ** 2) / 281), "Maier AI-only SE from the Table 8 CI", 1e-4);
near(row("maier_etal_2026__est91").effect_size_sd, .1624, "Maier metacognitive-feedback main effect", 1e-4);
near(row("maier_etal_2026__est92").effect_size_sd, -.1086, "Maier reward main effect", 1e-4);
check(["est91", "est92"].every(suffix => row(`maier_etal_2026__${suffix}`).comparison_type === "ai_design"), "Maier factorial main effects are design contrasts, not AI-versus-no-AI");
near(row("ates_2026__est93").effect_size_sd, -.12, "Ates direct AI vs peer, delayed transfer (paper's d)", 1e-9);
near(row("ates_2026__est93").se, .25 * (.12 / .36), "Ates direct AI vs peer SE scaled by d/b", 1e-4);
near(row("ates_2026__est97").effect_size_sd, .48, "Ates hybrid vs direct AI, delayed transfer", 1e-9);
check(["est96", "est97"].every(suffix => row(`ates_2026__${suffix}`).comparison_type === "ai_design"), "Ates reflective/hybrid vs direct AI are design contrasts");
check(["est101", "est102", "est103"].every(suffix => row(`ates_2026__${suffix}`).outcome_with_ai === true), "Ates draft-to-revision gains were produced with the feedback in hand");
near(row("oreopoulos_etal_2026__est104").effect_size_sd, .032 / Math.sqrt(.37 * .63), "NUMI practiced Exercise 1 item standardized by the CAL-only Bernoulli SD", 1e-4);
near(row("oreopoulos_etal_2026__est104").se, .017 / Math.sqrt(.37 * .63), "NUMI practiced Exercise 1 SE", 1e-4);
check(row("oreopoulos_etal_2026__est106").effect_size_sd === null && /-0\.041/.test(row("oreopoulos_etal_2026__est106").notes || ""),
  "NUMI non-mastery two-item total stays raw (-0.041) with no SD conversion");
check(row("oreopoulos_and_low_2026__est107").comparison_type === "ai_bundled" && row("oreopoulos_and_low_2026__est107").n_total === 6902,
  "Khanmigo bundled program row must be ai_bundled with 6,902 student-terms");
near(row("oreopoulos_and_low_2026__est107").effect_size_sd, .05, "Khanmigo pooled ITT in control SD", 1e-9);
check(!filterEstimates(estimates, { paperKeys: new Set(papers.map(item => item.paper_key)) }).some(item => item.paper_key === "oreopoulos_and_low_2026"),
  "Bundled Khanmigo rows must not enter the AI-versus-business-as-usual pool");
check(filterEstimates(estimates, { paperKeys: new Set(papers.map(item => item.paper_key)), comparisonType: "ai_bundled" }).map(item => item.estimate_id).join() ===
  "oreopoulos_and_low_2026__est107,barrera_osorio_and_munoz_morales_2026__est114",
  "The bundled view holds exactly the Khanmigo and Bogota main rows");
for (const [suffix, effect, se, n] of [["est108", .171, .087, 520], ["est109", .071, .080, 654]]) {
  const actual = row(`cruces_etal_2026__${suffix}`);
  near(actual.effect_size_sd, effect, `Cruces ${suffix} follow-up effect`, 1e-9);
  near(actual.se, se, `Cruces ${suffix} SE`, 1e-9);
  check(actual.n_total === n && actual.is_subgroup !== true, `Cruces ${suffix}: stratum row count or main-row status changed`);
}

// October 5, 2026 additions: values recomputed from the printed statistics
// (see docs/ra-verification-queue.md for the checks awaiting human review).
const pooledSd = (n1, s1, n2, s2) => Math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2));
const dSe = (d, n1, n2) => Math.sqrt((n1 + n2) / (n1 * n2) + d ** 2 / (2 * (n1 + n2)));
const heldrethNow = (9.2 - 8.2) / pooledSd(30, 2.2, 30, 2.0);
const heldrethLater = (4.7 - 4.0) / pooledSd(29, 1.2, 29, 1.4);
near(row("heldreth_etal_2026__est110").effect_size_sd, heldrethNow, "Heldreth immediate recall d from the printed means and SDs", 1e-4);
near(row("heldreth_etal_2026__est110").se, dSe(heldrethNow, 30, 30), "Heldreth immediate recall SE", 1e-4);
near(row("heldreth_etal_2026__est111").effect_size_sd, heldrethLater, "Heldreth follow-up recall d from the printed means and SDs", 1e-4);
near(row("heldreth_etal_2026__est111").se, dSe(heldrethLater, 29, 29), "Heldreth follow-up recall SE", 1e-4);
check(row("heldreth_etal_2026__est110").n_total === 60 && row("heldreth_etal_2026__est111").n_total === 58 &&
  row("heldreth_etal_2026__est111").outcome_timing === "delayed", "Heldreth analyzed counts or follow-up timing changed");
check(filterEstimates(estimates, { paperKeys: new Set(papers.map(item => item.paper_key)) }).filter(item => item.paper_key === "heldreth_etal_2026").length === 2,
  "Both Heldreth rows belong to the AI-versus-business-as-usual view");
for (const [suffix, n, withAi, oddsRatio] of [["est112", 6698, false, /0\.75/], ["est113", 3223, true, /85 percent/]]) {
  const actual = row(`rismanchian_etal_2026__${suffix}`);
  check(actual.effect_size_sd === null && actual.se === null && actual.ci_lower === null && actual.ci_upper === null,
    `Rismanchian ${suffix}: odds ratios stay raw with no SD conversion`);
  check(actual.n_total === n && actual.outcome_with_ai === withAi && actual.design_class === "observational" && oddsRatio.test(actual.notes || ""),
    `Rismanchian ${suffix}: response count, AI-at-test flag, design class, or reported odds changed`);
}
const bogota = row("barrera_osorio_and_munoz_morales_2026__est114");
near(bogota.effect_size_sd, .207, "Bogota midline ITT (Table 5, Panel B, column 2)", 1e-9);
near(bogota.se, .098, "Bogota midline SE", 1e-9);
check(bogota.comparison_type === "ai_bundled" && bogota.n_total === 2264 && bogota.is_subgroup !== true,
  "Bogota main row must be ai_bundled with 2,264 students");
const bogotaIntact = row("barrera_osorio_and_munoz_morales_2026__sg1");
near(bogotaIntact.effect_size_sd, .133, "Bogota intact-randomization sample (Table 5, Panel B, column 5)", 1e-9);
near(bogotaIntact.se, .119, "Bogota intact-randomization SE", 1e-9);
check(bogotaIntact.is_subgroup === true && bogotaIntact.comparison_type === "ai_bundled" && bogotaIntact.n_total === 1604,
  "Bogota intact-randomization row stays secondary and bundled");
check(!filterEstimates(estimates, { paperKeys: new Set(papers.map(item => item.paper_key)) })
  .some(item => ["barrera_osorio_and_munoz_morales_2026", "rismanchian_etal_2026"].includes(item.paper_key)),
  "Bundled Bogota rows and observational Rismanchian rows must not enter the default pool");

// Asirvatham: Appendix Tables A.7, A.9-A.11, August 2026 PDF.
const asirvatham = estimates.filter(e => e.paper_key === "asirvatham_etal_2026");
check(asirvatham.length === 14, "Asirvatham must retain both AI contrasts for seven outcomes");
const sourceCoefficients = [
  [.862, .082, .843], [-.008, .129, .437], [.029, .203, 1.027],
  [.214, .228, .478], [.026, .003, .041], [.028, -.007, .045], [.044, -.002, .050],
];
for (const [i, [gpt, interaction, sd]] of sourceCoefficients.entries()) {
  for (const trained of [0, 1]) {
    const estimate = row(`asirvatham_etal_2026__est${115 + i * 2 + trained}`);
    near(estimate.effect_size_sd, (gpt + trained * interaction) / sd,
      `Asirvatham outcome ${i}, trained ${trained}: use the AI contrast, not the interaction alone`, 1e-9);
    check(estimate.n_total === 1053 && estimate.n_treatment === (trained ? 351 : 197) &&
      estimate.n_control === (trained ? 256 : 249), "Asirvatham: separate regression N from contrast counts");
    check(estimate.outcome_with_ai === true && estimate.outcome_timing === "immediate" &&
      estimate.comparison_type === "ai_vs_bau", "Asirvatham: AI access during assessment and fixed training condition");
    check(estimate.se === null && estimate.ci_lower === null && estimate.ci_upper === null &&
      !isPoolableEstimate(estimate) && !isPlottableEstimate(estimate),
      "Asirvatham: no class-level precision, no interval or pooled weight");
  }
}
const asirvathamKeys = new Set(["asirvatham_etal_2026"]);
check(filterEstimates(estimates, { paperKeys: asirvathamKeys }).length === 0,
  "Asirvatham must be excluded from the default unaided-outcome view");
check(filterEstimates(estimates, { paperKeys: asirvathamKeys, outcomeMode: "all" }).length === 14,
  "Asirvatham must be available when AI-assisted outcomes are included");
const asirvathamPdf = readFileSync(join(root, "public/pdfs/Asirvatham et al (2026) - Training Novices to Think or Giving Them LLMs.pdf"));
check(createHash("sha256").update(asirvathamPdf).digest("hex") ===
  "5f4873c28ac6b184c6675c603832a9b0da7f90872abfce40e7c37dad995cd721",
  "Asirvatham PDF must match the primary-source review");

assert.equal(failures.length, 0, failures.join("\n"));
console.log(`All ${checks} numerical audit checks passed (${papers.length} papers, ${estimates.length} estimates).`);
