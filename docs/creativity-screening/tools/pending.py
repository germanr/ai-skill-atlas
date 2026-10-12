"""Print what each screening path still lacks, as JSON ready for workflow args."""
import io
import json

import retrieve as R

dec = json.load(io.open(R.ROOT / "triage" / "decisions.json", encoding="utf-8"))
log = json.load(io.open(R.ROOT / "retrieval.json", encoding="utf-8"))
cands = {c["cid"]: c for c in json.load(io.open(R.ROOT / "candidates.json", encoding="utf-8"))}
forms = {}
for p in (R.ROOT / "forms").glob("c*.json"):
    if not p.stem[1:].isdigit():  # skip helper files such as citations-family.json
        continue
    try:
        forms[p.stem] = json.load(io.open(p, encoding="utf-8")).get("screener")
    except Exception:
        forms[p.stem] = "unparseable"
agents = {p.stem for p in (R.ROOT / "retrieval-agents").glob("*.json")}
cites = {p.stem for p in (R.ROOT / "forms" / "citations").glob("*.json")}
out = {"full_text_unscreened": [], "full_text_reconciled_not_final": [], "full_no_text": [], "retrieve_agent_todo": [],
       "context_todo": [], "small_todo": [], "missing_citation": []}
for d in dec:
    cid, path = d["cid"], d["path"]
    if d["in_library"] or path in ("out", "untriaged"):
        continue
    has = log.get(cid, {}).get("status") == "ok"
    state = forms.get(cid)
    if path == "experiment_full":
        if has and state is None:
            out["full_text_unscreened"].append(cid)
        elif has and state == "reconciled":
            out["full_text_reconciled_not_final"].append(cid)
        elif not has:
            out["full_no_text"].append(cid)
            if cid not in agents:
                out["retrieve_agent_todo"].append({"cid": cid, "stem": R.file_stem(cands[cid])})
    elif path == "context" and state is None:
        out["context_todo"].append(cid)
    elif path == "experiment_small" and state is None:
        out["small_todo"].append(cid)
    if state is not None and cid not in cites:
        out["missing_citation"].append(cid)
for key, val in out.items():
    print(key, len(val))
print(json.dumps(out, ensure_ascii=False))
print("form states:", {s: sum(1 for v in forms.values() if v == s) for s in sorted(set(forms.values()), key=str)})
