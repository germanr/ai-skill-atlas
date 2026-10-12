export const meta = {
  name: 'creativity-retrieve',
  description: 'Find and save an open full text (preprint, working paper, or open-access copy) for papers a download script could not obtain',
  phases: [
    { title: 'Retrieve', detail: 'one agent per paper looks for a legitimate open copy' },
  ],
}

const ROOT = 'C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening'
const MODEL = 'claude-opus-5-5'  // Germán, 2026-10-08: subagents run on Opus 5.5 to save capacity
const LIB = 'C:/Dropbox/Research/ai-lab/literature/creativity'
const ITEMS = args.items

const SCHEMA = {
  type: 'object',
  properties: {
    cid: { type: 'string' },
    status: { type: 'string', enum: ['ok', 'not_obtained'] },
    version_saved: { type: ['string', 'null'] },
    is_latest_version: { type: ['boolean', 'null'] },
    suggestion_for_owner: { type: 'string' },
  },
  required: ['cid', 'status'],
}

const prompt = item => [
  'You are a retrieval agent for one paper in a literature screening for the AI and Human Skill Atlas (aiskillatlas.org), which is adding a section on generative AI and creativity. A download script could not obtain this paper\'s full text. Find an open, legitimate copy and save it for the screeners.',
  '',
  'Paper: ' + item.cid + '. Its record is the object with "cid": "' + item.cid + '" in ' + ROOT + '/candidates.json (title, authors, year, venue, DOI, other versions). The script\'s failed attempts are under key "' + item.cid + '" in ' + ROOT + '/retrieval.json ("tried").',
  '',
  'Where to look, in this order:',
  '1. The publisher\'s own PDF when the article is open access. Try a plain request with a browser-like User-Agent through Python urllib. Known patterns: https://www.nature.com/articles/<suffix>.pdf ; https://link.springer.com/content/pdf/<doi>.pdf ; https://www.frontiersin.org/articles/<doi>/pdf ; MDPI article URL + "/pdf" ; https://journals.plos.org/plosone/article/file?id=<doi>&type=printable ; PubMed Central or Europe PMC (https://europepmc.org/backend/ptpmcrender.fcgi?accid=PMC<id>&blobtype=pdf).',
  '2. A preprint or working-paper version by the same authors: arXiv (API search by title or author: http://export.arxiv.org/api/query?search_query=ti:"..."), OSF and PsyArXiv, SSRN, NBER (https://www.nber.org/system/files/working_papers/w<no>/w<no>.pdf), IZA (https://docs.iza.org/dp<no>.pdf), CESifo, EdWorkingPapers, RePEc/IDEAS, HAL, Zenodo, university repositories, and the authors\' own pages. WebSearch with the exact title in quotes plus "pdf" finds most of these (load WebSearch and WebFetch with ToolSearch, query "select:WebSearch,WebFetch", if needed).',
  '',
  'Hard limits. Do not use Sci-Hub, LibGen, Anna\'s Archive, or any other pirate source. Do not use credentials, proxies, or any trick to get past a paywall, a login, a CAPTCHA, or a bot check: if a site answers 403 or shows a bot check, move on to another source. Send no email address or personal identifier in request headers.',
  '',
  'When you find a PDF:',
  '- Download it with Python (urllib, browser-like User-Agent) to "' + LIB + '/' + item.stem + '.pdf". Do not overwrite an existing file.',
  '- Check that it is the right paper: open page 1 with the Read tool ("pages": "1") and compare title and authors with the record. A different paper by the same authors does not count.',
  '- Convert it to markdown and save it beside the PDF with the same name and the extension .md: python -c "import pymupdf4llm, io; md = pymupdf4llm.to_markdown(r\'<pdf path>\'); io.open(r\'<md path>\', \'w\', encoding=\'utf-8\', newline=\'\\n\').write(md)".',
  '- Establish which version you saved (journal version of record, arXiv v2 of a given date, working paper number and date) and how it differs from the latest version in the record: a different title, a different sample size in the abstract, added or removed studies.',
  '',
  'Then write a JSON object to ' + ROOT + '/retrieval-agents/' + item.cid + '.json with the Write tool: {"cid": "' + item.cid + '", "status": "ok" or "not_obtained", "pdf_path": "...", "md_path": "...", "source": "agent", "source_url": "...", "version_saved": "...", "is_latest_version": true or false or null, "differences_from_latest": "...", "pages": <integer>, "tried": [{"source": "...", "url": "...", "result": "..."}], "suggestion_for_owner": "where the latest version can be downloaded with a subscription, as a URL"}. Use forward slashes in paths and null for fields that do not apply. Confirm with python that the file parses. Create no files other than the PDF, the markdown, and this JSON.',
  '',
  'Your structured reply repeats "cid", "status", "version_saved", "is_latest_version", and "suggestion_for_owner".',
].join('\n')

phase('Retrieve')
const out = (await parallel(ITEMS.map(item => () =>
  agent(prompt(item), { model: MODEL, label: 'retrieve:' + item.cid, phase: 'Retrieve', schema: SCHEMA, effort: 'medium' })
))).filter(Boolean)

const ok = out.filter(x => x.status === 'ok')
log('Retrieved ' + ok.length + ' of ' + ITEMS.length)
return {
  ok: ok.map(x => ({ cid: x.cid, version: x.version_saved, latest: x.is_latest_version })),
  not_obtained: out.filter(x => x.status !== 'ok').map(x => ({ cid: x.cid, where: x.suggestion_for_owner })),
  failed_agents: ITEMS.map(i => i.cid).filter(c => !out.some(x => x.cid === c)),
}
