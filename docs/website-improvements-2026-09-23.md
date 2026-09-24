# Website improvements, 23 September 2026

## Implementation status

The minimum versions of the four priorities below are now implemented locally: explicit release snapshots and source-review fields, sample-unit labels without an aggregate participant count, shareable filters, and an immediate/delayed filter. The original effect estimates and timing classifications are unchanged. LearnLM and Contractor–Reyes sample definitions were checked against existing local coding; a full primary-source audit remains pending. Mixed-unit sample-size sorting was removed. Historical interactive views, exact follow-up bands, cross-paper sample deduplication, and production heterogeneity integration remain deferred. See the README for the release and review workflow. These changes have not been published.

The decision guide below records the original scope and tradeoffs. Statements describing the old interface refer to the state before this implementation.

The next improvements should make results easier to share, trace to their sources, and interpret. Preserve the current restrained visual style. The forest-plot, filter, count, and deployment repairs are part of the current maintenance work; the proposals below extend that work.

## Ranked proposals

Effort is relative: **small** means a contained UI change, **medium** crosses several components or data fields, and **large** needs source review or a methodological choice. Value describes the expected benefit to a reader, not a measured effect.

| Rank | Proposal | Value | Effort | Concrete result |
| --- | --- | --- | --- | --- |
| 1 | Share the current evidence view | High | Medium | Encode filters, search, chart/table choice, and sort order in the URL. Add a copy-link control. Opening a study and returning should preserve the view. A fresh browser should reproduce the same selected records. |
| 2 | Show data provenance and release dates | High | Medium | Generate the update date from a release manifest. Record the source version, coding date, source page/table, and effect-size derivation for each estimate. Make previous data releases downloadable, with an explicit release identifier in citations and exports. |
| 3 | Make heterogeneity explorable without changing the primary pooled result | High | Large | Add a separate heterogeneity view organized by study and moderator. Distinguish participant subgroups from alternative outcomes, specifications, and treatment contrasts. Show within-study comparisons and their uncertainty. Add cross-study summaries only where the contrasts and their dependence are documented. |
| 4 | Resolve scope and denominator labels | High | Medium | State whether each sample size counts people, sessions, enrollments, or observations. Explain differences between recruited and analyzed samples. Reconcile the stated inclusion threshold with existing records, and distinguish countries from multi-country setting labels. |
| 5 | Complete screen-reader and motion support | High | Small to medium | Build on the repaired focus and anchor navigation. Give view/sort controls an announced selected state, use consistent semantics for single-choice filters, and support reduced motion. |
| 6 | Make outcome timing easier to compare | High | Medium | Add an immediate/delayed filter using the existing timing field, then add the actual follow-up interval where sources report it. Keep AI-free learning and AI-assisted performance visibly distinct. Give every filtered view a short, readable scope description. |
| 7 | Improve browsing at tablet and phone widths | Medium | Medium | Keep the table available by default on phones. At tablet widths, fit the plot to its container where labels remain readable, or make horizontal scrolling explicit. Offer an expanded row with outcome, interval, sample, and source details before opening the full study record. |
| 8 | Export a chart with its context | Medium | Medium | Download an SVG or PNG that includes the selected filters, axis range, number of studies and estimates, pooling method, release identifier, and site citation. Use the same plotting data as the on-screen chart. |
| 9 | Make source records easier to find and cite | Medium | Medium | Give each study a descriptive browser title and stable source/DOI link. Provide separate links for the publisher page and available PDF. Include DOI and URL fields in citations when verified. Add a clear fallback when clipboard access fails. |
| 10 | Put search beside the controls it affects | Medium | Small | Move or duplicate search into the evidence toolbar. It currently sits under “The studies” but changes the chart above it. Add clear-search behavior and visible search scope. Allow table sorting by effect, year, precision, and study. |

## Decision guide for the four priorities

These four changes remain proposals. The recent repairs already distinguish matching, plotted, and pooled records and restore focus after study navigation. They do not add shareable filters, archived releases, sample-unit fields, or timing filters.

### 1. Shareable filters

Today, a study link identifies a paper, but the address does not record the design, sample, domain, population, comparison, AI access, search, display, or sort choices. Those choices survive opening a study within the same session. They disappear when someone opens a copied browse-page address in a fresh browser.

The proposed behavior is simple: set the filters, select “Copy view link,” and send a link that opens the same selection. For example, a coauthor could open student field experiments in mathematics, measured without AI, in table view. The link would also retain the view when the reader opens a study and returns. This would help with coauthor discussions, teaching, and checking a particular subset.

The minimum useful scope is to store the active selections in URL parameters, read them on page load, and preserve them through study navigation. Omit default choices to keep links short. Validate unknown values so that old or mistyped links have an understandable fallback. I recommend updating the current history entry as filters change, so each search keystroke does not create a new Back-button step. Opening a study should remain a separate navigation step.

This is medium UI work with little data work. The main effort is keeping controls, the address, and browser history consistent. Saved named views or comparisons between several views are a larger, optional feature. No account system is needed for the minimum scope.

A filter link selects records from the current dataset. It does not freeze the dataset or promise the same numerical result after an update. For a stable citation, combine the selection with an archived release, as described below. I recommend implementing the current-data link first and making that limitation explicit.

### 2. Source and version tracking

Today, records provide a PDF or source link, free-text notes, and some page or table references. They do not have consistent fields for the source-document version, extraction date, or data-release identifier. The visible update date is hard-coded to July 2026. A filename or DOI identifies a document, but it may not establish which working-paper version supplied an estimate.

There are two separate benefits. Estimate-level provenance lets a reader check a number: which document, which table, and which calculation produced it. Release tracking lets a reader recover the Atlas data used in an earlier result. A study record could show the source version and a table reference beside “standardized from reported means and SDs.” An export could identify the Atlas release and the selected filters.

The minimum useful scope is a generated release identifier and date, immutable copies of the released JSON and CSV, and structured source locators for newly added or revised estimates. Record the derivation where the effect or SE was calculated. Existing free-text notes can remain while missing fields are reviewed. The current JSON and notes should be preserved before any regeneration step. An automatic date should identify the data release, rather than the day someone rebuilt the website.

The larger scope is to review provenance for every existing estimate, retain source-document versions where available, publish a change log, and let the website open historical releases. An archived CSV preserves input data. Reproducing a historical pooled result also needs the corresponding calculation code and settings. A filter URL that happens to contain an old date is insufficient unless the site actually loads that archived release.

Release packaging is medium engineering work. Filling source fields can require substantial paper review. I recommend starting the release archive now and requiring complete provenance for new or changed estimates, then reviewing older records in batches. Historical interactive views can follow once the archive is reliable.

### 3. Clearer sample counts

The recent count repair answers how many records match, appear in the chart, and enter pooling. It does not answer how many people those records represent. The current `n_total` field can count participants, sessions, enrollments, or other observations. Study cards and tables label it simply “n,” while the hero sums paper-level values under “Participants.” A study count, an estimate count, and a participant count are different quantities.

The LearnLM record shows why the distinction matters. Its paper-level `n_total` is 2,713, but the existing coding notes describe 165 students and session-level samples. A clearer record would distinguish “Trial: 165 students” from “This estimate: 2,713 sessions.” The Contractor–Reyes test rows illustrate a different issue: the immediate estimate uses 211 participants and the one-week estimate uses 204. The endpoint's analyzed sample can differ from the original trial sample without indicating an error.

The minimum useful scope is to record the unit attached to each sample count and distinguish the study's recruited or randomized participants from the observations used for each estimate. Display those units in the report, table, tooltip, and CSV. Keep treatment and control counts tied to their actual contrast and sample. A trial with three arms can have a larger total sample than either two-arm comparison.

I recommend removing the aggregate participant headline until its components have been reviewed. Relabeling a sum of people and sessions as “total sample” would retain the same problem. Do not sum estimate-level samples: the same participants often appear in several outcomes or comparisons. A later aggregate can be labeled as the sum of reported study participants, with its coverage stated. A claim about unique people across the Atlas would additionally require checking whether studies or papers share cohorts.

This is mainly data-review work, with a smaller UI change once the fields are agreed. The larger scope adds cohort identifiers, shared-control relationships, attrition fields, and overlap checks. I recommend fixing ambiguous units first. The minimum sample-size inclusion rule should then state which denominator it uses, rather than treating every reported `n_total` as interchangeable.

### 4. Outcome-timing filters

Every current estimate has an `immediate` or `delayed` code. The table and study record display it, but readers cannot filter by it. A proposed “All / Immediate / Delayed” control would update the chart, cards, counts, and filtered export using this existing field. It would let a reader inspect evidence on later retention without finding each relevant row manually.

The minimum useful scope is small to medium: check the existing classifications, add the control, and carry its state into shareable links. Keep “All” as the initial choice so this feature does not silently change the current sample. Keep the existing distinction between outcomes measured with and without AI separate from timing. A delayed assessment can still permit AI use.

The broad categories conceal meaningful differences. The current data label both the Contractor–Reyes one-week test and Barcaui's 45-day test as delayed. The larger scope records a verified follow-up interval and its reference point, such as the end of the intervention. Where the paper gives a range or no precise interval, retain that information rather than inventing a day count. Once enough records have been reviewed, the site could offer follow-up bands or show timing directly beside each estimate.

The control itself needs little data work. Exact intervals require source review, especially for ongoing interventions and repeated exposure. I recommend the two existing categories first, followed by verified interval fields. Differences between immediate and delayed pooled subsets should remain descriptive: the subsets contain different studies and populations, so their difference does not identify learning decay. Estimating decay would need linked within-study outcomes and a separate analysis.

### Recommended sequence and scope

Start a release archive before the next data update and address the ambiguous participant headline and sample units. These steps protect the meaning and traceability of the results. The shareable-view control and the basic timing filter can then proceed together because they use mostly existing fields. Record timing in the URL from the start.

I recommend approving the minimum useful scope of all four proposals. They have distinct benefits: sharing a selection, checking a source, interpreting a denominator, and isolating a follow-up category. Full provenance review, exact follow-up intervals, cohort deduplication, and historical interactive views are larger extensions. They can be added in stages without holding up the initial controls.

## Checks behind these proposals

The local browser review covered the home page at widths of 390, 620, 768, 1,024, and 1,310 pixels. None produced page-level horizontal overflow. The chart itself remained 1,084 pixels wide at tablet widths, which required scrolling within the plot. The phone view started on the table. The Bastani study record and About page also fitted a 390-pixel viewport without page-level overflow or application errors.

Focus restoration is now fixed and verified locally. Opening a study moves focus to its heading. Returning restores the original card or estimate row and its scroll position. Independent browser checks covered table rows at 390 pixels and chart rows at 1,310 pixels, starting both at `/` and at `/#evidence`. All four cases restored the same estimate identifier and exact scroll position, with no application errors. Card navigation also passed. Restoring focus after browser history processing resolved an additional failure specific to fragment links.

Anchor visibility is now fixed and verified locally. The new 120-pixel scroll margin kept the evidence heading below the sticky header at both 390 and 1,310 pixels. The measured header heights were 103 and 59 pixels, respectively.

Tertiary text contrast is now improved. The color changed from `#847E74` to `#787269`, increasing its computed contrast on white from 4.02:1 to 4.76:1. The repaired observational forest plot also passed visual inspection: the pooled diamond and its band remain inside the plotting area and no longer cover the label column.

Study deep links retained the generic home-page browser title. Filters and search were stored in component state, so copying the address did not preserve a filtered result. These observations motivate shareable views and record-specific titles.

## Decisions that need data review

The current pooling function treats estimate rows as independent inputs. Multiple outcomes or treatment arms can come from one study, sometimes with a shared control group. A different treatment of this dependence is a methodological change, not a visual repair. State the intended estimand and choose the pooling rule before adding moderator summaries or study-level sensitivity analyses.

The existing `subgroup` labels include participant characteristics, alternative outcomes, treatment comparisons, and specifications. A heterogeneity interface should use a reviewed classification. The maintenance changes remove the dormant subgroup selector and exclude subgroup rows from the primary filter. The separate heterogeneity view should retain that separation.

The About page states a minimum sample size of 50, while the current Kalam card displays 21. This may reflect different sample denominators or an inclusion exception. Review the source and state the rule before changing inclusion. The hero also sums paper-level sample sizes and counts distinct country strings. Those totals need explicit definitions if studies share participants or span several countries.

## Suggested order

Complete the current correctness and deployment repairs first. Then add shareable views, provenance, and the small navigation improvements. These changes make later results reproducible and easier to inspect. Build the heterogeneity view after reviewing the relevant estimates and choosing how to handle dependence. Chart export and richer mobile presentation can follow without changing the scientific content.

The ranked table lists remaining proposals. The browser observations distinguish repairs verified in the local app from work still proposed.
