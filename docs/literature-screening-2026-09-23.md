# Literature screening, 23 September 2026

## Scope and decision rule

This is a screening report, not a dataset update. The search covered July 1 through September 23, 2026, plus older omissions found through references and related searches. Titles and authors were checked against the 35 learning papers in `src/papers.json`. No paper or estimate was added to the source workbook or generated JSON.

The working eligibility rule is randomized or credible quasi-random assignment of generative AI access, at least 50 participants at the study level, and an objective assessment without AI. AI-design comparisons belong in a separate category from AI versus a non-AI comparison. An AI tutor bundled with a learning platform or instructional changes does not isolate the contribution of AI.

Primary publisher, working-paper, and author sources were used. Available full texts and relevant appendices were checked. Downloaded PDFs were converted with `pymupdf4llm` before reading. Search results are not an exhaustive systematic review. “Unverified” means that a required detail was not established from the material accessed, not that the study fails that criterion.

The most useful additions to review first are Maier et al., Ates, and the two Oreopoulos studies. The first has explicit unaided testing and readily recoverable outcome statistics. Ates has explicit supervised AI-free transfer but needs complete numerical extraction. The Oreopoulos studies need careful treatment of comparators, counts, and possible participant overlap.

## Priority studies

### Maier, Schwabe, Schneider, and Feuerriegel: Designing Against Deskilling

[Designing Against Deskilling: Metacognitive Feedback Reduces Cognitive Offloading to LLM Assistants](https://arxiv.org/abs/2609.20143), first posted September 17, 2026, v1. [Full text and appendices](https://arxiv.org/html/2609.20143v1).

Five individually randomized conditions: no AI, AI only, AI plus metacognitive feedback, AI plus effort reward, and both additions. The study recruited 720 UK adults; 704 remained after five non-completions and eleven honesty-check exclusions. A separate pre-exclusion randomized tally is not tabulated. The immediate six-item fraction test explicitly removed LLM assistance.

Table 2 reports analyzed N and unaided-score mean/SD: control 146, .65/.32; AI-only 137, .62/.34; feedback 144, .67/.30; reward 138, .58/.32; combined 139, .64/.34. These permit approximate standardized contrasts from rounded statistics. Prefer exact data from the linked repository before coding. Appendix H gives AI-only minus control −2.57 percentage points, 95% CI [−10.28, 5.14].

Recommendation: eligible adult-learning addition. Retain shared-control dependence across four contrasts. Do not enter item responses as participants. The feedback OR 1.51 [0.98, 2.33] compares AI designs, not AI against no AI. Its significance uses a preregistered one-sided test. No delayed retention assessment.

### Ates: Human-centered GenAI feedback design

Huseyin Ates, [Human-centered GenAI feedback design in higher education: a multisite experiment on direct, reflective, and hybrid approaches to scientific argumentation](https://link.springer.com/article/10.1186/s41239-026-00614-9). Journal publication July 16, 2026; [preprint record](https://doi.org/10.21203/rs.3.rs-9396658/v1) dates to April 29. This is a July publication of older evidence.

Forty-eight sections across four universities were cluster randomized to peer feedback without AI, direct GPT-5 feedback, reflective AI feedback, or hybrid self/peer/AI feedback. There were 1,248 enrolled students and 1,176 analyzed. Exclusions combine non-consent, withdrawal, and missing assessments; do not label all 72 as post-randomization attrition. Week-10 transfer used a novel, supervised individual task with neither the study tool nor internet-enabled devices.

Recommendation: eligible student-learning addition, pending complete Table 4 extraction and cluster-aware standardized effects. Journal HTML and its DOCX supplement were accessible; journal PDF and separate tables were not. Supplementary Table S5 reports reflective versus direct transfer +1.15 raw rubric points (SE .26), hybrid versus direct +1.42 (.27). These are AI-design contrasts, not effects against peer-only control. Do not substitute AI-assisted draft improvement for transfer. Conditions also change reflection, peer input, and workload.

### Oreopoulos, Liut, Sungu, and Low: Making AI Tutoring Productive

[Making AI Tutoring Productive: Evidence from a Mastery-Based Math Practice Experiment](https://edworkingpapers.com/ai26-1552), August 2026, EdWorkingPaper 26-1552, also NBER 35621. The [73-page paper and appendix](https://edworkingpapers.com/sites/default/files/ai26-1552.pdf) were converted and reviewed.

Grades 6–8 students in 20 Hamilton County schools were individually assigned at registration in a topic × AI × mastery factorial design. There were 6,997 observed practice entrants and 6,327 delayed-test observations; the paper does not separately tabulate all initial randomized registrations. AI is compared with the same CAL platform without AI. Testing occurred approximately one week later, in class, with paper/pencil instructions and no teacher content help. Explicit disabling of the platform's AI during this assessment still needs confirmation.

Table 5: AI effect without mastery on practiced-item total −.041 (SE .028), mastery × AI interaction +.085 (.039). Table 9: within mastery, AI effect on practiced total +.044 (.028), N=3,209. These are raw counts out of two, not SDs. The highlighted first-item effect +.032 (.017) is not the overall learning effect.

Recommendation: high-priority conditional addition. Obtain the outcome standardizer and assessment restriction. Preserve both mastery strata and shared factorial dependence. Possible participant overlap with the next study needs checking.

### Oreopoulos and Low: One Click Away

[One Click Away: AI Tutoring with Khanmigo in a Two-Year School Experiment](https://edworkingpapers.com/ai26-1551), August 2026, EdWorkingPaper 26-1551, also NBER 35620. The [54-page paper and appendix](https://edworkingpapers.com/sites/default/files/ai26-1551.pdf) were converted and reviewed.

Grade-within-school randomization across 18 schools and 53 clusters evaluates Khan Academy plus Khanmigo against usual remedial instruction in 2024–26. It does not isolate Khanmigo from Khan Academy. District MAP tests are independent of the platform; explicit AI restrictions were not located. The announced TCAP outcome is not yet reported.

Table 5 pools 6,902 student-term observations, not people. Baseline-adjusted ITT is +.050 control SD (clustered SE .023), or +.040 population SD (.019). Table 7's stacked annual effect is +.062 population SD (.035), over 2,759 student-years. Choose an estimand; do not pool these repeated observations as independent evidence.

Recommendation: high-priority bundled-intervention addition after count reconciliation. Figure 1 implies 2,472 unique observed students from 2,708 ever scheduled minus 236 never observed; Appendix A1's pooled first-entry baseline/endline counts sum to 2,265. Some students change treatment exposure across years. The Hamilton County cohort could overlap NUMI. Do not sum the studies' participant counts without clarification.

### Cruces, Fernández Meijide, Galiani, Gálvez, and Lombardi: education-based gaps

[Does generative AI narrow education-based productivity gaps? Evidence from a randomized experiment](https://www.nber.org/papers/w34851), NBER 34851: original February 2026, revised May. The [August 4 arXiv posting](https://arxiv.org/abs/2608.04198) is a repost, not newly collected August evidence. Its 99-page PDF is dated May and includes the appendices reviewed here.

The Argentina experiment randomized 1,795 adults to embedded GPT-4.1 or no AI; 1,174 completed. After an assisted business task, participants immediately answered an explicitly unaided explanation and two recall/interpretation questions. The authors distinguish this carry-over outcome from durable learning or performance on a new task.

Table 1's follow-up effect is +.171 (SE .087) for lower-education adults and +.071 (.080) for higher-education adults. Both use the lower-education control group's SD. The interaction is −.100 (.118), not evidence of a reliable education gradient. Appendix A5 separates explanation from multiple-choice outcomes.

Recommendation: older omission suitable for an adult immediate-retention/carry-over category, with attrition flagged. Do not use the much larger AI-assisted work effects as learning. Preserve the common standardizer and distinguish randomized education-group heterogeneity from descriptive, post-treatment engagement comparisons. No cross-paper overlap was identified.

## Candidates requiring clarification

### Liu, Guo, Gao, Chen, Zhu, and Chang: Borrowed or kept?

[Borrowed or kept? How self-generation-first and direct-adoption AI workflows shape immediate unaided reasoning](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2026.1910545/full), September 14, 2026. This is not the already included Grace Liu et al. persistence paper.

The paper reports 900 randomized adults, with 659 analyzed: 222 self-generation-first AI, 225 direct-adoption AI, 212 no AI. A new essay 15–20 minutes later explicitly prohibited AI/external tools. Dependent minus no-AI reasoning is −.38 points [−.59, −.18], reported d=−.28; autonomous minus no-AI is +.21 [.01, .41]. These raw-point intervals cannot be attached directly to d.

Hold for clarification. Reported equal allocation in blocks of six across ability-tertile × student/worker strata does not readily reconcile with initial arms 278/294/328. Under the stated six strata, incomplete final blocks alone cannot explain the 50-person spread. Exclusions are also differential: 20.1%, 23.5%, 35.4%, including an AI-use screen applied only to controls. The primary model conditions on post-treatment task time. Full-sample sensitivity analyses exist but do not resolve the allocation description. Immediate transfer is relevant; long-run skill loss is not established. This is mixed student/worker evidence, not a pure student sample.

### Harrison, Khowaja, Dobson, Uwimpuhwe, and Higgins: Medly science

[Evaluating AI Tutoring at the Speed of Innovation: Practitioner-Led Micro-Randomised Trials of an AI Tutoring Platform in GCSE Science](https://arxiv.org/abs/2609.14789), September 13, 2026, v1. [Full text](https://arxiv.org/html/2609.14789v1).

Students in English Years 9–10 were individually randomized to four weeks of Medly or time-matched usual revision. Of 929 baseline students, 644 completed post-tests: 332 AI and 312 control. Overall Hedges g=.33 [.18, .48]; subject-specific samples total the same participants, not additional studies. The treatment-by-Pupil-Premium interaction is .57 raw marks [−2.25, 3.39].

Conditional addition. Post-test questions were new and unavailable during practice, but explicit AI-free test rules were not found. Confirm assessment restrictions and whether controls could use other generative AI. Attrition was 30.7%, with 33.2% control and 27.7% intervention loss. Outcomes were AI-marked and checked by teachers, not independently blinded assessors. Preserve the mixed-model uncertainty; any SE recovered from the reported CI must document its distributional assumption. Engagement analyses are post-randomization associations. The study was funded by Medly. No participant overlap with existing papers was identified.

### Yang, Van Alstyne, and Dellarocas: When AI Tutors Speak

[When AI Tutors Speak: Evidence from a Randomized Field Experiment](https://arxiv.org/abs/2609.23958), September 21, 2026, v1. [Full text and appendices](https://arxiv.org/html/2609.23958v1).

Eighty-six online MBA students were randomized: 52 structured tutor, 34 holdout. Consumer AI remained available to controls. Fifty-one completed the post-test; the primary analysis retains 46 after quality screens, 29 versus 17. Primary adjusted effect: +6.63/55 points [1.95, 11.31]. Baseline-only adjustment gives +3.56 [−.4, 7.5]. Retaining one response-quality exclusion changes the primary estimate to +5.52, p=.052.

The course final includes all 86: +2.57/100 [.12, 5.01], but it is take-home and was not a preregistered outcome. The paper says the tutor was absent during assessments; this does not establish that all external AI was prohibited. The reported gain-score d and adjusted raw-score coefficient are different estimands.

Recommendation: AI-design category pending test-policy confirmation, not headline AI-versus-no-AI evidence. Treat voice/text contrasts as repeated observations within tutor students. Do not count student-weeks as participants or treat self-selected external-AI users among controls as randomized groups.

### Medical education candidates

| Study and primary source | What is established | Decision / remaining check |
| --- | --- | --- |
| Rother, Nissen, Laupichler, Raupach, and Sommer, [Enhancing Clinical Reasoning in Surgical Education](https://pubmed.ncbi.nlm.nih.gov/42413233/), DOI 10.1016/j.jsurg.2026.104068 | Online July 7, 2026, September issue. Randomized crossover of personalized AI feedback versus general feedback for fourth-year medical students. Exit-exam contrast p=.454. | Publisher full text returned 403 despite an open-access label. N, comparator origin, AI-free assessment, and effect/SE remain unverified. Do not infer a zero effect or use app-use associations as randomized evidence. |
| Sevinç Meşe, Yanjun Pan, Can Meşe, and Gözde Sirganci, [nursing case-learning trial](https://www.sciencedirect.com/science/article/abs/pii/S1471595326002520), DOI 10.1016/j.nepr.2026.104949 | Online August 20, 2026. Three-week RCT: 108 randomized, 91 analyzed, comprising 28 traditional, 31 individual-plus-ChatGPT, 32 peer-plus-ChatGPT. Interaction p=.936. | Full text unavailable. Verify unaided post-test, attrition reasons, and numerical contrasts. Peer-plus-AI changes two components. Do not impute zero from nonsignificance. |
| Wang et al., [AI-driven virtual standardized patients combined with scenario-based simulation in anesthesiology training](https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2026.1927674/full), September 8, 2026 | Sixty graduate trainees, 20 per arm, no reported attrition. Conventional teaching, simulation, or simulation-plus-LLM patient practice. Individual faculty-supervised written/practical tests. Clinical total means/SDs: 78.0/7.7, 80.4/6.5, 88.2/4.8. | Promising professional-learning candidate. Explicit test AI prohibition still needs verification. Prefer AI-plus-simulation versus simulation to isolate the added component. Preserve the common treatment arm across contrasts. Very large pilot effects warrant careful extraction and small-sample uncertainty. |

## Older AI-design omission

Sebastian Gallegos, [Guidance Over Adoption: Experimental Evidence on AI-Assisted Learning](https://www.iza.org/index.php/de/publications/dp/18513/guidance-over-adoption-experimental-evidence-on-ai-assisted-learning), IZA DP 18513, March 2026. The [33-page paper and appendices](https://docs.iza.org/dp18513.pdf) were converted and reviewed.

Two individual, stratified randomizations use the same 384 initially enrolled econometrics students in Chile. Analysis samples are 303 before the midterm and 289 before the final. Controls retained GPT-UAI access. Encouragement precedes the midterm; structured usage guidance precedes the final. The latter's Table 3 ITT is +.218 control SD (robust SE .100); passing rises .128 (.049). Do not substitute the IV estimate or count the two experiments as separate participants.

Recommendation: older AI-design candidate. Printed, in-class exam procedures support independent measurement, but explicit AI restrictions should be confirmed. The intervention changes guidance, not access. Shared students and successive assignments require linked-study identifiers. Do not label this paper as a post-July discovery of new evidence merely because it was found in this search.

## Exclusions and lower-priority queue

| Paper | Reason / next action |
| --- | --- |
| Haqbeen, Sahab, and Ito, [Facilitating Student Engagement and Learning Outcomes with GPT-Based Chatbots](https://globals.ieice.org/en_transactions/information/10.1587/transinf.2025AHP0009/_f) | Published July 1, but publicized February 3, 2026. RCT with 80 Afghan undergraduates. Outcomes are perceived learning and discussion engagement, not an objective unaided post-test. Exclude from the learning-effect pool. |
| Wu et al., [How AI Assistance Affects Human Skill Development: A Study of Learning with Logic Puzzles](https://arxiv.org/abs/2608.23543) | August 24. The helper is simulated and perfectly accurate, not generative AI. Exclude under the current technology scope. |
| Oreopoulos, Dong, and Low, [Virtual Tutoring with Computer-Assisted Learning](https://www.nber.org/papers/w35622) | August 2026. Human virtual tutoring plus CAL, not a GenAI treatment. Do not confuse it with the neighboring NBER Khanmigo/NUMI papers. |
| Gao et al., [Beyond the prompt](https://link.springer.com/article/10.1186/s12909-026-10217-7) | August 22. Guided versus minimally guided AI, N=72. Potential AI-design entry. Reconcile the reported standardized effect with group means/SDs and verify assessment rules before coding. |
| Lei et al., [AI-scaffolded L2 vocabulary intervention](https://doi.org/10.1007/s43545-026-01725-w) | September 22. Sixteen participants and existing classes. Below the minimum sample and not an eligible randomized contrast. |
| Fütterer et al., [school students' self-regulated learning with AI](https://doi.org/10.1007/s10648-026-10133-8) | April 2026, not a new July/August study. N=371; prompting designs with AI in every arm. Older AI-design screening queue. |

Franco et al. and Chung et al. already appear in the local dataset. A later web posting or repository record must not create another study. More generally, preserve original release, latest version, journal publication, and retrieval dates as distinct fields.

## Implications for extraction and heterogeneity

Use this search to strengthen the data structure before adding estimates. Record randomized, analyzed, outcome-specific, and unique-participant counts separately. Also record cluster counts, participant overlap, control-arm identifiers, the assessment's AI policy, the test delay, the outcome standardizer, and whether an intervention bundles AI with other changes.

Separate three kinds of evidence in the interface: AI versus non-AI instruction, alternative AI designs, and observational usage differences within a randomized arm. Only the first two identify assigned-intervention effects. Post-treatment usage, effort, or engagement splits should not be presented as causal moderators.

Participant heterogeneity deserves its own view, starting with prior ability and socioeconomic background. Mastery rules and feedback designs are treatment-design comparisons and should appear separately. Report the interaction estimate or test alongside subgroup estimates. A significant effect in one group and a non-significant effect in another does not establish a difference. Keep exploratory analyses labeled, and do not put multiple outcomes, shared controls, or repeated tests into a pooled estimator as independent observations.

Before adding records, check the extraction against the exact paper version, resolve the flagged numerical/access issues, and update the source workbook and coded metadata described in the README. Regenerate the website data through the builder. This report alone does not certify every candidate for pooling.
