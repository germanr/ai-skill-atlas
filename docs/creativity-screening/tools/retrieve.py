"""Download open full texts for screening candidates and convert them to markdown.

Usage: python retrieve.py <cids.txt>   (one cid per line; reads candidates.json)

For each candidate with no library copy, tries in order: arXiv, OSF/PsyArXiv, Europe PMC,
OpenAlex open-access locations, Semantic Scholar, and the DOI landing page. A download is
kept only if it is a PDF whose first two pages contain most of the title's words.
Never overwrites a file. Writes retrieval.json (one entry per cid) next to candidates.json.
No email address or personal identifier is sent.
"""
import io
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
LIB = Path("C:/Dropbox/Research/ai-lab/literature/creativity")
UA_API = {"User-Agent": "atlas-screening/0.1"}
UA_WEB = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0 Safari/537.36", "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8"}
STOP = {"the", "a", "an", "of", "and", "in", "on", "for", "to", "with", "is", "are", "by", "from", "at", "as", "or"}


def fetch(url, headers, timeout=60, limit=60_000_000):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(limit), resp.geturl(), resp.headers.get("Content-Type", "")


def get_json(url):
    try:
        data, _, _ = fetch(url, UA_API, timeout=40)
        return json.loads(data.decode("utf-8", "replace"))
    except Exception:
        return None


def fold(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def title_words(title):
    words = re.findall(r"[a-z0-9]+", fold(title).lower())
    return [w for w in words if w not in STOP and len(w) > 2]


def file_stem(cand):
    authors = fold(cand.get("authors") or "Unknown")
    etal = bool(re.search(r"et al", authors, flags=re.I))
    names = [re.sub(r"[^A-Za-z' -]", "", a).strip() for a in re.split(r",|;| and | & ", re.sub(r"et al\.?", "", authors, flags=re.I))]
    names = [n.split()[-1] if " " in n and len(n.split()) <= 3 and n.split()[0][0].isupper() and len(n.split()[0]) <= 2 else n for n in names if n]
    if etal or len(names) >= 5:
        who = f"{names[0]} et al" if names else "Unknown"
    elif len(names) == 1:
        who = names[0]
    elif len(names) == 2:
        who = f"{names[0]} and {names[1]}"
    else:
        who = " ".join(names)
    title = fold(cand.get("title") or "untitled")
    short = re.split(r"[:?]", title)[0].strip() or title
    short = re.sub(r"[\\/*\"<>|]", " ", short)
    short = re.sub(r"[^A-Za-z0-9 ,'&()-]", "", short)
    short = re.sub(r"\s+", " ", short).strip()[:80].rstrip(" ,-")
    year = cand.get("year") or "nd"
    return f"{who} ({year}) - {short}"


def pdf_candidates(cand):
    urls = []
    arx = cand.get("arxiv_id") or next(iter(cand.get("all_arxiv_ids") or []), None)
    if arx:
        urls.append(("arxiv", f"https://arxiv.org/pdf/{arx}"))
    dois = [d for d in ([cand.get("doi")] + list(cand.get("all_dois") or [])) if d]
    seen = set()
    dois = [d for d in dois if not (d in seen or seen.add(d))]
    for doi in dois:
        m = re.match(r"10\.(31234|31219|31235|35542|17605)/osf\.io/([a-z0-9]+)", doi)
        if m:
            guid = m.group(2)
            urls.append(("osf", f"https://osf.io/{guid}/download"))
            urls.append(("osf", f"https://osf.io/download/{guid}/"))
        m = re.match(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi)
        if m:
            urls.append(("arxiv", f"https://arxiv.org/pdf/{m.group(1)}"))
    for doi in dois:
        q = urllib.parse.quote(f'DOI:"{doi}"')
        res = get_json(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&resultType=lite")
        for hit in ((res or {}).get("resultList") or {}).get("result", []):
            if hit.get("pmcid"):
                urls.append(("europepmc", f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={hit['pmcid']}&blobtype=pdf"))
        oa = get_json(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}?select=id,open_access,best_oa_location,locations")
        if oa:
            locs = [oa.get("best_oa_location") or {}] + list(oa.get("locations") or [])
            for loc in locs:
                if loc and loc.get("pdf_url"):
                    urls.append(("openalex", loc["pdf_url"]))
            if (oa.get("open_access") or {}).get("oa_url"):
                urls.append(("openalex_oa", oa["open_access"]["oa_url"]))
        s2 = get_json(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=openAccessPdf,externalIds")
        if s2:
            if (s2.get("openAccessPdf") or {}).get("url"):
                urls.append(("semanticscholar", s2["openAccessPdf"]["url"]))
            ax = (s2.get("externalIds") or {}).get("ArXiv")
            if ax:
                urls.append(("arxiv", f"https://arxiv.org/pdf/{ax}"))
        # Publishers with predictable open-access PDF links.
        if doi.startswith("10.1038/"):
            urls.append(("nature", f"https://www.nature.com/articles/{doi.split('/', 1)[1]}.pdf"))
        if doi.startswith("10.3390/") or doi.startswith("10.3389/") or doi.startswith("10.1371/"):
            urls.append(("doi", f"https://doi.org/{doi}"))
        if doi.startswith("10.1093/pnasnexus/"):
            urls.append(("doi", f"https://doi.org/{doi}"))
    if cand.get("url") and str(cand["url"]).lower().endswith(".pdf"):
        urls.append(("url", cand["url"]))
    out, seen = [], set()
    for src, u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append((src, u))
    return out


def looks_right(pdf_bytes, title):
    import pymupdf
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return False, 0, 0.0
    text = " ".join(doc[i].get_text() for i in range(min(2, doc.page_count)))
    have = set(re.findall(r"[a-z0-9]+", fold(text).lower()))
    words = title_words(title)
    share = sum(w in have for w in words) / max(1, len(words))
    return share >= 0.7, doc.page_count, round(share, 2)


def convert(pdf_path, md_path):
    import pymupdf4llm
    md = pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)
    with io.open(md_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md)
    return len(md)


def main():
    cids = [ln.strip() for ln in io.open(sys.argv[1], encoding="utf-8") if ln.strip()]
    cands = {c["cid"]: c for c in json.load(io.open(ROOT / "candidates.json", encoding="utf-8"))}
    log_path = ROOT / "retrieval.json"
    log = json.load(io.open(log_path, encoding="utf-8")) if log_path.exists() else {}
    for cid in cids:
        cand = cands[cid]
        if log.get(cid, {}).get("status") == "ok":
            continue
        if cand.get("library"):
            log[cid] = {"status": "ok", "source": "library", "pdf_path": cand["library"]["pdf_path"],
                        "md_path": cand["library"]["md_path"], "title": cand["title"]}
            continue
        stem = file_stem(cand)
        pdf_path, md_path = LIB / f"{stem}.pdf", LIB / f"{stem}.md"
        entry = {"status": "not_obtained", "title": cand["title"], "tried": []}
        if pdf_path.exists() and md_path.exists():
            entry.update(status="ok", source="already_on_disk", pdf_path=str(pdf_path).replace("\\", "/"),
                         md_path=str(md_path).replace("\\", "/"))
            log[cid] = entry
            continue
        for src, url in pdf_candidates(cand):
            try:
                data, final_url, ctype = fetch(url, UA_WEB if src not in ("arxiv",) else UA_API)
            except Exception as exc:
                entry["tried"].append({"source": src, "url": url, "result": f"error {type(exc).__name__}: {str(exc)[:80]}"})
                continue
            if not data.startswith(b"%PDF"):
                entry["tried"].append({"source": src, "url": url, "result": f"not a PDF ({ctype[:40]})"})
                continue
            ok, pages, share = looks_right(data, cand["title"])
            if not ok:
                entry["tried"].append({"source": src, "url": url, "result": f"PDF with title-word share {share}, {pages} pages; rejected"})
                continue
            with io.open(pdf_path, "wb") as fh:
                fh.write(data)
            chars = convert(pdf_path, md_path)
            entry.update(status="ok", source=src, source_url=final_url, pages=pages, title_word_share=share,
                         md_chars=chars, pdf_path=str(pdf_path).replace("\\", "/"), md_path=str(md_path).replace("\\", "/"))
            break
        log[cid] = entry
        print(cid, entry["status"], entry.get("source", ""), "|", stem[:70])
        with io.open(log_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(log, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        time.sleep(1.0)
    with io.open(log_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    done = [c for c in cids if log.get(c, {}).get("status") == "ok"]
    print(f"obtained {len(done)} of {len(cids)}")


if __name__ == "__main__":
    main()
