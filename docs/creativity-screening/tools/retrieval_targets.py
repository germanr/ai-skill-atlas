"""List candidates that still lack full text, with the file name each should be saved under.

Usage: python retrieval_targets.py experiment_full[,context,...]   -> prints a JSON list for workflow args
Only candidates the script has already tried and failed are listed, unless --all is given.
"""
import io
import json
import sys

import retrieve as R

paths = set(sys.argv[1].split(","))
include_untried = "--all" in sys.argv
cands = {c["cid"]: c for c in json.load(io.open(R.ROOT / "candidates.json", encoding="utf-8"))}
dec = json.load(io.open(R.ROOT / "triage" / "decisions.json", encoding="utf-8"))
log = json.load(io.open(R.ROOT / "retrieval.json", encoding="utf-8"))
done_agents = {p.stem for p in (R.ROOT / "retrieval-agents").glob("*.json")} if (R.ROOT / "retrieval-agents").exists() else set()
out = []
for d in dec:
    cid = d["cid"]
    if d["path"] not in paths or d["in_library"] or cid in done_agents:
        continue
    entry = log.get(cid)
    if entry is None and not include_untried:
        continue
    if entry and entry.get("status") == "ok":
        continue
    out.append({"cid": cid, "stem": R.file_stem(cands[cid])})
print(json.dumps(out, ensure_ascii=False))
