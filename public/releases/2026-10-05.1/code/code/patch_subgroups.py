"""Patch src/estimates.json and src/papers.json with subgroup estimates.

Used when support_info/meta_analysis/ isn't synced locally and we can't
re-run the full build pipeline. Reads the current JSON, marks existing
estimates with is_subgroup=False, and appends the ADDITIONAL_ESTIMATES
list from build_website_data.py with is_subgroup=True.

Also applies a few high-confidence scorecard corrections from the third
fact-check pass directly to papers.json (so we don't need the XLSX to
re-run the full build).
"""
import json
from pathlib import Path
import sys

SITE = Path(r"C:/Users/greyes/Dropbox/Admin/website/ai-skill-atlas")
EST_PATH = SITE / "src" / "estimates.json"
PAPERS_PATH = SITE / "src" / "papers.json"

# Make build_website_data importable
sys.path.insert(0, str(SITE / "code"))
import build_website_data as bwd

# ── Load current JSON ────────────────────────────────────────────────────
estimates = json.loads(EST_PATH.read_text(encoding="utf-8"))
papers = json.loads(PAPERS_PATH.read_text(encoding="utf-8"))

# ── Mark existing estimates as non-subgroup ──────────────────────────────
for e in estimates:
    e.setdefault("is_subgroup", False)

# ── Apply scorecard corrections to papers.json ───────────────────────────
PAPER_PATCHES = {
    "hausman_etal_2025": {
        "setting_detail": "Israel, Hebrew University Business School; BA/MA/MBA courses across multiple faculties (2018-2024)",
    },
    "kazemitabaar_etal_2023": {
        "setting_detail": "Canada (recruited from coding camps in two North American cities), online via Google Meet; ages 10-17 (M=12.5)",
    },
    "chung_etal_2025": {
        "authors_full": "Angel Tsai-Hsuan Chung, Botong Zhang, Ling-Chieh Kung, Hamsa Bastani, Osbert Bastani",
    },
}

for p in papers:
    patch = PAPER_PATCHES.get(p["paper_key"])
    if patch:
        p.update(patch)

# ── Append ADDITIONAL_ESTIMATES with synthetic estimate_ids ──────────────
sg_counter = {}
n_added = 0
for est in bwd.ADDITIONAL_ESTIMATES:
    pkey = est["paper_key"]
    sg_counter[pkey] = sg_counter.get(pkey, 0) + 1
    est_id = f"{pkey}__sg{sg_counter[pkey]}"

    eff = est.get("effect_size_sd")
    se = est.get("se")
    ci_lo = est.get("ci_lower")
    ci_hi = est.get("ci_upper")
    if ci_lo is None and eff is not None and se is not None:
        ci_lo = eff - 1.96 * se
    if ci_hi is None and eff is not None and se is not None:
        ci_hi = eff + 1.96 * se
    if se is None and ci_lo is not None and ci_hi is not None:
        se = (ci_hi - ci_lo) / (2 * 1.96)

    full = dict(est)
    full["estimate_id"] = est_id
    full["se"] = se
    full["ci_lower"] = ci_lo
    full["ci_upper"] = ci_hi
    estimates.append(full)
    n_added += 1

# ── Write back ───────────────────────────────────────────────────────────
EST_PATH.write_text(
    json.dumps(estimates, indent=2, ensure_ascii=False), encoding="utf-8"
)
PAPERS_PATH.write_text(
    json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8"
)

print(f"  Added {n_added} subgroup estimates.")
print(f"  Total estimates: {len(estimates)}")
print(f"  Applied scorecard patches to {len(PAPER_PATCHES)} papers.")
print(f"  WROTE {EST_PATH}")
print(f"  WROTE {PAPERS_PATH}")
