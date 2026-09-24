// Real snapshots and real data, isolated in a temporary directory. No release
// is created in the repository by these checks.
import assert from "node:assert/strict";
import { copyFileSync, cpSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRelease, verifyReleases } from "./release.mjs";
import { buildEstimatesCSV, buildRecordsCSV } from "../src/export.mjs";
import { ciOf } from "../src/shared.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fixture = mkdtempSync(join(tmpdir(), "atlas-release-test-"));
const readJSON = path => JSON.parse(readFileSync(path, "utf8"));
mkdirSync(join(fixture, "public"));
mkdirSync(join(fixture, "src"));
cpSync(join(root, "public", "releases"), join(fixture, "public", "releases"), { recursive: true });
copyFileSync(join(root, "src", "release.json"), join(fixture, "src", "release.json"));

const original = verifyReleases({ root: fixture });
assert.ok(original.length >= 1);
const existing = original[0];
assert.throws(() => createRelease({ root: fixture, id: existing.id, date: "2026-09-23", label: "Duplicate" }), /overwrite/);
assert.throws(() => createRelease({ root: fixture, id: "../escape", date: "2026-09-23", label: "Unsafe" }), /Release ID/);
assert.throws(() => createRelease({ root: fixture, id: "bad-date", date: "2026-02-30", label: "Invalid" }), /Invalid release date/);
assert.throws(() => createRelease({ root: fixture, id: "missing-date", label: "Invalid" }), /explicit YYYY-MM-DD/);

const entry = createRelease({ root: fixture, sourceRoot: root, id: "isolated-release-test", date: "2026-09-23", label: "Isolated release test" });
const manifest = readJSON(join(fixture, "public", "releases", entry.id, "manifest.json"));
assert.equal(manifest.previous_release_id, existing.id);
assert.ok(Array.isArray(manifest.source_review.newly_reviewed_estimate_ids));
// Restore only the files needed for exact current-source checks, from the
// captured snapshot rather than a checkout another agent could be changing.
for (const file of manifest.files.filter(file => file.source_path)) {
  const destination = join(fixture, file.source_path);
  mkdirSync(dirname(destination), { recursive: true });
  copyFileSync(join(fixture, "public", "releases", entry.id, file.path), destination);
}
assert.equal(verifyReleases({ root: fixture, current: true }).length, original.length + 1);

const papers = readJSON(join(root, "src", "papers.json"));
const estimates = readJSON(join(root, "src", "estimates.json"));
assert.equal(entry.counts.learning_papers, papers.length);
assert.equal(entry.counts.learning_estimates, estimates.length);
const metadata = readJSON(join(root, "src", "evidence_metadata.json"));
const csv = buildEstimatesCSV(estimates, papers, {
  releaseId: entry.id, releaseDate: entry.date, selection: { scope: "full", dataset: "learning" }, metadata,
});
assert.equal(readFileSync(join(fixture, "public", "releases", entry.id, "exports", "learning-estimates.csv"), "utf8"), csv);
assert.ok(csv.includes("study_sample_review_basis"));
assert.ok(csv.includes("provenance_review_status"));
assert.ok(csv.includes("release_id,release_date,view_url,selection"));
assert.equal(buildRecordsCSV([{ a: 'one,"two"', b: "line1\nline2", c: null }]), 'a,b,c\n"one,""two""","line1\nline2",');

// Every original browser-export field retains its meaning. This includes
// notes and stored intervals, and the original normal-CI fallback.
const paper = papers.find(p => p.paper_key === estimates[0].paper_key);
const oneCSV = buildEstimatesCSV([estimates[0]], [paper]);
const interval = ciOf(estimates[0]);
assert.ok(oneCSV.includes(String(interval.lo)));
assert.ok(oneCSV.includes(String(interval.hi)));
assert.equal(estimates[0].notes, readJSON(join(fixture, "public", "releases", entry.id, "data", "estimates.json"))[0].notes);

const currentPath = join(fixture, "src", "estimates.json");
const originalBytes = readFileSync(currentPath);
const normalizedText = originalBytes.toString("utf8").replace(/\r\n/g, "\n");
writeFileSync(currentPath, normalizedText);
verifyReleases({ root: fixture, current: true });
writeFileSync(currentPath, normalizedText.replace(/\n/g, "\r\n"));
verifyReleases({ root: fixture, current: true });
writeFileSync(currentPath, originalBytes);
const revised = JSON.parse(originalBytes);
revised[0].notes = `${revised[0].notes || ""} Release-gate test only.`;
writeFileSync(currentPath, JSON.stringify(revised));
assert.throws(() => verifyReleases({ root: fixture, current: true }), /current src\/estimates.json differs/);
const metadataPath = join(fixture, "src", "evidence_metadata.json");
const originalMetadataBytes = readFileSync(metadataPath);
const missingReview = JSON.parse(originalMetadataBytes);
delete missingReview.estimates[revised[0].estimate_id];
writeFileSync(metadataPath, JSON.stringify(missingReview));
assert.throws(() => createRelease({ root: fixture, sourceRoot: fixture, id: "unreviewed-change", date: "2026-09-23", label: "Must fail" }), /New or revised estimate metadata is incomplete/);
writeFileSync(currentPath, originalBytes);
writeFileSync(metadataPath, originalMetadataBytes);

const archivePath = join(fixture, "public", "releases", entry.id, "data", "estimates.json");
const archiveBytes = readFileSync(archivePath);
writeFileSync(archivePath, Buffer.concat([archiveBytes, Buffer.from(" ")]));
assert.throws(() => verifyReleases({ root: fixture }), /integrity check failed/);
writeFileSync(archivePath, archiveBytes);
verifyReleases({ root: fixture, current: true });
console.log(`Release smoke passed: ${estimates.length} real learning rows; immutable snapshots, CSV context/notes, metadata gate, portable source hashes, current-source mismatch and corruption detection.`);
console.log(`Isolated test files retained at ${fixture}`);
