export const meta = {
  name: 'creativity-triage',
  description: 'Abstract-level triage of search candidates: two independent agents classify each batch of ten',
  phases: [
    { title: 'Triage', detail: 'two independent classifications per batch of ten candidates' },
  ],
}

const ROOT = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening'
const MODEL = 'claude-opus-5-5'  // Germán, 2026-10-08: subagents run on Opus 5.5 to save capacity
const CODEBOOK = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-codebook.md'
const CIDS = args.cids
const BATCH = 10
const batches = []
for (let i = 0; i < CIDS.length; i += BATCH) batches.push(CIDS.slice(i, i + BATCH))

const ITEM = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    verdict: { type: 'string', enum: ['experiment', 'context_ai_vs_human', 'context_observational', 'context_synthesis', 'out'] },
    out_reason: { type: ['string', 'null'] },
    randomized: { type: 'string', enum: ['yes', 'no', 'not_stated'] },
    n_participants: { type: ['integer', 'null'] },
    outcome_on_output: { type: 'string', enum: ['yes', 'no', 'unclear'] },
    abstract_found: { type: 'boolean' },
    note: { type: 'string' },
  },
  required: ['cid', 'verdict', 'randomized', 'outcome_on_output', 'abstract_found', 'note'],
}
const SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    items: { type: 'array', items: ITEM },
  },
  required: ['file', 'items'],
}

const prompt = (batch, s) => [
  'You are one of two independent screeners who classify literature-search candidates from their abstracts. The other screener classifies the same batch without seeing your work. This is the triage step of a literature screening for the AI and Human Skill Atlas (aiskillatlas.org), which is adding a section on generative AI and creativity, ideation, and homogenization of ideas. Read ' + CODEBOOK + ' sections 1 and 3 first (scope, the three questions, and eligibility).',
  '',
  'Your batch: ' + batch.join(', ') + '. The candidate records are in ' + ROOT + '/candidates.json (a JSON list; load it with python and select the objects whose "cid" is in your batch). Each record has the title, authors, DOI or arXiv id, URL, and notes from the search agents ("evidence", "design_guesses"). Treat those notes as leads; they are unverified.',
  '',
  'For each candidate:',
  '1. Get the abstract from a primary record. Options, through Python urllib run in PowerShell (send no email address or personal identifier in headers; User-Agent "atlas-screening/0.1" is fine): the arXiv API (http://export.arxiv.org/api/query?id_list=<id>); the OpenAlex API (https://api.openalex.org/works/doi:<doi> returns "abstract_inverted_index", which you rebuild into text); the Crossref API (https://api.crossref.org/works/<doi>, sometimes with "abstract"); Semantic Scholar (https://api.semanticscholar.org/graph/v1/paper/DOI:<doi>?fields=title,abstract); Europe PMC (https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"<doi>"&format=json&resultType=core); or the landing page through WebFetch (load it with ToolSearch, query "select:WebSearch,WebFetch", if it is not available). If no abstract can be reached after trying at least three routes, classify from the title and the search notes and set "abstract_found" to false.',
  '2. Classify the candidate:',
  '   - "experiment": human participants work on a creative, ideation, design, or writing task under conditions that differ in generative-AI assistance (AI versus no AI, AI versus another aid, or one AI configuration versus another), and the creativity, quality, or diversity of what they produce is scored, or may be (the abstract is not clear). Quasi-experiments, classroom studies, within-person designs, and small studies all count here.',
  '   - "context_ai_vs_human": AI-generated output is compared with human-generated output, and no participant receives AI help.',
  '   - "context_observational": real-world output (papers, proposals, art, marketing, news, essays, posts, platform contributions) is analyzed for diversity, similarity, novelty, or originality in relation to generative AI.',
  '   - "context_synthesis": a systematic review or meta-analysis on generative AI and creativity, co-creativity, or idea diversity.',
  '   - "out": none of the above. Set "out_reason" to one of: "no_data" (opinion, theory, commentary), "model_only" (no human data), "no_creativity_or_diversity_outcome", "self_report_only" (the only outcomes are self-reported or attitudes), "perception_of_ai_work" (how people judge or value AI-made work), "not_generative_ai", "narrative_review", "system_paper_no_comparison" (a tool description whose user study has no comparison condition), "not_found" (the work could not be located at all), "other".',
  '   If a paper combines kinds (for example a natural experiment plus a controlled experiment), choose "experiment". When in doubt between "experiment" and anything else, choose "experiment": the next stage reads the full text.',
  '3. Record what the abstract says: "randomized" ("yes" if it states random assignment of people to conditions, "no" if it states a non-random design, otherwise "not_stated"); "n_participants" (the number of human participants as an integer, or null if the abstract does not state it; people only, never ideas, essays, or ratings; for several experiments give the largest single experiment); "outcome_on_output" ("yes" if a creativity, quality, or diversity outcome is scored on what participants produced, "no" if outcomes are only self-reports or perceptions, "unclear" otherwise).',
  '4. "note": one sentence on what the study does, plus anything that the next stage should know (for example "abstract not reachable", "same study as the SSRN version", "reanalysis of another paper\'s data").',
  '',
  'Output: write a JSON object to ' + ROOT + '/triage/batch-' + batch[0] + '.' + s + '.json with the Write tool: {"first_cid": "' + batch[0] + '", "screener": "' + s + '", "items": [...]} with one item per candidate in your batch, each with "cid", "verdict", "out_reason" (null unless the verdict is "out"), "randomized", "n_participants", "outcome_on_output", "abstract_found", and "note". Confirm with python that the file parses and has ' + batch.length + ' items. Do not open any other file under ' + ROOT + '/triage. Create no other files. Your structured reply repeats the items.',
].join('\n')

phase('Triage')
const out = await parallel(batches.flatMap(b => ['A', 'B'].map(s => () =>
  agent(prompt(b, s), { model: MODEL, label: 'triage ' + s + ':' + b[0], phase: 'Triage', schema: SCHEMA, effort: 'medium' })
    .then(r => ({ first: b[0], s, r }))
)))

const by = {}
for (const x of out.filter(Boolean)) {
  for (const item of ((x.r && x.r.items) || [])) {
    by[item.cid] = by[item.cid] || {}
    by[item.cid][x.s] = item.verdict
  }
}
const counts = { both_experiment: 0, one_experiment: 0, both_out: 0, context: 0, incomplete: 0, disagree: 0 }
for (const cid of CIDS) {
  const v = by[cid] || {}
  if (!v.A || !v.B) { counts.incomplete++; continue }
  if (v.A !== v.B) counts.disagree++
  if (v.A === 'experiment' && v.B === 'experiment') counts.both_experiment++
  else if (v.A === 'experiment' || v.B === 'experiment') counts.one_experiment++
  else if (v.A === 'out' && v.B === 'out') counts.both_out++
  else counts.context++
}
const failedBatches = out.map((x, i) => x && x.r ? null : i).filter(i => i !== null)
log('Triage done: ' + JSON.stringify(counts))
return { n: CIDS.length, batches: batches.length, counts, failed_agent_slots: failedBatches }
