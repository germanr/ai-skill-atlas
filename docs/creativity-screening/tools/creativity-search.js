export const meta = {
  name: 'creativity-search',
  description: 'Literature search for the AI Skill Atlas creativity section: structure three saved search reports, then run 18 independent search lanes that each write a candidate file',
  phases: [
    { title: 'Structure seeds', detail: 'three saved search reports become candidate files' },
    { title: 'Search', detail: 'one agent per source, blind to the others' },
  ],
}

const DIR = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening/search'
const LIB = 'C:/Dropbox/Research/ai-lab/literature/creativity'

const PROJECT = [
  'Project: The AI and Human Skill Atlas (aiskillatlas.org) is a living meta-analysis of experiments on generative AI and learning. It is adding a section on generative AI and creativity, ideation, and homogenization of ideas. This task is the literature search for that section. Today is 2026-10-04.',
  '',
  'The section is organized around three questions:',
  '1. with_ai: does generative-AI assistance change the rated creativity (overall creativity, novelty, originality, usefulness, fluency, flexibility) of what a person produces?',
  '2. across_people: does generative-AI assistance make different people\'s outputs more alike (idea or content diversity, similarity, homogenization)?',
  '3. after_ai: what happens to people\'s unassisted creative work, or to the diversity of their output, after a period of AI use (AI removed at measurement)?',
  '',
  'What we collect:',
  'A. CORE. Experiments in which human participants are randomly assigned to generative-AI assistance (LLM chatbots, AI writing suggestions, AI-generated ideas or examples, text-to-image tools) versus no AI or versus a different AI configuration, on a creative or ideation task (story, essay or ad writing, brainstorming, product or business ideas, divergent-thinking tests, design, research ideas, humor), where creativity or diversity is scored on the output by raters or by computed measures. Any sample size; record N.',
  'B. CONTEXT. (i) Comparisons of AI-generated output with human-generated output in which no person receives AI help. (ii) Observational or quasi-experimental studies of real human output (papers, grant proposals, art, marketing, news, essays, online posts) with a diversity, similarity, novelty, or originality outcome linked to generative AI. (iii) Systematic reviews and meta-analyses on these questions.',
  'Not wanted: opinion or theory pieces with no data; model-only benchmarks with no human data; surveys of attitudes or of self-reported creativity only; studies of learning or productivity with no creativity or diversity outcome; studies of how people perceive or value AI-made work; tools that are not generative AI.',
  '',
  'Time: all years since 2022, with special attention to work first posted or published from 2026-05-01 through 2026-10-04, because the existing collection was assembled in late May 2026.',
].join('\n')

const RECORD_SPEC = [
  'Each candidate is one JSON object with exactly these fields:',
  '- "title": the exact title of the paper (string).',
  '- "authors": family names in the order the source lists them, e.g. "Doshi, Hauser"; when there are more than six, give the first three followed by "et al." (string).',
  '- "year": publication or posting year of the version you cite (integer).',
  '- "venue": journal, proceedings, or preprint server, with volume or working-paper number when known (string).',
  '- "status": one of "journal", "proceedings", "working_paper", "preprint", "thesis", "other".',
  '- "doi": the DOI without the https://doi.org/ prefix, or null.',
  '- "arxiv_id": the arXiv identifier without version suffix, e.g. "2410.03703", or null.',
  '- "url": a link that opens the paper\'s own page (string).',
  '- "first_posted": the date the work first became public, as "YYYY-MM-DD", "YYYY-MM" or "YYYY", or null.',
  '- "other_versions": other versions of the same work (earlier preprint or working paper, later journal article) as a list of strings such as "arXiv 2401.13481" or "doi 10.2139/ssrn.4686415"; an empty list if none is known.',
  '- "design_guess": one of "randomized_experiment_people" (people randomly assigned to generative-AI assistance), "experiment_assignment_unclear" (an experiment with AI and no-AI or AI-variant conditions for people, random assignment not stated), "quasi_experiment_people", "ai_vs_human_output" (AI-generated output compared with human output; no person receives AI help), "observational" (corpus or platform data on real human output), "synthesis" (review or meta-analysis), "model_only", "other".',
  '- "question_guess": a list with any of "with_ai", "across_people", "after_ai"; may be empty.',
  '- "n_participants": the number of human participants if the abstract or paper states it, else null. Count people, never ideas, essays, or ratings.',
  '- "task": a few words on the task or setting, e.g. "short story writing", "alternate uses task", "product ideas at a consumer-goods firm" (string, may be empty).',
  '- "evidence": one or two sentences in your own words on what was assigned or compared and which creativity or diversity outcome was measured, based on the abstract or paper (string).',
  '- "confirmed_from": where you confirmed the record: "publisher_page", "arxiv", "ssrn", "osf", "nber", "crossref_api", "openalex_api", "pdf", "prior_report" or "search_snippet_only".',
  '- "lane": your lane id (string).',
  '',
  'Rules for every record:',
  '- Never write a title, author, year, venue, DOI, or sample size from memory. If a field cannot be confirmed, use null (or an empty string for "task") and say so in "evidence".',
  '- Copy DOIs and arXiv ids character by character.',
  '- One record per work. If a work has a preprint and a journal version, cite the latest version and list the others in "other_versions".',
].join('\n')

const KNOWN_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    n_records: { type: 'integer' },
    known: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          first_author: { type: 'string' },
          year: { type: ['integer', 'null'] },
          title: { type: 'string' },
        },
        required: ['first_author', 'title'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['file', 'n_records', 'known'],
}

const LANE_SCHEMA = {
  type: 'object',
  properties: {
    lane: { type: 'string' },
    file: { type: 'string' },
    n_candidates: { type: 'integer' },
    n_randomized_guess: { type: 'integer' },
    n_queries: { type: 'integer' },
    coverage_limits: { type: 'string' },
  },
  required: ['lane', 'file', 'n_candidates'],
}

const SEEDS = [
  {
    id: 'seed-verified-leads',
    how: 'The report lists 33 numbered entries with a verdict and a corrected citation each. Make one record per entry, using the corrected citation. Entry 26 describes two publications of one meta-analysis: cite the journal article (Behaviour & Information Technology) and list the others in "other_versions". Entry 25: cite the full paper (de Rooij and Biskjaer, ECCE 2025) and mention the one-page abstract in "evidence".',
  },
  {
    id: 'seed-meta-analysis-lists',
    how: 'The report covers three meta-analyses and ends with a merged list of 48 articles on 47 lines. Make one record per primary study in the merged list, taking its details from the three per-meta-analysis tables (title, venue, link). Map the "Rand." column: Y -> "randomized_experiment_people"; ? -> "experiment_assignment_unclear"; N with an AI-versus-human comparison -> "ai_vs_human_output"; N marked quasi or before-versus-after -> "observational" or "quasi_experiment_people" as the description indicates. Put in "evidence" which meta-analyses include the study and under which comparison code. Also make one record for each of the three meta-analyses themselves (design_guess "synthesis"), using the bibliographic records in the report, with their other outputs in "other_versions". Where the report gives a newer published version of a study (for example Research Policy 2026 for Doshi, Chai and Troebinger; Journal of Economic Behavior & Organization 2026 for Zhu and Zou), cite the published version and list the earlier one in "other_versions".',
  },
  {
    id: 'seed-openalex-citing',
    how: 'The report has a shortlist of 90 numbered works in five groups (A to E) and a list of 15 reviews and meta-analyses. Make one record per work in both lists (105 records). Map the labels: "RCT" -> "randomized_experiment_people"; "RCT?" -> "experiment_assignment_unclear"; "Other exp." -> "quasi_experiment_people" when the note says quasi or pre-post, "ai_vs_human_output" when the note says human versus AI or LLM, otherwise "other"; "Obs." -> "observational"; "Unclear" -> "other" with the words "abstract unclear" in "evidence"; reviews and meta-analyses -> "synthesis". The report gives first author "et al." only: put exactly what it gives in "authors". Put the stated N in "n_participants" only when the report says it counts people (students, participants, designers); otherwise null. Put the anchors cited and any note in "evidence".',
  },
]

phase('Structure seeds')
const seeds = (await parallel(SEEDS.map(s => () => agent(
  [
    'Task: convert a saved search report into a JSON candidate file. Do not look anything up and do not add or drop works: convert only what the report states.',
    '',
    PROJECT,
    '',
    'Input file (read all of it): ' + DIR + '/' + s.id + '.md',
    '',
    'How to convert this report: ' + s.how,
    '',
    RECORD_SPEC,
    '',
    'For this task, set "lane" to "' + s.id + '" and "confirmed_from" to "prior_report". Leave any field the report does not state as null (empty string for "task", empty list for the two list fields).',
    '',
    'Output: write a JSON object to ' + DIR + '/' + s.id + '.json with the Write tool (UTF-8), with these keys: "lane" ("' + s.id + '"), "queries" (empty list), "sources_checked" (a one-item list naming the report), "coverage_limits" (the limits the report itself states, in a sentence or two), and "candidates" (the list of records). Then run python to confirm the file parses and to print the number of candidates, and check that every DOI and arXiv id in your file appears character for character in the report; fix any that do not. Create no other files.',
    '',
    'Your structured reply: "file" (the path), "n_records", "known" (one item per record with "first_author" (family name), "year", and "title"), and "notes" (anything in the report that you could not convert cleanly).',
  ].join('\n'),
  { label: 'structure:' + s.id, phase: 'Structure seeds', schema: KNOWN_SCHEMA }
)))).filter(Boolean)

const knownItems = seeds.flatMap(s => s.known || [])
const seenKnown = new Set()
const knownLines = []
for (const k of knownItems) {
  const key = (k.title || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
  if (!key || seenKnown.has(key)) continue
  seenKnown.add(key)
  knownLines.push('- ' + k.first_author + (k.year ? ' (' + k.year + ')' : '') + ': ' + k.title)
}
log('Seeds structured: ' + seeds.map(s => s.n_records).join(' + ') + ' records, ' + knownLines.length + ' distinct known titles')

const LIBRARY_TITLES = [
  '- Padmakumar & He (2024): Does Writing With Language Models Reduce Content Diversity?',
  '- Doshi & Hauser (2024): Generative AI Enhances Individual Creativity but Reduces the Collective Diversity of Novel Content',
  '- Anderson, Shah & Kreminski (2024): Homogenization Effects of LLMs on Human Creative Ideation',
  '- Moon, Green & Kushlev (2025): The Homogenizing Effect of LLMs on Creative Diversity',
  '- Meincke, Nave & Terwiesch (2025): ChatGPT Decreases Idea Diversity in Brainstorming',
  '- Moon et al. (2026): The Creative Link Between Words and Ideas is Weakening in the AI Era',
  '- Lee & Chung (2024): An Empirical Investigation of the Impact of ChatGPT on Creativity',
  '- Boussioux et al. (2024): The Crowdless Future? Generative AI and Creative Problem-Solving',
  '- Ashkinaze et al. (2025): How AI Ideas Affect the Creativity, Diversity, and Evolution of Human Ideas',
  '- Girotra et al. (2023): Ideas Are Dimes a Dozen: Large Language Models for Idea Generation in Innovation',
  '- Meincke, Mollick & Terwiesch (2024): Prompting Diverse Ideas: Increasing AI Idea Variance',
  '- Liu et al. (2024): When ChatGPT is Gone: Creativity Reverts and Homogeneity Persists',
  '- Wenger & Kenett (2025): We\'re Different, We\'re the Same: Creative Homogeneity Across LLMs',
  '- Hintze, Proschinger Astrom & Schossau (2026): Autonomous Language-Image Generation Loops Converge to Generic Visual Motifs',
  '- Liang et al. (2024): Monitoring AI-Modified Content at Scale: A Case Study on Peer Reviews',
  '- Kobak et al. (2024): Delving into ChatGPT Usage in Academic Writing through Excess Vocabulary',
  '- Si, Yang & Hashimoto (2025): Can LLMs Generate Novel Research Ideas?',
  '- Russell et al. (2025): AI Use in American Newspapers is Widespread, Uneven, and Rarely Disclosed',
  '- Liu, Wang & Yang (2025): Generative AI and Content Homogenization: The Case of Digital Marketing',
  '- Sourati, Ziabari & Dehghani (2026): The Homogenizing Effect of LLMs on Human Expression and Thought',
  '- Castro, Gao & Martin (2024): Human-AI Interactions and Societal Pitfalls',
  '- Raghavan (2024): Competition and Diversity in Generative AI',
  '- Wu, Black & Chandrasekaran (2024): Generative Monoculture in Large Language Models',
  '- Dolezal, Alam, Graham & Bohacek (2026): The Impact of AI-Generated Text on the Internet',
  '- Russell et al. (2026): StoryScope: Investigating Idiosyncrasies in AI Fiction',
]

const KNOWN_BLOCK = [
  'Already collected (' + (knownLines.length + LIBRARY_TITLES.length) + ' items). Do not spend effort on these. Do report a newer or published version of any of them if you come across one, and report everything else you find:',
  LIBRARY_TITLES.join('\n'),
  knownLines.join('\n'),
].join('\n')

const TOOLS = [
  'Tools: WebSearch and WebFetch may need to be loaded first with ToolSearch (query "select:WebSearch,WebFetch"). WebFetch summarizes pages with a small model, so confirm bibliographic facts from page metadata or an API record. Useful APIs through Python urllib (run python through PowerShell; send no email address or personal identifier in headers; a plain User-Agent such as "atlas-screening/0.1" is fine):',
  '- OpenAlex: https://api.openalex.org/works?search=...&filter=from_publication_date:2022-01-01&per-page=50 ; citing works with filter=cites:<openalex id> ; a work\'s references in its "referenced_works" field; abstracts come as "abstract_inverted_index". Anonymous use has a daily credit limit, so prefer filters over free-text search and keep requests purposeful.',
  '- Crossref: https://api.crossref.org/works?query.bibliographic=...&rows=5 and https://api.crossref.org/works/<doi> (the "reference" field lists references).',
  '- arXiv: http://export.arxiv.org/api/query?search_query=...&start=0&max_results=100&sortBy=submittedDate&sortOrder=descending',
  'Many publisher sites return HTTP 403 to scripts. Use the APIs or search snippets for those and set "confirmed_from" accordingly.',
].join('\n')

const EFFORT = 'Effort: be exhaustive within your lane. Run at least 25 distinct queries or listing passes and vary the vocabulary: creativity, creative, ideation, idea generation, brainstorming, divergent thinking, originality, novelty, innovation, creative writing, storytelling, design fixation, homogenization, homogeneity, idea diversity, content diversity, similarity, convergence, monoculture; generative AI, large language model, LLM, ChatGPT, GPT-4, Claude, Gemini, Copilot, text-to-image, Midjourney, Stable Diffusion, DALL-E. Keep going until eight consecutive queries add no new relevant work. Favor recall: when unsure whether a work belongs, include it and say why in "evidence".'

const LANES = [
  { id: 'econ-wp', title: 'Economics working papers', body: 'Sources: NBER working papers, SSRN (economics and management networks), IZA discussion papers, CESifo working papers, CEPR discussion papers, arXiv econ.GN, RePEc/IDEAS search, and the AEA RCT Registry (trials on generative AI with creativity, ideation, or innovation outcomes, and any papers they produced). Look for lab, online, and field experiments by economists on generative AI and idea generation, innovation, creative work, entrepreneurship ideas, writing originality, or homogenization.' },
  { id: 'management', title: 'Management, marketing, and innovation journals', body: 'Sources: Management Science, Organization Science, Strategic Management Journal, Academy of Management Journal, Administrative Science Quarterly, Strategy Science, Information Systems Research, MIS Quarterly, Journal of Management Information Systems, Marketing Science, Journal of Marketing Research, Journal of Marketing, Journal of Consumer Research, Research Policy, Journal of Product Innovation Management, Technovation, Production and Operations Management, Journal of Business Research, and the Academy of Management and ICIS/ECIS proceedings. Include articles in press and online-first.' },
  { id: 'psych-creativity', title: 'Psychology and creativity research', body: 'Sources: Journal of Creative Behavior; Creativity Research Journal; Thinking Skills and Creativity; Psychology of Aesthetics, Creativity, and the Arts; Journal of Intelligence; Journal of Creativity; Psychological Science; Journal of Experimental Psychology (General, Applied); Cognition; Computers in Human Behavior (including Artificial Humans and Reports); Frontiers in Psychology; Acta Psychologica; Behavior Research Methods; and PsyArXiv/OSF preprints. Look for experiments on divergent thinking, creative writing, idea generation, and co-creation with generative AI.' },
  { id: 'education', title: 'Education research', body: 'Sources: Computers & Education (including Artificial Intelligence and Open); British Journal of Educational Technology; Journal of Computer Assisted Learning; Studies in Higher Education; International Journal of Educational Technology in Higher Education; Educational Psychology Review; Learning and Instruction; Education and Information Technologies; Interactive Learning Environments; Educational Technology Research and Development; Journal of Research on Technology in Education; EdWorkingPapers. Only studies with a creativity, divergent-thinking, creative-writing, or design-creativity outcome scored on student output, with random or quasi-random assignment to generative-AI use. Skip studies whose outcome is learning, exam performance, or self-reported creativity only.' },
  { id: 'hci', title: 'Human-computer interaction venues', body: 'Sources: CHI 2024 to 2026 (papers and extended abstracts), CSCW, UIST, DIS, IUI, Creativity & Cognition, Collective Intelligence, CUI, NordiCHI, TOCHI, International Journal of Human-Computer Studies, International Journal of Human-Computer Interaction, Human-Computer Interaction, Behaviour & Information Technology, FAccT, and arXiv cs.HC. Look for controlled experiments on writing, ideation, and design with generative AI that score creativity or diversity of the output. Record N for every study; many are small.' },
  { id: 'general-science', title: 'General science journals', body: 'Sources: Nature, Science, PNAS, Nature Human Behaviour, Nature Communications, Nature Machine Intelligence, Science Advances, Scientific Reports, PNAS Nexus, Communications Psychology, Humanities and Social Sciences Communications, PLoS ONE, Royal Society Open Science, iScience, Patterns, Heliyon, and Trends in Cognitive Sciences. Include experiments, observational studies of real output, and syntheses.' },
  { id: 'arxiv-recent', title: 'arXiv from May through October 2026', body: 'Source: the arXiv API. Go systematically through submissions dated 2026-05-01 to 2026-10-04 in cs.HC, cs.CL, cs.CY, cs.AI, cs.SI, cs.DL, econ.GN, and stat.AP that match the vocabulary below, paging through the results of each query (not only the first page). Also check arXiv listings for 2026-01 to 2026-04 with the same queries, more briefly. For each relevant submission read the abstract from the API record.' },
  { id: 'obs-science', title: 'Observational: science and scholarship', body: 'Sources: Nature, Science, PNAS, Research Policy, Quantitative Science Studies, Scientometrics, Journal of Informetrics, arXiv cs.DL and cs.CY, SSRN, and NBER. Look for studies that link LLM adoption to the diversity, novelty, originality, or similarity of scientific papers, research ideas, hypotheses, grant proposals, peer reviews, or citations, using real corpora. Studies that only measure how much AI text exists, with no diversity or novelty outcome, are not wanted, but list the few most prominent ones with "design_guess": "other" and say so.' },
  { id: 'obs-art-design-music', title: 'Observational: art, design, music, fiction', body: 'Sources: any outlet. Look for studies of real creative platforms and markets after generative AI: text-to-image and art communities (DeviantArt, ArtStation, Pixiv, Midjourney or Stable Diffusion prompt logs), illustration and stock-image markets, design and logo marketplaces, music, fiction and fan-fiction platforms, games, and video. Outcomes of interest: novelty, originality, content or style diversity, similarity, variety of the human or human-with-AI output.' },
  { id: 'obs-marketing-news-online', title: 'Observational: marketing, news, online content, applications', body: 'Sources: any outlet. Look for studies of real text after generative AI with a diversity, similarity, novelty, or originality outcome: marketing and advertising content, product descriptions, online reviews, news articles, social media posts, crowdsourcing and innovation-contest platforms, crowdfunding or product-launch platforms, job applications and cover letters, resumes, college admission essays, student writing corpora, open-ended survey responses, and question-and-answer communities.' },
  { id: 'reference-lists', title: 'Reference lists of the library and of recent reviews', body: 'Method: backward citation tracking. (1) The library folder ' + LIB + ' holds markdown conversions of 25 papers; read the reference sections of the experiments and of the review by Sourati, Ziabari and Dehghani (2026) and pull every cited empirical study on generative AI and creativity, ideation, or diversity that is not in the known list. (2) Do the same for these reviews, taking their reference lists from the Crossref API ("reference" field of https://api.crossref.org/works/<doi>) or OpenAlex ("referenced_works"): 10.1080/07370024.2026.2720237 (Ahsan et al. 2026), 10.1016/j.copsyc.2026.102425 (Caprioli 2026), 10.3390/jintelligence14090218 (Huang et al. 2026), 10.1016/j.daai.2026.100104 (Ramakrishnan 2026), 10.1007/978-3-032-12405-0_24 (Im et al. 2025), 10.1016/j.tics.2026.01.003 (Sourati et al. 2026), and 10.1080/0144929X.2026.2726451 (de Rooij and Biskjaer 2026). Confirm each new candidate in a primary record before listing it.' },
  { id: 'meta-analyses-2', title: 'Included-study lists of further meta-analyses', body: 'Method: find the full text or the reference list of each of these syntheses and extract the primary studies that involve generative AI and a creativity or diversity outcome: Yao et al. (2025), "Uneven Gains of Generative Artificial Intelligence on Creativity Enhancement: A Systematic Review and Meta-Analysis", PsyArXiv 10.31234/osf.io/jy3ba_v1; Shi et al. (2026), "Enhancing students\' Creativity with Generative Artificial Intelligence: A Systematic Review and Meta-Analysis", Creativity Research Journal 10.1080/10400419.2026.2726242; Peng et al. (2025), "The impact of AI-supported instructional interventions on students\' creative thinking: a meta-analysis of 56 experimental studies", 10.1080/15391523.2025.2557392; Lo Presti et al. (2026), Education Sciences 10.3390/educsci16091486; Guo (2026), Thinking Skills and Creativity 10.1016/j.tsc.2026.102336; Ren et al. (2026), Educational Psychology Review 10.1007/s10648-026-10217-5 (creativity outcomes only); Vaccaro, Almaatouq and Malone (2024), Nature Human Behaviour 10.1038/s41562-024-02024-1 (creation tasks with generative AI only). Also search for any other meta-analysis or systematic review on generative AI and creativity, co-creativity, or idea diversity from 2024 to 2026 and do the same. Record each synthesis itself as a candidate with "design_guess": "synthesis", and say in "evidence" how many studies it pools and its headline estimate if the abstract gives one. PDFs can be read in memory without writing files: fetch bytes with urllib and open them with pymupdf.open(stream=bytes, filetype="pdf").' },
  { id: 'after-ai', title: 'Unassisted creativity after AI use', body: 'Focus: question 3. Studies with a phase without AI after a phase with AI, or a delayed or transfer measure of creative performance or of output diversity: unassisted or independent creativity after AI exposure, withdrawal of AI, "creative scar", dependence or over-reliance and later creativity, deskilling of creative or writing ability, "think first, AI later" designs, multi-session and longitudinal designs, classroom interventions with a later unassisted creative task. Any outlet. Also list the works that cite these three papers (OpenAlex filter=cites:): Kumar et al. 2025 (W4409746216), Liu et al. 2024 (W4390961159), Zhou et al. "Creative scar without generative AI" (W4414497210), keeping those with their own data.' },
  { id: 'ai-design', title: 'Experiments that compare AI designs for creative work', body: 'Focus: experiments with human participants that compare ways of using or designing generative AI for a creative task, with creativity or diversity scored on the human output: timing of AI access (before or after generating one\'s own ideas), number or diversity of AI ideas shown, personas or diversified prompts, coach or question-asking AI versus answer-giving AI, provocations and cognitive friction, human-led versus model-led interaction, disclosure of AI use, group brainstorming with AI, and tools built to reduce homogenization. Any outlet. Say in "evidence" whether the study also has a no-AI arm.' },
  { id: 'professionals-field', title: 'Professionals and field settings', body: 'Focus: lab, online, or field experiments with professionals or inside organizations: advertising and marketing professionals, designers, architects, consultants, R&D staff, engineers, software developers, journalists, writers, scientists, entrepreneurs; hackathons, innovation contests, and crowdsourcing platforms with randomized AI access. Outcome: rated creativity, novelty, or quality of ideas or creative output, or the diversity of ideas across people. Any outlet, including practitioner-facing working papers from business schools.' },
  { id: 'replications-comments', title: 'Replications, comments, and re-analyses', body: 'Focus: replications, comments, corrections, author replies, and re-analyses of the main experiments: Doshi and Hauser (2024, Science Advances); Lee and Chung (2024, Nature Human Behaviour), including the replication report on OSF, the comment on EconStor, and Lee and Chung\'s reply to Meincke, Nave and Terwiesch (2025); Padmakumar and He (2024); Anderson, Shah and Kreminski (2024); Dell\'Acqua et al. (jagged frontier; cybernetic teammate); Noy and Zhang (2023, Science), which graded writing on originality among other things. Also: Institute for Replication (I4R) discussion papers, registered reports, multi-site studies on AI and creativity, and doctoral dissertations (ProQuest, university repositories) that report a randomized experiment on generative AI and creative output.' },
  { id: 'writing-homogenization', title: 'Experiments on writing assistance and convergence of text', body: 'Focus: randomized or controlled experiments on AI writing assistance (autocomplete, sentence suggestions, co-writing, rewriting, feedback) whose outcome is the similarity or diversity of what different writers produce: content, style, vocabulary, structure, cultural markers, or expressed opinions converging across writers. Includes predictive-text and opinionated-language-model studies when the tool is a generative language model, and cross-cultural writing studies. Any outlet.' },
  { id: 'design-engineering', title: 'Design and engineering research', body: 'Sources: Design Studies, Design Science, Journal of Mechanical Design, Journal of Engineering Design, Research in Engineering Design, International Journal of Design Creativity and Innovation, The Design Journal, Proceedings of the Design Society (ICED, DESIGN), ASME IDETC/DTM, Journal of Computing and Information Science in Engineering, Automation in Construction and architecture journals, and Creativity and Innovation Management. Look for experiments on generative AI (text or image) in concept generation and design ideation with novelty, variety, fixation, or quality outcomes scored on the designs.' },
]

phase('Search')
const lanes = (await parallel(LANES.map(l => () => agent(
  [
    'You are one of 18 search agents working in parallel on a literature screening. Each agent covers one lane and cannot see the others. Overlaps are removed later, so report everything relevant that you find in your lane.',
    '',
    PROJECT,
    '',
    'YOUR LANE: ' + l.id + ' (' + l.title + ')',
    l.body,
    '',
    EFFORT,
    '',
    TOOLS,
    '',
    RECORD_SPEC,
    '- Report only works you located in a primary record or an API record during this run.',
    '',
    KNOWN_BLOCK,
    '',
    'Output: write a JSON object to ' + DIR + '/lane-' + l.id + '.json with the Write tool (UTF-8), with these keys: "lane" ("' + l.id + '"), "queries" (every query or listing pass you ran, as short strings), "sources_checked" (journals, servers, or APIs you covered), "coverage_limits" (what you could not reach or did not finish, in a few sentences), and "candidates" (the list of records, with "lane" set to "' + l.id + '"). Then run python to confirm the file parses and to print the number of candidates; fix the file if it does not parse. Create no other files.',
    '',
    'Your structured reply is a short summary: "lane", "file", "n_candidates", "n_randomized_guess" (records with design_guess "randomized_experiment_people"), "n_queries", and "coverage_limits".',
  ].join('\n'),
  { label: 'search:' + l.id, phase: 'Search', schema: LANE_SCHEMA }
)))).filter(Boolean)

log('Lanes finished: ' + lanes.length + ' of ' + LANES.length + '; candidates reported: ' + lanes.reduce((a, r) => a + (r.n_candidates || 0), 0))

return {
  seeds: seeds.map(s => ({ file: s.file, n_records: s.n_records, notes: s.notes || '' })),
  known_titles: knownLines.length + LIBRARY_TITLES.length,
  lanes,
  lanes_missing: LANES.map(l => l.id).filter(id => !lanes.some(r => r.lane === id)),
}
