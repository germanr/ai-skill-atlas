// Durable annotations live outside the generated evidence arrays. A coding-note
// check is not a primary-source review, so sample and provenance status differ.
export const METADATA_SCHEMA_VERSION = 1;
export const CSV_METADATA_COLUMNS = Object.freeze([
  "study_sample_n", "study_sample_unit", "study_sample_review_status",
  "study_recruited_n", "study_randomized_n", "estimate_analyzed_n",
  "estimate_sample_unit", "estimate_sample_review_status", "source_document",
  "source_url", "source_version", "source_locator", "extraction_date",
  "review_date", "provenance_review_status", "provenance_review_basis", "derivation_notes",
  "study_sample_review_basis", "study_sample_notes", "study_sample_missing_reasons",
  "estimate_sample_review_basis", "estimate_sample_notes", "estimate_sample_missing_reasons",
  "provenance_missing_reasons",
]);
export const SAMPLE_UNITS = Object.freeze([
  "unknown", "participants", "students", "sessions", "student_terms",
  "student_years", "responses", "classes", "schools", "workers", "teams",
]);

const own = (object, key) => Object.prototype.hasOwnProperty.call(object || {}, key);
const nonempty = value => typeof value === "string" && value.trim().length > 0;
const validCount = value => value === null || (Number.isInteger(value) && value >= 0);
const countOrNull = value => validCount(value) && value !== undefined ? value : null;
const isDate = value => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.valueOf()) && date.toISOString().slice(0, 10) === value;
};
const canonical = value => {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical(value[key])]),
  );
  return value;
};

export function evidenceEstimateKey(estimate) {
  return estimate.estimate_id || `${estimate.paper_key}__outcome_${estimate.outcome_idx}`;
}

function defaultProvenance(record, paper = record) {
  return {
    source_document: paper?.pdf_filename || null,
    source_url: paper?.pdf_url || null,
    source_version: null,
    source_locator: null,
    extraction_date: null,
    review_date: null,
    review_status: "unreviewed",
    review_basis: null,
    derivation_notes: record?.notes || record?.coding_notes || null,
    missing_reasons: {},
  };
}

export function resolveStudyMetadata(paper, metadata = {}) {
  const override = metadata.studies?.[paper?.paper_key] || {};
  const raw = countOrNull(paper?.n_total ?? paper?.n ?? null);
  return {
    raw_n_total: raw,
    sample: {
      n: raw, unit: "unknown", review_status: "unreviewed", review_basis: null,
      recruited_n: null, randomized_n: null, notes: null, missing_reasons: {},
      ...override.sample,
    },
    provenance: { ...defaultProvenance(paper), ...override.provenance },
  };
}

export function resolveEstimateMetadata(estimate, paper, metadata = {}) {
  const override = metadata.estimates?.[evidenceEstimateKey(estimate)] || {};
  const raw = countOrNull(estimate?.n_total ?? estimate?.n ?? null);
  return {
    raw_n_total: raw,
    sample: {
      n: raw, unit: "unknown", review_status: "unreviewed", review_basis: null,
      treatment_n: countOrNull(estimate?.n_treatment ?? null),
      control_n: countOrNull(estimate?.n_control ?? null), notes: null, missing_reasons: {},
      ...override.sample,
    },
    // A study's locator cannot stand in for this estimate's source location.
    provenance: { ...defaultProvenance(estimate, paper), ...override.provenance },
  };
}

const UNIT_LABELS = {
  participants: "participants", students: "students", sessions: "sessions",
  student_terms: "student-terms", student_years: "student-years", responses: "responses",
  classes: "classes", schools: "schools", workers: "workers", teams: "teams",
};

export function formatSample(sample) {
  if (sample?.n == null) return "Not reported";
  const number = sample.n.toLocaleString("en-US");
  if (sample?.review_status !== "reviewed") return `${number} (unit unreviewed)`;
  const unit = UNIT_LABELS[sample.unit];
  if (!unit) return `${number} (unit not reported)`;
  return `${number} ${unit}`;
}

export function flattenEstimateMetadata(estimate, paper, metadata = {}) {
  const study = resolveStudyMetadata(paper, metadata);
  const endpoint = resolveEstimateMetadata(estimate, paper, metadata);
  return {
    study_sample_n: study.sample.n,
    study_sample_unit: study.sample.unit,
    study_sample_review_status: study.sample.review_status,
    study_recruited_n: study.sample.recruited_n,
    study_randomized_n: study.sample.randomized_n,
    estimate_analyzed_n: endpoint.sample.review_status === "reviewed" ? endpoint.sample.n : null,
    estimate_sample_unit: endpoint.sample.unit,
    estimate_sample_review_status: endpoint.sample.review_status,
    source_document: endpoint.provenance.source_document,
    source_url: endpoint.provenance.source_url,
    source_version: endpoint.provenance.source_version,
    source_locator: endpoint.provenance.source_locator,
    extraction_date: endpoint.provenance.extraction_date,
    review_date: endpoint.provenance.review_date,
    provenance_review_status: endpoint.provenance.review_status,
    provenance_review_basis: endpoint.provenance.review_basis,
    derivation_notes: endpoint.provenance.derivation_notes,
    study_sample_review_basis: study.sample.review_basis,
    study_sample_notes: study.sample.notes,
    study_sample_missing_reasons: JSON.stringify(study.sample.missing_reasons),
    estimate_sample_review_basis: endpoint.sample.review_basis,
    estimate_sample_notes: endpoint.sample.notes,
    estimate_sample_missing_reasons: JSON.stringify(endpoint.sample.missing_reasons),
    provenance_missing_reasons: JSON.stringify(endpoint.provenance.missing_reasons),
  };
}

const SOURCE_FIELDS = [
  "source_document", "source_url", "source_version", "source_locator",
  "extraction_date", "review_date", "derivation_notes",
];

const REVIEW_BASES = [null, "local_coding", "primary_source", "analysis_output"];
const STATUSES = ["reviewed", "unreviewed"];
const objectRecord = value => value !== null && typeof value === "object" && !Array.isArray(value);

function validateAnnotation(annotation, id, errors) {
  if (!objectRecord(annotation)) { errors.push(`${id}: annotation must be an object.`); return; }
  for (const part of ["sample", "provenance"]) {
    if (!own(annotation, part)) continue;
    const record = annotation[part];
    if (!objectRecord(record)) { errors.push(`${id}: ${part} must be an object.`); continue; }
    if (own(record, "review_status") && !STATUSES.includes(record.review_status)) errors.push(`${id}: invalid ${part} review_status.`);
    if (own(record, "review_basis") && !REVIEW_BASES.includes(record.review_basis)) errors.push(`${id}: invalid ${part} review_basis.`);
    if (record.review_status === "reviewed" && !record.review_basis) errors.push(`${id}: reviewed ${part} needs a review_basis.`);
    if (own(record, "missing_reasons")) {
      if (!objectRecord(record.missing_reasons) || Object.values(record.missing_reasons).some(value => !nonempty(value))) errors.push(`${id}: ${part}.missing_reasons must contain nonempty explanations.`);
    }
    if (part === "sample") {
      for (const field of ["n", "recruited_n", "randomized_n", "treatment_n", "control_n"]) {
        if (own(record, field) && !validCount(record[field])) errors.push(`${id}: invalid sample.${field}.`);
      }
      if (own(record, "unit") && !SAMPLE_UNITS.includes(record.unit)) errors.push(`${id}: invalid sample unit.`);
      if (record.review_status === "reviewed" && !own(record, "unit")) errors.push(`${id}: reviewed sample needs an explicit unit.`);
      if (own(record, "notes") && record.notes !== null && !nonempty(record.notes)) errors.push(`${id}: sample notes must be nonempty text or null.`);
    } else {
      for (const field of SOURCE_FIELDS) {
        if (own(record, field) && record[field] !== null && !nonempty(record[field])) errors.push(`${id}: invalid provenance.${field}.`);
      }
      for (const field of ["review_date", "extraction_date"]) {
        if (record[field] != null && !isDate(record[field])) errors.push(`${id}: invalid provenance.${field}.`);
      }
      if (record.review_status === "reviewed" && !["primary_source", "analysis_output"].includes(record.review_basis)) errors.push(`${id}: reviewed source cannot rely only on legacy coding.`);
    }
  }
}

// Compare raw release records, not resolver-enriched display records. Unchanged
// legacy rows keep their honest unknowns. A new/changed row needs a documented
// review before publication. Null facts need field-specific explanations.
export function validateMetadataRelease({ papers = [], estimates = [], previousEstimates = [], metadata = {} }) {
  const errors = [];
  const requiredReviewIds = [];
  const paperRows = Array.isArray(papers) ? papers : papers?.papers || [];
  const previous = new Map(previousEstimates.map(e => [evidenceEstimateKey(e), e]));
  const paperKeys = new Set(paperRows.map(p => p.paper_key));
  const estimateMap = new Map(estimates.map(e => [evidenceEstimateKey(e), e]));
  const currentIds = new Set();
  if (metadata.schema_version !== METADATA_SCHEMA_VERSION) errors.push("Unsupported evidence metadata schema_version.");
  for (const [section, known] of [["studies", paperKeys], ["estimates", new Set(estimateMap.keys())]]) {
    if (metadata[section] !== undefined && !objectRecord(metadata[section])) {
      errors.push(`metadata.${section} must be an object.`);
      continue;
    }
    for (const [id, annotation] of Object.entries(metadata[section] || {})) {
      if (!known.has(id)) errors.push(`${id}: metadata refers to an unknown ${section === "studies" ? "paper" : "estimate"} ID.`);
      validateAnnotation(annotation, id, errors);
      if (section === "estimates" && estimateMap.has(id) && own(annotation?.sample, "n")) {
        const rawN = estimateMap.get(id).n_total ?? estimateMap.get(id).n ?? null;
        if (rawN !== null && annotation.sample.n !== rawN) errors.push(`${id}: analyzed sample metadata does not match the raw estimate count.`);
      }
    }
  }

  for (const estimate of estimates) {
    const id = evidenceEstimateKey(estimate);
    if (currentIds.has(id)) errors.push(`${id}: duplicate estimate key.`);
    currentIds.add(id);
    if (!paperKeys.has(estimate.paper_key)) errors.push(`${id}: unknown paper_key.`);
    const old = previous.get(id);
    if (old && JSON.stringify(canonical(old)) === JSON.stringify(canonical(estimate))) continue;
    requiredReviewIds.push(id);
    const annotation = metadata.estimates?.[id];
    if (!annotation) { errors.push(`${id}: new or revised estimate requires metadata.`); continue; }
    const sample = annotation.sample || {};
    for (const field of ["n", "unit", "treatment_n", "control_n", "notes"]) {
      if (!own(sample, field)) errors.push(`${id}: sample.${field} is required.`);
      else if (sample[field] === null && !nonempty(sample.missing_reasons?.[field])) errors.push(`${id}: sample.${field} needs a value or missing reason.`);
    }
    if (!validCount(sample.n) || !validCount(sample.treatment_n) || !validCount(sample.control_n)) errors.push(`${id}: sample counts must be nonnegative integers or null.`);
    const rawN = estimate.n_total ?? estimate.n ?? null;
    if (rawN !== null && sample.n !== rawN) errors.push(`${id}: analyzed sample metadata does not match the raw estimate count.`);
    if (!SAMPLE_UNITS.includes(sample.unit)) errors.push(`${id}: invalid sample unit.`);
    if (sample.unit === "unknown" && !nonempty(sample.missing_reasons?.unit)) errors.push(`${id}: unknown sample unit needs a missing reason.`);
    if (sample.review_status !== "reviewed") errors.push(`${id}: sample definition has not been reviewed.`);
    if (!["primary_source", "analysis_output"].includes(sample.review_basis)) errors.push(`${id}: sample needs a primary-source or analysis-output review.`);

    const provenance = annotation.provenance || {};
    for (const field of SOURCE_FIELDS) {
      if (!own(provenance, field)) errors.push(`${id}: provenance.${field} is required.`);
      else if (!nonempty(provenance[field]) && !nonempty(provenance.missing_reasons?.[field])) errors.push(`${id}: provenance.${field} needs a value or missing reason.`);
    }
    if (!nonempty(provenance.source_document) && !nonempty(provenance.source_url)) errors.push(`${id}: source document or URL is required.`);
    if (provenance.review_status !== "reviewed") errors.push(`${id}: source provenance has not been reviewed.`);
    if (!["primary_source", "analysis_output"].includes(provenance.review_basis)) errors.push(`${id}: source review cannot rely only on legacy coding.`);
    if (!isDate(provenance.review_date)) errors.push(`${id}: review_date must be a valid ISO date.`);
    if (provenance.extraction_date !== null && !isDate(provenance.extraction_date)) errors.push(`${id}: extraction_date must be null or a valid ISO date.`);
    if (!nonempty(provenance.source_locator)) errors.push(`${id}: source_locator must identify the supporting table, page, or analysis output.`);
    if (!nonempty(provenance.derivation_notes)) errors.push(`${id}: derivation_notes must explain the effect/uncertainty extraction (or state no derivation).`);
  }
  return { valid: errors.length === 0, errors, requiredReviewIds };
}
