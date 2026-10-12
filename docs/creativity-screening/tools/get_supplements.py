"""Fetch the supplements of extraction papers whose supplement exists but is not on file, where a public link allows it.

Sources: the screening form's source.supplement ("where": URLs) and the data check's deposits of supplementary material.
Only public pages and direct file links are requested, with a generic User-Agent and no personal identifier. A login,
paywall, bot check, or refusal (HTTP 401/403) stops the attempt for that link, and the paper goes on the manual list.
Files go to D:/projects/ai-skill-atlas/creativity-supplements/<cid>/ (Germ\u00e1n, 2026-10-09: downloads go to D:), each PDF
with a markdown conversion beside it; manifest.json there records URL, size, SHA-256, and time, with a copy in the
screening folder (supplement-manifest.json). supplements-to-download.md lists what needs a person.

Usage: python tools/get_supplements.py [--only c015 ...]
"""
import argparse
import hashlib
import html
import io
import json
import re
import shutil
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SCREEN = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEST = Path("D:/projects/ai-skill-atlas/creativity-supplements")
UA = {"User-Agent": "Mozilla/5.0 (compatible; atlas-supplements/0.1)"}
FILE_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip|csv|txt|rtf|sav|dta|rds|rdata|json)(\?|$)", re.I)


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


def fetch(url, binary=True, max_bytes=200 << 20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise RuntimeError("larger than 200 MB")
        ctype = r.headers.get("Content-Type", "")
        final = r.geturl()
    if not binary:
        return data.decode("utf-8", errors="replace"), ctype, final
    return data, ctype, final


def looks_blocked(text):
    return bool(re.search(r"captcha|are you a robot|access denied|cf-chl|cloudflare|enable javascript and cookies|sign in to|log in to", text[:20000], re.I))


def links_from_page(url):
    """Supplement file links on a public article page (Springer Nature ESM, Frontiers, MDPI, journal 'suppl' paths)."""
    text, ctype, final = fetch(url, binary=False)
    if looks_blocked(text):
        raise RuntimeError("the page shows a login or bot check")
    hrefs = {html.unescape(h) for h in re.findall(r"""href=["']([^"']+)["']""", text)}
    out = []
    for h in hrefs:
        if h.startswith("//"):
            h = "https:" + h
        elif h.startswith("/"):
            m = re.match(r"(https?://[^/]+)", final)
            h = (m.group(1) if m else "") + h
        if ("static-content.springer.com/esm/" in h or "/supplementary-material/" in h.lower() or "/doi/suppl/" in h
                or re.search(r"(supp|suppl|supplement|esm|data_sheet|appendix)[^/]*" + FILE_RE.pattern, h, re.I)):
            out.append(h)
    return sorted(set(out)), final


def save(cid, url, data, ctype):
    folder = DEST / cid
    folder.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[<>:\"|?*\x00-\x1f]", "_", urllib.request.url2pathname(url.split("?")[0].rstrip("/").split("/")[-1])) or "supplement"
    if not FILE_RE.search(name):
        ext = ".pdf" if "pdf" in ctype else ".zip" if "zip" in ctype else ".bin"
        name += ext
    path = folder / name
    path.write_bytes(data)
    rec = {"url": url, "path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
           "content_type": ctype, "downloaded_at": datetime.now().isoformat(timespec="seconds")}
    if path.suffix.lower() == ".pdf" and data[:5] == b"%PDF-":
        try:
            import pymupdf4llm
            md = pymupdf4llm.to_markdown(str(path))
            path.with_suffix(".md").write_text(md, encoding="utf-8")
            rec["md_path"] = str(path.with_suffix(".md"))
        except Exception as e:
            rec["md_error"] = str(e)[:200]
    elif path.suffix.lower() == ".pdf":
        rec["warning"] = "the response is not a PDF (first bytes differ); probably a login or landing page"
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    st = (load(SCREEN / "report-data.json", {}) or {}).get("status_by_cid", {})
    cids = a.only or sorted(c for c, v in st.items() if v == "core" and c not in {"c044", "c276", "c818"})
    mpath = DEST / "manifest.json"
    manifest = load(mpath, {}) or {}
    manual = []
    for cid in cids:
        form = load(SCREEN / "forms" / f"{cid}.json", {}) or {}
        sup = (form.get("source") or {}).get("supplement") or {}
        if not (sup.get("exists") == "yes" and not sup.get("in_this_pdf") and not sup.get("on_file")):
            continue
        urls = [u.rstrip(".,;") for u in re.findall(r"https?://[^\s)\"';,]+", str(sup.get("where") or ""))]
        for dep in ((load(SCREEN / "forms" / "data" / f"{cid}.json", {}) or {}).get("deposits") or []):
            if dep.get("access") == "public" and dep.get("contents") == "aggregate_only" and dep.get("url"):
                urls.append(dep["url"])
        entry = manifest.setdefault(cid, {"holds": sup.get("holds"), "files": [], "attempts": []})
        if entry["files"]:
            continue
        for url in dict.fromkeys(urls):
            if re.search(r"osf\.io|github\.com|zenodo|dryad|dataverse|figshare|dropbox\.com", url, re.I):
                entry["attempts"].append({"url": url, "result": "data repository or personal link: handled by the data downloader or skipped"})
                continue
            try:
                if FILE_RE.search(url) or "static-content.springer.com/esm/" in url or "researchsquare.com/files/" in url:
                    data, ctype, final = fetch(url)
                    if b"<html" in data[:2000].lower():
                        raise RuntimeError("a web page came back instead of a file")
                    entry["files"].append(save(cid, url, data, ctype))
                    entry["attempts"].append({"url": url, "result": "downloaded"})
                else:
                    links, final = links_from_page(url)
                    entry["attempts"].append({"url": url, "result": f"page read ({final}); {len(links)} supplement links"})
                    for link in links:
                        try:
                            data, ctype, _ = fetch(link)
                            if b"<html" in data[:2000].lower():
                                raise RuntimeError("a web page came back instead of a file")
                            entry["files"].append(save(cid, link, data, ctype))
                            entry["attempts"].append({"url": link, "result": "downloaded"})
                        except Exception as e:
                            entry["attempts"].append({"url": link, "result": f"failed: {str(e)[:160]}"})
                        time.sleep(1)
            except urllib.error.HTTPError as e:
                entry["attempts"].append({"url": url, "result": f"HTTP {e.code}: stopped (login, paywall, or bot check)"})
            except Exception as e:
                entry["attempts"].append({"url": url, "result": f"failed: {str(e)[:160]}"})
            time.sleep(1)
        if not entry["files"]:
            manual.append((cid, sup.get("holds"), urls, entry["attempts"]))
        print(f"{cid}: {len(entry['files'])} files | " + " | ".join(x['result'][:70] for x in entry["attempts"]))
    with io.open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    shutil.copyfile(mpath, SCREEN / "supplement-manifest.json")
    lines = ["# Supplements to download by hand", "",
             "The papers below have a supplement that the scripts could not fetch (a publisher page refused scripted requests, "
             "or no direct link exists). Open the link, download the supplement files, and save them to "
             "`D:\\projects\\ai-skill-atlas\\creativity-supplements\\<cid>\\` (one folder per paper id). The extraction then reads them.", ""]
    for cid, holds, urls, attempts in manual:
        lines.append(f"- **{cid}**: {' / '.join(urls) or 'no link in the paper; see the journal page'}  ")
        lines.append(f"  What it holds: {str(holds or '')[:300]}")
    io.open(SCREEN / "supplements-to-download.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"papers with supplements on file: {sum(1 for v in manifest.values() if v['files'])} | manual: {len(manual)}")


if __name__ == "__main__":
    main()
