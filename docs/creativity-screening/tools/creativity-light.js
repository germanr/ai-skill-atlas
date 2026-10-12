export const meta = {
  name: 'creativity-light',
  description: 'Short-form screening for context papers, small experiments, and experiments with no full text on file: one screener, an independent checker, a fixer when they disagree, and a citation check',
  phases: [
    { title: 'Screen', detail: 'one screener fills the short form' },
    { title: 'Check', detail: 'an independent agent checks the form against the source' },
    { title: 'Fix', detail: 'corrections applied when the checker disagrees' },
    { title: 'Citation', detail: 'bibliographic record checked against primary sources' },
  ],
}

const ROOT = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening'
const MODEL = 'claude-opus-5-5'  // Germán, 2026-10-08: subagents run on Opus 5.5 to save capacity
const CODEBOOK = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-codebook.md'
const SPEC = ROOT + '/form-spec.md'
const ITEMS = [
  ...(args.context || []).map(cid => ({ cid, kind: 'context' })),
  ...(args.small || []).map(cid => ({ cid, kind: 'small' })),
  ...(args.abstract_only || []).map(cid => ({ cid, kind: 'abstract_only' })),
  ...(args.nonrandom || []).map(cid => ({ cid, kind: 'nonrandom' })),
]
// Finishing an interrupted run: skip_screen keeps an existing form, skip_check and skip_cite keep existing
// check and citation files, and needs_fix lists forms whose saved check disagreed but no fix was applied.
const SKIP_SCREEN = new Set(args.skip_screen || [])
const SKIP_CHECK = new Set(args.skip_check || [])
const SKIP_CITE = new Set(args.skip_cite || [])
const NEEDS_FIX = new Set(args.needs_fix || [])

const INTRO = 'This is part of a literature screening for the AI and Human Skill Atlas (aiskillatlas.org), a living meta-analysis that is adding a section on generative AI and creativity, ideation, and homogenization of ideas. A later audit checks every recorded number against its source, so accuracy matters more than speed.'

const FILES = cid => [
  'Paper: ' + cid + '.',
  '- Its search record is the object with "cid": "' + cid + '" in ' + ROOT + '/candidates.json. The notes there ("evidence", "design_guesses") are unverified leads.',
  '- Its triage record is the object with "cid": "' + cid + '" in ' + ROOT + '/triage/decisions.json (two screeners\' readings of the abstract).',
  '- If a full text is on file, key "' + cid + '" in ' + ROOT + '/retrieval.json has "status": "ok" with "md_path" (markdown) and "pdf_path" (PDF; the Read tool opens it with "pages", 20 per call). Check every number against the PDF page, because the markdown conversion can drop or scramble tables.',
  '- If no full text is on file, work from primary records you can reach without credentials: the abstract through the OpenAlex, Crossref, arXiv, Semantic Scholar, or Europe PMC APIs (Python urllib through PowerShell; no email address in headers), an open HTML full text on the publisher\'s site if one loads, or a preprint. You may read a PDF in memory with pymupdf without saving it. Do not try to get past paywalls, logins, or bot checks. Set "source.version" to say exactly what you read, for example "abstract only (Crossref)" or "arXiv v2 read in memory".',
].join('\n')

const SHORT = {
  context: [
    'Context papers are listed on the site with a one-line finding and never enter a pooled estimate. Fill the SHORT version of the form:',
    '- "source" (including "supplement" if you can tell) and "paper_design_summary".',
    '- One entry in "studies" per study or dataset: "study_id", "label", "design_class", "assignment" (fill "randomized", "quote", and "locator" only if people are assigned to conditions), "participants" (people if there are any; for a corpus, describe it in "who" and put its size in each outcome\'s "n_units"), "ai_tool", "task".',
    '- Up to five main outcomes that bear on the three questions, each with "name", "construct", "question" ("none" when AI output is compared with human output; otherwise the closest of the three), "measure", "unit", "n_units", and one contrast with "treatment_arm", "control_arm", "comparison_type", "direction", "reported" (numbers exactly as printed), and "locator".',
    '- The "synthesis" block for reviews and meta-analyses: number of studies, number of effect sizes, search end date, inclusion rule, and every pooled estimate with its interval, what it compares, and what it standardizes.',
    '- "eligibility": "core" is "no" and "context_class" is "ai_vs_human", "observational", "synthesis", or "none" (with the reason, for example a count of AI text with no diversity or novelty outcome, a model-only study, or a narrative review). One exception: if the paper contains a study in which people were randomly assigned to generative-AI assistance and creativity or diversity was scored on their output, set "core" to "unclear" and say so in "reason"; the paper then goes to the two-screener pipeline.',
    '- "one_line_finding": one plain sentence with the main numbers and where they are printed.',
  ].join('\n'),
  small: [
    'Triage read fewer than 50 participants in this experiment. Under the current rule, randomized experiments with fewer than 50 participants are listed in the screening report and left out of the dataset. Your job is to confirm the participant count and the design. Fill the SHORT version of the form:',
    '- "source" and "paper_design_summary".',
    '- One entry in "studies" per experiment: "design_class", "assignment" ("randomized", "what_was_assigned", "unit", "structure", "quote", "locator"), "arms" with counts, "participants" ("n_randomized", "n_analyzed", "counts_are", "population", "who", "quote", "locator"), "ai_tool", "task".',
    '- Up to three main outcomes, each with "name", "construct", "question", "measure", "unit", and one contrast with "reported" and "locator".',
    '- "eligibility": criterion 2 is "not_met" when fewer than 50 people were analyzed across all arms. If you find 50 or more, set "core" to "unclear" and explain: the paper then goes to the two-screener pipeline.',
    '- "one_line_finding".',
  ].join('\n'),
  nonrandom: [
    'Triage read a design in which people were not randomly assigned to generative-AI assistance: a quasi-experiment, a classroom or cohort comparison, a single-group before-and-after study, or self-selected groups. Under the codebook only randomized experiments enter the core dataset. Your job is to confirm the assignment mechanism from the text and record the main result. Fill the SHORT version of the form:',
    '- "source" and "paper_design_summary".',
    '- One entry in "studies" per study: "design_class", "assignment" ("randomized", "what_was_assigned", "unit", "structure", "quote", "locator"; quote the sentence that says how people came to be in each condition), "arms" with counts, "participants" ("n_randomized" only if assignment was random, "n_analyzed", "counts_are", "population", "who", "quote", "locator"), "ai_tool", "task".',
    '- Up to three main outcomes, each with "name", "construct", "question", "measure", "unit", and one contrast with "reported" and "locator".',
    '- "eligibility": criterion 1 is "not_met" when the text states a non-random allocation and "unclear" when the text does not say how people were allocated. If you find that people were randomly assigned to conditions that differ in generative-AI assistance, set "core" to "unclear" and explain: the paper then goes to the two-screener pipeline.',
    '- "one_line_finding".',
  ].join('\n'),
  abstract_only: [
    'Triage called this an experiment, and no full text could be obtained. The paper will be listed as "full text not obtained" so that the owner can download it. Fill the SHORT version of the form from what you can reach:',
    '- "source" (say exactly what you read) and "paper_design_summary".',
    '- One entry in "studies" per experiment: "design_class", "assignment" ("randomized" is "not_stated" unless the text you read states it; "quote"; "locator" such as "abstract"), "arms", "participants" (counts only if stated), "ai_tool", "task".',
    '- The outcomes the abstract names, each with "name", "construct", "question", "measure" if stated, and one contrast with "reported" (numbers exactly as printed, or an empty string) and "locator".',
    '- "eligibility": each criterion is "met", "not_met", or "unclear" on the evidence you read, and "core" is "unclear" unless a criterion clearly fails.',
    '- "one_line_finding", and in "open_questions" what the full text must settle (random assignment, people analyzed, how the outcome was scored, whether AI was available).',
  ].join('\n'),
}

const TAG = { context: 'single', small: 'single_small', abstract_only: 'single_abstract', nonrandom: 'single_nonrandom' }

const screenPrompt = item => [
  'You are the screener for one paper. ' + INTRO,
  'An independent checker will compare your form with the source.',
  '',
  FILES(item.cid),
  '',
  'Read first: ' + CODEBOOK + ' (scope, the three questions, eligibility, vocabulary) and ' + SPEC + ' (the form and its rules).',
  '',
  SHORT[item.kind],
  '',
  'Leave every other field of the form at its default. Save the form with the Write tool to ' + ROOT + '/forms/' + item.cid + '.json, with "cid": "' + item.cid + '" and "screener": "' + TAG[item.kind] + '". Confirm with python that the file parses. Do not open any other file under ' + ROOT + '/forms. Create no other files.',
  '',
  'Your structured reply is a short summary of the form.',
].join('\n')

const checkPrompt = item => [
  'You are the checker for one paper. ' + INTRO,
  'Another agent filled a short screening form at ' + ROOT + '/forms/' + item.cid + '.json. Check it against the source, independently: find the passages yourself.',
  '',
  FILES(item.cid),
  '',
  'Definitions: ' + CODEBOOK + '. Form rules: ' + SPEC + '.',
  '',
  'Check:',
  '1. The design class and the context class. Does the paper contain any study in which people were randomly assigned to generative-AI assistance, with creativity or diversity scored on their output? If so it belongs in the two-screener pipeline: set "has_randomized_people_study" to true and describe the study.',
  '2. The counts: people versus texts, ideas, or ratings; people randomized versus analyzed; for small experiments, whether fewer than 50 people were analyzed.',
  '3. Every "reported" string and the one-line finding: the numbers must match the cited table, figure, or passage exactly.',
  '4. For syntheses: the number of studies, the pooled estimates, their intervals, and what they standardize.',
  '5. The version read ("source.version") and whether the form says more than that source supports.',
  '',
  'Write a JSON object to ' + ROOT + '/forms/checks/' + item.cid + '.json: {"cid": "' + item.cid + '", "agrees": true or false, "has_randomized_people_study": true or false, "corrections": [{"field": "...", "form_value": "...", "source_says": "...", "quote": "verbatim, 40 words at most", "locator": "..."}], "confirmed": ["short statements you verified, with locators"], "summary": "two sentences"}. "agrees" is true only if you found nothing to correct. Confirm with python that it parses. Do not change the form. Create no other files. Reply with the same content in brief.',
].join('\n')

const fixPrompt = item => [
  'You are the fixer for one paper. ' + INTRO,
  'A checker found problems in the short screening form at ' + ROOT + '/forms/' + item.cid + '.json. The problems are in ' + ROOT + '/forms/checks/' + item.cid + '.json ("corrections").',
  '',
  FILES(item.cid),
  '',
  'Definitions: ' + CODEBOOK + '. Form rules: ' + SPEC + '.',
  '',
  'For each correction, open the source passage yourself and decide whether the checker or the form is right. Apply the corrections that hold. Then rewrite ' + ROOT + '/forms/' + item.cid + '.json with the same structure, "screener" set to its current value plus "_fixed", and a new top-level "fix" object: {"applied": [{"field": "...", "old": "...", "new": "...", "quote": "...", "locator": "..."}], "rejected": [{"field": "...", "why": "...", "quote": "...", "locator": "..."}]}. Re-evaluate "eligibility" after the changes. Confirm with python that the file parses. Create no other files.',
  '',
  'Your structured reply gives the final "core" and "context_class" and the number of corrections applied and rejected.',
].join('\n')

const citePrompt = cid => [
  'You are the citation checker for one paper. ' + INTRO,
  'The owner\'s rule is strict: never fabricate or guess any reference field. Confirm the bibliographic record of paper ' + cid + ' against primary sources.',
  '',
  'Inputs: the object with "cid": "' + cid + '" in ' + ROOT + '/candidates.json (title, authors, year, venue, DOI, arXiv id, URL, other versions: all unverified), and, if a file is on record, the first pages of the PDF at "pdf_path" under key "' + cid + '" in ' + ROOT + '/retrieval.json (Read tool, "pages": "1-2").',
  '',
  'Check against the Crossref API (https://api.crossref.org/works/<doi> or ?query.bibliographic=...), the OpenAlex API (https://api.openalex.org/works/doi:<doi>), the arXiv API (http://export.arxiv.org/api/query?id_list=<id>), the OSF API, or the publisher page: the exact title; the full author list in order; the year; the venue with volume, issue, and pages or article number; the DOI; and every version of the work (preprint ids with dates, journal publication date). Establish which version the PDF on disk is, if there is one, and whether a later version exists. Use Python urllib through PowerShell for the APIs; send no email address or personal identifier in headers. WebSearch and WebFetch may need loading with ToolSearch (query "select:WebSearch,WebFetch"). Many publisher sites return HTTP 403 to scripts; the APIs usually suffice.',
  '',
  'Write a JSON object to ' + ROOT + '/forms/citations/' + cid + '.json with "cid", "pdf_version" (what the PDF on disk is, or null if none), "latest_version" (an object with "title", "authors" (list of full names in order), "authors_family" (the family names in the same order, as Crossref or the publisher gives them, for example "Van de Cruys", "de Rooij", "Dell\'Acqua"), "year", "venue", "volume_issue_pages", "doi", "url", "status" (journal, proceedings, working_paper, or preprint), "date"), "other_versions" (a list of objects with "what", "id_or_doi", "date", "title_if_different"), "pdf_is_latest" (true, false, or null), "corrections_to_candidate_record" (a list of strings; empty if the record was right), "checked_against" (which sources you used), and "unverified_fields" (fields you could not confirm). Write null for anything you could not confirm. Confirm with python that the file parses. Create no other files.',
  '',
  'Your structured reply: "citation" is one line in the form Authors (Year), "Title", Venue; "corrections" repeats corrections_to_candidate_record.',
].join('\n')

const SCREEN_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    main_design_class: { type: 'string' },
    core: { type: 'string', enum: ['yes', 'no', 'unclear'] },
    context_class: { type: 'string' },
    n_people_analyzed: { type: ['integer', 'null'] },
    version_read: { type: 'string' },
  },
  required: ['cid', 'main_design_class', 'core'],
}
const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    agrees: { type: 'boolean' },
    has_randomized_people_study: { type: 'boolean' },
    n_corrections: { type: 'integer' },
    summary: { type: 'string' },
  },
  required: ['cid', 'agrees', 'has_randomized_people_study', 'summary'],
}
const FIX_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    core: { type: 'string', enum: ['yes', 'no', 'unclear'] },
    context_class: { type: 'string' },
    n_applied: { type: 'integer' },
    n_rejected: { type: 'integer' },
  },
  required: ['cid', 'core'],
}
const CITE_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    citation: { type: 'string' },
    corrections: { type: 'array', items: { type: 'string' } },
  },
  required: ['cid', 'citation'],
}

const results = await pipeline(
  ITEMS,
  async item => {
    if (SKIP_SCREEN.has(item.cid)) return { screen: null, kept: true }
    const screen = await agent(screenPrompt(item), { model: MODEL, label: 'screen ' + item.kind + ':' + item.cid, phase: 'Screen', schema: SCREEN_SCHEMA, effort: 'high' })
      || await agent(screenPrompt(item), { model: MODEL, label: 'screen retry:' + item.cid, phase: 'Screen', schema: SCREEN_SCHEMA, effort: 'high' })
    return { screen }
  },
  async (prev, item) => {
    const [check, cite] = await parallel([
      () => SKIP_CHECK.has(item.cid)
        ? Promise.resolve({ cid: item.cid, agrees: NEEDS_FIX.has(item.cid) ? false : null, has_randomized_people_study: null, summary: 'kept from earlier run' })
        : agent(checkPrompt(item), { model: MODEL, label: 'check:' + item.cid, phase: 'Check', schema: CHECK_SCHEMA }),
      () => SKIP_CITE.has(item.cid)
        ? Promise.resolve({ cid: item.cid, citation: 'kept from earlier run', corrections: [] })
        : agent(citePrompt(item.cid), { model: MODEL, label: 'cite:' + item.cid, phase: 'Citation', schema: CITE_SCHEMA, effort: 'medium' }),
    ])
    return { ...prev, check, cite }
  },
  async (prev, item) => {
    let fix = null
    if (prev.check && prev.check.agrees === false) {
      fix = await agent(fixPrompt(item), { model: MODEL, label: 'fix:' + item.cid, phase: 'Fix', schema: FIX_SCHEMA })
    }
    const s = prev.screen
    return {
      cid: item.cid,
      kind: item.kind,
      design: s ? s.main_design_class : null,
      core: fix ? fix.core : (s ? s.core : (prev.kept ? 'kept' : 'screen_failed')),
      context_class: fix ? fix.context_class : (s ? s.context_class : null),
      n: s ? s.n_people_analyzed : null,
      check_agrees: prev.check ? prev.check.agrees : null,
      has_rct: prev.check ? prev.check.has_randomized_people_study : null,
      fixed: fix ? fix.n_applied : 0,
      citation: prev.cite ? prev.cite.citation : null,
    }
  }
)

const done = results.filter(Boolean)
log('Papers finished: ' + done.length + ' of ' + ITEMS.length)
return {
  papers: done,
  failed: ITEMS.map(i => i.cid).filter(c => !done.some(d => d.cid === c)),
  promote_to_full_pipeline: done.filter(d => d.core === 'unclear' || d.has_rct).map(d => d.cid),
}
