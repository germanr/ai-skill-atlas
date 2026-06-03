"""Build per-paper input files for summary + fact-check subagents.

Each output file contains: markdown_path, refreshed_pdf_path (if any),
current_entry (the scorecard fields to verify), and estimates.
"""
import json
from pathlib import Path

SITE = Path(r"C:/Users/greyes/Dropbox/Admin/website/ai-skill-atlas")
PAPERS = json.loads((SITE / "src" / "papers.json").read_text(encoding="utf-8"))
ESTIMATES = json.loads((SITE / "src" / "estimates.json").read_text(encoding="utf-8"))

MD_DIR = Path(r"C:/Users/greyes/Dropbox/Research/ai-learning/support_info/meta_analysis/markdown")
PDF_DIR = SITE / "public" / "pdfs"

# Override map for non-standard markdown filenames
MD_OVERRIDES = {
    "learnlm_team_2025": "AI Team (2025) - AI Tutoring UK Classrooms.md",
}

# For own paper, point to the .tex source
TEX_PATH = r"C:/Users/greyes/Dropbox/Research/ai-learning/paper/ai-learning.tex"


def find_md(paper):
    key = paper["paper_key"]
    if key in MD_OVERRIDES:
        return MD_DIR / MD_OVERRIDES[key]
    author_root = paper["authors_short"].replace(" et al.", "").split()[0]
    year = paper.get("year", "")
    for f in MD_DIR.glob("*.md"):
        # Match by first author word (handles "Shen & Tamkin", "and", etc.)
        if author_root in f.stem:
            return f
    return None


OUT = SITE / "code" / "subagent_inputs"
OUT.mkdir(exist_ok=True)

scorecard_fields = [
    "title", "authors_full", "year", "venue",
    "country", "population_category", "setting_detail",
    "lab_vs_field", "study_design", "ai_tool", "ai_design",
    "n_total", "incentives", "learning_domain_primary",
]

for p in PAPERS:
    key = p["paper_key"]
    if key == "contractor_reyes_2026":
        md_path = TEX_PATH
    else:
        md = find_md(p)
        md_path = str(md) if md else None

    # Newest PDF path (if we refreshed it)
    pdf_filename = p.get("pdf_filename") or ""
    pdf_path = str(PDF_DIR / pdf_filename) if pdf_filename and (PDF_DIR / pdf_filename).exists() else None

    ests = [{k: e.get(k) for k in ["estimate_id","study_label","effect_size_sd","se","ci_lower","ci_upper","n_total","treatment","control","outcome","outcome_timing"]}
            for e in ESTIMATES if e["paper_key"] == key]

    ctx = {
        "paper_key": key,
        "markdown_path": md_path,
        "refreshed_pdf_path": pdf_path,
        "current_scorecard": {f: p.get(f) for f in scorecard_fields},
        "estimates": ests,
    }
    (OUT / f"{key}.json").write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Wrote {len(PAPERS)} per-paper input files to {OUT}")
