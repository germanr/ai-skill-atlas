# Human verification queue

Last updated: October 5, 2026. This file lists the atlas records that no human research assistant has checked against the source documents, and what the next RA should check. It is a working list, not a public page.

## What has been verified so far

Three human verification rounds covered the atlas as it stood in July 2026. The commit history records each round.

| Round | Date | Who | Coverage |
| --- | --- | --- | --- |
| 1 | July 8, 2026 | Nam Nguyen | The 24 papers then in the atlas (23 literature papers plus Contractor and Reyes); 60 or more data errors fixed |
| 2 | July 15, 2026 | Nam Nguyen | The 10 papers added by the July 2026 literature sweep (Ba, Bassner, Dai, Fischer, Gan, Hou, Huang, Kavadella, LearnLM 2026, Wu); two Gan corrections applied, Wu later removed |
| 3 | July 24, 2026 | Wills Erda | Full round over the 34 papers then in the atlas; corrections to Ba, Lira, LearnLM UK and Sierra Leone, Fan, Kalam, Bassner, Lehmann, Hou, Contractor and Reyes, Chung, Kazemitabaar |

Two later passes were done by models, not people: the July 24 Codex audit and the September 23 to 24 primary-source audit by Claude. They changed numbers in rows that the RAs had already verified (see Part B).

## Part A. Papers never verified by a human RA

| Paper | Added | By | Status |
| --- | --- | --- | --- |
| Heldreth et al. (2026), An experimental evaluation of an AI-powered interactive learning platform | October 5, 2026 | Claude | Not verified; two independent model extractions agreed on every number |
| Rismanchian, Uzun, Matayoshi, Cosyn, and Kurd-Misto (2026), Faster Completion, Less Learning, observational | October 5, 2026 | Claude | Not verified; two independent model extractions agreed on every number |
| Barrera-Osorio and Muñoz-Morales (2026), Complementing Teachers, preliminary midline results | October 5, 2026 | Claude | Not verified; two independent model extractions agreed on every number; replace with the endline results when they appear |
| Maier, Schwabe, Schneider, and Feuerriegel (2026), Designing Against Deskilling | October 3, 2026 | Claude | Not verified |
| Ates (2026), Human-centered GenAI feedback design | October 3, 2026 | Claude | Not verified; Claude checked the journal version of record on October 3 and it matches the preprint |
| Oreopoulos, Liut, Sungu, and Low (2026), Making AI Tutoring Productive (NUMI) | October 3, 2026 | Claude | Not verified |
| Oreopoulos and Low (2026), One Click Away (Khanmigo) | October 3, 2026 | Claude | Not verified |
| Cruces, Fernández Meijide, Galiani, Gálvez, and Lombardi (2026) | October 3, 2026 | Claude | Not verified |
| Franco, Irmert, and Isaksson (2026) | August 23, 2026 | Claude | Not verified; the September 23 audit removed its SD conversion |
| Stromberg, Lei, and Wu (2026), observational | July 8, 2026 | Claude | Added after round 1; not named in the round 2 or round 3 commit messages, so verification is undocumented |

### What to check for each new paper

Every record for the October 2026 papers carries this sentence in its provenance notes, with its own extraction date (2026-10-03 or 2026-10-05): "Extracted and checked by Claude (model) against the linked PDF on 2026-10-03; not yet verified by a human research assistant." The checks below are the ones a person should do before that sentence is removed.

**Maier et al. (2026).** Source: arXiv 2609.20143 v1, local PDF `Maier et al (2026) - Designing Against Deskilling.pdf`.

1. Table 2 (p. 14): arm N, mean, and SD of unaided performance for all five arms. The atlas uses 146/0.65/0.32, 137/0.62/0.34, 144/0.67/0.30, 138/0.58/0.32, 139/0.64/0.34.
2. Appendix H, Table 8 (p. 39): the H1 difference of -2.57 percentage points with CI [-10.28, 5.14], the H2b difference +5.28 [-0.14, 10.70], and the H3b difference -3.53 [-8.95, 1.89].
3. The derivations: pooled SD of the AI-only and control arms (0.330), pooled SD of the four AI arms (0.325), Cohen's d for the three design arms versus control from the rounded Table 2 statistics.
4. Whether the anonymized repository (footnote 4) now gives exact per-arm statistics or a public dataset. If so, replace the rounded-input d values with exact ones.
5. Whether a later arXiv version or a published version exists.

**Ates (2026).** Source: journal version of record, local PDF `Ates (2026) - IJETHE - Human-Centered GenAI Feedback Design.pdf` (DOI 10.1186/s41239-026-00614-9). The Research Square v1 preprint stays in `public/pdfs` because release 2026-10-03.1 cites it; the journal renumbered its tables (preprint Tables 3, 4, 5 are journal Tables 2, 3, 4).

1. Done on October 3, 2026 (Claude, from the journal HTML and PDF): journal Tables 2 to 4 match the preprint values used here for every contrast (b, SE, Cohen's d, CI). The supplementary DOCX (Tables S1 to S7, robustness models) has not been opened; check it if the ICC or the baseline-adjusted sensitivity model matters.
2. Confirm the arm sizes in Table 2 (293, 295, 294, 294) and the 1,248 enrolled / 1,176 analyzed counts.
3. Check the conversion rule: the atlas uses the paper's d as the effect and multiplies the raw SE and CI by d/b. Confirm this matches the standardizer the paper used.
4. Confirm the Week 10 transfer task was AI-free and supervised (Section 4.7.3) and that the Week 9 conceptual post-test was taken without AI.
5. Record the country of the four universities if the journal version states it.
6. Confirm the classification of the hybrid arm versus peer feedback as an AI-versus-active-control contrast, given that the hybrid arm also adds self-evaluation and a revision memo.

**Oreopoulos, Liut, Sungu, and Low (2026), NUMI.** Source: EdWorkingPaper 26-1552 (August 2026), DOI 10.26300/01qv-6c22, local PDF `Oreopoulos et al (2026) - Making AI Tutoring Productive.pdf`.

1. Table 9 (p. 40): CAL-only mean 0.370 and AI mean 0.402 on the practiced Exercise 1 item, difference 0.032 (SE 0.017), p = 0.065; practiced Exercise 2 difference 0.013 (0.017); unpracticed Exercise 1 difference 0.002 (0.017), CAL-only mean 0.339; N = 3,209.
2. Table 5 (p. 37): AI coefficient -0.041 (0.028) and Mastery x AI interaction 0.085 (0.039) on the practiced two-item total; N = 6,327.
3. The standardization of binary items by the CAL-only Bernoulli SD, sqrt(p(1-p)). Decide whether this convention is acceptable or whether the authors should be asked for the SD of the two-item totals so the non-mastery row can be standardized too.
4. Whether the AI tutor was disabled during the week-2 delayed assessment. The paper says students used paper and pencil and teachers gave no content help; it does not state that the platform's tutor was off.
5. Arm counts within the mastery delayed-test sample (not reported; Table A5 gives shares only). Ask the authors if needed.
6. Whether an NBER working paper number exists for this paper and should be cited.

**Oreopoulos and Low (2026), Khanmigo.** Source: EdWorkingPaper 26-1551 (August 2026), DOI 10.26300/kner-hv33, local PDF `Oreopoulos and Low (2026) - One Click Away Khanmigo.pdf`.

1. Table 5 (p. 24), Panel C, Baseline column: 0.050 (SE 0.023), N 6,902, 53 clusters; Panel D 0.040 (0.019).
2. Table 7 (p. 27), Panel A: 0.016 (0.043), 0.116 (0.053), 0.066 (0.043), with N 1,214, 1,545, 2,759.
3. Table 2 (p. 15), pooled column, last row: 3,389 control and 3,513 treated student-terms.
4. The derived student count: 2,708 ever scheduled minus 236 never observed, from the Figure 1 note. Decide whether 2,472 should stay as the study-level count or be replaced.
5. The bundled classification: the paper itself says the contrast does not isolate the AI tutor. Confirm that "AI bundled with other changes" is the right category and that no row of this paper enters the default pool.
6. Whether AI was restricted during MAP testing (the paper does not say) and whether the TCAP outcome has been released in a later version.

**Cruces et al. (2026).** Source: arXiv 2608.04198 (May 2026 version), NBER Working Paper 34851, local PDF `Cruces et al (2026) - Does Generative AI Narrow Education-Based Productivity Gaps.pdf`.

1. Table 1 (p. 44), Follow-up column: 0.171 (0.087) for lower-education and 0.071 (0.080) for higher-education adults; control means 0.000 and 0.300.
2. Table A.3: arm counts 276/244 (lower education) and 336/318 (higher education); Table A.1: 1,795 randomized (922/873) and 1,174 completers (612/562).
3. The decision to enter the two education strata as separate full-sample rows rather than deriving a pooled effect. Check whether the NBER version reports a pooled follow-up effect; if it does, consider replacing the two rows with one.
4. Whether the follow-up module counts as learning under the atlas rule. The authors call it carry-over and the module was taken immediately after the task.
5. Whether a newer NBER or journal version changes the follow-up estimates.

**Heldreth et al. (2026).** Source: journal version of record, Frontiers in Artificial Intelligence 9:1783117 (DOI 10.3389/frai.2026.1783117), local PDF `Heldreth et al (2026) - AI-Powered Interactive Learning Platform.pdf`.

1. Section 5.2 and Tables 3 and 4 (p. 9). Immediate test: Learn Your Way mean 9.2 (SD 2.2, n = 30), Textbook mean 8.2 (SD 2, n = 30), Z = 1.89, p = 0.029. Follow-up test: 4.7 (SD 1.2, n = 29) and 4 (SD 1.4, n = 29), Z = 1.89, p = 0.03.
2. The derivations: pooled SDs of 2.10 and 1.30, Cohen's d of 0.476 and 0.537, and SEs of 0.262 and 0.267 from the large-sample formula. The means and SDs are rounded to one decimal, so d could lie between about 0.42 and 0.54 (immediate) and between 0.44 and 0.64 (follow-up). Check whether the supplementary material or the authors can give exact values.
3. The comparison type. The atlas codes both rows as AI versus business-as-usual, so both enter the default pool. The textbook arm had no quizzes or feedback, and the authors say the gains may come from the content transformations together with those features (Section 7.1). The AI platform itself generates the quizzes, which is why the rows are not coded as bundled. Both model extractions chose the bundled code, and one of them called AI versus business-as-usual a defensible alternative. Confirm or change this.
4. Whether the platform was closed during the immediate test, and whether students could use outside help on the remote follow-up. The paper states neither.
5. The effect size r in Table 4 is labeled a rank-biserial correlation, but the printed values equal Z divided by the square root of N. The atlas does not use r.
6. Time on task differed by arm (30:49 versus 22:05 minutes on average, Table 1). The paper reports no time-adjusted treatment effect.
7. Google LLC built the platform, funded the study, and took part in its design, analysis, and writing. Decide whether the atlas should show company involvement in a visible field.

**Rismanchian et al. (2026).** Source: arXiv 2605.21629 v3 (July 13, 2026), local PDF `Rismanchian et al (2026) - Faster Completion Less Learning.pdf`.

1. Section 2.4 (p. 7) and SI Tables 4, 8, 9, and 11 (pp. 18 to 23): ramp coefficient -0.0260 (SE 0.0125, p = 0.037; two-way SE 0.0121), cumulative odds ratio 0.75 over eleven quarters (bootstrap CI 0.56 to 0.98), randomization inference p = 0.056 unstratified and 0.027 stratified, N = 6,698 responses on 66 items.
2. Section 2.5 (p. 8) and Section 3.1.1 (p. 9): non-proctored coefficient +0.0561 (p = 0.021), an 85 percent increase in the odds, N = 3,223. The paper prints no SE or CI for it.
3. The decision to keep the odds ratios raw. The paper prints no baseline proportions (Figure 4 shows them only as a chart), so the atlas makes no SD conversion. Ask the authors for the proportions by item type and period if a standardized effect is wanted.
4. The design. No student's AI use is observed, and AI access is not assigned: the contrast is item type by time, as in Hausman et al. (2025). Confirm that this meets the atlas rule for quasi-experiments with an outcome assessed without AI.
5. The count of people. The paper reports item-level responses only. Each 30-question session carries one randomly assigned extra item, which suggests about one response per session, but the paper does not say so.
6. Three details in the paper do not match the retention sample as described. SI Table 10 applies a floor of 100 attempts per item-quarter cell to a sample that averages about 4.6 responses per cell. SI Table 6 lists placebo breaks in 2018 and 2019 for data that start in 2020 Q3. The text reports 2.61 percent per quarter and 25.0 percent, which correspond to a coefficient of -0.0261. Ask the authors or check a later version.
7. The timing code. The rows are coded as delayed because the outcome comes from a retake of the placement test after a preparation period. The paper does not report the interval.
8. Four of the five authors work for McGraw Hill, which owns ALEKS. Check for a published version.

**Barrera-Osorio and Muñoz-Morales (2026).** Source: working paper marked "Preliminary Results", June 19, 2026 (from the author's site), local PDF `Barrera-Osorio and Munoz-Morales (2026) - Complementing Teachers.pdf`; pre-analysis plan AEARCTR-0017147. PDF page numbers are one higher than the printed ones.

1. Table 5 (PDF p. 26), Panel B: column (2) 0.207 (SE 0.098), 2,264 observations, wild cluster bootstrap p = 0.056; column (5) 0.133 (SE 0.119), 1,604 observations, p = 0.311; columns (1) and (4) 0.198 (0.115) and 0.063 (0.142). Table 3 (PDF p. 25): 29, 28, and 20 schools.
2. The choice of main row. The authors prefer the comparison across blocks in the sample that drops blocks with a reassigned control school, and they do not choose between the columns with and without controls. The atlas uses column (2) because Table 6 repeats that specification. The pre-analysis plan names the within-block comparison in the sample with intact randomization as the main specification, and it plans tests at baseline and endline only.
3. Whether a preliminary midline estimate from a non-random subsample of 29 of the 158 schools should be in the atlas before the endline. The rows are coded as bundled, so they stay out of the default pool. Under the "AI bundled with other changes" filter, the site pools the main row with the Khanmigo row (+0.10 SD from two estimates). Replace the rows when the endline paper appears (expected after November 2026).
4. The bundled classification. Teachers received the platform together with a bootcamp, three workshops, four school visits, and three webinars. Teachers use the tool; students do not. Confirm that "AI bundled with other changes" is the right category.
5. How schools that declined the treatment enter the midline sample. The paper does not say, and the balance tables count them with the control schools (55 versus 103 schools in Appendix Table A.2).
6. Counts that disagree inside the paper. The text and Table 2 give different numbers of declining and reassigned schools. The regression samples (2,264 and 1,604) are smaller than the numbers of students tested in the same schools (2,324 and 1,644).
7. The standardization of the test score. Only the pre-analysis plan defines it: the share of correct answers on 18 multiple-choice questions, standardized by the mean and SD of the test-takers in each round.
8. Prior achievement. In the 28 schools, treated schools had higher 2019 exit-exam averages than control schools (0.082 versus -0.073, p = 0.072; Appendix Table A.4). Student baseline test scores were balanced.

### Suggested paper checked and not added

Cheng, Yin, Lin, Shi, Zheng, Zhu, Liu, Chen, and Dong (2024), "Chatbot dialogic reading boosts comprehension for Chinese kindergarteners with higher language skills", Journal of Experimental Child Psychology 240, 105842 (DOI 10.1016/j.jecp.2023.105842). The study randomly assigned 148 kindergarteners in Beijing in a 2 x 2 design (dialogic or non-dialogic reading, with a chatbot or a human partner). Claude read the full text on October 5, 2026. The chatbot is scripted, so the study does not meet the first criterion (generative AI). The chatbot follows a fixed 14-prompt dialogue script, and the human and chatbot narrators "used identical dialogic or non-dialogic scripts" (p. 4). It was "programmed based on speech synthesis, speech recognition, and semantic similarity measurement algorithms" (p. 4). It transcribes the child's answer, classifies it into one of four intent categories (correct, incorrect, unable to answer, irrelevant), and plays the prepared response for that category (p. 5). No language model writes the responses.

## Part B. RA-verified papers whose numbers changed after the RA rounds

The September 23 to 24, 2026 audit (Claude) changed the stored values of these rows after the human rounds. The archived release `2026-09-23-baseline` holds the pre-audit values; `2026-09-24.4` holds the post-audit values. An RA should confirm each change against the source.

| Paper | Rows changed | What changed |
| --- | --- | --- |
| Bassner et al. (2026) | est59, est60; Ns on est61, est62, est63, est84 | Gain effects and SEs recomputed in Stata from the public arm statistics (`code/audit/bassner_gain_precision.do`); contrast Ns now exclude the other AI arm |
| Contractor and Reyes (2026) | all nine rows | Re-pinned to the September 2026 PDF and the matching regression output (`code/sources/contractor-reyes-2026-09.json`); own paper |
| Franco et al. (2026) | est85, est86 | SD-unit effect, SE, and CI removed because the SD = 1.9 standardizer was not verified; raw coefficients kept in notes |
| Henkel et al. (2024) | est15 | Individual-level SE removed for a school-randomized trial |
| Lehmann et al. (2024) | sg2, sg4 | SE and CI removed because the required coefficient covariance is not reported |
| Lira et al. (2025) | est38 | SE corrected to 0.049 (Table S20); three-arm N removed |
| Liu et al. (2026) | sg1, sg4, sg5 | Sign orientation and CI endpoints corrected |
| Kalam et al. (2025) | both rows removed | Excluded under the 50-participant minimum (33 randomized) |

## How to record a verification

When an RA has checked a paper, edit `src/evidence_metadata.json`: remove the "not yet verified by a human research assistant" sentence from each of the paper's provenance notes, add "Verified by [name] on [date]" with any corrections applied, and move the paper out of Part A above. Metadata edits do not need an editorial receipt; changes to effect sizes, SEs, Ns, or classifications do go through the normal release process described in the README.
