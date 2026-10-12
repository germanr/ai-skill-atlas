# Included-study lists of three meta-analyses (2026-10-04)

Search input for the creativity screening. Produced by a read-only sub-agent; every entry is rechecked downstream.

I found and read all three meta-analyses and checked every primary study's link. Holzner (28 studies) and de Rooij & Biskjaer 2026 (18 articles) have full lists. The ECCE 2025 list (15 articles) has one link I could not find (Bangerl et al.). Your 28-name Holzner list is correct. Your descriptions of meta-analyses 2 and 3 each need a correction (see the flags section).

**How I checked:**
- **Sources read in full:**
  - Holzner: the arXiv PDF plus the authors' GitHub data files.
  - ECCE 2025: the final published PDF (pure.au.dk/ws/files/465399318/3746175.3746189.pdf) and the accepted manuscript.
  - Homogenization: the OSF preprint.
- **Links:** DOIs were checked against Crossref (or OpenAlex where Crossref had no record, plus doi.org for two odd ones), arXiv IDs against the arXiv API, and other URLs by opening them.

**Codes used below:**
- **Comparison entered:**
  - **HAI:** AI output vs human output.
  - **CP:** people with AI vs without, creativity score.
  - **CD:** people with AI vs without, diversity score.
- **Rand.:** were people randomly assigned to AI assistance (Y / N / ?). The basis is in brackets: [abs] the paper's abstract, [MA] the meta-analysis's coding, [txt] the paper body.

## 1. Holzner, Maier & Feuerriegel (2025)

**A. Record**
- **Title:** "Generative AI and Creativity: A Systematic Literature Review and Meta-Analysis" (LMU Munich).
- **Status:** arXiv preprint, arXiv:2505.17241. Only v1 exists (22 May 2025); no journal version found. Data and code: github.com/SM2982/Meta-Analysis-LLMs-Creativity.
- **Search end:** 2 May 2025. Databases: Web of Science, SSRN, arXiv; English; past five years; plus 2 studies added by hand.
- **Inclusion:** between-subject experiments comparing either humans vs GenAI, or humans with vs without GenAI. Each needs statistics for Hedges' g and an established creativity measure (novelty, originality, diversity). Total: 28 studies, 127 effect sizes, 8,214 participants.
- **Pooled estimates** (random effects, DerSimonian–Laird, Hedges' g):
  - GenAI output vs humans: g = −0.048 [−0.257, 0.161], 100 effect sizes. Trim-and-fill gives 0.364 [0.131, 0.596].
  - Humans with GenAI vs humans alone, creativity: g = 0.273 [0.018, 0.528], 21 effect sizes.
  - Humans with GenAI vs humans alone, diversity: g = −0.863 [−1.328, −0.398], 6 effect sizes from 4 studies.
- **Diversity unit and standardizer:** not stated in the text. The repo file Human-AI_Diversity.csv shows the inputs:
  - Doshi & Hauser, Doshi et al. and Ismayilzada et al.: regression coefficients ± SE on cosine similarity.
  - Chen & Chan: group means and SDs of cosine distance.

**B. Included studies** (Table 2 order; ID with number of effect sizes)

| # | ID | Study | Exact title | Venue | Link | Rand. |
|---|---|---|---|---|---|---|
| 1 | HAI01 (12) | Gómez-Rodríguez & Williams 2023 | A Confederacy of Models: a Comprehensive Evaluation of LLMs on Creative Writing | Findings of EMNLP 2023 (cited as arXiv) | arXiv:2310.08433; 10.18653/v1/2023.findings-emnlp.966 | N |
| 2 | HAI02 (6) | Zhang et al. 2025 | AI Delivers Creative Output but Struggles with Thinking Processes | arXiv | arXiv:2503.23327 | N |
| 3 | HAI03 (1), CP01 (6) | Lee & Chung 2024 | An empirical investigation of the impact of ChatGPT on creativity | Nat Hum Behav 8(10) | 10.1038/s41562-024-01953-1 | Y (Meincke et al.'s preprint describes these experiments as randomized; Lee & Chung's own abstract doesn't say) |
| 4 | HAI04 (1) | Grassini & Koivisto 2025 | Artificial Creativity? Evaluating AI Against Human Performance in Creative Interpretation of Visual Stimuli | IJHCI 41(7) | 10.1080/10447318.2024.2345430 | N |
| 5 | HAI05 (1) | Haase & Hanel 2023 | Artificial muses: Generative artificial intelligence chatbots have risen to human-level creativity | J Creativity 33(3) | 10.1016/j.yjoc.2023.100066 | N |
| 6 | HAI06 (1) | Koivisto & Grassini 2023 | Best humans still outperform artificial intelligence in a creative divergent thinking task | Sci Rep 13 | 10.1038/s41598-023-40858-3 | N |
| 7 | HAI07 (1) | Si, Yang & Hashimoto 2024 | Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers | arXiv | arXiv:2409.04109 | N |
| 8 | HAI08 (2), CP02 (1) | Bohren, Hakimov & Lalive 2024 | Creative and Strategic Capabilities of Generative AI: Evidence from Large-Scale Experiments | IZA DP 17302 | docs.iza.org/dp17302.pdf; SSRN 10.2139/ssrn.4963992 (the cited hdl:10419/305744 could not be checked: EconStor blocks scripts) | Y [txt: randomly assigned to HumanBaseline / HumanAgainstAI / HumanPlusAI; AI use optional within HumanPlusAI] |
| 9 | HAI09 (4) | Charness & Grieco 2024 | Creativity and AI | SSRN WP | 10.2139/ssrn.4686415 | N |
| 10 | HAI10 (1), CP03 (3) | McGuire, De Cremer & Van de Cruys 2024 | Establishing the importance of co-creation and self-efficacy in creative collaboration with artificial intelligence | Sci Rep 14 | 10.1038/s41598-024-69423-2 | ? [abs: "two experimental studies"] |
| 11 | HAI11 (1), CD03 (1) | Ismayilzada, Stevenson & van der Plas 2024 | Evaluating Creative Short Story Generation in Humans and Large Language Models | arXiv | arXiv:2411.02316 | N (60 LLMs vs 60 people) |
| 12 | CP04 (1) | Zou & Zhu 2025 | Generative AI Adoption in Human Creative Tasks: Experimental Evidence | SSRN WP; now J Econ Behav Organ 2026, authors listed as Zhu & Zou | 10.2139/ssrn.5196748; 10.1016/j.jebo.2026.107414 | ? (abstract unreachable) |
| 13 | CP05 (2), CD01 (2) | Doshi & Hauser 2024 | Generative AI enhances individual creativity but reduces the collective diversity of novel content | Sci Adv 10(28) | 10.1126/sciadv.adn5290 | Y [MA3 "Controlled"; abs: online experiment, "causal impact"] |
| 14 | HAI12 (1) | Ashkinaze et al. 2024 | How AI Ideas Affect the Creativity, Diversity, and Evolution of Human Ideas: Evidence From a Large, Dynamic Experiment | arXiv; later ACM CI '25 | arXiv:2401.13481; 10.1145/3715928.3737481 | Y [MA3 "Controlled"; abs: AI-exposure conditions varied] |
| 15 | HAI13 (1) | Castelo, Katona, Li & Sarvary 2024 | How AI Outperforms Humans at Creative Idea Generation | SSRN WP | 10.2139/ssrn.4751779 | N per both meta-analyses' descriptions (abstract unreachable) |
| 16 | CP06 (1), CD02 (1) | Doshi, Chai & Troebinger 2024 | How Experience Moderates the Impact of Generative AI Ideas on the Research Process | SSRN WP; now Research Policy 2026 (Tröbinger, Doshi & Chai, new title) | 10.2139/ssrn.5013086; 10.1016/j.respol.2026.105575 | Y [abs: "pre-registered randomized online experiment with 310 researchers"] |
| 17 | CP07 (1) | Mei et al. 2025 | If ChatGPT can do it, where is my creativity? generative AI boosts performance but diminishes experience in creative writing | CHB: Artificial Humans 4 | 10.1016/j.chbah.2025.100140 | ? [abs: "experimental design … compared to a control group"] |
| 18 | CP08 (1) | Song et al. 2025 | Interactions with generative AI chatbots: unveiling dialogic dynamics, students' perceptions, and practical competencies in creative problem-solving | Int J Educ Technol High Educ 22 | 10.1186/s41239-025-00508-2 | N [abs: "quasi-experiments", chatbot vs peers] |
| 19 | HAI14 (1), CP09 (1), CD04 (2) | Chen & Chan 2024 | Large Language Model in Creative Work: The Role of Collaboration Modality and User Expertise | Mgmt Sci 70(12) | 10.1287/mnsc.2023.03014 | Y [MA3 "Controlled"; abs: experiment with and without LLM] |
| 20 | CP10 (1) | Zheng, Wong, Zhou & Koh 2024 | Large Language Model in Ideation for Product Innovation: An Exploratory Comparative Study | SSRN WP | 10.2139/ssrn.4729982 | ? (abstract unreachable) |
| 21 | HAI15 (52) | Sun et al. 2024 | Large Language Models show both individual and collective creativity comparable to humans | arXiv | arXiv:2412.03151 | N |
| 22 | HAI16 (1) | Wu, Weber & Müller 2025 | One Does Not Simply Meme Alone: Evaluating Co-Creativity Between LLMs and Humans in the Generation of Humor | IUI '25 | 10.1145/3708359.3712094 | ? [abs: groups of 50 human-only / human-AI / AI-only] |
| 23 | HAI17 (1), CP11 (1) | Eisenreich et al. 2024 | Revolution or inflated expectations? Exploring the impact of generative AI on ideation in a practical sustainability context | Technovation 138 | 10.1016/j.technovation.2024.103123 | ? [abs: AI-based vs expert-workshop ideation at one firm] |
| 24 | CP12 (2) | Boussioux et al. 2024 | The Crowdless Future? Generative AI and Creative Problem-Solving | Org Sci 35(5) | 10.1287/orsc.2023.18430 | N [abs: crowd solutions vs GPT-4 solutions prompted by the researchers] |
| 25 | HAI18 (5) | Hubert, Awa & Zabelina 2024 | The current state of artificial intelligence generative language models is more creative than humans on divergent thinking tasks | Sci Rep 14 | 10.1038/s41598-024-53303-w | N |
| 26 | "HAI20" (2) | Orwig et al. 2024 | The Language of Creativity: Evidence from Humans and Large Language Models | J Creat Behav 58(1) | 10.1002/jocb.636 | N |
| 27 | "HAI21" (3) | Wenger & Kenett 2025 | We're Different, We're the Same: Creative Homogeneity Across LLMs | arXiv | arXiv:2501.19361 | N |
| 28 | "HAI22" (2) | de Vicente-Yagüe-Jara et al. 2023 | Writing, creativity, and artificial intelligence. ChatGPT in the university context | Comunicar 31(77) | 10.3916/C77-2023-04 | N [abs: non-experimental AI vs students, plus a quasi pre/post phase] |

## 2. Biskjaer & de Rooij (2025), whose full text is de Rooij & Biskjaer, ECCE 2025

**A. Record**
- **The title you gave is a one-page conference abstract:** Biskjaer & de Rooij, "Generative AI has not (yet?) surpassed humans in creative idea generation: A meta-analysis (2022-2025)", 9th MIC Conference, Bolzano, 3–6 Sep 2025. The Tilburg portal lists it as "Accepted/In press"; it has no DOI. Your repository link returned 403 (web) and 401 (API), so I could not open that specific record.
- **Full text:** de Rooij & Biskjaer, "Has AI Surpassed Humans in Creative Idea Generation? A Meta-Analysis".
  - Venue: ECCE '25, Proceedings of the 36th Annual Conference of the European Association of Cognitive Ergonomics (Tallinn), Article 10, pp. 1–11. Published 6 Oct 2025, CC BY.
  - DOI: 10.1145/3746175.3746189.
  - Preprints: 10.31234/osf.io/9u2ke_v1 and _v2. OSF materials: osf.io/2xdba.
- **Search window:** Jan 2022 – Jan 2025. Databases: Web of Science, ACM DL, DRS DL, Google Scholar titles, plus repeated backward and forward citation tracking.
- **Inclusion:** experiments comparing human ideas with ideas from prompting GenAI using similar instructions and no further interaction (co-creation excluded). Tasks must be discrete idea generation, rated blind on creativity, originality or usefulness. Total: 15 articles, 17 studies, 115 effect sizes.
- **Pooled estimates** (three-level, Cohen's d; positive favors GenAI):
  - All GenAI vs humans: d = .360 [−.071, .790]; without 14 influential values, .236 [−.073, .544].
  - ChatGPT vs humans: d = .478 [−.040, .996]; without 2 influential values, .374 [−.047, .975].
  - Originality relative to usefulness: .323 [.040, .606], not significant after the sensitivity analysis.
- **Diversity:** not analyzed.

**B. Included studies.** Every row entered as HAI; Rand. is N for all, since the AI was prompted alone and no participant used it.

| Ref | Study | Title | Venue | Link | Comparison |
|---|---|---|---|---|---|
| [2] | Bangerl, Stefan & Pammer-Schindler 2024 | Explorations in human vs. generative AI creative performances: A study on human-AI creative potential | TREW workshop, CHI EA '24 | not found | student dyads vs 10 GenAI models; AUT |
| [6] | Boussioux et al. 2024 | as in table 1 | Org Sci | 10.1287/orsc.2023.18430 | crowd vs GPT-4 |
| [8] S1, S2 | Castelo et al. 2024 | cited as "Frontiers: Determining the validity of large language models for automated perceptual analysis" (see flags) | Marketing Science | cited 10.1287/mksc.2023.0454 | experts vs GPT-4; app ideas (S1), product-invention ideas (S2) |
| [10] S1, S2 | Charness & Grieco 2024 | Creativity and AI | SSRN | 10.2139/ssrn.4686415 | students vs GPT-3.5 (S1) and GPT-4 (S2) |
| [15] | Eisenreich et al. 2024 | as in table 1 | Technovation | 10.1016/j.technovation.2024.103123 | experts vs GPT-4 |
| [28] | Haase & Hanel 2023 | as in table 1 | J Creativity | 10.1016/j.yjoc.2023.100066 | crowd vs 5 models; AUT |
| [33] | Hubert et al. 2024 | as in table 1 | Sci Rep | 10.1038/s41598-024-53303-w | crowd vs GPT-4; AUT |
| [38] | Koivisto & Grassini 2023 | as in table 1 | Sci Rep | 10.1038/s41598-023-40858-3 | crowd vs 3 models; AUT |
| [39] S2b | Lee & Chung 2024 | as in table 1 | Nat Hum Behav | 10.1038/s41562-024-01953-1 | crowd vs GPT-3.5; Study 2b only |
| [42] | Maltese, Pelletier & Guichardaz 2024 | Can AI Enhance its Creativity to Beat Humans ? | arXiv | arXiv:2409.18776 | students vs GPT-4; vs GPT-4 + DALL·E 2 |
| [45] | Meincke, Girotra, Nave, Terwiesch & Ulrich 2024 | Using Large Language Models for Idea Generation in Innovation | Wharton School Research Paper | rotmandigital.ca/wp-content/uploads/2024/11/Using-Large-Language-Models-for-Idea-Generation-in-Innovation.pdf | students (before LLMs) vs GPT-4 |
| [50] S3 | Raz, Reiter-Palmon & Kenett 2024 | Open and closed-ended problem solving in humans and AI: The influence of question asking complexity | Think Skills Creat 53 | 10.1016/j.tsc.2024.101598 | crowd vs GPT-4 |
| [60] | Si et al. 2024 | as in table 1 | arXiv | arXiv:2409.04109 | experts vs Claude 3.5 |
| [66] | Stevenson et al. 2022 | Putting GPT-3's Creativity to the (Alternative Uses) Test | ICCC 2022 | arXiv:2206.08932 | students vs GPT-3; AUT |
| [67] | Sun et al. 2024 | as in table 1 | arXiv | arXiv:2412.03151 | students vs 5 models |

## 3. de Rooij & Biskjaer (2026), homogenization

**A. Record.** There are three outputs, all reporting the same data (19 studies, 61 effect sizes).
- **Preprint:** "Does Generative AI Make Us Think Alike? A Systematic Review and Meta-Analysis of Homogenization Effects in Human–AI Co-Creation", PsyArXiv, 10.31234/osf.io/rz5s4_v1 (dated 15 Apr 2026; only v1 exists). Read in full.
- **Journal version** (OSF links the preprint to it): "Does generative AI make us think alike? A systematic review and meta-analysis of homogenisation effects in human–AI co-creation".
  - Venue: Behaviour & Information Technology, e-pub 31 Aug 2026, pp. 1–14, CC BY.
  - DOI: 10.1080/0144929X.2026.2726451.
  - Full text unreachable. Its abstract matches the preprint, and its Crossref reference list contains all 18 included articles.
- **Short paper:** "Generative AI Makes Creative Output More Homogeneous".
  - Venue: Proceedings of ECCE 2026 (Siena), pp. 198–201, 14 Sep 2026.
  - DOI: 10.1145/3822301.3822304.
  - Full text unreachable. The abstract reports 19 studies, 61 effect sizes, d = .334; its references also contain all 18 included articles.
- **Search:** 2022 to 25 Feb 2026. Databases: Web of Science, ACM DL, PsycINFO, Google Scholar (top 200), arXiv, PsyArXiv, SSRN, ProQuest Dissertations; ASReview-assisted screening plus citation tracking.
- **Inclusion:** experiments comparing GenAI users with non-users on a group-level homogenization outcome scored on creative output, during or after AI use. A human–AI co-creative interaction is required; surface lexical similarity and individual-level-only diversity are excluded.
- **Pooled estimates** (three-level, Cohen's d; positive means more homogeneous with AI):
  - Overall: d = .334 [.094, .574]; without one influential study, .247 [.065, .429].
  - By task: idea generation .70 [.30, 1.10]; divergent thinking .12 [−.285, .518]; writing .27 [−.078, .613]; visual art .27 [−.555, 1.088].
  - By timing: during co-creation .453 [.048, .953]; after AI use .414 [.235, .593].
  - By setting (writing and visual tasks only): controlled .255 [.034, .477]; quasi-experiments .303 [.082, .524].
- **Unit of analysis:** each participant's response, scored by cosine distance between sentence embeddings against all responses in the sample, or by expert ratings relative to the sample.
- **Standardizer:** not stated beyond "Cohen's d and sampling variance from reported statistics". One study was computed from raw data (Padmakumar & He); two were digitized from graphs (Kumar et al., Wadinambiarachchi et al.).
- **Meaning of the "Controlled" code:** the paper defines "Controlled" as "randomized experiments conducted in controlled settings", so [MA] = Y below.
- **Peer review:** † marks studies not peer-reviewed at the time of the review.

**B. Included studies**

| Ref | Study | Exact title | Venue | Link | Comparison (task; timing; design) | Rand. |
|---|---|---|---|---|---|---|
| [1] | Agarwal, Naaman & Vashistha 2025 | AI Suggestions Homogenize Writing Toward Western Styles and Diminish Cultural Nuances | CHI '25 | 10.1145/3706598.3713564 | human vs human + GPT-4o suggestions; writing; during; controlled | Y [MA]; abstract doesn't describe assignment |
| [3, 4] | Anderson, Shah & Kreminski 2024 (2 papers, 1 study) | Evaluating Creativity Support Tools via Homogenization Analysis; Homogenization Effects of Large Language Models on Human Creative Ideation | CHI EA '24; C&C '24 | 10.1145/3613905.3651088; 10.1145/3635636.3656204 | human + Oblique Strategies vs human + ChatGPT-3.5; idea generation; during; controlled | Y [MA]; abs: "36-participant comparative user study" |
| [5] | Ashkinaze et al. 2025 | as in table 1 | ACM CI '25 | 10.1145/3715928.3737481 | 6 human example ideas vs 4 GPT-3.5 + 2 human, and vs 2 GPT-3.5 + 4 human; divergent thinking; during; controlled | Y [MA] |
| [6] | Baltà-Salvador, Brasò-Vives & Peña 2026 | Evaluating AI-assisted creative ideation: A crossover study in higher education | Think Skills Creat 59 | 10.1016/j.tsc.2025.101958 | human vs human + ChatGPT-3.5; idea generation; during; controlled | Y [abs: randomised crossover] |
| [11] | Chen & Chan 2024 | as in table 1 | Mgmt Sci | 10.1287/mnsc.2023.03014 | GPT-4 feedback; GPT-4 example texts; writing; during; controlled | Y [MA] |
| [19] | Doshi & Hauser 2024 | as in table 1 | Sci Adv | 10.1126/sciadv.adn5290 | 1 or 5 GPT-4 ideas; writing; during; controlled | Y [MA] |
| [37] | Kumar, Vincentius, Jordan & Anderson 2025 | Human Creativity in the Age of LLMs: Randomized Experiments on Divergent and Convergent Thinking | CHI '25 | 10.1145/3706598.3714198 | GPT-4o idea list; GPT-4o SCAMPER; divergent thinking; during and after; controlled | Y [abs] |
| [38]† | Lai, Luchini, Lauharatanahirun & Beaty 2025 | Creative or Uncreative Partner: Comparing Humans and AI in Collaborative Creative Tasks | PsyArXiv | 10.31234/osf.io/ey7u4_v1 | human pair vs human + GPT-4o partner; writing; during; controlled | Y [abs: "randomly assigned"] |
| [42]† | Luchini et al. 2025 | The Roles of Idea Generation and Elaboration in Human-AI Collaborative Creativity | PsyArXiv | 10.31234/osf.io/xm2f5_v1 (BIT cites _v2) | GPT-3.5 access; writing; during; controlled | ? (meta-analysis says controlled; abstract calls it a "naturalistic study") |
| [43]† | Maier, Schneider & Feuerriegel 2025 | Partnering with Generative AI: Experimental Evaluation of Human-Led and Model-Led Interaction in Human-AI Co-Creation | arXiv; CHI '26 version | arXiv:2510.23324; 10.1145/3772318.3791185 | GPT-4.1 access, three modes; idea generation; during; controlled | Y [abs: "randomized controlled experiment"] |
| [45] (2a, 2b) | Meincke, Nave & Terwiesch 2025 | ChatGPT decreases idea diversity in brainstorming | Nat Hum Behav 9(6) | 10.1038/s41562-025-02173-x | GPT-3.5 vs none, reanalyzing Lee & Chung's experiments 2a/2b; divergent thinking (2a), idea generation (2b); controlled | Y (randomized per its preprint abstract) |
| [46]† | Moon, Kushlev, Bank & Green 2025 | Impersonal Statements: LLM-Era College Admissions Essays Exhibit Deep Homogenization Despite Lexical Diversity | PsyArXiv / OSF | cited 10.17605/OSF.IO/P58K3 (resolves to osf.io/p58k3, listed there as "(a Replication Study)"); BIT cites 10.31234/osf.io/jsz58_v1 | essays before vs after ChatGPT; writing; quasi | N |
| [48] | Padmakumar & He 2024 | Does Writing with Language Models Reduce Content Diversity? | ICLR 2024 | arXiv:2309.05196 | GPT-3; InstructGPT; writing; during; controlled | Y [MA] |
| [64] | Wadinambiarachchi et al. 2024 | The Effects of Generative AI on Design Fixation and Divergent Thinking | CHI '24 | 10.1145/3613904.3642919 | Midjourney image examples; visual design; during; controlled | Y [MA]; abs: between-participants, N = 60 |
| [65]† | Wan & Kalman 2025 | Using Generative AI Personas Increases Collective Diversity in Human Ideation (v1; now titled "Diverse AI personas can mitigate the homogenization effect in human-AI collaborative ideation") | arXiv; CHB: Artificial Humans 2026 | arXiv:2504.13868; 10.1016/j.chbah.2026.100289 | 1 or 5 o1-preview story plots; writing; during; controlled | Y [MA] |
| [69] | Zhou & Lee 2024 | Generative artificial intelligence, human creativity, and art | PNAS Nexus 3(3) | 10.1093/pnasnexus/pgae052 | artworks before vs after AI adoption; visual art; quasi | N |
| [70] (1), (2) | Zhou, Liu, Huang & Li 2025 | Creative scar without generative AI: Individual creativity fails to sustain while homogeneity keeps climbing | Technol Soc 84 (Mar 2026) | 10.1016/j.techsoc.2025.103087 | (1) papers before vs after ChatGPT, quasi; (2) ChatGPT-4 vs none, divergent thinking and ideas, during and after, controlled | (1) N; (2) Y [MA] |

## Merged, de-duplicated list (48 articles, 47 lines)

**H** = Holzner; **E** = ECCE 2025; **D** = de Rooij & Biskjaer 2026. No study is in all three. Holzner and ECCE 2025 share 10; Holzner and the homogenization paper share 3. Lee & Chung's data also reaches the homogenization paper through Meincke et al. 2025.

| Study | H | E | D | Rand. |
|---|---|---|---|---|
| Agarwal 2025 | – | – | yes | Y |
| Anderson 2024a,b | – | – | yes | Y |
| Ashkinaze 2024/25 | HAI | – | yes | Y |
| Baltà-Salvador 2026 | – | – | yes | Y |
| Bangerl 2024 | – | yes | – | N |
| Bohren 2024 | HAI, CP | – | – | Y |
| Boussioux 2024 | CP | yes | – | N |
| Castelo 2024 | HAI | yes (miscited) | – | N |
| Charness & Grieco 2024 | HAI | yes | – | N |
| Chen & Chan 2024 | HAI, CP, CD | – | yes | Y |
| de Vicente-Yagüe-Jara 2023 | HAI | – | – | N |
| Doshi & Hauser 2024 | CP, CD | – | yes | Y |
| Doshi, Chai & Troebinger 2024 | CP, CD | – | – | Y |
| Eisenreich 2024 | HAI, CP | yes | – | ? |
| Gómez-Rodríguez 2023 | HAI | – | – | N |
| Grassini & Koivisto 2025 | HAI | – | – | N |
| Haase & Hanel 2023 | HAI | yes | – | N |
| Hubert 2024 | HAI | yes | – | N |
| Ismayilzada 2024 | HAI, CD | – | – | N |
| Koivisto & Grassini 2023 | HAI | yes | – | N |
| Kumar 2025 | – | – | yes | Y |
| Lai 2025 | – | – | yes | Y |
| Lee & Chung 2024 | HAI, CP | yes (S2b) | via Meincke 2025 | Y |
| Luchini 2025 | – | – | yes | ? |
| Maier 2025/26 | – | – | yes | Y |
| Maltese 2024 | – | yes | – | N |
| McGuire 2024 | HAI, CP | – | – | ? |
| Mei 2025 | CP | – | – | ? |
| Meincke, Girotra et al. 2024 | – | yes | – | N |
| Meincke, Nave & Terwiesch 2025 | – | – | yes | Y |
| Moon 2025 | – | – | yes (quasi) | N |
| Orwig 2024 | HAI | – | – | N |
| Padmakumar & He 2024 | – | – | yes | Y |
| Raz 2024 | – | yes | – | N |
| Si 2024 | HAI | yes | – | N |
| Song 2025 | CP | – | – | N |
| Stevenson 2022 | – | yes | – | N |
| Sun 2024 | HAI | yes | – | N |
| Wadinambiarachchi 2024 | – | – | yes | Y |
| Wan & Kalman 2025 | – | – | yes | Y |
| Wenger & Kenett 2025 | HAI | – | – | N |
| Wu 2025 | HAI | – | – | ? |
| Zhang 2025 | HAI | – | – | N |
| Zheng 2024 | CP | – | – | ? |
| Zhou & Lee 2024 | – | – | yes (quasi) | N |
| Zhou, Liu et al. 2025 | – | – | yes | Study 1 N; Study 2 Y |
| Zou & Zhu 2025 | CP | – | – | ? |

Tally: 17 Y, 7 ?, 23 N.

## Flags on your starting information
- **Holzner list:** correct. All 28 first authors and years match Table 2, in Table 2 order. The source itself has these problems:
  - **ID numbering:** Table 2 skips HAI19. The rows labelled HAI20/21/22 (Orwig; Wenger & Kenett; de Vicente-Yagüe-Jara) are HAI19/20/21 in the forest plot and data files. The total is still 21 AI-vs-human studies.
  - **Two wrong titles in Table 2:** Doshi & Hauser appears as "Generative artificial intelligence enhances creativity but reduces the diversity of novel content", and Boussioux et al. appears under its working-paper title. The reference list has the correct titles.
  - **Ismayilzada et al.:** entered the human-with-AI diversity analysis (CD03), but the paper and its data row compare LLM stories with human stories; there is no human-with-AI condition.
- **Meta-analysis 2:**
  - **Wrong item:** the title and author order you gave belong to the one-page MIC abstract. The full text is the ECCE 2025 paper, with a different title and de Rooij as first author.
  - **Count:** the 17 studies come from 15 articles.
  - **Miscited reference [8]:** the DOI in reference [8] resolves to a different Castelo paper: Li, Castelo, Katona & Sarvary, Marketing Science 43(2):254–266, a market-research paper. The idea-generation studies described in its Table 1 are probably SSRN 4751779, but I couldn't confirm that.
- **Meta-analysis 3:**
  - **Three outputs, not two:** the preprint became the Behaviour & Information Technology article, and the ECCE 2026 paper is a separate four-page version.
  - **Counts:** the 19 studies come from 18 articles, and three of the 19 are quasi-experiments.
  - **Bad reference [39]:** reference [39], "Dokyun Lee & Jonah Chung 2024 … doi:10.1038/s41562-024-01898-1", is not registered at doi.org. It is cited in the text only, not in Table 1, and is repeated in the journal and ECCE 2026 reference lists.
  - **Volume number:** Zhou et al. is cited as volume 75 (2025); Crossref gives volume 84 (Mar 2026).

## Not reachable
- **Full texts:**
  - Behaviour & Information Technology article (Taylor & Francis and Tilburg, 403/404).
  - ECCE 2026 paper (ACM and Tilburg, 403).
  - Your Tilburg repository record (403/401).
- **Abstracts:**
  - SSRN pages (403): Castelo, Zheng, Zou & Zhu.
  - ScienceDirect (403): Zou & Zhu, Zhou et al. Zhou et al.'s design description comes only from a search-engine snippet.
- **Links:**
  - Bohren's EconStor handle is behind a bot check, so I used the IZA PDF instead.
  - Bangerl et al. 2024 has no DOI or URL anywhere I could find.
