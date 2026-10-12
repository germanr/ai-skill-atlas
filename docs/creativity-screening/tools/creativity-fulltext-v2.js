export const meta = {
  name: 'creativity-fulltext-v2',
  description: 'Full-text screening of candidate experiments: two independent screeners, a reconciler, three challengers and a finalizer for core papers, and a citation check',
  phases: [
    { title: 'Screen', detail: 'two independent screeners fill the form for each paper' },
    { title: 'Reconcile', detail: 'a third agent settles every difference against the source' },
    { title: 'Challenge', detail: 'three skeptics per core paper: assignment, people, outcome' },
    { title: 'Finalize', detail: 'challenge findings are applied to the form against the source' },
    { title: 'Citation', detail: 'bibliographic record checked against primary sources' },
  ],
}

const ROOT = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening'
const MODEL = 'claude-opus-5-5'  // Germán, 2026-10-08: subagents run on Opus 5.5 to save capacity
const CODEBOOK = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-codebook.md'
const SPEC = ROOT + '/form-spec.md'
const CIDS = args.cids
// args.skip_screen: cids whose reconciled form already exists (run challenges, finalize, and citation only when missing).
const SKIP_SCREEN = new Set(args.skip_screen || [])
const SKIP_CITE = new Set(args.skip_cite || [])
const SKIP_CHALLENGE = new Set(args.skip_challenge || [])
// args.skip_raw: cids whose two raw forms (forms/raw/<cid>.A.json and .B.json) already exist: reconcile them without screening again.
const SKIP_RAW = new Set(args.skip_raw || [])

const INTRO = 'This is part of a full-text literature screening for the AI and Human Skill Atlas (aiskillatlas.org), a living meta-analysis that is adding a section on generative AI and creativity, ideation, and homogenization of ideas. A later audit checks every recorded number against the PDF, so accuracy matters more than speed.'

const FILES = cid => [
  'Paper: ' + cid + '.',
  '- Its search record is the object with "cid": "' + cid + '" in ' + ROOT + '/candidates.json. The notes there ("evidence", "design_guesses") are unverified leads.',
  '- Its files are under key "' + cid + '" in ' + ROOT + '/retrieval.json: "md_path" is a markdown conversion of the PDF at "pdf_path". The entry may also say which version of the paper is on file ("version_saved") and how it differs from the latest version.',
  '- The Read tool opens PDFs with its "pages" parameter (at most 20 pages per call). The markdown can be long: read it in chunks with offset and limit until you have covered the whole document, appendices included.',
].join('\n')

const HOW = {
  A: 'How to read the paper: read the markdown from start to end, design and methods before results. Then open the PDF pages that hold the design description, the participant counts, and each table or figure you cite, and check your entries against those pages.',
  B: 'How to read the paper: start with the PDF. Go through the tables, figures, and any appendix or supplement first and list every outcome they report. Then read the design and methods sections to establish who was assigned to what. Check each entry against the PDF page.',
}

const screenPrompt = (cid, s) => [
  'You are screener ' + s + ' for one paper. ' + INTRO,
  'A second screener fills the same form independently, and a third agent then compares the two forms against the source.',
  '',
  FILES(cid),
  '',
  'Read first:',
  '1. ' + CODEBOOK + ' (scope, the three questions, eligibility, and the coded vocabulary).',
  '2. ' + SPEC + ' (the form and its rules).',
  '',
  HOW[s],
  '',
  'Then fill the form for this paper and save it with the Write tool to ' + ROOT + '/forms/raw/' + cid + '.' + s + '.json, with "cid": "' + cid + '" and "screener": "' + s + '". Confirm with python that the file parses. Do not open any other file under ' + ROOT + '/forms. Create no other files.',
  '',
  'Points that screeners often get wrong:',
  '- Whether people were randomly assigned to AI assistance, or whether the paper compares AI-generated output with human-generated output. In the second case no person receives AI help and the design class is "ai_vs_human".',
  '- Participant counts. Count people. A paper that reports 400 ideas or 200 essays may have far fewer participants. Write "analyzed" for a count after exclusions and "randomized" only for a count given at assignment.',
  '- Whether AI was available while the scored output was produced. An outcome measured after AI was taken away is "after_ai".',
  '- Whether the paper reanalyzes another paper\'s participants ("sample_overlap").',
  '- Whether the statistics sit in a supplement that is not in this PDF ("source.supplement").',
  '- Papers with no human participants at all (model-only studies, theory, reviews): fill "source", "paper_design_summary", one study entry with the right "design_class", the "synthesis" block for reviews, "eligibility", and "one_line_finding"; leave the rest at its defaults.',
  '',
  'Your structured reply is a short summary of your form: "main_design_class" is the design class of the study that best supports eligibility; "n_people_analyzed" is the largest number of people analyzed in a single study (null if the paper has no human participants or does not say).',
].join('\n')

const reconcilePrompt = cid => [
  'You are the reconciler for one paper. ' + INTRO,
  'Two screeners filled the same form independently. You produce the final form and settle every difference between them against the source document.',
  '',
  FILES(cid),
  '',
  'Other inputs:',
  '- ' + CODEBOOK + ' and ' + SPEC + ': the definitions and the form.',
  '- The two raw forms: ' + ROOT + '/forms/raw/' + cid + '.A.json and ' + ROOT + '/forms/raw/' + cid + '.B.json. If one of them is missing or does not parse, say so in your reply, screen the paper yourself from the source, and treat every field as a difference.',
  '',
  'Steps:',
  '1. Read both forms and list every substantive difference: design class; assignment (randomized, unit, structure); arms; participant counts; AI tool and role; task; which outcomes are listed; each outcome\'s construct, question, measure, unit, AI availability, timing, and primary status; the reported statistics and their locators; the supplement; sample overlap; company involvement; each eligibility criterion; the one-line finding. Differences of wording that mean the same thing do not count.',
  '2. Settle each difference from the source: open the passage (markdown first, then the PDF page) and decide which form is right, or that neither is. Record the resolved value with a verbatim quote (40 words at most) and a locator. If the source does not settle it, mark it unresolved and say what is missing.',
  '3. Agreement between the screeners is not proof. Confirm from the source, once each, the facts that decide eligibility even where the forms agree: how assignment was done, the number of people analyzed, that the outcome is scored on the output, and whether AI was available when the output was produced.',
  '4. Keep an outcome that only one screener listed if the source supports it.',
  '5. Write the final form to ' + ROOT + '/forms/' + cid + '.json: the structure in the spec, with "screener": "reconciled", plus a top-level "reconciliation" object with "differences" (a list of objects with "field", "a", "b", "resolved", "quote", "locator", and "status" equal to "resolved" or "unresolved"), "agreed_fields_checked" (a list of objects with "field", "value", "quote", "locator", "confirmed"), "n_differences", and "n_unresolved". Confirm with python that the file parses. Create no other files.',
  '',
  'Your structured reply summarizes the final form. "core" repeats eligibility.core. "unresolved" lists each unresolved item in a few words. "questions" lists which of with_ai, across_people, after_ai the paper\'s outcomes answer.',
].join('\n')

const LENSES = [
  {
    id: 'assignment',
    claim: 'the paper is a randomized experiment in which people were randomly assigned to generative-AI assistance',
    criterion: 'people were randomly assigned to conditions that differ in generative-AI assistance (criterion 1)',
    read: 'Read "studies[].assignment", "arms", and "ai_tool" in the final form.',
    checks: 'For each study the form calls randomized, check: (a) does the document itself say that assignment to conditions was random, and where; (b) what was assigned: access to a generative-AI tool, or AI-generated material, for the participant\'s own work, as opposed to conditions that only differ in whose output gets evaluated; (c) is the tool generative AI (a large language model or an image generator); (d) does the comparison arm match the form (no AI, another aid, or another AI configuration); (e) in a within-person design, was the order of conditions randomized.',
  },
  {
    id: 'people',
    claim: 'at least 50 people took part, and the participant counts in the form are right',
    criterion: 'at least 50 people were analyzed across all arms of at least one randomized study (criterion 2)',
    read: 'Read "studies[].participants" and "arms" in the final form.',
    checks: 'Check: (a) the number of people randomized and analyzed in each study and arm, from the participant section, any flow diagram, the tables, and the appendix; (b) that the form\'s counts are people and not ideas, texts, ratings, sessions, or pairs; (c) exclusions and attrition between randomization and analysis; (d) whether the same people appear in more than one study of the paper, or in another paper; (e) whether at least one study on its own has 50 or more people analyzed.',
  },
  {
    id: 'outcome',
    claim: 'the paper scores creativity or diversity on the output that participants produced, and each outcome\'s question, construct, measure, unit, and AI availability are coded correctly',
    criterion: 'at least one outcome is scored on the output that participants produced, by raters or a computed measure (criterion 3)',
    read: 'Read "studies[].outcomes" in the final form, and the codebook sections on questions and outcome fields.',
    checks: 'For each outcome in the form, check: (a) it is scored on the produced output, by raters or a computed measure, and is not self-reported; (b) whether AI was available while that output was produced, and whether "question" follows the codebook rule (after AI is removed: after_ai; with AI and a diversity construct: across_people; otherwise with_ai); (c) the construct (diversity always compares different people; variety within one person is flexibility); (d) the unit is the unit of the paper\'s own analysis; (e) the "reported" numbers match the cited table or figure exactly. Also look for outcomes that bear on the three questions and are missing from the form.',
  },
]

const challengePrompt = (cid, lens) => [
  'You are a skeptical checker. ' + INTRO,
  'Another agent has concluded that, for paper ' + cid + ', ' + lens.claim + '. Try to refute that conclusion from the source document.',
  '',
  FILES(cid),
  '',
  'Other inputs: the final form at ' + ROOT + '/forms/' + cid + '.json, and the definitions in ' + CODEBOOK + '. ' + lens.read + ' Do not rely on the form\'s quotes: find the passages in the PDF yourself.',
  '',
  lens.checks,
  '',
  'Give two verdicts.',
  '- "refuted": true if any part of the coding is wrong or is not supported by the text; false only if you found explicit support for each part. If you cannot find the supporting text, the answer is true.',
  '- "eligibility_holds": does this conclusion stand after your check: ' + lens.criterion + '? Answer "yes", "no", or "unclear". Errors of detail that leave this conclusion intact do not change the answer.',
  '',
  'Write a JSON object to ' + ROOT + '/forms/challenges/' + cid + '.' + lens.id + '.json with "cid", "lens" ("' + lens.id + '"), "refuted", "eligibility_holds", "problems" (a list of objects with "where" (study or outcome id), "field", "form_value", "source_says", "quote" (verbatim, 40 words at most), "locator"), "confirmed" (a list of short statements you verified, each with its locator), and "summary" (two sentences). Confirm with python that it parses. Do not change the form. Create no other files. Reply with the same content in brief.',
].join('\n')

const finalizePrompt = cid => [
  'You are the finalizer for one paper. ' + INTRO,
  'Skeptical checkers have examined the reconciled screening form of paper ' + cid + '. You apply what they found, after confirming each point against the source, and state the final eligibility.',
  '',
  FILES(cid),
  '',
  'Other inputs:',
  '- ' + CODEBOOK + ' and ' + SPEC + ': the definitions and the form (the spec may have gained fields since the form was written).',
  '- The form: ' + ROOT + '/forms/' + cid + '.json.',
  '- The challenge files: every file matching ' + ROOT + '/forms/challenges/' + cid + '.*.json (list the folder with python or Glob). Each has "problems" with quotes and locators.',
  '',
  'Steps:',
  '1. For each problem in each challenge file, open the source passage yourself and decide: "corrected" (the checker is right: fix the form), "rejected" (the form was right: say why, with a quote), or "open" (the source does not settle it).',
  '2. Apply the corrections to the form. Also bring the form in line with the current spec: fill "source.supplement" if it is missing; a reanalysis of another paper\'s experiment takes that experiment\'s design class; prose says "analyzed" for counts after exclusions.',
  '3. Re-evaluate the three eligibility criteria after the corrections and update "eligibility".',
  '4. Go through "open_questions" and any unresolved item in "reconciliation.differences". For each, say whether it affects an eligibility criterion and what would settle it: "supplement", "posted_data", "authors", "journal_version", or "nothing_needed".',
  '5. Rewrite ' + ROOT + '/forms/' + cid + '.json with the same structure, "screener": "final", the "reconciliation" object unchanged, and a new top-level "final" object: {"core": "yes" | "no" | "unclear", "criteria": {"random_assignment_of_ai": "met" | "not_met" | "unclear", "at_least_50_people": "met" | "not_met" | "unclear", "outcome_scored_on_output": "met" | "not_met" | "unclear"}, "challenge_resolution": [{"lens": "...", "problem": "...", "action": "corrected" | "rejected" | "open", "what_changed": "...", "quote": "...", "locator": "..."}], "open_items": [{"item": "...", "affects_eligibility": true | false, "settled_by": "..."}], "n_corrected": 0, "n_rejected": 0, "n_open": 0}. Confirm with python that the file parses. Create no other files.',
  '',
  'Your structured reply: "core" and the three criteria from the "final" object, the three counts, and "open_eligibility_items" (the open items that affect eligibility, in a few words each).',
].join('\n')

const citePrompt = cid => [
  'You are the citation checker for one paper. ' + INTRO,
  'The owner\'s rule is strict: never fabricate or guess any reference field. Confirm the bibliographic record of paper ' + cid + ' against primary sources.',
  '',
  'Inputs: the object with "cid": "' + cid + '" in ' + ROOT + '/candidates.json (title, authors, year, venue, DOI, arXiv id, URL, other versions: all unverified), and, if a file is on record, the first pages of the PDF at "pdf_path" under key "' + cid + '" in ' + ROOT + '/retrieval.json (Read tool, "pages": "1-2").',
  '',
  'Check against the Crossref API (https://api.crossref.org/works/<doi> or ?query.bibliographic=...), the OpenAlex API (https://api.openalex.org/works/doi:<doi>), the arXiv API (http://export.arxiv.org/api/query?id_list=<id>), the OSF API, or the publisher page: the exact title; the full author list in order; the year; the venue with volume, issue, and pages or article number; the DOI; and every version of the work (preprint ids with dates, journal publication date). Establish which version the PDF on disk is and whether a later version exists. Use Python urllib through PowerShell for the APIs; send no email address or personal identifier in headers. WebSearch and WebFetch may need loading with ToolSearch (query "select:WebSearch,WebFetch"). Many publisher sites return HTTP 403 to scripts; the APIs usually suffice.',
  '',
  'Write a JSON object to ' + ROOT + '/forms/citations/' + cid + '.json with "cid", "pdf_version" (what the PDF on disk is, or null if none), "latest_version" (an object with "title", "authors" (list of full names in order), "authors_family" (the family names in the same order, as Crossref or the publisher gives them, for example "Van de Cruys", "de Rooij", "Dell\'Acqua"), "year", "venue", "volume_issue_pages", "doi", "url", "status" (journal, proceedings, working_paper, or preprint), "date"), "other_versions" (a list of objects with "what", "id_or_doi", "date", "title_if_different"), "pdf_is_latest" (true, false, or null), "corrections_to_candidate_record" (a list of strings; empty if the record was right), "checked_against" (which sources you used), and "unverified_fields" (fields you could not confirm). Write null for anything you could not confirm. Confirm with python that the file parses. Create no other files.',
  '',
  'Your structured reply: "citation" is one line in the form Authors (Year), "Title", Venue; "corrections" repeats corrections_to_candidate_record.',
].join('\n')

const SCREEN_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    screener: { type: 'string' },
    file: { type: 'string' },
    main_design_class: { type: 'string' },
    randomized: { type: 'string' },
    n_people_analyzed: { type: ['integer', 'null'] },
    core: { type: 'string', enum: ['yes', 'no', 'unclear'] },
    context_class: { type: 'string' },
    n_studies: { type: 'integer' },
    n_outcomes: { type: 'integer' },
  },
  required: ['cid', 'file', 'main_design_class', 'core'],
}
const RECON_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    file: { type: 'string' },
    main_design_class: { type: 'string' },
    core: { type: 'string', enum: ['yes', 'no', 'unclear'] },
    context_class: { type: 'string' },
    n_people_analyzed: { type: ['integer', 'null'] },
    n_differences: { type: 'integer' },
    n_unresolved: { type: 'integer' },
    unresolved: { type: 'array', items: { type: 'string' } },
    questions: { type: 'array', items: { type: 'string' } },
    one_line_finding: { type: 'string' },
  },
  required: ['cid', 'file', 'main_design_class', 'core', 'n_differences', 'n_unresolved'],
}
const CHALLENGE_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    lens: { type: 'string' },
    refuted: { type: 'boolean' },
    eligibility_holds: { type: 'string', enum: ['yes', 'no', 'unclear'] },
    n_problems: { type: 'integer' },
    summary: { type: 'string' },
  },
  required: ['cid', 'lens', 'refuted', 'eligibility_holds', 'summary'],
}
const FINAL_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    core: { type: 'string', enum: ['yes', 'no', 'unclear'] },
    random_assignment_of_ai: { type: 'string' },
    at_least_50_people: { type: 'string' },
    outcome_scored_on_output: { type: 'string' },
    n_corrected: { type: 'integer' },
    n_rejected: { type: 'integer' },
    n_open: { type: 'integer' },
    open_eligibility_items: { type: 'array', items: { type: 'string' } },
  },
  required: ['cid', 'core', 'n_corrected', 'n_rejected', 'n_open'],
}
const CITE_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    file: { type: 'string' },
    citation: { type: 'string' },
    corrections: { type: 'array', items: { type: 'string' } },
  },
  required: ['cid', 'citation'],
}

const screenOnce = (cid, s) => agent(screenPrompt(cid, s), { model: MODEL, label: 'screen ' + s + ':' + cid, phase: 'Screen', schema: SCREEN_SCHEMA, effort: 'high' })
const screenWithRetry = async (cid, s) => (await screenOnce(cid, s)) || (await screenOnce(cid, s))

const results = await pipeline(
  CIDS,
  async cid => {
    if (SKIP_SCREEN.has(cid)) return { skipped: true }
    const screens = SKIP_RAW.has(cid) ? [] : await parallel(['A', 'B'].map(s => () => screenWithRetry(cid, s)))
    const recon = await agent(reconcilePrompt(cid), { model: MODEL, label: 'reconcile:' + cid, phase: 'Reconcile', schema: RECON_SCHEMA })
    return { screens, recon }
  },
  async (prev, cid) => {
    const recon = prev.recon
    const core = prev.skipped || (recon && (recon.core === 'yes' || recon.core === 'unclear'))
    const tasks = []
    tasks.push(SKIP_CITE.has(cid) ? () => Promise.resolve({ cid, citation: 'kept from earlier run', corrections: [] })
      : () => agent(citePrompt(cid), { model: MODEL, label: 'cite:' + cid, phase: 'Citation', schema: CITE_SCHEMA, effort: 'medium' }))
    if (core && !SKIP_CHALLENGE.has(cid)) {
      for (const lens of LENSES) {
        tasks.push(() => agent(challengePrompt(cid, lens), { model: MODEL, label: 'challenge ' + lens.id + ':' + cid, phase: 'Challenge', schema: CHALLENGE_SCHEMA }))
      }
    }
    const out = await parallel(tasks)
    return { prev, core, cite: out[0], challenges: out.slice(1).filter(Boolean) }
  },
  async (mid, cid) => {
    const recon = mid.prev.recon
    let fin = null
    if (mid.core) {
      fin = await agent(finalizePrompt(cid), { model: MODEL, label: 'finalize:' + cid, phase: 'Finalize', schema: FINAL_SCHEMA })
    }
    const screens = mid.prev.screens || []
    return {
      cid,
      screens: screens.map(x => x ? { s: x.screener, design: x.main_design_class, core: x.core, n: x.n_people_analyzed } : null),
      design: recon ? recon.main_design_class : null,
      recon_core: recon ? recon.core : (mid.prev.skipped ? 'kept' : 'reconcile_failed'),
      n: recon ? recon.n_people_analyzed : null,
      questions: recon ? recon.questions : [],
      n_differences: recon ? recon.n_differences : null,
      unresolved: recon ? (recon.unresolved || []) : [],
      challenges: mid.challenges.map(c => ({ lens: c.lens, refuted: c.refuted, holds: c.eligibility_holds })),
      final_core: fin ? fin.core : null,
      final_open: fin ? (fin.open_eligibility_items || []) : [],
      corrected: fin ? fin.n_corrected : null,
      citation: mid.cite ? mid.cite.citation : null,
      citation_corrections: mid.cite ? (mid.cite.corrections || []) : ['citation check failed'],
    }
  }
)

const done = results.filter(Boolean)
log('Papers finished: ' + done.length + ' of ' + CIDS.length)
return {
  papers: done,
  failed: CIDS.filter(c => !done.some(d => d.cid === c)),
}
