# The AI and Human Skill Atlas

A living atlas of evidence on how generative AI affects human skill formation. The default view shows randomized experiments on learning. Observational studies are available through the Design filter. The atlas builds on the meta-analysis in Contractor & Reyes (2026).

Live: https://aiskillatlas.org/ (previously germanr.github.io/ai-skill-atlas, which now redirects)

## Stack

- React 19 + Vite 8 single-page app
- Inline CSS-in-JS (no Tailwind, no separate CSS files)
- Design system: "evidence journal" — warm paper/ink palette, hairline rules, Newsreader (display serif) + IBM Plex Sans/Mono (UI and data), via Google Fonts
- Data pipeline: Excel, CSV, Stata results, and coded metadata → JSON via Python

## Local development

```powershell
Set-Location C:\Dropbox\Admin\website\ai-skill-atlas
npm install
npm run dev
```

Opens at `http://localhost:5175/`. Vite selects another port if 5175 is busy. Run `npm test` for data, URL-state, and metadata checks. `npm run build` first checks that the data and captured source match the active release. Development does not require creating a new release after every edit.

For browser regression checks, install Chromium once and run:

```powershell
npx playwright-core install chromium
npm run test:browser
```

The browser checks start and stop their own local server. Set `ATLAS_TEST_URL` to test an existing server, or `ATLAS_CHROMIUM_PATH` to use a specific Chromium executable. GitHub Pages deployment runs both the data checks and the browser checks before building.

## Updating data

The learning builder reads these inputs:

- `C:\Dropbox\Research\ai-learning\support_info\meta_analysis\meta_analysis.xlsx`: source estimate rows.
- `C:\Dropbox\Research\ai-learning\support_info\meta_analysis\literature_effects.csv`: curated estimates, which override matching effect sizes and SEs.
- `code/sources/contractor-reyes-2026-09.json`: nine Contractor and Reyes estimates pinned to the September 2026 PDF and matching regression output, with source hashes and outcome-specific counts. The builder does not read the live research regression file.
- `code/audit/bassner_gain_precision.csv`: gain effects and SEs calculated in Stata from the pinned three-arm statistics in `code/audit/bassner_arm_statistics.csv`.
- `code/build_website_data.py`: paper metadata, summaries, verified corrections, exclusions, additional estimates, and classification rules.
- `code/estimand_method.json`: estimation-method and estimand labels, keyed by estimate ID.

`papers_for_website.xlsx` is an output, not an input. The builder overwrites its `papers` and `estimates` sheets, along with `src/papers.json` and `src/estimates.json`. Edits made only to that workbook or to generated JSON will not survive a rebuild.

After changing the relevant inputs, run:

```powershell
Set-Location C:\Dropbox\Admin\website\ai-skill-atlas
python code/build_website_data.py --json-only
npm run social:generate
npm test
npm run build
```

Review the generated diff and build output before publishing. `--json-only` leaves the research workbook unchanged. Use `--output-dir` with a temporary directory for a preview before replacing the website JSON. Check the builder's research-input paths before running on another machine. The Contractor and Reyes source extraction is pinned inside the website repository so a research rerun cannot silently mix new effects with old PDF versions or sample counts.

The build command above will refuse unarchived data or calculation/interface changes. Complete the metadata review and create a release as described below before the final production build. During implementation, `npx vite build` can check compilation without declaring a release. Do not use that shortcut for publication.

The creativity collection uses separate builders: `code/creativity_estimates_raw.py` writes `src/creativity_estimates.json`, and `code/build_creativity_data.py` writes `src/creativity_papers.json` from inline metadata and counts the extracted outcomes. The creativity page remains a preview at `?section=creativity`.

## Adding a new paper

1. Append the paper's estimate rows to `meta_analysis.xlsx`. Preserve existing row order: generated estimate IDs use the source row index, and correction tables refer to those IDs.
2. Add the paper's metadata, design classification, summary, and any needed corrections to `code/build_website_data.py`. Add curated estimates to `literature_effects.csv` and the builder's matching rules when appropriate. Add estimand and method labels to `code/estimand_method.json`.
3. Add the PDF to `public/pdfs/`, using the filename in the paper metadata. Use a new filename for a revised document so older release records keep their original source.
4. Add source and sample annotations to `src/evidence_metadata.json`. Rebuild, run the checks above, and inspect the new paper, estimates, units, links, and counts.
5. Create a new release, verify it, and run the production build. Commit and push to `main` only when ready to publish.

Paper cards do not display study images, so new papers do not need one. The historical `image_filename` field is optional legacy metadata. The PDF and site social-preview image remain required assets.

Do not use `code/patch_subgroups.py` as a routine update command. It appends rows to the current JSON without checking for duplicate IDs and can reintroduce rows excluded by the main builder.

The proposed integration of the existing heterogeneity extractions is described in [the September 2026 proposal](docs/heterogeneity-proposal-2026-09-23.md). Those files are not yet part of the application data pipeline.

## Shareable views and outcome timing

Filters, search, chart/table choice, and both sort orders are stored in the URL. “Copy view link” opens the same selection on another device, including the chosen chart/table view. If clipboard access fails, a selectable link appears. Browser Back/Forward and returning from a study preserve the selection. Invalid URL values fall back to valid choices with a notice. Filter changes replace the current history entry rather than adding one entry per keystroke.

“All timings / Immediate / Delayed” uses the existing `outcome_timing` field. It changes the chart, table, study cards, counts, and filtered export. It does not change the default headline pooled estimate. Timing and AI availability during assessment remain separate filters. Differences between immediate and delayed subsets do not identify learning decay. No timing classifications were changed in this implementation; unresolved source questions are in `evidence_metadata.json` under `timing_audit`.

A shared view always uses the current dataset. It is not a frozen result. Exports record the release ID, release date, and filter selection. Full exports explicitly identify their full-dataset scope.

## Sample definitions and source metadata

`src/evidence_metadata.json` is a durable annotation file, not builder output. It separates study participants from each estimate's observations, specifies units, and records source-document versions, locations, review dates, and derivations. The resolvers in `src/evidence-metadata.mjs` leave missing definitions unreviewed. They never assume that `n_total` counts people.

The annotations distinguish LearnLM's 165 students from its session-level endpoints. Contractor and Reyes has 256 assigned students, 211 Session One attendees, and outcome-specific analyzed samples. The September test estimates use 210 and 205 students. Source checks and calculation details are recorded for the corrected estimates; unreviewed legacy fields remain marked as such. The aggregate participant headline and mixed-unit sample-size sort have been removed. No claim about unique participants across studies is made.

## September 23 numerical corrections

The corrected collection excludes Kalam under the stated minimum of 50 participants: its whole trial randomized 33. The previous release retains its records. Franco's verified raw coefficients remain available, but its unverified SD conversion is no longer displayed or pooled. Henkel retains the reported effect without the unsupported individual-level SE for a school-randomized trial. Two Lehmann subgroup intervals remain unavailable because the required covariance is not reported.

Other corrections cover Lira's SE, Lehmann's method labels, Liu's effect direction and reported interval, domain classifications, sample counts, and study summaries. Bassner's gain estimates now use observed within-person gain variances and full-precision arm statistics. Its SE treats the pooled pretest SD as fixed, an explicit approximation. Contractor and Reyes uses the September PDF and nine matching regression rows. The accuracy endpoint uses regression N=196; its notes disclose that the PDF appendix prints a shared N=198 line.

`npm test` includes source-specific regression checks. The social card is generated from `scripts/social-card.html` and current counts. `npm run social:check` rejects a stale card or changed image. Regenerate it after count or template changes with `npm run social:generate`.

New or revised estimate rows require an explicit sample definition and reviewed provenance before release creation. The validator compares rows with the previous archived data. It requires a supporting document or URL, an estimate-specific locator, review date, and derivation details. Missing facts such as an undated source version need a field-specific explanation. Local-coding checks alone do not satisfy the review gate for new/revised estimates. Unchanged legacy rows can retain their documented missing fields while the audit continues. All supplied annotations are checked for valid counts, units, IDs, and statuses.

Approved wording-only changes to an existing estimate's `notes` can use an exact receipt in `code/audit/editorial-reviews.json`. Each receipt names the previous release and estimate ID, records the exact old and new notes, and explains the edit. Every other field must remain identical. A receipt cannot exempt a new estimate, an unapproved notes edit, or changes to numbers, samples, classifications, or source fields. Editorial review does not verify a source, fill missing facts, or promote an unreviewed record. The release archives the receipt ledger and reports editorial changes separately from source reviews. Older receipts cannot approve changes against a different previous release.

## Creating and checking releases

`public/releases/2026-09-23-baseline/` preserves the data and available calculation/interface source captured before this implementation. It is not a reconstructed July release. Each subsequent release stores all four raw JSON collections, raw CSVs, the joined learning CSV, metadata, captured source, and a SHA-256 manifest. Source PDFs, research workbooks, and analysis outputs are not bundled. This preserves website calculations from their JSON inputs, not the entire research extraction workflow.

Finish and test changes before creating a release. Use a new ID every time, even for a same-day correction. Replace the example ID and date below with the release you are actually creating:

```powershell
npm test
npm run test:browser
node scripts/release.mjs create --id 2026-09-23.2 --date 2026-09-23 --label "Source-audited corrections, Kalam exclusion, and September paper update"
npm run release:verify
npm run release:check
npm run build
```

Creation refuses to overwrite an existing release. Ordinary builds never change the release date. `release:verify` checks archive integrity; `release:check` also checks current data, metadata, and captured source against the active snapshot. If a checked file changes after release creation, create another release after review. Do not edit an archive to make a check pass.

`src/release.json` points to the active release. `public/releases/index.json` lists the archive. Both feed the About page, dates, citations, and downloads. Archive bytes are exempt from Git line-ending conversion through `.gitattributes`. Current-source checks accept CRLF/LF differences but reject substantive changes. The historical files and manifests remain byte-checked.

To inspect an old calculation, use its archived data and helpers in a separate directory. Historical interactive browsing is not implemented. See the manifest's reproduction notes for dependencies and limits.

## Deployment

GitHub Pages via `.github/workflows/deploy.yml`. Push to `main` triggers a build.

## Repo layout

```
ai-skill-atlas/
├── ai-skill-atlas-explorer.jsx     # main React component
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx
│   ├── shared.mjs              # data helpers shared with tests
│   ├── papers.json             # generated learning metadata
│   ├── estimates.json          # generated learning estimates
│   ├── creativity_papers.json
│   └── creativity_estimates.json
├── public/
│   ├── images/                  # social preview and legacy study images
│   └── pdfs/                    # one .pdf per paper
├── code/
│   ├── build_website_data.py   # learning pipeline
│   ├── build_creativity_data.py
│   ├── creativity_estimates_raw.py
│   └── heterogeneity/          # extraction drafts, not yet integrated
├── scripts/
│   ├── smoke.mjs
│   └── browser-smoke.mjs
├── docs/
└── .github/workflows/deploy.yml
```
