"""Save the three planning-stage search reports and the library list as workflow inputs."""
import io
import json
from pathlib import Path

REPO = Path("C:/Dropbox/Admin/website/ai-skill-atlas")
OUT = REPO / "docs" / "creativity-screening"
SUB = Path("C:/Users/greyes/.claude/projects/c--Users-greyes-Dropbox/"
           "9b21ac29-ce13-4c2a-915c-885dae0d8cf8/subagents")
LIB = Path("C:/Dropbox/Research/ai-lab/literature/creativity")

for sub in ["search", "triage", "forms/raw", "audit"]:
    (OUT / sub).mkdir(parents=True, exist_ok=True)

SEEDS = {
    "a64ec5fe68b2ce82e": ("seed-verified-leads.md",
                          "Citation check of 33 leads from the first scan (2026-10-04)"),
    "a204503db28eb0cbd": ("seed-meta-analysis-lists.md",
                          "Included-study lists of three meta-analyses (2026-10-04)"),
    "a3ead43f9ab99c310": ("seed-openalex-citing.md",
                          "OpenAlex works since 2025-01-01 that cite eight anchor experiments (2026-10-04)"),
}

for tid, (name, title) in SEEDS.items():
    lines = io.open(SUB / f"agent-{tid}.jsonl", encoding="utf-8").read().splitlines()
    text = None
    for ln in reversed(lines):
        obj = json.loads(ln)
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        if obj.get("type") == "assistant" and isinstance(msg.get("content"), list):
            texts = [b.get("text", "") for b in msg["content"] if b.get("type") == "text"]
            if texts and len("".join(texts)) > 2000:
                text = "\n".join(texts)
                break
    assert text, tid
    body = f"# {title}\n\nSearch input for the creativity screening. Produced by a read-only sub-agent; every entry is rechecked downstream.\n\n{text.strip()}\n"
    with io.open(OUT / "search" / name, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    print(name, len(body))

# Library list: papers already on disk, with their keys in the current JSON.
papers = json.load(io.open(REPO / "src" / "creativity_papers.json", encoding="utf-8"))["papers"]
by_md = {p["md_filename"]: p for p in papers}
rows = []
for md in sorted(LIB.glob("*.md")):
    p = by_md.get(md.name)
    rows.append({
        "paper_key": p["paper_key"] if p else None,
        "in_current_json": bool(p),
        "authors_short": p["authors_short"] if p else None,
        "year": p["year"] if p else None,
        "title": p["title"] if p else None,
        "doi_or_url": p["doi_or_url"] if p else None,
        "current_design_class": p["design_class"] if p else None,
        "current_theme": p["theme"] if p else None,
        "md_path": str(md).replace("\\", "/"),
        "pdf_path": str(md.with_suffix(".pdf")).replace("\\", "/"),
        "pdf_exists": md.with_suffix(".pdf").exists(),
    })
missing = [p["paper_key"] for p in papers if p["md_filename"] not in {r["md_path"].split("/")[-1] for r in rows}]
with io.open(OUT / "search" / "library.json", "w", encoding="utf-8", newline="\n") as fh:
    json.dump(rows, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print("library rows", len(rows), "in json", sum(r["in_current_json"] for r in rows), "json papers with no md", missing)
for r in rows:
    if not r["in_current_json"]:
        print("  not in json:", r["md_path"].split("/")[-1])
