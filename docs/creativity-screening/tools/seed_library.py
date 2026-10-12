"""Write search/seed-library.json: one candidate record per paper already in the source library."""
import io
import json
import re
from pathlib import Path

ROOT = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
lib = json.load(io.open(ROOT / "search" / "library.json", encoding="utf-8"))

DESIGN = {"RCT": "experiment_assignment_unclear", "Hybrid": "other", "Corpus": "observational", "Review": "synthesis"}
records, seen = [], set()
for row in lib:
    name = row["md_path"].split("/")[-1][:-3]
    if "Widespread Uneven Rarely Disclosed" in name:
        continue  # second copy of Russell et al. (2025)
    m = re.match(r"(.+?) \((\d{4})\) - (.+)$", name)
    who, year, short = m.group(1), int(m.group(2)), m.group(3)
    ref = row["doi_or_url"] or ""
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", ref) if "doi.org/" in ref else None
    arx = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", ref)
    rec = {
        "title": row["title"] or short,
        "authors": row["authors_short"] or who,
        "year": row["year"] or year,
        "venue": "",
        "status": "other",
        "doi": doi,
        "arxiv_id": arx.group(1) if arx else None,
        "url": ref or row["pdf_path"],
        "first_posted": None,
        "other_versions": [],
        "design_guess": DESIGN.get(row["current_design_class"], "other"),
        "question_guess": [],
        "n_participants": None,
        "task": "",
        "evidence": ("In the source library and in the current creativity_papers.json (design label "
                     f"{row['current_design_class']!r}, theme {row['current_theme']!r}); labels are unverified."
                     if row["in_current_json"] else
                     "In the source library but not in the current creativity_papers.json; title taken from the file name."),
        "confirmed_from": "prior_report",
        "lane": "seed-library",
        "library_md_path": row["md_path"],
        "library_pdf_path": row["pdf_path"],
        "library_paper_key": row["paper_key"],
    }
    key = rec["title"].lower()
    if key in seen:
        continue
    seen.add(key)
    records.append(rec)

out = {"lane": "seed-library", "queries": [], "sources_checked": ["Research/ai-lab/literature/creativity"],
       "coverage_limits": "Titles and labels come from the May 2026 collection and are rechecked downstream.",
       "candidates": records}
with io.open(ROOT / "search" / "seed-library.json", "w", encoding="utf-8", newline="\n") as fh:
    json.dump(out, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print(len(records), "library records")
