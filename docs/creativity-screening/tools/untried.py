"""Write the cids on a screening path that no retrieval attempt has touched yet."""
import io
import json
import sys

import retrieve as R

paths = set(sys.argv[1].split(","))
out_path = sys.argv[2]
dec = json.load(io.open(R.ROOT / "triage" / "decisions.json", encoding="utf-8"))
log = json.load(io.open(R.ROOT / "retrieval.json", encoding="utf-8"))
pick = [d["cid"] for d in dec if d["path"] in paths and not d["in_library"] and d["cid"] not in log]
io.open(out_path, "w", encoding="utf-8", newline="\n").write("\n".join(pick) + "\n")
print(len(pick), "untried cids")
