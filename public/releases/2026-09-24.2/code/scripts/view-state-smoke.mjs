import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseViewState, serializeViewState, VIEW_DEFAULTS } from "../src/view-state.mjs";

const papers = JSON.parse(readFileSync(new URL("../src/papers.json", import.meta.url), "utf8"));
const estimates = JSON.parse(readFileSync(new URL("../src/estimates.json", import.meta.url), "utf8"));
const options = {
  domains: [...new Set(estimates.map(estimate => estimate.learning_domain).filter(Boolean))],
  populations: [...new Set(papers.map(paper => paper.population_category).filter(Boolean))],
  paperKeys: papers.map(paper => paper.paper_key),
};
const paperKey = "bastani_etal_2025";
assert(options.paperKeys.includes(paperKey));

assert.deepEqual(parseViewState("", options), { state: VIEW_DEFAULTS, invalidParams: [] });
assert.equal(parseViewState("", { ...options, defaultView: "table" }).state.view, "table");
assert.equal(parseViewState("?view=chart", { ...options, defaultView: "table" }).state.view, "chart");
assert.equal(parseViewState("?view=table", options).state.view, "table");

const chosen = {
  designMode: "field", sampleMode: "all", activeDomains: ["Math", "Language"],
  activePopulations: ["High school", "Undergraduate"], comparisonType: "ai_vs_active",
  outcomeMode: "all", timingMode: "delayed", search: "Contractor and Reyes & learning",
  sortBy: "author", view: "table", plotSort: "precision", section: "creativity", paperKey,
};
const originalUrl = new URL("https://aiskillatlas.org/atlas/?utm_source=seminar#evidence");
const shared = serializeViewState(chosen, originalUrl, options);
const parsed = parseViewState(shared, options);
assert.deepEqual(parsed.invalidParams, []);
assert.deepEqual(parsed.state, {
  ...chosen, activeDomains: [...chosen.activeDomains].sort(), activePopulations: [...chosen.activePopulations].sort(),
});
assert(shared.startsWith("/atlas/?"));
assert(shared.endsWith("#evidence"));
assert(shared.includes("utm_source=seminar"));
assert.equal(originalUrl.href, "https://aiskillatlas.org/atlas/?utm_source=seminar#evidence");
assert.equal(serializeViewState(parsed.state, shared, options), shared);

const invalid = parseViewState("?design=invalid&sample=none&comparison=none&outcome=none&timing=later&sort=title&view=grid&plotSort=size&section=unknown&paper=missing&domain=Math&domain=Unknown&population=Undergraduate&population=Unknown", options);
assert.deepEqual(invalid.state, { ...VIEW_DEFAULTS, activeDomains: ["Math"], activePopulations: ["Undergraduate"] });
assert.deepEqual(new Set(invalid.invalidParams), new Set(["design", "sample", "comparison", "outcome", "timing", "sort", "view", "plotSort", "section", "paper", "domain", "population"]));

const duplicate = parseViewState("?design=lab&design=field&view=table&view=chart&q=Math&q=Coding&domain=Math,Language&domain=Math", options);
assert.equal(duplicate.state.designMode, "rct");
assert.equal(duplicate.state.view, "chart");
assert.equal(duplicate.state.search, "");
assert.deepEqual(duplicate.state.activeDomains, ["Language", "Math"]);
assert.deepEqual(new Set(duplicate.invalidParams), new Set(["design", "view", "q"]));
assert.deepEqual(parseViewState("?domain=&population=&view=", options).invalidParams.sort(), ["domain", "population", "view"]);

// A selected report and its return destination retain every active filter.
const reportUrl = serializeViewState({ paperKey }, shared, options);
assert.equal(parseViewState(reportUrl, options).state.timingMode, "delayed");
const returned = serializeViewState({ paperKey: null, section: "learning" }, reportUrl, options);
const returnState = parseViewState(returned, options).state;
assert.equal(returnState.paperKey, null);
assert.equal(returnState.section, "learning");
assert.equal(returnState.designMode, "field");
assert.equal(returnState.search, chosen.search);
assert.equal(returnState.view, "table");
assert.deepEqual(returnState.activeDomains, ["Language", "Math"]);
assert(returned.endsWith("#evidence"));

const defaultsUrl = serializeViewState(VIEW_DEFAULTS, "/atlas/#studies", options);
assert.equal(defaultsUrl, "/atlas/?view=chart#studies");
assert.equal(parseViewState(defaultsUrl, { ...options, defaultView: "table" }).state.view, "chart");
const setUrl = serializeViewState({ activeDomains: new Set(["Math", "Language", "Math"]) }, "/", options);
assert.deepEqual(parseViewState(setUrl, options).state.activeDomains, ["Language", "Math"]);
assert.deepEqual(parseViewState(new URLSearchParams("timing=immediate&q=Germ%C3%A1n"), options).state.search, "Germán");
assert.equal(parseViewState(new URL("https://aiskillatlas.org/?design=online"), options).state.designMode, "online");
assert.equal(parseViewState("design=obs&sample=nonstudents", options).state.sampleMode, "nonstudents");
assert.deepEqual(parseViewState("?utm_source=seminar", options).invalidParams, []);
assert.equal(serializeViewState({ designMode: "invalid", activeDomains: ["Unknown"] }, "/", options), "/?view=chart");
assert.equal(parseViewState("?sort=n", options).state.sortBy, "effect");
assert.deepEqual(parseViewState("?sort=n", options).invalidParams, ["sort"]);

// Every control value used in the app must survive a link round trip.
const choices = {
  designMode: ["rct", "lab", "field", "online", "obs"], sampleMode: ["students", "nonstudents", "all"],
  comparisonType: ["ai_vs_bau", "ai_vs_active", "ai_design"], outcomeMode: ["without_ai", "all"],
  timingMode: ["all", "immediate", "delayed"], sortBy: ["effect", "year", "author"],
  view: ["chart", "table"], plotSort: ["effect", "precision", "year"], section: ["learning", "creativity"],
};
for (const [field, values] of Object.entries(choices)) {
  for (const value of values) {
    const url = serializeViewState({ [field]: value }, "/", options);
    assert.equal(parseViewState(url, options).state[field], value, `${field}=${value}`);
  }
}
console.log("View-state smoke checks passed: filters, validation, navigation, and viewport-independent shared views.");
