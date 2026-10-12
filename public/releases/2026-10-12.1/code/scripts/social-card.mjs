// Regenerate after changing the learning data or HTML source:
// node scripts/social-card.mjs
// Read-only stale-input and PNG integrity check: node scripts/social-card.mjs --check
// ATLAS_CHROMIUM_PATH overrides the browser used for HTML rendering.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const templatePath = join(root, "scripts/social-card.html");
const imagePath = join(root, "public/images/og-card.png");
const receiptPath = join(root, "public/images/og-card.meta.json");
const hash = content => createHash("sha256").update(content).digest("hex");
const papers = JSON.parse(readFileSync(join(root, "src/papers.json"), "utf8"));
const estimates = JSON.parse(readFileSync(join(root, "src/estimates.json"), "utf8"));
const template = readFileSync(templatePath, "utf8");
const inputs = {
  schema_version: 1,
  width: 1200,
  height: 630,
  studies: papers.length,
  estimate_records: estimates.length,
  standardized_effects: estimates.filter(row => Number.isFinite(row.effect_size_sd)).length,
  template_sha256: hash(template),
};

function verifyImage() {
  const png = readFileSync(imagePath);
  assert.equal(png.subarray(0, 8).toString("hex"), "89504e470d0a1a0a", "Social card is not a PNG");
  assert.equal(png.readUInt32BE(16), inputs.width, "Social-card width changed");
  assert.equal(png.readUInt32BE(20), inputs.height, "Social-card height changed");
  return hash(png);
}

if (process.argv.includes("--check")) {
  assert.ok(existsSync(receiptPath), "Generate the social card first: node scripts/social-card.mjs");
  const { image_sha256, ...previousInputs } = JSON.parse(readFileSync(receiptPath, "utf8"));
  assert.deepEqual(previousInputs, inputs, "Social card is stale. Run node scripts/social-card.mjs after updating the learning data or HTML source.");
  assert.equal(verifyImage(), image_sha256, "Social card changed without its code-native renderer");
  console.log(`Social card current: ${inputs.studies} studies, ${inputs.estimate_records} records, ${inputs.standardized_effects} standardized effects.`);
} else {
  const { chromium } = await import("playwright-core");
  const candidates = [
    process.env.ATLAS_CHROMIUM_PATH,
    chromium.executablePath(),
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
  ].filter(Boolean);
  const executablePath = candidates.find(candidate => existsSync(candidate));
  assert.ok(executablePath, "No Chromium browser found. Set ATLAS_CHROMIUM_PATH or run npx playwright-core install chromium.");
  const html = template.replaceAll("{{STUDIES}}", inputs.studies.toLocaleString("en-US"))
    .replaceAll("{{RECORDS}}", inputs.estimate_records.toLocaleString("en-US"))
    .replaceAll("{{STANDARDIZED}}", inputs.standardized_effects.toLocaleString("en-US"));
  assert.ok(!html.includes("{{"), "Unresolved social-card template field");
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: inputs.width, height: inputs.height }, deviceScaleFactor: 1 });
    await page.route("**/*", route => route.abort());
    await page.setContent(html, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    const bounds = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }));
    assert.deepEqual(bounds, { width: inputs.width, height: inputs.height }, "Social-card content overflows its canvas");
    await page.screenshot({ path: imagePath, type: "png" });
    writeFileSync(receiptPath, `${JSON.stringify({ ...inputs, image_sha256: verifyImage() }, null, 2)}\n`);
    console.log(`Rendered social card: ${inputs.studies} studies, ${inputs.estimate_records} records, ${inputs.standardized_effects} standardized effects.`);
  } finally {
    await browser.close();
  }
}
