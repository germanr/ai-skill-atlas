"""Second retrieval pass for candidates the first pass did not obtain.

Usage: python retrieve2.py <cids.txt>

Extra routes: publisher PDF patterns (Springer, Nature, MDPI, Frontiers, PLOS, PNAS Nexus),
the citation_pdf_url meta tag on the DOI landing page, and an arXiv title search.
Same acceptance test as the first pass: a real PDF whose first two pages contain most of
the title's words. Never overwrites a file. No personal identifier is sent.
"""
import io
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

import retrieve as R


def landing(doi):
    """Final URL and HTML of the DOI landing page, or (None, '')."""
    try:
        data, final_url, ctype = R.fetch(f"https://doi.org/{doi}", R.UA_WEB, timeout=40, limit=3_000_000)
    except Exception:
        return None, ""
    if data.startswith(b"%PDF"):
        return final_url, ""
    return final_url, data.decode("utf-8", "replace")


def extra_candidates(cand):
    urls = []
    dois = [d for d in ([cand.get("doi")] + list(cand.get("all_dois") or [])) if d]
    for doi in dict.fromkeys(dois):
        suffix = doi.split("/", 1)[1]
        if doi.startswith(("10.1007/", "10.1186/", "10.1140/")):
            urls.append(("springer", f"https://link.springer.com/content/pdf/{doi}.pdf"))
        if doi.startswith(("10.1038/", "10.1057/s41599")):
            urls.append(("nature", f"https://www.nature.com/articles/{suffix}.pdf"))
        if doi.startswith("10.3389/"):
            urls.append(("frontiers", f"https://www.frontiersin.org/articles/{doi}/pdf"))
        if doi.startswith("10.1371/journal.pone"):
            urls.append(("plos", f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable"))
        if doi.startswith("10.1093/pnasnexus/"):
            urls.append(("oup", f"https://academic.oup.com/pnasnexus/article-pdf/doi/{doi}"))
        final_url, html = landing(doi)
        if final_url and "mdpi.com" in final_url:
            urls.append(("mdpi", final_url.rstrip("/") + "/pdf"))
        for m in re.finditer(r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I):
            urls.append(("citation_pdf_url", m.group(1).replace("&amp;", "&")))
        for m in re.finditer(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']', html, flags=re.I):
            urls.append(("citation_pdf_url", m.group(1).replace("&amp;", "&")))
    # arXiv title search: finds preprints of proceedings and journal papers.
    words = R.title_words(cand.get("title") or "")[:9]
    if len(words) >= 4:
        q = "+AND+".join(f"ti:{urllib.parse.quote(w)}" for w in words)
        try:
            data, _, _ = R.fetch(f"http://export.arxiv.org/api/query?search_query={q}&max_results=3", R.UA_API, timeout=40)
            root = ET.fromstring(data)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("a:entry", ns):
                ident = entry.find("a:id", ns).text.rsplit("/", 1)[-1]
                urls.append(("arxiv_title", f"https://arxiv.org/pdf/{re.sub(r'v\\d+$', '', ident)}"))
        except Exception:
            pass
    return list(dict.fromkeys(urls))


def main():
    cids = [ln.strip() for ln in io.open(sys.argv[1], encoding="utf-8") if ln.strip()]
    cands = {c["cid"]: c for c in json.load(io.open(R.ROOT / "candidates.json", encoding="utf-8"))}
    log_path = R.ROOT / "retrieval.json"
    log = json.load(io.open(log_path, encoding="utf-8"))
    got = 0
    for cid in cids:
        entry = log.get(cid) or {"status": "not_obtained", "title": cands[cid]["title"], "tried": []}
        if entry.get("status") == "ok":
            continue
        cand = cands[cid]
        stem = R.file_stem(cand)
        pdf_path, md_path = R.LIB / f"{stem}.pdf", R.LIB / f"{stem}.md"
        for src, url in extra_candidates(cand):
            try:
                data, final_url, ctype = R.fetch(url, R.UA_WEB if not src.startswith("arxiv") else R.UA_API)
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
            if not pdf_path.exists():
                with io.open(pdf_path, "wb") as fh:
                    fh.write(data)
            chars = R.convert(pdf_path, md_path) if not md_path.exists() else md_path.stat().st_size
            entry.update(status="ok", source=src, source_url=final_url, pages=pages, title_word_share=share,
                         md_chars=chars, pdf_path=str(pdf_path).replace("\\", "/"), md_path=str(md_path).replace("\\", "/"))
            got += 1
            break
        log[cid] = entry
        print(cid, entry["status"], entry.get("source", ""), "|", stem[:70], flush=True)
        # Re-read before writing so that a concurrent first pass is not overwritten.
        current = json.load(io.open(log_path, encoding="utf-8"))
        current[cid] = entry
        with io.open(log_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(current, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        log = current
        time.sleep(1.0)
    print(f"second pass obtained {got} of {len(cids)}", flush=True)


if __name__ == "__main__":
    main()
