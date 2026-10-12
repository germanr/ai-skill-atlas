# Extraction file

Working instructions for the Phase 2 extraction (October 2026). An extractor fills this file for one paper from its full text and saves it as JSON. The vocabulary and the rules come from `docs/creativity-codebook.md`. Read it first, especially sections 3, 4, and 6 to 13. The paper's reconciled screening form (`forms/<cid>.json`) lists its studies, arms, outcomes, and contrasts. Use the form as a map, and check every entry against the paper.

## Rules

1. **Transcribe; do not compute.** Record each number exactly as printed, with its printed precision and sign. Code computes the standardized effects, standard errors, and intervals from what you record. Do not convert units, derive a standard deviation from a standard error, back out a statistic from a p-value, or average numbers. A number that can only be read off a figure is not recorded; say so in `notes`.
2. **Every number has a source.** Each estimate's `sources` list says where each recorded number comes from: the PDF page (the page index in the PDF file plus one, followed by the printed page number when it differs, for example `"PDF p. 12 (printed p. 10), Table 3"`), and a verbatim quote of at most 40 words that contains the number. For a table row, the quote is the row label and the cells you used, copied from the PDF text.
3. **Check against the PDF.** The markdown conversion can drop or scramble tables. Extract the text of every page you cite with pymupdf and confirm each number there. `page.find_tables()` recovers most tables.
4. **What to extract.** Every outcome that (a) is scored on the output that participants produced, (b) answers `with_ai`, `across_people`, or `after_ai`, and (c) comes from a study in which people were randomly assigned to generative-AI assistance (`lab_rct`, `online_rct`, `field_rct`, or a within-person design with randomized order). For each such outcome, extract every full-sample contrast the paper reports between an AI arm and a comparison arm, and between two AI configurations.
5. **What not to extract.** Self-reports and attitudes, ratings of how people perceive AI-made work, subgroup and moderation results, mediation analyses and any effect adjusted for variables measured after treatment (for example a direct effect controlling for a mediator), studies in the paper that did not randomize people, model-only analyses, and arms in which no person worked. List each skipped outcome or study in `not_extracted` with the reason.
6. **Paper-specific decisions from Review 1.**
   - Contractor and Reyes (2026) [c750]: extract only the two essay-similarity outcomes (with AI in Session One, and without AI one week later). Use the September 2026 version, `public/pdfs/Contractor & Reyes (2026-09) - AI Learning RCT.pdf` in the repository.
   - Writing-proficiency scores on argumentative or expository writing (for example an IELTS-style composite) are not creativity outcomes. Skip them.
   - Convergent outcomes (tests with right answers) are extracted with construct `convergent`. They are shown on study pages and never pooled.
7. **Counts are people.** `n_treatment`, `n_control`, and `n_total` count the people in the analysis that produced the statistic, as printed for that analysis (degrees of freedom do not count as a printed count). Clusters, ideas, ratings, and pairs go in their own fields.
8. **Within-person designs.** If the paper prints results for the first round only (people in their first condition), extract them as a record with `within_person` set to `first_round`. Extract the paper's paired contrast as a separate record with `within_person` set to `paired`.
9. **Clustered designs.** When classes, teams, or sessions were randomized, record the number of clusters in each arm and how the paper's standard errors treat the clusters. When the paper shows that every session ran a single arm (for example, a table of sessions by treatment), assignment_unit is `session`, even if the paper describes the assignment of people.
10. **Diversity outcomes.** For `across_people` outcomes, and `after_ai` outcomes with construct `diversity`, record both arm levels and the paper's uncertainty in the paper's own units, the unit over which the measure is computed, and whether higher values mean more alike or less alike.
11. **Direction words.** `higher_is` says what a higher value of the outcome means: `more_creative`, `less_creative`, `more_diverse`, `more_similar`, `more_ideas`, `more_accurate`, or `other` (explain in `notes`). Code sets the sign of every effect from it.
12. **Arms.** Use the arm names of the screening form when they match the paper. Name the arms of each contrast in `treatment_arm` and `control_arm`. When the paper pools arms for a contrast, write their exact names joined by "and", followed by "(combined)", for example `"Human with one GenAI idea and Human with five GenAI ideas (combined)"`. In an `ai_design` contrast, the treatment arm is the configuration the paper proposes or tests, and the control arm is the plain or default configuration (codebook section 5).
13. Use `null` for a number the paper does not print. Do not guess.

## JSON structure

```json
{
  "cid": "c000",
  "extractor": "A",
  "source": {
    "pdf_file": "path of the PDF read",
    "version": "which version this is, as the document shows",
    "supplement_used": "the supplement file or section used, or null"
  },
  "studies": [
    {
      "study_id": "S1",
      "label": "Experiment 1 (story writing)",
      "design_class": "lab_rct | online_rct | field_rct | unstated_rct (randomized, setting not stated)",
      "assignment_unit": "individual | team | class | session | within_person_order",
      "clusters_per_arm": { "arm name": 0 },
      "cluster_se_treatment": "how the paper's standard errors treat clusters, or null",
      "n_randomized": null,
      "n_analyzed": null,
      "counts_source": { "locator": "", "quote": "" },
      "arms": [
        { "name": "", "description": "", "ai": "none | generative_ai | other_aid", "n_randomized": null, "n_analyzed": null }
      ],
      "population": "students | online_panel | professionals | general_public | mixed",
      "country": "",
      "task_type": "divergent_test | idea_generation | creative_writing | design_visual | humor | other",
      "task": "one sentence",
      "ai_role": "ideas_supplied | open_chat | suggestions | refinement | coach | image_generation | other",
      "ai_tool": { "name": "model or product as the paper names it", "year": 2023, "locator": "" },
      "preregistration": { "exists": "yes | no | not_stated", "where": "", "primary_outcome": "the preregistered primary outcome, or null" },
      "shared_sample": "other papers that analyze these participants, from the form's sample_overlap, or null"
    }
  ],
  "estimates": [
    {
      "slug": "short_snake_case_name_unique_in_this_paper",
      "study_id": "S1",
      "form_outcome_id": "S1-O1 or null",
      "outcome": "label, e.g. Story novelty (rated by 600 evaluators)",
      "question": "with_ai | across_people | after_ai",
      "construct": "overall_creativity | novelty | usefulness | fluency | flexibility | elaboration | convergent | diversity | other",
      "measure": "human_raters | expert_raters | embedding_similarity | lexical_overlap | category_count | automated_score | behavioral | length | text_features, or null when the paper does not say who or what scored the outcome (human raters whose expertise the paper does not state are human_raters)",
      "measure_detail": "scale, raters, embedding model, metric",
      "unit": "participant | team | output | rating | pair | set, or null when the paper does not say",
      "n_units": null,
      "outcome_timing": "immediate | delayed",
      "delay_days": null,
      "outcome_with_ai": true,
      "comparison_type": "ai_vs_bau | ai_vs_active | ai_design",
      "treatment_arm": "",
      "control_arm": "",
      "within_person": "null | first_round | paired",
      "n_treatment": null,
      "n_control": null,
      "n_total": null,
      "higher_is": "more_creative | less_creative | more_diverse | more_similar | more_ideas | more_accurate | other",
      "stats": {
        "treatment_mean": null, "treatment_sd": null, "treatment_se": null,
        "control_mean": null, "control_sd": null, "control_se": null,
        "sd_level": "participant | output | rating | pair | set | null",
        "difference": null, "difference_is": "treatment minus control, or as printed",
        "difference_se": null,
        "ci_lower": null, "ci_upper": null, "ci_level": null, "ci_of": "difference | paper_effect | treatment_mean | null",
        "regression": { "coef": null, "se": null, "se_type": "robust | clustered_participant | clustered_cluster | conventional | not_stated", "outcome_scale": "raw | standardized", "model": "" },
        "test": { "type": "t | F | z | chi2 | U | W | H | other", "value": null, "df": null },
        "p_value": null,
        "paper_effect": { "type": "d | g | beta_std | r | eta2 | cliffs_delta | odds_ratio | other", "value": null, "se": null, "ci_lower": null, "ci_upper": null, "standardizer": "what the paper divides by, if it says" }
      },
      "se_basis": "participant | cluster | output | rating | pair | set | not_reported | unclear",
      "preregistered_primary": "yes | no | not_stated",
      "sources": [
        { "fields": ["treatment_mean", "control_mean", "treatment_sd", "control_sd"], "locator": "", "quote": "" }
      ],
      "notes": ""
    }
  ],
  "not_extracted": [
    { "what": "outcome, study, or contrast", "reason": "" }
  ],
  "open_items": [ "what the paper does not print that the codebook needs, e.g. participant-level SDs" ],
  "notes": ""
}
```

## Field notes

- `regression`, `test`, and `paper_effect` are objects only when the paper prints them; otherwise `null`.
- `p_value` is a number when printed exactly (0.032) and a string when printed as a bound (`"<0.001"`).
- `sd_level` is the level at which the printed standard deviations are computed: across participants, across outputs, across ratings, and so on. If the paper averages each person's outputs before computing the SD, the level is `participant`.
- `se_basis` describes the paper's own uncertainty for this contrast, judged against the unit that was randomized:
  - `participant`: the uncertainty counts each randomized person once: one value per person, standard errors clustered by person, or a mixed model with person random effects. An analysis with one output per person is `participant`.
  - `cluster`: classes, teams, or sessions were randomized, and the standard errors are clustered by those randomized clusters, or the analysis uses one value per randomized cluster.
  - `output`, `rating`, `pair`, or `set`: the analysis treats outputs, ratings, pairs, or sets as independent observations of the randomized people. This holds even when the standard errors are clustered by something other than the randomized unit. Example: ratings of each writer's story, analyzed at the rating level with standard errors clustered by evaluator, are `rating`, because evaluator clusters do not account for the repeated ratings of each writer's work. Clustering by raters, evaluators, items, prompts, or topics never makes a record `participant` or `cluster`.
  - `not_reported`: the paper prints no uncertainty for this contrast.
  - `unclear`: the paper prints a test or interval, but its unit of analysis cannot be established from the paper (for example, degrees of freedom that exceed the number of people). Never pooled.
- `fields` in `sources` names the keys of `stats` (and `n_treatment`, `n_control`, `n_total`) that the quote supports. Every number you record appears in exactly one source's `fields`.
- A `slug` uses lowercase letters, digits, and underscores, starts with the study id (`s1_`), and names the outcome and the contrast, for example `s1_novelty_one_idea_vs_human_only`.
