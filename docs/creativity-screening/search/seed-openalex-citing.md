# OpenAlex works since 2025-01-01 that cite eight anchor experiments (2026-10-04)

Search input for the creativity screening. Produced by a read-only sub-agent; every entry is rechecked downstream.

I screened all 1,100 OpenAlex works citing the anchors (dated 2025-01-01 to 2026-10-04) and shortlisted about 265. The 90 most relevant are listed below. Nine are randomized experiments where the abstract states random assignment; another 22 are controlled experiments whose abstracts don't state randomization. Screening was hand-coded from titles plus abstract excerpts, and the randomization labels rely on abstract wording.

## 1. Anchors

| | Anchor | OpenAlex record | Cited-by | Citing since 2025-01-01 |
|---|---|---|---|---|
| A1 | Doshi & Hauser 2024 | W4400578758 (Sci Adv) | 760 | 715 |
| | | W4385820196 (SSRN) / W4389325962 (arXiv) / W7113772747 (RePEc) | 116 / 7 / 0 | 64 / 6 / 0 |
| | | all A1 records, de-duplicated | | 783 |
| A2 | Lee & Chung 2024 | W4401518309 | 171 | 166 |
| A3 | Padmakumar & He | W4386651352 (arXiv; no separate ICLR record found) | 21 | 14 |
| A4 | Anderson, Shah & Kreminski 2024 | W4391556516 | 170 | 158 |
| A5 | Kumar et al. 2025 | W4409746216 (CHI; no separate arXiv record found) | 51 | 50 |
| A6 | Meincke, Nave & Terwiesch 2025 | W4410374906 / W4405226672 (OSF preprint) | 32 / 2 | 32 / 2 |
| A7 | Girotra et al. (SSRN 4526071) | W4385447813 | 179 | 109 |
| | | W7170184151 (2026 journal article) | 1 | 1 |
| A8 | Liu et al. 2024 | W4390961159 (arXiv) / W4415999555 (AoM Proceedings abstract) | 9 / 1 | 8 / 1 |
| | | W4414497210 (Technology in Society 2025, "Creative scar without generative AI") | 22 | 22 |

- **A7 mismatch:** the DOI 10.2139/ssrn.4526071 resolves to a record titled "AI and Its Impact on Creativity and Diversity: An Empirical Study of LLM-Generated Product Ideas." Its listed authors are Terwiesch, Meincke, Girotra, Mollick and Nave. No OpenAlex record is titled "Ideas are Dimes a Dozen." W7170184151 has the same title and adds Ulrich as an author (DOI 10.1177/10591478261474243).
- **A2 lookalike:** OSF record W7116130859 has the Lee & Chung title but is authored by Abel Brodeur and has 0 citations. It is not an anchor version.

## 2. Totals
- **Examined:** 1,100 unique citing works. None is dated after 2026-10-04.
- **Excluded as anchors or anchor versions:** 4 (W4409746216, W4410374906, W4414497210, W7170184151).
- **Merged:** 8 preprint/journal duplicate records of shortlisted papers.
- **Shortlisted:** about 265, of which 90 are listed below. The other ~175 are mostly cross-sectional surveys of GenAI use and self-reported creativity, qualitative or interview studies, and system papers with small user studies. The rest are experiments on how people perceive AI-made art or designs, and items judged from the title alone.
- **Dropped:** about 823. These reason counts are approximate hand tallies:

| Reason | Approx. count |
|---|---|
| No creativity, ideation or diversity outcome (learning, productivity, adoption, trust, writing quality, labor, innovation-behavior surveys) | 500 |
| Commentary, theory, essays, editorials, news, chapters without own data | 215 |
| Reviews, meta-analyses, bibliometric maps | 60 |
| Model-only benchmarks or simulations | 40 |
| Creativity studies with no GenAI component | 8 |

## 3. Shortlist (90)

**Labels:**
- **RCT** = random assignment stated in the abstract.
- **RCT?** = controlled or between-subjects GenAI conditions, but randomization not stated.
- **Other exp.** = within-subject, quasi-experimental, pre-post, system user study, or human-vs-AI comparison.
- **Obs. corpus** = observational corpus of human output.
- **Unclear [abstract unclear]** = no usable abstract in OpenAlex; the guess comes from the title.
- "N —" means no N appears in the OpenAlex abstract text.

Within RCT and RCT?, works from May 2026 onward come first.

**A. RCT (randomization stated)**
1. Carvalho Milano et al. (2026); Human-GenAI Collaboration in Creative Ideation: A Study with Advertising Professionals; Journal of Advertising Research; 2026-09-01; 10.1080/00218499.2026.2702092; RCT; N=98; A1,A2
2. Tröbinger et al. (2026); How experience moderates the impact of AI suggestions on researchers' perceptions of their ideas; Research Policy; 2026-07-27; 10.1016/j.respol.2026.105575; RCT (pre-registered, online); N=310 (+28 follow-up); A1,A6 (SSRN W4406163873 "How Experience Moderates the Impact of Generative AI Ideas on the Research Process" is probably an earlier version; not verified)
3. Dell'Acqua et al. (2026); The Cybernetic Teammate: A Field Experiment on Generative AI and Teamwork; Organization Science; 2026-06-12; 10.1287/orsc.2025.20702; RCT (field); N=791; A1 (SSRN versions W4408722803, W4409251416)
4. Maier et al. (2026); Partnering with Generative AI: Experimental Evaluation of Model-Led and Human-Led Interaction in Human-AI Co-Creation; CHI 2026; 2026-04-13; 10.1145/3772318.3791185; RCT; N=486; A1,A2,A4,A5,A6,A7
5. Jin et al. (2026); Can large language models teach creativity? Cognitive gains, affective gaps, and distinct neural patterns; Computers in Human Behavior: Artificial Humans; 2026-03-18; 10.1016/j.chbah.2026.100288; RCT (AI instruction vs human instruction vs control); N=95; A2
6. Dell'Acqua et al. (2026); Navigating the Jagged Technological Frontier: Field Experimental Evidence of the Effects of Artificial Intelligence on Knowledge Worker Productivity and Quality; Organization Science; 2026-03-01; 10.1287/orsc.2025.21838; RCT (field; creative and analytical tasks); N=758; A7
7. Bian et al. (2025); Effects of AI-generated images in visual art education on students' classroom engagement, self-efficacy and cognitive load; Humanities and Social Sciences Communications; 2025-09-30; 10.1057/s41599-025-05860-2; RCT; N=78; A1
8. Baltà‐Salvador et al. (2025); Evaluating AI-assisted creative ideation: A crossover study in higher education; Thinking Skills and Creativity; 2025-08-18; 10.1016/j.tsc.2025.101958; RCT (crossover); N —; A1
9. Yu et al. (2025); Story Forge: A Card-Based Framework for AI-Assisted Interactive Storytelling; Electronics; 2025-07-24; 10.3390/electronics14152955; RCT (two AI tools compared); N —; A1

**B. RCT? (controlled, randomization not stated)**
10. Liu et al. (2026); Generative AI ‐Supported Creative Writing Among Primary School Students: A Study of Creative Writing Performance, Writing Self‐Efficacy, and Flow State; Journal of Computer Assisted Learning; 2026-10-02; 10.1002/jcal.70347; RCT?; N=78; A1
11. Xiao et al. (2026); Generative AI-assisted workflows in architectural conceptual design: Performance, creative self-efficacy, and cognitive load; Computers and Education: Artificial Intelligence; 2026-09-23; 10.1016/j.caeai.2026.100682; RCT?; N=36; A1
12. Najjar et al. (2026); Dialogue patterns in human-AI co-creation: how interaction structure shapes output and process; Human-Computer Interaction; 2026-09-21; 10.1080/07370024.2026.2717534; RCT?; N=244; A4
13. Yuan et al. (2026); The Impact of Generative AI Dependence on University Students' Creativity: The Mediating Role of Critical Thinking and the Moderating Role of Thinking Orientation; Journal of Intelligence; 2026-08-01; 10.3390/jintelligence14080168; RCT? (survey + 2 experiments); N —; A1,A8
14. Jussupow et al. (2026); The Indirect Disclosure Effect: How Disclosing Generative AI Use Impacts Human Creative Collaboration with AI; Information Systems Research; 2026-07-28; 10.1287/isre.2024.0951; RCT? (2 experiments); N —; A1
15. Wu et al. (2026); The Role of Human Agency in Human-AI Co-Creativity; Creativity & Cognition 2026; 2026-07-13; 10.1145/3803784.3816857; RCT? (3 conditions incl. human-only; homogenization outcome); N —; A1,A2,A4,A6
16. Gordetzki et al. (2026); Agency Configurations in Generative AI Ideation: How Textual and Visual Idea Concretizations Shape Idea Creativity and Ideator Effort; Information Systems Research; 2026-06-19; 10.1287/isre.2024.0952; RCT?; N=276; A7
17. Gero et al. (2026); From Planning to Revision: How AI Writing Support at Different Stages Alters Ownership; DIS 2026; 2026-06-12; 10.1145/3800645.3813003; RCT?; N=253; A1,A4
18. Guo (2026); When LLMs meet creativity: rethinking GFL writing through Human–LLM co-creation; Innovation in Language Learning and Teaching; 2026-05-30; 10.1080/17501229.2026.2678315; RCT?; N=40; A1,A4
19. Wong et al. (2026); Think First, ChatGPT Later: Guiding Human–AI Collaboration for Learning Gains in Independent Human Creativity; Educational Psychology Review; 2026-04-15; 10.1007/s10648-026-10118-7; RCT?; N=196; A2
20. Liu et al. (2026); AHAlogy: Agent-Supported In-Class Analogical Learning for Primary School Students' Divergent Thinking; ACM Extended Abstracts proceedings; 2026-04-13; 10.1145/3772363.3799384; RCT?; N=38; A5
21. Dai et al. (2026); Who performs better? Exploring the role of generative AI in creativity and brainstorming; Computers in Human Behavior: Artificial Humans; 2026-03-31; 10.1016/j.chbah.2026.100302; RCT? (lab); N=212; A1
22. Wan et al. (2026); Diverse AI personas can mitigate the homogenization effect in human-AI collaborative ideation; Computers in Human Behavior: Artificial Humans; 2026-03-24; 10.1016/j.chbah.2026.100289; RCT? (extends the Doshi-Hauser design); N —; A1,A4,A5
23. Komura et al. (2026); Deepening ideas vs. exploring new ones: AI strategy effects in human-AI creative collaboration; PLoS ONE; 2026-01-07; 10.1371/journal.pone.0340449; RCT?; N=148; A1
24. Memmert et al. (2025); Brainstorming with a Generative Language Model: Effect of Exposure to AI Ideas on Brainstorming Performance and Cognitive Load; Business & Information Systems Engineering; 2025-11-18; 10.1007/s12599-025-00974-y; RCT?; N=75; A2,A5
25. Cheng et al. (2025); Inspiration booster or creative fixation? The dual mechanisms of LLMs in shaping individual creativity in tasks of different complexity; Humanities and Social Sciences Communications; 2025-10-03; 10.1057/s41599-025-05867-9; RCT? (2 experiments); N —; A1,A2,A4,A8
26. Kreisberg-Nitzav et al. (2025); Creativeable: Leveraging AI for Personalized Creativity Enhancement; AI (MDPI); 2025-10-01; 10.3390/ai6100247; RCT? (4 conditions); N=385; A1
27. Ashkinaze et al. (2025); How AI Ideas Affect the Creativity, Diversity, and Evolution of Human Ideas: Evidence From a Large, Dynamic Experiment; ACM Collective Intelligence 2025; 2025-07-29; 10.1145/3715928.3737481; RCT?; N=800+; A1,A3
28. Qin et al. (2025); Timing Matters: How Using LLMs at Different Timings Influences Writers' Perceptions and Ideation Outcomes in AI-Assisted Ideation; CHI 2025; 2025-04-24; 10.1145/3706598.3713146; RCT?; N=60; A1,A4
29. Shin et al. (2025); No Evidence for LLMs Being Useful in Problem Reframing; CHI 2025; 2025-04-24; 10.1145/3706598.3713273; RCT? (3 LLM-use conditions); N=280; A1,A4
30. Liu et al. (2025); Empower or Disempower: The Impact of Generative Artificial Intelligence on College Students' Creativity; CSTE 2025 (IEEE); 2025-04-18; 10.1109/cste64638.2025.11091881; RCT?; N=113; A2
31. Medeiros et al. (2025); Human‐ AI Co‐Creativity: Does ChatGPT Make Us More Creative?; Journal of Creative Behavior; 2025-04-18; 10.1002/jocb.70022; RCT? (stimuli labeled as from a human or from ChatGPT); N —; A1,A2

**C. Other experiments**
32. Cuveillier et al. (2026); CreaRobot - Improving creativity using a social robot; ACM companion proceedings (28th Int. Conf.); 2026-10-02; 10.1145/3776591.3832523; Other exp.; N=49; A1
33. Berger et al. (2026); My Way or the AI Way? How Autonomy Frustration Undermines Creative Performance Through Editing AI Advice; Creativity and Innovation Management; 2026-09-29; 10.1111/caim.70090; Other exp. (qualitative + quantitative study); N —; A1,A7 (SSRN version W4410156412)
34. Purnamasari et al. (2026); Magic Easel: Environment-Grounded Visual Inspiration for Gen AI Creativity Support; NordiCHI 2026; 2026-09-28; 10.1145/3829807.3829832; Other exp. (within-subjects); N=32; A4
35. Disley et al. (2026); Designing cognitive friction with concept suppression in large language models; Human-Computer Interaction; 2026-09-21; 10.1080/07370024.2026.2708617; Other exp. (within-subject); N=37; A1,A2,A4,A5,A6
36. Estrella Maya et al. (2026); "Impacto de la Inteligencia Artificial Generativa sobre la Originalidad Creativa y el Pensamiento Proyectual en Estudiantes de Diseño Gráfico"; Visión Académica; 2026-09-10; 10.70577/0p0tya49; Other exp. (quasi); N —; A2
37. Liang et al. (2026); The Effects of Dual-Pathway AI Assistance on Divergent Thinking in Tasks of Varying Semantic Richness; Creativity Research Journal; 2026-08-25; 10.1080/10400419.2026.2721513; Other exp. (within-subjects, incl. no-AI); N=35; A1,A2
38. Sektani et al. (2026); Generative AI and the Reordering of Design Creativity in Architectural Education: Evidence from Undergraduate Students; Architecture; 2026-08-10; 10.3390/architecture6030133; Other exp. (pre-post); N=45; A1
39. Viduchinsky et al. (2026); Negotiating Creativity with AI: Effects on Self-Efficacy and Task-Performance; ACM CUI 2026; 2026-07-21; 10.1145/3816046.3816266; Other exp.; N=28; A1,A4,A5
40. Hemmatian et al. (2026); Two-Player Alternate Uses Test: A Controlled Testbed for Interactive Human-AI and Human-Human Co-Creation; Creativity & Cognition 2026; 2026-07-13; 10.1145/3803784.3816851; Other exp.; N=62; A1
41. Čok et al. (2026); Evaluating TRIZ with and without LLM support: an experimental study on engineering problem-solving; Proceedings of the Design Society; 2026-07-02; 10.1017/pds.2026.10409; Other exp.; N —; A7
42. Lin et al. (2026); Stimulating or constraining creativity? Traditional vs. generative AI on divergent thinking in product design; Frontiers in Psychology; 2026-06-30; 10.3389/fpsyg.2026.1839565; Other exp.; N=41; A1
43. Koolman et al. (2026); Influence of Artificial Intelligence Use on Creativity-Related Perceptions and Outcomes in an Idea Generation Task; Journal of Computing and Information Science in Engineering; 2026-06-15; 10.1115/1.4072161; Other exp.; N —; A1
44. Chen et al. (2026); Impact of metacognitive scaffolding on high-school students' creativity within a GenAI learning environment; Interactive Learning Environments; 2026-06-02; 10.1080/10494820.2026.2677726; Other exp. (quasi); N=70; A8
45. Radensky et al. (2026); Scideator: Human-LLM Compound System for Scientific Ideation through Facet Recombination and Novelty Evaluation; Proc. ACM Conference on AI and A… (name truncated in output); 2026-05-22; 10.1145/3786335.3813161; Other exp. (system vs baseline LLM); N —; A1,A4,A6
46. Sattele et al. (2026); Sketching vs. AI Prompt Based Design Intent Evolution in Undergraduate Students: an Exploratory Study; CHI 2026; 2026-04-13; 10.1145/3772318.3791350; Other exp.; N=61; A4
47. Candi et al. (2026); How the integration of generative AI in design thinking-based collaborative learning impacts student creativity; The Design Journal; 2026-04-09; 10.1080/14606925.2026.2652387; Other exp. (5 classroom experiments); N —; A1
48. Cui et al. (2026); Can Gen AI Improve Creativity in Students with Low Academic Performance? A Quasi-Experimental Study Based on Chinese Samples; SAGE Open; 2026-04-01; 10.1177/21582440261449529; Other exp. (quasi); N=75; A1,A2
49. Zhou et al. (2026); Group‐ AI Collaboration Enhances Creativity Performance: The Roles of Perspective‐Taking and AI Utilisation Strategies; Journal of Computer Assisted Learning; 2026-03-09; 10.1002/jcal.70223; Other exp.; N=96; A1 (preprint W4412882002)
50. Tsakalerou et al. (2026); AI-assisted design synthesis and human creativity in engineering education; Frontiers in Artificial Intelligence; 2026-01-20; 10.3389/frai.2026.1714523; Other exp.; N —; A1,A2
51. Krajcer et al. (2026); The hidden costs of AI-assisted ideation: empirical findings on ChatGPT's impact on novice designers' creative confidence and design process; Design Science; 2026-01-01; 10.1017/dsj.2026.10060; Other exp. (within-group); N=35; A2
52. Wang et al. (2025); A large-scale comparison of divergent creativity in humans and large language models; Nature Human Behaviour; 2025-12-23; 10.1038/s41562-025-02331-1; Other exp. (human vs LLM) [abstract unclear]; N —; A1,A4
53. Roméro (2025); Delayed Ai Access: Mitigating the Homogenising Effects of Generative Ai in Collaborative Problemsolving; ICAITE 2025 (IEEE); 2025-12-07; 10.1109/icaite68636.2025.11442590; Other exp. (quasi); N=36; A5
54. Kamada et al. (2025); Simply Incorporating Generative AI into Groups Is Not Enough: Exploring the Effects of Human-AI Collaboration in Groups on Brainstorming; IEICE Transactions on Information and Systems; 2025-11-27; 10.1587/transinf.2025dkp0002; Other exp. (within-subjects); N=24; A1
55. Liu et al. (2025); Who Is the Best Helper for University Students' Mathematical Creativity? A Quasi‐Experimental Study of Human–ChatGPT, Human–Google, and Human–Human Co‐Creation; Computer Applications in Engineering Education; 2025-10-23; 10.1002/cae.70100; Other exp. (quasi); N=230; A1,A2,A7
56. Arora et al. (2025); Generative artificial intelligence models outperform students on divergent and convergent thinking assessments; Scientific Reports; 2025-10-22; 10.1038/s41598-025-21398-4; Other exp. (human vs GenAI); N=46; A1,A6,A7 (preprint W4412158470)

**D. Observational corpus**
57. Shen et al. (2026); Generative AI in creative education: baseline-linked evidence on learning processes, artistic performance, and authorship; Frontiers in Psychology; 2026-10-02; 10.3389/fpsyg.2026.1956939; Obs. (course data); N=133; A2
58. Yilmaz et al. (2026); The impact of generative artificial intelligence on innovation: Evidence from software products; Strategic Management Journal; 2026-08-25; 10.1002/smj.70118; Obs. corpus (Firefox add-ons); A1
59. Cui et al. (2026); When platforms integrate generative AI: the dynamics of professional contribution in artist communities; Internet Research; 2026-08-21; 10.1108/intr-10-2025-1753; Obs. corpus (difference-in-differences); N=43,587 designers; A1
60. Qian et al. (2026); The rise of large language models and the direction and impact of US federal research funding; PNAS; 2026-08-11; 10.1073/pnas.2601439123; Obs. corpus (NSF/NIH proposals); A1
61. Luo et al. (2026); Generative artificial intelligence and corporate innovation: Quantity boon or quality bane; Technology in Society; 2026-07-28; 10.1016/j.techsoc.2026.103488; Obs.? [abstract unclear]; A1,A8
62. Lee et al. (2026); The Digital Divide in Generative AI: Evidence from Large Language Model Use in College Admissions Essays; Proc. 13th ACM Conference (name truncated in output); 2026-06-22; 10.1145/3774398.3811620; Obs. corpus; N=81,663 applications; A4
63. Mak et al. (2025); Style, sentiment, and quality of undergraduate writing in the AI era: A cross-sectional and longitudinal analysis of 4,820 authentic empirical reports; Computers and Education: Artificial Intelligence; 2025-11-26; 10.1016/j.caeai.2025.100507; Obs. corpus (pre-registered); N=2,000 students; A1,A2
64. Moon et al. (2025); Homogenizing effect of large language models (LLMs) on creative diversity: An empirical comparison of human and ChatGPT writing; Computers in Human Behavior: Artificial Humans; 2025-09-17; 10.1016/j.chbah.2025.100207; Obs. corpus (human vs ChatGPT); N=2,200 essays; A1,A7
65. Zhou et al. (2025); Who expands the human creative frontier with generative AI: Hive minds or masterminds?; Science Advances; 2025-09-03; 10.1126/sciadv.adu5800; Obs. corpus (art platform, matched non-adopters); A1,A7 (SSRN W4410233406)
66. De Rosa Palmini et al. (2025); Exploring Language Patterns of Prompts in Text-to-Image Generation and Their Impact on Visual Diversity; FAccT 2025; 2025-06-23; 10.1145/3715275.3732158; Obs. corpus (6M+ prompts); A4
67. Zhang et al. (2025); Generative AI Meets Open-Ended Survey Responses: Research Participant Use of AI and Homogenization; Sociological Methods & Research; 2025-05-07; 10.1177/00491241251327130; Obs. (survey responses); A1,A3,A4
68. Li et al. (2025); Generating creativity through ChatGPT: an empirical investigation in open innovation platforms; Information Technology and Management; 2025-04-17; 10.1007/s10799-025-00454-5; Obs.? [abstract unclear]; A2,A7
69. Liu et al. (2025); Generative AI and Content Homogenization: The Case of Digital Marketing; SSRN; 2025-01-01; 10.2139/ssrn.5367123; Obs.? [abstract unclear]; A4,A6

**E. Unclear [abstract unclear]**
70. Tan et al. (2026); The effects of generative AI usage on employee innovation: Collaboration modes, idea journey, and decline in creative psychological ownership; Technovation; 2026-09-01; 10.1016/j.technovation.2026.103700; A1,A2
71. Xu et al. (2026); Human or model? A four-factor experimental study of design experience and image-generation alignment strategies in industrial product ideation; Research in Engineering Design; 2026-08-31; 10.1007/s00163-026-00497-x; experiment (title); A1
72. Zhou et al. (2026); Long-term impact of ChatGPT-4 on music students' creative and analytical skills: A follow-up study; Thinking Skills and Creativity; 2026-08-23; 10.1016/j.tsc.2026.102344; A2
73. Hassan et al. (2026); Searching together: Human–AI complementarities in innovation search; Research Policy; 2026-08-14; 10.1016/j.respol.2026.105597; A1
74. Hukerikar et al. (2026); Generative Al as a Collaborative Screenwriting Tool Measuring Creative Output Quality VS. Human-Authored Scripts; ICICIT 2026 (IEEE); 2026-07-01; 10.1109/icicit69063.2026.11634223; A1
75. Kang et al. (2026); The Effects of Generative AI Use on University Students' Creative Idea Generation: Switching Effects in Repeated Task Performance; Journal of Korean Association of Computer Education; 2026-06-30; 10.32431/kace.2026.29.6.004; A1
76. Villarreal et al. (2026); LLM Randomness and Creativity: An Experiment on Human-AI Collaboration; MIPRO 2026; 2026-05-25; 10.1109/mipro70003.2026.11592010; experiment (title); A5
77. Fu et al. (2026); Decoupling of Usefulness and Novelty: Evaluating the Impact of Generative AI on Design Outputs and Novice Designers' Creative Thinking; CHI 2026; 2026-04-13; 10.1145/3772318.3791329; A1,A4,A5
78. Sorin et al. (2026); The role of task breadth and cognitive flexibility in generative AI-supported creative idea generation; Technovation; 2026-03-19; 10.1016/j.technovation.2026.103540; A1
79. Zhu et al. (2026); Generative AI adoption in human creative tasks: Experimental evidence; Journal of Economic Behavior & Organization; 2026-01-15; 10.1016/j.jebo.2026.107414; experiment (title); A1,A2
80. Zhao et al. (2025); Experimental study on improving the quality of interdisciplinary design: Collaborate with AI psychology experts for design develop process; Design Studies; 2025-12-26; 10.1016/j.destud.2025.101371; experiment (title); A1
81. Chen et al. (2025); Effects of Personalized Generative AI on Student Creativity: Evidence from Creative Performance, Self-efficacy, and Attention Allocation; CCIS (Springer); 2025-11-25; 10.1007/978-981-95-4499-8_31; A2
82. Zastudil et al. (2025); Helping or Homogenizing? GenAI as a Design Partner to Pre-Service SLPs for Just-in-Time Programming of AAC; ASSETS 2025; 2025-10-22; 10.1145/3663547.3746384; OpenAlex abstract is figure-caption text; A4
83. Huang et al. (2025); Human–GenAI collaboration across creative phases: Cognitive mechanisms shaping novelty and usefulness; International Journal of Information Management; 2025-10-03; 10.1016/j.ijinfomgt.2025.102986; A1,A7
84. Preuschoff et al. (2025); Groups and AI: How Access to Generative AI Influences Creative Teamwork; Mensch und Computer 2025; 2025-08-28; 10.1145/3743049.3743073; A5
85. Rayan et al. (2025); Cueing the Crowd: LLM-Driven Conversational Cues Across Different Meeting Modalities Increase Topical Diversity of Generated Ideas; ACM Collective Intelligence 2025; 2025-07-29; 10.1145/3715928.3737486; A4
86. Xu et al. (2025); Productive vs. Reflective: How Different Ways of Integrating AI into Design Workflows Affect Cognition and Motivation; CHI 2025; 2025-04-24; 10.1145/3706598.3713649; A4
87. Bangerl et al. (2025); CreAItive Collaboration? Users' Misjudgment of AI-Creativity Affects Their Collaborative Performance; CHI 2025; 2025-04-23; 10.1145/3706598.3713886; A5
88. Wu et al. (2025); Guided Creativity: AI Intermediation for Enhancing Originality and Quality in Visual Design; SSRN; 2025-01-01; 10.2139/ssrn.5371575; A1
89. Yang et al. (2025); Large Language Models Improve Hypothesis Generation by Reducing Effort; SSRN; 2025-01-01; 10.2139/ssrn.5339141; A1
90. Ueda et al. (2025); Neural Mechanisms of Collaborative Creative Thinking in Engineering Design: Human-Human Versus Human-AI Interaction; LNCS; 2025-01-01; 10.1007/978-3-031-93718-7_21; A8

## 4. Reviews and meta-analyses
1. de Rooij et al. (2026); Does generative AI make us think alike? A systematic review and meta-analysis of homogenisation effects in human–AI co-creation; Behaviour and Information Technology; 10.1080/0144929x.2026.2726451; A1,A4,A5,A6
2. de Rooij et al. (2025); Has AI Surpassed Humans in Creative Idea Generation? A Meta-Analysis; ACM proceedings (36th Annual Conference); 10.1145/3746175.3746189; A1,A2,A4
3. Ahsan et al. (2026); How do we measure creativity? A systematic review and taxonomy of evaluative methods in human-AI co-creativity; Human-Computer Interaction; 10.1080/07370024.2026.2720237; A1,A4,A5
4. Sourati et al. (2026); The homogenizing effect of large language models on human expression and thought; Trends in Cognitive Sciences; 10.1016/j.tics.2026.01.003; A1
5. Huang et al. (2026); Evaluation of Large Language Models as Tools, Models, and Partners in Creative Thinking Research: A Selective Narrative Review with the GCA Framework; Journal of Intelligence; 10.3390/jintelligence14090218; A1,A2
6. Caprioli (2026); Collaborating with GenAI: A blessing or a curse for creativity?; Current Opinion in Psychology; 10.1016/j.copsyc.2026.102425; A1,A2,A7
7. Ramakrishnan (2026); AI-augmented design creativity: A review of human-AI collaboration and the conditions for creative enhancement; Design and Artificial Intelligence; 10.1016/j.daai.2026.100104; A1
8. Peng et al. (2025); The impact of AI-supported instructional interventions on students' creative thinking: a meta-analysis of 56 experimental studies; Journal of Research on Technology in Education; 10.1080/15391523.2025.2557392; A4
9. Shi et al. (2026); Enhancing students' Creativity with Generative Artificial Intelligence: A Systematic Review and Meta-Analysis; Creativity Research Journal; 10.1080/10400419.2026.2726242; A8
10. Yao et al. (2025); Uneven Gains of Generative Artificial Intelligence on Creativity Enhancement: A Systematic Review and Meta-Analysis; PsyArXiv; 10.31234/osf.io/jy3ba_v1; not linked as citing any anchor (found by title search)
11. Lo Presti et al. (2026); The Role of Generative Artificial Intelligence in Nurturing Creativity: A Systematic Review of the Early Adoption Phase; Education Sciences; 10.3390/educsci16091486; A1
12. Guo (2026); How generative artificial intelligence influences the creative thinking of STEAM learners in higher education: A systematic literature review; Thinking Skills and Creativity; 10.1016/j.tsc.2026.102336; A1
13. Al-Sharafi et al. (2026); A topic modelling-driven systematic mapping of generative AI and creativity research: toward a conceptual framework; International Journal of Innovation Management; 10.1142/s1363919626500210; A1
14. Ren Xiaotian et al. (2026); Effects of AI Interventions Across Cognitive, Social-emotional, and Academic Outcomes: a Meta-analysis of Randomized Controlled Trials with Nonlinear Dose–response Evidence; Educational Psychology Review; 10.1007/s10648-026-10217-5; A2
15. Im et al. (2025); Human–AI Co-creativity in Storytelling: A Scoping Review of Literature, Education, Media, and Interactive Systems; LNCS; 10.1007/978-3-032-12405-0_24; A1

## 5. Coverage limits
- **Missing abstracts:** 328 of the first 1,092 works (about 30%) had no abstract or fewer than 30 words in OpenAlex. I screened those by title only, and 25 of the 90 rows depend on titles.
- **Incomplete citation links:** title searches returned several records not linked as citing any anchor. These include a comment on Lee & Chung (W7115971788, EconStor) and a replication report on Lee & Chung (W7111471034, OSF). Others are the Brodeur OSF record (W7116130859) and the meta-analysis in item 10 of section 4. Preprints with unparsed reference lists will be missed the same way.
- **Anchor records:** three anchor versions had no separate OpenAlex record (the ICLR version of Padmakumar & He and the arXiv versions of Kumar et al. and Anderson et al.). Anchor 7 is attached to a mis-titled record, as noted under the table.
- **Worth a manual check:** I dropped Lee & Chung's NHB reply to Meincke et al. (W4410375713, no abstract) as commentary, but it may contain a reanalysis.
- **Dates:** many SSRN and book records carry placeholder dates such as 2025-01-01 or 2026-01-01.
- **Rate limits:** anonymous access allowed 1,000 credits; filter queries cost 1 credit and searches cost 10. The pool appeared to be shared, since it dropped faster than my own use. 489 credits remained at the end and no requests were refused.
- **Requests and files:** no email or identifier was sent (User-Agent "atlas-screening/0.1"). I created no files. Claude Code automatically saved one oversized command output to its own session folder.
