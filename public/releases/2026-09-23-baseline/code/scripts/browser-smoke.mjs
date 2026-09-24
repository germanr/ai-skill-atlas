// Browser regressions against the checked-in atlas data. Run with npm run test:browser.
// ATLAS_TEST_URL can target an existing server. ATLAS_CHROMIUM_PATH overrides browser discovery.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "playwright-core";
import { createServer } from "vite";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const papers = JSON.parse(readFileSync(join(root, "src/papers.json"), "utf8"));
const estimates = JSON.parse(readFileSync(join(root, "src/estimates.json"), "utf8"));
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

function checkCSV(rows, expected) {
  sameMembers(idsOf(rows), idsOf(expected), "Exported IDs differ from the requested data");
  assert.equal(rows.length, expected.length, "Exported record count is wrong");
  for (const row of rows) {
    const source = estimateById.get(row.estimate_id);
    for (const field of ["paper_key", "study_label", "effect_size_sd", "se", "outcome", "notes", "is_subgroup"]) {
      assert.equal(row[field], String(source[field] ?? ""), `${row.estimate_id}: CSV ${field} changed`);
    }
    const paper = paperByKey.get(source.paper_key);
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
    await filter("Comparison", "Off-the-shelf vs scaffolded AI");
    await filter("Domain", "Math");
    await page.getByRole("button", { name: "Table", exact: true }).click();
    const chungMath = estimates.filter(e => e.paper_key === "chung_etal_2025" && e.learning_domain === "Math" && !e.is_subgroup && e.comparison_type === "ai_design" && !e.outcome_with_ai);
    assert.ok(chungMath.length > 0, "Chung math fixture is missing");
    await eventually(async () => {
      const ids = await tableIDs();
      assert.ok(chungMath.every(e => ids.includes(e.estimate_id)), "Math omitted Chung because its paper category is Coding");
      assert.ok(ids.every(id => estimateById.get(id).learning_domain === "Math"), "Math includes another subject");
    }, "Math table did not update");
    await filter("Domain", "All");
    await filter("Domain", "Coding");
    await eventually(async () => {
      const ids = await tableIDs();
      assert.ok(ids.length > 0, "Coding comparison should have records");
      assert.ok(ids.every(id => estimateById.get(id).learning_domain === "Coding"), "Coding includes another subject");
      assert.ok(chungMath.every(e => !ids.includes(e.estimate_id)), "Coding retained Chung's math results");
    }, "Coding table did not update");
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
