# Creativity section codebook

Rules for extraction, October 9, 2026. Sections 1 to 8 fix the vocabulary that the screening forms and the extraction files use. Sections 9 to 11 were proposals in the October 4 draft, and Review 1 confirmed them on October 9 with the changes stated there. Section 13 lists the Review 1 decisions. The October 4 draft is archived in `docs/archive/2026.10.09-codebook-before-review1/`.

## 1. Scope

The section covers evidence on how generative AI affects human creative work. Generative AI means any model that produces text, images, audio, or code on request: chatbots built on large language models, writing suggestions built on language models, text-to-image tools, and earlier neural generators, such as the 2020 poetry generator in McGuire, De Cremer, and Van de Cruys (2024). Every record names the AI tool and its year, so readers can see which model a study used. Predictive keyboards, search engines, and recommender systems are outside the scope.

Each estimate answers one of three questions.

| Code | Question | AI when the output is produced |
| --- | --- | --- |
| `with_ai` | Does AI assistance change the rated creativity of what a person produces? | Available |
| `across_people` | Does AI assistance make different people's outputs more alike? | Available |
| `after_ai` | What happens to unassisted creative work after a period of AI use? | Removed |

An outcome produced after AI is removed is `after_ai` whatever its construct. An outcome produced with AI available is `across_people` when its construct is diversity and `with_ai` otherwise.

A creative or ideation task asks for output that has more than one acceptable answer and is judged on novelty, originality, usefulness, or overall creativity: stories, poems, essays judged for creativity, slogans and advertisements, product and business ideas, research ideas, arguments or reasons listed for a claim, divergent-thinking tests, designs, images, and humor. Writing tasks whose outputs are compared across writers for similarity also belong, because they answer `across_people`. For such tasks (argumentative, expository, or personal writing that is not judged for creativity), only the similarity records count: quality, readability, or length scores of the texts are coded `other`, shown on study pages and never pooled, as Review 1 Decisions 7 and 10 do for Contractor and Reyes (added during Phase 2, October 11, 2026, for review). A writing-proficiency score on an argumentative or expository text, such as an IELTS-style composite, measures writing skill and is not a creativity outcome.

## 2. Units

- **Paper.** One document. When a preprint and a journal article report the same work, the paper is the latest version and the record lists the others.
- **Study.** One experiment or one dataset inside a paper.
- **Sample.** One set of participants or one corpus. Two papers that analyze the same participants share a sample. Meincke, Nave, and Terwiesch (2025) analyzes the participants of Lee and Chung (2024).
- **Estimate.** One contrast between two conditions on one outcome in one sample.

## 3. Eligibility

A study enters the core dataset if it satisfies three criteria. All three are applied before reading the results.

1. **Source of variation.** Random assignment of people to generative-AI assistance on a creative or ideation task, with a comparison group that works without AI or with a different AI configuration. Assistance includes AI-generated ideas or examples handed to participants who never interact with a model (`ideas_supplied`). A within-person design qualifies when the order of conditions is randomized (section 4). When classes, teams, or other clusters are randomized, each arm needs at least two clusters. With one cluster per arm, the AI effect cannot be separated from that cluster, and the study is a non-random comparison. When the paper or its posted data show that every session ran a single arm, the session is the assignment unit, even if the paper describes the assignment of people: everyone in a session shared its conditions, so the session counts as a cluster (added during Phase 2, October 10, 2026, for review).
2. **Sample size.** At least 50 participants across all arms, counting people. Ideas, essays, ratings, and pairs of outputs do not count toward the 50. A within-person design counts each person once. The count is the people analyzed when the paper prints it, otherwise the people randomized (added during Phase 2, October 11, 2026, for review: 16 randomized studies print no analyzed total).
3. **Outcome.** Creativity or diversity scored on the output that participants produce, by raters or by a computed measure. Self-reported creativity, attitudes, and intentions do not qualify.

Criteria 1 and 2 repeat the learning section's criteria. Criterion 3 is new, because "creativity" needs a boundary that "learning assessed on a test" already has.

Three kinds of context evidence appear on the site and never enter a pooled estimate:

- **AI versus human output.** AI-generated output is compared with human-generated output, and no person receives AI help.
- **Observational.** Real output (papers, proposals, artworks, essays, posts) is compared across time or across adopters and non-adopters, with a diversity, similarity, novelty, or originality outcome.
- **Synthesis.** Reviews and meta-analyses. No estimates are coded. Their pooled numbers are quoted beside the atlas's.

The screening report lists the following, and the dataset and the site omit them:

- Randomized experiments with fewer than 50 participants.
- Non-random comparisons of people: intact classes, one cluster per arm, before-and-after designs, and self-selected AI use.
- Model-only studies and theory papers.
- Studies whose only outcome is self-reported.
- Studies that measure how much AI text exists, with no diversity outcome.
- Studies of how people perceive or value AI-made work.

## 4. Design

Design is coded per estimate, because a few papers combine designs.

| Code | Definition | Role |
| --- | --- | --- |
| `lab_rct`, `online_rct`, `field_rct` | Randomized experiment with people: in a supervised session, on an online panel, or inside the participants' ordinary work or coursework | Core |
| `unstated_rct` | Randomized experiment with people whose setting the paper does not state (added during Phase 2, October 11, 2026, for review) | Core |
| `ai_vs_human` | AI-generated output compared with human-generated output | Context |
| `observational` | Real output compared across time or across adopters and non-adopters | Context |
| `quasi_people` | People compared under non-random assignment, including one cluster per arm | Screening report only |
| `synthesis` | Review or meta-analysis | Reference list |

The three randomized codes and `observational` are the learning section's codes. `ai_vs_human`, `quasi_people`, and `synthesis` are new.

**Within-person designs.** When each person works in both conditions in random order, the estimate uses the first round, the comparison between people in their first condition, whenever the paper or its posted data report it, because the AI round can carry over into the unassisted round. Otherwise the record uses the paper's paired contrast and says so (`within_person`: `first_round` or `paired`). The site shows pooled results with and without paired records.

**Clustered designs.** Record the number of clusters in each arm. Standard errors must reflect the clustering (section 10).

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
| `usefulness` | Usefulness, feasibility, appropriateness, or quality of a single creative output: an idea, design, story, or image. Proficiency scores on argumentative or expository writing do not qualify. |
| `fluency` | Number of ideas a person produces |
| `flexibility` | Number of distinct categories among one person's ideas |
| `elaboration` | Detail or length of a single output |
| `convergent` | Accuracy on a creativity test that has correct answers, such as the Remote Associates Test. Shown on study pages and never pooled. |
| `diversity` | Similarity or diversity across different people's outputs |
| `other` | Any other outcome scored on the output; the record describes it. Shown on study pages and never pooled. |

Variety among one person's own ideas is `flexibility`. `diversity` always compares different people.

**Measure.**

| Code | Definition |
| --- | --- |
| `human_raters` | Lay raters or crowd workers, and human raters whose expertise the paper does not state (added during Phase 2, October 11, 2026, for review) |
| `expert_raters` | Domain experts, instructors, or professionals |
| `embedding_similarity` | Distances between text or image embeddings |
| `lexical_overlap` | N-gram overlap, type-token ratios, ROUGE, BLEU, distinct-n |
| `category_count` | Counts of ideas, categories, or unique ideas, coded by hand or by clustering |
| `automated_score` | A scoring model for creativity: semantic-distance scoring of divergent-thinking tests, or a language model used as judge |
| `behavioral` | Market or usage outcomes: clicks, sales, votes |
| `length` | Word or character count of the output |
| `text_features` | Counts or shares of word types that a text-processing tool tags in the output: parts of speech, stopwords, or emotion words |

When the paper does not say who or what scored an outcome, the measure is left empty; such an outcome is not treated as rated by people. `text_features` was added during Phase 2 (October 11, 2026, for review), for word-type counts that a paper computes with a named tool such as NLTK.

**Unit.** What one observation in the paper's analysis is: `participant`, `team`, `output` (one idea, story, or design), `rating` (one rater's score of one output), `pair` (two outputs compared), or `set` (one condition's whole pool of outputs).

**Task type.** `divergent_test` (alternate uses and similar tests), `idea_generation` (product, business, policy, or research ideas), `creative_writing` (stories, poems, essays, slogans, advertisements), `design_visual` (sketches, images, product designs), `humor`, `other`.

**AI role.** `ideas_supplied` (the study hands participants AI-generated ideas or examples), `open_chat` (free use of a chatbot), `suggestions` (inline suggestions or completions while writing), `refinement` (AI edits or comments on the person's own draft), `coach` (AI asks questions or gives strategies and supplies no content), `image_generation`, `other`. The site shows results by AI role, so readers can see whether `ideas_supplied` studies differ from the others.

**AI tool.** The model or product the participants used and its release year, as the paper names them (for example GPT-4, 2023).

**Population.** `students`, `online_panel`, `professionals`, `general_public`, `mixed`. Left empty when the paper does not say who the participants were, for example a university lab panel of unstated make-up (added during Phase 2, October 11, 2026, for review).

**AI availability and timing.** `outcome_with_ai` is true when AI was available while the scored output was produced. `outcome_timing` is `immediate` or `delayed` (a later session), with the delay in days when the paper states it.

## 7. Signs and counts

- A positive effect means the treatment arm's output is more creative, or more diverse across people. When a paper reports similarity or homogenization, the sign is reversed and the record says so.
- `n_treatment`, `n_control`, and `n_total` count the people analyzed in the two arms of the contrast. `n_units` counts observations when the unit is something else (ideas, ratings, pairs).
- The study record keeps people randomized and people analyzed as separate counts.
- In a within-person design, `n_total` counts each person once. A first-round record counts the people in each condition of the first round in `n_treatment` and `n_control`. A paired record counts all people in both.

## 8. Shared samples and primary records

- `sample_id` names the set of participants. Experiments on separate samples inside one paper get separate ids. Papers that analyze the same participants get the same id.
- One record per sample, question, and comparison type enters a pooled estimate. That record is the primary record. Every other record stays on the study page.
- The primary record is chosen by these rules, in order:
  1. The outcome that the preregistration or the paper names as primary.
  2. For `with_ai`: overall creativity rated by people, then novelty rated by people, then an automated creativity score (an automated score of overall creativity or novelty). For `across_people`: the paper's main semantic-similarity measure across all participants in each arm. For `after_ai`: the same order, on the unassisted output. After these (added during Phase 2, October 11, 2026, for review): overall creativity or novelty scored any other way (for example counts of unique ideas), then usefulness, flexibility, fluency, and elaboration, in that order. The order never depends on results; it replaces choosing among outcomes by what an abstract highlights.
  3. When several AI arms share one no-AI arm, the primary record uses the arm closest to free use of a general chatbot. If no arm is closer than the others, it uses the paper's own contrast of all AI arms combined against the shared control, when the paper reports one. The other arms are secondary records and share the control group. A tie that these rules leave open is settled per paper, with the reason and a quote recorded in the source file (`primary_override`), by these further rules, in order (added during Phase 2, October 10, 2026, for review): the paper's main specification, the one its abstract or introduction reports, over robustness variants; among different analyses of the same contrast and outcome, the one whose statistics allow a participant-level standardized effect; for repeated sessions of one contrast, the paper's own summary across sessions, else the session its abstract emphasizes, else the first session with AI; a full-sample contrast over contrasts within cells or subgroups; when a factorial paper prints only cell contrasts, the cell at the crossed factor's baseline or least modified level; when tasks tie within one sample, the task of that sample's other primary record. Further rules added on October 11, 2026, for review: among regression specifications of one contrast that the paper does not rank, the one with no added covariates, fixed effects, or controls; in a factorial design without a full-sample contrast, the contrast in which AI access is the only difference between the arms; in a within-person design, first-round records only, whenever the paper or its posted data give them (Review 1 Decision 11), so the paired contrast and later rounds stay on the study page; for `after_ai`, a task the person did not do with AI over a repeat of the task done with AI. No rule looks at the size, sign, precision, or significance of a result.
  4. A reanalysis of another paper's sample can supply the primary record for a question the original paper did not report.
- Convergent outcomes and outcomes coded `other` are never primary records.
- A record whose contrast has no number (the paper describes it only in words or in an unlabeled figure, and no posted data supply it) is primary only when no record of its pool key has a number.

## 9. Standardized effects (confirmed at Review 1)

For creativity outcomes (`with_ai`, and `after_ai` outcomes other than diversity), the effect is the difference in mean outcomes between the two arms divided by a standard deviation of the outcome across participants. Preferred standardizers, in order:

1. The control arm's standard deviation at the participant level.
2. The pooled standard deviation of the two arms at the participant level.
3. The paper's own standardized effect, when it uses one of the two above.
4. The standard deviation of the regression outcome, when the paper standardized the outcome before estimation.

When a participant contributes several outputs, the participant-level outcome is that participant's mean score. If a paper reports only output-level or rating-level statistics, the effect uses the standard deviation at that level and the record's `unit` says so.

A record with no usable standard deviation stays in the dataset with its raw effect, both arm levels, and the paper's own measure.

## 10. Standard errors (confirmed at Review 1)

A standard error enters a pooled estimate only if it reflects the number of independent units: participants, or clusters when assignment is clustered. Participant-level analyses, analyses with one output per participant, standard errors clustered by participant, and mixed models with participant effects all qualify. When clusters were randomized, standard errors clustered by those clusters qualify. Standard errors clustered by raters, evaluators, items, or prompts do not qualify, because they do not count each randomized person or cluster once. `se_basis` records which one a record uses; `unclear` marks a printed test whose unit of analysis the paper does not establish, and such a record is not pooled.

When a paper's precision treats ideas, ratings, or pairs as independent observations, the record keeps the paper's numbers, `se_basis` names the unit, and the record stays out of pooled estimates until a participant-level or cluster-level standard error is available from printed participant-level statistics, from posted data, or from the authors. Posted data are downloaded to `D:/projects/ai-skill-atlas/creativity-data/<cid>/`, outside Dropbox.

Derived quantities carry their formula in the provenance notes. From arm means, standard deviations, and counts: d = (m1 − m0) / s, with SE(d) = sqrt((n1 + n0) / (n1 n0) + d² / (2 (n1 + n0))). From a 95 percent confidence interval under normality: SE = (upper − lower) / 3.92.

## 11. Diversity effects (decided at Review 1)

Diversity measures have no common unit, and they are defined on sets of outputs. The site shows each paper's own measure: both arm levels, the unit, the reported uncertainty, and the direction (outputs more alike or less alike with AI), with no conversion to a common scale and no pooled number. Once extraction shows how many studies report participant-level statistics, a forest plot of standardized effects for those studies may follow, still without a pooled number.

The screening report tabulates what each eligible experiment reports.

## 12. Provenance

Every estimate records the source document and its version, the table or page that supports it, the extraction and review dates, who reviewed it, and how each derived quantity was computed. These are the fields the release gate already requires for learning estimates (`src/evidence-metadata.mjs`).

## 13. Review 1 decisions (October 9, 2026)

1. All 87 recommended papers go to extraction, except the three that Decision 9 moves out (Cui and Li 2026, Dai et al. 2026, Kultas 2026). The 43 papers that need clarification stay out of the core, with no author contact for now.
2. The 50-participant rule holds (section 3).
3. Diversity effects appear in each paper's own units (section 11).
4. Standardizers and standard errors follow sections 9 and 10: the control arm's participant-level SD first, and standard errors at the level of the people or clusters that were randomized.
5. The page opens with `with_ai` beside `across_people`. `after_ai` follows as a labeled panel on the skill question, marked as early evidence.
6. The site hosts a PDF for every creativity paper, as it does for learning papers.
7. Contractor and Reyes (2026) enters with its two essay-similarity records only, flagged `is_own_paper`. Its essay-quality outcomes stay in the learning section.
8. `ideas_supplied` counts as assistance, and the site shows results by AI role (section 6).
9. Clustered designs need at least two clusters per arm (section 3).
10. Writing-proficiency scores are not usefulness (sections 1 and 6). Gero et al. (2026) stays excluded.
11. Within-person designs follow the same rules and use first-round results when available (section 4).
12. McGuire, De Cremer, and Van de Cruys (2024) and Qin et al. (2025) stay in the core. Every record names its AI tool and year (section 1).
13. Convergent outcomes appear on study pages and are never pooled (section 6).
14. Non-random comparisons of people are listed in the screening report only (section 3).
