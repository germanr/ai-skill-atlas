"""Write to-download.html: papers whose full text could not be fetched by script, with links.

Publishers block scripted requests, including for open-access articles. A person's browser
gets them. The page lists experiments first. Saved PDFs go to the _inbox folder under any
file name; ingest_inbox.py matches them to candidates by the title on the first page.
"""
import html
import io
import json
import re

import retrieve as R

INBOX = R.LIB / "_inbox"
INBOX.mkdir(exist_ok=True)
cands = {c["cid"]: c for c in json.load(io.open(R.ROOT / "candidates.json", encoding="utf-8"))}
dec = {d["cid"]: d for d in json.load(io.open(R.ROOT / "triage" / "decisions.json", encoding="utf-8"))}
log = json.load(io.open(R.ROOT / "retrieval.json", encoding="utf-8"))

ORDER = [("experiment_full", "Experiments (full two-screener pipeline once the PDF is on file)"),
         ("experiment_small", "Experiments that report fewer than 50 participants"),
         ("context", "Context papers (AI versus human output, observational, syntheses)")]
rows = {key: [] for key, _ in ORDER}
for cid, d in dec.items():
    if d["path"] not in rows or d["in_library"]:
        continue
    entry = log.get(cid)
    if not entry or entry.get("status") == "ok":
        continue
    c = cands[cid]
    hint = entry.get("suggestion_for_owner") or ""
    urls = re.findall(r"https?://[^\s)\"']+", hint)
    urls = [u.rstrip(".,;") for u in urls]
    doi_url = f"https://doi.org/{c['doi']}" if c.get("doi") else (c.get("url") or "")
    if doi_url and doi_url not in urls:
        urls.append(doi_url)
    open_access = bool(re.search(r"open access|no subscription|free", hint, flags=re.I))
    rows[d["path"]].append((c["authors"], c["year"], c["title"], c.get("venue") or "", urls, open_access, cid))

parts = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Creativity screening: papers to download</title>",
         "<style>body{font:15px/1.45 system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#222}"
         "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}li{margin:.55rem 0}small{color:#666}"
         ".oa{color:#1a6b2f;font-weight:600}a{word-break:break-all}</style></head><body>",
         "<h1>Creativity screening: papers to download</h1>",
         "<p>These papers could not be fetched by script because the publishers block automated requests. "
         "Open each link in your browser and save the PDF, under any file name, to<br>"
         f"<code>{html.escape(str(INBOX))}</code><br>"
         "The screening then matches each file to its paper by the title on the first page.</p>"]
total = 0
for key, heading in ORDER:
    items = sorted(rows[key], key=lambda r: (not r[5], (r[0] or "").lower()))
    if not items:
        continue
    parts.append(f"<h2>{html.escape(heading)}: {len(items)}</h2><ol>")
    for authors, year, title, venue, urls, oa, cid in items:
        total += 1
        links = " &middot; ".join(f"<a href='{html.escape(u)}' target='_blank' rel='noopener'>{html.escape(u)}</a>" for u in urls[:3])
        tag = "<span class='oa'>open access</span> " if oa else ""
        parts.append(f"<li>{tag}<b>{html.escape(str(authors))} ({year})</b>. {html.escape(title)}. "
                     f"<small>{html.escape(venue)} [{cid}]</small><br>{links}</li>")
    parts.append("</ol>")
parts.append("</body></html>")
out = R.ROOT / "to-download.html"
io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(parts) + "\n")
print(total, "papers listed ->", out)
print({k: len(v) for k, v in rows.items()}, "open access flagged:", sum(r[5] for v in rows.values() for r in v))
