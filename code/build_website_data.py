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
    "Franco et al. (2026)": dict(
        authors_full="Catalina Franco, Natalie Irmert, Siri Isaksson",
        venue="Working paper (SSRN)",
        country="UK",
        country_emoji="🇬🇧",
        population_category="Undergraduate",
        lab_vs_field="Lab",
        incentives="GBP 5 show-up + GBP 7 practice threshold + GBP 1 per correct exam answer (max GBP 27)",
        learning_domain_primary="Language",
        summary="Pre-registered lab experiment at Nottingham randomizing 572 students to browsing-only, ChatGPT, or ChatGPT-plus-guidance while studying Esperanto. No average effect on an unaided exam; AI crowds out practice questions, and heavy copy-pasters learn least.",
        image_keywords="university computer lab students UK",
        pdf_filename="Franco et al (2026) - Does AI Help or Hurt Learning.pdf",
    ),
    "Barcaui (2025)": dict(
        authors_full="Andre Barcaui",
        venue="Working paper",
        country="Brazil",
        country_emoji="🇧🇷",
        population_category="Undergraduate",
        lab_vs_field="Field",
        incentives="Course grade",
        learning_domain_primary="General knowledge",
        summary="Compares ChatGPT-assisted learning vs traditional learning on knowledge retention 45 days after undergraduate business students studied AI/ML concepts.",
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
        # [RA-2026-07] Voluntary after-school program; primary outcomes are
        # ungraded research assessments (Sec 2.2).
        incentives="None (voluntary; ungraded research assessment)",
        learning_domain_primary="Language",
        summary="Nigerian senior secondary students got after-school sessions with an English-tutoring GPT-4 chatbot. Treatment group gained on English, AI knowledge, and digital skills; gains extended to a broader-curriculum school exam taken right after the program.",
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
        summary="University students wrote essays with ChatGPT vs checklist, expert, or no support. AI users produced better essays but showed no significant knowledge gain or transfer advantage; process data suggest \"metacognitive laziness\".",
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
        summary="WhatsApp-based math tutor (Rori) deployed to grades 3–8 students in Ghana. RCT measured math gains over the Feb–Aug 2023 school year (~8 months).",
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
        learning_domain_primary="Science",
        summary="First-year Georgetown medical students randomized to ChatGPT vs traditional study for a basic-science quiz (pathology, pharmacology, physiology, anatomy).",
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
        summary="Children ages 10–17 learned Python with vs without OpenAI Codex code-generator assistance. Treatment showed higher gains during training, near-equal immediate post-test scores, and a modest non-significant edge at 1-week retention.",
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
        summary="Quasi-experimental study at Squirrel AI learning centers in China, K-12 students. Compared the post-solution GenAI tutor mode to the baseline digital practice mode (correctness feedback + static solutions).",
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
        summary="University students learning Python in the Netherlands (Study 1: Dutch graduate courses, ChatGPT outages as instrument) and Germany (Studies 2-3: lab RCTs randomizing ChatGPT access).",
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
        learning_domain_primary="Coding",
        summary="Boston Consulting Group consultants worldwide were randomized to use GPT-4 for data-science tasks (coding, statistics, prediction). Measured task performance and skill transfer.",
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
    ),    'Ba et al. (2024)': dict(
        authors_full='Hongjun Ba, Lili Zhang, Zizheng Yi',
        venue='BMC Medical Education',
        country='China',
        country_emoji='🇨🇳',
        population_category='Undergraduate',
        lab_vs_field='Field',
        incentives='No monetary incentives reported; the closed-book theoretical exam and Mini-CEX were embedded assessments in the required 2-week pediatric internship rotation.',
        learning_domain_primary='Medicine',
        summary='An RCT of 77 medical interns at Sun Yat-sen University found that adding ChatGPT (GPT-4.0) to a two-week pediatric cardiology rotation left closed-book theoretical exam scores unchanged (near ceiling, ~92/100) but improved categorical Mini-CEX clinical-skills ratings.',
        image_keywords='pediatrics, medical interns, bedside teaching, hospital ward, clinical skills, ChatGPT, China',
        pdf_filename='Ba et al (2024) - ChatGPT-Assisted vs Traditional Pediatric Teaching.pdf',
    ),
    'Bassner et al. (2026)': dict(
        authors_full='Patrick Bassner, Ben Lenk-Ostendorf, Ramona Beinstingel, Tobias Wasner, Stephan Krusche',
        venue='Computers and Education: Artificial Intelligence',
        country='Germany',
        country_emoji='🇩🇪',
        population_category='University (mixed)',
        lab_vs_field='Field',
        incentives='Course bonus points for participating seriously in the tutorial-session experiment, awarded regardless of exercise score or survey answers',
        learning_domain_primary='Coding',
        summary="A three-arm RCT in a TU Munich CS1 course (N=275) found that a scaffolded AI tutor (Iris) and unrestricted ChatGPT both sharply raised programming-exercise scores but produced no advantage in conceptual knowledge gains or code comprehension over a no-AI control, a dissociation of performance from learning. Both AI tools lowered frustration and cognitive load, but only Iris raised intrinsic motivation, while the more-preferred ChatGPT acted as a 'comfort trap.'",
        image_keywords='programming education; Java concurrency; AI coding tutor; university computer science students; coding on laptop; ChatGPT',
        pdf_filename='Bassner et al (2026) - Less Stress Better Scores Same Learning.pdf',
    ),
    'Dai et al. (2025)': dict(
        authors_full='Xusheng Dai, Zhaochun Wen, Jianxiao Jiang, Huiqin Liu, Yu Zhang',
        venue='arXiv preprint (Tsinghua University)',
        country='China',
        country_emoji='🇨🇳',
        population_category='High school',
        lab_vs_field='Field',
        incentives="None (voluntary participation; outcome is the school's regular end-of-term exam, no monetary incentive)",
        learning_domain_primary='Science',
        summary='Two RCTs with 387 Grade 10 physics students in China find that AI-generated homework feedback had small, non-significant effects on unassisted final-exam scores overall, with gains concentrated in specific achievement subgroups and offsetting declines in learner autonomy. How students used the AI feedback mattered more than the feedback itself.',
        image_keywords='high school physics classroom; Chinese students studying homework; AI-generated feedback; paper worksheets',
        pdf_filename='Dai et al (2025) - How Students Use AI Feedback Matters.pdf',
    ),
    'Fischer et al. (2025)': dict(
        authors_full='Mira Fischer (BiB, WZB and IZA); Holger A. Rau (Georg-August-Universität Göttingen); Rainer Michael Rilke (WHU)',
        venue='IZA DP #18338',
        country='Germany',
        country_emoji='🇩🇪',
        population_category='University (mixed)',
        lab_vs_field='Lab',
        incentives='All 50 test items (Test 1 + Test 2) and 2 self-performance estimates incentivized at €0.25 each; average pay €16.72 for a ~75-minute session; no penalty for wrong answers',
        learning_domain_primary='Economics',
        summary='A preregistered lab experiment with 334 German university students finds that access to a GPT-4-based AI tutor during exam prep raised unassisted test scores by 0.23 SD, driven by unrestricted access (0.34 SD) rather than reading-first restricted access (0.13 SD, n.s.).',
        image_keywords='AI tutor chatbot, university student studying, computer lab cubicle, economics textbook, exam preparation',
        pdf_filename='Fischer et al (2025) - AI Tutoring Enhances Student Learning.pdf',
    ),
    'Gan et al. (2024)': dict(
        authors_full='Wenyi Gan, Jianfeng Ouyang, Hua Li, Zhaowen Xue, Yiming Zhang, Qiu Dong, Jiadong Huang, Xiaofei Zheng, Yiyi Zhang',
        venue='Journal of Medical Internet Research',
        country='China',
        country_emoji='🇨🇳',
        population_category='Undergraduate',
        lab_vs_field='Field',
        incentives="Participation rewards (their implementation verified by the First Affiliated Hospital's Science and Technology Department); not tied to test performance. No performance-based incentive described.",
        learning_domain_primary='Medicine',
        summary='A single-center RCT with 110 third-year medical undergraduates at Jinan University (China) finds that a one-week orthopedics review using ChatGPT-4 raised unassisted exam scores by about 0.4 SD relative to ordinary internet/forum self-study, with significant spillovers to two of five end-of-semester final exams.',
        image_keywords='orthopedics medical education, medical students studying, X-ray bones skeleton, ChatGPT on laptop, China university',
        pdf_filename='Gan et al (2024) - ChatGPT in Orthopedic Education.pdf',
    ),
    'Hou et al. (2026)': dict(
        authors_full='Xiaoyu Hou, Bo Xiao, Hexu Liu, and Shane Mueller',
        venue='arXiv preprint',
        country='USA',
        country_emoji='🇺🇸',
        population_category='Undergraduate',
        lab_vs_field='Lab',
        incentives='None stated',
        learning_domain_primary='Engineering',
        summary='An online three-arm RCT with 95 undergraduates testing whether a five-step prompting framework changes what students learn from a course-grounded (RAG) generative-AI assistant. Guided AI use raised unassisted post-test scores (d~0.86), entirely through open-ended reasoning items, while free-form AI use was no better than slide-only review.',
        image_keywords='construction engineering education, generative AI assistant, chatbot tutoring, undergraduate students, online learning, laptop study',
        pdf_filename='Hou et al (2026) - Instructional Guidance in GenAI-Assisted Learning.pdf',
    ),
    'Huang et al. (2025)': dict(
        authors_full='Siyu Huang, Chang Wen, Xueying Bai, Sihong Li, Shuining Wang, Xiaoxuan Wang, Dong Yang',
        venue='Journal of Medical Internet Research',
        country='China',
        country_emoji='🇨🇳',
        population_category='Undergraduate',
        lab_vs_field='Field',
        incentives='Not stated (no compensation or incentives reported)',
        learning_domain_primary='Medicine',
        summary='A single-site RCT with 187 fourth- and fifth-year dental undergraduates at Wuhan University: adding ChatGPT-3.5 to instructional videos raised operative-skill scores on a desktop-VR simulator by about 0.67 SD (7.58 points on 100) over videos alone, with the largest gains among students with lower spatial ability.',
        image_keywords='dental students, virtual reality dental simulator, tooth preparation training, dentistry education, China',
        pdf_filename='Huang et al (2025) - ChatGPT as Instructor Dental Skills.pdf',
    ),
    'Kavadella et al. (2024)': dict(
        authors_full='Argyro Kavadella, Marco Antonio Dias da Silva, Eleftherios G Kaklamanos, Vasileios Stamatopoulos, Kostis Giannakopoulos',
        venue='JMIR Medical Education',
        country='Cyprus',
        country_emoji='🇨🇾',
        population_category='Undergraduate',
        lab_vs_field='Field',
        incentives="None on the outcome: the 10-MCQ exam was unannounced, anonymous, and ungraded, framed as a diagnostic for the educator to spot knowledge gaps. The assignment itself was a required but ungraded part of the module's semester program (replacing a lecture).",
        learning_domain_primary='Medicine',
        summary='A randomized trial with 77 second-year dental students at European University Cyprus: one group used ChatGPT and the other used conventional literature/internet search to complete a radiation-biology assignment, after which an unannounced, blind 10-question exam found the ChatGPT group scored significantly higher (7.54 vs 6.94 of 10, p=.045).',
        image_keywords='dental students, dentistry education, dental radiography X-ray, university classroom, ChatGPT',
        pdf_filename='Kavadella et al (2024) - ChatGPT in Undergraduate Dental Education.pdf',
    ),
    'LearnLM Team (2026)': dict(
        authors_full='LearnLM Team, Google DeepMind & Fab AI (report prepared by Kevin R. McKee)',
        venue='Google DeepMind & Fab AI technical report',
        country='Sierra Leone',
        country_emoji='🇸🇱',
        population_category='Middle school',
        lab_vs_field='Field',
        incentives='None for students (the endline math assessment was itself the outcome and was taken unassisted)',
        learning_domain_primary='Math',
        summary="A preregistered cluster RCT in 48 junior-secondary math classrooms in Port Loko District, Sierra Leone: teachers wove Gemini's Guided Learning feature into half of their weekly lessons (~12h over eight weeks) while a control arm kept standard instruction. Endline IRT math scores rose 0.258 SD (ITT), and 0.380 SD for students who completed the requested 12 hours.",
        image_keywords='Sierra Leone junior secondary classroom, students sharing tablets, mathematics lesson, West Africa education, Gemini AI',
        pdf_filename='LearnLM Team (2026) - Teaching with Gemini Sierra Leone.pdf',
    ),
    'Stromberg et al. (2026)': dict(
        authors_full='David Strömberg, Victor Lei, Yanhui Wu',
        venue='CEPR Discussion Paper 21577',
        country='China',
        country_emoji='🇨🇳',
        population_category='High school',
        setting_detail='China, one county; grades 7-12 (junior and senior secondary)',
        lab_vs_field='Field',
        incentives='High-stakes coursework: monthly closed-book exams and the Zhongkao/Gaokao entrance exams (observational data; no experimental incentives)',
        learning_domain_primary='Mixed',
        summary="Thirty months of administrative panel data on 26,811 students in grades 7-12 in one Chinese county, analyzed with staggered-adoption difference-in-differences around each student's self-reported first use of generative AI (observational, not randomized). Homework scores jump (+1.9 SD) while closed-book monthly exam scores fall 20% of the baseline mean (-1.4 SD) within six months; entrance-exam scores fall 18-24% for students with 2+ years of exposure, and 81% of experienced AI users show homework-outsourcing patterns.",
        image_keywords='Chinese secondary school classroom, students taking exam, homework smartphone chatbot, gaokao exam hall China',
        pdf_filename='Stromberg et al (2026) - Generative AI Learning Penalty.pdf',
    ),
}


# ── Papers excluded from the atlas ──────────────────────────────────────────
# Rows stay in meta_analysis.xlsx (append-only master; estimate IDs are
# positional) but are skipped when building the site.
# Wu et al. (2025): full-text review found assignment by odd/even alternation
# rather than random allocation (Medical Teacher 47(3), sec. 2.1), which fails
# the atlas criterion of random assignment or a clean quasi-experimental
# design. Also excluded from the companion paper's curated meta-analysis;
# see support_info/meta_analysis/litverify/wu_bassner_fulltext_2026-07-08.md.
DROP_PAPERS = {"Wu et al. (2025)"}


# ── Design class (drives the site's Design filter) ──────────────────────────
# lab_rct / field_rct / online_rct = randomized experiments by setting;
# observational = no random assignment (DiD, FE2SLS/IV, cohort comparisons).
# Paper-level default with per-estimate overrides for mixed-design papers.
DESIGN_CLASS = {
    "contractor_reyes_2026": "lab_rct",
    "franco_etal_2026": "lab_rct",
    "fan_etal_2025": "lab_rct",
    "fischer_etal_2025": "lab_rct",
    "hou_etal_2026": "lab_rct",
    # Lehmann Studies 2-3 (the plotted estimates) are pre-registered lab
    # experiments; Study 1 rows are overridden to observational below.
    "lehmann_etal_2024": "lab_rct",
    "kazemitabaar_etal_2023": "online_rct",
    "kumar_etal_2023": "online_rct",
    "lira_etal_2025": "online_rct",
    "nie_etal_2025": "online_rct",
    "liu_etal_2026": "online_rct",
    "shen_and_tamkin_2026": "online_rct",
    "hausman_etal_2025": "observational",
    "kim_etal_2025": "observational",
    "xu_etal_2025": "observational",
    "stromberg_etal_2026": "observational",
}
DESIGN_CLASS_DEFAULT = "field_rct"
DESIGN_CLASS_OVERRIDES = {
    # Lehmann Study 1: FE2SLS field study (ChatGPT-outage IV), not randomized
    "lehmann_etal_2024__est32": "observational",
    "lehmann_etal_2024__est35": "observational",
}


# ── Subagent verification corrections (one verification pass per paper) ────
# These override values in PAPER_META based on what each paper actually reports.
PAPER_CORRECTIONS = {
    "franco_etal_2026": dict(
        pdf_url="https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6425840",
        n_total=572,  # randomized sample across all three arms (572 analyzed)
    ),
    # [RA-2026-07 W. Erda] Card showed only the Iris arm's tool; the study
    # also has an unrestricted-ChatGPT arm.
    "bassner_etal_2026": dict(
        ai_tool="Iris tutor and ChatGPT (both GPT-4.0)",
    ),
    "barcaui_2025": dict(
        venue="Social Sciences & Humanities Open",
        learning_domain_primary="General knowledge",  # AI/ML conceptual content; not coding
        incentives="None (voluntary participation)",
        n_total=120,  # randomized (85 completed the retention test)
    ),
    "bastani_etal_2025": dict(
        venue="PNAS, 122(26), e2422633122",
        authors_full="Hamsa Bastani, Osbert Bastani, Alp Sungu, Haosen Ge, Özge Kabakcı, Rei Mariman",
        # PDF unchanged (PNAS PDF gated; SSRN preprint identical content).
        n_total=839,  # students (estimate rows carry 2,848 student-session obs)
    ),
    "de_simone_etal_2025": dict(
        n_total=759,  # completers (regression Ns are 636-654; 1,328 randomized)
    ),
    "fan_etal_2025": dict(
        year=2024,
        venue="British Journal of Educational Technology",
        title="Beware of metacognitive laziness: Effects of generative artificial intelligence on learning motivation, processes, and performance",
        pdf_filename="Fan et al (2024) - BJET - Metacognitive Laziness.pdf",
        # [RA-2026-07] Paper describes no compensation; sample is 55%
        # undergraduate / ~45% graduate (Sec 3.1).
        incentives="None (no performance-based incentive; compensation not reported)",
        population_category="University (mixed)",
        n_total=117,  # four-arm study total (two-arm comparisons carry 62/58)
    ),
    "hausman_etal_2025": dict(
        authors_full="Naomi Hausman, Oren Rigbi, Sarit Weisburd",
        venue="CEPR DP 20206 / CESifo WP 11843",
        pdf_filename="Hausman et al (2025) - CESifo - GenAI Impact on Student Achievement.pdf",
        # [RA-2026-07] Grade data cover ALL BA/MA/MBA courses university-wide
        # (only the 91-student adoption survey is business-school); population
        # spans undergrad + graduate. n_total = ~36,000 unique students (the
        # paper-card/hero counter counts PEOPLE); the baseline DiD regression
        # sample of 500,611 student-course-semester observations lives on the
        # estimate rows. The old 22,806 was the Table 5 advanced-course subsample.
        setting_detail="Israel, large research university; all BA/MA/MBA courses across faculties (2018-2024)",
        population_category="University (mixed)",
        n_total=36000,
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
    "kim_etal_2025": dict(
        # [RA-2026-07 r2] Exact paper title (card had dropped "and Engagement").
        title="Generative AI Can Improve Performance and Engagement without Harming Learning",
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
        # [RA-2026-07] Study 1 is a Dutch university, Studies 2-3 a German lab
        # pool of enrolled students of mixed level (not graduate-only).
        country="Netherlands & Germany",
        country_emoji="🇳🇱🇩🇪",
        population_category="University (mixed)",
    ),
    "lira_etal_2025": dict(
        authors_full="Benjamin Lira, Todd Rogers, Daniel G. Goldstein, Lyle Ungar, Angela L. Duckworth",
        year=2026,
        title="Coach not crutch: Evidence that AI can improve writing skill despite reducing effort",
        venue="Working paper (arXiv v4, Feb 2026)",
        summary="Prolific adults practiced rewriting cover letters with an AI writing tool, without AI, with professional editor feedback, with Google Search, or by viewing an AI-generated example. Practicing with AI improved writing skill more than practicing without AI, with gains persisting one day later.",
        pdf_filename="Lira et al (2026) - Coach Not Crutch.pdf",
        # [RA-2026-07 r2] The writing tests were performance-incentivized
        # ("a 7-minute incentivized test of writing skill", Methods p.9).
        incentives="Prolific pay; performance-incentivized writing tests",
        # [RA-2026-07] Four non-overlapping samples: 2,637 + 2,238 + 2,997 +
        # 2,003 (the old 1,294 was only the Study 2 follow-up subsample).
        n_total=9875,
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
        # [RA-2026-07] Table B3 reports SEs/CIs, so "no SE/CI" was stale; the
        # accurate caveat is that effects are raw benchmark-normalized ATEs.
        quality_flags="no SD effect (raw benchmark-normalized ATEs)",
        n_total=573,  # began the survey (487 completed both tasks; 986 allocated)
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
        # [RA-2026-07] Table 2 reports an SE for the main effect, so the old
        # "no SE/CI" flag was stale.
        quality_flags="non-standard outcome (binary exit-ticket pass)",
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
        # [RA-2026-07] Sample is freelance/professional software developers
        # (Sec 5.2.1), not general adults.
        population_category="Professional",
    ),
    "kazemitabaar_etal_2023": dict(
        incentives="None (flat $50 gift card)",
        setting_detail="Canada (recruited from coding camps in two North American cities), online via Google Meet; ages 10-17 (M=12.5)",
    ),
    "contractor_reyes_2026": dict(
        n_total=211,  # 211 attended Session One (Table 1); 204 attended both
        lab_vs_field="Lab",
        incentives="$50 for completing both sessions + lottery tickets ($100 each, 30 drawn) tied to test correctness and essay quality",
        summary="Two-session RCT at Middlebury College randomizing undergraduates to ChatGPT access while learning an unfamiliar topic. Measures effects on test scores and essay quality, immediately and one week later.",
    ),    "dai_etal_2025": dict(
        n_total=387,  # valid samples across both experiments (121 + 266)
    ),
    "kavadella_etal_2024": dict(
        n_total=77,  # randomized (70 sat the unannounced exam)
    ),

}


# ── 3-part paper summaries (setup / empirical strategy / key results) ──────
# From 24 subagents that read each paper and produced structured summaries.
PAPER_SUMMARIES = {
    "franco_etal_2026": {
        "setup": "Pre-registered lab RCT at the University of Nottingham (CedEX lab, December 2024) with 572 analyzed students (604 randomized) from all fields of study. Students studied Esperanto for 15 minutes, then worked practice questions for about 20 minutes under one of three arms: browsing-only control (Google allowed, AI sites blocked), AI-assisted (logged-in premium ChatGPT), or AI-guided (ChatGPT plus brief written guidance on learning-oriented use). All students then took an unaided 15-question exam. Incentives: GBP 5 show-up, GBP 7 for at least 20 correct practice questions, GBP 1 per correct exam answer.",
        "empirical_strategy": "Pre-registered OLS of exam score on treatment indicators with baseline covariates (age, degree level, field of study, prior AI use, paid AI subscription); pre-registered heterogeneity by gender and high-GPA status and binary top-score (>10) and low-score (<5) outcomes. Exploratory prompt analysis links a copy-paste index (share of prompts containing verbatim practice-question text) to study behavior and exam scores.",
        "key_results": "No average effect on exam scores in either AI arm (about 8 of 15 correct in all arms; 0.04 SD AI-assisted, -0.12 SD AI-guided). AI arms attempted 4.2-5.8 fewer practice questions (12-17 percent less) at a higher per-question success rate. Suggestive heterogeneity: high-GPA women gain under guided access while low-GPA students face a higher bottom-tail risk. The heaviest copy-pasters score 16 percent below the control mean; high-GPA women copy-paste least.",
    },
    "contractor_reyes_2026": {
        "setup": "In-person computer-lab RCT with 211 Middlebury College undergraduates across two sessions one week apart. Students were randomized to AI-allowed (logged-in ChatGPT GPT-4o) or AI-forbidden conditions during a 35-minute learning phase on one of three unfamiliar topics (blockchain, carbon capture, CRISPR), then wrote an analytical essay. Incentives: $50 for completing both sessions plus lottery tickets ($100 each, 30 drawn) tied to test correctness and essay quality.",
        "empirical_strategy": "ITT estimated via OLS of outcomes on the AI-allowed indicator, with randomization-strata dummies and double-lasso-selected controls. Robust SEs. A complementary TOT/2SLS specification instruments AI use with random assignment to recover the LATE for compliers.",
        "key_results": "AI access raised immediate Session 1 test scores by 0.27 SD and Session 2 retention test scores (one week later, no AI) by 0.27 SD, with largest gains for middle-performing students. Essay quality gains persisted only for 'augmentation' users who prompted AI to explain concepts; 'automation' users (who used AI to draft) saw Session 1 essay gains fade entirely.",
    },
    "barcaui_2025": {
        "setup": "120 undergraduate business administration students at UFRJ in Rio de Janeiro were randomized (n=60 per arm) to study AI/ML concepts (foundations, methods, applications, ethics) via either ChatGPT (GPT-4, no prompt-engineering guidance) or traditional resources (notes, library databases, non-AI search). Each participant prepared a 10-minute peer-group presentation over two weeks. Participation was voluntary with no course-grade incentive.",
        "empirical_strategy": "Independent-samples t-test on a surprise delayed 20-item MCQ retention test 45 days after the intervention; ANCOVA adjusts for self-reported study time. Three-phase RCT (Oct 2024-Jan 2025) with attrition: 85 of 120 completed the retention test (70.8% follow-up).",
        "key_results": "AI-assisted students scored substantially lower than traditional learners on retention (57.5% vs 68.5%, d=-0.68, 95% CI [-1.12, -0.24], p=.002). They also spent ~45% less time studying; the AI penalty survives time-on-task adjustment.",
    },
    "bastani_etal_2025": {
        "setup": "Field RCT with ~1,000 Turkish high-school students (grades 9-11) at a single school, randomized at the classroom level across three arms: GPT Base (unrestricted GPT-4), GPT Tutor (GPT-4 with guardrails and teacher-designed prompts), or control (course books and notes, no AI). Students completed four 90-minute sessions, each with a lecture, AI-assisted practice, and an unassisted closed-book exam. Performance counted toward course grades.",
        "empirical_strategy": "OLS at the student-session level (N=2,848) regressing normalized 0-1 grades on GPT Base and GPT Tutor indicators (control omitted), with prior GPA and session/grader/grade-level/teacher fixed effects, classroom-clustered SEs. Pre-registered primary outcome is the unassisted exam.",
        "key_results": "On assisted practice, GPT Base raised grades by 0.48 SD and GPT Tutor by 1.26 SD. But on the unassisted exam, GPT Base hurt performance by -0.19 SD (p<0.05) while GPT Tutor was essentially zero. Students used GPT Base as a 'crutch' (copying answers) and overestimated their own learning.",
    },
    "de_simone_etal_2025": {
        "setup": "Student-level RCT in 9 Nigerian public secondary schools in Benin City. 1,328 first-year senior secondary students (~age 15) randomized (657 treatment, 671 control); 759 completed endline. Treatment: 12 after-school sessions (90 min, twice weekly for 6 weeks) in school computer labs using Microsoft Copilot (GPT-4) as a virtual English tutor with teacher-guided prompt toolkit. Control: business-as-usual classroom instruction. No participation incentives reported.",
        "empirical_strategy": "ITT via OLS with school fixed effects and second-term baseline exam score as a control; robust SEs. Robustness via Lee bounds, inverse-probability weighting, and value-added IV/LATE specifications using attendance days.",
        "key_results": "English skills rose by 0.238 SD and total weighted endline by 0.31 SD. Effects extended to the broader-curriculum third-term school exam taken the day after the program ended (0.206 SD) - transfer, not delayed retention. Larger effects for female, higher-baseline, and higher-SES students; benefits across the whole distribution.",
    },
    "fan_etal_2025": {
        "setup": "Lab study at Peking University with 117 university students (mean age 22.6; 55% undergraduate, 45% graduate; all L1 Chinese / English L2). Four-arm design with a shared baseline 2-hour reading-and-writing task followed by a 1-hour revision phase under one of four conditions: CN no support (n=30), AI = ChatGPT 4.0 with guardrails restricting it to task content (n=35), HE = human academic-writing expert (n=25), or CL = AI-powered checklist feedback tool (n=27). No course-grade incentive.",
        "empirical_strategy": "Random assignment to four arms; ANOVA + Tukey HSD on essay-score improvement (post-revision minus pre-revision), knowledge gain (10-item MCQ on AI in education), and knowledge transfer (10-item MCQ on AI in healthcare). Process mining of trace data via first-order Markov models.",
        "key_results": "AI group's essay improvement significantly exceeded all three other arms (d≈0.73 vs CN; F=4.55, p=0.005). But no significant group differences in knowledge gain (d≈-0.05) or knowledge transfer. Trace-data process mining showed AI students looped through tight 'revising-via-ChatGPT' patterns rather than reading and evaluating - the 'metacognitive laziness' the title warns of.",
    },
    "hausman_etal_2025": {
        "setup": "Administrative panel data from a large Israeli research university covering ~36,000 BA/MA/MBA students in ~6,000 courses university-wide across 6 academic years (2018-2019 through 2023-2024), spanning ChatGPT's November 2022 rollout. Treatment: 'AI-compatible' courses (≤60% of grade from in-class/lab work); control: AI-incompatible courses (≥90%). A survey of 91 business-school students shows ChatGPT adoption rising from ~30% in 2022-23 to ~80% in 2023-24.",
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
        "setup": "Online matched-groups RCT (run remotely over Google Meet from Canada) with 69 novice coders ages 10-17 (mean 12.5) recruited from coding camps. None had prior text-based programming. Three-week, ten-session study learning Python via the Coding Steps platform. Codex group (n=33) had unrestricted OpenAI Codex during training only; Baseline group (n=36) had no AI. $50 gift-card compensation. Outcomes at training, immediate post-test (1 day later), and retention (1 week later) - all on Python authoring and modifying tasks.",
        "empirical_strategy": "Matched-groups design: pairs balanced on Scratch pre-test scores, random assignment within pairs. Two-rater independent coding (79% full agreement). Independent-samples t-tests with Cohen's d; Bonferroni-adjusted alpha.",
        "key_results": "Training-phase authoring (with AI): Codex 80.1% vs baseline 44.4% (d=1.67). But on the immediate unassisted post-test, no difference (d=-0.05 authoring, d=0.01 modifying; positive favors Codex). On 1-week retention, modest non-significant Codex advantages (d=0.41 modifying, d=0.38 MCQ overall). Codex-High learners benefited most, suggesting prior competency moderates AI's learning effects.",
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
        "setup": "Pre-registered RCT in 7 English secondary schools with Year 10 students (ages 14-15). 405 recruited, 344 analyzed. Two sessions: a learning session studying two history passages under different conditions, then a test session three days later assessing literal retention, comprehension, and free recall. Three conditions: LLM only (GPT-3.5 Turbo via Azure; up to 20 prompts, hidden meta-prompt, usage strategy unrestricted), Notes only, and LLM + Notes. No incentives.",
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
        # [RA-2026-07] Renumbered to the 2026 arXiv v4: Study 1 is a
        # descriptive Gallup survey (not a Prolific experiment); the editors/
        # Google experiment is Study 3 and the example-only experiment Study 4.
        "setup": "A descriptive Gallup survey (Study 1, N=2,637 young adults) followed by three pre-registered Prolific experiments with US adults examining whether practicing cover-letter writing with a custom GPT-based AI tool helps or hinders writing skill. Experiment participants completed a baseline pretest, a lesson on five writing principles, random assignment to practice conditions, then a no-AI test (and 1-day follow-up in Studies 2 and 4). Study 2 (N=2,238) compared practice-with-AI vs practice-without-AI; Study 3 (N=2,997) added expert-editor feedback and Google Search arms; Study 4 (N=2,003) added an example-only condition.",
        "empirical_strategy": "RCT with random assignment. Writing quality scored by GPT-4o averaging five-principle ratings (alpha=.81), validated against human RA ratings (r=.70). Effects reported as Cohen's d; BH-corrected heterogeneity by demographics and baseline skill.",
        "key_results": "Forecasters expected AI to hinder learning (65% vs 35%); the opposite held. Study 2: AI-practice beat no-AI practice on the test phase (d=0.38) and at 1-day follow-up (d=0.41) despite less effort. Study 3: AI-practice beat editor feedback (d=0.20) and Google (d=0.46). Study 4: merely viewing an AI-generated example improved skill as much as practicing with AI (d=0.37 vs no-AI practice). Mechanism: AI teaches by example.",
    },
    "nie_etal_2025": {
        "setup": "Stanford's free online Code-in-Place 2023 intro Python course. From 8,762 enrollees, 5,831 were active after week 1 and randomized 60/40 (3,581 treated / 2,250 control) across 146 countries. At the start of week 4, treated students received an email and a sidebar button granting access to a custom GPT-4 chat interface with system prompts designed to prevent direct solution-giving. Outcomes: optional 4-hour midterm exam in week 6, weekly homework, section attendance. Only 14.2% of treated actually used the GPT-4 interface.",
        "empirical_strategy": "Two estimands: (1) Advertisement Effect / ITT via difference-in-means; (2) LATE for adopters with treatment as instrument for GPT-4 usage. Missing exam scores handled via MCAR (ignore) or MAR (Ridge regression imputation with 2-fold cross-fitting). Bonferroni-corrected p-values; BCa bootstrap CIs.",
        "key_results": "Advertisement reduced exam participation by 4.3 pp (44.1% vs 48.5%, p=.020) with parallel declines in week-6 homework and attendance. Effect reverses for low-HDI countries (+14.8 pp participation). LATE for adopters with imputation: +6.86 pp exam score (90% CI [0.30, 14.13], ES=0.40). Adopters skew older, male, higher prior section attendance, and from lower-HDI countries.",
    },
    "vanzo_etal_2024": {
        "setup": "RCT at Istituto Pindemonte, a technical institute in Verona (Italy). Four English-as-L2 classes taught by the same teacher: two 3rd-year (n=39) and two 5th-year (n=37); N=76 total. 3rd-year homework was objective grammar exercises; 5th-year was open-ended essay/literature questions. Treatment replaced standard homework with interactive GPT-4 (gpt-4-0125-preview) sessions via a custom web platform; control submitted standard homework on the same platform. 6-8 week intervention. No incentives (voluntary).",
        # [RA-2026-07] Updated to the published ACL 2025 version (the old
        # p=0.087 / words-typed d=1.42 / <1% figures were from the 2024 preprint).
        "empirical_strategy": "Stratified randomization within class by self-reported English GPA. Teacher blind to condition. Pre/post-tests with 24 MCQ items. Cohen's d via one-sided t-tests pooled and by cohort. Weekly Likert engagement questionnaires; OLS regression of learning gains on condition and words typed.",
        "key_results": "Pooled learning gain d=0.251 (not significant). 3rd year d=0.603 (p=0.044, significant). 5th year d=-0.004 (null). Treatment students reported significantly higher interestingness (d=0.59), and words typed was positively associated with learning gains (r=0.434, p=0.007). Weaker students gained more, consistent with personalized scaffolding. Hallucination rate <0.5%.",
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
        "setup": "Quasi-experiment with Chinese undergraduate sophomores (avg age 19.4) in Educational Technology at a Chinese university, all enrolled in 'Instructional Technology and Media' course. 71 randomized: 36 to experimental (ChatGPT 4.0 + paper-based metacognitive scaffolding prompts), 35 to control (ChatGPT 4.0 alone); 3 non-completers left 35 vs 33 analyzed. Task: 4-week interdisciplinary K-12 lesson design assignment integrating math/IT/biology. Participants told data would not affect course grades (no incentives).",
        "empirical_strategy": "Pretest-posttest design. Academic achievement test (40% theory MC/short-answer, 60% practical instructional design, graded by educators) analyzed via ANCOVA with pretest as covariate. SRL via Barnard et al. (2008) questionnaire across six dimensions; t-tests. Cognitive load and technology acceptance via Likert scales. Semi-structured interviews thematically coded.",
        "key_results": "Academic achievement: experimental d=0.36 vs control (F=3.94, p=0.051, marginal). SRL: significant gains in task strategy (d=0.69) and self-evaluation (d=0.53); the control group showed declines across five SRL dimensions. Lower cognitive load (d=-0.47) and higher perceived usefulness in experimental. Interviews showed deeper reflection and critical evaluation of ChatGPT outputs in the scaffolded condition.",
    },
    "chung_etal_2025": {
        "setup": "Five-month 'AI for Python Learning' course (Jan-Jun 2025) in partnership with Taipei City Government across 10 Taipei high schools (8 public, 2 private). 1,047 enrolled; 770 met pre-registration inclusion criteria. Platform combined lecture videos, browser-based coding practice, and an LLM-powered chatbot tutor (both arms); copy-paste was disabled. Students earned a government-endorsed certificate (valid for college applications) by completing modules and passing a proctored final written exam.",
        "empirical_strategy": "Individual-level RCT. Treatment: POMDP-based reinforcement-learning algorithm that adaptively sequences practice problem difficulty using particle-filter belief estimation over knowledge state; uses LLM-derived signals from chat and code-edit traces. Control: fixed easy-to-hard sequence. Same chatbot tutor in both arms. ITT via OLS on standardized final-exam scores. Pre-registered, IRB-approved.",
        "key_results": "Adaptive sequencing raised exam performance by 0.156 SD without controls and 0.150 SD with baseline controls and FE — about 6-9 months of additional schooling. Heterogeneity: beginners gained 0.215 SD; students with prior Python skill gained ~0 SD. Lower-tier schools gained 0.173 SD; higher-tier 0.039 SD. Mediation: engagement (time, attempts) accounts for essentially the full effect; chat quality (LLM-as-judge) was significantly higher in treatment.",
    },
    "liu_etal_2026": {
        "setup": "Three RCTs on Prolific (US adults; the paper reports no pre-registration). Exp 1 (N=307 post-exclusions) gives 12 fraction problems with a GPT-5 sidebar (or no AI) followed by 3 unassisted test problems. Exp 2 (N=585) replicates with a pretest-based exclusion and a matched control sidebar (worked pretest solutions) to remove interface asymmetry. Exp 3 (N=168) extends to SAT reading comprehension (5 learning + 3 test passages); control sidebar contains test-taking tips. AI was pre-prompted with each problem and solution, allowing one-word answer requests. Skipping was costless. Pay: $2.60-$3.40.",
        "empirical_strategy": "Random assignment to AI vs control at study entry. Primary outcomes: mean solve rate and skip rate on the final 3 unassisted test problems. Two-sample t-tests on participant means with Cohen's d. Exp 2 adds heterogeneity by self-reported AI usage type (direct answer vs hints vs no use).",
        "key_results": "AI access lowers unassisted solve rates: Exp 1 d=-0.42, Exp 2 d=-0.19, Exp 3 d=-0.42. Skip rates rise (Exp 1 d=0.25, Exp 3 d=0.42). Decline concentrates among the 61% who used AI for direct solutions; hint-users (27%) scored like controls (0.76 vs 0.77) and non-users (12%) slightly above (0.89). Effects emerge after only ~10-15 minutes of exposure.",
    },
    "shen_and_tamkin_2026": {
        "setup": "Between-subjects online RCT with 52 experienced Python developers (≥1 year Python, no prior Trio library experience) recruited through a crowdwork platform. Flat $150 fee. After a warm-up coding task to calibrate Python familiarity, participants had up to 35 minutes to complete two Trio asynchronous-programming tasks on an online coding-interview platform. Treatment (n=26): chat-based GPT-4o coding assistant prompted to produce full correct solutions. Control (n=26): no AI. Both groups then took a 14-question, 27-point Trio quiz with no AI permitted.",
        "empirical_strategy": "Pre-registered between-subjects randomization with balance on coding experience, Python frequency, prior asyncio use, and async-familiarity score. Primary outcomes: Trio quiz score and task completion time; treatment effects as differences in means and Cohen's d, with one specification controlling for warm-up time. Exploratory analyses decompose quiz scores by question type and qualitatively annotate screen recordings into AI-interaction patterns.",
        "key_results": "AI assistance reduced quiz scores by 4.15 points on the 27-point quiz (Cohen's d=0.738, p=0.010). No significant difference in task completion time; all 26 AI participants finished both tasks while 4 of 26 controls did not. Control outperformed treatment across all experience strata. Three of six AI-interaction patterns (involving cognitive engagement) preserved learning; full-delegation patterns showed productivity gains but worst learning.",
    },    "ba_etal_2024": {
        "setup": "In 2023, 77 medical interns (42 male, 35 female) in Sun Yat-sen University's five-year MBBS program completed a two-week pediatric cardiology internship rotation at the First Affiliated Hospital in Guangzhou, China. They were randomly allocated across four rotation groups into a ChatGPT-assisted arm (39) or a standard bedside-teaching arm (38). The ChatGPT-assisted arm used ChatGPT version 4.0, configured to the rotation's objectives, to interactively explore dynamically generated pediatric case vignettes (history-taking, physical exams, differential diagnosis, treatment), with educators reviewing student work and giving feedback. Both arms saw identical cases (e.g., Kawasaki disease, congenital heart disease, nephrotic syndrome), the same instructors, teaching materials (9th-ed. 'Pediatrics' textbook), and course intensity. Assessments were embedded in the rotation and no monetary incentives were reported.",
        "empirical_strategy": "Interns were randomized via a computer-generated list stratified by baseline clinical examination scores, with blinded Mini-CEX assessors; groups were balanced on gender, age, and baseline scores (p>0.05). The primary knowledge contrast is a between-group comparison of post-rotation closed-book theoretical exam scores using an independent-samples t-test (analyzed in R 4.2.2 and SPSS 26). For the atlas, Cohen's d and its standard error were back-calculated from the reported group means and SDs (d=-0.067, SE=0.228); the source meta-analysis reports Hedges g=-0.07, 95% CI [-0.51, 0.38].",
        "key_results": 'Theoretical exam scores were statistically indistinguishable and near ceiling: ChatGPT 92.21±2.37 vs traditional 92.38±2.68 out of 100 (t=0.295, p=0.768; d=-0.067). Mini-CEX clinical-skills ratings favored the ChatGPT group on clinical judgment (p=0.032), doctor-patient communication (p=0.02), professionalism (p=0.022), and overall competence (p=0.006), but these are reported as categorical case counts/percentages rather than means, so they are not SMD-extractable. Trainee satisfaction with the ChatGPT method was uniformly high, with no reported dissatisfaction.',
    },
    "bassner_etal_2026": {
        "setup": "A three-arm randomized controlled trial run in an introductory programming (CS1) course for management/technical students at the Technical University of Munich, Germany. During regular 90-minute on-site tutorial sessions (35 sessions led by 19 tutors), students attempted a challenging Java concurrency exercise ('Divide and Conquer', implementing a parallel sum with threading primitives); 452 initially participated and 275 remained after eight sequential data-quality filters. Each student was assigned to one of three conditions: Iris, a scaffolded LLM tutor that gives calibrated hints but withholds full solutions; unrestricted ChatGPT that supplies complete solutions on demand (both built on OpenAI GPT-4.0); or a no-AI control using lecture slides and web resources with AI tools prohibited and monitored. Students earned course bonus points simply for participating seriously, independent of their survey answers or exercise score. Pre/post knowledge tests and a post code-comprehension task measured learning, while the Artemis platform auto-graded exercise performance.",
        "empirical_strategy": "Assignment to the three arms was randomized using students' university IDs as the seed; baseline balance on gender, programming experience, and age was confirmed (Table 3, all p>.05). Analyses were complete-case on the 275 students passing the quality filters (39.2% excluded). The paper compared arms with one-way ANOVA (Welch's when variances were heterogeneous) using generalized eta-squared, a repeated-measures ANOVA for pre-post knowledge, and Tukey HSD / Games-Howell post-hoc tests; no adjustment for clustering within the 35 tutorial sessions is reported. For this dataset, knowledge-gain effects are meta-analyst-computed Cohen's d standardized by the pooled pre-test SD (Morris), code-comprehension effects are Cohen's d on post-only means/SDs, and the exercise-performance effect is the paper's own reported Cohen's d; all SEs use the large-sample d formula.",
        "key_results": "Both AI arms sharply outperformed the no-AI control on the exercise itself: ChatGPT users passed 71.84% of test cases and Iris users 57.50%, versus 29.85% for control (one-way ANOVA F=29.69, eta_g^2=.179, p<.001; ChatGPT vs control d=1.10). Yet this performance gain did not carry over to learning: pre-post knowledge gains were statistically indistinguishable across arms (gains 0.83 ChatGPT / 0.71 Iris / 0.85 control on a 0-6 test; Group x Time F=0.26, p=.773), and post-intervention code comprehension did not differ (1.36 / 1.43 / 1.18 on a 0-3 test; F=2.01, p=.136). Both AI tools reduced frustration and extraneous/germane cognitive load relative to control, but only Iris raised intrinsic motivation (d=0.55, p<.001), while ChatGPT, rated easier and more helpful, showed no motivational benefit, which the authors call a 'comfort trap.'",
    },
    "dai_etal_2025": {
        "setup": "Two sequential five-week randomized controlled trials with 387 Grade 10 physics students at a single high school in southwest China (Experiment 1 n=121; Experiment 2 n=266), reported as an arXiv preprint in May 2025. A custom LLM+RAG feedback system generated heuristic solution hints (personalized diagnosis, emotional support, no direct answers) for students' homework problems; because the school bans classroom devices, all interaction was paper-based, with students marking errors on sheets that were scanned via OCR and printed feedback returned the next day. Experiment 1 tested compulsory personalized recommendation of previously-missed problems (GAI hints + workbook answers vs workbook-only recommendation vs no recommendation); Experiment 2 tested autonomous on-demand help, comparing full learner control over feedback type, system/shared control, and a no-intervention control. There was no monetary incentive; the outcome was the school's regular high-stakes end-of-term physics exam, taken without AI.",
        "empirical_strategy": "Within each class, students were individually randomized (stratified) across the three arms, and baseline equivalence was confirmed by one-way ANOVA (Exp 1 pretest F(2,118)=0.09, p=.914; Exp 2 F(2,263)=0.56, p=.571). All exam and questionnaire scores were converted to z-scores before analysis, so the OLS regression coefficients are Cohen's d. Models control for pretest score, pretest self-regulation (Exp 1) / learner autonomy (Exp 2), and class fixed effects, with robust standard errors computed at the individual level (the unit of randomization). Estimates are complete-case, using only students with valid pre- and post-intervention data (76% retained in Exp 1, 71% in Exp 2).",
        "key_results": 'On the unassisted final physics exam, the full-sample AI-vs-control effects were small and non-significant: Experiment 1 compulsory hints (Group A vs C1) d=0.212 (SE 0.154); Experiment 2 on-demand help d=0.032 (SE 0.094) when students chose the feedback type (Group D) and d=0.111 (SE 0.098) when the system chose (Group E). Significant achievement gains were confined to subgroups: low-achieving students in Experiment 1 improved by d=0.673 (p<0.05), and high-achieving students under fully learner-controlled help in Experiment 2 improved by d=0.378 (p<0.05). The paper also documents declines in self-regulation/autonomy for other subgroups (e.g., top-third SRL d=-0.477 in Exp 1; full-sample learner autonomy d=-0.274 for Group D in Exp 2), reported as secondary outcomes outside the achievement focus.',
    },
    "fischer_etal_2025": {
        "setup": "Fischer, Rau, and Rilke ran a preregistered artefactual field (lab) experiment with 334 university students in the experimental economics lab of the Technical University of Berlin in February 2025 (14 sessions, ~24 participants each, individual cubicles). After a common baseline test, students had a 25-minute learning phase to study two excerpts (5 and 7 pages) from Varian's Intermediate Microeconomics with Calculus and were individually randomized to one of three conditions: textbook-only control, unrestricted AI tutor access (AI chat + textbook throughout), or restricted access (textbook only for the first 10 minutes, then AI + textbook for the final 15). The AI tutor was 'acemate,' a GPT-4-based system using retrieval-augmented generation over the specific course PDFs. All students then took the same 25-item multiple-choice test with no access to the textbook or AI. All 50 test items and two self-performance estimates were incentivized at €0.25 each, with average pay of €16.72 for a ~75-minute session.",
        "empirical_strategy": "Students were individually randomized to the three arms within each session, so treatment status is balanced across sessions. Treatment effects come from preregistered covariate-adjusted OLS on the standardized Test 2 score, controlling for the baseline Test 1 score, a Bachelor indicator, and field-of-study (9), semester (10), and session (14) fixed effects. Standard errors are heteroskedasticity-robust. The estimand is intention-to-treat; the pooled 'any AI' specification (Col. 1) tests H1 and the two-arm split (Col. 2) tests H2.",
        "key_results": 'Any AI tutor access raised unassisted test scores by 0.227 SD (SE 0.106, p<0.05). The effect was concentrated in the unrestricted arm (0.337 SD, SE 0.116, p<0.01); the reading-first restricted arm was not significant (0.132 SD, SE 0.122). Contrary to the preregistered H2, unrestricted access outperformed restricted access by 0.21 SD (F-test p=0.066). Benefits were largest for students with lower baseline knowledge and stronger self-regulation (low procrastination, low distraction preference).',
    },
    "gan_etal_2024": {
        "setup": "Third-year undergraduate medical students at the Medical College of Jinan University, China, were recruited by convenience sampling in April 2023. Of 129 students assessed for eligibility, 4 were excluded before randomization (2 not meeting criteria, 2 declining), and 125 were randomized (sealed envelopes; 60 ChatGPT, 65 control per the CONSORT diagram) to spend a one-week review period studying orthopedics with either ChatGPT-4.0 only (no other search engines or forums) or ordinary internet forums and search engines with no OpenAI tools; 15 withdrew after randomization, leaving 110 completers (54 ChatGPT, 56 control). All students then sat a 214-item orthopedics multiple-choice examination, and their end-of-semester final exams in five clinical subjects were later collected as long-term outcomes. Participants received participation rewards (verified by the hospital's Science and Technology Department) that were not tied to test scores; all study materials, instruction, and testing were in Chinese.",
        "empirical_strategy": "Randomization used sealed envelopes prepared by an uninvolved clinician, and the outcome collector was blinded to group assignment; the arms were balanced at baseline on age, sex, GPA, and pre-intervention practice accuracy (all P>.05). Between-group differences were tested with independent-samples two-tailed t tests in SPSS 26 (normality by Kolmogorov-Smirnov, variance homogeneity by Levene, alpha=.05). Analysis is per-protocol (complete-case, 110 completers) with no intention-to-treat. The paper reports each mean difference and its standard error (labeled 'SD') but no standardized effect sizes or confidence intervals; the SD-scale effect for the primary exam (Cohen's d=0.398, SE 0.193) is back-calculated from the per-arm means and SDs.",
        "key_results": "On the primary 214-item orthopedics exam the ChatGPT group scored higher (mean 141.20, SD 26.68) than controls (130.80, SD 25.56), a difference of 10.40 points (SE 4.98, P=.04; d≈0.40), with significant gains on A1, A2, and A3/A4 items and a non-significant deficit on case-analysis items. Among the five end-of-semester final exams, the ChatGPT group scored significantly higher in surgery (76.54 vs 72.54, P=.02; d=0.446, SE 0.193, back-calculated) and obstetrics/gynecology (75.98 vs 72.54, P=.04), while internal medicine (P=.88), pediatrics (P=.38, ChatGPT lower), infectious diseases (P=.36), and the total final-exam difference (7.71 points, P=.31) were not significant. Note the Results body misprints the ChatGPT exam mean as 138.46 (SD 26.97); the abstract's 141.20 (SD 26.68) is internally consistent with the reported 10.40 difference and 4.98 SE.",
    },
    "hou_etal_2026": {
        "setup": "Ninety-five undergraduates at Michigan Technological University (recruited to have no prior construction-management or BIM coursework or experience) completed an online, individually administered experiment on Qualtrics (arXiv June 2026; research team at Michigan Tech and Western Michigan). All first studied identical PowerPoint materials on introductory construction concepts (a common baseline), then were randomly assigned to one of three review conditions: continued slide review (control), free-form 'unprompted' use of a course-grounded retrieval-augmented (RAG) generative-AI assistant, or 'prompted' AI use following a five-step Generative-Learning-Theory framework (Clarify, Organize, Integrate, Differentiate, Correct). The AI platform, instructional corpus, configuration, and review duration were identical across the two AI arms. No participant incentive or compensation is mentioned. The study is NSF-funded (award #2417804).",
        "empirical_strategy": "Participants were randomly assigned to the three arms (recruited 45 control / 37 prompted / 37 unprompted; analyzed 33 / 29 / 33 after 24 incomplete cases were dropped for missing UEQ or performance data). Group differences were tested with one-way (three-group) ANOVA on each outcome; the paper reports only omnibus F and p, not pairwise contrasts. Pairwise Cohen's d for each AI arm vs the slide-only control was back-calculated from the per-arm means, SDs, and Ns in Table 3, with SE(d) from the standard large-sample formula. The design is post-test-only, with no pre-test covariate or other adjustment (the baseline phase is common exposure, not a measured control).",
        "key_results": 'On the total post-test (max 27), the guided/prompted arm scored 18.86 vs 15.35 for slide-only control (+3.51 points, d~0.86), while the free/unprompted arm was essentially identical to control (15.73 vs 15.35, d~0.09). The gain was concentrated in open-ended reasoning items (guided 12.41 vs control 9.68 on max 18, d~1.06; omnibus F=7.32, p=0.0011) with no significant effect on multiple-choice recall (F=2.38, p=0.099). The authors conclude that access to AI alone does not improve learning outcomes; the structure of the interaction does.',
    },
    "huang_etal_2025": {
        "setup": 'In October-November 2024, the authors ran a single-site randomized controlled trial with fourth- and fifth-year undergraduate dental students at Wuhan University, a top-tier Chinese university; 192 were recruited and 5 were excluded at eye-tracking calibration, leaving 187 analyzed (ages 20-25, mean 22.53). Both arms received the same instructional videos for a hands-on operative skill. The ChatGPT group (n=94) could additionally consult ChatGPT-3.5 (the free version) during a one-week skill-acquisition period to resolve doubts, verify procedures, and get extra guidance, while the blank control group (n=93) used videos only. After the week, both groups took an operative-skill test on a desktop-VR simulator (auto-scored, 0-100), plus tests of theoretical knowledge, spatial ability (Purdue Spatial Visualization Test), cognitive load (pupillometry), learning motivation, and self-efficacy. No participant compensation or incentives were reported.',
        "empirical_strategy": "Students were randomized to the ChatGPT-3.5 or blank-control arm using the sealed-envelope method. The primary operative-performance contrast used an independent-samples (Welch) t test on post-test VR scores, t(176.24)=4.569, with normality checked via Shapiro-Wilk; motivation and self-efficacy used Mann-Whitney U tests, and cognitive load used a t test on pupil-diameter change. The authors reported per-arm means and SDs but no standardized effect size, so Cohen's d (0.669) and its SE (0.150) were back-calculated from the reported means, SDs, and per-arm n. The analysis is complete-case on the 187 students who passed eye-tracking calibration.",
        "key_results": 'The ChatGPT group scored higher on the desktop-VR operative test (mean 73.12, SD 10.06) than the video-only control (mean 65.54, SD 12.48), a 7.58-point gap on the 0-100 scale (P<.001), roughly 0.67 SD. Pre-intervention theoretical knowledge was balanced (41.24 vs 42.03, P=.52). The gain was concentrated among low-spatial-ability students (70.20 vs 55.41, P<.001) and absent among high-spatial-ability students (76.58 vs 73.89, P=.22). Secondary outcomes also favored ChatGPT: lower cognitive load via pupil-diameter change (0.137 vs 0.312, P<.001), higher self-efficacy (P=.04), and higher learning motivation (P=.02).',
    },
    "kavadella_etal_2024": {
        "setup": "In March 2023, 77 second-year dental students at the English-speaking School of Dentistry of European University Cyprus (Nicosia) were randomized into two groups to complete a collaborative learning assignment on 'Radiation Biology and Radiation Protection in the Dental Office,' part of the Dentomaxillofacial Radiology module. One group used ChatGPT to research and compose the assignment; the other searched the internet and scientific literature (the module's traditional method). Both worked in small subgroups of 3-7, produced a PowerPoint presentation, and presented it in class; the ChatGPT group additionally logged every prompt and interaction, critiqued the LLM's output against a textbook, and answered an open-ended evaluation questionnaire. Students had one month to complete the assignment. Learning was assessed by an unannounced, anonymous, ungraded 10-MCQ exam given at the start of the presentation session, framed as a diagnostic for the educator, so it carried no grade incentive.",
        "empirical_strategy": 'Students were randomly assigned to the ChatGPT arm (n=39) or the literature-research arm (n=38); 70 sat the exam (39 ChatGPT vs 31 literature; 7 absent). Differences in exam grades were tested with the nonparametric Mann-Whitney U test in SPSS v25, with significance set at p=.05. The paper reports only group means, SDs, and the Mann-Whitney p-value, with no regression adjustment; the standardized effect size (d approx 0.52) and its SE (approx 0.25) shown here are back-calculated from the reported means, SDs, and group sizes.',
        "key_results": 'The ChatGPT group scored significantly higher on the unannounced exam: mean 7.54 (SD 1.18, n=39) versus 6.94 (SD 1.12, n=31), a 0.60-point gap on the 0-10 scale (Mann-Whitney p=.045). Grades ranged from 5 to 10 with no low-range scores; the ChatGPT group dominated the 8-10 band while the literature group did better in the 5-7 band. In the mixed-methods qualitative component, thematic analysis of free-text questionnaires from 31 of 39 ChatGPT students surfaced perceived benefits (human-like interface, immediate responses, broad knowledge base), limitations (need to rephrase prompts, generic content, false or hallucinated citations, no images or videos), and future prospects in education, clinical practice, continuing education, and research.',
    },
    "learnlm_team_2026": {
        "setup": "The LearnLM Team (Google DeepMind and Fab AI) ran a preregistered two-arm cluster randomized controlled trial (AEARCTR-0016651) across 12 government-supported junior secondary schools in Port Loko District, Sierra Leone, from 6 October to 5 December 2025. The trial enrolled 1,763 grade 7 and 8 students (aged 13 or older) in 48 mathematics classrooms. In treatment classrooms, teachers integrated Gemini's Guided Learning feature into two of four weekly math periods (90 minutes per week, a requested ~12 hours over eight weeks), with students working in pairs at a 2:1 student-to-device ratio; control classrooms continued standard instruction with no AI. Both arms received identical 5-6 hour teacher training via a cascade model. Students received no incentives; the endline math assessment, developed and scored blind to assignment by Oxford MeasurEd, was itself the outcome and was taken unassisted.",
        "empirical_strategy": 'Randomization was at the classroom level within school-by-grade blocks (48 classrooms as clusters), with block fixed effects and standard errors clustered at the classroom level (48 clusters). The headline intent-to-treat estimate is an ANCOVA regression of the IRT-scaled endline math score on treatment assignment, controlling for baseline math and reading scores (Table C.4, col 2), on the balanced panel of students present at both waves (N=1,423). Treatment-on-the-treated effects use 2SLS, instrumenting completion of the requested 12 hours (and, separately, total dosage hours) with random assignment (Tables C.6-C.7). Field monitors logged implementation fidelity and spillover; documented spillover was negligible and would only attenuate the estimates.',
        "key_results": 'Guided Learning raised endline math scores by 0.258 SD (ITT; 95% CI [0.027, 0.488], p=0.029), which the authors benchmark at roughly 1.2-1.7 years of additional learning in low- and middle-income countries. Among students who completed the requested 12 hours, the treatment-on-the-treated effect was 0.380 SD (95% CI [0.040, 0.719], p=0.029), with a per-hour dosage effect of 0.016 SD. Uptake was unexpectedly high: 69.0% of the 871 students in treatment classrooms reached the 12-hour threshold, and treatment classrooms averaged about 15 hours. Effects were larger for students with higher baseline math skills (+0.195 SD per baseline SD, p=0.002).',
    },
    "stromberg_etal_2026": {
        "setup": "The authors assemble 30 months (January 2023 to June 2025) of administrative panel data covering 26,811 students in grades 7-12 across all nine secondary schools of one county in central China (~90% of the county's secondary students; 524 classes). A June 2025 survey with >96% valid response recorded the month each student first adopted generative AI (teachers instructed students to check AI-tool registration dates) and weekly hours of use; roughly 80% had adopted by June 2025, using general-purpose chatbots (Doubao, DeepSeek, ChatGLM, Ernie Bot, Qwen), most often for math (66%) and English (55%). The education bureau's grade system supplies weekly platform-timestamped homework scores and completion times, monthly closed-book in-class exams in 7-9 subjects, county-wide joint exams, and centrally graded Zhongkao and Gaokao entrance-exam scores. All scores are rescaled to percent of the pre-adoption baseline mean.",
        "empirical_strategy": "Staggered difference-in-differences in each student's self-reported first-adoption month, estimated with the Callaway-Sant'Anna (2021) regression-adjustment estimator against never-AI students (robustness: not-yet-treated controls; OLS and extended TWFE give near-identical results), with standard errors clustered at the class level. Identification rests on parallel trends rather than random assignment; the paper documents covariate balance (standardized differences below 0.1 with one exception at 0.103), flat pre-trends, a falsification showing only 5 of thousands of never-AI students ever experience a comparable six-month score drop, a placebo on the pre-AI 2022 Zhongkao (0.104, SE 0.351), and null spillovers onto classmates. Entrance-exam effects come from OLS with pre-AI scores, demographics, and class fixed effects; the authors note this identification is weaker because each entrance exam is observed once. Adoption timing is self-reported and retrospective, the design's main vulnerability.",
        "key_results": "Homework productivity jumps while learning falls. Six to ten months after adoption, homework scores are up 18.13% of the baseline mean (SE 0.19; the authors' stated 1.9 SD) and completion time is down about 19 minutes, but monthly closed-book exam scores are down 20.05% (SE 0.41), a 1.4 SD decline that stabilizes after six months. Entrance-exam regressions with full controls show adopters scoring 5.2% lower on the Zhongkao (SE 0.38) and 5.3% lower on the Gaokao (SE 0.62); dynamic estimates reach -24% and -18% (about -1.5 and -1.2 SD) for students who adopted 2+ years before the exam. Losses are largest in social sciences, then STEM, and are bigger for junior, high-achieving, and male students. 81% of students using AI for 5+ months show homework-outsourcing patterns (very short completion times with high homework scores), and the learning losses concentrate among them.",
    },
}


# ── Per-estimate overrides (verification passes) ────────────────────────────
# Override specific fields per estimate_id. Entries below marked [RA-2026-07]
# come from the July 2026 RA verification workbook, re-verified against each
# paper's PDF. Policy: effect_size_sd/se/ci hold SD-unit values ONLY; raw
# (points / pp / grade-point) coefficients live in `notes` with explicit units.
ESTIMATE_OVERRIDES = {
    # Bastani: PNAS version uses SD-standardized SEs throughout; current xlsx
    # has Table 1 raw SEs for the practice estimates. Override to SD units.
    "bastani_etal_2025__est1": {"se": 0.108, "n_total": 2848},
    "bastani_etal_2025__est2": {"se": 0.112, "n_total": 2848},
    "bastani_etal_2025__est3": {"n_total": 2848},
    "bastani_etal_2025__est4": {"n_total": 2848},

    # [RA-2026-07] Barcaui: analysis is on the 85 completers (43+42), not the
    # 120 randomized (Table 2, p.6-7).
    "barcaui_2025__est0": {"n_total": 85},

    # [RA-2026-07] Kazemitabaar post-test: baseline outscored Codex (62.9% vs
    # 61.3%, Sec 5.2.1), so under the positive-favors-AI convention d = -0.05.
    # NOTE: literature_effects.csv (paper Figure 5) still carries +0.05.
    "kazemitabaar_etal_2023__est19": {
        "effect_size_sd": -0.05, "ci_lower": -0.522, "ci_upper": 0.422,
        "notes": "Post-test 1 day after training; no AI access. Baseline group "
                 "scored slightly higher (62.9% vs 61.3%), so the sign is negative "
                 "under the positive-favors-AI convention. Not significant (p=.838).",
    },

    # [RA-2026-07] De Simone: regression Ns are 654/654/636 (Tables 2-3), not
    # the 759 completers; arm split not reported for the analysis samples.
    # Third-term exam was taken 7/12/24, one day after sessions ended -> immediate.
    "de_simone_etal_2025__est5": {
        "n_total": 654, "n_treatment": None, "n_control": None,
        "notes": "ITT. 6-week intervention, 12 sessions of 90 min. School FE and "
                 "baseline controls. Regression N=654 (Table 2); 759 completers.",
    },
    "de_simone_etal_2025__est6": {
        "n_total": 654, "n_treatment": None, "n_control": None,
        "notes": "Main outcome. Equivalent to 1.5 years of business-as-usual "
                 "schooling. Regression N=654 (Table 3); 759 completers.",
    },
    "de_simone_etal_2025__est7": {
        "n_total": 636, "n_treatment": None, "n_control": None,
        "outcome_timing": "immediate",
        "notes": "Broader-curriculum school exam taken the day after sessions "
                 "ended (Table 14) - transfer, not delayed retention. Regression "
                 "N=636 (Table 2).",
    },

    # [RA-2026-07] Fan: n_total should be the two-arm comparison sample
    # (AI vs CN), not the four-arm study total (Appendix Tables 1-2).
    "fan_etal_2025__est8": {"n_total": 62},
    "fan_etal_2025__est9": {"n_total": 58},

    # [RA-2026-07] Hausman: all effects are raw grade points on a 0-100 scale,
    # not SD units. Keep SD columns empty; raw values documented in notes.
    "hausman_etal_2025__est10": {
        "se": None,
        "notes": "Effect of early AI exposure on subsequent advanced course "
                 "performance. Raw effect: +0.928 grade points (0-100 scale), "
                 "SE 0.229 (Table 5 col. 3). Not in SD units.",
    },
    "hausman_etal_2025__est11": {
        "se": None,
        "notes": "Year 2 after rollout; effect larger than Year 1. ~80% AI "
                 "adoption in 2023-24. Raw effect: +1.484 grade points (0-100 "
                 "scale), SE 0.406 (Table 2). Not in SD units. n_total is the "
                 "course-enrollment observation count of the full regression "
                 "sample; arm Ns come from a narrower specification and do not "
                 "sum to n_total by design. [Codex audit note, 2026-07]",
    },
    "hausman_etal_2025__est12": {
        "se": None,
        "notes": "ITT effect (AI availability, not use). Student FE + semester FE "
                 "+ course controls. ~30% AI adoption in 2022-23. Raw effect: "
                 "+0.970 grade points (0-100 scale), SE 0.289 (Table 2). Not in "
                 "SD units. n_total is the course-enrollment observation count "
                 "of the full regression sample; arm Ns come from a narrower "
                 "specification and do not sum to n_total by design. [Codex "
                 "audit note, 2026-07]",
    },
    "hausman_etal_2025__est13": {
        "se": None,
        "notes": "Course-semester level. Largest effects for weakest students. "
                 "Raw effect: +3.014 grade points at the 25th percentile (0-100 "
                 "scale), SE 0.933 (Table 4). Not in SD units.",
    },

    # [RA-2026-07] Henkel: endline is the end-of-intervention post-test (no
    # retention wave); intervention ran Feb-Aug 2023 (~8 months, not ~6).
    "henkel_etal_2024__est15": {
        "outcome_timing": "immediate",
        "treatment": "Rori AI math tutor (2x30min/week, Feb-Aug 2023)",
    },

    # [RA-2026-07] Kalam: df-weighted pooled-SD Cohen's d = 2.48 (Table 2 means/
    # SDs); Week 1 quiz was taken with assigned resources in hand (ChatGPT arm
    # could query ChatGPT during the quiz) -> outcome_with_ai set in map below.
    "kalam_etal_2025__est16": {
        "effect_size_sd": 2.48,
        "notes": "Quiz WITH assigned resources in hand (ChatGPT arm could query "
                 "ChatGPT during the proctored quiz). Very small sample. Scores: "
                 "9.60 vs 6.64; df-weighted pooled-SD Cohen's d.",
    },

    # [RA-2026-07] Kim: est23 SE 0.01 was the raw log-scale SE next to an empty
    # effect; move raw values to notes. est24 paired a crude d (0.2) with the
    # raw SE (0.001); convert SE to the same IQR-based SD units.
    "kim_etal_2025__est23": {
        "se": None,
        "notes": "DiD exploiting staggered rollout. Student and date FEs. 2.1M "
                 "student-day obs. Raw effect: +0.3057 log points (SE 0.0103, "
                 "p<0.01) = ~35.8% more problems/day; no SD conversion available.",
    },
    "kim_etal_2025__est24": {
        "se": 0.008, "ci_lower": 0.184, "ci_upper": 0.216,
        "quality_flags": "not RCT; non-standard outcome; active control",
        "notes": "DiD design. Raw effect +2.64pp on ~74% base (Table 2: 0.0264, "
                 "SE 0.0011); d approximated via IQR-based SD 0.133, SE converted "
                 "to the same units. Low-performing students benefit most.",
    },

    # [RA-2026-07] Kreijkes: est25/est26 stored the paper's raw-point SE/CI
    # next to SD-unit effects (CIs did not contain the point estimates).
    # Converted to SD units via delta method from Table 3 raw B/SE.
    "kreijkes_etal_2026__est25": {
        "se": 0.060, "ci_lower": -0.557, "ci_upper": -0.323,
        "notes": "Within-subject (Group 1). Test 3 days post-learning. Negative = "
                 "LLM worse than notes. SE/CI converted to SD units from raw "
                 "B=1.92 (SE 0.26), Table 3.",
    },
    "kreijkes_etal_2026__est26": {
        "se": 0.068, "ci_lower": -0.513, "ci_upper": -0.247,
        "notes": "Within-subject (Group 1). Test 3 days post-learning. SE/CI "
                 "converted to SD units from raw B=0.95 (SE 0.17), Table 3.",
    },

    # [RA-2026-07] Lehmann Study 1: est32 is the FE estimate (Table 2: -0.02,
    # SE 0.00); its stored SE 0.02 belonged to the IV row (est35, Table 3).
    # est34's raw coefficient (-1.407, SE 0.525, Table 10) converted to SD
    # units by the pooled post-test SD 4.6 used for the subgroup rows.
    # Studies 2/3 arm splits are not reported in the paper.
    "lehmann_etal_2024__est32": {
        "se": None,
        "notes": "Study 1 (field). Continuous treatment. Raw FE coefficient -0.02 "
                 "per unit of cumulative ChatGPT similarity (SE 0.00, p<0.001, "
                 "Table 2). 6,594 student-question obs.",
    },
    "lehmann_etal_2024__est33": {
        "n_treatment": 38, "n_control": 31,
        "notes": "Study 3 (replication with copy-paste). d~0.42 back-calculated "
                 "from Table 6 means/SDs. Arm Ns 38/31 are not printed in "
                 "Table 6; recovered from Table 15 covariate proportions "
                 "cross-checked with Table 10's treated N=94 (the stored SE "
                 "0.245 reproduces only under this split). Marginally "
                 "significant in t-test, null in regression. "
                 "[2026-07 W. Erda verification round]",
    },
    "lehmann_etal_2024__est34": {
        "effect_size_sd": -0.306, "se": 0.114,
        "ci_lower": -0.530, "ci_upper": -0.082,
        "notes": "Exploratory. Treated subjects only. Copy-paste as exogenous "
                 "shifter of substitutive use. Raw coefficient -1.407 post-test "
                 "questions (SE 0.525, p=0.009, Table 10 col 2); converted to "
                 "SD units by the pooled post-test SD 4.6 across all four arms "
                 "of Studies 2-3 (arm SDs 4.2/4.7/4.4/5.1, Ns 51/56/31/38; "
                 "n-weighted pooled SD = 4.60). The treated-only post-test SD "
                 "would be ~4.9. [provenance documented 2026-07, W. Erda round]",
    },
    "lehmann_etal_2024__est35": {
        "notes": "FE2SLS using ChatGPT service outages as IV. Raw IV coefficient "
                 "-0.06 per unit of cumulative similarity (SE 0.02, p=0.002, "
                 "Table 3). N=6,594 obs. Continuous treatment.",
    },
    "lehmann_etal_2024__est36": {
        "n_treatment": 56, "n_control": 51,
        "notes": "Study 2. No copy-paste available (unintended). d~0.25 "
                 "back-calculated from Table 4 means/SDs. Arm Ns 56/51 are not "
                 "printed in Table 4; recovered from Table 15 covariate "
                 "proportions cross-checked with Table 10's treated N=94. Not "
                 "significant. [2026-07 W. Erda verification round]",
    },

    # [RA-2026-07] LearnLM UK: the stored CIs were percentage-point ATE
    # intervals sitting in the SD-unit CI columns; moved to notes with pp
    # units. [W. Erda round] Ns are session-level analyzed samples (Tables
    # F.1/F.4): the two-level design randomized 165 STUDENTS to static hints
    # (91) vs tutoring (74), then each tutoring SESSION to human tutor vs
    # supervised LearnLM within the 74 -- so the old 74/91/165 student counts
    # were not this contrast's analyzed sample.
    "learnlm_team_2025__est29": {
        "ci_lower": None, "ci_upper": None,
        "notes": "Key learning outcome: transfer to new topic. ATE +10.1pp, 95% "
                 "CI [+4.6, +15.4] (Table F.6; pp units). OR=1.6 [1.2, 2.0]. "
                 "P(LearnLM>hint)>99.9%. Ns are session-level analyzed samples "
                 "(Table F.4: LearnLM 328, static hints 2,385) from the "
                 "two-level design (91 students static hints vs 74 tutoring; "
                 "sessions randomized within the 74).",
    },
    "learnlm_team_2025__est30": {
        "ci_lower": None, "ci_upper": None,
        "notes": "Bayesian logistic regression. ATE +27.7pp, 95% CI [+24.6, "
                 "+30.4] (pp units). OR=7.4 [5.1, 11.0]. Human tutor supervised "
                 "LearnLM messages. Ns are session-level analyzed samples "
                 "(Table F.1: LearnLM 467, static hints 3,301); 165 students "
                 "in the trial overall.",
    },
    "learnlm_team_2025__est31": {
        "ci_lower": None, "ci_upper": None,
        "notes": "ATE +5.5pp over human tutoring on transfer, 95% CI [-1.4, "
                 "+12.4] (pp units). OR=1.3 [0.9, 1.7]. P(LearnLM>human)=93.6%. "
                 "Both arms within the 74 tutoring students (session-level "
                 "randomization); Ns are analyzed sessions (Table F.4: LearnLM "
                 "328, human tutor 376).",
    },

    # [RA-2026-07] Lira: site links the 2026 arXiv v4, whose numbering merges
    # the 2025 draft's Study 5 into Study 4 and makes the editors/Google
    # experiment Study 3.
    "lira_etal_2025__est38": {
        "notes": "Study 3 (2026 version). AI beats 49 professional editors "
                 "(avg 25 yrs experience).",
    },
    "lira_etal_2025__est39": {
        "study_label": "Lira et al., Study 4 (example only)",
        "notes": "Study 4 (2026 version; labeled Study 5 in the 2025 draft). "
                 "Example-only as effective as practice with AI (d=0.03 "
                 "difference). Mechanism: learning by example. Effect/SE from "
                 "the test-phase writing-quality table, main GPT-4o spec "
                 "(See-AI-example vs Practice-without-AI = .36, SE .056; Table "
                 "S27 in the Sep-2025 draft = S29 in arXiv v4): the in-text "
                 "d=.37 is rounded, and the previously stored SE .057 belonged "
                 "to the adjacent contrast. Arm Ns 679/672 (balance table). "
                 "[corrected 2026-07, W. Erda round]",
    },

    # [RA-2026-07] Nie: raw percentage-point SE/CIs were sitting in SD-unit
    # columns; LATE intervals are 90% BCa (not 95%). Raw values -> notes.
    "nie_etal_2025__est41": {
        "se": None, "ci_lower": None, "ci_upper": None,
        "notes": "ITT. Only 14.2% of treatment group used GPT-4. Raw effect: "
                 "-4.4pp exam participation (SE 1.34, 95% CI [-7.10, -1.82], "
                 "Fig. 3b; pp units). Bonferroni-corrected p=0.020.",
    },
    "nie_etal_2025__est42": {
        "ci_lower": None, "ci_upper": None,
        "notes": "LATE for adopters (14.2% compliance), imputing for missingness. "
                 "ES=0.40; raw LATE +6.86pp, 90% BCa CI [0.30, 14.13] (Table 2; "
                 "pp units). Preferred estimate. Not significant after Bonferroni.",
    },

    # [RA-2026-07] Shen & Tamkin: exact back-calculated SE/CI; quiz is 14
    # questions / 27 points (Sec 4.2), not 6.
    "shen_and_tamkin_2026__est57": {
        "se": 0.287, "ci_lower": -1.300, "ci_upper": -0.176,
        "notes": "35-min coding task with AI; 14-question (27-point) quiz w/o AI. "
                 "No significant productivity gain. SE back-calculated from d "
                 "and N.",
    },

    # [RA-2026-07] Vanzo: cohort rows are subgroups of the pooled estimate
    # (est43); ACL version reports the 3rd-year effect as significant p=0.044.
    "vanzo_etal_2024__est44": {
        "is_subgroup": True, "subgroup": "Grade: Younger",
        "notes": "Significant (one-sided, p=0.044, ACL version). "
                 "Objective/grammar homework type.",
    },
    "vanzo_etal_2024__est45": {
        "is_subgroup": True, "subgroup": "Grade: Older",
    },

    # [RA-2026-07] Wang: Table 2 reports SE 0.01 (raw pp) for the main effect;
    # converted to the same binary-outcome SD units as the stored 0.08.
    # est46 is the bottom tutor-quality tercile -> subgroup.
    "wang_etal_2025__est46": {
        "is_subgroup": True, "subgroup": "Tutor quality: Bottom tercile",
    },
    "wang_etal_2025__est47": {
        "se": 0.021, "ci_lower": 0.040, "ci_upper": 0.120,
        "quality_flags": "non-standard outcome",
        "notes": "AI assists the TUTOR, not student directly. Tutor-level "
                 "randomization (782 tutors). 4,136 sessions. $20/tutor/year. "
                 "Raw effect +4pp (SE 0.01, Table 2); SE converted to the same "
                 "binary-outcome SD units as the effect.",
    },

    # [RA-2026-07] Wiles: knowledge questions are five separate regressions
    # with Ns 253-573 (Table B7); task scores are raw benchmark-normalized
    # ATEs (Table B3), not SD units -> raw values in notes.
    "wiles_etal_2024__est48": {
        "n_total": None,
        "notes": "No consistent difference on 5 post-experiment knowledge "
                 "questions without ChatGPT (two of five marginal at p<0.10, "
                 "opposite signs). No learning retained. N varies by question: "
                 "253-573 (Table B7).",
    },
    "wiles_etal_2024__est49": {
        "se": None,
        "notes": "Raw ATE +0.490 on the benchmark-normalized coding score "
                 "(SE 0.036, 95% CI [0.42, 0.56], Table B3); not SD units. Score "
                 "normalized to data-scientist benchmark. Effect during AI use.",
    },

    # [RA-2026-07] Xu: 0.997 was Table 2's adjusted-mean SE (raw points), not
    # the SE of Cohen's d; the paper reports no SE for d.
    "xu_etal_2025__est50": {
        "se": None,
        "notes": "Both groups used ChatGPT; treatment = metacognitive prompts. "
                 "F=3.939, p=0.051; paper reports no SE for Cohen's d (Table 2's "
                 "0.997 is the adjusted-mean SE in raw points). 4-week experiment.",
    },

    # [RA-2026-07] Chung: certification exam was the end-of-course terminal
    # assessment (June 2025) at the end of the ~5-month course, not a delayed
    # retention wave. (Codex audit 2026-07: keep the enum strictly
    # immediate/delayed; the course-length nuance lives in the xlsx notes.)
    "chung_etal_2025__est52": {"outcome_timing": "immediate"},
    "chung_etal_2025__est53": {"outcome_timing": "immediate"},

    # ── [RA-2026-07 r2] Round-2 adversarial re-check findings ──────────────
    # Kestin: 0.73-1.3 is a RANGE of quantile-regression estimates, not a CI.
    "kestin_etal_2025__est22": {
        "ci_lower": None, "ci_upper": None,
        "notes": "Preferred estimate: quantile-regression effect-size RANGE "
                 "0.73-1.3 SD (not a confidence interval; the paper reports no "
                 "SE/CI for it). Midpoint ~1.0 shown as the point value. Avoids "
                 "ceiling effect in the post-test.",
    },
    "vanzo_etal_2024__est43": {
        "notes": "Not significant. Pooled across 3rd and 5th year. One-sided "
                 "t-test. ACL 2025 published version.",
    },
}

# [RA-2026-07 r2] Additions to entries defined above.
# (De Simone's "third-term exam" label now flows from CURATED_MAP and
# literature_effects.csv, which were renamed from the stale "retention".)
# Lehmann Studies 2/3: the post-test is 20 CODING questions (write & submit
# code, p.13), not multiple choice; est35's raw-scale IV SE leaves the
# SD-unit column (its note already carries the raw value).
ESTIMATE_OVERRIDES["lehmann_etal_2024__est33"]["outcome"] = "Post-test score (Python programming, 20 coding questions)"
ESTIMATE_OVERRIDES["lehmann_etal_2024__est36"]["outcome"] = "Post-test score (Python programming, 20 coding questions)"
ESTIMATE_OVERRIDES["lehmann_etal_2024__est35"]["se"] = None

# Estimates removed from the site entirely (duplicates confirmed in the
# 2026-07 RA verification pass).
DROP_ESTIMATES: set[str] = {
    # Duplicate of hausman est12: same Table 2 col (1) coefficient 0.970 (0.289)
    "hausman_etal_2025__est14",
    # [RA-2026-07 W. Erda] Lira "Google vs editor feedback": both arms non-AI
    # (the GenAI arm is a separate third arm); off-topic for an AI-vs-X atlas.
    "lira_etal_2025__sg3",
}


# ── ADDITIONAL ESTIMATES (subgroup heterogeneity, alternative arms, etc.) ───
# Each entry is a full estimate dict. These get flagged is_subgroup=True so
# the React app can hide them by default behind a toggle.
def _ce(study_label, paper_key, effect, se, treatment, control, outcome,
        timing="immediate", domain="General knowledge",
        comparison="ai_vs_bau", outcome_with_ai=False, n=None,
        ci_lo=None, ci_hi=None, subgroup="", notes=None,
        nt=None, nc=None):
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
        n_treatment=nt,
        n_control=nc,
        n_total=n,
        treatment=treatment,
        control=control,
        notes=notes if notes is not None else "",
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
    # From regression_results_main.dta avg_score1..5_s2 (OLS spec), i.e. paper
    # Table 6 Panel A ITT betas (human and AI graders averaged) divided by the
    # control-group SD. Ns follow the paper's Table 6, which reports a single
    # Session Two N (197) for all dimensions.
    _ce("Contractor and Reyes (2026), Writing style & clarity (S2 essay)",
        "contractor_reyes_2026", 0.304, 0.125,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: writing style & clarity (S2)",
        timing="delayed", n=197, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Evidence & examples (S2 essay)",
        "contractor_reyes_2026", 0.232, 0.145,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: evidence & examples (S2)",
        timing="delayed", n=197, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Structure & organization (S2 essay)",
        "contractor_reyes_2026", 0.153, 0.130,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: structure & organization (S2)",
        timing="delayed", n=197, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Relevance to prompt (S2 essay)",
        "contractor_reyes_2026", 0.264, 0.128,
        "ChatGPT access during practice", "No AI access",
        "Essay quality component: relevance to prompt (S2)",
        timing="delayed", n=197, subgroup="Essay component"),
    _ce("Contractor and Reyes (2026), Factual accuracy (S2 essay)",
        "contractor_reyes_2026", 0.229, 0.139,
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
    # [RA-2026-07 W. Erda check] The stratum Ns below are BOTH-ARM completer
    # counts (31%/62% of the 85 completers; Fig 6), i.e., AI-vs-traditional
    # comparisons within each prior-experience stratum -- not treatment-only
    # subsets against the full control arm.
    _ce("Barcaui (2025), Recent/initial AI users",
        "barcaui_2025", -0.89, None,
        "ChatGPT (GPT-4)", "Traditional study (no AI)",
        "Retention test (recent/initial AI users)",
        timing="delayed", n=26, ci_lo=-1.56, ci_hi=-0.22,
        subgroup="Prior AI exposure: Recent",
        notes="Within-stratum AI-vs-traditional comparison; n=26 counts "
              "completers in BOTH arms of the recent/initial-user stratum "
              "(31% of the 85 completers). d=0.89 confirmed in the paper's "
              "Fig 7 caption (sign flipped to the atlas convention)."),
    _ce("Barcaui (2025), Frequent AI users",
        "barcaui_2025", -0.41, None,
        "ChatGPT (GPT-4)", "Traditional study (no AI)",
        "Retention test (frequent AI users)",
        timing="delayed", n=53, ci_lo=-0.90, ci_hi=0.08,
        subgroup="Prior AI exposure: Frequent",
        notes="Within-stratum AI-vs-traditional comparison; n=53 counts "
              "completers in BOTH arms of the frequent-user stratum (62% of "
              "the 85 completers)."),

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
        domain="Math", comparison="ai_design", n=None,
        subgroup="AI design comparison",
        notes="Pairwise GPT Tutor vs GPT Base contrast (Table 4, raw diff 0.028 "
              "[0.005, 0.052] / exam SD 0.277); two-arm N not reported (2,848 "
              "is the three-arm regression sample)."),

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
    # [RA-2026-07 W. Erda] Arm Ns filled from Appendix Tables A1-A3 analyzed
    # samples; knowledge/transfer tests taken within one day of the task
    # (single session), so timing is immediate, not delayed.
    _ce("Fan et al. (2024), Essay improvement, AI vs Human Expert",
        "fan_etal_2025", 0.66, 0.269,
        "ChatGPT 4.0 during revision", "Human expert support",
        "Essay score improvement (post-revision minus pre-revision)",
        domain="Writing", comparison="ai_vs_active", outcome_with_ai=True,
        n=60, nt=35, nc=25, subgroup="AI vs Human Expert"),
    # [RA-2026-07 r2] SE from the standard SE(d) formula with N=35/30 (0.2574);
    # the old 0.252 was a ~2% low outlier vs the sibling rows.
    _ce("Fan et al. (2024), Essay improvement, AI vs Checklist tool",
        "fan_etal_2025", 0.75, 0.257,
        "ChatGPT 4.0 during revision", "Checklist writing analytics tool",
        "Essay score improvement (post-revision minus pre-revision)",
        domain="Writing", comparison="ai_vs_active", outcome_with_ai=True,
        n=65, nt=35, nc=30, subgroup="AI vs Checklist"),
    _ce("Fan et al. (2024), Knowledge gain, AI vs Human Expert",
        "fan_etal_2025", 0.45, 0.275,
        "ChatGPT 4.0 during revision", "Human expert support",
        "Knowledge gain (pre-post test on AI in education)",
        domain="Writing", comparison="ai_vs_active",
        n=56, nt=33, nc=23, subgroup="AI vs Human Expert"),
    _ce("Fan et al. (2024), Knowledge gain, AI vs Checklist",
        "fan_etal_2025", 0.22, 0.269,
        "ChatGPT 4.0 during revision", "Checklist writing analytics tool",
        "Knowledge gain (pre-post test on AI in education)",
        domain="Writing", comparison="ai_vs_active",
        n=57, nt=33, nc=24, subgroup="AI vs Checklist"),
    _ce("Fan et al. (2024), Knowledge transfer, AI vs CN",
        "fan_etal_2025", -0.02, 0.260,
        "ChatGPT 4.0 during revision", "No additional support",
        "Knowledge transfer (AI in healthcare, 10-item MCQ)",
        domain="Writing", n=60, nt=34, nc=26,
        subgroup="Transfer outcome",
        notes="Post-test within one day of the task (same wave as knowledge "
              "gain; coded immediate). Transfer domain: AI in healthcare. "
              "The paper's Table A3 caption is generic ('posttest score'); "
              "body text p.16 identifies it as the transfer test."),

    # ── Hausman — heterogeneity by demographics/course type/percentile ──
    # [RA-2026-07] Effects are raw grade points (0-100 scale), NOT SD units;
    # per site policy the SD columns stay empty and raw values live in notes
    # (matching the paper's five main estimates, which are handled the same way).
    _ce("Hausman et al. (2025), Male students (Year 2)",
        "hausman_etal_2025", None, None,
        "AI-compatible courses post-ChatGPT (male)",
        "AI-incompatible courses (DiD)",
        "Course grade (0-100), male students",
        domain="Mixed", n=200672, subgroup="Gender: Male",
        notes="Raw DiD effect: +1.374 grade points (0-100 scale), SE 0.470 "
              "(Table 3). Not in SD units."),
    _ce("Hausman et al. (2025), Young students (<26, Year 2)",
        "hausman_etal_2025", None, None,
        "AI-compatible courses post-ChatGPT (age<26)",
        "AI-incompatible courses (DiD)",
        "Course grade (0-100), young students",
        domain="Mixed", n=238466, subgroup="Age: <26",
        notes="Raw DiD effect: +2.079 grade points (0-100 scale), SE 0.537 "
              "(Table 3). Not in SD units."),
    _ce("Hausman et al. (2025), Advanced courses (Year 2)",
        "hausman_etal_2025", None, None,
        "AI-compatible advanced courses post-ChatGPT",
        "AI-incompatible advanced courses (DiD)",
        "Course grade (0-100), advanced courses",
        domain="Mixed", n=254662, subgroup="Course level: Advanced",
        notes="Raw DiD effect: +1.466 grade points (0-100 scale), SE 0.511 "
              "(Table 3). Not in SD units."),
    _ce("Hausman et al. (2025), STEM courses (Year 2)",
        "hausman_etal_2025", None, None,
        "AI-compatible STEM post-ChatGPT", "AI-incompatible STEM (DiD)",
        "Course grade (0-100), STEM courses",
        domain="Math", n=119260, subgroup="Domain: STEM",
        notes="Raw DiD effect: +1.269 grade points (0-100 scale), SE 0.969, "
              "not significant (Table 3). Not in SD units."),
    _ce("Hausman et al. (2025), Large classes (>25, Year 2)",
        "hausman_etal_2025", None, None,
        "AI-compatible large courses post-ChatGPT",
        "AI-incompatible large courses (DiD)",
        "Course grade (0-100), classes >25 students",
        domain="Mixed", n=435675, subgroup="Class size: Large",
        notes="Raw DiD effect: +1.671 grade points (0-100 scale), SE 0.453 "
              "(Table 3). Not in SD units."),
    _ce("Hausman et al. (2025), Median grade (Year 1)",
        "hausman_etal_2025", None, None,
        "AI-compatible courses post-ChatGPT",
        "AI-incompatible courses (DiD)",
        "50th percentile grade (Year 1)",
        domain="Mixed", n=10076, subgroup="Percentile: 50th",
        notes="Raw DiD effect: +1.272 grade points at the median (0-100 scale), "
              "SE 0.612 (Table 4). Not in SD units."),
    _ce("Hausman et al. (2025), AI-incompatible advanced (cohort experience)",
        "hausman_etal_2025", None, None,
        "2022-23 cohort (post-ChatGPT exposure)",
        "2021-22 cohort (pre-ChatGPT, baseline)",
        "Grade in AI-incompatible advanced courses (Year 2)",
        domain="Mixed", timing="delayed", outcome_with_ai=False,
        n=34829, subgroup="AI human-capital spillover",
        notes="Raw DiD effect: -0.507 grade points (0-100 scale), SE 0.353, "
              "not significant (Table 5 col. 6). Not in SD units."),

    # ── Kreijkes — Group 2 (LLM vs LLM+Notes) + free recall outcomes ─────
    # [RA-2026-07 r2] SE via the same delta-method conversion as est25/est26
    # (0.43 x 0.21/1.02 = 0.089); the old 0.10 was a coarser rounding.
    _ce("Kreijkes et al. (2026), Free recall (LLM vs Notes)",
        "kreijkes_etal_2026", -0.21, 0.089,
        "LLM chatbot only", "Note-taking only",
        "Free recall (open response)",
        domain="Language", timing="delayed", comparison="ai_vs_active",
        n=184, subgroup="Outcome: Free recall",
        notes="Within-subject (Group 1). SE converted to SD units by the delta "
              "method from raw B=1.02 (SE 0.43), Table 3."),
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
    # [RA-2026-07 W. Erda] "Study 3, Google vs editor feedback" is DROPPED at
    # build time (see DROP_ESTIMATES): both arms are non-AI (Google Search vs
    # human editors; the generative-AI arm is a separate third arm), so the
    # contrast does not belong in an AI-vs-comparison atlas. The entry stays
    # here so the positional __sgN ids of later Lira rows do not renumber.
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
    # [RA-2026-07] The Cohen's d values the paper reports for hint-users and
    # non-users are contrasts AGAINST DIRECT-ANSWER USERS (t(269)/t(224), p.7),
    # not against the no-AI control; relabeled accordingly (ai_design,
    # within-AI-arm descriptive contrasts).
    _ce("Liu et al. (2026), Direct answers vs hint-seekers (Exp 2)",
        "liu_etal_2026", -0.29, 0.133,
        "AI users obtaining direct solutions", "AI users requesting only hints",
        "Test solve rate, 3 fraction problems (Exp 2 heterogeneity)",
        domain="Math", comparison="ai_design", n=271,
        subgroup="AI use: Direct vs hints",
        notes="Descriptive within-AI-arm contrast (t(269)); the paper flags "
              "these splits as non-causal. Hint-users vs control is ~null "
              "(0.76 vs 0.77)."),
    _ce("Liu et al. (2026), Direct answers vs non-users (Exp 2)",
        "liu_etal_2026", -0.66, 0.184,
        "AI users obtaining direct solutions",
        "AI-arm participants who did not use AI",
        "Test solve rate, 3 fraction problems (Exp 2 heterogeneity)",
        domain="Math", comparison="ai_design", n=226,
        subgroup="AI use: Direct vs non-users",
        notes="Descriptive within-AI-arm contrast (t(224)); non-causal. "
              "Non-users outperformed the no-AI control (0.89 vs 0.77)."),
    _ce("Liu et al. (2026), Exp 1 skip rate",
        "liu_etal_2026", 0.25, 0.117,
        "GPT-5 sidebar access", "No AI access",
        "Skip rate, 3 fraction test problems (Exp 1)",
        domain="Math", n=307, ci_lo=0.02, ci_hi=0.48,
        subgroup="Outcome: Skip rate"),
    _ce("Liu et al. (2026), Exp 3 skip rate",
        "liu_etal_2026", 0.42, 0.156,
        "GPT-5 sidebar access", "No-AI control with test-tips",
        "Skip rate, 3 SAT reading test problems (Exp 3)",
        domain="Language", comparison="ai_vs_active",
        n=168, ci_lo=0.11, ci_hi=0.72, subgroup="Outcome: Skip rate"),

    # ── Chung — subgroup heterogeneity by Python skill and school tier ──
    # [RA-2026-07] Split is self-reported prior Python skill (53% beginners /
    # 39% experienced, p.13), not a prior-achievement median split. Subgroup Ns
    # from Table 7: beginners 411, experienced 299; per-tier Ns are not
    # reported (combined N=716, Table 15). Exam = end-of-course terminal
    # assessment -> immediate.
    _ce("Chung et al. (2026), Python beginners",
        "chung_etal_2025", 0.215, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (beginners only)",
        domain="Coding", timing="immediate", comparison="ai_design",
        n=411, ci_lo=0.048, ci_hi=0.382,
        subgroup="Prior Python skill: Beginner",
        notes="Self-identified first-time learners/beginners (53% of sample, "
              "N=411). 0.215 SD, p=0.012 reported in sec 4.2; the paper "
              "prints no numeric SE/CI for this subgroup (Fig. 3 shows CIs "
              "visually), so the CI here is reconstructed by p-value "
              "inversion. [2026-07 W. Erda verification]"),
    _ce("Chung et al. (2026), Python experienced",
        "chung_etal_2025", 0.008, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (experienced)",
        domain="Coding", timing="immediate", comparison="ai_design",
        n=299, ci_lo=-0.21, ci_hi=0.226,
        subgroup="Prior Python skill: Experienced",
        notes="Self-identified intermediate/proficient coders (39% of sample, "
              "N=299). 0.008 SD, p=0.941 reported in sec 4.2; the paper "
              "prints no numeric SE/CI for this subgroup (Fig. 3 shows CIs "
              "visually), so the CI here is reconstructed by p-value "
              "inversion. [2026-07 W. Erda verification]"),
    _ce("Chung et al. (2026), Lower-tier schools",
        "chung_etal_2025", 0.173, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (lower-tier schools)",
        domain="Coding", timing="immediate", comparison="ai_design",
        n=716, ci_lo=0.004, ci_hi=0.342, subgroup="School tier: Lower",
        notes="N=716 is the combined school-tier interaction sample (Table 15); "
              "per-tier N is not reported. 0.173 SD, p=0.045."),
    _ce("Chung et al. (2026), Higher-tier schools",
        "chung_etal_2025", 0.039, None,
        "RL adaptive sequencing + GenAI tutor", "Fixed sequence + GenAI tutor",
        "Standardized Python exam (higher-tier schools)",
        domain="Coding", timing="immediate", comparison="ai_design",
        n=716, ci_lo=-0.205, ci_hi=0.283, subgroup="School tier: Higher",
        notes="N=716 is the combined school-tier interaction sample (Table 15); "
              "per-tier N is not reported. 0.039 SD, p=0.752."),

    # ── Wiles — task-specific effects ────────────────────────────────────
    # [RA-2026-07] Table B3 coefficients are raw benchmark-normalized ATEs,
    # not SD units; SD columns stay empty, raw values in notes.
    _ce("Wiles et al. (2026), Statistics task with AI",
        "wiles_etal_2024", None, None,
        "ChatGPT access + training", "Google/Stack Overflow training",
        "Statistics task score (with AI access)",
        domain="Coding", comparison="ai_vs_active",
        outcome_with_ai=True, n=330, subgroup="Task: Statistics",
        notes="Raw ATE +0.201 on the benchmark-normalized statistics score "
              "(SE 0.026, 95% CI [0.15, 0.25], Table B3); not SD units."),
    _ce("Wiles et al. (2026), Prediction task with AI",
        "wiles_etal_2024", None, None,
        "ChatGPT access + training", "Google/Stack Overflow training",
        "Prediction task score (with AI access)",
        domain="Coding", comparison="ai_vs_active",
        outcome_with_ai=True, n=298, subgroup="Task: Prediction",
        notes="Raw ATE +0.172 on the benchmark-normalized prediction score "
              "(SE 0.042, 95% CI [0.09, 0.25], Table B3); not SD units."),

    # ── Nie — alternative ITT/LATE specs ─────────────────────────────────
    # [RA-2026-07] LATE intervals are 90% BCa on the raw pp effect (not 95%
    # SD-unit CIs); homework effect is raw pp. Raw values in notes.
    _ce("Nie et al. (2025), Exam score LATE (ignore missingness)",
        "nie_etal_2025", 0.23, None,
        "GPT-4 access (adopters, LATE)", "No GPT-4 access",
        "Exam score LATE (ignore missingness)",
        domain="Coding", n=5831,
        subgroup="Spec: LATE ignore missingness",
        notes="ES=0.23; raw LATE +4.49pp, 90% BCa CI [-0.31, 9.66] (Table 2; "
              "fn. 4 reports [-0.34, 8.98]; pp units). Paper reports no SE."),
    _ce("Nie et al. (2025), Week 6 homework completion (ITT)",
        "nie_etal_2025", None, None,
        "GPT-4 access", "No GPT-4 access",
        "Week 6 homework completion rate (pp)",
        domain="Coding", n=5831,
        subgroup="Outcome: Homework completion",
        notes="Raw effect: -4.6pp Week-6 homework completion (SE 1.3, 95% CI "
              "[-7.2, -1.9], p=.01; Fig. 3b reports SE 1.34, CI [-7.20, -1.94]). "
              "pp units, no SD conversion available."),

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
        domain="Coding", subgroup="Prior achievement: Above median",
        notes="Above-median level effect = (main + interaction)/4.6 from Table "
              "12; the SE shown is the interaction-term SE as a proxy (the "
              "exact level-effect SE needs the unreported covariance)."),
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
        domain="Coding", subgroup="Prior achievement: Above median",
        notes="Above-median level effect = (main + interaction)/4.6 from Table "
              "12; the SE shown is the interaction-term SE as a proxy (the "
              "exact level-effect SE needs the unreported covariance)."),

    # ── Vanzo — grade/year split ──────────────────────────────────────────
    # [RA-2026-07] Removed: these duplicated est44/est45 (the 3rd/5th-year
    # rows from meta_analysis.xlsx), which are now flagged is_subgroup=True
    # via ESTIMATE_OVERRIDES instead.
]


# ── Outcome-with-AI classification per estimate ─────────────────────────────
# True if the outcome was measured WITH AI access (i.e., performance, not
# transferable learning). Default for any not listed is False (unassisted).
# These reflect the AI vs No-AI distinction the user wants to filter.
OUTCOME_WITH_AI = {
    # Stromberg: homework completed with AI in hand (productivity outcome)
    "stromberg_etal_2026__est83": True,
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
    # Kalam Week-1 quiz: taken with assigned resources in hand; the ChatGPT arm
    # could query ChatGPT during the proctored quiz (p.3). Week-2 retention
    # (est17) was closed-book → False.
    "kalam_etal_2025__est16": True,    "bassner_etal_2026__est63": True,
    # Iris-arm exercise performance, added 2026-07 (W. Erda verification)
    "bassner_etal_2026__est84": True,

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
    "De Simone et al., third-term exam": "Language",
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
    "Shen & Tamkin": "Coding",    'Ba et al., pediatrics': 'Medicine',
    'Bassner et al., Iris tutor': 'Coding',
    'Bassner et al., ChatGPT': 'Coding',
    'Dai et al., Exp 1': 'Science',
    'Dai et al., Exp 2 student choice': 'Science',
    'Dai et al., Exp 2 system choice': 'Science',
    'Fischer et al., unrestricted AI': 'Economics',
    'Fischer et al., restricted AI': 'Economics',
    'Gan et al., orthopedics': 'Medicine',
    'Hou et al., guided AI': 'Engineering',
    'Hou et al., unguided AI': 'Engineering',
    'Huang et al., dental skills': 'Medicine',
    'Kavadella et al., dentistry': 'Medicine',
    'LearnLM, Sierra Leone': 'Math',
    'Franco et al., AI-assisted': 'Language',
    'Franco et al., AI-guided': 'Language',

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
    ("Franco et al. (2026)", "AI-assisted", "", "Franco et al., AI-assisted"),
    ("Franco et al. (2026)", "AI-guided", "", "Franco et al., AI-guided"),
    ("Bastani et al. (2025)", "GPT Base", "unassisted exam", "Bastani et al., GPT Base"),
    ("Bastani et al. (2025)", "GPT Tutor", "unassisted exam", "Bastani et al., GPT Tutor"),
    ("De Simone et al. (2025)", "", "English skills", "De Simone et al., English"),
    ("De Simone et al. (2025)", "", "Third-term", "De Simone et al., third-term exam"),
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
    ('Ba et al. (2024)', 'ChatGPT-assisted instruction', 'closed-book theoretical knowledge exam', 'Ba et al., pediatrics'),
    ('Bassner et al. (2026)', 'Iris', 'Knowledge gain', 'Bassner et al., Iris tutor'),
    ('Bassner et al. (2026)', 'ChatGPT', 'Knowledge gain', 'Bassner et al., ChatGPT'),
    ('Dai et al. (2025)', 'Exp 1', 'physics exam', 'Dai et al., Exp 1'),
    ('Dai et al. (2025)', 'student', 'physics exam', 'Dai et al., Exp 2 student choice'),
    ('Dai et al. (2025)', 'system', 'physics exam', 'Dai et al., Exp 2 system choice'),
    ('Fischer et al. (2025)', 'Unrestricted AI tutor access', '25-item multiple-choice exam', 'Fischer et al., unrestricted AI'),
    ('Fischer et al. (2025)', 'Restricted AI tutor access', '25-item multiple-choice exam', 'Fischer et al., restricted AI'),
    ('Gan et al. (2024)', 'ChatGPT-4 self-study', '214-item orthopedics examination', 'Gan et al., orthopedics'),
    ('Hou et al. (2026)', 'guided', 'post-test', 'Hou et al., guided AI'),
    ('Hou et al. (2026)', 'Unprompted', 'post-test', 'Hou et al., unguided AI'),
    ('Huang et al. (2025)', 'ChatGPT-3.5', 'operative skill', 'Huang et al., dental skills'),
    ('Kavadella et al. (2024)', 'research and compose', 'knowledge exam', 'Kavadella et al., dentistry'),
    ('LearnLM Team (2026)', 'Gemini "Guided Learning"', 'intent-to-treat', 'LearnLM, Sierra Leone'),
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
    """Load the 4 'This paper' estimates from regression_results_main.dta.

    Test scores match paper Table 4 (ITT columns). Essay quality uses
    avg_score6 (overall quality, human and AI graders averaged, student
    level), matching paper Table 6 Panel B "Overall quality (average)",
    standardized by the control-group SD.
    """
    try:
        df = pd.read_stata(REG_DTA)
    except Exception as exc:  # pragma: no cover
        print(f"WARN: could not read {REG_DTA}: {exc}")
        return []

    keep = [
        ("test_score1", "s1_student"),
        ("test_score2", "s2_student"),
        ("avg_score6_s1", "s1_student"),
        ("avg_score6_s2", "s2_student"),
    ]
    df = df[df["spec"] == "ols"].copy()
    df = df[df.apply(lambda r: (r["outcome"], r["sample"]) in keep, axis=1)].copy()
    df["effect"] = df["beta"] / df["sd_ctrl"]
    df["se_std"] = df["se"] / df["sd_ctrl"]

    label_map = {
        ("test_score1", "s1_student"): "Contractor and Reyes (2026), Session one test",
        ("test_score2", "s2_student"): "Contractor and Reyes (2026), Session two test",
        ("avg_score6_s1", "s1_student"): "Contractor and Reyes (2026), Session one essay",
        ("avg_score6_s2", "s2_student"): "Contractor and Reyes (2026), Session two essay",
    }

    # Human-readable outcome names (replaces raw Stata variable names)
    outcome_pretty = {
        ("test_score1", "s1_student"): "Test score, Session 1 (immediate, no AI)",
        ("test_score2", "s2_student"): "Test score, Session 2 (1 week later, no AI)",
        ("avg_score6_s1", "s1_student"): "Essay quality, Session 1 (written with AI access)",
        ("avg_score6_s2", "s2_student"): "Essay quality, Session 2 (1 week later, no AI)",
    }
    timing_for = {
        ("test_score1", "s1_student"): "immediate",
        ("test_score2", "s2_student"): "delayed",
        ("avg_score6_s1", "s1_student"): "immediate",
        ("avg_score6_s2", "s2_student"): "delayed",
    }
    # Arm splits for the test-score samples, paper Table 4 (ITT columns).
    # [RA-2026-07 verification: W. Erda]
    arm_ns = {
        ("test_score1", "s1_student"): (107, 104),
        ("test_score2", "s2_student"): (102, 102),
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
                n_treatment=arm_ns.get((r["outcome"], r["sample"]), (None, None))[0],
                n_control=arm_ns.get((r["outcome"], r["sample"]), (None, None))[1],
                n_total=int(r["N"]),
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
        if paper_name in DROP_PAPERS:
            continue
        sub = meta[meta["paper"] == paper_name].copy()
        key = slugify(paper_name)
        first = sub.iloc[0]
        manual = PAPER_META.get(paper_name, {})
        corrections = PAPER_CORRECTIONS.get(key, {})

        # whether any estimate in this paper maps to a row of the curated csv
        in_curated = False
        for _, r in sub.iterrows():
            lbl = match_curated(paper_name, str(r["treatment"]), str(r["outcome"]))
            if lbl and lbl in curated_studies:
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
            if estimate_id in DROP_ESTIMATES:
                continue
            # Apply per-estimate overrides from verification passes
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
            # Apply remaining overrides post-construction (any estimate field:
            # n_total, n_treatment, n_control, ci_lower, ci_upper,
            # outcome_timing, subgroup, study_label, outcome, notes, ...)
            estimates_rows[-1].update(
                {k: v for k, v in ov.items() if k not in ("se", "effect_size_sd")}
            )

    # ── Append ADDITIONAL_ESTIMATES (subgroup / heterogeneity rows) ───────
    # Each gets a synthetic estimate_id keyed to paper_key.
    sg_counter = {}
    for est in ADDITIONAL_ESTIMATES:
        pkey = est["paper_key"]
        sg_counter[pkey] = sg_counter.get(pkey, 0) + 1
        est_id = f"{pkey}__sg{sg_counter[pkey]}"
        # Positional ids: dropped entries still advance the counter above so
        # later __sgN ids never renumber.
        if est_id in DROP_ESTIMATES:
            continue
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

    # ── recompute n_estimates over the FINAL estimate set ─────────────────
    # (own + xlsx + synthetic subgroup rows, after drops; the values set at
    # construction counted only xlsx rows — Codex audit 2026-07)
    final_counts: dict[str, int] = {}
    for e in estimates_rows:
        final_counts[e["paper_key"]] = final_counts.get(e["paper_key"], 0) + 1
    for row in papers_rows:
        row["n_estimates"] = final_counts.get(row["paper_key"], 0)

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

    # ── attach design_class (paper default + per-estimate overrides) ──────
    estimates_df["design_class"] = estimates_df.apply(
        lambda r: DESIGN_CLASS_OVERRIDES.get(
            r["estimate_id"], DESIGN_CLASS.get(r["paper_key"], DESIGN_CLASS_DEFAULT)
        ),
        axis=1,
    )
    papers_df["design_class"] = papers_df["paper_key"].map(
        lambda k: DESIGN_CLASS.get(k, DESIGN_CLASS_DEFAULT)
    )

    # ── public schema: factual coding notes only ──────────────────────────
    # The internal High/Medium/Low quality_label stays in meta_analysis.xlsx
    # and is not published; quality_flags ships as coding_notes (how derived
    # quantities were computed, plus design facts), with "none" blanked.
    def _notes(v):
        s = "" if v is None else str(v).strip()
        return "" if s.lower() in ("", "none", "nan") else s

    papers_df = papers_df.drop(columns=["quality_label"]).rename(columns={"quality_flags": "coding_notes"})
    estimates_df = estimates_df.drop(columns=["quality_label"]).rename(columns={"quality_flags": "coding_notes"})
    papers_df["coding_notes"] = papers_df["coding_notes"].map(_notes)
    estimates_df["coding_notes"] = estimates_df["coding_notes"].map(_notes)

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
