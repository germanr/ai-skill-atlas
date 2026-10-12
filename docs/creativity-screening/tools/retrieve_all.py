"""Download open full texts for screening candidates, in parallel, and convert them to markdown.

Usage: python retrieve_all.py <cids.txt>

Routes tried per candidate, in order: arXiv id, OSF, publisher PDF patterns (Springer, Nature,
Frontiers, PLOS, MDPI), OpenAlex open-access locations, Semantic Scholar, Europe PMC, the
citation_pdf_url meta tag on the DOI landing page, and an arXiv title search. A download is
kept only if it is a PDF whose first two pages contain at least 70 percent of the title's words.
Never overwrites a file. Updates retrieval.json. No personal identifier is sent.
"""
import io
import os
import json
import re
import sys
import time
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import retrieve as R

TIMEOUT = 25
CONVERT_LOCK = threading.Lock()


def fetch(url, api=False):
    return R.fetch(url, R.UA_API if api else R.UA_WEB, timeout=TIMEOUT)


def get_json(url):
    try:
        data, _, _ = R.fetch(url, R.UA_API, timeout=TIMEOUT)
        return json.loads(data.decode("utf-8", "replace"))
    except Exception:
        return None


def routes(cand):
    """Yield (source, url) lazily so that slow lookups run only when earlier routes fail."""
    arxivs = [a for a in ([cand.get("arxiv_id")] + list(cand.get("all_arxiv_ids") or [])) if a]
    dois = [d for d in ([cand.get("doi")] + list(cand.get("all_dois") or [])) if d]
    for other in cand.get("other_versions") or []:
        for kind, ident in R_ids(other):
            (arxivs if kind == "arxiv" else dois).append(ident)
    arxivs, dois = list(dict.fromkeys(arxivs)), list(dict.fromkeys(dois))
    for a in arxivs:
        yield "arxiv", f"https://arxiv.org/pdf/{a}"
    for doi in dois:
        m = re.match(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi)
        if m:
            yield "arxiv", f"https://arxiv.org/pdf/{m.group(1)}"
        m = re.match(r"10\.(31234|31219|31235|35542|17605)/osf\.io/([a-z0-9]+)", doi)
        if m:
            yield "osf", f"https://osf.io/{m.group(2)}/download"
            yield "osf", f"https://osf.io/download/{m.group(2)}/"
        m = re.match(r"10\.3386/(w\d+)", doi)
        if m:
            yield "nber", f"https://www.nber.org/system/files/working_papers/{m.group(1)}/{m.group(1)}.pdf"
    for doi in dois:
        suffix = doi.split("/", 1)[1]
        if doi.startswith(("10.1007/", "10.1186/", "10.1140/")):
            yield "springer", f"https://link.springer.com/content/pdf/{doi}.pdf"
        if doi.startswith(("10.1038/", "10.1057/s41599")):
            yield "nature", f"https://www.nature.com/articles/{suffix}.pdf"
        if doi.startswith("10.3389/"):
            yield "frontiers", f"https://www.frontiersin.org/articles/{doi}/pdf"
        if doi.startswith("10.1371/journal."):
            journal = {"pone": "plosone"}.get(suffix.split(".")[1], "plosone")
            yield "plos", f"https://journals.plos.org/{journal}/article/file?id={doi}&type=printable"
    for doi in dois:
        oa = get_json(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}?select=id,open_access,best_oa_location,locations")
        if oa:
            for loc in [oa.get("best_oa_location") or {}] + list(oa.get("locations") or []):
                if loc and loc.get("pdf_url"):
                    yield "openalex", loc["pdf_url"]
            if (oa.get("open_access") or {}).get("oa_url"):
                yield "openalex_oa", oa["open_access"]["oa_url"]
        s2 = get_json(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=openAccessPdf,externalIds")
        if s2:
            if (s2.get("openAccessPdf") or {}).get("url"):
                yield "semanticscholar", s2["openAccessPdf"]["url"]
            if (s2.get("externalIds") or {}).get("ArXiv"):
                yield "arxiv", f"https://arxiv.org/pdf/{s2['externalIds']['ArXiv']}"
        q = urllib.parse.quote(f'DOI:"{doi}"')
        res = get_json(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&format=json&resultType=lite")
        for hit in ((res or {}).get("resultList") or {}).get("result", []):
            if hit.get("pmcid"):
                yield "europepmc", f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={hit['pmcid']}&blobtype=pdf"
    for doi in dois:
        try:
            data, final_url, _ = R.fetch(f"https://doi.org/{doi}", R.UA_WEB, timeout=TIMEOUT, limit=3_000_000)
        except Exception:
            continue
        if data.startswith(b"%PDF"):
            yield "doi", f"https://doi.org/{doi}"
            continue
        html = data.decode("utf-8", "replace")
        if "mdpi.com" in final_url:
            yield "mdpi", final_url.rstrip("/") + "/pdf"
        for pat in (r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']'):
            for m in re.finditer(pat, html, flags=re.I):
                yield "citation_pdf_url", m.group(1).replace("&amp;", "&")
    if cand.get("url") and str(cand["url"]).lower().split("?")[0].endswith(".pdf"):
        yield "url", cand["url"]
    words = R.title_words(cand.get("title") or "")[:9]
    if len(words) >= 4:
        q = "+AND+".join(f"ti:{urllib.parse.quote(w)}" for w in words)
        try:
            data, _, _ = R.fetch(f"http://export.arxiv.org/api/query?search_query={q}&max_results=3", R.UA_API, timeout=TIMEOUT)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in ET.fromstring(data).findall("a:entry", ns):
                ident = re.sub(r"v\d+$", "", entry.find("a:id", ns).text.rsplit("/", 1)[-1])
                yield "arxiv_title", f"https://arxiv.org/pdf/{ident}"
        except Exception:
            pass


def R_ids(text):
    text = text if isinstance(text, str) else json.dumps(text)
    for m in re.finditer(r"10\.\d{4,9}/[^\s,;\"')\]]+", text, flags=re.I):
        yield "doi", m.group(0).rstrip(".").lower()
    for m in re.finditer(r"arxiv[:\s]*?(\d{4}\.\d{4,5})", text, flags=re.I):
        yield "arxiv", m.group(1)


def one(cand):
    stem = R.file_stem(cand)
    pdf_path, md_path = R.LIB / f"{stem}.pdf", R.LIB / f"{stem}.md"
    entry = {"status": "not_obtained", "title": cand["title"], "tried": []}
    if pdf_path.exists() and md_path.exists():
        entry.update(status="ok", source="already_on_disk", pdf_path=str(pdf_path).replace("\\", "/"),
                     md_path=str(md_path).replace("\\", "/"))
        return cand["cid"], entry
    seen = set()
    for src, url in routes(cand):
        if url in seen:
            continue
        seen.add(url)
        try:
            data, final_url, ctype = fetch(url, api=src.startswith("arxiv"))
        except Exception as exc:
            entry["tried"].append({"source": src, "url": url, "result": f"error {type(exc).__name__}: {str(exc)[:80]}"})
            continue
        if not data.startswith(b"%PDF"):
            entry["tried"].append({"source": src, "url": url, "result": f"not a PDF ({ctype[:40]})"})
            continue
        ok, pages, share = R.looks_right(data, cand["title"])
        if not ok:
            entry["tried"].append({"source": src, "url": url, "result": f"PDF with title-word share {share}, {pages} pages; rejected"})
            continue
        with CONVERT_LOCK:
            if not pdf_path.exists():
                with io.open(pdf_path, "wb") as fh:
                    fh.write(data)
            chars = R.convert(pdf_path, md_path) if not md_path.exists() else md_path.stat().st_size
        entry.update(status="ok", source=src, source_url=final_url, pages=pages, title_word_share=share,
                     md_chars=chars, pdf_path=str(pdf_path).replace("\\", "/"), md_path=str(md_path).replace("\\", "/"))
        break
    return cand["cid"], entry


def save(updates):
    log_path = R.ROOT / "retrieval.json"
    log = json.load(io.open(log_path, encoding="utf-8")) if log_path.exists() else {}
    for cid, entry in updates.items():
        if log.get(cid, {}).get("status") == "ok":
            continue
        log[cid] = entry
    # Write to a temporary file and swap it in, so readers never see a partial file.
    tmp_path = log_path.with_suffix(".json.tmp")
    with io.open(tmp_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for attempt in range(120):
        try:
            os.replace(tmp_path, log_path)
            break
        except PermissionError:  # Dropbox or a reader holds the file for a moment
            time.sleep(0.5)
    else:  # still locked after a minute: write directly rather than lose the updates
        with io.open(log_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(log, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        tmp_path.unlink(missing_ok=True)


def main():
    cids = [ln.strip() for ln in io.open(sys.argv[1], encoding="utf-8") if ln.strip()]
    cands = {c["cid"]: c for c in json.load(io.open(R.ROOT / "candidates.json", encoding="utf-8"))}
    log_path = R.ROOT / "retrieval.json"
    log = json.load(io.open(log_path, encoding="utf-8")) if log_path.exists() else {}
    todo = [cands[c] for c in cids if log.get(c, {}).get("status") != "ok" and not cands[c].get("library")]
    updates, ok = {}, 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(one, cand) for cand in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            cid, entry = fut.result()
            updates[cid] = entry
            ok += entry["status"] == "ok"
            print(cid, entry["status"], entry.get("source", ""), "|", (entry["title"] or "")[:60], flush=True)
            if i % 10 == 0:
                save(updates)
    save(updates)
    print(f"obtained {ok} of {len(todo)} (skipped {len(cids) - len(todo)} already on file)", flush=True)


if __name__ == "__main__":
    main()
