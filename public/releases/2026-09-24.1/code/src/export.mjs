// Deterministic CSV serialization shared by browser downloads and release snapshots.
import { ciOf } from "./shared.mjs";
import { flattenEstimateMetadata, CSV_METADATA_COLUMNS } from "./evidence-metadata.mjs";

export const ESTIMATE_CSV_COLUMNS = [
  "estimate_id", "paper_key", "authors", "year", "study_label", "effect_size_sd", "se",
  "ci_lower", "ci_upper", "n_treatment", "n_control", "n_total", "learning_domain", "outcome",
  "outcome_timing", "treatment", "control", "comparison_type", "estimand", "estimation_method",
  "outcome_with_ai", "is_subgroup", "subgroup", "coding_notes", "design_class",
  "included_in_curated_subset", "notes", "country", "population_category", "lab_vs_field",
  "study_design", "ai_tool", "ai_design", "incentives", "venue",
];

export const EXPORT_CONTEXT_COLUMNS = ["release_id", "release_date", "view_url", "selection"];

export function escapeCSV(value) {
  if (value == null) return "";
  const text = typeof value === "object" ? JSON.stringify(value) : String(value);
  return /[",\n\r]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
}

export function buildRecordsCSV(records, columns = [...new Set(records.flatMap(Object.keys))]) {
  return [columns.map(escapeCSV).join(","), ...records.map(record =>
    columns.map(column => escapeCSV(record[column])).join(","))].join("\n");
}

export function buildEstimatesCSV(estimates, papers, {
  releaseId = "", releaseDate = "", viewUrl = "", selection = null, metadata,
} = {}) {
  const paperByKey = new Map(papers.map(paper => [paper.paper_key, paper]));
  const paperColumns = ["country", "population_category", "lab_vs_field", "study_design",
    "ai_tool", "ai_design", "incentives", "venue"];
  const records = estimates.map(estimate => {
    const paper = paperByKey.get(estimate.paper_key) || {};
    const { lo, hi } = ciOf(estimate);
    return {
      ...estimate,
      ...Object.fromEntries(paperColumns.map(column => [column, paper[column]])),
      authors: paper.authors_full || paper.authors_short || "",
      year: paper.year,
      ci_lower: lo,
      ci_upper: hi,
      ...(metadata ? flattenEstimateMetadata(estimate, paper, metadata) : {}),
      release_id: releaseId,
      release_date: releaseDate,
      view_url: viewUrl,
      selection,
    };
  });
  return buildRecordsCSV(records, [...ESTIMATE_CSV_COLUMNS,
    ...CSV_METADATA_COLUMNS, ...EXPORT_CONTEXT_COLUMNS]);
}
