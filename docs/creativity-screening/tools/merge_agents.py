"""Fold the retrieval agents' results into retrieval.json and report what each path now has."""
import io
import json
import os
from collections import Counter

import retrieve as R

log_path = R.ROOT / "retrieval.json"
log = json.load(io.open(log_path, encoding="utf-8"))
added = 0
for path in sorted((R.ROOT / "retrieval-agents").glob("*.json")):
    d = json.load(io.open(path, encoding="utf-8"))
    cid = d["cid"]
    entry = log.get(cid, {"tried": []})
    if d.get("status") == "ok" and d.get("pdf_path") and os.path.exists(d["pdf_path"]) and os.path.exists(d.get("md_path") or ""):
        if entry.get("status") != "ok":
            added += 1
        entry.update(status="ok", source="agent", source_url=d.get("source_url"), pdf_path=d["pdf_path"].replace("\\", "/"),
                     md_path=d["md_path"].replace("\\", "/"), version_saved=d.get("version_saved"),
                     is_latest_version=d.get("is_latest_version"), differences_from_latest=d.get("differences_from_latest"),
                     pages=d.get("pages"))
    else:
        entry.setdefault("status", "not_obtained")
        entry["suggestion_for_owner"] = d.get("suggestion_for_owner")
        entry["agent_tried"] = d.get("tried", [])
    entry.setdefault("title", d.get("title"))
    log[cid] = entry
with io.open(log_path, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(log, fh, indent=1, ensure_ascii=False)
    fh.write("\n")

dec = json.load(io.open(R.ROOT / "triage" / "decisions.json", encoding="utf-8"))
forms = {p.stem for p in (R.ROOT / "forms").glob("c*.json")}
raw = {p.name.split(".")[0] for p in (R.ROOT / "forms" / "raw").glob("c*.json")}
summary = Counter()
todo = {"full_with_text": [], "full_no_text": [], "context": [], "small": []}
for d in dec:
    cid, path = d["cid"], d["path"]
    if d["in_library"] or path in ("out", "untriaged"):
        continue
    has = log.get(cid, {}).get("status") == "ok"
    tried = cid in log
    summary[(path, "text" if has else ("no text" if tried else "untried"))] += 1
    if cid in forms or cid in raw:
        continue
    if path == "experiment_full":
        (todo["full_with_text"] if has else todo["full_no_text"] if tried else []).append(cid)
    elif path == "context" and tried:
        todo["context"].append(cid)
    elif path == "experiment_small" and tried:
        todo["small"].append(cid)
print("agent results merged; newly obtained:", added)
for key, n in sorted(summary.items()):
    print("  ", key, n)
print(json.dumps(todo))
