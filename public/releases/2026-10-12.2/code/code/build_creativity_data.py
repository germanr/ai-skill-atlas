"""Build creativity_papers.json from inline paper metadata.

Parallel to build_website_data.py but for the creativity section of the
Atlas of AI and Human Skill. Initially only paper-level metadata —
effect-size estimates will be added as subagent extraction proceeds.

Source markdowns: C:/Users/greyes/Dropbox/Research/ai-lab/literature/creativity/
"""
import json
from pathlib import Path

# Themes follow user's taxonomy:
#   "Anchor — homogenization", "Counterpoints / nuance", "Fixes / mechanisms",
#   "Cross-model / cross-modal", "Academic & scientific writing",
#   "Market consequences", "Synthesis / review"
# Theory-only papers (Castro Gao Martin, Wu et al., Raghavan) are excluded.
# stub = paywalled, no PDF on file yet.

PAPERS = [
    # ── Anchor empirical results (homogenization) ────────────────────────────
    dict(
        paper_key="padmakumar_he_2024",
        authors_short="Padmakumar & He",
        year=2024,
        title="Does Writing With Language Models Reduce Content Diversity?",
        venue="ICLR 2024",
        doi_or_url="https://arxiv.org/abs/2309.05196",
        design_class="RCT",
        theme="Anchor — homogenization",
        outcome_focus="Essay content diversity",
        stub=False,
        md_filename="Padmakumar and He (2024) - Does Writing With Language Models Reduce Content Diversity.md",
    ),
    dict(
        paper_key="doshi_hauser_2024",
        authors_short="Doshi & Hauser",
        year=2024,
        title="Generative AI Enhances Individual Creativity but Reduces the Collective Diversity of Novel Content",
        venue="Science Advances",
        doi_or_url="https://doi.org/10.1126/sciadv.adn5290",
        design_class="RCT",
        theme="Anchor — homogenization",
        outcome_focus="Story creativity vs collective diversity",
        stub=False,
        md_filename="Doshi and Hauser (2024) - Generative AI Enhances Individual Creativity.md",
    ),
    dict(
        paper_key="anderson_shah_kreminski_2024",
        authors_short="Anderson, Shah & Kreminski",
        year=2024,
        title="Homogenization Effects of LLMs on Human Creative Ideation",
        venue="ACM C&C 2024",
        doi_or_url="https://doi.org/10.1145/3635636.3656204",
        design_class="RCT",
        theme="Anchor — homogenization",
        outcome_focus="Idea similarity across users",
        stub=False,
        md_filename="Anderson Shah Kreminski (2024) - Homogenization Effects of LLMs on Human Creative Ideation.md",
    ),
    dict(
        paper_key="moon_green_kushlev_2025",
        authors_short="Moon, Green & Kushlev",
        year=2025,
        title="The Homogenizing Effect of LLMs on Creative Diversity",
        venue="CHB: Artificial Humans 6",
        doi_or_url="https://doi.org/10.1016/j.chbah.2025.100207",
        design_class="RCT",
        theme="Anchor — homogenization",
        outcome_focus="Creative output similarity across users",
        stub=False,
        md_filename="Moon Green Kushlev (2025) - Homogenizing Effect of LLMs on Creative Diversity.md",
    ),
    dict(
        paper_key="meincke_nave_terwiesch_2025",
        authors_short="Meincke, Nave & Terwiesch",
        year=2025,
        title="ChatGPT Decreases Idea Diversity in Brainstorming",
        venue="Nature Human Behaviour",
        doi_or_url="https://doi.org/10.1038/s41562-025-02173-x",
        design_class="RCT",
        theme="Anchor — homogenization",
        outcome_focus="Brainstorm idea diversity",
        stub=False,
        md_filename="Meincke et al (2025) - ChatGPT Decreases Idea Diversity in Brainstorming.md",
    ),
    dict(
        paper_key="moon_etal_2026",
        authors_short="Moon et al.",
        year=2026,
        title="The Creative Link Between Words and Ideas is Weakening in the AI Era",
        venue="PsyArXiv",
        doi_or_url="https://doi.org/10.31234/osf.io/jsz58_v6",
        design_class="Hybrid",
        theme="Anchor — homogenization",
        outcome_focus="Word-idea associative diversity",
        stub=False,
        md_filename="Moon et al (2026) - The Creative Link Between Words and Ideas.md",
    ),

    # ── Counterpoints / nuance ───────────────────────────────────────────────
    dict(
        paper_key="lee_chung_2024",
        authors_short="Lee & Chung",
        year=2024,
        title="An Empirical Investigation of the Impact of ChatGPT on Creativity",
        venue="Nature Human Behaviour",
        doi_or_url="https://doi.org/10.1038/s41562-024-01953-1",
        design_class="RCT",
        theme="Counterpoints / nuance",
        outcome_focus="Originality and quality of creative output",
        stub=False,
        md_filename="Lee and Chung (2024) - Empirical Investigation of ChatGPT on Creativity.md",
    ),
    dict(
        paper_key="boussioux_etal_2024",
        authors_short="Boussioux et al.",
        year=2024,
        title="The Crowdless Future? Generative AI and Creative Problem-Solving",
        venue="Organization Science",
        doi_or_url="https://doi.org/10.1287/orsc.2023.18430",
        design_class="RCT",
        theme="Counterpoints / nuance",
        outcome_focus="Solution quality and novelty",
        stub=False,
        md_filename="Boussioux et al (2024) - The Crowdless Future Generative AI and Creative Problem-Solving.md",
    ),
    dict(
        paper_key="ashkinaze_etal_2025",
        authors_short="Ashkinaze et al.",
        year=2025,
        title="How AI Ideas Affect the Creativity, Diversity, and Evolution of Human Ideas",
        venue="ACM CI 2025",
        doi_or_url="https://doi.org/10.1145/3715928.3737481",
        design_class="RCT",
        theme="Counterpoints / nuance",
        outcome_focus="Creativity, diversity, idea evolution over time",
        stub=False,
        md_filename="Ashkinaze et al (2025) - How AI Ideas Affect Creativity Diversity Evolution.md",
    ),

    # ── Fixes / mechanisms ───────────────────────────────────────────────────
    dict(
        paper_key="girotra_etal_2023",
        authors_short="Girotra et al.",
        year=2023,
        title="Ideas Are Dimes a Dozen: Large Language Models for Idea Generation in Innovation",
        venue="SSRN 4526071",
        doi_or_url="https://doi.org/10.2139/ssrn.4526071",
        design_class="Hybrid",
        theme="Fixes / mechanisms",
        outcome_focus="Idea quantity, quality, novelty",
        stub=False,
        md_filename="Girotra Meincke Terwiesch Ulrich (2023) - Ideas Are Dimes a Dozen.md",
    ),
    dict(
        paper_key="meincke_mollick_terwiesch_2024",
        authors_short="Meincke, Mollick & Terwiesch",
        year=2024,
        title="Prompting Diverse Ideas: Increasing AI Idea Variance",
        venue="SSRN / arXiv",
        doi_or_url="https://doi.org/10.2139/ssrn.4708466",
        design_class="RCT",
        theme="Fixes / mechanisms",
        outcome_focus="Prompt-induced idea variance",
        stub=False,
        md_filename="Meincke Mollick Terwiesch (2024) - Prompting Diverse Ideas.md",
    ),
    dict(
        paper_key="liu_etal_2024",
        authors_short="Liu et al.",
        year=2024,
        title="When ChatGPT is Gone: Creativity Reverts and Homogeneity Persists",
        venue="arXiv:2401.06816",
        doi_or_url="https://arxiv.org/abs/2401.06816",
        design_class="RCT",
        theme="Fixes / mechanisms",
        outcome_focus="Post-AI residual homogeneity",
        stub=False,
        md_filename="Liu et al (2024) - When ChatGPT is Gone Creativity Reverts and Homogeneity Persists.md",
    ),

    # ── Cross-model / cross-modal ────────────────────────────────────────────
    dict(
        paper_key="wenger_kenett_2025",
        authors_short="Wenger & Kenett",
        year=2025,
        title="We're Different, We're the Same: Creative Homogeneity Across LLMs",
        venue="arXiv:2501.19361",
        doi_or_url="https://arxiv.org/abs/2501.19361",
        design_class="Corpus",
        theme="Cross-model / cross-modal",
        outcome_focus="Cross-LLM convergence in creative output",
        stub=False,
        md_filename="Wenger and Kenett (2025) - Creative Homogeneity Across LLMs.md",
    ),
    dict(
        paper_key="hintze_etal_2026",
        authors_short="Hintze, Proschinger Åström & Schossau",
        year=2026,
        title="Autonomous Language-Image Generation Loops Converge to Generic Visual Motifs",
        venue="Patterns (Cell Press)",
        doi_or_url="https://doi.org/10.1016/j.patter.2025.101451",
        design_class="Corpus",
        theme="Cross-model / cross-modal",
        outcome_focus="Image-text loop convergence",
        stub=True,
        md_filename="Hintze Proschinger Schossau (2026) - Language-Image Generation Loops Converge to Generic Motifs.md",
    ),

    # ── Academic / scientific writing ────────────────────────────────────────
    dict(
        paper_key="liang_etal_2024",
        authors_short="Liang et al.",
        year=2024,
        title="Monitoring AI-Modified Content at Scale: A Case Study on Peer Reviews",
        venue="ICML 2024",
        doi_or_url="https://arxiv.org/abs/2403.07183",
        design_class="Corpus",
        theme="Academic & scientific writing",
        outcome_focus="AI text fraction in peer reviews",
        stub=False,
        md_filename="Liang et al (2024) - Monitoring AI-Modified Content Peer Reviews.md",
    ),
    dict(
        paper_key="kobak_etal_2024",
        authors_short="Kobak et al.",
        year=2024,
        title="Delving into ChatGPT Usage in Academic Writing through Excess Vocabulary",
        venue="arXiv:2406.07016",
        doi_or_url="https://arxiv.org/abs/2406.07016",
        design_class="Corpus",
        theme="Academic & scientific writing",
        outcome_focus="Excess vocabulary signatures of AI use",
        stub=False,
        md_filename="Kobak et al (2024) - Delving into ChatGPT Excess Vocabulary.md",
    ),
    dict(
        paper_key="si_yang_hashimoto_2025",
        authors_short="Si, Yang & Hashimoto",
        year=2025,
        title="Can LLMs Generate Novel Research Ideas?",
        venue="ICLR 2025",
        doi_or_url="https://arxiv.org/abs/2409.04109",
        design_class="RCT",
        theme="Academic & scientific writing",
        outcome_focus="Novelty of research ideas (LLM vs experts)",
        stub=False,
        md_filename="Si Yang Hashimoto (2025) - Can LLMs Generate Novel Research Ideas.md",
    ),
    dict(
        paper_key="russell_etal_2025",
        authors_short="Russell et al.",
        year=2025,
        title="AI Use in American Newspapers is Widespread, Uneven, and Rarely Disclosed",
        venue="arXiv:2510.18774",
        doi_or_url="https://arxiv.org/abs/2510.18774",
        design_class="Corpus",
        theme="Academic & scientific writing",
        outcome_focus="AI text prevalence in published newspaper articles",
        stub=False,
        md_filename="Russell et al (2025) - AI Use in American Newspapers.md",
    ),

    # ── Market consequences ──────────────────────────────────────────────────
    dict(
        paper_key="liu_wang_yang_2025",
        authors_short="Liu, Wang & Yang",
        year=2025,
        title="Generative AI and Content Homogenization: The Case of Digital Marketing",
        venue="SSRN 5367123",
        doi_or_url="https://doi.org/10.2139/ssrn.5367123",
        design_class="Corpus",
        theme="Market consequences",
        outcome_focus="Marketing content similarity post-LLM",
        stub=True,
        md_filename="Liu Wang Yang (2025) - GenAI and Content Homogenization Digital Marketing.md",
    ),

    # ── Synthesis / review ───────────────────────────────────────────────────
    dict(
        paper_key="sourati_etal_2026",
        authors_short="Sourati, Ziabari & Dehghani",
        year=2026,
        title="The Homogenizing Effect of LLMs on Human Expression and Thought",
        venue="Trends in Cognitive Sciences",
        doi_or_url="https://doi.org/10.1016/j.tics.2026.01.003",
        design_class="Review",
        theme="Synthesis / review",
        outcome_focus="Linguistic homogenization (review)",
        stub=False,
        md_filename="Sourati Ziabari Dehghani (2026) - Homogenizing Effect of LLMs on Human Expression.md",
    ),
]

THEME_ORDER = [
    "Anchor — homogenization",
    "Counterpoints / nuance",
    "Fixes / mechanisms",
    "Cross-model / cross-modal",
    "Academic & scientific writing",
    "Market consequences",
    "Synthesis / review",
]


# Best-guess total sample sizes (largest study / pooled N from each paper).
# Used for the "RCT + N>=50" curated-subset filter.
N_TOTAL = {
    "padmakumar_he_2024": 200,           # 100 InstructGPT + 100 Solo essays
    "doshi_hauser_2024": 293,            # writers
    "anderson_shah_kreminski_2024": 33,  # within-subject paired
    "moon_green_kushlev_2025": 1600,     # Study 3 largest
    "meincke_nave_terwiesch_2025": 288,  # 96 per arm across 3 arms (Exp 2A)
    "moon_etal_2026": 312388,            # natural experiment across 4 universities
    "lee_chung_2024": 383,               # largest single experiment (Exp 5)
    "boussioux_etal_2024": 234,          # solutions; 3,900 ratings
    "ashkinaze_etal_2025": 844,          # unique participants
    "girotra_etal_2023": 400,            # 200 human + 200 AI ideas
    "meincke_mollick_terwiesch_2024": 1100,  # 1000 AI ideas + 100 humans
    "liu_etal_2024": 61,
    "si_yang_hashimoto_2025": 228,       # reviewer × idea pairs (Test 1)
    # Corpus / review / theory papers: no human-subjects N
    "wenger_kenett_2025": None,
    "hintze_etal_2026": None,
    "liang_etal_2024": None,
    "kobak_etal_2024": None,
    "liu_wang_yang_2025": None,
    "sourati_etal_2026": None,
    "russell_etal_2025": None,    # corpus audit of 186K newspaper articles
}


def main():
    # Pull per-paper estimate counts from creativity_estimates_raw.py if available
    n_extracted = {}
    try:
        from creativity_estimates_raw import ESTIMATES
        from collections import Counter
        n_extracted = dict(Counter(e["paper_key"] for e in ESTIMATES))
    except ImportError:
        pass

    for p in PAPERS:
        p["n_outcomes_extracted"] = n_extracted.get(p["paper_key"], 0)
        p["n_total"] = N_TOTAL.get(p["paper_key"])
        # Curated subset: RCT design + N >= 50 (AI involved by definition for all in this collection)
        p["included_in_curated_subset"] = bool(
            p["design_class"] == "RCT"
            and p["n_total"] is not None
            and p["n_total"] >= 50
        )

    out_path = Path(r"C:\Users\greyes\Dropbox\Admin\website\ai-skill-atlas\src\creativity_papers.json")
    payload = {"theme_order": THEME_ORDER, "papers": PAPERS}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {out_path} ({len(PAPERS)} papers; {sum(n_extracted.values())} estimates linked)")

    from collections import Counter
    themes = Counter(p["theme"] for p in PAPERS)
    designs = Counter(p["design_class"] for p in PAPERS)
    print("\nThemes:")
    for t in THEME_ORDER:
        print(f"  {themes[t]:>2} | {t}")
    print("\nDesigns:", dict(designs))
    print("Stubs (no PDF):", sum(p["stub"] for p in PAPERS), "/", len(PAPERS))


if __name__ == "__main__":
    main()
