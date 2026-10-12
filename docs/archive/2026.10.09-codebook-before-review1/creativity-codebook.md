# Creativity section codebook

Draft for Review 1, October 4, 2026. Sections 1 to 8 fix the vocabulary that the screening forms use. Sections 9 to 11 are proposals that Review 1 confirms or changes. This document has changed nothing in the dataset.

## 1. Scope

The section covers evidence on how generative AI affects human creative work. Generative AI means systems that produce text, images, audio, or code from a prompt: chatbots built on large language models, writing suggestions built on language models, and text-to-image tools. Predictive keyboards, search engines, and recommender systems are outside the scope.

Each estimate answers one of three questions.

| Code | Question | AI when the output is produced |
| --- | --- | --- |
| `with_ai` | Does AI assistance change the rated creativity of what a person produces? | Available |
| `across_people` | Does AI assistance make different people's outputs more alike? | Available |
| `after_ai` | What happens to unassisted creative work after a period of AI use? | Removed |

An outcome produced after AI is removed is `after_ai` whatever its construct. An outcome produced with AI available is `across_people` when its construct is diversity and `with_ai` otherwise.

A creative or ideation task asks for output that has more than one acceptable answer and is judged on novelty, originality, usefulness, or overall creativity: stories, poems, essays judged for creativity, slogans and advertisements, product and business ideas, research ideas, divergent-thinking tests, designs, images, and humor. Writing tasks whose outputs are compared across writers for similarity also belong, because they answer `across_people`.

## 2. Units

- **Paper.** One document. When a preprint and a journal article report the same work, the paper is the latest version and the record lists the others.
- **Study.** One experiment or one dataset inside a paper.
- **Sample.** One set of participants or one corpus. Two papers that analyze the same participants share a sample. Meincke, Nave, and Terwiesch (2025) analyzes the participants of Lee and Chung (2024).
- **Estimate.** One contrast between two conditions on one outcome in one sample.

## 3. Eligibility

A study enters the core dataset if it satisfies three criteria. All three are applied before reading the results.

1. **Source of variation.** Random assignment of people to generative-AI assistance on a creative or ideation task, with a comparison group that works without AI or with a different AI configuration. A within-person design qualifies when the order of conditions is randomized.
2. **Sample size.** At least 50 participants across all arms, counting people. Ideas, essays, ratings, and pairs of outputs do not count toward the 50.
3. **Outcome.** Creativity or diversity scored on the output that participants produce, by raters or by a computed measure. Self-reported creativity, attitudes, and intentions do not qualify.

Criteria 1 and 2 repeat the learning section's criteria. Criterion 3 is new, because "creativity" needs a boundary that "learning assessed on a test" already has.

Three kinds of context evidence appear on the site and never enter a pooled estimate:

- **AI versus human output.** AI-generated output is compared with human-generated output, and no person receives AI help.
- **Observational.** Real output (papers, proposals, artworks, essays, posts) is compared across time or across adopters and non-adopters, with a diversity, similarity, novelty, or originality outcome. Comparisons of people who work with and without AI under non-random assignment also go here.
- **Synthesis.** Reviews and meta-analyses. No estimates are coded. Their pooled numbers are quoted beside the atlas's.

The screening report lists the following and the dataset omits them: randomized experiments with fewer than 50 participants, model-only studies, theory papers, studies whose only outcome is self-reported, studies that measure how much AI text exists with no diversity outcome, and studies of how people perceive or value AI-made work.

## 4. Design

Design is coded per estimate, because a few papers combine designs.

| Code | Definition | Role |
| --- | --- | --- |
| `lab_rct`, `online_rct`, `field_rct` | Randomized experiment with people: in a supervised session, on an online panel, or inside the participants' ordinary work or coursework | Core |
| `ai_vs_human` | AI-generated output compared with human-generated output | Context |
| `observational` | Real output compared across time or across adopters and non-adopters, or people compared under non-random assignment | Context |
| `synthesis` | Review or meta-analysis | Reference list |

The three randomized codes and `observational` are the learning section's codes. `ai_vs_human` and `synthesis` are new.

## 5. Comparison type

For randomized experiments, the learning section's codes apply.

| Code | Definition |
| --- | --- |
| `ai_vs_bau` | AI assistance versus no assistance |
| `ai_vs_active` | AI assistance versus another aid: web search, human-written examples, a human partner |
| `ai_design` | One AI configuration versus another: ideas versus refinement, coach versus answers, one idea versus five, persona prompts |

In an `ai_design` contrast the treatment arm is the configuration the paper proposes or tests, and the control arm is the plain or default configuration. Every record names both arms.

## 6. Outcome fields

**Construct.**

| Code | Definition |
| --- | --- |
| `overall_creativity` | A rating or score of creativity as a whole |
| `novelty` | Novelty, originality, surprise, or rarity of a single output |
| `usefulness` | Usefulness, feasibility, appropriateness, or quality of a single output |
| `fluency` | Number of ideas a person produces |
| `flexibility` | Number of distinct categories among one person's ideas |
| `elaboration` | Detail or length of a single output |
| `convergent` | Accuracy on a creativity test that has correct answers, such as the Remote Associates Test |
| `diversity` | Similarity or diversity across different people's outputs |
| `other` | Any other outcome scored on the output; the record describes it |

Variety among one person's own ideas is `flexibility`. `diversity` always compares different people.

**Measure.**

| Code | Definition |
| --- | --- |
| `human_raters` | Lay raters or crowd workers |
| `expert_raters` | Domain experts, instructors, or professionals |
| `embedding_similarity` | Distances between text or image embeddings |
| `lexical_overlap` | N-gram overlap, type-token ratios, ROUGE, BLEU, distinct-n |
| `category_count` | Counts of ideas, categories, or unique ideas, coded by hand or by clustering |
| `automated_score` | A scoring model for creativity: semantic-distance scoring of divergent-thinking tests, or a language model used as judge |
| `behavioral` | Market or usage outcomes: clicks, sales, votes |

**Unit.** What one observation in the paper's analysis is: `participant`, `team`, `output` (one idea, story, or design), `rating` (one rater's score of one output), `pair` (two outputs compared), or `set` (one condition's whole pool of outputs).

**Task type.** `divergent_test` (alternate uses and similar tests), `idea_generation` (product, business, policy, or research ideas), `creative_writing` (stories, poems, essays, slogans, advertisements), `design_visual` (sketches, images, product designs), `humor`, `other`.

**AI role.** `ideas_supplied` (the study hands participants AI-generated ideas or examples), `open_chat` (free use of a chatbot), `suggestions` (inline suggestions or completions while writing), `refinement` (AI edits or comments on the person's own draft), `coach` (AI asks questions or gives strategies and supplies no content), `image_generation`, `other`.

**Population.** `students`, `online_panel`, `professionals`, `general_public`, `mixed`.

**AI availability and timing.** `outcome_with_ai` is true when AI was available while the scored output was produced. `outcome_timing` is `immediate` or `delayed` (a later session), with the delay in days when the paper states it.

## 7. Signs and counts

- A positive effect means the treatment arm's output is more creative, or more diverse across people. When a paper reports similarity or homogenization, the sign is reversed and the record says so.
- `n_treatment`, `n_control`, and `n_total` count the people analyzed in the two arms of the contrast. `n_units` counts observations when the unit is something else (ideas, ratings, pairs).
- The study record keeps people randomized and people analyzed as separate counts.

## 8. Shared samples and primary records

- `sample_id` names the set of participants. Experiments on separate samples inside one paper get separate ids. Papers that analyze the same participants get the same id.
- One record per sample, question, and comparison type enters a pooled estimate. That record is the primary record. Every other record stays on the study page.
- The primary record is chosen by these rules, in order:
  1. The outcome that the preregistration or the paper names as primary.
  2. For `with_ai`: overall creativity rated by people, then novelty rated by people, then an automated creativity score. For `across_people`: the paper's main semantic-similarity measure across all participants in each arm. For `after_ai`: the same order, on the unassisted output.
  3. When several AI arms share one no-AI arm, the primary record uses the arm closest to free use of a general chatbot. The other arms are secondary records and share the control group.
  4. A reanalysis of another paper's sample can supply the primary record for a question the original paper did not report.

## 9. Standardized effects (proposal)

For creativity outcomes (`with_ai`, and `after_ai` outcomes other than diversity), the effect is the difference in mean outcomes between the two arms divided by a standard deviation of the outcome across participants. Preferred standardizers, in order:

1. The control arm's standard deviation at the participant level.
2. The pooled standard deviation of the two arms at the participant level.
3. The paper's own standardized effect, when it uses one of the two above.
4. The standard deviation of the regression outcome, when the paper standardized the outcome before estimation.

When a participant contributes several outputs, the participant-level outcome is that participant's mean score. If a paper reports only output-level or rating-level statistics, the effect uses the standard deviation at that level and the record's `unit` says so.

A record with no usable standard deviation stays in the dataset with its raw effect, both arm levels, and the paper's own measure.

## 10. Standard errors (proposal)

A standard error enters a pooled estimate only if it reflects the number of independent units: participants, or clusters when assignment is clustered. Participant-level analyses, standard errors clustered by participant, and mixed models with participant effects all qualify. `se_basis` records which one a record uses.

When a paper's precision treats ideas, ratings, or pairs as independent observations, the record keeps the paper's numbers, `se_basis` names the unit, and the record stays out of pooled estimates until a participant-level standard error is available from posted data or from the authors.

Derived quantities carry their formula in the provenance notes. From arm means, standard deviations, and counts: d = (m1 − m0) / s, with SE(d) = sqrt((n1 + n0) / (n1 n0) + d² / (2 (n1 + n0))). From a 95 percent confidence interval under normality: SE = (upper − lower) / 3.92.

## 11. Diversity effects (decision for Review 1)

Diversity measures have no common unit, and they are defined on sets of outputs. Three display rules are possible:

1. **Pooled standardized effect.** Compute each output's mean similarity to the other outputs in its arm, standardize the arm difference by the standard deviation of that output-level score, and pool. The standard error treats output-level scores as independent, an approximation that the page would state.
2. **Standardized effects without a pooled number.** The same per-study effects in a forest plot, with no pooled estimate.
3. **Each paper's own measure.** Both arm levels and the direction of the difference in the paper's own measure, with no common axis.

The screening report tabulates what each eligible experiment reports, so that the choice can be made on what the papers allow.

## 12. Provenance

Every estimate records the source document and its version, the table or page that supports it, the extraction and review dates, who reviewed it, and how each derived quantity was computed. These are the fields the release gate already requires for learning estimates (`src/evidence-metadata.mjs`).

## 13. Open questions for Review 1

- Whether `convergent` outcomes (Remote Associates Test accuracy) belong beside rated creativity or in a separate view.
- Whether the 50-participant rule holds for this section. It excludes Padmakumar and He (2024, 38 writers) and Anderson, Shah, and Kreminski (2024).
- Whether non-randomized comparisons of people (intact classes, before-and-after designs) appear as observational context or only in the screening report.
