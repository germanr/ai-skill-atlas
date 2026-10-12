"""Which extraction papers are ready for the next stage.

  supplement: supplement files on file, extraction chain finished, no supplement pass yet
  analysis:   posted data downloaded, extraction chain finished, supplement pass done (when a supplement exists), no analysis yet
  sources:    everything above that applies is done

Usage: python tools/stage_ready.py [supplement|analysis|sources]   (prints the cids, space-separated)
"""
import io
import json
import sys
from pathlib import Path

S = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return default


st = (load(S / "report-data.json", {}) or {}).get("status_by_cid", {})
scope = sorted(c for c, v in st.items() if v == "core" and c not in {"c044", "c276", "c818"})
supp = {c for c, v in (load("D:/projects/ai-skill-atlas/creativity-supplements/manifest.json", {}) or {}).items() if v.get("files")}
data = set(((load("D:/projects/ai-skill-atlas/creativity-data/manifest.json", {}) or {}).get("papers") or {}).keys())
ready = {"supplement": [], "analysis": [], "sources": []}
for c in scope:
    status = load(S / "extraction" / "status" / f"{c}.json")
    if not status:
        continue
    sup_done = "supplement" in status
    if c in supp and not sup_done:
        ready["supplement"].append(c)
        continue
    analyzed = (S / "analysis" / c / "compare.json").exists()
    if c in data and not analyzed:
        ready["analysis"].append(c)
        continue
    ready["sources"].append(c)
stage = sys.argv[1] if len(sys.argv) > 1 else None
if stage:
    print(" ".join(ready[stage]))
else:
    for k, v in ready.items():
        print(f"{k}: {len(v)} {' '.join(v)}")
