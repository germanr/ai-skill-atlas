import { readFileSync, readdirSync, mkdirSync, writeFileSync, realpathSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validateMetadataRelease } from "../src/evidence-metadata.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const DEFAULT_PAPERS_DIR = join(ROOT, "code", "creativity", "papers");
export const DEFAULT_OUT_DIR = join(ROOT, "code", "creativity", "build");
export const OUTPUT_FILES = ["creativity_papers.json", "creativity_estimates.json", "creativity_metadata.json"];
const SIGNS = { more_creative: 1, more_diverse: 1, more_ideas: 1, more_accurate: 1, less_creative: -1, more_similar: -1, other: null };
// unstated_rct: randomized, but the paper does not say whether in a supervised session, online, or in ordinary work (2026-10-11).
const RCTS = ["lab_rct", "online_rct", "field_rct", "unstated_rct"];
const CONSTRUCTS = ["overall_creativity", "novelty", "usefulness", "fluency", "flexibility", "elaboration", "convergent", "diversity", "other"];
// null: the paper does not say who or what scored the outcome. length: a word or character count of the output.
const MEASURES = [null, "human_raters", "expert_raters", "embedding_similarity", "lexical_overlap", "category_count", "automated_score", "behavioral", "length", "text_features"];
const TASKS = ["divergent_test", "idea_generation", "creative_writing", "design_visual", "humor", "other"];
const ROLES = ["ideas_supplied", "open_chat", "suggestions", "refinement", "coach", "image_generation", "other"];
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const nonempty = value => typeof value === "string" && value.trim().length > 0;
const finite = Number.isFinite;
const positive = value => finite(value) && value > 0;
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
// A contrast may pool several arms of a study ("A and B (combined)"): the text must say combined or pooled and name
// at least two of the study's arms. Returns the component arm names, or null.
export function combinedArms(study, text) {
  if (typeof text !== "string" || !/\b(combined|pooled)\b/i.test(text)) return null;
  // Longest names first, each match removed from the text, so that "T&AI" is not also read as the arm "T".
  let rest = text;
  const parts = [];
  for (const name of study.arms.map(arm => arm.name).filter(nonempty).sort((a, b) => b.length - a.length)) {
    if (rest.includes(name)) {
      parts.push(name);
      rest = rest.split(name).join("\u0000");
    }
  }
  const order = study.arms.map(arm => arm.name);
  return parts.length >= 2 ? parts.sort((a, b) => order.indexOf(a) - order.indexOf(b)) : null;
}
const unique = values => [...new Set(values)];
const json = value => `${JSON.stringify(value, null, 2)}\n`;
const cleanZero = value => Object.is(value, -0) ? 0 : value;

function fail(file, slug, field, message) {
  throw new Error(`${file}: ${slug || "<paper>"}: ${field}: ${message}`);
}

// A source may cite a whole object ("test") or its individual leaves
// ("test.value", "test.df"). Expansion makes overlapping citations fail too.
function leaves(value, prefix = "", predicate = value => typeof value === "number") {
  if (predicate(value)) return [prefix];
  if (value !== null && typeof value === "object") return Object.entries(value)
    .flatMap(([key, child]) => leaves(child, prefix ? `${prefix}.${key}` : key, predicate));
  return [];
}

function get(object, path) {
  return path.split(".").reduce((value, key) => value != null && Object.hasOwn(value, key) ? value[key] : undefined, object);
}

function sourceField(field) { return field.replace(/^stats\./, ""); }
function covers(field, leaf) { return leaf === field || leaf.startsWith(`${field}.`); }

export function parsePValue(value) {
  if (typeof value === "number") return { operator: "=", value };
  if (typeof value !== "string") return null;
  const match = value.trim().match(/^(<=|>=|<|>|=|≤|≥)?\s*((?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)$/i);
  return match ? { operator: match[1] || "=", value: Number(match[2]) } : null;
}

export function validateSource(source, file = "<source>") {
  let slug = "<paper>";
  const bad = (field, message) => fail(file, slug, field, message);
  const record = (value, field, keys) => {
    if (!object(value)) bad(field, "must be an object");
    for (const key of keys.split(" ").filter(Boolean)) if (!Object.hasOwn(value, key)) bad(`${field}.${key}`, "required key is missing");
  };
  const array = (value, field) => { if (!Array.isArray(value)) bad(field, "must be an array"); };
  const text = (value, field, nullable = false, empty = false) => {
    if (!(nullable && value === null) && !(typeof value === "string" && (empty || nonempty(value)))) bad(field, `must be ${nullable ? "null or " : ""}${empty ? "text" : "nonempty text"}`);
  };
  const boolean = (value, field) => { if (typeof value !== "boolean") bad(field, "must be boolean"); };
  const enumeration = (value, field, choices) => { if (!choices.includes(value)) bad(field, `must be one of ${choices.map(v => JSON.stringify(v)).join(", ")}`); };
  const number = (value, field, nonnegative = false) => {
    if (value !== null && (!finite(value) || (nonnegative && value < 0))) bad(field, `must be a ${nonnegative ? "non-negative " : ""}finite number or null`);
  };
  const count = (value, field) => { if (value !== null && (!Number.isSafeInteger(value) || value < 0)) bad(field, "must be a non-negative safe integer or null"); };
  const date = (value, field) => {
    if (value === null) return;
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) bad(field, "must be an ISO YYYY-MM-DD date or null");
    const parsed = new Date(`${value}T00:00:00Z`);
    if (!finite(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== value) bad(field, "must be a real ISO date");
  };
  const interval = (value, field) => {
    number(value.ci_lower, `${field}.ci_lower`);
    number(value.ci_upper, `${field}.ci_upper`);
    if (finite(value.ci_lower) && finite(value.ci_upper) && value.ci_lower > value.ci_upper) bad(`${field}.ci_lower`, "must not exceed ci_upper");
  };
  record(source, "source", "schema paper_key cid status paper provenance studies estimates not_extracted open_items chain");
  enumeration(source.schema, "schema", [1]);
  text(source.paper_key, "paper_key");
  if (!/^[a-z0-9]+(?:_[a-z0-9]+)*$/.test(source.paper_key)) bad("paper_key", "must use lowercase letters, digits and underscores");
  text(source.cid, "cid");
  enumeration(source.status, "status", ["verified", "draft"]);
  record(source.paper, "paper", "authors_short authors_full year title venue doi url pdf_filename version_read is_own_paper one_line_finding shared_samples");
  for (const field of ["authors_short", "authors_full", "title", "venue", "doi", "url", "pdf_filename", "version_read", "one_line_finding"]) text(source.paper[field], `paper.${field}`, true, true);
  count(source.paper.year, "paper.year");
  boolean(source.paper.is_own_paper, "paper.is_own_paper");
  const shared = source.paper.shared_samples;
  if (Array.isArray(shared)) shared.forEach((value, i) => text(value, `paper.shared_samples.${i}`));
  else text(shared, "paper.shared_samples", true, true);
  record(source.provenance, "provenance", "source_document source_url source_version extraction_date review_date review_basis checked_by statement");
  for (const field of ["source_document", "source_url", "source_version", "checked_by", "statement"]) text(source.provenance[field], `provenance.${field}`, true, true);
  for (const field of ["extraction_date", "review_date"]) date(source.provenance[field], `provenance.${field}`);
  enumeration(source.provenance.review_basis, "provenance.review_basis", ["primary_source", "analysis_output"]);
  record(source.chain, "chain", "");
  for (const field of ["verify_problems", "fixes", "kept", "reverify_problems"]) if (Object.hasOwn(source.chain, field)) count(source.chain[field], `chain.${field}`);
  array(source.not_extracted, "not_extracted");
  source.not_extracted.forEach((value, i) => {
    record(value, `not_extracted.${i}`, "what reason");
    text(value.what, `not_extracted.${i}.what`);
    text(value.reason, `not_extracted.${i}.reason`);
  });
  array(source.open_items, "open_items");
  source.open_items.forEach((value, i) => text(value, `open_items.${i}`));
  array(source.studies, "studies");
  const studies = new Map();
  source.studies.forEach((study, i) => {
    const field = `studies.${i}`;
    record(study, field, "study_id sample_id label design_class assignment_unit clusters_per_arm cluster_se_treatment n_randomized n_analyzed counts_source arms population country task_type task ai_role ai_tool preregistration shared_sample");
    text(study.study_id, `${field}.study_id`);
    if (studies.has(study.study_id)) bad(`${field}.study_id`, "duplicate study id");
    studies.set(study.study_id, study);
    text(study.sample_id, `${field}.sample_id`);
    text(study.label, `${field}.label`);
    enumeration(study.design_class, `${field}.design_class`, RCTS);
    enumeration(study.assignment_unit, `${field}.assignment_unit`, ["individual", "team", "class", "session", "within_person_order"]);
    if (study.clusters_per_arm !== null) {
      record(study.clusters_per_arm, `${field}.clusters_per_arm`, "");
      for (const [arm, value] of Object.entries(study.clusters_per_arm)) count(value, `${field}.clusters_per_arm.${arm}`);
    }
    text(study.cluster_se_treatment, `${field}.cluster_se_treatment`, true, true);
    count(study.n_randomized, `${field}.n_randomized`);
    count(study.n_analyzed, `${field}.n_analyzed`);
    record(study.counts_source, `${field}.counts_source`, "locator quote");
    for (const key of ["locator", "quote"]) text(study.counts_source[key], `${field}.counts_source.${key}`, true, true);
    array(study.arms, `${field}.arms`);
    const armNames = new Set();
    study.arms.forEach((arm, j) => {
      const prefix = `${field}.arms.${j}`;
      record(arm, prefix, "name description ai n_randomized n_analyzed");
      text(arm.name, `${prefix}.name`);
      if (armNames.has(arm.name)) bad(`${prefix}.name`, "duplicate arm name");
      armNames.add(arm.name);
      text(arm.description, `${prefix}.description`, false, true);
      enumeration(arm.ai, `${prefix}.ai`, ["none", "generative_ai", "other_aid"]);
      count(arm.n_randomized, `${prefix}.n_randomized`);
      count(arm.n_analyzed, `${prefix}.n_analyzed`);
    });
    // null: the paper does not say who the participants were (for example a university lab panel of unstated make-up).
    enumeration(study.population, `${field}.population`, [null, "students", "online_panel", "professionals", "general_public", "mixed"]);
    text(study.country, `${field}.country`, true, true);
    enumeration(study.task_type, `${field}.task_type`, TASKS);
    text(study.task, `${field}.task`, false, true);
    enumeration(study.ai_role, `${field}.ai_role`, ROLES);
    record(study.ai_tool, `${field}.ai_tool`, "name year locator");
    text(study.ai_tool.name, `${field}.ai_tool.name`, true, true);
    count(study.ai_tool.year, `${field}.ai_tool.year`);
    text(study.ai_tool.locator, `${field}.ai_tool.locator`, true, true);
    record(study.preregistration, `${field}.preregistration`, "exists where primary_outcome");
    enumeration(study.preregistration.exists, `${field}.preregistration.exists`, ["yes", "no", "not_stated"]);
    for (const key of ["where", "primary_outcome"]) text(study.preregistration[key], `${field}.preregistration.${key}`, true, true);
    text(study.shared_sample, `${field}.shared_sample`, true, true);
  });
  array(source.estimates, "estimates");
  const slugs = new Set();
  for (const estimate of source.estimates) {
    slug = nonempty(estimate?.slug) ? estimate.slug : "<missing slug>";
    record(estimate, "estimate", "slug study_id form_outcome_id outcome question construct measure measure_detail unit n_units outcome_timing delay_days outcome_with_ai comparison_type treatment_arm control_arm within_person n_treatment n_control n_total higher_is stats se_basis preregistered_primary sources notes");
    text(estimate.slug, "slug");
    text(estimate.study_id, "study_id");
    if (!/^[a-z0-9]+(?:_[a-z0-9]+)*$/.test(slug) || !slug.startsWith(`${estimate.study_id.toLowerCase()}_`)) bad("slug", "must be snake_case starting with the lowercased study id and underscore");
    if (slugs.has(slug)) bad("slug", "duplicate slug within paper");
    slugs.add(slug);
    const study = studies.get(estimate.study_id);
    if (!study) bad("study_id", "does not reference a study in this paper");
    text(estimate.form_outcome_id, "form_outcome_id", true, true);
    text(estimate.outcome, "outcome");
    enumeration(estimate.question, "question", ["with_ai", "across_people", "after_ai"]);
    enumeration(estimate.construct, "construct", CONSTRUCTS);
    enumeration(estimate.measure, "measure", MEASURES);
    text(estimate.measure_detail, "measure_detail", false, true);
    // null: the paper does not say at which level the outcome was analyzed.
    enumeration(estimate.unit, "unit", [null, "participant", "team", "output", "rating", "pair", "set"]);
    for (const key of ["n_units", "n_treatment", "n_control", "n_total"]) count(estimate[key], key);
    number(estimate.delay_days, "delay_days", true);
    enumeration(estimate.outcome_timing, "outcome_timing", ["immediate", "delayed"]);
    boolean(estimate.outcome_with_ai, "outcome_with_ai");
    enumeration(estimate.comparison_type, "comparison_type", ["ai_vs_bau", "ai_vs_active", "ai_design"]);
    for (const key of ["treatment_arm", "control_arm"]) {
      text(estimate[key], key);
      if (!study.arms.some(arm => arm.name === estimate[key]) && !combinedArms(study, estimate[key])) bad(key, "does not name an arm in the referenced study, nor a combination of at least two of its arms marked combined or pooled");
    }
    enumeration(estimate.within_person, "within_person", [null, "first_round", "paired"]);
    enumeration(estimate.higher_is, "higher_is", Object.keys(SIGNS));
    // unclear: the paper prints a test or interval, but its unit of analysis cannot be established from the paper.
    enumeration(estimate.se_basis, "se_basis", ["participant", "cluster", "output", "rating", "pair", "set", "not_reported", "unclear"]);
    // "cluster" means standard errors over randomized clusters. Clustering by evaluators or items in an individually
    // randomized study does not count each randomized person once (codebook section 10).
    if (estimate.se_basis === "cluster" && !["team", "class", "session"].includes(study.assignment_unit)) bad("se_basis", `cluster requires a study that randomized clusters (team, class, or session); this study's assignment_unit is ${study.assignment_unit}`);
    enumeration(estimate.preregistered_primary, "preregistered_primary", ["yes", "no", "not_stated"]);
    if (Object.hasOwn(estimate, "primary_override")) boolean(estimate.primary_override, "primary_override");
    // From the screening form's outcome code: the outcome the preregistration or the paper names as primary (codebook
    // section 8, rule 1).
    if (Object.hasOwn(estimate, "named_primary")) enumeration(estimate.named_primary, "named_primary", [null, "preregistered", "paper"]);
    if (["convergent", "other"].includes(estimate.construct) && estimate.primary_override === true) bad("primary_override", `${estimate.construct} outcomes can never be primary`);
    text(estimate.notes, "notes", false, true);
    if (Object.hasOwn(estimate, "data_stats") && estimate.data_stats !== null) {
      // Statistics computed from the authors' posted data by two independent analysts whose results agree and who both
      // reproduced the paper's printed statistics (docs/creativity-screening/tools/codex_analyze.py).
      const d = estimate.data_stats;
      record(d, "data_stats", "round n_treatment n_control treatment_mean treatment_sd control_mean control_sd difference difference_se se_type n_clusters scripts deposit compare_file");
      enumeration(d.round, "data_stats.round", ["all", "first_round"]);
      for (const key of ["n_treatment", "n_control"]) { count(d[key], `data_stats.${key}`); if (!positive(d[key])) bad(`data_stats.${key}`, "must be a positive count"); }
      for (const key of ["treatment_mean", "control_mean", "difference"]) { number(d[key], `data_stats.${key}`); if (!finite(d[key])) bad(`data_stats.${key}`, "is required"); }
      for (const key of ["treatment_sd", "control_sd", "difference_se"]) { number(d[key], `data_stats.${key}`, true); if (!positive(d[key])) bad(`data_stats.${key}`, "must be positive"); }
      enumeration(d.se_type, "data_stats.se_type", ["HC2", "cluster", "paired"]);
      count(d.n_clusters, "data_stats.n_clusters");
      if (d.se_type === "cluster" && !["team", "class", "session"].includes(study.assignment_unit)) bad("data_stats.se_type", "cluster standard errors require a study that randomized clusters");
      if (d.se_type === "paired" && estimate.within_person !== "paired") bad("data_stats.se_type", "paired standard errors belong to a paired within-person estimate");
      if (d.round === "first_round" && estimate.within_person !== "first_round") bad("data_stats.round", "first-round statistics belong to an estimate with within_person first_round");
      array(d.scripts, "data_stats.scripts");
      d.scripts.forEach((value, i) => text(value, `data_stats.scripts.${i}`));
      text(d.deposit, "data_stats.deposit");
      text(d.compare_file, "data_stats.compare_file");
    }
    const stats = estimate.stats;
    record(stats, "stats", "treatment_mean treatment_sd treatment_se control_mean control_sd control_se sd_level difference difference_is difference_se ci_lower ci_upper ci_level ci_of regression test p_value paper_effect");
    for (const key of ["treatment_mean", "control_mean", "difference"]) number(stats[key], `stats.${key}`);
    for (const key of ["treatment_sd", "control_sd", "treatment_se", "control_se", "difference_se"]) number(stats[key], `stats.${key}`, true);
    enumeration(stats.sd_level, "stats.sd_level", [null, "participant", "output", "rating", "pair", "set"]);
    text(stats.difference_is, "stats.difference_is", true, true);
    interval(stats, "stats");
    number(stats.ci_level, "stats.ci_level", true);
    if (stats.ci_level !== null && !(stats.ci_level > 0 && stats.ci_level < 100)) bad("stats.ci_level", "must be a probability or a percentage strictly between 0 and 100");
    enumeration(stats.ci_of, "stats.ci_of", [null, "difference", "paper_effect", "treatment_mean"]);
    if (stats.regression !== null) {
      record(stats.regression, "stats.regression", "coef se se_type outcome_scale model");
      number(stats.regression.coef, "stats.regression.coef");
      number(stats.regression.se, "stats.regression.se", true);
      enumeration(stats.regression.se_type, "stats.regression.se_type", ["robust", "clustered_participant", "clustered_cluster", "conventional", "not_stated"]);
      // null: the paper does not say whether the outcome was standardized; such a coefficient is never converted.
      enumeration(stats.regression.outcome_scale, "stats.regression.outcome_scale", [null, "raw", "standardized"]);
      text(stats.regression.model, "stats.regression.model", false, true);
    }
    if (stats.test !== null) {
      record(stats.test, "stats.test", "type value df");
      enumeration(stats.test.type, "stats.test.type", ["t", "F", "z", "chi2", "U", "W", "H", "other"]);
      number(stats.test.value, "stats.test.value");
      if (Array.isArray(stats.test.df)) stats.test.df.forEach((df, i) => number(df, `stats.test.df.${i}`, true));
      else number(stats.test.df, "stats.test.df", true);
    }
    if (stats.p_value !== null) {
      const p = parsePValue(stats.p_value);
      if (!p || !finite(p.value) || p.value < 0 || p.value > 1) bad("stats.p_value", "must be a probability, a bound such as <0.001, or null");
    }
    if (stats.paper_effect !== null) {
      record(stats.paper_effect, "stats.paper_effect", "type value se ci_lower ci_upper standardizer");
      enumeration(stats.paper_effect.type, "stats.paper_effect.type", ["d", "g", "beta_std", "r", "eta2", "cliffs_delta", "odds_ratio", "other"]);
      number(stats.paper_effect.value, "stats.paper_effect.value");
      number(stats.paper_effect.se, "stats.paper_effect.se", true);
      interval(stats.paper_effect, "stats.paper_effect");
      text(stats.paper_effect.standardizer, "stats.paper_effect.standardizer", true, true);
    }
    array(estimate.sources, "sources");
    const supported = { ...stats, n_treatment: estimate.n_treatment, n_control: estimate.n_control, n_total: estimate.n_total, n_units: estimate.n_units, delay_days: estimate.delay_days };
    const fields = [];
    estimate.sources.forEach((source, i) => {
      record(source, `sources.${i}`, "fields locator quote");
      array(source.fields, `sources.${i}.fields`);
      text(source.locator, `sources.${i}.locator`);
      text(source.quote, `sources.${i}.quote`);
      source.fields.forEach((field, j) => {
        text(field, `sources.${i}.fields.${j}`);
        const normalized = sourceField(field);
        // A source may also cite the passage behind a coding choice (se_basis, unit, higher_is, ...): any key of the
        // estimate is a known field. Only statistics and counts enter the exactly-one-source rule below.
        if (get(supported, normalized) === undefined && !(Object.hasOwn(estimate, normalized) && !["stats", "sources", "slug"].includes(normalized))) bad(`sources.${i}.fields.${j}`, `unknown field ${field}`);
        fields.push(normalized);
      });
    });
    const numericFields = leaves(supported);
    if (typeof stats.p_value === "string") numericFields.push("p_value");
    // The extraction file asks for a source for every statistic and for the three people counts. The confidence level,
    // the count of units, and the delay in days are descriptive; a source is optional for them, but never doubled.
    const optional = new Set(["ci_level", "n_units", "delay_days"]);
    for (const field of numericFields) {
      const matches = fields.filter(candidate => covers(candidate, field)).length;
      if (optional.has(field) ? matches > 1 : matches !== 1) bad(Object.hasOwn(stats, field.split(".")[0]) ? `stats.${field}` : field, `must appear in ${optional.has(field) ? "at most" : "exactly"} one source's fields (found ${matches})`);
    }
  }
  return source;
}

export function readSources(papersDir = DEFAULT_PAPERS_DIR, { strict = false, draftProblems = [] } = {}) {
  let names;
  try { names = readdirSync(papersDir, { withFileTypes: true }).filter(file => file.isFile() && /\.json$/i.test(file.name)).map(file => file.name).sort(compare); }
  catch (error) {
    // The extraction pipeline may not have created the default directory yet.
    // Resolve its existing parent too: Windows may expose this checkout via
    // both C:/Dropbox and C:/Users/<user>/Dropbox junction paths.
    if (error.code === "ENOENT") {
      try {
        const canonical = path => {
          const result = join(realpathSync(dirname(resolve(path))), basename(resolve(path)));
          return process.platform === "win32" ? result.toLowerCase() : result;
        };
        if (canonical(papersDir) === canonical(DEFAULT_PAPERS_DIR)) return [];
      } catch { /* A missing custom parent is an error, not an empty dataset. */ }
    }
    throw error;
  }
  const keys = new Set();
  const entries = names.map(name => {
    const file = join(papersDir, name);
    let source;
    try { source = JSON.parse(readFileSync(file, "utf8")); }
    catch (error) { fail(file, "<paper>", "JSON", error.message); }
    // A draft is never emitted, so an invalid draft is reported and skipped; --strict (the release build) fails on it.
    if (source?.status === "draft" && !strict) {
      try { validateSource(source, file); }
      catch (error) { draftProblems.push(error.message); return null; }
    } else validateSource(source, file);
    if (keys.has(source.paper_key)) fail(file, "<paper>", "paper_key", "duplicate paper key across files");
    keys.add(source.paper_key);
    return { source, file };
  }).filter(Boolean);
  return entries.sort((a, b) => compare(a.source.paper_key, b.source.paper_key));
}

function locations(estimate, fields) {
  return unique(estimate.sources.filter(source => source.fields.some(field => fields.some(leaf => covers(sourceField(field), leaf))))
    .map(source => source.locator)).join("; ");
}
function cited(estimate, fields) { return ` (${locations(estimate, fields) || "no numeric source locator"})`; }

// The extraction keeps printed signs: a difference or coefficient printed as control minus treatment says so in
// difference_is (or, for a coefficient, in the regression model text). delta always runs treatment minus control.
const REVERSED = /control minus treatment/i;
export function reversedPrint(estimate, what) {
  const stats = estimate.stats;
  const texts = what === "coef" ? [stats.regression?.model, stats.difference_is] : [stats.difference_is];
  return texts.some(text => REVERSED.test(String(text || "")));
}
export function deltaOf(estimate) {
  const stats = estimate.stats;
  if (stats.regression?.outcome_scale === "raw" && finite(stats.regression.coef)) {
    if (reversedPrint(estimate, "coef")) return { value: cleanZero(-stats.regression.coef), formula: `-(${stats.regression.coef}) (raw regression coefficient printed as control minus treatment)`, fields: ["regression.coef"] };
    return { value: stats.regression.coef, formula: `${stats.regression.coef} (raw regression coefficient)`, fields: ["regression.coef"] };
  }
  if (finite(stats.difference)) {
    if (reversedPrint(estimate, "difference")) return { value: cleanZero(-stats.difference), formula: `-(${stats.difference}) (printed difference, control minus treatment)`, fields: ["difference"] };
    return { value: stats.difference, formula: `${stats.difference} (printed difference)`, fields: ["difference"] };
  }
  if (finite(stats.treatment_mean) && finite(stats.control_mean)) return { value: stats.treatment_mean - stats.control_mean, formula: `(${stats.treatment_mean} - ${stats.control_mean})`, fields: ["treatment_mean", "control_mean"] };
  return { value: null, formula: "unreported difference", fields: [] };
}

// With schema 1's shared sd_level, rank 2 can be reached when the control SD
// is zero (so rank 1 cannot divide by it) and the pooled SD is positive.
export function pooledSD(estimate) {
  const { treatment_sd: a, control_sd: b } = estimate.stats;
  const { n_treatment: n1, n_control: n0 } = estimate;
  if (!positive(n1) || !positive(n0) || n1 + n0 <= 2 || !finite(a) || a < 0 || !finite(b) || b < 0) return null;
  const value = Math.sqrt(((n1 - 1) * a ** 2 + (n0 - 1) * b ** 2) / (n1 + n0 - 2));
  return positive(value) ? value : null;
}

function paperStandardizer(value) {
  if (!nonempty(value)) return null;
  const description = value.toLowerCase().replace(/[_\u2010-\u2015]/g, " ");
  // Free prose must affirm both the level and denominator. Ambiguous or
  // explicitly unknown standardizers stay raw; no d_z or output SD conversion.
  if (/not (?:stated|reported|specified|identified)|unknown|unclear|output|rating|pair|difference scores?|change scores?/.test(description)) return null;
  if (!/\b(?:participant|person|people|individual|subject|student)s?\b/.test(description) || !/\b(?:sd|standard deviation)\b/.test(description)) return null;
  if (/\bpooled\b/.test(description)) return "paper_pooled_sd";
  if (/\bcontrol\b/.test(description)) return "paper_control_sd";
  return null;
}

function hasDifferenceCI(stats) {
  return stats.ci_of === "difference" && [95, 0.95].includes(stats.ci_level) && finite(stats.ci_lower) && finite(stats.ci_upper);
}

function diversity(estimate, sign, delta) {
  const stats = estimate.stats;
  // A printed coefficient or difference with its standard error also tests the contrast: z = delta / SE.
  const zSE = stats.regression?.outcome_scale === "raw" && finite(stats.regression.coef) && positive(stats.regression.se) ? { value: stats.regression.coef / stats.regression.se, fields: ["regression.coef", "regression.se"] }
    : finite(stats.difference) && positive(stats.difference_se) ? { value: stats.difference / stats.difference_se, fields: ["difference", "difference_se"] } : null;
  const tested = hasDifferenceCI(stats) || stats.p_value !== null || zSE !== null;
  const p = parsePValue(stats.p_value);
  const significantP = p && ((p.operator === "<" && p.value <= 0.05) || (["=", "<=", "≤"].includes(p.operator) && p.value < 0.05));
  const clear = (hasDifferenceCI(stats) && (stats.ci_lower > 0 || stats.ci_upper < 0)) || significantP || (zSE !== null && Math.abs(zSE.value) >= 1.96);
  const oriented = sign !== null && finite(delta.value) ? sign * delta.value : null;
  const direction = !tested ? "not_tested" : oriented === null ? null : oriented === 0 ? "no_clear_difference"
    : `${oriented > 0 ? "less_alike" : "more_alike"} ${clear ? "clear" : "no_clear_difference"}`;
  const notes = ["No standardized effect or SE is computed: diversity outcomes retain the paper's own units (Review 1 Decision 3)."];
  if (oriented !== null) notes.push(`Direction uses s * delta = ${sign} * ${delta.formula}${cited(estimate, delta.fields)} = ${cleanZero(oriented)}.`);
  else notes.push("Direction cannot be signed because higher_is is other or the contrast is unreported.");
  if (hasDifferenceCI(stats)) notes.push(`Printed ${stats.ci_level} confidence interval of the difference [${stats.ci_lower}, ${stats.ci_upper}]${cited(estimate, ["ci_lower", "ci_upper", "ci_level"])} ${stats.ci_lower > 0 || stats.ci_upper < 0 ? "excludes" : "includes"} zero.`);
  if (stats.p_value !== null) notes.push(`Printed p = ${stats.p_value}${cited(estimate, ["p_value"])} ${significantP ? "establishes p < 0.05" : "does not establish p < 0.05"}.`);
  if (zSE !== null) notes.push(`z = ${cleanZero(zSE.value)} from the printed estimate and its standard error${cited(estimate, zSE.fields)}; |z| ${Math.abs(zSE.value) >= 1.96 ? ">=" : "<"} 1.96.`);
  if (!tested) notes.push("No printed 95 percent interval of the difference, p-value, or estimate with its standard error is available; direction is not_tested.");
  return { effect_size_sd: null, se: null, ci_lower: null, ci_upper: null, standardizer: null, direction, derivation_notes: notes.join(" ") };
}

export function computeEstimate(estimate) {
  const printed = computePrinted(estimate);
  const base = { ...printed, se_basis_used: estimate.se_basis, review_basis: null, counts: null, data_source: null };
  const d = estimate.data_stats;
  if (!d || estimate.construct === "diversity") return base;
  const printedOK = finite(printed.effect_size_sd) && positive(printed.se) && ["participant", "cluster"].includes(estimate.se_basis) && printed.standardizer !== "output_level_sd";
  if (printedOK) return { ...base, derivation_notes: `${printed.derivation_notes} Statistics computed from the posted data exist for this estimate but are not used: the printed statistics give a participant-level effect.` };
  const sign = SIGNS[estimate.higher_is];
  // A record derived from posted data alone (a first-round record) has no printed source, so it keeps the posted-data locator.
  const unusedSource = estimate.sources.length ? null : `posted data ${d.deposit}; ${d.compare_file}`;
  if (sign === null) return { ...base, data_source: unusedSource, derivation_notes: `${printed.derivation_notes} Statistics computed from the posted data are not used because higher_is is other.` };
  const effect = cleanZero(sign * d.difference / d.control_sd);
  const se = d.difference_se / d.control_sd;
  const lower = effect - 1.96 * se, upper = effect + 1.96 * se;
  if (![effect, se, lower, upper].every(finite)) throw new Error(`${estimate.slug}: posted-data calculation is non-finite`);
  const paired = estimate.within_person === "paired";
  const seText = d.se_type === "cluster" ? `clustered by ${d.n_clusters ?? "an unreported number of"} randomized clusters` : d.se_type === "paired" ? "the standard error of the mean within-person difference" : "HC2 robust, one row per person";
  const notes = [
    `Printed statistics: ${printed.derivation_notes} They give no participant-level effect that can be pooled.`,
    `From the authors' posted data (${d.deposit}), two analysts computed the statistics independently; both reproduced the paper's printed numbers, and their results agree (${d.compare_file}; scripts ${d.scripts.join(", ")}).`,
    `${d.round === "first_round" ? "First round only: each person's first condition. " : ""}Participant-level means ${d.treatment_mean} (treatment, n = ${d.n_treatment}) and ${d.control_mean} (control, n = ${d.n_control}); control SD ${d.control_sd}.`,
    `d = ${sign} * ${d.difference} / ${d.control_sd} = ${effect}; SE = ${d.difference_se} (${seText}) / ${d.control_sd} = ${se}; 95 percent CI = [${lower}, ${upper}].`,
  ];
  return {
    effect_size_sd: effect, se, ci_lower: lower, ci_upper: upper, standardizer: "control_sd", direction: null,
    derivation_notes: notes.join(" "), se_basis_used: d.se_type === "cluster" ? "cluster" : "participant", review_basis: "analysis_output",
    counts: { n_treatment: d.n_treatment, n_control: d.n_control, n_total: paired ? d.n_treatment : d.n_treatment + d.n_control },
    data_source: `posted data ${d.deposit}; ${d.compare_file}`,
  };
}

export function computePrinted(estimate) {
  const stats = estimate.stats;
  const sign = SIGNS[estimate.higher_is];
  const delta = deltaOf(estimate);
  if (estimate.construct === "diversity") return diversity(estimate, sign, delta);
  const notes = [`s = ${sign === null ? "undefined" : sign} from higher_is = ${estimate.higher_is}.`];
  let effect = null, denominator = null, standardizer = null;
  let denominatorFields = [];
  const fromSD = (sd, name, pooled = false) => {
    denominator = sd;
    standardizer = name;
    denominatorFields = pooled ? ["treatment_sd", "control_sd", "n_treatment", "n_control"] : ["control_sd"];
    if (pooled) notes.push(`SD_pooled = sqrt(((${estimate.n_treatment} - 1) * ${stats.treatment_sd}^2 + (${estimate.n_control} - 1) * ${stats.control_sd}^2) / (${estimate.n_treatment} + ${estimate.n_control} - 2))${cited(estimate, denominatorFields)} = ${sd}.`);
    effect = sign * delta.value / sd;
    notes.push(`d = ${sign} * ${delta.formula} / ${sd} (${pooled ? "pooled-arm" : "control-arm"} SD, ${stats.sd_level} level)${cited(estimate, [...delta.fields, ...denominatorFields])} = ${cleanZero(effect)}.`);
  };
  if (sign !== null) {
    const pooled = pooledSD(estimate);
    if (finite(delta.value) && stats.sd_level === "participant" && positive(stats.control_sd)) fromSD(stats.control_sd, "control_sd");
    else if (finite(delta.value) && stats.sd_level === "participant" && positive(pooled)) fromSD(pooled, "pooled_sd", true);
    else {
      const paper = stats.paper_effect;
      const named = paperStandardizer(paper?.standardizer);
      if (paper && ["d", "g"].includes(paper.type) && finite(paper.value) && named) {
        const candidate = sign * paper.value;
        // A printed d or g runs in the outcome's raw direction (treatment minus control), like delta, so its sign must
        // match delta's. An unsigned or oppositely oriented paper effect is not used. When the signs match,
        // s * paper effect has the sign of s * delta, as every computed effect must.
        const printedDisagrees = finite(delta.value) && Math.sign(paper.value) !== Math.sign(delta.value);
        if (printedDisagrees) {
          notes.push(`Paper ${paper.type} = ${paper.value}${cited(estimate, ["paper_effect.value"])} is not used: its printed sign disagrees with the sign of delta = ${delta.formula}${cited(estimate, delta.fields)} = ${delta.value}.`);
        } else {
          effect = candidate;
          standardizer = named;
          if (stats.sd_level === "participant") {
            if (named === "paper_control_sd" && positive(stats.control_sd)) {
              denominator = stats.control_sd;
              denominatorFields = ["control_sd"];
            } else if (named === "paper_pooled_sd" && positive(pooled)) {
              denominator = pooled;
              denominatorFields = ["treatment_sd", "control_sd", "n_treatment", "n_control"];
              notes.push(`SD_pooled = sqrt(((${estimate.n_treatment} - 1) * ${stats.treatment_sd}^2 + (${estimate.n_control} - 1) * ${stats.control_sd}^2) / (${estimate.n_treatment} + ${estimate.n_control} - 2))${cited(estimate, denominatorFields)} = ${pooled}.`);
            }
          }
          notes.push(`d = ${sign} * printed ${paper.type} ${paper.value}${cited(estimate, ["paper_effect.value"])} = ${cleanZero(effect)}; paper standardizer: ${paper.standardizer}. ${denominator === null ? "Its numeric SD is not reported; raw-unit SEs cannot be divided by an inferred SD." : `Its numeric SD = ${denominator}${cited(estimate, denominatorFields)} is available for the SE rules.`}`);
        }
      } else if (paper && finite(paper.value)) notes.push(`Paper ${paper.type} = ${paper.value}${cited(estimate, ["paper_effect.value"])} is not used: it is not d or g with an explicitly named control or pooled participant-level SD.`);
      if (effect === null && stats.regression?.outcome_scale === "standardized" && finite(stats.regression.coef)) {
        effect = sign * stats.regression.coef;
        standardizer = "standardized_outcome";
        denominator = 1;
        notes.push(`d = ${sign} * ${stats.regression.coef}${cited(estimate, ["regression.coef"])} = ${cleanZero(effect)} (regression outcome already standardized; SD = 1).`);
      }
      if (effect === null && finite(delta.value) && ["output", "rating"].includes(stats.sd_level)) {
        if (positive(stats.control_sd)) fromSD(stats.control_sd, "output_level_sd");
        else if (positive(pooled)) fromSD(pooled, "output_level_sd", true);
      }
    }
  }
  let se = null;
  if (finite(effect)) {
    const between = estimate.within_person !== "paired";
    // For rank 4, coefficients and their SEs are already in SD units. Rank 3
    // may lack a numeric SD: never add a paper-effect-SE rule to (a)-(e).
    if (positive(denominator)) {
      const finishSE = (rawSE, formula, fields, rule) => {
        se = rawSE / denominator;
        notes.push(`SE = ${formula} / ${denominator}${cited(estimate, [...fields, ...denominatorFields])} = ${se} (rule ${rule}).`);
      };
      const scaleMatches = stats.regression?.outcome_scale === (standardizer === "standardized_outcome" ? "standardized" : "raw");
      if (scaleMatches && finite(stats.regression.coef) && finite(stats.regression.se)) finishSE(stats.regression.se, `${stats.regression.se} (regression SE)`, ["regression.se"], "a");
      else if (finite(stats.difference_se)) finishSE(stats.difference_se, `${stats.difference_se} (difference SE)`, ["difference_se"], "b");
      else if (hasDifferenceCI(stats)) finishSE((stats.ci_upper - stats.ci_lower) / 3.92, `(${stats.ci_upper} - ${stats.ci_lower}) / 3.92 from the printed 95 percent interval of the difference`, ["ci_upper", "ci_lower", "ci_level"], "c");
      // Rule d serves between-person and paired contrasts alike: a two-group or paired t is delta over its SE.
      else if (stats.regression === null && stats.test?.type === "t" && finite(delta.value) && positive(Math.abs(stats.test.value))) finishSE(Math.abs(delta.value) / Math.abs(stats.test.value), `abs(${delta.value}) / abs(${stats.test.value}) from ${between ? "a two-group" : "a paired"} t`, [...delta.fields, "test.value"], "d");
    }
    if (se === null && between && positive(estimate.n_treatment) && positive(estimate.n_control)) {
      const n1 = estimate.n_treatment, n0 = estimate.n_control;
      se = Math.sqrt((n1 + n0) / (n1 * n0) + effect ** 2 / (2 * (n1 + n0)));
      notes.push(`SE = sqrt((${n1} + ${n0}) / (${n1} * ${n0}) + ${effect}^2 / (2 * (${n1} + ${n0})))${cited(estimate, ["n_treatment", "n_control"])} = ${se} (rule e; between-person counts).`);
    }
    if (se === null) notes.push(`No SE is computed: no usable rule a-d${between ? ", and no usable between-person counts for rule e" : "; paired within-person contrasts cannot use rule e"}. Paper-effect SEs and intervals are retained raw; they are not extra SE rules.`);
    if (stats.test?.type === "F") notes.push("The printed F statistic is not converted.");
    if (stats.regression !== null && stats.test?.type === "t") notes.push("Rule d is unavailable because a regression is reported.");
  } else {
    notes.push(sign === null ? "No effect is computed because higher_is is other." : "No effect is computed: no usable difference and participant/output SD, admissible paper d or g, or standardized regression coefficient.");
  }
  if (effect !== null && !finite(effect)) throw new Error(`${estimate.slug}: effect_size_sd: calculation is non-finite`);
  if (se !== null && !finite(se)) throw new Error(`${estimate.slug}: se: calculation is non-finite`);
  const lower = effect !== null && se !== null ? effect - 1.96 * se : null;
  const upper = effect !== null && se !== null ? effect + 1.96 * se : null;
  if ((lower !== null && !finite(lower)) || (upper !== null && !finite(upper))) throw new Error(`${estimate.slug}: ci_lower/ci_upper: calculation is non-finite`);
  if (se !== null) notes.push(`95 percent CI = ${effect} +/- 1.96 * ${se} = [${lower}, ${upper}].`);
  return { effect_size_sd: effect === null ? null : cleanZero(effect), se, ci_lower: lower, ci_upper: upper, standardizer, direction: null, derivation_notes: notes.join(" ") };
}

export function poolKey(row) { return JSON.stringify([row.sample_id, row.question, row.comparison_type]); }

// Outcomes below overall creativity and novelty, in the order the primary record prefers them (codebook section 8).
const LATER_OUTCOMES = ["usefulness", "flexibility", "fluency", "elaboration"];

function selectPrimaries(contexts) {
  // Every problem is collected, so that one build lists all the pool keys that need a decision.
  const problems = [];
  const ties = [];
  const groups = new Map();
  for (const context of contexts) {
    const key = poolKey(context.row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(context);
  }
  for (const [key, group] of groups) {
    const never = estimate => ["convergent", "other"].includes(estimate.construct);
    let candidates = group.filter(({ estimate }) => !never(estimate) && estimate.primary_override !== false);
    if (group.every(({ estimate }) => never(estimate))) continue;
    const overrides = candidates.filter(({ estimate }) => estimate.primary_override === true);
    const error = (message, candidatesTied = []) => {
      problems.push(`${group[0].file}: ${group[0].estimate.slug}: primary_override: ${message} for pool key ${key}`);
      ties.push({ file: group[0].file, paper_key: group[0].row.paper_key, pool_key: JSON.parse(key), problem: message.split(" (")[0],
        candidates: candidatesTied.map(c => c.row.estimate_id) });
    };
    if (overrides.length > 1) { error(`multiple true overrides (${overrides.map(c => c.row.estimate_id).join(", ")})`); continue; }
    if (overrides.length === 1) { overrides[0].row.is_primary = true; continue; }
    if (!candidates.length) { error("no eligible primary record; all non-convergent records are overridden false"); continue; }
    // Review 1 Decision 11: in a within-person design, first-round results whenever the paper or its posted data give them.
    // The paired contrast and later rounds (whose comparison arm had already used AI) then stay on the study page.
    if (candidates.some(({ estimate }) => estimate.within_person === "first_round")) candidates = candidates.filter(({ estimate }) => estimate.within_person === "first_round");
    // Only a record with a numeric contrast (printed, or computed from posted data) can be primary, when one exists.
    // This depends on whether a number exists, never on its size or sign.
    const quantitative = candidates.filter(({ estimate: e }) => finite(deltaOf(e).value) || finite(e.stats.paper_effect?.value)
      || finite(e.stats.regression?.coef) || finite(e.stats.test?.value) || (e.data_stats && finite(e.data_stats.difference)));
    if (quantitative.length) candidates = quantitative;
    const rank = ({ estimate: e, study, row }) => {
      const people = ["human_raters", "expert_raters"].includes(e.measure);
      // Rule 2: overall creativity rated by people, novelty rated by people, then an automated creativity score (an
      // automated score of overall creativity or novelty, not of other qualities). Extended during Phase 2 (2026-10-11,
      // for review): then overall creativity or novelty scored any other way, usefulness, flexibility, fluency,
      // elaboration, and last a diversity outcome (an embedding-similarity measure first).
      const outcome = e.question === "across_people" ? (e.measure === "embedding_similarity" ? 0 : 1)
        : e.construct === "overall_creativity" && people ? 0 : e.construct === "novelty" && people ? 1
          : e.measure === "automated_score" && ["overall_creativity", "novelty"].includes(e.construct) ? 2
            : ["overall_creativity", "novelty"].includes(e.construct) ? 3
              : LATER_OUTCOMES.includes(e.construct) ? 4 + LATER_OUTCOMES.indexOf(e.construct)
                // A diversity outcome after AI (after_ai) prefers the semantic-similarity measure, as across_people does.
                : e.construct === "diversity" && e.measure === "embedding_similarity" ? 8 : 9;
      // A contrast of combined AI arms counts as free chatbot use when every component arm does; otherwise a combined
      // contrast could never win when all AI arms allow free use (rule 3).
      const armTexts = (combinedArms(study, e.treatment_arm) || [e.treatment_arm]).map(name => {
        const arm = study.arms.find(arm => arm.name === name);
        return arm ? `${arm.name} ${arm.description}` : name;
      });
      const freeChat = study.ai_role === "open_chat" && armTexts.every(text => /\b(unrestricted|free use|freely|open chat|general chatbot)\b/i.test(text));
      // Codebook section 8, rule 3 extended (2026-10-09): after the arm closest to free chatbot use, the paper's own
      // contrast of all its AI arms combined against the shared control.
      const combined = combinedArms(study, e.treatment_arm) ? 0 : 1;
      const named = e.preregistered_primary === "yes" || ["preregistered", "paper"].includes(e.named_primary);
      // Rule 4: when participants are shared across papers, the paper that owns the sample (its key starts the sample_id)
      // supplies the primary record; a reanalysis supplies it only for a question the owner does not report.
      const owner = row.sample_id.startsWith(`${row.paper_key}__`) ? 0 : 1;
      return [owner, named ? 0 : 1, outcome, freeChat ? 0 : 1, combined];
    };
    const compareRanks = (a, b) => { const x = rank(a), y = rank(b); return x.reduce((acc, v, i) => acc || v - y[i], 0); };
    candidates.sort(compareRanks);
    if (candidates.length > 1 && compareRanks(candidates[0], candidates[1]) === 0) {
      const tied = candidates.filter(c => compareRanks(c, candidates[0]) === 0);
      error(`unresolved primary tie (${tied.map(c => c.row.estimate_id).join(", ")}); set primary_override`, tied);
      continue;
    }
    candidates[0].row.is_primary = true;
  }
  if (problems.length) {
    const error = new Error(`${problems.length} pool key(s) need a primary decision:\n${problems.join("\n")}`);
    error.ties = ties;
    throw error;
  }
}

function sumCounts(studies, field) {
  if (studies.some(study => study[field] === null)) return null;
  const sum = studies.reduce((total, study) => total + study[field], 0);
  if (!Number.isSafeInteger(sum)) throw new Error(`${field}: sum exceeds the safe integer range`);
  return sum;
}
function withMissing(record, reasons = {}) {
  return { ...record, missing_reasons: Object.fromEntries(Object.entries(record).filter(([, value]) => value === null)
    .map(([key]) => [key, reasons[key] || "Not reported in the source file; no value was inferred."])) };
}
const nullableText = text => nonempty(text) ? text : null;

function provenance(source, locator, notes, reviewBasis = null) {
  const p = source.provenance;
  return withMissing({
    source_document: nullableText(p.source_document), source_url: nullableText(p.source_url), source_version: nullableText(p.source_version),
    source_locator: nullableText(locator), extraction_date: p.extraction_date, review_date: p.review_date,
    derivation_notes: notes, review_status: "reviewed", review_basis: reviewBasis || p.review_basis,
    checked_by: nullableText(p.checked_by), statement: nullableText(p.statement),
  });
}

export function buildCreativity({ papersDir = DEFAULT_PAPERS_DIR, includeDrafts = false, strict = false } = {}) {
  const draftProblems = [];
  const entries = readSources(papersDir, { strict, draftProblems });
  const papers = [], estimates = [], contexts = [];
  const metadata = { schema_version: 1, scope_note: "Creativity Phase 2 annotations from the extraction chain. Review status describes source-file checks; it does not assert human verification. Each annotation preserves the source's review basis and provenance statement.", studies: {}, estimates: {} };
  for (const { source, file } of entries) {
    if (source.status !== "verified" && !includeDrafts) continue;
    const p = source.paper;
    const studies = source.studies.filter(study => RCTS.includes(study.design_class));
    const n = sumCounts(studies, "n_analyzed");
    const paper = {
      paper_key: source.paper_key, authors_short: p.authors_short, authors_full: p.authors_full, year: p.year, title: p.title,
      venue: p.venue, doi: p.doi, url: p.url, pdf_filename: p.pdf_filename, is_own_paper: p.is_own_paper,
      one_line_finding: p.one_line_finding, design_classes: unique(studies.map(study => study.design_class)),
      questions_answered: unique(source.estimates.map(estimate => estimate.question)), n_total: n, n_estimates: source.estimates.length,
    };
    papers.push(paper);
    const countsNote = `Paper n_total = sum of people analyzed in randomized studies: ${studies.map(study => `${study.study_id}: ${study.n_analyzed ?? "not reported"} (${study.counts_source.locator || "locator not reported"})`).join(" + ") || "no studies"} = ${n ?? "null (at least one study count is unreported)"}. Each study's within-person sample is counted once, without summing its arm counts.`;
    metadata.studies[source.paper_key] = {
      sample: withMissing({ n, unit: "participants", treatment_n: null, control_n: null, recruited_n: null, randomized_n: sumCounts(studies, "n_randomized"), notes: countsNote, review_status: "reviewed", review_basis: source.provenance.review_basis }, { treatment_n: "Paper totals span study-specific contrasts; no single treatment-arm count is inferred.", control_n: "Paper totals span study-specific contrasts; no single control-arm count is inferred." }),
      provenance: provenance(source, unique(studies.map(study => study.counts_source.locator).filter(nonempty)).join("; "), countsNote),
    };
    for (const estimate of source.estimates) {
      const study = studies.find(study => study.study_id === estimate.study_id);
      let derived;
      try { derived = computeEstimate(estimate); }
      catch (error) { fail(file, estimate.slug, "calculation", error.message); }
      const reasons = [];
      if (estimate.construct === "diversity") reasons.push("diversity outcomes are never standardized or pooled");
      if (estimate.construct === "convergent") reasons.push("convergent outcomes are never pooled");
      if (estimate.construct === "other") reasons.push("outcomes outside the creativity constructs (construct other) are never pooled");
      if (!finite(derived.effect_size_sd)) reasons.push("no finite standardized effect");
      if (!positive(derived.se)) reasons.push("no finite positive standard error");
      const seBasis = derived.se_basis_used;
      const counts = derived.counts || { n_treatment: estimate.n_treatment, n_control: estimate.n_control, n_total: estimate.n_total };
      if (!["participant", "cluster"].includes(seBasis)) reasons.push(`se_basis is ${seBasis}; participant or cluster required`);
      if (derived.standardizer === "output_level_sd") reasons.push("output-level or rating-level SD");
      if (["team", "class", "session"].includes(study.assignment_unit) && seBasis !== "cluster") reasons.push("cluster randomization requires cluster-level standard errors");
      const row = {
        estimate_id: `${source.paper_key}__${estimate.slug}`, paper_key: source.paper_key, study_label: study.label,
        effect_size_sd: derived.effect_size_sd, se: derived.se, ci_lower: derived.ci_lower, ci_upper: derived.ci_upper,
        outcome: estimate.outcome, outcome_timing: estimate.outcome_timing, n_treatment: counts.n_treatment, n_control: counts.n_control, n_total: counts.n_total,
        treatment: estimate.treatment_arm, control: estimate.control_arm,
        treatment_arms_combined: combinedArms(study, estimate.treatment_arm), control_arms_combined: combinedArms(study, estimate.control_arm),
        notes: estimate.notes, is_own_paper: p.is_own_paper,
        comparison_type: estimate.comparison_type, outcome_with_ai: estimate.outcome_with_ai, is_subgroup: false, design_class: study.design_class,
        question: estimate.question, construct: estimate.construct, measure: estimate.measure, unit: estimate.unit, n_units: estimate.n_units,
        task_type: study.task_type, ai_role: study.ai_role, ai_tool: study.ai_tool, sample_id: study.sample_id, is_primary: false,
        pooled: false, eligible: reasons.length === 0, not_pooled_reason: reasons.length ? reasons.join("; ") : null,
        se_basis: seBasis, within_person: estimate.within_person, standardizer: derived.standardizer,
        computed_from_posted_data: derived.review_basis === "analysis_output",
        higher_is: estimate.higher_is, raw: estimate.stats, direction: derived.direction, derivation_notes: derived.derivation_notes,
      };
      estimates.push(row);
      contexts.push({ row, estimate, study, file });
      metadata.estimates[row.estimate_id] = {
        sample: withMissing({ n: counts.n_total, unit: "participants", treatment_n: counts.n_treatment, control_n: counts.n_control,
          notes: `${derived.counts ? "Counts are the people in the authors' posted data used for this contrast." : "Counts are the printed people analyzed for this contrast."} ${estimate.within_person === "paired" ? "Paired n_total counts each person once; the arm counts describe the same people." : estimate.within_person === "first_round" ? "Arm counts refer to participants in their first assigned condition." : "Counts are not inferred from study-wide totals or degrees of freedom."}${estimate.notes ? ` ${estimate.notes}` : ""}`,
          review_status: "reviewed", review_basis: derived.review_basis || source.provenance.review_basis }),
        provenance: provenance(source, [estimate.sources.map(source => source.locator).join("; "), derived.data_source].filter(nonempty).join("; "), derived.derivation_notes, derived.review_basis),
      };
    }
  }
  selectPrimaries(contexts);
  // One record per pool key enters a pooled estimate: the primary record, when it is eligible (codebook section 8).
  for (const { row } of contexts) {
    row.pooled = row.eligible && row.is_primary;
    if (row.eligible && !row.is_primary) row.not_pooled_reason = "eligible, but not the primary record of its pool key";
    else if (!row.eligible && row.is_primary) row.not_pooled_reason = `primary record, not eligible: ${row.not_pooled_reason}`;
  }
  const validation = validateMetadataRelease({ papers, estimates, previousEstimates: [], metadata });
  if (!validation.valid) throw new Error(`Metadata release validation failed:\n${validation.errors.map(error => {
    const context = contexts.find(context => error.startsWith(`${context.row.estimate_id}:`));
    return context ? `${context.file}: ${context.estimate.slug}: ${error}` : error;
  }).join("\n")}`);
  return { papers, estimates, metadata, sources: entries, draftProblems, files: Object.fromEntries(OUTPUT_FILES.map((name, i) => [name, json([papers, estimates, metadata][i])])) };
}

export function writeBuild(build, outDir = DEFAULT_OUT_DIR, check = false) {
  if (check) {
    const differences = [];
    for (const [name, expected] of Object.entries(build.files)) {
      let actual;
      try { actual = readFileSync(join(outDir, name), "utf8"); }
      catch (error) { if (error.code !== "ENOENT") throw error; differences.push(`${name}: missing`); continue; }
      if (actual !== expected) {
        const a = actual.split("\n"), b = expected.split("\n");
        const line = b.findIndex((value, i) => a[i] !== value);
        differences.push(`${name}: differs at line ${line < 0 ? b.length + 1 : line + 1} (disk ${Buffer.byteLength(actual)} bytes; rebuilt ${Buffer.byteLength(expected)} bytes)`);
      }
    }
    if (differences.length) throw new Error(`Creativity outputs differ:\n${differences.join("\n")}`);
  } else {
    mkdirSync(outDir, { recursive: true });
    for (const [name, content] of Object.entries(build.files)) writeFileSync(join(outDir, name), content, "utf8");
  }
}

function main(args) {
  const options = {};
  let outDir = DEFAULT_OUT_DIR, check = false;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--check") check = true;
    else if (arg === "--include-drafts") options.includeDrafts = true;
    else if (arg === "--strict") options.strict = true;
    else if (arg === "--report-ties") {
      const value = args[++i];
      if (!value || value.startsWith("--")) throw new Error(`${arg} requires a file`);
      options.reportTies = resolve(value);
    }
    else if (arg === "--papers-dir" || arg === "--out") {
      const value = args[++i];
      if (!value || value.startsWith("--")) throw new Error(`${arg} requires a directory`);
      if (arg === "--papers-dir") options.papersDir = resolve(value);
      else outDir = resolve(value);
    } else throw new Error(`Unknown argument: ${arg}`);
  }
  let build;
  try { build = buildCreativity(options); }
  catch (error) {
    // --report-ties writes the open primary decisions as JSON (an empty list when there are none) before failing.
    if (options.reportTies) writeFileSync(options.reportTies, json(error.ties || []), "utf8");
    throw error;
  }
  if (options.reportTies) writeFileSync(options.reportTies, json([]), "utf8");
  writeBuild(build, outDir, check);
  const drafts = build.sources.filter(({ source }) => source.status === "draft").length;
  for (const problem of build.draftProblems) console.warn(`Draft not valid (skipped): ${problem}`);
  console.log(`Creativity ${check ? "check" : "build"} passed (${build.papers.length} papers, ${build.estimates.length} estimates; ${drafts} drafts validated${options.includeDrafts ? " and included" : " and excluded"}${build.draftProblems.length ? `; ${build.draftProblems.length} invalid drafts skipped` : ""}).`);
}

if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
