// URL state only. This module has no React, DOM, or data-file dependencies.
// Pass the complete allowed domain, population, and paper-key lists in options.
const SCALARS = Object.freeze({
  designMode: { key: "design", values: ["rct", "lab", "field", "online", "obs"], fallback: "rct" },
  sampleMode: { key: "sample", values: ["students", "nonstudents", "all"], fallback: "students" },
  comparisonType: { key: "comparison", values: ["ai_vs_bau", "ai_vs_active", "ai_design"], fallback: "ai_vs_bau" },
  outcomeMode: { key: "outcome", values: ["without_ai", "all"], fallback: "without_ai" },
  timingMode: { key: "timing", values: ["all", "immediate", "delayed"], fallback: "all" },
  sortBy: { key: "sort", values: ["effect", "year", "author"], fallback: "effect" },
  view: { key: "view", values: ["chart", "table"], fallback: "chart" },
  plotSort: { key: "plotSort", values: ["effect", "precision", "year"], fallback: "effect" },
  section: { key: "section", values: ["learning", "creativity"], fallback: "learning" },
});
const LISTS = Object.freeze({ activeDomains: "domain", activePopulations: "population" });
const KNOWN_KEYS = [...Object.values(SCALARS).map(item => item.key), ...Object.values(LISTS), "q", "paper"];
const has = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

export const VIEW_DEFAULTS = Object.freeze({
  ...Object.fromEntries(Object.entries(SCALARS).map(([field, config]) => [field, config.fallback])),
  activeDomains: Object.freeze([]), activePopulations: Object.freeze([]), search: "", paperKey: null,
});

function parametersOf(input) {
  if (input instanceof URLSearchParams) return new URLSearchParams(input);
  if (input instanceof URL) return new URLSearchParams(input.search);
  const value = String(input ?? "");
  if (!value || value.startsWith("?")) return new URLSearchParams(value);
  if (!value.startsWith("/") && !value.startsWith("#") && !value.includes("?") && !/^[a-z][a-z\d+.-]*:/i.test(value)) {
    return new URLSearchParams(value);
  }
  return new URL(value, "https://atlas.invalid/").searchParams;
}

/**
 * Parse a URL, query string, or URLSearchParams into validated view state.
 * options: { domains, populations, paperKeys, defaultView: "chart" | "table" }.
 * Lists may be arrays or Sets. Returned selection lists are arrays.
 * invalidParams contains query-key names, once each, for the UI's notice.
 * Unknown query keys are ignored, so tracking parameters do not become filters.
 * Invalid scalar values use defaults; invalid list entries are dropped.
 */
export function parseViewState(input, options = {}) {
  const params = parametersOf(input);
  const invalid = new Set();
  const state = {};
  const singleValue = (key, fallback) => {
    if (!params.has(key)) return fallback;
    const values = [...new Set(params.getAll(key))];
    if (values.length !== 1) {
      invalid.add(key);
      return fallback;
    }
    return values[0];
  };

  for (const [field, config] of Object.entries(SCALARS)) {
    const fallback = field === "view" && options.defaultView === "table" ? "table" : config.fallback;
    const value = singleValue(config.key, fallback);
    state[field] = config.values.includes(value) ? value : fallback;
    if (!config.values.includes(value)) invalid.add(config.key);
  }

  for (const [field, key] of Object.entries(LISTS)) {
    const allowed = new Set(field === "activeDomains" ? options.domains || [] : options.populations || []);
    const selected = new Set();
    for (const raw of params.getAll(key)) {
      for (const value of raw.split(",").map(item => item.trim())) {
        if (allowed.has(value)) selected.add(value);
        else invalid.add(key);
      }
    }
    state[field] = [...selected].sort();
  }

  state.search = singleValue("q", "");
  const paper = singleValue("paper", null);
  const allowedPapers = new Set(options.paperKeys || []);
  state.paperKey = paper !== null && allowedPapers.has(paper) ? paper : null;
  if (paper !== null && !allowedPapers.has(paper)) invalid.add("paper");
  return { state, invalidParams: [...invalid] };
}

/**
 * Return pathname + query + hash for history or a copyable view link.
 * Merge state into currentUrl, preserving any omitted state fields, navigation,
 * unknown query parameters, the base path, and the hash. Explicit paperKey:null
 * clears the report. Explicit section:"learning" clears the creativity route.
 * Serialize view even when it is "chart", so a shared link overrides a phone's
 * table default. Other default choices are omitted. Validate using parse options.
 * Prefix the result with the current origin when copying an absolute link.
 */
export function serializeViewState(state, currentUrl = "/", options = {}) {
  const url = new URL(String(currentUrl), "https://atlas.invalid/");
  for (const [field, { key }] of Object.entries(SCALARS)) {
    if (has(state, field)) {
      url.searchParams.delete(key);
      if (state[field] != null) url.searchParams.set(key, String(state[field]));
    }
  }
  for (const [field, key] of Object.entries(LISTS)) {
    if (has(state, field)) {
      url.searchParams.delete(key);
      const values = typeof state[field] === "string" ? [state[field]] : state[field] || [];
      for (const value of values) url.searchParams.append(key, String(value));
    }
  }
  if (has(state, "search")) {
    url.searchParams.delete("q");
    if (state.search) url.searchParams.set("q", String(state.search));
  }
  if (has(state, "paperKey")) {
    url.searchParams.delete("paper");
    if (state.paperKey != null) url.searchParams.set("paper", String(state.paperKey));
  }

  const normalized = parseViewState(url, options).state;
  for (const key of KNOWN_KEYS) url.searchParams.delete(key);
  for (const [field, { key, fallback }] of Object.entries(SCALARS)) {
    if (field === "view" || normalized[field] !== fallback) url.searchParams.set(key, normalized[field]);
  }
  for (const [field, key] of Object.entries(LISTS)) {
    for (const value of normalized[field]) url.searchParams.append(key, value);
  }
  if (normalized.search) url.searchParams.set("q", normalized.search);
  if (normalized.paperKey !== null) url.searchParams.set("paper", normalized.paperKey);
  return url.pathname + url.search + url.hash;
}
