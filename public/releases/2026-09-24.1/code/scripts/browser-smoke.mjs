// Browser regressions against the checked-in atlas data. Run with npm run test:browser.
// ATLAS_TEST_URL can target an existing server. ATLAS_CHROMIUM_PATH overrides browser discovery.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "playwright-core";
import { createServer } from "vite";
import { CSV_METADATA_COLUMNS, flattenEstimateMetadata } from "../src/evidence-metadata.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const papers = JSON.parse(readFileSync(join(root, "src/papers.json"), "utf8"));
const estimates = JSON.parse(readFileSync(join(root, "src/estimates.json"), "utf8"));
const metadata = JSON.parse(readFileSync(join(root, "src/evidence_metadata.json"), "utf8"));
const release = JSON.parse(readFileSync(join(root, "src/release.json"), "utf8"));
const paperByKey = new Map(papers.map(p => [p.paper_key, p]));
const estimateById = new Map(estimates.map(e => [e.estimate_id, e]));
const studentKeys = new Set(papers.filter(p => !["Adults general", "Professional"].includes(p.population_category)).map(p => p.paper_key));
const primary = estimates.filter(e => studentKeys.has(e.paper_key) && !e.is_subgroup && !e.outcome_with_ai && (e.comparison_type || "ai_vs_bau") === "ai_vs_bau");
const defaultRows = primary.filter(e => e.design_class !== "observational");
const observationalRows = primary.filter(e => e.design_class === "observational");
const hasInterval = e => e.effect_size_sd != null && (e.se > 0 || (e.ci_lower != null && e.ci_upper != null));
const idsOf = rows => rows.map(e => e.estimate_id);
const sameMembers = (actual, expected, message) => assert.deepEqual([...actual].sort(), [...expected].sort(), message);
const forestSelector = 'svg[aria-label="Forest plot of learning effects"]';
const runtimeErrors = [];
let server;
let browser;
let passed = 0;

async function eventually(check, message) {
  const deadline = Date.now() + 6000;
  let lastError;
  do {
    try { await check(); return; } catch (error) { lastError = error; }
    await delay(50);
  } while (Date.now() < deadline);
  throw new Error(message, { cause: lastError });
}

async function test(name, run) {
  await run();
  passed += 1;
  console.log(`PASS ${name}`);
}

function browserExecutable() {
  if (process.env.ATLAS_CHROMIUM_PATH) {
    assert.ok(existsSync(process.env.ATLAS_CHROMIUM_PATH), "ATLAS_CHROMIUM_PATH does not exist");
    return process.env.ATLAS_CHROMIUM_PATH;
  }
  const candidates = [
    chromium.executablePath(),
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
  ];
  const executable = candidates.find(candidate => existsSync(candidate));
  assert.ok(executable, "No Chromium browser found. Set ATLAS_CHROMIUM_PATH or run npx playwright-core install chromium.");
  return executable;
}

// Parse actual browser downloads, including quoted commas, quotes, and line breaks.
function parseCSV(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i += 1; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(field); field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += char;
  }
  assert.equal(quoted, false, "CSV has an unterminated quoted field");
  if (field !== "" || row.length > 0) { row.push(field); rows.push(row); }
  const [header, ...data] = rows;
  assert.ok(header?.includes("estimate_id"), "CSV lacks its header");
  assert.equal(new Set(header).size, header.length, "CSV repeats a column");
  return data.map((values, index) => {
    assert.equal(values.length, header.length, `CSV row ${index + 2} has the wrong field count`);
    return Object.fromEntries(header.map((name, col) => [name, values[col]]));
  });
}

async function readDownload(page, buttonName) {
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: buttonName, exact: true }).click(),
  ]);
  assert.equal(await download.failure(), null, "CSV download failed");
  const stream = await download.createReadStream();
  assert.ok(stream, "CSV download has no content stream");
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  const rows = parseCSV(Buffer.concat(chunks).toString("utf8"));
  await download.delete();
  return rows;
}

function checkCSV(rows, expected, expectedPapers = papers) {
  const sourceById = new Map(expected.map(row => [row.estimate_id, row]));
  const sourcePapers = new Map(expectedPapers.map(paper => [paper.paper_key, paper]));
  sameMembers(idsOf(rows), idsOf(expected), "Exported IDs differ from the requested data");
  assert.equal(rows.length, expected.length, "Exported record count is wrong");
  for (const row of rows) {
    const source = sourceById.get(row.estimate_id);
    for (const field of ["paper_key", "study_label", "effect_size_sd", "se", "n_total", "outcome", "notes", "is_subgroup"]) {
      assert.equal(row[field], String(source[field] ?? ""), `${row.estimate_id}: CSV ${field} changed`);
    }
    const paper = sourcePapers.get(source.paper_key);
    assert.equal(row.authors, paper.authors_full || paper.authors_short || "", "CSV author quoting changed");
  }
}

async function main() {
  let baseURL = process.env.ATLAS_TEST_URL;
  if (!baseURL) {
    server = await createServer({
      configFile: join(root, "vite.config.js"),
      logLevel: "error", clearScreen: false,
      server: { host: "127.0.0.1", port: 0, strictPort: true, open: false, hmr: false },
    });
    await server.listen();
    const address = server.httpServer.address();
    assert.ok(address && typeof address === "object", "Vite did not open a TCP port");
    baseURL = `http://127.0.0.1:${address.port}/`;
  }
  const homeURL = new URL(baseURL);
  homeURL.search = "";
  homeURL.hash = "";
  if (!homeURL.pathname.endsWith("/")) homeURL.pathname += "/";
  browser = await chromium.launch({ executablePath: browserExecutable(), headless: true });

  async function newPage(viewport) {
    const context = await browser.newContext({ viewport, acceptDownloads: true, reducedMotion: "reduce", serviceWorkers: "block" });
    // Never send test traffic to analytics, fonts, or other external services.
    await context.route("**/*", route => {
      const url = new URL(route.request().url());
      return url.origin === homeURL.origin || ["data:", "blob:"].includes(url.protocol)
        ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    page.on("pageerror", error => runtimeErrors.push(`${page.url()}: ${error.message}`));
    return page;
  }

  const page = await newPage({ width: 1440, height: 1000 });
  const forest = () => page.locator(forestSelector);
  const plottedIDs = () => forest().locator("[data-estimate-id]").evaluateAll(nodes => nodes.map(node => node.dataset.estimateId));
  const tableIDs = () => page.locator("#evidence table [data-estimate-id]").evaluateAll(nodes => nodes.map(node => node.dataset.estimateId));
  const search = () => page.getByRole("textbox", { name: "Search studies by title, author, or country" });
  const filter = (name, value) => page.locator(`[aria-label="${name} filter"]`).getByRole("button", { name: value, exact: true }).click();
  async function home(hash = "") {
    await page.goto(`${homeURL.href}${hash}`, { waitUntil: "domcontentloaded" });
    await page.locator("#evidence").waitFor();
  }

  await test("last-updated month matches the active release", async () => {
    await home();
    const month = new Intl.DateTimeFormat("en", { month: "long", year: "numeric", timeZone: "UTC" })
      .format(new Date(`${release.date}T00:00:00Z`));
    await page.getByText(`Last updated · ${month}`, { exact: true }).waitFor();
  });

  await test("observational plot counts, clipped statistics, and overflow arrows", async () => {
    await home();
    await filter("Design", "Observational data");
    const plotted = observationalRows.filter(hasInterval);
    const studyCount = new Set(plotted.map(e => e.paper_key)).size;
    const allStudyCount = new Set(observationalRows.map(e => e.paper_key)).size;
    await page.getByText(`${plotted.length} plotted estimates · ${studyCount} ${studyCount === 1 ? "study" : "studies"}`, { exact: true }).waitFor();
    if (observationalRows.length > plotted.length) {
      await page.getByText(new RegExp(`${observationalRows.length} matching records from ${allStudyCount} stud`)).waitFor();
    }
    sameMembers(await plottedIDs(), idsOf(observationalRows.filter(hasInterval)), "Observational plot membership changed");
    // Isolate the original overflow case so new studies cannot remove it.
    await search().fill("Stromberg");
    const overflowRows = observationalRows.filter(e => e.paper_key === "stromberg_etal_2026");
    await eventually(async () => sameMembers(await plottedIDs(), idsOf(overflowRows.filter(hasInterval)), "Overflow fixture is not isolated"), "Stromberg filter did not update");
    await forest().evaluate(svg => svg.scrollIntoView({ block: "center", behavior: "instant" }));
    const geometry = await forest().evaluate(svg => {
      const clip = svg.querySelector("clipPath");
      const clipRect = clip.querySelector("rect");
      const bounds = { x: clipRect.x.baseVal.value, width: clipRect.width.baseVal.value };
      const pooled = svg.querySelector('g[aria-label^="Pooled estimate:"]');
      const diamond = pooled.querySelector("polygon");
      const band = [...svg.children].find(node => node.localName === "rect" && node.hasAttribute("clip-path"));
      const meanLine = [...svg.children].find(node => node.localName === "line" && node.hasAttribute("clip-path"));
      const axis = [...svg.children].find(node => node.localName === "line" &&
        Number(node.getAttribute("x1")) === bounds.x && Number(node.getAttribute("x2")) === bounds.x + bounds.width &&
        node.getAttribute("y1") === node.getAttribute("y2"));
      const screen = new DOMPoint(220, 38).matrixTransform(svg.getScreenCTM());
      const hit = document.elementFromPoint(screen.x, screen.y);
      return {
        bounds, hasMatchingAxis: Boolean(axis),
        labelX: Number(pooled.querySelector("text").getAttribute("x")),
        clipReference: `url(#${clip.id})`,
        diamondClip: diamond.parentElement.getAttribute("clip-path"),
        bandClip: band?.getAttribute("clip-path"), meanClip: meanLine?.getAttribute("clip-path"),
        rawDiamondCoversLabelPoint: diamond.isPointInFill(new DOMPoint(220, 38)),
        hitInsideSvg: Boolean(hit && svg.contains(hit)), hitDiamond: hit === diamond,
        pooledText: pooled.getAttribute("aria-label"),
      };
    });
    assert.ok(geometry.hasMatchingAxis && geometry.bounds.x > geometry.labelX, "Clip must match the plot axis and exclude labels");
    for (const field of ["diamondClip", "bandClip", "meanClip"]) assert.equal(geometry[field], geometry.clipReference, `${field} is not clipped to the plot`);
    assert.ok(geometry.rawDiamondCoversLabelPoint, "Regression no longer exercises a raw diamond extending into labels");
    assert.ok(geometry.hitInsideSvg && !geometry.hitDiamond, "Pooled diamond is visible over the label area");
    assert.match(geometry.pooledText, /[−-]1\.40/, "Full pooled confidence interval must remain available");

    const outside = overflowRows.find(e => e.effect_size_sd < -1);
    const inside = overflowRows.find(e => e.effect_size_sd > -1 && e.effect_size_sd < 1 && hasInterval(e));
    assert.ok(outside && inside, "Observational fixture needs both an off-axis point and an ordinary point");
    const markers = await forest().evaluate((svg, { outsideId, insideId }) => {
      const marker = id => svg.querySelector(`[data-estimate-id="${id}"] > g[clip-path]`).lastElementChild;
      const arrow = marker(outsideId);
      const normal = marker(insideId);
      return {
        arrowTag: arrow.localName,
        arrowPoints: [...arrow.points].map(point => ({ x: point.x, y: point.y })),
        normalCenter: normal.getBBox().x + normal.getBBox().width / 2,
      };
    }, { outsideId: outside.estimate_id, insideId: inside.estimate_id });
    assert.equal(markers.arrowTag, "polygon");
    assert.equal(markers.arrowPoints.length, 3, "Off-axis point must use an arrow rather than its normal marker");
    assert.equal(markers.arrowPoints[0].x, geometry.bounds.x);
    assert.ok(markers.arrowPoints.slice(1).every(point => point.x > geometry.bounds.x), "Lower-bound arrow must point left");
    const expectedCenter = geometry.bounds.x + (inside.effect_size_sd + 1) * geometry.bounds.width / 2;
    assert.ok(Math.abs(markers.normalCenter - expectedCenter) < 0.1, "In-range point moved from its true effect");
    await search().fill("");
    await eventually(async () => sameMembers(await plottedIDs(), idsOf(plotted), "Clearing search did not restore the observational slice"), "Observational filter did not update");
  });

  await test("filtered and full CSV downloads preserve source IDs, values, and quoting", async () => {
    checkCSV(await readDownload(page, "↓ CSV (filtered)"), observationalRows);
    checkCSV(await readDownload(page, "↓ CSV (full dataset)"), estimates);
    console.log(`  Full CSV: ${estimates.length} source records`);
  });

  await test("domain filters select estimate subjects within mixed-subject papers", async () => {
    await home();
    await filter("Sample", "Non-students");
    await filter("Domain", "Math");
    await page.getByRole("button", { name: "Table", exact: true }).click();
    const liuMath = estimates.filter(e => e.paper_key === "liu_etal_2026" && e.learning_domain === "Math" && !e.is_subgroup && e.comparison_type === "ai_vs_bau" && !e.outcome_with_ai);
    assert.ok(liuMath.length > 0, "Liu math fixture is missing");
    await eventually(async () => {
      const ids = await tableIDs();
      assert.ok(liuMath.every(e => ids.includes(e.estimate_id)), "Math omitted Liu because its paper category is Mixed");
      assert.ok(ids.every(id => estimateById.get(id).learning_domain === "Math"), "Math includes another subject");
    }, "Math table did not update");
    await filter("Domain", "All");
    await filter("Domain", "Language");
    await filter("Comparison", "AI vs active control");
    const liuReading = estimates.filter(e => e.paper_key === "liu_etal_2026" && e.learning_domain === "Language" && !e.is_subgroup && e.comparison_type === "ai_vs_active" && !e.outcome_with_ai);
    assert.ok(liuReading.length > 0, "Liu reading fixture is missing");
    await eventually(async () => {
      const ids = await tableIDs();
      assert.ok(liuReading.every(e => ids.includes(e.estimate_id)), "Language omitted Liu's reading result");
      assert.ok(ids.every(id => estimateById.get(id).learning_domain === "Language"), "Language includes another subject");
      assert.ok(liuMath.every(e => !ids.includes(e.estimate_id)), "Language retained Liu's math results");
    }, "Language table did not update");
  });

  await test("search-only reset and records without a plotted effect", async () => {
    await home();
    await search().fill("Hausman");
    const reset = page.getByRole("button", { name: "Reset all (1)", exact: true });
    await reset.waitFor();
    await reset.click();
    assert.equal(await search().inputValue(), "", "Reset did not clear search");
    await eventually(async () => assert.equal(await page.getByRole("button", { name: /Reset all/ }).count(), 0), "Reset stayed visible after clearing search");
    await filter("Design", "Observational data");
    await search().fill("Hausman");
    await page.getByText("Matching records lack a standardized effect or uncertainty interval. Open Table to inspect them.", { exact: true }).waitFor();
    assert.equal(await page.getByText("No estimates match the current filters.", { exact: true }).count(), 0, "Missing effects are mislabeled as no matching records");
    await page.getByRole("button", { name: "Table", exact: true }).click();
    const hausmanRows = observationalRows.filter(e => e.paper_key === "hausman_etal_2025");
    assert.equal(hausmanRows.length, 4, "Hausman regression fixture changed");
    await eventually(async () => sameMembers(await tableIDs(), idsOf(hausmanRows), "Hausman records disappeared from Table"), "Hausman table did not update");
  });

  await test("chart sort orders preserve membership and follow effect, precision, and year", async () => {
    await home();
    const expected = defaultRows.filter(hasInterval);
    for (const mode of ["Effect", "Precision", "Year"]) {
      await page.locator("#evidence .toolbar").getByRole("button", { name: mode, exact: true }).click();
      await eventually(async () => {
        const ids = await plottedIDs();
        sameMembers(ids, idsOf(expected), `${mode} sort changed the plot membership`);
        const rows = ids.map(id => estimateById.get(id));
        for (let i = 1; i < rows.length; i += 1) {
          const [before, after] = [rows[i - 1], rows[i]];
          if (mode === "Effect") assert.ok(before.effect_size_sd >= after.effect_size_sd, "Effect order is not descending");
          if (mode === "Precision") assert.ok((before.se ?? Infinity) <= (after.se ?? Infinity), "Precision order is not ascending SE");
          if (mode === "Year") {
            const [a, b] = [paperByKey.get(before.paper_key).year, paperByKey.get(after.paper_key).year];
            assert.ok(a > b || (a === b && before.effect_size_sd >= after.effect_size_sd), "Year order or its effect tie-break is wrong");
          }
        }
      }, `${mode} sort did not update`);
    }
  });

  await test("timing filters partition default records and apply only to the filtered CSV", async () => {
    await home();
    await page.getByRole("button", { name: "Table", exact: true }).click();
    const byTiming = new Map();
    for (const [label, value] of [["Immediate", "immediate"], ["Delayed", "delayed"]]) {
      await filter("Timing", label);
      const expected = defaultRows.filter(row => row.outcome_timing === value);
      assert.ok(expected.length > 0, `The checked-in data lack ${value} records`);
      await eventually(async () => sameMembers(await tableIDs(), idsOf(expected), `${label} selected the wrong records`), `${label} timing did not update`);
      byTiming.set(value, await tableIDs());
      const exported = await readDownload(page, "↓ CSV (filtered)");
      checkCSV(exported, expected);
      assert.ok(exported.every(row => row.outcome_timing === value), "Timing-filtered CSV contains another follow-up category");
      for (const row of exported) {
        assert.equal(row.release_id, release.id);
        assert.equal(row.release_date, release.date);
        assert.equal(new URL(row.view_url).searchParams.get("timing"), value, "CSV view URL dropped outcome timing");
        const selection = JSON.parse(row.selection);
        assert.equal(selection.timingMode, value);
        assert.equal(selection.scope, "filtered");
        assert.equal(selection.dataset, "learning");
        const source = estimateById.get(row.estimate_id);
        const expectedMetadata = flattenEstimateMetadata(source, paperByKey.get(source.paper_key), metadata);
        for (const column of CSV_METADATA_COLUMNS) assert.equal(row[column], String(expectedMetadata[column] ?? ""), `${row.estimate_id}: CSV changed ${column}`);
      }
    }
    assert.ok(byTiming.get("immediate").every(id => !byTiming.get("delayed").includes(id)), "Timing categories overlap");
    sameMembers([...byTiming.get("immediate"), ...byTiming.get("delayed")], idsOf(defaultRows), "Timing categories do not partition default records");
    const full = await readDownload(page, "↓ CSV (full dataset)");
    checkCSV(full, estimates);
    for (const row of full) {
      assert.equal(row.release_id, release.id);
      assert.equal(row.release_date, release.date);
      assert.equal(row.view_url, "", "Full export incorrectly inherits an active filtered view");
      assert.deepEqual(JSON.parse(row.selection), { scope: "full", dataset: "learning" });
      const sample = metadata.estimates?.[row.estimate_id]?.sample;
      const reviewedN = sample?.review_status === "reviewed" ? sample.n : null;
      assert.equal(row.estimate_analyzed_n, String(reviewedN ?? ""), "Unreviewed raw N was promoted to a verified analyzed count");
    }
    await filter("Timing", "All timings");
    await eventually(async () => sameMembers(await tableIDs(), idsOf(defaultRows), "All timings did not restore the default sample"), "All timings did not update");
  });

  const sharedExpected = defaultRows.filter(row => row.learning_domain === "General knowledge" &&
    row.outcome_timing === "delayed" && paperByKey.get(row.paper_key).authors_short.includes("Contractor"));
  assert.ok(sharedExpected.length > 0, "The checked-in Contractor delayed-learning fixture is missing");
  async function checkSharedView(target) {
    await target.locator("#evidence").waitFor();
    await eventually(async () => {
      const actual = await target.locator(forestSelector).locator("[data-estimate-id]").evaluateAll(nodes => nodes.map(node => node.dataset.estimateId));
      sameMembers(actual, idsOf(sharedExpected.filter(hasInterval)), "Shared chart membership changed");
      assert.equal(await target.locator("#evidence table").count(), 0, "Shared chart selection changed to Table");
      assert.equal(await target.getByRole("textbox", { name: "Search studies by title, author, or country" }).inputValue(), "Contractor");
      for (const [name, value] of [["Timing", "Delayed"], ["Domain", "General knowledge"]]) {
        assert.equal(await target.locator(`[aria-label="${name} filter"]`).getByRole("button", { name: value, exact: true }).getAttribute("aria-pressed"), "true", `${name} control does not show the shared choice`);
      }
      const params = new URL(target.url()).searchParams;
      assert.equal(params.get("timing"), "delayed");
      assert.equal(params.get("q"), "Contractor");
      assert.ok(params.getAll("domain").flatMap(value => value.split(",")).includes("General knowledge"));
      assert.equal(params.get("view"), "chart");
      assert.equal(params.get("plotSort"), "precision");
      assert.equal(params.get("sort"), "author");
      for (let i = 1; i < actual.length; i += 1) {
        assert.ok((estimateById.get(actual[i - 1]).se ?? Infinity) <= (estimateById.get(actual[i]).se ?? Infinity), "Shared precision ordering changed");
      }
    }, "Shared filters, display, or sorting did not restore");
  }

  await test("copy view link, fresh browser, reload, and manual clipboard fallback", async () => {
    await home("#evidence");
    await filter("Timing", "Delayed");
    await filter("Domain", "General knowledge");
    await search().fill("Contractor");
    await page.locator("#evidence .toolbar").getByRole("button", { name: "Precision", exact: true }).click();
    await page.locator("#studies").getByRole("button", { name: "Author", exact: true }).click();
    await checkSharedView(page);
    await page.evaluate(() => {
      window.__atlasCopiedLink = null;
      Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
        writeText: async value => { window.__atlasCopiedLink = value; },
      } });
    });
    await page.getByRole("button", { name: "Copy view link", exact: true }).click();
    await eventually(async () => assert.equal(typeof await page.evaluate(() => window.__atlasCopiedLink), "string"), "Copy did not write a view URL");
    const copied = await page.evaluate(() => window.__atlasCopiedLink);
    const copiedURL = new URL(copied);
    assert.equal(copiedURL.origin, homeURL.origin, "Copied link lost its origin");
    assert.equal(copiedURL.pathname, homeURL.pathname, "Copied link lost the site base path");
    assert.equal(copiedURL.hash, "#evidence", "Copied link lost its anchor");
    const fresh = await newPage({ width: 1310, height: 900 });
    await fresh.goto(copied, { waitUntil: "domcontentloaded" });
    await checkSharedView(fresh);
    await fresh.reload({ waitUntil: "domcontentloaded" });
    await checkSharedView(fresh);
    await fresh.context().close();

    await page.evaluate(() => {
      Object.defineProperty(navigator, "clipboard", { configurable: true, value: {
        writeText: async () => { throw new Error("Clipboard unavailable in smoke test"); },
      } });
    });
    await page.getByRole("button", { name: "Copy view link", exact: true }).click();
    const fallback = page.getByRole("textbox", { name: "View link", exact: true });
    await fallback.waitFor();
    assert.equal(await fallback.inputValue(), copied, "Manual copy fallback changed the shared view");
  });

  await test("filter keystrokes replace history and study Back/Forward preserve shared filters", async () => {
    await home("#evidence");
    await eventually(async () => sameMembers(await plottedIDs(), idsOf(defaultRows.filter(hasInterval)), "Initial chart did not settle"), "Default records did not render");
    const initialHistoryLength = await page.evaluate(() => history.length);
    await filter("Timing", "Delayed");
    await filter("Domain", "General knowledge");
    await search().pressSequentially("Contractor", { delay: 10 });
    await page.locator("#evidence .toolbar").getByRole("button", { name: "Precision", exact: true }).click();
    await page.locator("#studies").getByRole("button", { name: "Author", exact: true }).click();
    await checkSharedView(page);
    assert.equal(await page.evaluate(() => history.length), initialHistoryLength, "Filter changes or search keystrokes added browser history entries");
    const row = forest().locator("[data-estimate-id]").first();
    await row.focus();
    const key = estimateById.get(await row.getAttribute("data-estimate-id")).paper_key;
    await row.press("Enter");
    await page.getByRole("heading", { name: paperByKey.get(key).title, exact: true }).waitFor();
    const reportParams = new URL(page.url()).searchParams;
    assert.equal(reportParams.get("paper"), key);
    assert.equal(reportParams.get("q"), "Contractor", "Opening a report dropped search");
    assert.equal(reportParams.get("timing"), "delayed", "Opening a report dropped timing");
    assert.ok(reportParams.getAll("domain").flatMap(value => value.split(",")).includes("General knowledge"), "Opening a report dropped subject selection");
    await page.goBack();
    await checkSharedView(page);
    await page.goForward();
    await page.getByRole("heading", { name: paperByKey.get(key).title, exact: true }).waitFor();
    assert.equal(new URL(page.url()).searchParams.get("timing"), "delayed");
    await page.getByRole("button", { name: "All studies", exact: true }).click();
    await checkSharedView(page);
  });

  await test("invalid URL choices show a notice and recover to valid default filters", async () => {
    const malformed = new URL(homeURL);
    malformed.search = "?design=unknown&timing=later&view=grid&domain=Unknown";
    await page.goto(malformed.href, { waitUntil: "domcontentloaded" });
    await page.getByText(/Link options reset/).waitFor();
    await eventually(async () => sameMembers(await plottedIDs(), idsOf(defaultRows.filter(hasInterval)), "Malformed URL did not recover default chart membership"), "Invalid URL recovery did not render");
    assert.equal(await page.locator('[aria-label="Timing filter"]').getByRole("button", { name: "All timings", exact: true }).getAttribute("aria-pressed"), "true");
  });

  await test("keyboard study navigation preserves focus, history, and anchor scroll", async () => {
    await home("#evidence");
    await page.waitForFunction(() => {
      const top = document.getElementById("evidence").getBoundingClientRect().top;
      return top >= 0 && top < 250;
    });
    const row = forest().locator("[data-estimate-id]").first();
    await row.scrollIntoViewIfNeeded();
    await row.focus();
    const rowId = await row.getAttribute("data-estimate-id");
    const key = estimateById.get(rowId).paper_key;
    const scrollBefore = await page.evaluate(() => window.scrollY);
    await row.press("Enter");
    await page.getByRole("heading", { name: paperByKey.get(key).title, exact: true }).waitFor();
    await eventually(async () => assert.equal(await page.locator("h1").evaluate(node => node === document.activeElement), true), "Report heading did not receive focus");
    assert.equal(new URL(page.url()).searchParams.get("paper"), key);
    assert.equal(new URL(page.url()).hash, "#evidence", "Opening a report dropped the anchor");
    await page.getByRole("button", { name: "All studies", exact: true }).click();
    await row.waitFor();
    await eventually(async () => {
      assert.equal(await row.evaluate(node => node === document.activeElement), true, "Closing report did not restore row focus");
      assert.ok(Math.abs(await page.evaluate(() => window.scrollY) - scrollBefore) < 2, "Anchor navigation overrode the restored scroll position");
    }, "Return from report did not restore the originating row");
    assert.equal(new URL(page.url()).searchParams.has("paper"), false);
    assert.equal(new URL(page.url()).hash, "#evidence");

    const card = page.locator("#studies [data-paper-key]").first();
    await card.scrollIntoViewIfNeeded();
    await card.focus();
    const cardKey = await card.getAttribute("data-paper-key");
    await card.press("Space");
    await page.getByRole("heading", { name: paperByKey.get(cardKey).title, exact: true }).waitFor();
    await page.goBack();
    await card.waitFor();
    await eventually(async () => assert.equal(await card.evaluate(node => node === document.activeElement), true), "Browser Back did not restore card focus");
  });

  await test("direct study links and standalone About page load", async () => {
    const paper = paperByKey.get("contractor_reyes_2026");
    const deepLink = new URL(homeURL);
    deepLink.searchParams.set("paper", paper.paper_key);
    await page.goto(deepLink.href, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { name: paper.title, exact: true }).waitFor();
    await page.getByRole("button", { name: "All studies", exact: true }).click();
    await page.locator("#evidence").waitFor();
    assert.equal(new URL(page.url()).searchParams.has("paper"), false, "Closing a direct link left the report query");
    const response = await page.goto(new URL("about/", homeURL).href, { waitUntil: "domcontentloaded" });
    assert.ok(response?.ok(), "Standalone About page did not return success");
    await page.getByRole("heading", { name: "About the Atlas", exact: true }).waitFor();
    assert.match(await page.title(), /^About/);
  });

  await test("390px mobile defaults to Table and keeps document width within the viewport", async () => {
    const mobile = await newPage({ width: 390, height: 844 });
    await mobile.goto(homeURL.href, { waitUntil: "domcontentloaded" });
    await mobile.locator("#evidence table").waitFor();
    assert.equal(await mobile.locator(forestSelector).count(), 0, "Mobile opened the wide chart by default");
    sameMembers(await mobile.locator("#evidence table [data-estimate-id]").evaluateAll(nodes => nodes.map(node => node.dataset.estimateId)), idsOf(defaultRows), "Mobile table lost matching records");
    const width = await mobile.evaluate(() => ({ viewport: window.innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }));
    assert.ok(width.document <= width.viewport + 1 && width.body <= width.viewport + 1, `Mobile document overflows: ${JSON.stringify(width)}`);
    await mobile.context().close();
  });

  await test("an explicit shared chart overrides the mobile Table default", async () => {
    const mobile = await newPage({ width: 390, height: 844 });
    const chartURL = new URL(homeURL);
    chartURL.searchParams.set("view", "chart");
    await mobile.goto(chartURL.href, { waitUntil: "domcontentloaded" });
    await mobile.locator(forestSelector).waitFor();
    assert.equal(await mobile.locator("#evidence table").count(), 0);
    sameMembers(await mobile.locator(forestSelector).locator("[data-estimate-id]").evaluateAll(nodes => nodes.map(node => node.dataset.estimateId)), idsOf(defaultRows.filter(hasInterval)), "Explicit mobile chart lost estimates");
    await mobile.reload({ waitUntil: "domcontentloaded" });
    await mobile.locator(forestSelector).waitFor();
    assert.equal(new URL(mobile.url()).searchParams.get("view"), "chart");
    const width = await mobile.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
    assert.ok(width.document <= width.viewport + 1, "Explicit chart caused page-level mobile overflow");
    await mobile.context().close();
  });

  await test("verified participant and observation counts use separate labels", async () => {
    const recordURL = new URL(homeURL);
    recordURL.searchParams.set("paper", "learnlm_team_2025");
    await page.goto(recordURL.href, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { name: paperByKey.get("learnlm_team_2025").title, exact: true }).waitFor();
    await page.getByText(/165 students/).first().waitFor();
    await page.getByText(/2,713 sessions/).first().waitFor();
    const details = page.locator("details").filter({ has: page.locator("summary", { hasText: "Source, sample, and version details" }) }).first();
    await details.locator("summary").click();
    assert.equal(await details.getAttribute("open"), "", "Source details did not expand");
    await details.getByText("Source review", { exact: true }).waitFor();
  });

  await test("dataset counts distinguish records from available standardized effects", async () => {
    await home();
    const standardizedCount = estimates.filter(row => Number.isFinite(row.effect_size_sd)).length;
    assert.ok(standardizedCount < estimates.length, "The missing-effect regression fixture changed");
    for (const [label, value] of [["Studies", papers.length], ["Estimate records", estimates.length], ["Standardized effects", standardizedCount]]) {
      const cell = page.locator(`[data-stat="${label}"]`);
      await cell.waitFor();
      assert.equal(await cell.locator("div").first().innerText(), value.toLocaleString("en-US"), `${label} uses the wrong denominator`);
    }
    assert.doesNotMatch(await page.locator('meta[property="og:description"]').getAttribute("content"), /Every effect size, standardized/i);
    await page.goto(new URL("about/", homeURL).href, { waitUntil: "domcontentloaded" });
    await page.getByText(`${estimates.length} estimate records`, { exact: true }).waitFor();
    await page.getByText(`${standardizedCount} standardized effects`, { exact: true }).waitFor();
    await page.getByText(/randomized and observational studies/).waitFor();
    await page.getByText("The study reports at least 50 participants in total.", { exact: true }).waitFor();
    if (!paperByKey.has("kalam_etal_2025")) await page.getByText(/Kalam et al\. \(2025\) is excluded/).waitFor();
  });

  await test("study reports distinguish missing standardized effects and missing intervals", async () => {
    const missingEffect = estimates.find(row => !Number.isFinite(row.effect_size_sd));
    const missingInterval = estimates.find(row => Number.isFinite(row.effect_size_sd) && !hasInterval(row));
    assert.ok(missingEffect && missingInterval, "Checked-in unavailable-result fixtures are missing");
    const auditCases = ["franco_etal_2026__est85", "franco_etal_2026__est86", "lehmann_etal_2024__sg2", "lehmann_etal_2024__sg4"]
      .map(id => estimateById.get(id)).filter(Boolean);
    for (const source of [missingEffect, missingInterval, ...auditCases]) {
      const recordURL = new URL(homeURL);
      recordURL.searchParams.set("paper", source.paper_key);
      await page.goto(recordURL.href, { waitUntil: "domcontentloaded" });
      await page.getByRole("heading", { name: paperByKey.get(source.paper_key).title, exact: true }).waitFor();
      const row = page.locator(`[data-estimate-id="${source.estimate_id}"]`);
      await row.waitFor();
      const hasEffect = Number.isFinite(source.effect_size_sd);
      assert.equal(await row.getAttribute("data-has-standardized-effect"), String(hasEffect));
      await row.getByText(hasEffect ? "Uncertainty interval unavailable." : "Standardized effect unavailable. This does not mean the effect is zero.", { exact: true }).waitFor();
      assert.equal(await row.locator('[data-statistic="se"]').count(), 0, "Missing SE became a reported number");
      assert.equal(await row.locator('[data-statistic="ci"]').count(), 0, "Missing CI became a reported interval");
      if (!source.is_subgroup) await page.getByText(`Estimate records (${estimates.filter(e => e.paper_key === source.paper_key && !e.is_subgroup).length})`, { exact: true }).waitFor();
    }
  });

  await test("About identifies the current release and serves archived data and its manifest", async () => {
    const aboutURL = new URL("about/#data-releases", homeURL);
    await page.goto(aboutURL.href, { waitUntil: "domcontentloaded" });
    const heading = page.getByRole("heading", { name: "Data releases", exact: true });
    await heading.waitFor();
    await eventually(async () => {
      const box = await heading.boundingBox();
      assert.ok(box && box.y >= 0 && box.y < 300, "Release anchor is obscured or not reached");
    }, "Data-release anchor did not settle");
    await page.getByText(release.id, { exact: true }).first().waitFor();
    const csvLink = page.getByRole("link", { name: "Learning estimates CSV ↓", exact: true }).first();
    const archivedCSV = await page.request.get(new URL(await csvLink.getAttribute("href"), page.url()).href);
    assert.ok(archivedCSV.ok(), "Archived learning CSV failed to load");
    const archivedRows = parseCSV(await archivedCSV.text());
    const jsonLink = page.getByRole("link", { name: "Learning estimates JSON ↓", exact: true }).first();
    const archivedJSON = await page.request.get(new URL(await jsonLink.getAttribute("href"), page.url()).href);
    assert.ok(archivedJSON.ok(), "Archived learning JSON failed to load");
    const archivedEstimates = await archivedJSON.json();
    const papersLink = page.getByRole("link", { name: "Study records JSON ↓", exact: true }).first();
    const archivedPapersResponse = await page.request.get(new URL(await papersLink.getAttribute("href"), page.url()).href);
    assert.ok(archivedPapersResponse.ok(), "Archived study records failed to load");
    checkCSV(archivedRows, archivedEstimates, await archivedPapersResponse.json());
    assert.equal(archivedEstimates.length, release.counts.learning_estimates, "Archive disagrees with the release's own estimate count");
    const manifestLink = page.getByRole("link", { name: "Manifest, code, and other files ↗", exact: true }).first();
    const manifestResponse = await page.request.get(new URL(await manifestLink.getAttribute("href"), page.url()).href);
    assert.ok(manifestResponse.ok(), "Release manifest failed to load");
    assert.equal((await manifestResponse.json()).id, release.id, "Manifest identifies a different release");
  });

  assert.deepEqual(runtimeErrors, [], "Browser reported uncaught application errors");
  console.log(`All ${passed} browser smoke checks passed.`);
}

try {
  await main();
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  await browser?.close();
  await server?.close();
}
