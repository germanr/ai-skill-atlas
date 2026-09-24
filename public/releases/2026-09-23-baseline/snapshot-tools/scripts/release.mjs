// Explicit, immutable evidence snapshots. Ordinary builds never create a release.
import { createHash, randomUUID } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, realpathSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { buildEstimatesCSV, buildRecordsCSV } from "../src/export.mjs";
import { validateMetadataRelease } from "../src/evidence-metadata.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SCHEMA_VERSION = 1;
const DATASETS = ["papers", "estimates", "creativity_papers", "creativity_estimates"];
const CODE_PATHS = [
  "ai-skill-atlas-explorer.jsx", "src/main.jsx", "src/about-main.jsx", "src/shared.mjs",
  "src/export.mjs", "src/evidence-metadata.mjs", "src/view-state.mjs", "src/release.mjs",
  "code/build_website_data.py", "code/build_creativity_data.py", "code/patch_subgroups.py",
  "scripts/release.mjs", "scripts/smoke.mjs", "scripts/browser-smoke.mjs",
  "package.json", "package-lock.json", "vite.config.js", "index.html", "about/index.html",
];
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
const jsonBytes = value => Buffer.from(JSON.stringify(value, null, 2) + "\n");
const readJSON = path => JSON.parse(readFileSync(path, "utf8"));
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const rowsOf = value => Array.isArray(value) ? value : value.papers;

function validateId(id) {
  assert(typeof id === "string" && /^[a-z0-9][a-z0-9._-]{0,79}$/.test(id),
    "Release ID must be 1–80 lowercase letters, digits, periods, underscores or hyphens, starting with a letter or digit.");
}

function validateDate(date) {
  assert(typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date), "An explicit YYYY-MM-DD release date is required.");
  const parsed = new Date(`${date}T00:00:00Z`);
  assert(Number.isFinite(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === date, "Invalid release date.");
}

function safePath(base, relative) {
  assert(typeof relative === "string" && relative.length > 0 && !relative.includes("\\") &&
    !relative.startsWith("/") && !relative.split("/").some(part => part === ".." || part === "." || part === "" || part.includes(":")),
  `Unsafe snapshot path: ${relative}`);
  return join(base, ...relative.split("/"));
}

function readIndex(root) {
  const path = join(root, "public", "releases", "index.json");
  if (!existsSync(path)) return { schema_version: SCHEMA_VERSION, current_release_id: null, releases: [] };
  const index = readJSON(path);
  assert(index.schema_version === SCHEMA_VERSION && Array.isArray(index.releases), "Invalid release index.");
  const ids = index.releases.map(entry => entry.id);
  ids.forEach(validateId);
  assert(new Set(ids).size === ids.length, "Duplicate release IDs in index.");
  assert(index.releases.length === 0 || ids.includes(index.current_release_id), "Current release is missing from index.");
  return index;
}

function countsOf(data) {
  return {
    learning_papers: rowsOf(data.papers).length,
    learning_estimates: rowsOf(data.estimates).length,
    creativity_papers: rowsOf(data.creativity_papers).length,
    creativity_estimates: rowsOf(data.creativity_estimates).length,
  };
}

function validateData(data) {
  for (const name of DATASETS) assert(Array.isArray(rowsOf(data[name])), `${name}: expected an array of records.`);
  for (const [paperName, estimateName] of [["papers", "estimates"], ["creativity_papers", "creativity_estimates"]]) {
    const paperRows = rowsOf(data[paperName]);
    const keys = new Set(paperRows.map(paper => paper.paper_key));
    assert(keys.size === paperRows.length, `${paperName}: duplicate paper keys.`);
    const ids = new Set();
    for (const estimate of rowsOf(data[estimateName])) {
      assert(keys.has(estimate.paper_key), `${estimateName}: unknown paper ${estimate.paper_key}.`);
      const id = estimate.estimate_id || `${estimate.paper_key}__outcome_${estimate.outcome_idx}`;
      assert(!ids.has(id), `${estimateName}: duplicate estimate ${id}.`);
      ids.add(id);
    }
  }
}

function atomicJSON(path, value) {
  mkdirSync(dirname(path), { recursive: true });
  const temporary = `${path}.${randomUUID()}.tmp`;
  writeFileSync(temporary, jsonBytes(value), { flag: "wx" });
  renameSync(temporary, path);
}

export function verifyRelease(root, entry, { current = false } = {}) {
  validateId(entry.id);
  validateDate(entry.date);
  const base = join(root, "public", "releases", entry.id);
  const manifestBytes = readFileSync(join(base, "manifest.json"));
  assert(digest(manifestBytes) === entry.manifest_sha256, `${entry.id}: manifest SHA256 differs from index.`);
  const manifest = JSON.parse(manifestBytes);
  assert(manifest.schema_version === SCHEMA_VERSION && manifest.id === entry.id && manifest.date === entry.date,
    `${entry.id}: manifest identity differs from index.`);
  assert(Array.isArray(manifest.files) && manifest.files.length > 0, `${entry.id}: missing file manifest.`);
  const listed = new Set(["manifest.json"]);
  for (const file of manifest.files) {
    assert(!listed.has(file.path), `${entry.id}: duplicate file ${file.path}.`);
    listed.add(file.path);
    const bytes = readFileSync(safePath(base, file.path));
    assert(bytes.length === file.bytes && digest(bytes) === file.sha256, `${entry.id}: integrity check failed for ${file.path}.`);
    if (current && file.source_path) {
      const currentBytes = readFileSync(safePath(root, file.source_path));
      assert(digest(currentBytes) === file.sha256, `${entry.id}: current ${file.source_path} differs from its release snapshot. Create a new release after review.`);
    }
  }
  function inspectDirectory(directory, prefix = "") {
    for (const item of readdirSync(directory, { withFileTypes: true })) {
      const path = prefix + item.name;
      assert(!item.isSymbolicLink(), `${entry.id}: symbolic links are not allowed in snapshots.`);
      if (item.isDirectory()) inspectDirectory(join(directory, item.name), path + "/");
      else assert(listed.has(path), `${entry.id}: unlisted file ${path}.`);
    }
  }
  inspectDirectory(base);
  const data = Object.fromEntries(DATASETS.map(name => [name, readJSON(join(base, "data", `${name}.json`))]));
  validateData(data);
  const counts = countsOf(data);
  assert(JSON.stringify(counts) === JSON.stringify(manifest.counts) && JSON.stringify(counts) === JSON.stringify(entry.counts),
    `${entry.id}: recorded counts differ from archived data.`);
  if (current) {
    const hasMetadata = manifest.files.some(file => file.source_path === "src/evidence_metadata.json");
    assert(hasMetadata === existsSync(join(root, "src", "evidence_metadata.json")),
      `${entry.id}: current evidence metadata was added or removed after the snapshot.`);
  }
  return manifest;
}

export function verifyReleases({ root = ROOT, id, current = false } = {}) {
  const index = readIndex(root);
  assert(index.releases.length > 0, "No releases have been recorded.");
  const entries = id ? index.releases.filter(entry => entry.id === id) : index.releases;
  assert(entries.length > 0, `Unknown release: ${id}`);
  for (const entry of entries) verifyRelease(root, entry, { current: current && entry.id === index.current_release_id });
  const pointer = readJSON(join(root, "src", "release.json"));
  const active = index.releases.find(entry => entry.id === index.current_release_id);
  assert(JSON.stringify(pointer) === JSON.stringify(active), "src/release.json differs from the current release index entry.");
  if (current && id && id !== index.current_release_id) throw new Error("Current-data checks must target the active release.");
  return entries;
}

export function createRelease({
  root = ROOT, sourceRoot = root, id, date, label, kind = "release", description = "",
} = {}) {
  validateId(id);
  validateDate(date);
  assert(kind === "release" || kind === "baseline", "Kind must be release or baseline.");
  assert(typeof label === "string" && label.trim().length > 0, "An explicit release label is required.");
  root = resolve(root);
  sourceRoot = resolve(sourceRoot);
  const index = readIndex(root);
  const target = join(root, "public", "releases", id);
  assert(!existsSync(target) && !index.releases.some(entry => entry.id === id), `Refusing to overwrite release ${id}.`);
  assert(kind !== "baseline" || index.releases.length === 0, "A baseline can only be the first archived snapshot.");
  assert(kind !== "release" || index.releases.length > 0, "Capture a baseline before creating a reviewed-workflow release.");
  if (index.releases.length) verifyReleases({ root });

  const data = {};
  const payloads = [];
  function add(path, bytes, role, sourcePath, recordCount) {
    const buffer = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes);
    payloads.push({ path, buffer, role, ...(sourcePath ? { source_path: sourcePath } : {}),
      ...(recordCount !== undefined ? { records: recordCount } : {}) });
  }
  for (const name of DATASETS) {
    const sourcePath = `src/${name}.json`;
    const bytes = readFileSync(join(sourceRoot, sourcePath));
    data[name] = JSON.parse(bytes);
    const rows = rowsOf(data[name]);
    assert(Array.isArray(rows), `${name}: expected an array of records.`);
    add(`data/${name}.json`, bytes, "data", sourcePath, rows.length);
    add(`data/${name}.csv`, buildRecordsCSV(rows), "raw_csv", undefined, rows.length);
  }
  validateData(data);
  let metadata;
  const metadataPath = join(sourceRoot, "src", "evidence_metadata.json");
  if (existsSync(metadataPath)) {
    const bytes = readFileSync(metadataPath);
    metadata = JSON.parse(bytes);
    add("data/evidence_metadata.json", bytes, "metadata", "src/evidence_metadata.json");
  }
  let requiredReviewIds = [];
  if (kind !== "baseline") {
    assert(metadata, "A release requires src/evidence_metadata.json.");
    const previous = join(root, "public", "releases", index.current_release_id, "data");
    const validation = validateMetadataRelease({
      papers: [...rowsOf(data.papers), ...rowsOf(data.creativity_papers)],
      estimates: [...rowsOf(data.estimates), ...rowsOf(data.creativity_estimates)],
      previousEstimates: [...readJSON(join(previous, "estimates.json")), ...readJSON(join(previous, "creativity_estimates.json"))],
      metadata,
    });
    assert(validation.valid, "New or revised estimate metadata is incomplete:\n" + validation.errors.join("\n"));
    requiredReviewIds = validation.requiredReviewIds;
  }
  add("exports/learning-estimates.csv", buildEstimatesCSV(data.estimates, data.papers, {
    releaseId: id, releaseDate: date, selection: { scope: "full", dataset: "learning" }, metadata,
  }), "joined_learning_csv", undefined, data.estimates.length);

  for (const sourcePath of CODE_PATHS) {
    if (existsSync(join(sourceRoot, sourcePath))) add(`code/${sourcePath}`, readFileSync(join(sourceRoot, sourcePath)), "code", sourcePath);
  }
  // These exact tools created the CSVs/manifest, including when the baseline
  // application was frozen before release tooling existed.
  for (const tool of ["scripts/release.mjs", "src/export.mjs", "src/shared.mjs", "src/evidence-metadata.mjs"]) {
    add(`snapshot-tools/${tool}`, readFileSync(join(ROOT, tool)), "snapshot_tool");
  }
  const counts = countsOf(data);
  const manifest = {
    schema_version: SCHEMA_VERSION, id, date, label, kind, description,
    previous_release_id: index.current_release_id,
    counts,
    source_review: {
      status: kind === "baseline" ? "baseline_not_retrospectively_verified" : "record_level_status_in_metadata",
      note: "The release date records this archive, not the original extraction date or a verified historical paper version. Unchanged legacy records remain unreviewed unless their annotations say otherwise. Free-text source and derivation notes are preserved.",
      newly_reviewed_estimate_ids: requiredReviewIds,
    },
    reproducibility: {
      scope: "Frozen website data plus calculation, filtering, export and build source available at capture.",
      raw_csv: "Raw CSVs preserve stored fields. Object/array cells use JSON. Null and absent fields are empty CSV cells; use JSON for a lossless distinction. Creativity theme order remains in creativity_papers.json.",
      joined_learning_csv: "The shared export joins study fields, derives missing CI limits using the captured ciOf helper, and appends metadata and release context. No filtering is applied.",
      limitations: "Underlying research workbooks, analysis outputs, PDFs and historical paper versions are not bundled or retrospectively verified. This archive reproduces website calculations from its frozen JSON, not extraction from primary documents.",
      restore: "Copy archived data and code files to each manifest source_path in a separate directory. Install with npm ci using the archived package-lock.json. Snapshot tools record the exact CSV generator. Do not overwrite a live checkout to reproduce an older release.",
    },
    files: payloads.map(({ buffer, ...file }) => ({ ...file, bytes: buffer.length, sha256: digest(buffer) })),
  };
  const manifestBytes = jsonBytes(manifest);
  const basePath = `/releases/${id}`;
  const downloads = Object.fromEntries(DATASETS.map(name => [name, {
    json: `${basePath}/data/${name}.json`, csv: `${basePath}/data/${name}.csv`,
  }]));
  downloads.estimates.raw_csv = downloads.estimates.csv;
  downloads.estimates.csv = `${basePath}/exports/learning-estimates.csv`;
  if (metadata) downloads.evidence_metadata = { json: `${basePath}/data/evidence_metadata.json` };
  const entry = {
    schema_version: SCHEMA_VERSION, id, date, label, kind, base_path: basePath,
    manifest_path: `${basePath}/manifest.json`, manifest_sha256: digest(manifestBytes),
    index_path: "/releases/index.json", counts, downloads,
  };
  mkdirSync(dirname(target), { recursive: true });
  mkdirSync(target); // Exclusive: a release directory is never reused or overwritten.
  for (const { path, buffer } of payloads) {
    const destination = safePath(target, path);
    mkdirSync(dirname(destination), { recursive: true });
    writeFileSync(destination, buffer, { flag: "wx" });
  }
  writeFileSync(join(target, "manifest.json"), manifestBytes, { flag: "wx" });
  verifyRelease(root, entry);
  atomicJSON(join(root, "public", "releases", "index.json"), {
    schema_version: SCHEMA_VERSION, current_release_id: id, releases: [entry, ...index.releases],
  });
  atomicJSON(join(root, "src", "release.json"), entry);
  return entry;
}

function main(argv) {
  const [command, ...arguments_] = argv;
  if (!command || command === "--help" || command === "help") {
    console.log("Usage:\n  node scripts/release.mjs create --id ID --date YYYY-MM-DD --label TEXT [--kind release|baseline] [--description TEXT] [--source-root PATH]\n  node scripts/release.mjs verify [--id ID]\n  node scripts/release.mjs check\n\nCreate is explicit and refuses existing IDs. verify checks archive integrity. check also requires current data, metadata and captured source to match the active release. Builds never create or date releases.");
    return;
  }
  assert(["create", "verify", "check"].includes(command), `Unknown command: ${command}`);
  const options = {};
  const allowed = command === "create" ? new Set(["id", "date", "label", "kind", "description", "source-root"]) : new Set(command === "verify" ? ["id"] : []);
  for (let i = 0; i < arguments_.length; i += 2) {
    const name = arguments_[i].replace(/^--/, "");
    assert(arguments_[i].startsWith("--") && allowed.has(name), `Unknown option: ${arguments_[i]}`);
    assert(arguments_[i + 1] !== undefined && !arguments_[i + 1].startsWith("--"), `Missing value for ${arguments_[i]}`);
    assert(!Object.hasOwn(options, name), `Repeated option: ${name}`);
    options[name] = arguments_[i + 1];
  }
  if (command === "create") {
    const entry = createRelease({ ...options, sourceRoot: options["source-root"] || ROOT });
    console.log(`Created ${entry.id} (${entry.date}): ${entry.counts.learning_papers} learning studies, ${entry.counts.learning_estimates} learning estimates; ${entry.counts.creativity_papers} creativity studies, ${entry.counts.creativity_estimates} creativity estimates.`);
  } else {
    const entries = verifyReleases({ id: options.id, current: command === "check" });
    console.log(`Verified ${entries.length} immutable release(s)${command === "check" ? "; current data, metadata and captured source match the active release" : ""}.`);
  }
}

if (process.argv[1] && pathToFileURL(realpathSync(process.argv[1])).href === import.meta.url) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(`Release error: ${error.message}`); process.exitCode = 1; }
}
