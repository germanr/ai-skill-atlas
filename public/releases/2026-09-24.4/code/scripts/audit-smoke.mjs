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
check(papers.length === 34 && estimates.length === 137, "Audit should remove only the ineligible Kalam paper and its two rows");
check(estimates.filter(item => Number.isFinite(item.effect_size_sd)).length === 110,
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

assert.equal(failures.length, 0, failures.join("\n"));
console.log(`All ${checks} numerical audit checks passed (${papers.length} papers, ${estimates.length} estimates).`);
