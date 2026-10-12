# Screening form

Working instructions for the full-text screening of October 2026. Every screener fills this form for one paper and saves it as JSON. The vocabulary comes from `docs/creativity-codebook.md`; read that file first.

## Rules

1. Record only what the document states. Use `null` for a number the paper does not give and `"not_stated"` where the form offers it. Do not infer, estimate, or recall from memory.
2. The markdown conversion sometimes drops or scrambles tables. Check every number you record against the PDF page itself.
3. Give a locator for every fact that decides eligibility and for every reported statistic: the page of the PDF and the section, table, or figure. Example: `"p. 7, Table 2"`.
4. Quotes are verbatim and short (40 words at most). Copy them from the document.
5. Counts of participants are people. When the paper gives only ideas, essays, ratings, or pairs, put that count in `n_units` and leave the people count `null`.
6. A paper can hold several studies (experiments or datasets). Fill one entry per study.
7. List every outcome that is scored on the output and bears on one of the three questions. Treat robustness variants of one outcome as a single outcome and mention them in `measure_detail`. If a paper has more than 15 such outcomes, list the main 15, primary ones first, and say in `notes` what you left out.
8. Do not compute effect sizes. Record what is printed.

## JSON structure

```json
{
  "cid": "c000",
  "screener": "A",
  "source": {
    "md_file": "",
    "pdf_file": "",
    "version": "which version this is: journal version of record, arXiv v2 of 2025-02-15, working paper dated ..., as the document shows",
    "title_on_document": "",
    "authors_on_document": [],
    "pages": null,
    "supplement": { "exists": "yes | no | not_stated", "in_this_pdf": false, "where": "URL or description if the document gives one", "holds": "what it contains that the main text lacks, e.g. tables S3 and S11 with standard errors" }
  },
  "paper_design_summary": "Two or three plain sentences: who did what, under which conditions, and what was scored.",
  "studies": [
    {
      "study_id": "S1",
      "label": "Short name, e.g. Experiment 1 (story writing)",
      "design_class": "lab_rct | online_rct | field_rct | quasi_people | ai_vs_human | observational | synthesis | model_only | other",
      "assignment": {
        "randomized": "yes | no | not_stated",
        "what_was_assigned": "",
        "unit": "individual | team | class | session | within_person_order | other",
        "structure": "between | within | crossover | mixed",
        "quote": "",
        "locator": "",
        "preregistered": "yes | no | not_stated",
        "prereg_locator": ""
      },
      "arms": [
        { "name": "", "description": "", "ai": "none | generative_ai | other_aid", "n_randomized": null, "n_analyzed": null }
      ],
      "participants": {
        "n_randomized": null,
        "n_analyzed": null,
        "counts_are": "people | teams | other",
        "exclusions": "",
        "population": "students | online_panel | professionals | general_public | mixed",
        "who": "",
        "country": "",
        "quote": "",
        "locator": ""
      },
      "ai_tool": {
        "name_model": "",
        "role": "ideas_supplied | open_chat | suggestions | refinement | coach | image_generation | other",
        "how_used": ""
      },
      "task": {
        "type": "divergent_test | idea_generation | creative_writing | design_visual | humor | other",
        "description": "",
        "duration": ""
      },
      "outcomes": [
        {
          "outcome_id": "S1-O1",
          "name": "",
          "construct": "overall_creativity | novelty | usefulness | fluency | flexibility | elaboration | convergent | diversity | other",
          "question": "with_ai | across_people | after_ai | none",
          "scored_on_output": true,
          "measure": "human_raters | expert_raters | embedding_similarity | lexical_overlap | category_count | automated_score | behavioral | self_report",
          "measure_detail": "",
          "unit": "participant | team | output | rating | pair | set",
          "n_units": null,
          "ai_available_when_produced": "yes | no | mixed",
          "timing": "immediate | delayed",
          "delay": "",
          "primary": "preregistered_primary | paper_primary | secondary | not_stated",
          "contrasts": [
            {
              "treatment_arm": "",
              "control_arm": "",
              "comparison_type": "ai_vs_bau | ai_vs_active | ai_design | ai_vs_human | before_after | other",
              "direction": "treatment_higher | treatment_lower | no_clear_difference | mixed",
              "statistics_available": [],
              "reported": "",
              "locator": ""
            }
          ],
          "diversity_detail": {
            "metric": "",
            "embedding_model": "",
            "computed_over": "",
            "uncertainty": "",
            "notes": ""
          }
        }
      ]
    }
  ],
  "synthesis": {
    "k_studies": null,
    "n_effect_sizes": null,
    "search_end": "",
    "inclusion": "",
    "pooled": [ { "comparison": "", "estimate": "", "interval": "", "what_it_standardizes": "", "locator": "" } ]
  },
  "sample_overlap": { "shares_participants_with": "", "quote": "", "locator": "" },
  "company_involvement": { "any": false, "description": "", "locator": "" },
  "data_and_code": { "data_url": "", "code_url": "" },
  "eligibility": {
    "core": "yes | no | unclear",
    "criterion_1_random_assignment_of_ai": "met | not_met | unclear",
    "criterion_2_at_least_50_people": "met | not_met | unclear",
    "criterion_3_outcome_scored_on_output": "met | not_met | unclear",
    "context_class": "ai_vs_human | observational | synthesis | none",
    "reason": ""
  },
  "one_line_finding": "",
  "open_questions": [],
  "notes": ""
}
```

## Field notes

- **`source.supplement`.** Say whether the paper refers to supplementary material or an online appendix, whether the PDF on file includes it, and which statistics sit only there. The extraction phase needs to know where the standard errors are.
- **`design_class`.** `quasi_people` means people worked with and without AI under non-random assignment (intact classes, self-selection, one group before and after). The dataset folds it into `observational`; the form keeps it apart. A reanalysis of another paper's experiment takes that experiment's design class, and `sample_overlap` names the original paper.
- **Counts in prose.** Write "analyzed" for a count after exclusions and "randomized" only for a count the paper gives at assignment. If people were dropped after assignment, say how many and why in `participants.exclusions`, and do not call the analysis intention-to-treat unless the paper keeps everyone who was assigned.
- **`arms[].ai`.** `other_aid` covers web search, human-written examples, and human partners.
- **`question`.** An outcome produced after AI was removed is `after_ai` whatever its construct. With AI available, a diversity outcome is `across_people` and any other construct is `with_ai`. Use `none` for outcomes that answer none of the three (for example AI output compared with human output).
- **`unit`.** The unit of the paper's own analysis for that outcome. If the regression has one row per idea, the unit is `output` even when ideas are nested in people.
- **`statistics_available`.** Any of: `arm_means_sds_ns`, `mean_difference_se`, `regression_coefficient_se`, `standardized_effect`, `confidence_interval`, `test_statistic`, `p_value_only`, `figure_only`, `none`.
- **`reported`.** The key numbers exactly as printed, with their labels. Example: `"ChatGPT 4.28 (SD 0.81, n = 116) vs web search 3.89 (SD 0.80, n = 117); d = 0.49, 95% CI [0.22, 0.75]"`.
- **`diversity_detail`.** Fill it for every `diversity` outcome and leave the strings empty otherwise. `computed_over` says which outputs are compared (all pairs within a condition, each output against the condition's centroid, each output against all others). `uncertainty` says how the paper got its standard error, interval, or test (regression on output-level scores, bootstrap, permutation, t-test over pairs).
- **`synthesis`.** Fill it only for reviews and meta-analyses; otherwise leave the defaults.
- **`eligibility.core`.** `yes` only if all three criteria are met for at least one study. Criterion 2 counts people analyzed across all arms of that study. If the count is close to 50 or unclear, say so in `reason`.
- **`one_line_finding`.** One plain sentence with the main numbers and where they are printed.
