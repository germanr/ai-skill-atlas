"""Patch src/papers.json incentives field to focus on PERFORMANCE incentives.

Per user: 'I don't care so much about compensation of participants,
but more about whether there are incentives to perform well.'

Run when meta_analysis.xlsx isn't synced and we can't rebuild from scratch.
"""
import json
from pathlib import Path

SITE = Path(r"C:/Users/greyes/Dropbox/Admin/website/ai-skill-atlas")
PAPERS_PATH = SITE / "src" / "papers.json"

INCENTIVE_PATCHES = {
    "barcaui_2025":         "None",
    "fan_etal_2025":        "None (flat compensation; no performance bonus)",
    "kalam_etal_2025":      "None (gift-card drawing for participation, not performance)",
    "kazemitabaar_etal_2023": "None (flat $50 gift card)",
    "kumar_etal_2023":      "None (flat $3.30 MTurk pay)",
    "lira_etal_2025":       "None (flat Prolific pay)",
    "liu_etal_2026":        "None (flat Prolific pay)",
    "shen_and_tamkin_2026": "None (flat $150)",
    "contractor_reyes_2026": "Lottery tickets ($100 each, 30 drawn) tied to test and essay performance",
}

papers = json.loads(PAPERS_PATH.read_text(encoding="utf-8"))
for p in papers:
    new = INCENTIVE_PATCHES.get(p["paper_key"])
    if new is not None:
        p["incentives"] = new

PAPERS_PATH.write_text(json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Patched {len(INCENTIVE_PATCHES)} papers; wrote {PAPERS_PATH}")
