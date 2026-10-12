"""Write a cid list for retrieval.

Usage: python pick_cids.py likely_experiments <out.txt>
       python pick_cids.py paths <out.txt> experiment_full,context   (uses triage/decisions.json)
Skips candidates that are in the library or already retrieved.
"""
import io
import json
import sys
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
mode, out = sys.argv[1], sys.argv[2]
cands = json.load(io.open(ROOT / "candidates.json", encoding="utf-8"))
log_path = ROOT / "retrieval.json"
done = json.load(io.open(log_path, encoding="utf-8")) if log_path.exists() else {}
EXP = {"randomized_experiment_people", "experiment_assignment_unclear", "quasi_experiment_people"}

if mode == "likely_experiments":
    pick = [c["cid"] for c in cands if not c.get("library") and EXP & set(c["design_guesses"])]
else:
    paths = set(sys.argv[3].split(","))
    dec = json.load(io.open(ROOT / "triage" / "decisions.json", encoding="utf-8"))
    pick = [d["cid"] for d in dec if d["path"] in paths and not d["in_library"]]
pick = [c for c in pick if done.get(c, {}).get("status") != "ok"]
io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(pick) + "\n")
print(len(pick), "cids ->", out)
