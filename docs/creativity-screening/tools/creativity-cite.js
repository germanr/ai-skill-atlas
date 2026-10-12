export const meta = {
  name: 'creativity-cite',
  description: 'Citation checks only: the bibliographic record of each listed paper is confirmed against Crossref, OpenAlex, arXiv, OSF, or the publisher page',
  phases: [
    { title: 'Citation', detail: 'one checker per paper; nothing is guessed' },
  ],
}

// Same prompt and schema as the citation stage of creativity-fulltext-v2.js and creativity-light.js,
// for papers whose screening form exists but whose citation file is missing.

const ROOT = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening'
const MODEL = 'claude-opus-5-5'  // Germán, 2026-10-08: subagents run on Opus 5.5 to save capacity
const CIDS = args.cids

const INTRO = 'This is part of a literature screening for the AI and Human Skill Atlas (aiskillatlas.org), a living meta-analysis that is adding a section on generative AI and creativity, ideation, and homogenization of ideas. A later audit checks every recorded field against its source, so accuracy matters more than speed.'

const citePrompt = cid => [
  'You are the citation checker for one paper. ' + INTRO,
  'The owner\'s rule is strict: never fabricate or guess any reference field. Confirm the bibliographic record of paper ' + cid + ' against primary sources.',
  '',
  'Inputs: the object with "cid": "' + cid + '" in ' + ROOT + '/candidates.json (title, authors, year, venue, DOI, arXiv id, URL, other versions: all unverified), and, if a file is on record, the first pages of the PDF at "pdf_path" under key "' + cid + '" in ' + ROOT + '/retrieval.json (Read tool, "pages": "1-2").',
  '',
  'Check against the Crossref API (https://api.crossref.org/works/<doi> or ?query.bibliographic=...), the OpenAlex API (https://api.openalex.org/works/doi:<doi>), the arXiv API (http://export.arxiv.org/api/query?id_list=<id>), the OSF API, or the publisher page: the exact title; the full author list in order; the year; the venue with volume, issue, and pages or article number; the DOI; and every version of the work (preprint ids with dates, journal publication date). Establish which version the PDF on disk is, if there is one, and whether a later version exists. Use Python urllib through PowerShell for the APIs; send no email address or personal identifier in headers. WebSearch and WebFetch may need loading with ToolSearch (query "select:WebSearch,WebFetch"). Many publisher sites return HTTP 403 to scripts; the APIs usually suffice. If an API answers HTTP 429, wait a few seconds and try once more, then use another source.',
  '',
  'Write a JSON object to ' + ROOT + '/forms/citations/' + cid + '.json with "cid", "pdf_version" (what the PDF on disk is, or null if none), "latest_version" (an object with "title", "authors" (list of full names in order), "authors_family" (the family names in the same order, as Crossref or the publisher gives them, for example "Van de Cruys", "de Rooij", "Dell\'Acqua"), "year", "venue", "volume_issue_pages", "doi", "url", "status" (journal, proceedings, working_paper, or preprint), "date"), "other_versions" (a list of objects with "what", "id_or_doi", "date", "title_if_different"), "pdf_is_latest" (true, false, or null), "corrections_to_candidate_record" (a list of strings; empty if the record was right), "checked_against" (which sources you used), and "unverified_fields" (fields you could not confirm). Write null for anything you could not confirm. Confirm with python that the file parses. Create no other files.',
  '',
  'Your structured reply: "citation" is one line in the form Authors (Year), "Title", Venue; "corrections" repeats corrections_to_candidate_record.',
].join('\n')

const CITE_SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    file: { type: 'string' },
    citation: { type: 'string' },
    corrections: { type: 'array', items: { type: 'string' } },
    unverified_fields: { type: 'array', items: { type: 'string' } },
  },
  required: ['cid', 'citation'],
}

phase('Citation')
const results = await pipeline(
  CIDS,
  async cid => {
    const r = await agent(citePrompt(cid), { model: MODEL, label: 'cite:' + cid, phase: 'Citation', schema: CITE_SCHEMA, effort: 'medium' })
      || await agent(citePrompt(cid), { model: MODEL, label: 'cite retry:' + cid, phase: 'Citation', schema: CITE_SCHEMA, effort: 'medium' })
    return r ? { cid, citation: r.citation, corrections: r.corrections || [], unverified: r.unverified_fields || [] } : null
  }
)

const done = results.filter(Boolean)
log('Citations checked: ' + done.length + ' of ' + CIDS.length)
return {
  papers: done,
  failed: CIDS.filter(c => !done.some(d => d.cid === c)),
  with_corrections: done.filter(d => d.corrections.length).map(d => d.cid),
}
