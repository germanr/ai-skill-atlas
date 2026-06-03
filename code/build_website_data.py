"""Build website data files from meta_analysis.xlsx + literature_effects.csv.

Outputs:
  1. papers_for_website.xlsx (in support_info/meta_analysis/) — source of truth Germán edits.
  2. src/papers.json — bundled into the React app.
  3. src/estimates.json — bundled into the React app.

Two sheets in the XLSX:
  - papers: one row per paper (~23 rows)
  - estimates: one row per effect-size estimate (~58 rows + 4 from "this paper")

Run with:
  python build_website_data.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

# ── paths ──────────────────────────────────────────────────────────────────
RESEARCH = Path(r"C:/Users/greyes/Dropbox/Research/ai-learning")
META_XLSX = RESEARCH / "support_info" / "meta_analysis" / "meta_analysis.xlsx"
LIT_CSV = RESEARCH / "support_info" / "meta_analysis" / "literature_effects.csv"
REG_DTA = RESEARCH / "data" / "regression_results_main.dta"
PDF_DIR = RESEARCH / "support_info" / "meta_analysis" / "pdf"

SITE = Path(r"C:/Users/greyes/Dropbox/Admin/website/ai-skill-atlas")
PAPERS_XLSX = RESEARCH / "support_info" / "meta_analysis" / "papers_for_website.xlsx"
PAPERS_JSON = SITE / "src" / "papers.json"
ESTIMATES_JSON = SITE / "src" / "estimates.json"

# ── helpers ────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Bastani et al. (2025) -> bastani_etal_2025"""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"\bet al\.?\b", "etal", s)
    s = re.sub(r"\band\b", "and", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    s = re.sub(r"_+", "_", s)
    return s


def extract_year(paper: str) -> int | None:
    m = re.search(r"\((\d{4})\)", paper)
    return int(m.group(1)) if m else None


def authors_short(paper: str) -> str:
    return re.sub(r"\s*\(\d{4}\)\s*$", "", paper).strip()


# ── manual mappings ────────────────────────────────────────────────────────
# For each paper, hand-curated columns that aren't cleanly derivable from
# the raw meta_analysis.xlsx. Germán can override these in the output XLSX.

PAPER_META = {
    "Barcaui (2025)": dict(
        authors_full="Andre Barcaui",
        venue="Working paper",
        country="Brazil",
        country_emoji="🇧🇷",
        population_category="Undergraduate",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="General knowledge",
        summary="Compares ChatGPT-assisted learning vs traditional learning on knowledge retention 45 days after a business administration course unit.",
        image_keywords="business school classroom Brazil",
        pdf_filename="Barcaui (2025) - ChatGPT as Cognitive Crutch.pdf",
    ),
    "Bastani et al. (2025)": dict(
        authors_full="Hamsa Bastani, Osbert Bastani, Alp Sungu, Haosen Ge, Özge Kabakcı, Rei Mariman",
        venue="Working paper",
        country="Turkey",
        country_emoji="🇹🇷",
        population_category="High school",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="Math",
        summary="High school students were randomized to GPT-4 (Base), GPT-4 with tutoring scaffolding (Tutor), or no AI for math practice. AI-only practice hurt unassisted exam performance.",
        image_keywords="math classroom high school students",
        pdf_filename="Bastani et al (2025) - Generative AI Without Guardrails Can Harm Learning.pdf",
    ),
    "De Simone et al. (2025)": dict(
        authors_full="Martín De Simone, Federico Tiberti, Maria Barron Rodriguez, Federico Manolio, Wuraola Mosuro, Eliot Dikoru",
        venue="Working paper",
        country="Nigeria",
        country_emoji="🇳🇬",
        population_category="High school",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="Language",
        summary="Nigerian senior secondary students got after-school sessions with an English-tutoring GPT-4 chatbot. Treatment group gained on English, AI knowledge, and digital skills; gains persisted at retention.",
        image_keywords="Nigerian students English class",
        pdf_filename="De Simone et al (2025) - From Chalkboards to Chatbots.pdf",
    ),
    "Fan et al. (2025)": dict(
        authors_full="Yizhou Fan, Luzhen Tang, Huixiao Le, Kejie Shen, Shufang Tan, Yueying Zhao, Yuan Shen, Xinyu Li, Dragan Gašević",
        venue="Working paper",
        country="China",
        country_emoji="🇨🇳",
        population_category="Undergraduate",
        lab_vs_field="Lab",
        incentives="Monetary fixed",
        learning_domain_primary="Writing",
        summary="University students wrote essays with ChatGPT vs traditional resources. AI users produced better essays but had lower knowledge retention afterward (\"metacognitive laziness\").",
        image_keywords="university students writing essay China",
        pdf_filename="Fan et al (2025) - Metacognitive Laziness.pdf",
    ),
    "Hausman et al. (2025)": dict(
        authors_full="Hausman et al.",
        venue="Working paper",
        country="Israel",
        country_emoji="🇮🇱",
        population_category="Undergraduate",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="Mixed",
        summary="Difference-in-differences across pre- and post-ChatGPT cohorts at an Israeli university, comparing grades across courses with different AI exposure.",
        image_keywords="university lecture hall Israel",
        pdf_filename="Hausman et al (2025) - GenAI Impact on Student Achievement.pdf",
    ),
    "Henkel et al. (2024)": dict(
        authors_full="Owen Henkel, et al.",
        venue="Working paper",
        country="Ghana",
        country_emoji="🇬🇭",
        population_category="Middle school",
        lab_vs_field="Field",
        incentives="None",
        learning_domain_primary="Math",
        summary="WhatsApp-based math tutor (Rori) deployed to grade 3–9 students in Ghana. RCT measured math gains over an academic term.",
        image_keywords="African students mobile phone learning",
        pdf_filename="Henkel et al (2024) - AI Math Tutor Ghana.pdf",
    ),
    "Kalam et al. (2025)": dict(
        authors_full="Kalam et al.",
        venue="Working paper",
        country="USA",
        country_emoji="🇺🇸",
        population_category="Graduate",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="General knowledge",
        summary="First-year Georgetown medical students randomized to ChatGPT vs traditional study for an immunology unit.",
        image_keywords="medical students library studying",
        pdf_filename="Kalam et al (2025) - ChatGPT as Learning Tool Medical Students.pdf",
    ),
    "Kazemitabaar et al. (2023)": dict(
        authors_full="Majeed Kazemitabaar, Justin Chow, Carl Ka To Ma, Barbara J. Ericson, David Weintrop, Tovi Grossman",
        venue="CHI 2023",
        country="Canada",
        country_emoji="🇨🇦",
        population_category="Middle school",
        lab_vs_field="Online",
        incentives="Monetary fixed",
        learning_domain_primary="Coding",
        summary="Children ages 10–17 learned Python with vs without OpenAI Codex code-generator assistance. Treatment showed higher gains during training; near-equal at retention.",
        image_keywords="kids learning to code laptop",
        pdf_filename="Kazemitabaar et al (2023) - AI Code Generators Novice Learners.pdf",
        setting_detail="Canada (recruited from coding camps in two North American cities), online via Google Meet; ages 10-17 (M=12.5)",
    ),
    "Kestin et al. (2025)": dict(
        authors_full="Greg Kestin, Kelly Miller, Anna Klales, Timothy Milbourne, Gregorio Ponti",
        venue="Working paper",
        country="USA",
        country_emoji="🇺🇸",
        population_category="Undergraduate",
        lab_vs_field="Lab",
        incentives="Course grade",
        learning_domain_primary="Science",
        summary="Harvard physics undergraduates received either AI-tutored instruction or active-learning instruction. AI tutor outperformed active learning on immediate post-test.",
        image_keywords="physics classroom Harvard students",
        pdf_filename="Kestin et al (2025) - AI Tutoring Outperforms Active Learning.pdf",
    ),
    "Kim et al. (2025)": dict(
        authors_full="Kim et al.",
        venue="Working paper",
        country="China",
        country_emoji="🇨🇳",
        population_category="Middle school",
        lab_vs_field="Field",
        incentives="None",
        learning_domain_primary="Math",
        summary="Quasi-experimental study at Squirrel AI learning centers in China, K-12 students. Compared AI-supported sessions to traditional tutoring.",
        image_keywords="China classroom tablets students",
        pdf_filename="Kim et al (2025) - GenAI Can Improve Performance Without Harming Learning.pdf",
    ),
    "Kreijkes et al. (2026)": dict(
        authors_full="Pia Kreijkes, et al.",
        venue="Working paper",
        country="England",
        country_emoji="🇬🇧",
        population_category="High school",
        lab_vs_field="Field",
        incentives="None",
        learning_domain_primary="Language",
        summary="UK Year 10 students used LLMs vs note-taking to study expository texts. Compared reading comprehension outcomes.",
        image_keywords="UK secondary school students reading",
        pdf_filename="Kreijkes et al (2026) - LLM Use and Note-Taking Reading Comprehension.pdf",
    ),
    "Kumar et al. (2023)": dict(
        authors_full="Kumar et al.",
        venue="Working paper",
        country="USA",
        country_emoji="🇺🇸",
        population_category="Adults general",
        lab_vs_field="Online",
        incentives="Monetary fixed",
        learning_domain_primary="Math",
        summary="MTurk adults solved SAT-style math problems with vs without GPT assistance, then took unassisted post-test.",
        image_keywords="online math test computer",
        pdf_filename="Kumar et al (2023) - Math Education with Large Language Models.pdf",
    ),
    "LearnLM Team (2025)": dict(
        authors_full="LearnLM Team (Google DeepMind)",
        venue="Working paper",
        country="UK",
        country_emoji="🇬🇧",
        population_category="High school",
        lab_vs_field="Field",
        incentives="None",
        learning_domain_primary="Science",
        summary="LearnLM (Gemini-based tutor) tested against static hints and human tutoring in UK secondary classrooms.",
        image_keywords="secondary school science class",
        pdf_filename="AI Team (2025) - AI Tutoring UK Classrooms.pdf",
    ),
    "Lehmann et al. (2024)": dict(
        authors_full="Matthias Lehmann, Philipp B. Cornelius, Fabian J. Sting",
        venue="Working paper",
        country="Netherlands",
        country_emoji="🇳🇱",
        population_category="Graduate",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="Coding",
        summary="Dutch graduate students learning Python; two studies used ChatGPT outages as instrumental variables to identify the causal effect of AI access.",
        image_keywords="programming students laptop coding",
        pdf_filename="Lehmann et al (2024) - When Does ChatGPT Harm Learning.pdf",
    ),
    "Lira et al. (2025)": dict(
        authors_full="Benjamin Lira, Joshua D. Greene, Hunter Gehlbach, Angela L. Duckworth",
        venue="Working paper",
        country="USA",
        country_emoji="🇺🇸",
        population_category="Adults general",
        lab_vs_field="Online",
        incentives="Monetary fixed",
        learning_domain_primary="Writing",
        summary="Prolific adults used an AI \"coach\" or \"crutch\" for writing tasks. Coaches (process-oriented) outperformed crutches (output-oriented), with persistent gains.",
        image_keywords="adult writing essay laptop",
        pdf_filename="Lira et al (2025) - Coach Not Crutch.pdf",
    ),
    "Nie et al. (2025)": dict(
        authors_full="Allen Nie, et al.",
        venue="Working paper",
        country="Global",
        country_emoji="🌍",
        population_category="Adults general",
        lab_vs_field="Online",
        incentives="None",
        learning_domain_primary="Coding",
        summary="Global online intro coding course; GPT-4 randomized as a tutoring aid. Measured learning gains across 146 countries.",
        image_keywords="online coding course laptop",
        pdf_filename="Nie et al (2025) - GPT Surprise Coding Class.pdf",
    ),
    "Vanzo et al. (2024)": dict(
        authors_full="Vanzo et al.",
        venue="Working paper",
        country="Italy",
        country_emoji="🇮🇹",
        population_category="High school",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="Language",
        summary="Italian technical-institute high school students used GPT-4 as a homework tutor for English as a second language.",
        image_keywords="Italian classroom English language",
        pdf_filename="Vanzo et al (2024) - GPT-4 as Homework Tutor.pdf",
    ),
    "Wang et al. (2025)": dict(
        authors_full="Wang et al.",
        venue="Working paper",
        country="USA",
        country_emoji="🇺🇸",
        population_category="Elementary",
        lab_vs_field="Field",
        incentives="None",
        learning_domain_primary="Math",
        summary="K-12 Title I tutors received an AI-augmented copilot during one-on-one tutoring sessions; measured student math outcomes.",
        image_keywords="elementary school tutoring math",
        pdf_filename="Wang et al (2025) - Tutor CoPilot.pdf",
    ),
    "Wiles et al. (2024)": dict(
        authors_full="Emma Wiles, Edward McFowland III, Hila Lifshitz-Assaf, Karim R. Lakhani, Katherine Kellogg, et al.",
        venue="Working paper",
        country="Global",
        country_emoji="🌍",
        population_category="Professional",
        lab_vs_field="Field",
        incentives="None",
        learning_domain_primary="General knowledge",
        summary="Boston Consulting Group consultants worldwide were randomized to use GPT-4 for knowledge tasks. Measured task performance and skill transfer.",
        image_keywords="consultants office laptop",
        pdf_filename="Wiles et al (2024) - GenAI as Exoskeleton.pdf",
    ),
    "Xu et al. (2025)": dict(
        authors_full="Xu et al.",
        venue="Working paper",
        country="China",
        country_emoji="🇨🇳",
        population_category="Undergraduate",
        lab_vs_field="Lab",
        incentives="Course grade",
        learning_domain_primary="General knowledge",
        summary="Chinese undergraduates in Educational Technology used GenAI with vs without metacognitive scaffolding.",
        image_keywords="Chinese university computer lab",
        pdf_filename="Xu et al (2025) - Metacognitive Support in GenAI Environments.pdf",
    ),
    "Chung et al. (2025)": dict(
        authors_full="Chung et al.",
        venue="Working paper",
        country="Taiwan",
        country_emoji="🇹🇼",
        population_category="High school",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="Math",
        summary="Taiwan high school students in 10 schools used either an LLM-guided adaptive RL tutor or a fixed-problem-sequence GenAI tutor.",
        image_keywords="Taiwan high school students tablets",
        pdf_filename="Chung et al (2025) - Personalized AI Tutors via LLM-Guided RL.pdf",
    ),
    "Liu et al. (2026)": dict(
        authors_full="Liu et al.",
        venue="Working paper",
        country="USA",
        country_emoji="🇺🇸",
        population_category="Adults general",
        lab_vs_field="Online",
        incentives="Monetary fixed",
        learning_domain_primary="Mixed",
        summary="Three online Prolific experiments testing whether AI assistance reduces task persistence on math and reading problems.",
        image_keywords="online study computer adult",
        pdf_filename="Liu et al (2026) - AI Assistance Reduces Persistence.pdf",
    ),
    "Shen and Tamkin (2026)": dict(
        authors_full="Shen and Tamkin",
        venue="Working paper",
        country="USA",
        country_emoji="🇺🇸",
        population_category="Adults general",
        lab_vs_field="Online",
        incentives="Monetary fixed",
        learning_domain_primary="Coding",
        summary="Experienced Python developers (≥1 yr experience) randomized to use AI vs no AI for coding tasks; measured skill formation.",
        image_keywords="programmer typing keyboard code",
        pdf_filename="Shen & Tamkin (2026) - How AI Impacts Skill Formation.pdf",
    ),
}


# ── Subagent verification corrections (one verification pass per paper) ────
# These override values in PAPER_META based on what each paper actually reports.
PAPER_CORRECTIONS = {
    "barcaui_2025": dict(
        venue="Social Sciences & Humanities Open",
        learning_domain_primary="General knowledge",  # AI/ML conceptual content; not coding
        incentives="None",
    ),
    "bastani_etal_2025": dict(
        venue="PNAS, 122(26), e2422633122",
        authors_full="Hamsa Bastani, Osbert Bastani, Alp Sungu, Haosen Ge, Özge Kabakcı, Rei Mariman",
        # PDF unchanged (PNAS PDF gated; SSRN preprint identical content).
    ),
    "fan_etal_2025": dict(
        year=2024,
        venue="British Journal of Educational Technology",
        title="Beware of metacognitive laziness: Effects of generative artificial intelligence on learning motivation, processes, and performance",
        pdf_filename="Fan et al (2024) - BJET - Metacognitive Laziness.pdf",
        incentives="None (flat compensation; no performance bonus)",
    ),
    "hausman_etal_2025": dict(
        authors_full="Naomi Hausman, Oren Rigbi, Sarit Weisburd",
        venue="CEPR DP 20206 / CESifo WP 11843",
        pdf_filename="Hausman et al (2025) - CESifo - GenAI Impact on Student Achievement.pdf",
        setting_detail="Israel, Hebrew University Business School; BA/MA/MBA courses across multiple faculties (2018-2024)",
    ),
    "henkel_etal_2024": dict(
        authors_full="Owen Henkel, Hannah Horne-Robinson, Nessie Kozhakhmetova, Amanda Lee",
        setting_detail="Ghana, grades 3-8 (11 Rising Academies schools; 5 treatment, 6 control)",
    ),
    "kalam_etal_2025": dict(
        venue="Cureus, 17(6):e85767",
        title="ChatGPT as a Learning Tool for Medical Students: Results From a Randomized Controlled Trial",
        authors_full="Kazi A. Kalam, Fadi D. Masoud, Adam Muntaser, Raghav Ranga, Xue Geng, Munish Goyal",
        pdf_filename="Kalam et al (2025) - Cureus - ChatGPT as Learning Tool Medical Students.pdf",
        incentives="None (gift-card drawing for participation, not performance)",
    ),
    "kumar_etal_2023": dict(
        year=2025,
        venue="AIED 2025 (Springer LNCS 15880)",
        title="Math Education With Large Language Models: Peril or Promise?",
        pdf_filename="Kumar et al (2025) - AIED - Math Education with Large Language Models.pdf",
        incentives="None (flat $3.30 MTurk pay)",
    ),
    "kestin_etal_2025": dict(
        venue="Scientific Reports",
        lab_vs_field="Field",
        incentives="Participation credit (not graded)",
    ),
    "kreijkes_etal_2026": dict(
        title="Effects of LLM use and note-taking on reading comprehension and memory: A randomised experiment in secondary schools",
        authors_full="Pia Kreijkes, Viktor Kewenig, Martina Kuvalja, Mina Lee, Jake M. Hofman, Sylvia Vitello, Abigail Sellen, Sean Rintel, Daniel G. Goldstein, David Rothschild, Lev Tankelevitch, Tim Oates",
        venue="Computers & Education (2026), 243, 105514",
        n_total=344,
    ),
    "learnlm_team_2025": dict(
        learning_domain_primary="Math",
        authors_full="LearnLM Team (Google & Eedi)",
    ),
    "lehmann_etal_2024": dict(
        setting_detail="Netherlands (Study 1) and Germany (Studies 2, 3); university students, Python programming",
        lab_vs_field="Mixed",
        study_design="Mixed (Study 1: quasi-experimental FE2SLS with outages as IV; Studies 2, 3: RCT)",
        n_total=289,  # 113 + 107 + 69 = 289 combined
        ai_tool="ChatGPT (Study 1: gpt-3.5-turbo-0613; Studies 2-3: gpt-3.5-turbo-0125)",
        incentives="Course grade (Study 1); €10 fixed + €1 per correct post-test answer (Studies 2-3)",
    ),
    "lira_etal_2025": dict(
        authors_full="Benjamin Lira, Todd Rogers, Daniel G. Goldstein, Lyle Ungar, Angela L. Duckworth",
        year=2026,
        title="Coach not crutch: Evidence that AI can improve writing skill despite reducing effort",
        venue="Working paper (arXiv v4, Feb 2026)",
        summary="Prolific adults practiced rewriting cover letters with an AI writing tool, without AI, with professional editor feedback, with Google Search, or by viewing an AI-generated example. Practicing with AI improved writing skill more than practicing without AI, with gains persisting one day later.",
        pdf_filename="Lira et al (2026) - Coach Not Crutch.pdf",
        incentives="None (flat Prolific pay)",
    ),
    "nie_etal_2025": dict(
        venue="ACM L@S 2025 (DOI 10.1145/3698205.3733960)",
        authors_full="Allen Nie, Yash Chandak, Miroslav Suzara, Ali Malik, Juliette Woodrow, Matt Peng, Mehran Sahami, Emma Brunskill, Chris Piech",
        title="The GPT Surprise: Offering Large Language Model Chat in a Massive Coding Class Reduced Engagement but Increased Adopters' Exam Performances",
        pdf_filename="Nie et al (2025) - ACM LaS - GPT Surprise Coding Class.pdf",
    ),
    "vanzo_etal_2024": dict(
        year=2025,
        venue="ACL 2025 (Long Papers, pp. 31119-31136)",
        authors_full="Alessandro Vanzo, Sankalan Pal Chowdhury, Mrinmaya Sachan",
        incentives="None",
        pdf_filename="Vanzo et al (2025) - ACL - GPT-4 as Homework Tutor.pdf",
    ),
    "wiles_etal_2024": dict(
        year=2026,
        venue="Nature Human Behaviour (forthcoming)",
        title="Generative AI and the Temporary Upskilling of Knowledge Workers",
        authors_full="Emma Wiles, Lisa Krayer, Mohamed Abbadi, Urvi Awasthi, Ryan Kennedy, Pamela Mishkin, Daniel Sack, Francois Candelon",
    ),
    "chung_etal_2025": dict(
        year=2026,
        venue="SSRN preprint (March 2026, id 6423358)",
        authors_full="Angel Tsai-Hsuan Chung, Botong Zhang, Ling-Chieh Kung, Hamsa Bastani, Osbert Bastani",
        learning_domain_primary="Coding",
        incentives="Certification valid for college applications",
    ),
    "wang_etal_2025": dict(
        population_category="Elementary",  # grades 3-8 spans both; primary skew is elementary
        setting_detail="USA, grades 3-8 (Title I schools)",
        n_total=1787,
        authors_full="Rose E. Wang, Ana T. Ribeiro, Carly D. Robinson, Susanna Loeb, Dora Demszky",
    ),
    "xu_etal_2025": dict(
        authors_full="Xu, X., Qiao, L., Cheng, N., Liu, H., & Zhao, W.",
        title="Enhancing self-regulated learning and learning experience in generative AI environments: The critical role of metacognitive support",
        venue="British Journal of Educational Technology (2025), 56, 1842-1863",
        lab_vs_field="Field",
        incentives="None",
    ),
    "liu_etal_2026": dict(
        n_total=1060,
        incentives="None (flat Prolific pay)",
    ),
    "shen_and_tamkin_2026": dict(
        incentives="None (flat $150)",
    ),
    "kazemitabaar_etal_2023": dict(
        incentives="None (flat $50 gift card)",
    ),
    "contractor_reyes_2026": dict(
        n_total=210,
        lab_vs_field="Lab",
        incentives="Lottery tickets ($100 each, 30 drawn) tied to test and essay performance",
    ),
}


# ── 3-part paper summaries (setup / empirical strategy / key results) ──────
# From 24 subagents that read each paper and produced structured summaries.
PAPER_SUMMARIES = {
    "contractor_reyes_2026": {
        "setup": "Field RCT with 210 Middlebury College undergraduates across two in-person sessions one week apart. Students were randomized to AI-allowed (logged-in ChatGPT GPT-4o) or AI-forbidden conditions during a 35-minute learning phase on one of three unfamiliar topics (blockchain, carbon capture, CRISPR), then wrote an analytical essay. Incentives: $50 attendance plus lottery tickets ($100 each, 30 drawn) tied to test correctness and essay quality.",
        "empirical_strategy": "ITT estimated via OLS of outcomes on the AI-allowed indicator, with randomization-strata dummies and double-lasso-selected controls. Robust SEs. A complementary TOT/2SLS specification instruments AI use with random assignment to recover the LATE for compliers.",
        "key_results": "AI access raised immediate Session 1 test scores by 0.25 SD and Session 2 retention test scores (one week later, no AI) by 0.27 SD, with largest gains for middle-performing students. Essay quality gains persisted only for 'augmentation' users who prompted AI to explain concepts; 'automation' users (who used AI to draft) saw Session 1 essay gains fade entirely.",
    },
    "barcaui_2025": {
        "setup": "120 undergraduate business administration students at UFRJ in Rio de Janeiro were randomized (n=60 per arm) to study AI/ML concepts (foundations, methods, applications, ethics) via either ChatGPT (GPT-4, no prompt-engineering guidance) or traditional resources (notes, library databases, non-AI search). Each participant prepared a 10-minute peer-group presentation over two weeks. Participation was voluntary with no course-grade incentive.",
        "empirical_strategy": "Independent-samples t-test on a surprise delayed 20-item MCQ retention test 45 days after the intervention; ANCOVA adjusts for self-reported study time. Three-phase RCT (Oct 2024-Jan 2025) with attrition: 85 of 120 completed the retention test (70.8% follow-up).",
        "key_results": "AI-assisted students scored substantially lower than traditional learners on retention (57.5% vs 68.5%, d=-0.68, 95% CI [-1.12, -0.24], p=.002). They also spent ~45% less time studying; the AI penalty survives time-on-task adjustment.",
    },
    "bastani_etal_2025": {
        "setup": "Field RCT with ~1,000 Turkish high-school students (grades 9-11) at a single school, randomized at the classroom level across three arms: GPT Base (unrestricted GPT-4), GPT Tutor (GPT-4 with Socratic guardrails and teacher-designed prompts), or control (textbook only). Students completed four 90-minute sessions, each with a lecture, AI-assisted practice, and an unassisted closed-book exam. Performance counted toward course grades.",
        "empirical_strategy": "OLS at the student-session level (N=2,848) regressing normalized 0-1 grades on GPT Base and GPT Tutor indicators (control omitted), with prior GPA and session/grader/grade-level/teacher fixed effects, classroom-clustered SEs. Pre-registered primary outcome is the unassisted exam.",
        "key_results": "On assisted practice, GPT Base raised grades by 0.48 SD and GPT Tutor by 1.26 SD. But on the unassisted exam, GPT Base hurt performance by -0.19 SD (p<0.05) while GPT Tutor was essentially zero. Students used GPT Base as a 'crutch' (copying answers) and overestimated their own learning.",
    },
    "de_simone_etal_2025": {
        "setup": "Student-level RCT in 9 Nigerian public secondary schools in Benin City. 1,328 first-year senior secondary students (~age 15) randomized (657 treatment, 671 control); 759 completed endline. Treatment: 12 after-school sessions (90 min, twice weekly for 6 weeks) in school computer labs using Microsoft Copilot (GPT-4) as a virtual English tutor with teacher-guided prompt toolkit. Control: business-as-usual classroom instruction. No participation incentives reported.",
        "empirical_strategy": "ITT via OLS with school fixed effects and second-term baseline exam score as a control; robust SEs. Robustness via Lee bounds, inverse-probability weighting, and value-added IV/LATE specifications using attendance days.",
        "key_results": "English skills rose by 0.238 SD and total weighted endline by 0.31 SD. Effects persisted on the third-term school exam (broader curriculum, 0.206 SD). Larger effects for female, higher-baseline, and higher-SES students; benefits across the whole distribution.",
    },
    "fan_etal_2025": {
        "setup": "Lab study at Peking University with 117 university students (mean age 22.6; 55% undergraduate, 45% graduate; all L1 Chinese / English L2). Four-arm design with a shared baseline 2-hour reading-and-writing task followed by a 1-hour revision phase under one of four conditions: CN no support (n=30), AI = ChatGPT 4.0 with guardrails restricting it to task content (n=35), HE = human academic-writing expert (n=25), or CL = AI-powered checklist feedback tool (n=27). No course-grade incentive.",
        "empirical_strategy": "Random assignment to four arms; ANOVA + Tukey HSD on essay-score improvement (post-revision minus pre-revision), knowledge gain (10-item MCQ on AI in education), and knowledge transfer (10-item MCQ on AI in healthcare). Process mining of trace data via first-order Markov models.",
        "key_results": "AI group's essay improvement significantly exceeded all three other arms (d≈0.73 vs CN; F=4.55, p=0.005). But no significant group differences in knowledge gain (d≈-0.05) or knowledge transfer. Trace-data process mining showed AI students looped through tight 'revising-via-ChatGPT' patterns rather than reading and evaluating - the 'metacognitive laziness' the title warns of.",
    },
    "hausman_etal_2025": {
        "setup": "Administrative panel data from a large Israeli research university (Hebrew University Business School) covering ~36,000 BA/MA/MBA students in ~6,000 courses across 6 academic years (2018-2019 through 2023-2024), spanning ChatGPT's November 2022 rollout. Treatment: 'AI-compatible' courses (≤60% of grade from in-class/lab work); control: AI-incompatible courses (≥90%). A 91-student survey shows ChatGPT adoption rising from ~30% in 2022-23 to ~80% in 2023-24.",
        "empirical_strategy": "Difference-in-differences event study with student fixed effects, comparing within-student grade changes across AI-compatible vs AI-incompatible courses before/after Nov 2022. Robustness via propensity-score matching. A cohort DiD isolates AI-specific human capital using cohort-2022-23 vs 2021-22 students' second-year advanced-course performance.",
        "key_results": "AI availability raised AI-compatible course grades by 0.6-1.5 points on the 0-100 scale (0.97 in 2022-23, 1.48 in 2023-24). Effects concentrated at the lower tail: 25th-percentile grades rose 2-3 points and failure rates dropped ~30-37%. Grade distribution compresses, eroding signal value. AI exposure in intro courses raised later AI-compatible grades but reduced AI-incompatible advanced-course grades, suggesting some basic human capital substitution.",
    },
    "henkel_etal_2024": {
        "setup": "School-level RCT in 11 Rising Academies schools in Ghana with ~500 students in grades 3-8 (5 treatment / 6 control schools; 477 students with baseline + endline). Treatment received two 30-min weekly sessions during study hall with Rori, a WhatsApp-based AI math tutor offering ~500 GPF-aligned micro-lessons. ~8-month intervention (Feb-Aug 2023). Control: regular math instruction without Rori. Marginal cost ~$5/student.",
        "empirical_strategy": "DiD using growth scores (endline minus baseline raw score) on a 35-item math assessment. Independent-samples t-test on growth; Cohen's d with pooled SD (Morris 2008). Baseline equivalence verified on test scores, gender, and age.",
        "key_results": "Treatment growth was 5.13 points vs control's 2.12 (d=0.36, p<0.001), roughly equivalent to an additional year of schooling. Some ceiling effects observed for higher-grade students.",
    },
    "kalam_etal_2025": {
        "setup": "Single-site prospective RCT at Georgetown University School of Medicine, April 2025. 33 first-year MD students randomized to three arms: ChatGPT-4.0 (n=10), external resources (Google, PubMed) excluding AI (n=12), and institutional resources (lecture materials, course slides, n=11). All completed a 15-min proctored 10-item MCQ on pathology, pharmacology, physiology, and anatomy with their assigned resource. One week later they retook the identical quiz with no resource access. Incentive: weekly $100 gift card drawing.",
        "empirical_strategy": "One-way ANOVA across the three groups with Tukey HSD pairwise comparisons; Fisher's exact for categorical outcomes with Benjamini-Hochberg correction. Eta-squared effect sizes. Post hoc power analysis.",
        "key_results": "Week 1 with resources: A=9.60, B=9.08, C=6.64 (p<0.001); ChatGPT and external resources both beat institutional resources, but A vs B not significant. Week 2 retention (no resources): A=6.20, B=5.58, C=4.36 (p=0.118, not significant; Cohen's d≈0.93 for A vs C). Conclusion: ChatGPT improved short-term performance but provided no significant retention advantage.",
    },
    "kazemitabaar_etal_2023": {
        "setup": "Lab RCT in Canada with 69 novice coders ages 10-17 (mean 12.5) recruited from coding camps. None had prior text-based programming. Three-week, ten-session study learning Python via the Coding Steps platform. Codex group (n=33) had unrestricted OpenAI Codex during training only; Baseline group (n=36) had no AI. $50 gift-card compensation. Outcomes at training, immediate post-test (1 day later), and retention (1 week later) - all on Python authoring and modifying tasks.",
        "empirical_strategy": "Matched-groups design: pairs balanced on Scratch pre-test scores, random assignment within pairs. Two-rater independent coding (79% full agreement). Independent-samples t-tests with Cohen's d; Bonferroni-adjusted alpha.",
        "key_results": "Training-phase authoring (with AI): Codex 80.1% vs baseline 44.4% (d=1.67). But on the immediate unassisted post-test, no difference (d=0.05 authoring, d=0.01 modifying). On 1-week retention, modest non-significant Codex advantages (d=0.41 modifying, d=0.38 MCQ overall). Codex-High learners benefited most, suggesting prior competency moderates AI's learning effects.",
    },
    "kestin_etal_2025": {
        "setup": "Crossover RCT in Harvard's PS2 introductory physics for life sciences, Fall 2023, N=194 of 233 enrolled. Two lessons (surface tension, fluid flow) in weeks 9-10. AI tutor 'PS2 Pal' (GPT-4 with engineered system prompts, scaffolded sequential problem-guidance, and pre-written step-by-step solutions to mitigate hallucination) versus in-class active learning (peer instruction, group work, instructor feedback). Both arms used identical content. Pre/post-test performance did not affect course grades (participation credit only).",
        "empirical_strategy": "Within-student crossover: each student experienced both conditions. Randomization at peer-instruction-group level (2-3 students). Mann-Whitney rank-sum tests on post-test scores, linear regression controlling for pre-test/midterm/FCI/topic, and quantile regression to address ceiling effects.",
        "key_results": "AI group post-test median was 4.5 vs in-class 3.5 (pre-test 2.75); median learning gains more than double with AI (z=-5.6, p<10^-8). Linear regression effect size 0.63 SD; quantile regression (ceiling-corrected) 0.73-1.3 SD. AI median time-on-task was 49 min vs 60 min in-class. 83% rated AI explanations as good as or better than human instructors.",
    },
    "kim_etal_2025": {
        "setup": "18,904 K-12 students (mean grade 6.7, median 7) using Squirrel AI, a Chinese commercial K-12 math platform at brick-and-mortar learning centers. The platform introduced a post-solution GenAI tutor (activated only after a student submits an answer, for debriefing). Sample yields 2.1 million student-day observations in 2024. A capacity-constrained rollout meant not all tablets at a center were upgraded.",
        "empirical_strategy": "Two-way fixed effects DiD with student and date fixed effects, exploiting quasi-random rollout: treated = ever received AI-tutor access; control = never used AI-tutor mode. SEs clustered at the student level. Event-study for parallel-trends checks; IV using capacity-driven AI availability.",
        "key_results": "Treated students solve ~35.8% more problems daily (log coefficient 0.31, SE 0.01), spend 3.9% less time per problem, and have correctness rates 2.6 percentage points higher (~3.6% relative). Gains concentrated among low-baseline-performance students; diminishing returns to very intensive AI use; long-run correctness trajectories steeper for treated, consistent with skill accumulation.",
    },
    "kreijkes_etal_2026": {
        "setup": "Pre-registered RCT in 7 English secondary schools with Year 10 students (ages 14-15). 405 recruited, 344 analyzed. Two sessions: a learning session studying two history passages under different conditions, then a test session three days later assessing literal retention, comprehension, and free recall. Three conditions: LLM only (GPT-3.5 Turbo via Azure, unrestricted), Notes only, and LLM + Notes. No incentives.",
        "empirical_strategy": "Mixed within- and between-participant design. Group 1 (n=184) experienced LLM vs Notes; Group 2 (n=160) LLM vs LLM+Notes. Passage and condition order randomized. Linear mixed-effects models with student random effects; Cohen's d from paired differences.",
        "key_results": "Notes significantly outperformed LLM-only on all three outcomes: literal retention d=0.44, comprehension d=0.38, free recall d=0.21. LLM+Notes also beat LLM-only on retention and comprehension (d=0.13-0.14) but not free recall. Yet students preferred the LLM, rated it more helpful, found it less effortful, and spent less time with it.",
    },
    "kumar_etal_2023": {
        "setup": "Pre-registered online experiment with 1,202 MTurk adults on SAT-style math. 2x3 between-subjects design: order (Try First vs See Answer First) crossed with explanation type (Answer only / Stock GPT-4 / Customized GPT-4 with hidden tutor pre-prompt encoding problem-solving strategies). Practice phase on 2 of 4 SAT question types, then a 1-minute Snake distractor, then a test phase on the same question types but with altered numbers, no assistance. Flat $3.30 payment.",
        "empirical_strategy": "Mixed-effects logistic regression of per-question test response, with main effects and interaction of order x explanation type, random effects for participants, fixed effects for question type. Pre-planned contrasts compare cells via z-tests. Free-text strategy descriptions coded via manual labels then GPT-4 few-shot classification.",
        "key_results": "LLM explanations boosted test accuracy. Largest gains in Try First: ~50% correct in Answer only vs >67% in Stock LLM (z=-3.46, p<0.001) and Customized LLM (z=-4.20, p<0.001). In See Answer First, only Customized LLM beat Answer only marginally. Gains driven by participants adopting LLM-shown strategies. LLM-condition participants reported lower perceived difficulty and >85% felt they learned something.",
    },
    "learnlm_team_2025": {
        "setup": "Exploratory RCT (May-June 2025, 7 weeks) on the Eedi math platform with N=165 UK Year 9-10 students across 5 secondary schools. The intervention integrated LearnLM (Gemini 2.0 Flash fine-tuned for pedagogy) into chat-based tutoring. 17 expert human tutors supervised LearnLM, approving, editing, or rewriting each drafted message before it reached students. Triggered when a student missed the first question in a study unit. Conditions: static pre-written hints, human tutor alone, or LearnLM (human-supervised).",
        "empirical_strategy": "Two-stage randomization: students first assigned to static hints vs interactive tutoring; tutoring arm further randomized to human-only vs LearnLM. Three outcomes: mistake remediation, misconception resolution, knowledge transfer (correct on first question of next study unit). Bayesian regression with weakly informative priors; posterior means and 95% credible intervals.",
        "key_results": "LearnLM tutors approved 74.4% of drafted messages without edits; zero harmful content and only 5 factual errors across 3,617 messages. Knowledge transfer: LearnLM 66.2% vs human tutor 60.7% (+5.5pp, 93.6% posterior probability of advantage) and vs static hints 56.2% (>99.9% probability). Mistake remediation: LearnLM 93.0% vs static hint 65.4%.",
    },
    "lehmann_etal_2024": {
        "setup": "Three studies. Study 1 is a field study of two graduate Python programming courses at a Dutch university (Spring 2023, N=113 students, 6,594 student-question observations) where ChatGPT was freely available. Studies 2 and 3 are pre-registered incentivized lab experiments at a German university (10 EUR fixed + 1 EUR per correct post-test question), teaching Python via a pre-test, ~45-min learning phase, and 20-item post-test. Treatment: unrestricted ChatGPT access. Study 3 enables copy-paste (N=69); Study 2 disables it (N=107).",
        "empirical_strategy": "Study 1: FE2SLS at the student-question level instrumenting ChatGPT similarity (and cumulative similarity over prior questions) with contemporaneous and cumulative ChatGPT outage minutes. Studies 2 & 3: OLS regressions of post-test on treatment indicator with pre-registered covariates; pooled analyses identify substitutive vs complementary AI use.",
        "key_results": "Study 1 (FE2SLS): higher cumulative ChatGPT use reduces grade on subsequent questions; the contemporaneous boost disappears under IV. Studies 2 & 3: no significant ATE on post-test (Study 2 d≈0.25, Study 3 d≈0.42). Exploratory pooled results: substitutive use (asking for solutions, facilitated by copy-paste) increases topic volume but lowers per-topic understanding; complementary use (asking for explanations) increases understanding. LLMs widen gap between low- and high-prior-knowledge students.",
    },
    "lira_etal_2025": {
        "setup": "Five pre-registered Prolific studies with US adults examining whether practicing cover-letter writing with a custom GPT-based AI tool helps or hinders writing skill. All participants completed baseline pretest, lesson on five writing principles, then random assignment to practice conditions, then a no-AI test (and 1-day follow-up in Studies 2 and 5). Study 2 (N=2,238) compared practice-with-AI vs practice-without-AI; Study 4 (N=2,997) added expert-editor feedback and Google Search arms; Study 5 (N=2,003) added an example-only condition.",
        "empirical_strategy": "RCT with random assignment. Writing quality scored by GPT-4o averaging five-principle ratings (alpha=.81), validated against human RA ratings (r=.70). Effects reported as Cohen's d; BH-corrected heterogeneity by demographics and baseline skill.",
        "key_results": "Forecasters expected AI to hinder learning (65% vs 35%); the opposite held. Study 2: AI-practice beat no-AI practice on the test phase (d=0.38) and at 1-day follow-up (d=0.41) despite less effort. Study 4: AI-practice beat editor feedback (d=0.20) and Google (d=0.46). Study 5: merely viewing an AI-generated example improved skill as much as practicing with AI (d=0.37 vs no-AI practice). Mechanism: AI teaches by example.",
    },
    "nie_etal_2025": {
        "setup": "Stanford's free online Code-in-Place 2023 intro Python course. From 8,762 enrollees, 5,831 were active after week 1 and randomized 60/40 (3,581 treated / 2,250 control) across 146 countries. At the start of week 4, treated students received an email and a sidebar button granting access to a custom GPT-4 chat interface with system prompts designed to prevent direct solution-giving. Outcomes: optional 4-hour midterm exam in week 6, weekly homework, section attendance. Only 14.2% of treated actually used the GPT-4 interface.",
        "empirical_strategy": "Two estimands: (1) Advertisement Effect / ITT via difference-in-means; (2) LATE for adopters with treatment as instrument for GPT-4 usage. Missing exam scores handled via MCAR (ignore) or MAR (Ridge regression imputation with 2-fold cross-fitting). Bonferroni-corrected p-values; BCa bootstrap CIs.",
        "key_results": "Advertisement reduced exam participation by 4.3 pp (44.1% vs 48.5%, p=.020) with parallel declines in week-6 homework and attendance. Effect reverses for low-HDI countries (+14.8 pp participation). LATE for adopters with imputation: +6.86 pp exam score (90% CI [0.30, 14.13], ES=0.40). Adopters skew older, male, higher prior section attendance, and from lower-HDI countries.",
    },
    "vanzo_etal_2024": {
        "setup": "RCT at Istituto Pindemonte, a technical institute in Verona (Italy). Four English-as-L2 classes taught by the same teacher: two 3rd-year (n=39) and two 5th-year (n=37); N=76 total. 3rd-year homework was objective grammar exercises; 5th-year was open-ended essay/literature questions. Treatment replaced standard homework with interactive GPT-4 (gpt-4-0125-preview) sessions via a custom web platform; control submitted standard homework on the same platform. 6-8 week intervention. No incentives (voluntary).",
        "empirical_strategy": "Stratified randomization within class by self-reported English GPA. Teacher blind to condition. Pre/post-tests with 24 MCQ items. Cohen's d via one-sided t-tests pooled and by cohort. Weekly Likert engagement questionnaires; OLS regression of learning gains on condition, words typed, and year.",
        "key_results": "Pooled learning gain d=0.251 (not significant). 3rd year d=0.603 (p=0.087, marginal). 5th year d=-0.004 (null). Treatment students reported much higher interestingness (d=0.59) and engaged much more (words-typed d=1.42). Weaker students gained more, consistent with personalized scaffolding. Hallucination rate <1%.",
    },
    "wang_etal_2025": {
        "setup": "Field RCT (Mar-May 2024) with FEV Tutor and a large southern US school district. Nine Title I schools, 1,787 students in grades 3-8 (80% Hispanic, 67% economically disadvantaged) receiving virtual math tutoring; 874 full-time tutors. Treatment tutors received access to Tutor CoPilot, an LLM-based tool built on the Bridge method (GPT-4) that generates real-time pedagogical suggestions during sessions. Final analytic sample: 4,136 sessions with 550,000+ chat messages.",
        "empirical_strategy": "Pre-registered ITT regression of session-level outcomes (primary: exit ticket passed) on tutor-level treatment indicator, controlling for student covariates and school-by-grade fixed effects, with SEs clustered at the student-tutor pair. Heterogeneity by tutor quality and experience terciles. 2SLS for TOT. NLP classifiers measure pedagogical strategy use.",
        "key_results": "ITT: students of treated tutors are 4 pp more likely to pass exit tickets (62% to 66%, p<0.01). 9 pp gain for lowest-rated tutors and 7 pp for least-experienced. TOT (using vs access): 14 pp. Treated tutors used more 'prompt to explain' and 'guiding questions' and less 'give answer' language. Cost ~$20/tutor/year.",
    },
    "wiles_etal_2024": {
        "setup": "RCT with BCG consultants globally (pre-registered March 2024; ran late March-early April 2024). 986 consultants allocated, 487 in the analytic sample. Treatment: 15-20 min training on ChatGPT (GPT-4) prompting plus access during tasks. Control: equivalent training on Google, Stack Overflow, Khan Academy. 44 BCG data scientists completed the tasks without AI as a benchmark. Each participant randomly assigned 2 of 3 90-min data science tasks (coding, statistics, prediction) designed so ChatGPT alone cannot solve them.",
        "empirical_strategy": "RCT with random assignment stratified on gender, location, role, coding skills, college degree, and prior ChatGPT-for-coding experience. Scores normalized so 0 = average data scientist benchmark. Huber-White robust SEs. Lee bounds for differential attrition.",
        "key_results": "Treated workers scored 49, 20, and 18 percentage points higher than control on coding, statistics, and prediction tasks. On coding, the treated 95% CI included the data scientist benchmark. But on the post-experiment knowledge test (without ChatGPT), no improvement: 'exoskeleton' gains vanish when AI is removed. Treated workers also became more overconfident in ChatGPT and worse at predicting which problems GPT-4 can solve.",
    },
    "xu_etal_2025": {
        "setup": "Quasi-experiment with 68 Chinese undergraduate sophomores (avg age 19.4) in Educational Technology at a Chinese university, all enrolled in 'Instructional Technology and Media' course. Randomly assigned to experimental (N=35, ChatGPT 4.0 + paper-based metacognitive scaffolding prompts) vs control (N=33, ChatGPT 4.0 alone). Task: 4-week interdisciplinary K-12 lesson design assignment integrating math/IT/biology. Participants told data would not affect course grades (no incentives).",
        "empirical_strategy": "Pretest-posttest design. Academic achievement test (40% theory MC/short-answer, 60% practical instructional design, graded by educators) analyzed via ANCOVA with pretest as covariate. SRL via Barnard et al. (2008) questionnaire across six dimensions; t-tests. Cognitive load and technology acceptance via Likert scales. Semi-structured interviews thematically coded.",
        "key_results": "Academic achievement: experimental d=0.36 vs control (F=3.94, p=0.051, marginal). SRL: significant gains in task strategy (d=0.69) and self-evaluation (d=0.43); the control group showed declines across five SRL dimensions. Lower cognitive load (d=-0.47) and higher perceived usefulness in experimental. Interviews showed deeper reflection and critical evaluation of ChatGPT outputs in the scaffolded condition.",
    },
    "chung_etal_2025": {
        "setup": "Five-month 'AI for Python Learning' course (Jan-Jun 2025) in partnership with Taipei City Government across 10 Taipei high schools (8 public, 2 private). 1,047 enrolled; 770 met pre-registration inclusion criteria. Platform combined lecture videos, browser-based coding practice, and an LLM-powered chatbot tutor (both arms); copy-paste was disabled. Students earned a government-endorsed certificate (valid for college applications) by completing modules and passing a proctored final written exam.",
        "empirical_strategy": "Individual-level RCT. Treatment: POMDP-based reinforcement-learning algorithm that adaptively sequences practice problem difficulty using particle-filter belief estimation over knowledge state; uses LLM-derived signals from chat and code-edit traces. Control: fixed easy-to-hard sequence. Same chatbot tutor in both arms. ITT via OLS on standardized final-exam scores. Pre-registered, IRB-approved.",
        "key_results": "Adaptive sequencing raised exam performance by 0.156 SD without controls and 0.150 SD with baseline controls and FE — about 6-9 months of additional schooling. Heterogeneity: beginners gained 0.215 SD; students with prior Python skill gained ~0 SD. Lower-tier schools gained 0.173 SD; higher-tier 0.039 SD. Mediation: engagement (time, attempts) accounts for essentially the full effect; chat quality (LLM-as-judge) was significantly higher in treatment.",
    },
    "liu_etal_2026": {
        "setup": "Three pre-registered RCTs on Prolific (US adults). Exp 1 (N=307 post-exclusions) gives 12 fraction problems with a GPT-5 sidebar (or no AI) followed by 3 unassisted test problems. Exp 2 (N=585) replicates with a pretest-based exclusion and a matched control sidebar (worked pretest solutions) to remove interface asymmetry. Exp 3 (N=168) extends to SAT reading comprehension (5 learning + 3 test passages); control sidebar contains test-taking tips. AI was pre-prompted with each problem and solution, allowing one-word answer requests. Skipping was costless. Pay: $2.60-$3.40.",
        "empirical_strategy": "Random assignment to AI vs control at study entry. Primary outcomes: mean solve rate and skip rate on the final 3 unassisted test problems. Two-sample t-tests on participant means with Cohen's d. Exp 2 adds heterogeneity by self-reported AI usage type (direct answer vs hints vs no use).",
        "key_results": "AI access lowers unassisted solve rates: Exp 1 d=-0.42, Exp 2 d=-0.19, Exp 3 d=-0.42. Skip rates rise (Exp 1 d=0.25, Exp 3 d=0.42). Decline concentrates among the 61% who used AI for direct solutions; hint-users (27%) and non-users (12%) look like controls. Effects emerge after only ~10-15 minutes of exposure.",
    },
    "shen_and_tamkin_2026": {
        "setup": "Between-subjects online RCT with 52 experienced Python developers (≥1 year Python, no prior Trio library experience) recruited through a crowdwork platform. Flat $150 fee. After a warm-up coding task to calibrate Python familiarity, participants had up to 35 minutes to complete two Trio asynchronous-programming tasks on an online coding-interview platform. Treatment (n=26): chat-based GPT-4o coding assistant prompted to produce full correct solutions. Control (n=26): no AI. Both groups then took a 14-question, 27-point Trio quiz with no AI permitted.",
        "empirical_strategy": "Pre-registered between-subjects randomization with balance on coding experience, Python frequency, prior asyncio use, and async-familiarity score. Primary outcomes: Trio quiz score and task completion time; treatment effects as differences in means and Cohen's d, with one specification controlling for warm-up time. Exploratory analyses decompose quiz scores by question type and qualitatively annotate screen recordings into AI-interaction patterns.",
        "key_results": "AI assistance reduced quiz scores by 4.15 points on the 27-point quiz (Cohen's d=0.738, p=0.010). No significant difference in task completion time; all 26 AI participants finished both tasks while 4 of 26 controls did not. Control outperformed treatment across all experience strata. Three of six AI-interaction patterns (involving cognitive engagement) preserved learning; full-delegation patterns showed productivity gains but worst learning.",
    },
}


# ── Per-estimate overrides (from version-refresh verification) ──────────────
# Override specific fields per estimate_id (e.g., refresh SE units, n_total)
ESTIMATE_OVERRIDES = {
    # Bastani: PNAS version uses SD-standardized SEs throughout; current xlsx
    # has Table 1 raw SEs for the practice estimates. Override to SD units.
    "bastani_etal_2025__est1": {"se": 0.108, "n_total": 2848},
    "bastani_etal_2025__est2": {"se": 0.112, "n_total": 2848},
    "bastani_etal_2025__est3": {"n_total": 2848},
    "bastani_etal_2025__est4": {"n_total": 2848},
    # Nie: refresh exam participation SE/CI to match Figure 3 caption
    "nie_etal_2025__est41": {"se": 1.34, "ci_lower": -7.10, "ci_upper": -1.82},
}


# ── ADDITIONAL ESTIMATES (subgroup heterogeneity, alternative arms, etc.) ───
# Each entry is a full estimate dict. These get flagged is_subgroup=True so
# the React app can hide them by default behind a toggle.
def _ce(study_label, paper_key, effect, se, treatment, control, outcome,
        timing="immediate", domain="General knowledge",
        comparison="ai_vs_bau", outcome_with_ai=False, n=None,
        ci_lo=None, ci_hi=None, subgroup=""):
    """Helper to build an additional estimate dict."""
    return dict(
        study_label=study_label,
        paper_key=paper_key,
        effect_size_sd=effect,
        se=se,
        ci_lower=ci_lo if ci_lo is not None else (effect - 1.96 * se if (effect is not None and se is not None) else None),
        ci_upper=ci_hi if ci_hi is not None else (effect + 1.96 * se if (effect is not None and se is not None) else None),
        learning_domain=domain,
        outcome=outcome,
        outcome_timing=timing,
        n_treatment=None,
        n_control=None,
        n_total=n,
        treatment=treatment,
        control=control,
        notes="Subgroup / alternative arm comparison extracted by verification subagent.",
        included_in_curated_subset=False,
        quality_label="High",
        quality_flags="none",
        comparison_type=comparison,
        outcome_with_ai=outcome_with_ai,
        is_own_paper=False,
        is_subgroup=True,
        subgroup=subgroup,
    )


ADDITIONAL_ESTIMATES = [
    # ── Contractor & Reyes — Session 2 essay quality components ────────────
    _ce("Contractor and Reyes (2026), Writing style & clarity (S2 essay)",
        "contractor_reyes_2026", 0.342, 0.138,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: writing style & clarity (S2)",
        timing="delayed", n=197, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Evidence & examples (S2 essay)",
        "contractor_reyes_2026", 0.251, 0.152,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: evidence & examples (S2)",
        timing="delayed", n=197, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Structure & organization (S2 essay)",
        "contractor_reyes_2026", 0.173, 0.142,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: structure & organization (S2)",
        timing="delayed", n=197, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Relevance to prompt (S2 essay)",
        "contractor_reyes_2026", 0.162, 0.168,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: relevance to prompt (S2)",
        timing="delayed", n=196, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Factual accuracy (S2 essay)",
        "contractor_reyes_2026", 0.128, 0.148,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: factual accuracy (S2)",
        timing="delayed", n=197, subgroup="Essay component"),

    # ── Barcaui — topic and prior-AI-experience subgroups ────────────────
    _ce("Barcaui (2025), Technical topics",
        "barcaui_2025", -0.92, None,
        "ChatGPT (GPT-4)", "Traditional study (no AI)",
        "Retention test (Technical Topics subset)",
        timing="delayed", n=85, ci_lo=-1.36, ci_hi=-0.48,
        subgroup="Topic: Technical"),
    _ce("Barcaui (2025), Ethics topics",
        "barcaui_2025", -0.45, None,
        "ChatGPT (GPT-4)", "Traditional study (no AI)",
        "Retention test (Ethics and Society subset)",
        timing="delayed", n=85, ci_lo=-0.89, ci_hi=-0.01,
        subgroup="Topic: Ethics"),
    _ce("Barcaui (2025), Other topics",
        "barcaui_2025", -0.60, None,
        "ChatGPT (GPT-4)", "Traditional study (no AI)",
        "Retention test (Other Topics subset)",
        timing="delayed", n=85, ci_lo=-1.04, ci_hi=-0.16,
        subgroup="Topic: Other"),
    _ce("Barcaui (2025), Recent/initial AI users",
        "barcaui_2025", -0.89, None,
        "ChatGPT (GPT-4)", "Traditional study (no AI)",
        "Retention test (recent/initial AI users)",
        timing="delayed", n=26, ci_lo=-1.56, ci_hi=-0.22,
        subgroup="Prior AI exposure: Recent"),
    _ce("Barcaui (2025), Frequent AI users",
        "barcaui_2025", -0.41, None,
        "ChatGPT (GPT-4)", "Traditional study (no AI)",
        "Retention test (frequent AI users)",
        timing="delayed", n=53, ci_lo=-0.90, ci_hi=0.08,
        subgroup="Prior AI exposure: Frequent"),

    # ── Bastani — heterogeneity and pairwise arm comparison ──────────────
    _ce("Bastani et al. (2025), GPT Base, below-median GPA (unassisted exam)",
        "bastani_etal_2025", -0.152, 0.087,
        "GPT Base", "No AI access",
        "Normalized grade on unassisted exam (below-median GPA)",
        domain="Math", n=2848, subgroup="Prior achievement: Below median"),
    _ce("Bastani et al. (2025), GPT Tutor, below-median GPA (unassisted exam)",
        "bastani_etal_2025", -0.051, 0.054,
        "GPT Tutor", "No AI access",
        "Normalized grade on unassisted exam (below-median GPA)",
        domain="Math", n=2848, subgroup="Prior achievement: Below median"),
    _ce("Bastani et al. (2025), GPT Tutor vs GPT Base (unassisted exam)",
        "bastani_etal_2025", 0.101, 0.043,
        "GPT Tutor (with guardrails)", "GPT Base (unrestricted)",
        "Normalized grade on unassisted exam (pairwise AI arms)",
        domain="Math", comparison="ai_design", n=2848,
        subgroup="AI design comparison"),

    # ── De Simone — alternative outcomes (AI knowledge, digital skills) ──
    _ce("De Simone et al. (2025), AI knowledge subscore",
        "de_simone_etal_2025", 0.309, 0.077,
        "AI tutoring sessions (Microsoft Copilot/GPT-4)",
        "Business-as-usual classroom instruction",
        "AI knowledge subscore (final assessment)",
        domain="Language", n=654, subgroup="Subscore: AI knowledge"),
    _ce("De Simone et al. (2025), Digital skills subscore",
        "de_simone_etal_2025", 0.139, 0.076,
        "AI tutoring sessions (Microsoft Copilot/GPT-4)",
        "Business-as-usual classroom instruction",
        "Digital skills subscore (final assessment)",
        domain="Language", n=654, subgroup="Subscore: Digital skills"),

    # ── Fan — alternative arm comparisons ────────────────────────────────
    _ce("Fan et al. (2024), Essay improvement, AI vs Human Expert",
        "fan_etal_2025", 0.66, 0.269,
        "ChatGPT 4.0 during revision", "Human expert support",
        "Essay score improvement (post-revision minus pre-revision)",
        domain="Writing", comparison="ai_vs_active", outcome_with_ai=True,
        n=60, subgroup="AI vs Human Expert"),
    _ce("Fan et al. (2024), Essay improvement, AI vs Checklist tool",
        "fan_etal_2025", 0.75, 0.252,
        "ChatGPT 4.0 during revision", "Checklist writing analytics tool",
        "Essay score improvement (post-revision minus pre-revision)",
        domain="Writing", comparison="ai_vs_active", outcome_with_ai=True,
        n=65, subgroup="AI vs Checklist"),
    _ce("Fan et al. (2024), Knowledge gain, AI vs Human Expert",
        "fan_etal_2025", 0.45, 0.275,
        "ChatGPT 4.0 during revision", "Human expert support",
        "Knowledge gain (pre-post test on AI in education)",
        domain="Writing", comparison="ai_vs_active", timing="delayed",
        n=56, subgroup="AI vs Human Expert"),
    _ce("Fan et al. (2024), Knowledge gain, AI vs Checklist",
        "fan_etal_2025", 0.22, 0.269,
        "ChatGPT 4.0 during revision", "Checklist writing analytics tool",
        "Knowledge gain (pre-post test on AI in education)",
        domain="Writing", comparison="ai_vs_active", timing="delayed",
        n=57, subgroup="AI vs Checklist"),
    _ce("Fan et al. (2024), Knowledge transfer, AI vs CN",
        "fan_etal_2025", -0.02, 0.260,
        "ChatGPT 4.0 during revision", "No additional support",
        "Knowledge transfer (AI in healthcare, 10-item MCQ)",
        domain="Writing", timing="retention", n=60,
        subgroup="Transfer outcome"),

    # ── Hausman — heterogeneity by demographics/course type/percentile ──
    # Note: effects are in raw grade points (0-100 scale), not SD units, but
    # the original 5 estimates in the dataset are in the same units, so we
    # keep the convention for consistency.
    _ce("Hausman et al. (2025), Male students (Year 2)",
        "hausman_etal_2025", 1.374, 0.470,
        "AI-compatible courses post-ChatGPT (male)",
        "AI-incompatible courses (DiD)",
        "Course grade (0-100), male students",
        domain="Mixed", n=200672, subgroup="Gender: Male"),
    _ce("Hausman et al. (2025), Young students (<26, Year 2)",
        "hausman_etal_2025", 2.079, 0.537,
        "AI-compatible courses post-ChatGPT (age<26)",
        "AI-incompatible courses (DiD)",
        "Course grade (0-100), young students",
        domain="Mixed", n=238466, subgroup="Age: <26"),
    _ce("Hausman et al. (2025), Advanced courses (Year 2)",
        "hausman_etal_2025", 1.466, 0.511,
        "AI-compatible advanced courses post-ChatGPT",
        "AI-incompatible advanced courses (DiD)",
        "Course grade (0-100), advanced courses",
        domain="Mixed", n=254662, subgroup="Course level: Advanced"),
    _ce("Hausman et al. (2025), STEM courses (Year 2)",
        "hausman_etal_2025", 1.269, 0.969,
        "AI-compatible STEM post-ChatGPT", "AI-incompatible STEM (DiD)",
        "Course grade (0-100), STEM courses",
        domain="Math", n=119260, subgroup="Domain: STEM"),
    _ce("Hausman et al. (2025), Large classes (>25, Year 2)",
        "hausman_etal_2025", 1.671, 0.453,
        "AI-compatible large courses post-ChatGPT",
        "AI-incompatible large courses (DiD)",
        "Course grade (0-100), classes >25 students",
        domain="Mixed", n=435675, subgroup="Class size: Large"),
    _ce("Hausman et al. (2025), Median grade (Year 1)",
        "hausman_etal_2025", 1.272, 0.612,
        "AI-compatible courses post-ChatGPT",
        "AI-incompatible courses (DiD)",
        "50th percentile grade (Year 1)",
        domain="Mixed", n=10076, subgroup="Percentile: 50th"),
    _ce("Hausman et al. (2025), AI-incompatible advanced (cohort experience)",
        "hausman_etal_2025", -0.507, 0.353,
        "2022-23 cohort (post-ChatGPT exposure)",
        "2021-22 cohort (pre-ChatGPT, baseline)",
        "Grade in AI-incompatible advanced courses (Year 2)",
        domain="Mixed", timing="delayed", outcome_with_ai=False,
        n=34829, subgroup="AI human-capital spillover"),

    # ── Kreijkes — Group 2 (LLM vs LLM+Notes) + free recall outcomes ─────
    _ce("Kreijkes et al. (2026), Free recall (LLM vs Notes)",
        "kreijkes_etal_2026", -0.21, 0.10,
        "LLM chatbot only", "Note-taking only",
        "Free recall (open response)",
        domain="Language", timing="delayed", comparison="ai_vs_active",
        n=184, subgroup="Outcome: Free recall"),
    _ce("Kreijkes et al. (2026), Literal retention (LLM vs LLM+Notes)",
        "kreijkes_etal_2026", -0.13, 0.064,
        "LLM chatbot only", "LLM + note-taking",
        "Literal retention (cued recall + MC)",
        domain="Language", timing="delayed", comparison="ai_design",
        n=160, subgroup="LLM only vs LLM+Notes"),
    _ce("Kreijkes et al. (2026), Comprehension (LLM vs LLM+Notes)",
        "kreijkes_etal_2026", -0.14, 0.072,
        "LLM chatbot only", "LLM + note-taking",
        "Comprehension (bridging/knowledge-based inferences)",
        domain="Language", timing="delayed", comparison="ai_design",
        n=160, subgroup="LLM only vs LLM+Notes"),

    # ── Lira — cross-arm comparisons ─────────────────────────────────────
    _ce("Lira et al. (2026), Study 2 immediate, AI vs no-practice",
        "lira_etal_2025", 0.47, 0.054,
        "Practice with AI writing tool", "No practice",
        "Writing quality (test phase, GPT-4o, no AI)",
        domain="Writing", n=2238, subgroup="Active control: no-practice"),
    _ce("Lira et al. (2026), Study 3, AI vs Google Search",
        "lira_etal_2025", 0.46, 0.050,
        "Practice with AI writing tool", "Practice with Google Search",
        "Writing quality (test phase, GPT-4o, no AI)",
        domain="Writing", comparison="ai_vs_active",
        n=2997, subgroup="AI vs Google Search"),
    _ce("Lira et al. (2026), Study 3, Google vs editor feedback",
        "lira_etal_2025", -0.26, 0.049,
        "Practice with Google Search", "Practice with editor feedback",
        "Writing quality (test phase, GPT-4o, no AI)",
        domain="Writing", comparison="ai_vs_active",
        n=2997, subgroup="Google vs Editor"),
    _ce("Lira et al. (2026), Study 4 follow-up, AI vs no-AI practice",
        "lira_etal_2025", 0.29, 0.106,
        "Practice with AI writing tool", "Practice without AI",
        "Writing quality (1-day follow-up, no AI)",
        domain="Writing", timing="delayed",
        n=608, subgroup="1-day follow-up"),
    _ce("Lira et al. (2026), Study 4 follow-up, AI example only vs no AI",
        "lira_etal_2025", 0.32, 0.106,
        "See AI-generated example (no practice)", "Practice without AI",
        "Writing quality (1-day follow-up, no AI)",
        domain="Writing", timing="delayed",
        n=608, subgroup="Example-only"),

    # ── Liu — heterogeneity by how AI was used ───────────────────────────
    _ce("Liu et al. (2026), Direct-answer AI users (Exp 2)",
        "liu_etal_2026", -0.36, 0.095,
        "AI users obtaining direct solutions", "No-AI control",
        "Test solve rate, 3 fraction problems (Exp 2 heterogeneity)",
        domain="Math", n=466, subgroup="AI use: Direct answers"),
    _ce("Liu et al. (2026), Hint-only AI users (Exp 2)",
        "liu_etal_2026", -0.29, 0.133,
        "AI users requesting only hints", "No-AI control",
        "Test solve rate, 3 fraction problems (Exp 2 heterogeneity)",
        domain="Math", n=359, subgroup="AI use: Hints only"),
    _ce("Liu et al. (2026), Self-reported no AI use in AI arm (Exp 2)",
        "liu_etal_2026", -0.66, 0.184,
        "AI arm participants who did not use AI", "No-AI control",
        "Test solve rate, 3 fraction problems (Exp 2 heterogeneity)",
        domain="Math", n=314, subgroup="AI use: None"),
    _ce("Liu et al. (2026), Exp 1 skip rate",
        "liu_etal_2026", 0.25, 0.116,
        "GPT-5 sidebar access", "No AI access",
        "Skip rate, 3 fraction test problems (Exp 1)",
        domain="Math", n=307, subgroup="Outcome: Skip rate"),
    _ce("Liu et al. (2026), Exp 3 skip rate",
        "liu_etal_2026", 0.42, 0.158,
        "GPT-5 sidebar access", "No-AI control with test-tips",
        "Skip rate, 3 SAT reading test problems (Exp 3)",
        domain="Language", comparison="ai_vs_active",
        n=168, subgroup="Outcome: Skip rate"),

    # ── Chung — subgroup heterogeneity by Python skill and school tier ──
    _ce("Chung et al. (2026), Python beginners",
        "chung_etal_2025", 0.215, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (beginners only)",
        domain="Coding", timing="delayed", comparison="ai_design",
        n=380, ci_lo=0.048, ci_hi=0.382, subgroup="Prior achievement: Below median"),
    _ce("Chung et al. (2026), Python experienced",
        "chung_etal_2025", 0.008, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (experienced)",
        domain="Coding", timing="delayed", comparison="ai_design",
        n=300, ci_lo=-0.21, ci_hi=0.226, subgroup="Prior achievement: Above median"),
    _ce("Chung et al. (2026), Lower-tier schools",
        "chung_etal_2025", 0.173, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (lower-tier schools)",
        domain="Coding", timing="delayed", comparison="ai_design",
        n=400, ci_lo=0.004, ci_hi=0.342, subgroup="School tier: Lower"),
    _ce("Chung et al. (2026), Higher-tier schools",
        "chung_etal_2025", 0.039, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (higher-tier schools)",
        domain="Coding", timing="delayed", comparison="ai_design",
        n=316, ci_lo=-0.205, ci_hi=0.283, subgroup="School tier: Higher"),

    # ── Wiles — task-specific effects ────────────────────────────────────
    _ce("Wiles et al. (2026), Statistics task with AI",
        "wiles_etal_2024", 0.201, 0.026,
        "ChatGPT access + training", "Google/Stack Overflow training",
        "Statistics task score (with AI access)",
        domain="General knowledge", comparison="ai_vs_active",
        outcome_with_ai=True, n=330, subgroup="Task: Statistics"),
    _ce("Wiles et al. (2026), Prediction task with AI",
        "wiles_etal_2024", 0.172, 0.042,
        "ChatGPT access + training", "Google/Stack Overflow training",
        "Prediction task score (with AI access)",
        domain="General knowledge", comparison="ai_vs_active",
        outcome_with_ai=True, n=298, subgroup="Task: Prediction"),

    # ── Nie — alternative ITT/LATE specs ─────────────────────────────────
    _ce("Nie et al. (2025), Exam score LATE (ignore missingness)",
        "nie_etal_2025", 0.23, None,
        "GPT-4 access (adopters, LATE)", "No GPT-4 access",
        "Exam score LATE (ignore missingness)",
        domain="Coding", n=5831, ci_lo=-0.34, ci_hi=8.98,
        subgroup="Spec: LATE ignore missingness"),
    _ce("Nie et al. (2025), Week 6 homework completion (ITT)",
        "nie_etal_2025", -4.6, 1.3,
        "GPT-4 access", "No GPT-4 access",
        "Week 6 homework completion rate (pp)",
        domain="Coding", n=5831, ci_lo=-7.2, ci_hi=-1.9,
        subgroup="Outcome: Homework completion"),

    # ── Lehmann — prior-knowledge median split (Table 12) ────────────────
    # Coefficients in raw # correct (20-question post-test); converted to SD
    # units using pooled post-test SD ≈ 4.6 (control 4.2-4.4, treatment 4.7-5.1
    # from Tables 4 & 6).
    _ce("Lehmann et al. (2024), prior knowledge below median (post-test)",
        "lehmann_etal_2024", 0.043/4.6, 0.701/4.6,
        "ChatGPT access during 45-min Python learning phase",
        "No LLM access",
        "Post-test score (20-question Python coding test)",
        domain="Coding", subgroup="Prior achievement: Below median"),
    _ce("Lehmann et al. (2024), prior knowledge above median (post-test)",
        "lehmann_etal_2024", 2.571/4.6, 1.142/4.6,
        "ChatGPT access during 45-min Python learning phase",
        "No LLM access",
        "Post-test score (20-question Python coding test)",
        domain="Coding", subgroup="Prior achievement: Above median"),
    _ce("Lehmann et al. (2024), prior knowledge below median (understanding)",
        "lehmann_etal_2024", -0.950/4.6, 0.466/4.6,
        "ChatGPT access during 45-min Python learning phase",
        "No LLM access",
        "Post-test, controlling for learning-phase volume (understanding)",
        domain="Coding", subgroup="Prior achievement: Below median"),
    _ce("Lehmann et al. (2024), prior knowledge above median (understanding)",
        "lehmann_etal_2024", 0.663/4.6, 0.754/4.6,
        "ChatGPT access during 45-min Python learning phase",
        "No LLM access",
        "Post-test, controlling for learning-phase volume (understanding)",
        domain="Coding", subgroup="Prior achievement: Above median"),

    # ── Vanzo — grade/year split (Cohen's d already in SD units) ──────────
    _ce("Vanzo et al. (2025), 3rd year students (age ~16)",
        "vanzo_etal_2024", 0.603, None,
        "GPT-4 interactive homework", "Traditional homework",
        "Learning gains (post-test minus pre-test, 24 MCQ on English-as-L2)",
        domain="Language", n=39, subgroup="Grade: Younger"),
    _ce("Vanzo et al. (2025), 5th year students (age ~18)",
        "vanzo_etal_2024", -0.004, None,
        "GPT-4 interactive homework", "Traditional homework",
        "Learning gains (post-test minus pre-test, 24 MCQ on English-as-L2)",
        domain="Language", n=37, subgroup="Grade: Older"),
]


# ── Outcome-with-AI classification per estimate ─────────────────────────────
# True if the outcome was measured WITH AI access (i.e., performance, not
# transferable learning). Default for any not listed is False (unassisted).
# These reflect the AI vs No-AI distinction the user wants to filter.
OUTCOME_WITH_AI = {
    # Bastani: "assisted practice problems" outcomes are WITH AI
    "bastani_etal_2025__est1": True,   # GPT Base, assisted practice
    "bastani_etal_2025__est2": True,   # GPT Tutor, assisted practice
    # est3, est4 = unassisted exam → False (default)
    # Kazemitabaar
    "kazemitabaar_etal_2023__est18": True,  # training phase, with AI
    # est19 (immediate post-test, no AI) and est20 (retention, no AI) → False
    # Fan: essay was written WITH AI (treatment group used ChatGPT to write)
    "fan_etal_2025__est8": True,  # Essay score improvement (written with AI)
    # est9 = knowledge gain test (unassisted) → False
    # Wiles: est49 coding task with AI
    "wiles_etal_2024__est49": True,
    # est48 = post-experiment knowledge without AI → False
    # Contractor and Reyes: per user, "essay 1 could reflect AI performance"
    "contractor_reyes_2026__contractor_and_reyes_2026_session_one_essay": True,
    # session 1 test, session 2 test, session 2 essay → False (unassisted)
}


# ── Comparison-type classification per estimate (from subagent verification) ──
# Default for any not listed is "ai_vs_bau"
COMPARISON_TYPES = {
    # barcaui_2025
    "barcaui_2025__est0": "ai_vs_bau",
    # bastani_etal_2025: all ai_vs_bau (GPT Tutor with guardrails vs No AI is still ai_vs_bau)
    # de_simone_etal_2025: all ai_vs_bau
    # fan_etal_2025: all ai_vs_bau
    # hausman_etal_2025: all ai_vs_bau (quasi-experimental DiD, pre vs post)
    # henkel_etal_2024: ai_vs_bau
    # kalam_etal_2025: both ai_vs_bau
    # kazemitabaar_etal_2023: all ai_vs_bau
    "kestin_etal_2025__est21": "ai_vs_active",
    "kestin_etal_2025__est22": "ai_vs_active",
    "kim_etal_2025__est23": "ai_vs_active",
    "kim_etal_2025__est24": "ai_vs_active",
    "kreijkes_etal_2026__est25": "ai_vs_active",  # vs note-taking
    "kreijkes_etal_2026__est26": "ai_vs_active",
    "kumar_etal_2023__est27": "ai_vs_active",  # vs answer-only
    "kumar_etal_2023__est28": "ai_vs_active",
    "learnlm_team_2025__est29": "ai_vs_active",  # vs static hints / human tutor
    "learnlm_team_2025__est30": "ai_vs_active",
    "learnlm_team_2025__est31": "ai_vs_active",
    # lehmann_etal_2024
    "lehmann_etal_2024__est34": "ai_design",  # copy-paste vs no-copy-paste; both AI arms
    # lira_etal_2025
    "lira_etal_2025__est38": "ai_vs_active",  # vs editor feedback
    # nie_etal_2025: all ai_vs_bau
    # vanzo_etal_2024: all ai_vs_bau
    # wang_etal_2025: all ai_vs_bau (per instruction; active component identical)
    "wiles_etal_2024__est48": "ai_vs_active",  # vs Google/Stack Overflow training
    "wiles_etal_2024__est49": "ai_vs_active",
    "xu_etal_2025__est50": "ai_design",  # metacog scaffolding vs no scaffolding (both AI)
    "xu_etal_2025__est51": "ai_design",
    "chung_etal_2025__est52": "ai_design",  # adaptive RL vs fixed sequencing (both AI)
    "chung_etal_2025__est53": "ai_design",
    # liu_etal_2026
    "liu_etal_2026__est56": "ai_vs_active",  # vs test-tips sidebar
    # shen_and_tamkin_2026: ai_vs_bau
    # contractor_reyes_2026: all ai_vs_bau
}


# Domain mapping: literature_effects.csv has finer "domain" per estimate.
# Use that mapping where available; fall back to PAPER_META.
LIT_DOMAIN = {
    "Bastani et al., GPT Base": "Math",
    "Bastani et al., GPT Tutor": "Math",
    "De Simone et al., English": "Language",
    "De Simone et al., retention": "Language",
    "Lehmann et al., Study 3": "Coding",
    "Lehmann et al., Study 2": "Coding",
    "Lira et al., retention": "Writing",
    "Lira et al., Study 5": "Writing",
    "Lira et al., Study 2": "Writing",
    "Liu et al., Exp 1 (Math)": "Math",
    "Liu et al., Exp 2 (Math)": "Math",
    "Liu et al., Exp 3 (Reading)": "Language",
    "Kazemitabaar et al., post-test": "Coding",
    "Kazemitabaar et al., retention": "Coding",
    "Shen & Tamkin": "Coding",
}


def load_lit_csv() -> pd.DataFrame:
    df = pd.read_csv(LIT_CSV)
    df = df.dropna(subset=["study"])
    return df


# Explicit map of (paper_name, treatment_substring, outcome_substring) -> curated label.
# Used because meta_analysis.xlsx stores raw SEs while literature_effects.csv stores
# SD-converted SEs for Bastani; effect-only matching is also ambiguous for Lira (multiple
# very close effects). Listed in the order of literature_effects.csv.
CURATED_MAP = [
    ("Bastani et al. (2025)", "GPT Base", "unassisted exam", "Bastani et al., GPT Base"),
    ("Bastani et al. (2025)", "GPT Tutor", "unassisted exam", "Bastani et al., GPT Tutor"),
    ("De Simone et al. (2025)", "", "English skills", "De Simone et al., English"),
    ("De Simone et al. (2025)", "", "Third-term", "De Simone et al., retention"),
    ("Lehmann et al. (2024)", "no copy-paste", "Post-test", "Lehmann et al., Study 2"),
    ("Lehmann et al. (2024)", "copy-paste enabled; Access", "Post-test", "Lehmann et al., Study 3"),
    ("Lira et al. (2025)", "Practice with AI writing tool", "1-day follow-up", "Lira et al., retention"),
    ("Lira et al. (2025)", "Shown AI-generated example", "test phase", "Lira et al., Study 5"),
    ("Lira et al. (2025)", "Practice with AI writing tool", "GPT-4o rated", "Lira et al., Study 2"),
    ("Liu et al. (2026)", "", "Exp 1", "Liu et al., Exp 1 (Math)"),
    ("Liu et al. (2026)", "", "Exp 2", "Liu et al., Exp 2 (Math)"),
    ("Liu et al. (2026)", "", "Exp 3", "Liu et al., Exp 3 (Reading)"),
    ("Kazemitabaar et al. (2023)", "", "immediate post-test", "Kazemitabaar et al., post-test"),
    ("Kazemitabaar et al. (2023)", "", "1-week retention", "Kazemitabaar et al., retention"),
    ("Shen and Tamkin (2026)", "", "", "Shen & Tamkin"),
]


def match_curated(paper_name: str, treatment: str, outcome: str) -> str | None:
    """Return the literature_effects.csv `study` label if this estimate matches.

    Uses explicit CURATED_MAP to handle Bastani's SE-unit mismatch and Lira's
    multiple close effect sizes.
    """
    for p_name, treat_sub, outcome_sub, label in CURATED_MAP:
        if paper_name != p_name:
            continue
        # treat_sub can be a list of required substrings, separated by "; "
        if treat_sub:
            required = treat_sub.split("; ")
            if not all(req in str(treatment) for req in required):
                continue
        if outcome_sub and outcome_sub not in str(outcome):
            continue
        return label
    return None


def load_own_estimates() -> list[dict]:
    """Load the 4 'This paper' estimates from regression_results_main.dta."""
    try:
        df = pd.read_stata(REG_DTA)
    except Exception as exc:  # pragma: no cover
        print(f"WARN: could not read {REG_DTA}: {exc}")
        return []

    mask = df["outcome"].isin(["test_score1", "test_score2", "score6_essay"])
    df = df[mask & (df["spec"] == "ols")].copy()

    # apply the same sample restrictions as in 4-figures.do lines 238-241
    def keep_row(r):
        oc = r["outcome"]
        sm = r["sample"]
        return (
            (oc == "test_score1" and sm == "s1_student")
            or (oc == "test_score2" and sm == "s2_student")
            or (oc == "score6_essay" and sm == "s1_grader")
            or (oc == "score6_essay" and sm == "s2_grader")
        )

    df = df[df.apply(keep_row, axis=1)].copy()
    df["effect"] = df["beta"] / df["sd_ctrl"]
    df["se_std"] = df["se"] / df["sd_ctrl"]

    label_map = {
        ("test_score1", "s1_student"): "Contractor and Reyes (2026), Session one test",
        ("test_score2", "s2_student"): "Contractor and Reyes (2026), Session two test",
        ("score6_essay", "s1_grader"): "Contractor and Reyes (2026), Session one essay",
        ("score6_essay", "s2_grader"): "Contractor and Reyes (2026), Session two essay",
    }

    # Human-readable outcome names (replaces raw Stata variable names)
    outcome_pretty = {
        ("test_score1", "s1_student"): "Test score, Session 1 (immediate, no AI)",
        ("test_score2", "s2_student"): "Test score, Session 2 (1 week later, no AI)",
        ("score6_essay", "s1_grader"): "Essay quality, Session 1 (written with AI access)",
        ("score6_essay", "s2_grader"): "Essay quality, Session 2 (1 week later, no AI)",
    }
    timing_for = {
        ("test_score1", "s1_student"): "immediate",
        ("test_score2", "s2_student"): "delayed",
        ("score6_essay", "s1_grader"): "immediate",
        ("score6_essay", "s2_grader"): "delayed",
    }

    out = []
    for _, r in df.iterrows():
        label = label_map[(r["outcome"], r["sample"])]
        out.append(
            dict(
                estimate_id=f"contractor_reyes_2026__{slugify(label)}",
                paper_key="contractor_reyes_2026",
                study_label=label,
                effect_size_sd=float(r["effect"]),
                se=float(r["se_std"]),
                ci_lower=float(r["effect"]) - 1.96 * float(r["se_std"]),
                ci_upper=float(r["effect"]) + 1.96 * float(r["se_std"]),
                learning_domain="General knowledge",
                outcome=outcome_pretty[(r["outcome"], r["sample"])],
                outcome_timing=timing_for[(r["outcome"], r["sample"])],
                n_treatment=None,
                n_control=None,
                n_total=210 if str(r["sample"]).startswith("s1_") else 204,
                treatment="AI allowed while learning a new topic",
                control="No AI allowed",
                notes="",
                included_in_curated_subset=True,
                quality_label="High",
                quality_flags="none",
                is_own_paper=False,
            )
        )
    return out


# ── main build ─────────────────────────────────────────────────────────────

def build():
    meta = pd.read_excel(META_XLSX)
    lit = load_lit_csv()
    curated_studies = set(lit["study"])

    papers_rows: list[dict] = []
    estimates_rows: list[dict] = []

    # add "This paper" as the first paper row
    own_estimates = load_own_estimates()
    # Attach comparison_type and outcome_with_ai to each own_estimate
    for e in own_estimates:
        e["comparison_type"] = COMPARISON_TYPES.get(e["estimate_id"], "ai_vs_bau")
        e["outcome_with_ai"] = OUTCOME_WITH_AI.get(e["estimate_id"], False)
        e["is_subgroup"] = False

    if own_estimates:
        own_avg_effect = sum(e["effect_size_sd"] for e in own_estimates) / len(own_estimates)
        own_row = dict(
            paper_key="contractor_reyes_2026",
            authors_short="Contractor and Reyes",
            authors_full="Zara Contractor and Germán Reyes",
            year=2026,
            title="Experimental Evidence on the Learning Impact of Generative AI",
            venue="IZA WP #18055",
            pdf_filename="Contractor & Reyes (2026) - AI Learning RCT.pdf",
            pdf_url="https://www.germanr.com/ai-learning",
            country="USA",
            country_emoji="🇺🇸",
            population_category="Undergraduate",
            setting_detail="USA, Middlebury College undergraduates",
            lab_vs_field="Lab",
            study_design="RCT",
            ai_tool="ChatGPT",
            ai_design="Unrestricted",
            n_total=210,
            incentives="Course grade",
            learning_domain_primary="General knowledge",
            summary="Two-semester RCT at Middlebury College randomizing undergraduates to AI access during course assignments. Measures effects on test scores and essay quality.",
            image_filename="paper-contractor_reyes_2026.jpg",
            image_keywords="college students laptop classroom",
            included_in_curated_subset=True,
            quality_label="High",
            quality_flags="none",
            avg_effect=own_avg_effect,
            n_estimates=len(own_estimates),
            is_own_paper=False,
        )
        own_row.update(PAPER_CORRECTIONS.get("contractor_reyes_2026", {}))
        s = PAPER_SUMMARIES.get("contractor_reyes_2026")
        if s:
            own_row["summary_setup"] = s["setup"]
            own_row["summary_strategy"] = s["empirical_strategy"]
            own_row["summary_results"] = s["key_results"]
        papers_rows.append(own_row)
        for e in own_estimates:
            estimates_rows.append(e)

    # walk papers in meta_analysis.xlsx
    for paper_name in meta["paper"].unique():
        sub = meta[meta["paper"] == paper_name].copy()
        key = slugify(paper_name)
        first = sub.iloc[0]
        manual = PAPER_META.get(paper_name, {})
        corrections = PAPER_CORRECTIONS.get(key, {})

        # whether any estimate in this paper appears in the curated csv
        in_curated = False
        for _, r in sub.iterrows():
            for cs in curated_studies:
                if paper_name.split(" (")[0] in cs:
                    in_curated = True
                    break

        # average effect across estimates
        valid_effects = sub["effect_size_sd"].dropna()
        avg_effect = float(valid_effects.mean()) if len(valid_effects) else None

        row = dict(
            paper_key=key,
            authors_short=authors_short(paper_name),
            authors_full=manual.get("authors_full", authors_short(paper_name)),
            year=extract_year(paper_name),
            title=str(first["title"]),
            venue=manual.get("venue", "Working paper"),
            pdf_filename=manual.get("pdf_filename", ""),
            pdf_url="",
            country=manual.get("country", ""),
            country_emoji=manual.get("country_emoji", ""),
            population_category=manual.get("population_category", ""),
            setting_detail=str(first["setting"]),
            lab_vs_field=manual.get("lab_vs_field", "Field"),
            study_design=str(first["study_design"]),
            ai_tool=str(first["ai_tool"]),
            ai_design=str(first["ai_design"]),
            n_total=int(first["n_total"]) if pd.notna(first["n_total"]) else None,
            incentives=manual.get("incentives", ""),
            learning_domain_primary=manual.get("learning_domain_primary", "Mixed"),
            summary=manual.get("summary", ""),
            image_filename=f"paper-{key}.jpg",
            image_keywords=manual.get("image_keywords", ""),
            included_in_curated_subset=in_curated,
            quality_label=str(first["quality_label"]),
            quality_flags=str(first["quality_flags"]),
            avg_effect=avg_effect,
            n_estimates=len(sub),
            is_own_paper=False,
        )
        # Apply verified corrections (override any pre-populated value)
        row.update(corrections)
        # Attach 3-part summary if available
        s = PAPER_SUMMARIES.get(key)
        if s:
            row["summary_setup"] = s["setup"]
            row["summary_strategy"] = s["empirical_strategy"]
            row["summary_results"] = s["key_results"]
        papers_rows.append(row)

        # estimates
        for idx, r in sub.iterrows():
            outcome_short = str(r["outcome"])[:40].rstrip()
            effect = float(r["effect_size_sd"]) if pd.notna(r["effect_size_sd"]) else None
            se = float(r["se"]) if pd.notna(r["se"]) else None
            curated_label = match_curated(paper_name, str(r["treatment"]), str(r["outcome"]))
            in_curated_est = curated_label is not None
            study_label = curated_label if curated_label else f"{authors_short(paper_name)}, {outcome_short}"
            # If curated, override (effect, se) with literature_effects.csv values
            # so the forest plot matches the paper's published Figure 5 exactly
            # (handles SE-unit differences for Bastani)
            if curated_label:
                lit_row = lit[lit["study"] == curated_label]
                if len(lit_row) == 1:
                    effect = float(lit_row.iloc[0]["effect"])
                    se = float(lit_row.iloc[0]["se"])
            domain = LIT_DOMAIN.get(study_label, manual.get("learning_domain_primary", "Mixed"))

            estimate_id = f"{key}__est{idx}"
            # Apply per-estimate overrides from version-refresh verification
            ov = ESTIMATE_OVERRIDES.get(estimate_id, {})
            if "se" in ov: se = ov["se"]
            if "effect_size_sd" in ov: effect = ov["effect_size_sd"]
            estimates_rows.append(
                dict(
                    estimate_id=estimate_id,
                    paper_key=key,
                    study_label=study_label,
                    effect_size_sd=effect,
                    se=se,
                    ci_lower=float(r["ci_lower"]) if pd.notna(r["ci_lower"]) else None,
                    ci_upper=float(r["ci_upper"]) if pd.notna(r["ci_upper"]) else None,
                    learning_domain=domain,
                    outcome=str(r["outcome"]),
                    outcome_timing=str(r["outcome_timing"]),
                    n_treatment=int(r["n_treatment"]) if pd.notna(r["n_treatment"]) else None,
                    n_control=int(r["n_control"]) if pd.notna(r["n_control"]) else None,
                    n_total=int(r["n_total"]) if pd.notna(r["n_total"]) else None,
                    treatment=str(r["treatment"]),
                    control=str(r["control"]),
                    notes=str(r["notes"]) if pd.notna(r["notes"]) else "",
                    included_in_curated_subset=in_curated_est,
                    quality_label=str(r["quality_label"]),
                    quality_flags=str(r["quality_flags"]),
                    comparison_type=COMPARISON_TYPES.get(estimate_id, "ai_vs_bau"),
                    outcome_with_ai=OUTCOME_WITH_AI.get(estimate_id, False),
                    is_own_paper=False,
                    is_subgroup=False,
                )
            )
            # Apply n_total / CI overrides post-construction
            if "n_total" in ov:
                estimates_rows[-1]["n_total"] = ov["n_total"]
            if "ci_lower" in ov:
                estimates_rows[-1]["ci_lower"] = ov["ci_lower"]
            if "ci_upper" in ov:
                estimates_rows[-1]["ci_upper"] = ov["ci_upper"]

    # ── Append ADDITIONAL_ESTIMATES (subgroup / heterogeneity rows) ───────
    # Each gets a synthetic estimate_id keyed to paper_key.
    sg_counter = {}
    for est in ADDITIONAL_ESTIMATES:
        pkey = est["paper_key"]
        sg_counter[pkey] = sg_counter.get(pkey, 0) + 1
        est_id = f"{pkey}__sg{sg_counter[pkey]}"
        # Fill in missing CI if needed
        eff = est.get("effect_size_sd")
        se = est.get("se")
        ci_lo = est.get("ci_lower")
        ci_hi = est.get("ci_upper")
        if ci_lo is None and eff is not None and se is not None:
            ci_lo = eff - 1.96 * se
        if ci_hi is None and eff is not None and se is not None:
            ci_hi = eff + 1.96 * se
        # Back out SE from CI when SE is missing
        if se is None and ci_lo is not None and ci_hi is not None:
            se = (ci_hi - ci_lo) / (2 * 1.96)
        full = dict(est)
        full["estimate_id"] = est_id
        full["se"] = se
        full["ci_lower"] = ci_lo
        full["ci_upper"] = ci_hi
        estimates_rows.append(full)

    # ── write XLSX ────────────────────────────────────────────────────────
    papers_df = pd.DataFrame(papers_rows)
    estimates_df = pd.DataFrame(estimates_rows)

    PAPERS_XLSX.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(PAPERS_XLSX, engine="openpyxl") as writer:
        papers_df.to_excel(writer, sheet_name="papers", index=False)
        estimates_df.to_excel(writer, sheet_name="estimates", index=False)
    print(f"WROTE {PAPERS_XLSX} ({len(papers_df)} papers, {len(estimates_df)} estimates)")

    # ── compute random-effects grand mean for sanity check ────────────────
    valid = estimates_df.dropna(subset=["effect_size_sd", "se"]).copy()
    valid = valid[valid["se"] > 0]
    w = 1.0 / (valid["se"] ** 2)
    mu_fe = (w * valid["effect_size_sd"]).sum() / w.sum()
    Q = (w * (valid["effect_size_sd"] - mu_fe) ** 2).sum()
    k = len(valid)
    tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
    w_re = 1.0 / (valid["se"] ** 2 + tau2)
    grand_mean = (w_re * valid["effect_size_sd"]).sum() / w_re.sum()
    grand_se = 1.0 / (w_re.sum() ** 0.5)
    print(f"Random-effects grand mean (full sample): {grand_mean:.3f} (SE {grand_se:.3f})")

    # curated subset grand mean
    curated = valid[valid["included_in_curated_subset"]]
    if len(curated) > 0:
        wc = 1.0 / (curated["se"] ** 2)
        muc_fe = (wc * curated["effect_size_sd"]).sum() / wc.sum()
        Qc = (wc * (curated["effect_size_sd"] - muc_fe) ** 2).sum()
        kc = len(curated)
        tau2c = max(0.0, (Qc - (kc - 1)) / (wc.sum() - (wc ** 2).sum() / wc.sum()))
        wc_re = 1.0 / (curated["se"] ** 2 + tau2c)
        gmc = (wc_re * curated["effect_size_sd"]).sum() / wc_re.sum()
        gmc_se = 1.0 / (wc_re.sum() ** 0.5)
        print(f"Random-effects grand mean (curated):     {gmc:.3f} (SE {gmc_se:.3f}, k={kc})")

    # ── attach estimation_method + estimand (from subagent classification) ──
    # Keyed by estimate_id in code/estimand_method.json. Missing → blank.
    em_path = SITE / "code" / "estimand_method.json"
    em_map = json.loads(em_path.read_text(encoding="utf-8")) if em_path.exists() else {}
    estimates_df["estimation_method"] = estimates_df["estimate_id"].map(
        lambda i: (em_map.get(i) or {}).get("estimation_method") or ""
    )
    estimates_df["estimand"] = estimates_df["estimate_id"].map(
        lambda i: (em_map.get(i) or {}).get("estimand") or ""
    )
    n_estimand = int((estimates_df["estimand"] != "").sum())
    print(f"Estimand/method attached: {n_estimand}/{len(estimates_df)} estimates labeled")

    # ── write JSON ────────────────────────────────────────────────────────
    PAPERS_JSON.parent.mkdir(parents=True, exist_ok=True)

    def df_to_records(df):
        records = json.loads(df.to_json(orient="records"))
        # clean up NaN -> None
        return records

    with open(PAPERS_JSON, "w", encoding="utf-8") as f:
        json.dump(df_to_records(papers_df), f, ensure_ascii=False, indent=2)
    with open(ESTIMATES_JSON, "w", encoding="utf-8") as f:
        json.dump(df_to_records(estimates_df), f, ensure_ascii=False, indent=2)
    print(f"WROTE {PAPERS_JSON}")
    print(f"WROTE {ESTIMATES_JSON}")


if __name__ == "__main__":
    build()
