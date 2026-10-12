# Creativity data: source files and builder

Phase 2 of the creativity plan (`C:/Dropbox/claude-config/plans/polished-sauteeing-elephant.md`). The rules are in `docs/creativity-codebook.md`; the Review 1 decisions are in its section 13.

## Pipeline

1. **Extraction** (`docs/creativity-screening/tools/codex_extract.py`). For each paper: two independent extractions, a reconciliation against the PDF, a script that checks every number against its quote and every quote against the cited PDF page, a verifier, and a fixer when needed. The extractors transcribe printed numbers only; they never compute.
2. **Source files** (`docs/creativity-screening/tools/make_sources.py`). One file per paper, `code/creativity/papers/<paper_key>.json`, built from the reconciled extraction, the citation record, and the screening form. `status` is `verified` when the extraction chain ended with no open problem, and `draft` otherwise.
3. **Builder** (`scripts/build-creativity.mjs`, Node). Reads every source file, validates it, computes the standardized effects, and writes `creativity_papers.json`, `creativity_estimates.json`, and `creativity_metadata.json`. Draft files are validated and not emitted. `--check` rebuilds in memory and fails if the written files differ. During Phase 2 the outputs go to `code/creativity/build/`, and no file that `scripts/release.mjs` captures changes, so the site and the active release stay as they are. Phase 3 points the outputs at `src/`, merges `creativity_metadata.json` into the release gate, adds `scripts/creativity-smoke.mjs` to `npm test`, archives the two Python builders, and creates a new release.
4. **Posted data** (`docs/creativity-screening/tools/download_data.py`). Public participant-level deposits are downloaded to `D:/projects/ai-skill-atlas/creativity-data/`, with a manifest of URLs, sizes, and SHA-256 hashes. Statistics computed from posted data enter a source file as an `analysis_output` with the script that produced them.

## Source file

```json
{
  "schema": 1,
  "paper_key": "doshi_hauser_2024",
  "cid": "c006",
  "status": "verified | draft",
  "paper": {
    "authors_short": "Doshi and Hauser",
    "authors_full": "Anil R. Doshi and Oliver P. Hauser",
    "year": 2024,
    "title": "",
    "venue": "",
    "doi": "10.xxxx/...",
    "url": "https://doi.org/...",
    "pdf_filename": "file name under public/pdfs once hosted (Review 1 Decision 6)",
    "version_read": "",
    "is_own_paper": false,
    "one_line_finding": "",
    "shared_samples": "other paper_keys that analyze the same participants, or null"
  },
  "provenance": {
    "source_document": "PDF file name",
    "source_url": "https://doi.org/...",
    "source_version": "version and SHA-256 of the PDF read",
    "extraction_date": "YYYY-MM-DD",
    "review_date": "YYYY-MM-DD",
    "review_basis": "primary_source",
    "checked_by": "the extraction chain, e.g. two Codex extractors, a reconciler, a verifier",
    "statement": "Extracted and checked by Codex jobs (gpt-6-astra) against the source PDF; not yet verified by a human research assistant."
  },
  "studies": [ "the reconciled extraction's studies, each with sample_id = <paper_key>__<study_id lowercased>" ],
  "estimates": [ "the reconciled extraction's estimates (slug, stats, sources, ...), plus optional primary_override: true | false" ],
  "not_extracted": [],
  "open_items": [],
  "chain": { "verify_problems": 0, "fixes": 0, "reverify_problems": 0 }
}
```

## What the builder computes

For every estimate, `estimate_id = <paper_key>__<slug>`. The sign `s` comes from `higher_is`: +1 for `more_creative`, `more_diverse`, `more_ideas`, and `more_accurate`; −1 for `less_creative` and `more_similar`; no effect is computed for `other`.

**Diversity outcomes** (construct `diversity`, any question; Review 1 Decision 3) are never converted. The output keeps both arm levels, the difference, the paper's uncertainty, the unit, and a direction: `less_alike` when `s × (treatment − control) > 0`, `more_alike` when it is below 0, each followed by `clear` when the printed 95 percent interval of the difference excludes 0, the printed p-value is below 0.05, or a printed estimate divided by its printed standard error is at least 1.96 in absolute value, and `no_clear_difference` otherwise; `not_tested` when the paper prints neither. `effect_size_sd`, `se`, `ci_lower`, and `ci_upper` stay null.

**Other outcomes.** The standardizer follows codebook section 9, first available:

1. `control_sd` with `sd_level` `participant`: d = s × Δ / SD_control.
2. The pooled participant-level SD of both arms, sqrt(((n1 − 1) SD1² + (n0 − 1) SD0²) / (n1 + n0 − 2)): d = s × Δ / SD_pooled.
3. The paper's own d or g, when `paper_effect.standardizer` names the control or the pooled participant-level SD and its printed sign matches the sign of Δ (both run treatment minus control): d = s × the paper's value.
4. A regression on a standardized outcome (`regression.outcome_scale` `standardized`): d = s × coefficient.
5. Last resort, flagged `standardizer: output_level_sd`: the same as 1 or 2 with SDs computed over outputs or ratings (codebook section 9, last paragraph).

Δ is the regression coefficient when one is printed in raw units, otherwise the printed difference, otherwise treatment mean minus control mean.

The standard error of d, first available: (a) the regression coefficient's SE divided by the same SD; (b) `difference_se` divided by the SD; (c) a printed 95 percent interval of the difference, (upper − lower) / 3.92, divided by the SD; (d) for a two-group or paired t statistic of Δ (no regression printed): |Δ| / |t| divided by the SD; (e) for a between-person contrast with both counts: sqrt((n1 + n0) / (n1 n0) + d² / (2 (n1 + n0))). A paired within-person contrast never uses (e). `ci_lower` and `ci_upper` are d ± 1.96 SE.

**Pooling** (`eligible`, `pooled`, `not_pooled_reason`). `pooled` is true only for the primary record of its pool key when it is eligible. A record is eligible only if d and SE are finite, `se_basis` is `participant` or `cluster`, the construct is not `convergent` (Decision 13) or `other`, the standardizer is not `output_level_sd`, and, when the study randomized clusters, `se_basis` is `cluster` (Decisions 4 and 9). Paired within-person records are pooled and flagged `within_person: paired`, so the site can show results with and without them (Decision 11).

**Primary records** (codebook section 8). Per pool key (`sample_id`, `question`, `comparison_type`), exactly one record is primary: the preregistered primary outcome; otherwise, for `with_ai` and `after_ai`, overall creativity rated by people, then novelty rated by people, then an automated creativity score; for `across_people`, the paper's main similarity measure. Among AI arms that share a control, the arm closest to free chatbot use wins, then the paper's contrast of all AI arms combined. `primary_override` in the source file settles the ties that remain, with a recorded reason; the builder lists every unresolved tie in one run. Convergent outcomes are never primary.

**Derivation notes.** Each estimate's `derivation_notes` states the formula and the numbers that entered it, and the locators of those numbers, in plain text.

## Outputs

- `creativity_estimates.json`: one row per emitted estimate with the learning section's names (`estimate_id`, `paper_key`, `study_label`, `effect_size_sd`, `se`, `ci_lower`, `ci_upper`, `outcome`, `outcome_timing`, `n_treatment`, `n_control`, `n_total`, `treatment`, `control`, `notes`, `is_own_paper`, `comparison_type`, `outcome_with_ai`, `is_subgroup` false, `design_class`) and the creativity fields (`question`, `construct`, `measure`, `unit`, `n_units`, `task_type`, `ai_role`, `ai_tool`, `sample_id`, `is_primary`, `pooled`, `not_pooled_reason`, `se_basis`, `within_person`, `standardizer`, `raw` with both arm levels and the paper's own statistics, `direction` for diversity records).
- `creativity_papers.json`: one row per emitted paper.
- `creativity_metadata.json`: the release-gate annotations (`studies` and `estimates`, schema of `src/evidence-metadata.mjs`), with `review_basis` `primary_source` (or `analysis_output` for numbers computed from posted data) and the provenance statement above. In Phase 3, `scripts/release.mjs` merges it with `src/evidence_metadata.json` before the gate.
