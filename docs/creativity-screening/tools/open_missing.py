"""Open the landing page of every experiment that still lacks full text, in the owner's Chrome.

Publishers block scripted downloads, so the owner saves the PDFs by hand. This script opens one
DOI landing page per paper (no direct-download links), in two new Chrome windows: papers that
are free to read, then papers that need a subscription. The first tab is to-download.html,
which lists every link the retrieval step found, including free working-paper versions.

Usage: python open_missing.py            (print the list only)
       python open_missing.py --open     (print the list and open the Chrome windows)
"""
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import retrieve as R

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
cands = {c["cid"]: c for c in json.load(io.open(R.ROOT / "candidates.json", encoding="utf-8"))}
dec = {d["cid"]: d for d in json.load(io.open(R.ROOT / "triage" / "decisions.json", encoding="utf-8"))}
log = json.load(io.open(R.ROOT / "retrieval.json", encoding="utf-8"))

free, paid = [], []
for cid, d in sorted(dec.items()):
    if d["path"] != "experiment_full" or d["in_library"]:
        continue
    entry = log.get(cid) or {}
    if entry.get("status") == "ok":
        continue
    c = cands[cid]
    hint = entry.get("suggestion_for_owner") or ""
    url = f"https://doi.org/{c['doi']}" if c.get("doi") else (c.get("url") or "")
    if not url:
        found = re.findall(r"https?://[^\s)\"']+", hint)
        url = found[0].rstrip(".,;") if found else ""
    # A hint that only mentions a free working-paper version (Chen and Chan; Zhu and Zou) stays in the subscription window.
    is_free = (bool(re.search(r"open access|no subscription|free to read", hint, flags=re.I))
               or (c.get("doi") or "").startswith("10.2139/ssrn") or "SAGE Open" in (c.get("venue") or ""))
    (free if is_free else paid).append((cid, c["authors"], c["year"], c["title"], c.get("venue") or "", url))

for label, rows in (("Free to read", free), ("Subscription or unknown access", paid)):
    print(f"\n{label}: {len(rows)}")
    for cid, authors, year, title, venue, url in rows:
        print(f"  {cid} {authors} ({year}). {title[:80]} [{venue}]\n       {url or 'NO URL'}")

if "--open" in sys.argv:
    assert CHROME.exists(), "Chrome not found"
    index = (R.ROOT / "to-download.html").resolve().as_uri()
    for rows, first in ((free, [index]), (paid, [])):
        urls = first + [r[5] for r in rows if r[5]]
        if urls:
            subprocess.Popen([str(CHROME), "--new-window", *urls])
    print(f"\nOpened {len(free)} + {len(paid)} paper tabs in two Chrome windows (plus the list page).")
