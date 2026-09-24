# Integrating treatment-effect heterogeneity

Proposal dated September 23, 2026. This document recommends a data contract and user interface. It does not implement the feature or change the extraction files.

## Recommendation

Start with a coverage matrix and a heterogeneity panel on each paper. Publish verified subgroup effects, interaction estimates, and tests as distinct forms of evidence. Add plots within a paper where outcomes and units match. A pooled moderator effect should be a later, separate analysis with an explicit estimand and a method for dependent estimates.

This approach uses the existing extraction work while showing what each paper actually reports. It also makes missing coverage visible. A blank extraction file, an unreviewed paper, and an imprecise interaction answer different questions.

## Inventory checked against the repository

The learning collection has 35 papers and 139 estimates. The `code/heterogeneity/` directory contains 24 JSON files, all dated September 1, 2026. Sixteen files contain records and eight contain an empty `records` array. The extraction prompt asks for nine participant characteristics and a separate category for other characteristics.

| Property | Count |
| --- | ---: |
| Extraction records | 561 |
| Split-sample records | 193 |
| Interaction records | 319 |
| Continuous-moderator records | 37 |
| Quantile records | 12 |
| Records with a numeric effect | 320 |
| Records with an SE | 197 |
| Records with both confidence limits | 52 |
| Records marked approximate | 97 |
| Records linked to an existing parent estimate | 415 |
| Records linked to an existing atlas duplicate | 20 |
| Records labeled preregistered / exploratory / unclear | 38 / 249 / 274 |

These are counts of extraction fields, not counts of verified causal effects. The uncertainty counts can overlap. All record IDs are unique. Every nonnull `parent_estimate_id` and `already_in_atlas` value resolves to a current learning estimate. The 20 duplicate links are distinct: 19 point to rows flagged `is_subgroup` and one to a main quantile estimate. The new pipeline should preserve those links and display each effect once.

Eleven papers have no extraction file: `ba_etal_2024`, `bassner_etal_2026`, `dai_etal_2025`, `fischer_etal_2025`, `gan_etal_2024`, `hou_etal_2026`, `huang_etal_2025`, `kavadella_etal_2024`, `learnlm_team_2026`, `stromberg_etal_2026`, and `franco_etal_2026`. Show them as **not yet reviewed**, rather than inferring that their papers did not examine heterogeneity.

The current checklist counts are below. “Reported” retains the extraction files' broad definition, which includes some p-values without effect estimates. These counts therefore need review before use as public claims.

| Characteristic | Reported | Tested, no numbers | Not examined | Difference test reported |
| --- | ---: | ---: | ---: | ---: |
| Prior achievement | 13 | 1 | 10 | 7 |
| Age or grade | 6 | 1 | 17 | 2 |
| Gender | 5 | 0 | 19 | 3 |
| Prior AI experience | 4 | 0 | 20 | 3 |
| Socioeconomic status | 4 | 0 | 20 | 4 |
| Race or ethnicity | 2 | 0 | 22 | 2 |
| Field of study | 2 | 0 | 22 | 2 |
| Education level | 1 | 0 | 23 | 1 |
| Language | 1 | 0 | 23 | 0 |

Each row covers the 24 papers with extraction files. The last column is an additional flag, not another mutually exclusive status. Count papers when summarizing coverage. Lira alone contributes 218 records and Contractor and Reyes contributes 125, so record counts would give a misleading picture of coverage across studies.

## Review findings and verification limits

The inventory above was recomputed from the JSON. Targeted source checks used existing markdown conversions. This was not a full re-extraction or an independent audit of all 561 records.

**Kestin: a correlation is stored as a moderator effect.** `kestin_etal_2025__het1` records a correlation of −0.2 between prior AI experience and post-test scores within the control condition. The local supplement markdown independently confirms this in the paragraph following Table S1. It reports no corresponding numeric correlation for the AI condition and no test of their difference. Move the record to contextual evidence and exclude it from treatment-effect plots. A within-arm correlation is not an interaction coefficient. Comparing whether two separate associations are statistically significant does not test whether they differ.

Source checked: `C:\Dropbox\Research\ai-learning\support_info\meta_analysis\markdown\Kestin et al (2025) - AI Tutoring Outperforms Active Learning - Supplement.md`, paragraph following Table S1, line 33.

**Lira: the 218 records report tests, not effect magnitudes.** All have a p-value and null effect, SE, and confidence limits. The local 2025 markdown independently confirms that the moderation tables report Benjamini–Hochberg-adjusted interaction p-values. Its first Pretest row matches the first extracted values, including 0.955 and 0.914. The extraction cites tables in the 2026 version and explains their renumbering. This check corroborates the evidence type and a sample row, not all cells or the current version's table locations. Preserve the results in a test table. Do not infer an effect direction or magnitude from the p-values. The extraction also leaves 72 Study 2 parent links null because the omitted treatment condition is unclear. Resolve the contrast before interpreting those tests as AI versus a particular control.

Source checked: `C:\Dropbox\Research\ai-learning\support_info\meta_analysis\markdown\Lira et al (2025) - Coach Not Crutch.md`, Section C6 and Table S13. The corresponding 2026 table is identified as S14 in the extraction's version note.

**Kumar: the available versions need review.** The files in `public/pdfs/` named as the 2023 preprint and the 2025 AIED paper have identical SHA-256 hashes. This independently confirms duplicate file content. It does not establish that the published version contains no new analyses. The extraction already assigns medium confidence because of this version issue. Keep that qualification visible until the publication is checked.

**Group means and participation outcomes need explicit fields.** The Nie extraction contains records with group means in notes but no computed difference. It also includes exam participation, which is distinct from learning conditional on assessment. The Shen and Tamkin extraction contains six figure records with null effects and approximate group means in notes. These are confirmed properties of the extraction files only. Preserve arm-level means separately and label outcome type. Any later derivation should retain its formula and source inputs.

**The legacy subgroup flag covers more than participant heterogeneity.** Of the 415 parent links, 104 point to rows flagged `is_subgroup`. This can be appropriate: `lira_etal_2025__sg2` is an AI-versus-Google comparison and `wiles_etal_2024__sg1` is a statistics-task outcome. Neither label defines a participant subgroup. Conversely, the existing Hausman 25th-percentile grade effect is a main row and one of the 20 duplicate links. Validate the underlying contrast and outcome instead of treating the legacy flag as the new evidence taxonomy.

**Adjusted p-values need their own metadata.** For example, Nie's low-HDI record stores an adjusted p-value of 0.680 alongside a confidence interval excluding zero. The source quotation in the extraction states that the unadjusted p-value is 0.045. A consistency check that assumes the interval and p-value use the same adjustment would flag the wrong issue. This example has not been independently checked against the paper during this review.

## Options

| Option | User value | Work required |
| --- | --- | --- |
| Coverage matrix and paper panels | Shows which characteristics were studied and makes individual results inspectable | Validate the extraction, resolve scope issues, add evidence types and provenance |
| Comparable plots within papers | Shows subgroup levels or interactions on a common axis | Add contrast IDs, outcome timing, units, reference groups, and uncertainty metadata |
| Cross-paper moderator synthesis | Estimates a defined average difference in AI effects | Select comparable estimands, harmonize scales, resolve dependent estimates, and specify the estimator |

Implement the first option, followed by the second for eligible records. Keep the third as a separate research task. A pooled result should not emerge automatically from filtering the extraction table.

## Proposed data contract

Keep the raw files unchanged and build a separate `src/heterogeneity.json`. Store paper review coverage separately from evidence records. Preserve raw fields and add derived display fields only through reproducible code.

| Field group | Required content |
| --- | --- |
| Identity and links | Stable `record_id`, `paper_key`, nullable `parent_estimate_id`, nullable `already_in_atlas`, and study/experiment identifier |
| Review coverage | `review_status`: `not_reviewed`, `needs_review`, or `reviewed`; explicit statuses for all nine characteristics |
| Evidence type | `effect_estimate`, `test_only`, `arm_summary`, `narrative_only`, or `contextual_association`; retain `estimate_type` separately |
| Contrast | Treatment and control, omitted treatment category, moderator reference group, category definition, and continuous-moderator scale |
| Outcome | Verbatim outcome, outcome family, timing, AI available during assessment, and whether the result concerns learning, performance, or participation |
| Numerical result | Raw effect and units, SE, confidence limits and level, subgroup and arm Ns, plus separate arm means where reported |
| Hypothesis test | Exact p-value or bound/operator, tested null, adjustment method, and correction family when stated |
| Difference test | Whether the paper tests differences in treatment effects across groups, with its statistic, p-value, adjustment, and location |
| Provenance | Paper version, source filename or URL, content hash, location, quotation, extraction date, review date, reviewer, and approximation flag |
| Derivations | Original inputs, formula, output units, and eligibility reason for any computed display value |
| Dependence | Paper, experiment, sample, outcome, and shared-control identifiers, plus relationship to overlapping records |

Use `not_examined` only after review. Add a checklist state for `test_only` so “reported with estimates” no longer includes a table of p-values alone. Preserve narrative tests without creating fictitious numerical effects. Keep categorical subgroup levels, interaction contrasts, continuous slopes, and quantile effects distinct. Quantile treatment effects are distributional effects and do not by themselves identify effects for people at the corresponding baseline quantile.

## Interface and statistical rules

The coverage matrix should show one cell per paper and characteristic, with text or a symbol for unreviewed, not examined, narrative/test only, and numerical evidence. A click opens the paper's evidence panel. Filters should operate on reviewed papers and show both the number reviewed and the number with results.

The paper panel should display the outcome, intervention contrast, subgroup definition, result, formal difference test, preregistration status, and source. A result for women and a result for men are subgroup levels. Their separate significance does not establish a gender difference. Display a reported interaction or equality test in its own column. Missing difference tests should say “Not reported.”

Plot only comparable quantities. Keep approximate figure readings visible as such. Do not combine SD effects, grade points, proportions, correlations, or slopes with different moderator scales. A raw-to-SD conversion requires an identified denominator and a recorded derivation. A null SE is not zero uncertainty.

Do not add subgroup rows to the main pooled estimate alongside their parent effects. The existing row-level DerSimonian–Laird helper has no study-clustering or covariance input. It is not suitable for pooling overlapping subgroup effects, repeated outcomes, shared-control contrasts, or adjusted interaction p-values. A later synthesis must choose its estimand, selection rule, and dependence adjustment before estimating a summary.

The September maintenance change makes subgroup exclusion unconditional in the shared primary-estimate filter and removes the dormant subgroup selector. The old selector was commented out, but its logic would have combined selected subgroups with parent effects if restored. The new feature should keep its own evidence view and preserve the primary-estimate exclusion.

## Implementation sequence and acceptance checks

1. Define the schema and source-version registry. Resolve the Kestin scope issue, Lira contrast/version questions, and Kumar publication version. Keep unresolved records available for review but out of quantitative summaries.
2. Review the eleven missing papers. Add explicit review entries even when no heterogeneity is reported. Do not generate a negative finding from a missing file.
3. Build a deterministic combined dataset. Preserve record IDs and raw values, deduplicate the 20 existing atlas links, and retain exclusions with reasons.
4. Add the coverage matrix, paper panels, and exports. Export review status, units, adjustment details, and source locations with the numerical results.
5. Add within-paper plots for eligible evidence. Consider cross-paper synthesis only after a separate statistical specification.

Checks should reject duplicate IDs, invalid paper/parent links, missing checklist dimensions, invalid enums, impossible numeric ranges, unexplained unit changes, and effect displays without a defined contrast. They should distinguish a reported confidence interval from a derived interval and check the stated confidence level. Tests should confirm that p-values retain adjustment metadata, unknown uncertainty stays unknown, unresolved evidence is labeled, and subgroup selection cannot alter the main pooled estimate by adding overlapping rows. Recomputed coverage counts should match the exported dataset and the visible matrix.
