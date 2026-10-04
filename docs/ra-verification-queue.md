# Human verification queue

Last updated: October 3, 2026. This file lists the atlas records that no human research assistant has checked against the source documents, and what the next RA should check. It is a working list, not a public page.

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
| Maier, Schwabe, Schneider, and Feuerriegel (2026), Designing Against Deskilling | October 3, 2026 | Claude | Not verified |
| Ates (2026), Human-centered GenAI feedback design | October 3, 2026 | Claude | Not verified; journal version not byte-checked |
| Oreopoulos, Liut, Sungu, and Low (2026), Making AI Tutoring Productive (NUMI) | October 3, 2026 | Claude | Not verified |
| Oreopoulos and Low (2026), One Click Away (Khanmigo) | October 3, 2026 | Claude | Not verified |
| Cruces, Fernández Meijide, Galiani, Gálvez, and Lombardi (2026) | October 3, 2026 | Claude | Not verified |
| Franco, Irmert, and Isaksson (2026) | August 23, 2026 | Claude | Not verified; the September 23 audit removed its SD conversion |
| Stromberg, Lei, and Wu (2026), observational | July 8, 2026 | Claude | Added after round 1; not named in the round 2 or round 3 commit messages, so verification is undocumented |

### What to check for each new paper

Every record for these papers carries this sentence in its provenance notes: "Extracted and checked by Claude (model) against the linked PDF on 2026-10-03; not yet verified by a human research assistant." The checks below are the ones a person should do before that sentence is removed.

**Maier et al. (2026).** Source: arXiv 2609.20143 v1, local PDF `Maier et al (2026) - Designing Against Deskilling.pdf`.

1. Table 2 (p. 14): arm N, mean, and SD of unaided performance for all five arms. The atlas uses 146/0.65/0.32, 137/0.62/0.34, 144/0.67/0.30, 138/0.58/0.32, 139/0.64/0.34.
2. Appendix H, Table 8 (p. 39): the H1 difference of -2.57 percentage points with CI [-10.28, 5.14], the H2b difference +5.28 [-0.14, 10.70], and the H3b difference -3.53 [-8.95, 1.89].
3. The derivations: pooled SD of the AI-only and control arms (0.330), pooled SD of the four AI arms (0.325), Cohen's d for the three design arms versus control from the rounded Table 2 statistics.
4. Whether the anonymized repository (footnote 4) now gives exact per-arm statistics or a public dataset. If so, replace the rounded-input d values with exact ones.
5. Whether a later arXiv version or a published version exists.

**Ates (2026).** Source: Research Square preprint v1, local PDF `Ates (2026) - Human-Centered GenAI Feedback Design.pdf`; version of record at DOI 10.1186/s41239-026-00614-9.

1. Obtain the journal PDF and supplement and confirm that Table 4 Panel B and Table 5 Panels A and B match the preprint values used here (b, SE, Cohen's d, CI for every contrast).
2. Confirm the arm sizes in Table 3 (293, 295, 294, 294) and the 1,248 enrolled / 1,176 analyzed counts.
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
