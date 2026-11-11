import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  CSV_METADATA_COLUMNS, evidenceEstimateKey, flattenEstimateMetadata, formatSample,
  resolveEstimateMetadata, resolveStudyMetadata, validateMetadataRelease,
} from "../src/evidence-metadata.mjs";

const read = name => JSON.parse(readFileSync(new URL(`../src/${name}`, import.meta.url), "utf8"));
const papers = read("papers.json");
const estimates = read("estimates.json");
const metadata = read("evidence_metadata.json");
const paper = key => papers.find(p => p.paper_key === key);
const estimate = id => estimates.find(e => e.estimate_id === id);
const before = JSON.stringify({ papers, estimates, metadata });

const learnlm = paper("learnlm_team_2025");
const learning = resolveStudyMetadata(learnlm, metadata);
assert.equal(learnlm.n_total, 2713);
assert.equal(learning.raw_n_total, 2713);
assert.equal(learning.sample.n, 165);
assert.equal(formatSample(learning.sample), "165 students");
assert.equal(learning.sample.randomized_n, null);
assert.equal(learning.sample.recruited_n, null);
assert.equal(learning.provenance.review_status, "reviewed");
assert.equal(learning.provenance.review_basis, "primary_source");
for (const [id, n] of [["est29", 2713], ["est30", 3768], ["est31", 704]]) {
  const record = estimate(`learnlm_team_2025__${id}`);
  const resolved = resolveEstimateMetadata(record, learnlm, metadata);
  assert.equal(resolved.sample.n, n);
  assert.equal(resolved.sample.unit, "sessions");
  assert.match(formatSample(resolved.sample), /sessions$/);
  assert.equal(resolved.provenance.review_status, "reviewed");
}

const contractor = paper("contractor_reyes_2026");
for (const [session, n] of [["one", 210], ["two", 205]]) {
  const record = estimate(`contractor_reyes_2026__contractor_and_reyes_2026_session_${session}_test`);
  const resolved = resolveEstimateMetadata(record, contractor, metadata);
  assert.equal(resolved.sample.n, n);
  assert.equal(resolved.sample.unit, "participants");
  assert.equal(resolved.provenance.review_basis, "analysis_output");
}

const unreviewed = estimates.find(e => !metadata.estimates[e.estimate_id]);
const unresolved = resolveEstimateMetadata(unreviewed, paper(unreviewed.paper_key), metadata);
assert.equal(unresolved.sample.unit, "unknown");
assert.equal(unresolved.sample.review_status, "unreviewed");
assert.match(formatSample(unresolved.sample), /unit unreviewed/);
assert.equal(unresolved.provenance.source_version, null);
assert.equal(unresolved.provenance.review_date, null);
assert.equal(resolveEstimateMetadata(unreviewed).sample.unit, "unknown");
assert.equal(resolveStudyMetadata(papers[0]).sample.unit, "unknown");
assert.equal(formatSample({ n: null, unit: "students", review_status: "reviewed" }), "Not reported");
assert.equal(formatSample({ n: null, unit: "unknown", review_status: "unreviewed" }), "Not reported");
assert.equal(flattenEstimateMetadata(unreviewed, paper(unreviewed.paper_key), metadata).estimate_analyzed_n, null);

const flat = flattenEstimateMetadata(estimate("learnlm_team_2025__est29"), learnlm, metadata);
assert.deepEqual(Object.keys(flat), [...CSV_METADATA_COLUMNS]);
assert.equal(flat.study_sample_n, 165);
assert.equal(flat.estimate_analyzed_n, 2713);
assert.equal(flat.estimate_sample_unit, "sessions");
assert.equal(flat.provenance_review_status, "reviewed");

// Release tests mutate copies of real records only. Their test-only review
// statuses below are inputs for exercising validation, not source attestations.
const baseline = validateMetadataRelease({ papers, estimates, previousEstimates: estimates, metadata });
assert.equal(baseline.valid, true, baseline.errors.join("\n"));
assert.deepEqual(baseline.requiredReviewIds, []);
const reordered = estimates.map(e => Object.fromEntries(Object.entries(e).reverse()));
assert.equal(validateMetadataRelease({ papers, estimates: reordered, previousEstimates: estimates, metadata }).valid, true);

const existing = estimates[0];
const revised = { ...existing, notes: `${existing.notes || ""} Review-required edit.` };
const unreviewedMetadata = structuredClone(metadata);
unreviewedMetadata.estimates[existing.estimate_id].provenance.review_status = "unreviewed";
let result = validateMetadataRelease({ papers, estimates: [revised], previousEstimates: [existing], metadata: unreviewedMetadata });
assert.equal(result.valid, false);
assert.deepEqual(result.requiredReviewIds, [existing.estimate_id]);
assert.ok(result.errors.some(error => error.includes("not been reviewed")));
assert.equal(validateMetadataRelease({ papers, estimates: [unreviewed], metadata }).valid, false);

const testOnlyMetadata = structuredClone(metadata);
testOnlyMetadata.estimates = { [existing.estimate_id]: testOnlyMetadata.estimates[existing.estimate_id] };
const annotation = testOnlyMetadata.estimates[existing.estimate_id];
annotation.sample.review_basis = "primary_source";
annotation.provenance.review_status = "reviewed";
annotation.provenance.review_basis = "primary_source";
annotation.provenance.source_version = null;
annotation.provenance.extraction_date = null;
annotation.provenance.missing_reasons = {
  source_version: "Not reported in this validation test input.",
  extraction_date: "Not reported in this validation test input.",
};
result = validateMetadataRelease({ papers, estimates: [revised], previousEstimates: [existing], metadata: testOnlyMetadata });
assert.equal(result.valid, true, result.errors.join("\n"));
delete annotation.provenance.missing_reasons.source_version;
assert.equal(validateMetadataRelease({ papers, estimates: [revised], previousEstimates: [existing], metadata: testOnlyMetadata }).valid, false);
annotation.provenance.source_version = "Test-only version marker";
annotation.provenance.review_date = "2026-02-30";
assert.equal(validateMetadataRelease({ papers, estimates: [revised], previousEstimates: [existing], metadata: testOnlyMetadata }).valid, false);
annotation.provenance.review_date = "2026-09-23";
annotation.sample.n = existing.n_total - 1;
assert.ok(validateMetadataRelease({ papers, estimates: [revised], previousEstimates: [existing], metadata: testOnlyMetadata }).errors.some(e => e.includes("does not match")));

const creativePapers = read("creativity_papers.json").papers;
const creativeEstimates = read("creativity_estimates.json");
assert.equal(new Set(creativeEstimates.map(evidenceEstimateKey)).size, creativeEstimates.length);
assert.equal(validateMetadataRelease({ papers: creativePapers, estimates: creativeEstimates, previousEstimates: creativeEstimates, metadata: { schema_version: 1 } }).valid, true);
const creative = creativeEstimates[0];
assert.equal(resolveEstimateMetadata(creative, creativePapers.find(p => p.paper_key === creative.paper_key), metadata).raw_n_total, creative.n);
assert.equal(JSON.stringify({ papers, estimates, metadata }), before, "Resolvers must not mutate evidence or metadata.");
assert.equal(metadata.timing_audit.flags.length, 3);
for (const corrupt of [
  data => { data.studies.learnlm_team_2025.sample.n = -1; },
  data => { data.studies.learnlm_team_2025.sample.unit = "people_maybe"; },
  data => { data.studies.learnlm_team_2025.sample.review_status = "verified_ish"; },
  data => { data.studies.learnlm_team_2025.provenance.review_date = "yesterday"; },
  data => { data.estimates.unknown_estimate = {}; },
  data => { data.studies.unknown_paper = {}; },
]) {
  const broken = structuredClone(metadata);
  corrupt(broken);
  assert.equal(validateMetadataRelease({ papers, estimates, previousEstimates: estimates, metadata: broken }).valid, false, "Malformed metadata must fail even when raw estimates are unchanged.");
}

// Editorial receipts use test-only prose revisions to a real unreviewed row.
// They never supply a source attestation or authorize another field change.
const editorialOriginal = estimate("wiles_etal_2024__est48");
assert.equal(resolveEstimateMetadata(editorialOriginal, paper(editorialOriginal.paper_key), metadata).provenance.review_status, "unreviewed");
const editorialRevised = { ...editorialOriginal, notes: `${editorialOriginal.notes} Editorial validation test only.` };
const receipt = {
  previous_release_id: "editorial-test-previous", estimate_id: editorialOriginal.estimate_id,
  field: "notes", before: editorialOriginal.notes, after: editorialRevised.notes,
  reason: "Exercise exact wording approval in an isolated validation input.",
};
const editorialInput = {
  papers, estimates: estimates.map(row => row === editorialOriginal ? editorialRevised : row),
  previousEstimates: estimates, metadata, previousReleaseId: receipt.previous_release_id,
  editorialReviews: [receipt],
};
result = validateMetadataRelease(editorialInput);
assert.equal(result.valid, true, result.errors.join("\n"));
assert.deepEqual(result.requiredReviewIds, []);
assert.deepEqual(result.editorialReviewIds, [editorialOriginal.estimate_id]);
assert.equal(resolveEstimateMetadata(editorialRevised, paper(editorialRevised.paper_key), metadata).sample.review_status, "unreviewed");
assert.equal(resolveEstimateMetadata(editorialRevised, paper(editorialRevised.paper_key), metadata).provenance.review_status, "unreviewed");
assert.equal(resolveEstimateMetadata(editorialRevised, paper(editorialRevised.paper_key), metadata).provenance.review_date, null);
assert.equal(validateMetadataRelease({ ...editorialInput, editorialReviews: [] }).valid, false, "Unapproved notes still require source review.");
assert.equal(validateMetadataRelease({ ...editorialInput, previousReleaseId: "another-release" }).valid, false, "An older receipt cannot authorize a later edit.");
assert.equal(validateMetadataRelease({ ...editorialInput, previousReleaseId: null }).valid, false);
for (const patch of [
  { before: `${receipt.before} changed` }, { after: `${receipt.after} changed` },
  { field: "effect_size_sd" }, { reason: "" }, { estimate_id: "unknown-estimate" },
]) {
  const invalid = validateMetadataRelease({ ...editorialInput, editorialReviews: [{ ...receipt, ...patch }] });
  assert.equal(invalid.valid, false, `Invalid editorial receipt passed: ${JSON.stringify(patch)}`);
}
assert.equal(validateMetadataRelease({ ...editorialInput, editorialReviews: [receipt, receipt] }).valid, false);
for (const patch of [
  { effect_size_sd: (editorialOriginal.effect_size_sd ?? 0) + 1 },
  { se: (editorialOriginal.se ?? 0) + 1 },
  { n_total: editorialOriginal.n_total + 1 },
  { design_class: editorialOriginal.design_class === "observational" ? "lab_rct" : "observational" },
  { outcome_timing: editorialOriginal.outcome_timing === "immediate" ? "delayed" : "immediate" },
  { source_document: "Different source, validation test only" },
  { coding_notes: `${editorialOriginal.coding_notes || ""} Changed source information.` },
]) {
  const invalid = validateMetadataRelease({
    ...editorialInput,
    estimates: editorialInput.estimates.map(row => row.estimate_id === editorialRevised.estimate_id ? { ...row, ...patch } : row),
  });
  assert.equal(invalid.valid, false, `Editorial receipt approved a non-notes change: ${JSON.stringify(patch)}`);
  assert.ok(invalid.errors.some(error => error.includes("outside notes")));
}
assert.equal(validateMetadataRelease({
  ...editorialInput, previousEstimates: estimates.filter(row => row.estimate_id !== editorialOriginal.estimate_id),
}).valid, false, "Editorial receipts cannot approve a new estimate.");
assert.equal(JSON.stringify({ papers, estimates, metadata }), before, "Editorial validation must not mutate data or review status.");
console.log(`Metadata smoke checks passed (${papers.length} learning studies, ${estimates.length} learning estimates, ${creativeEstimates.length} creativity estimates).`);
