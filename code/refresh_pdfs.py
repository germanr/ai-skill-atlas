"""Download refreshed PDFs for the 10 papers that had newer versions.

Each entry: paper_key -> (PDF URL, destination filename in public/pdfs/).
"""
import subprocess
from pathlib import Path

PDF_DIR = Path(r"C:/Users/greyes/Dropbox/Admin/website/ai-skill-atlas/public/pdfs")

REFRESH = {
    "bastani_etal_2025":     ("https://www.pnas.org/doi/pdf/10.1073/pnas.2422633122",
                              "Bastani et al (2025) - PNAS - Generative AI Without Guardrails Can Harm Learning.pdf"),
    "fan_etal_2024":         ("https://arxiv.org/pdf/2412.09315",
                              "Fan et al (2024) - BJET - Metacognitive Laziness.pdf"),
    "hausman_etal_2025":     ("https://www.econstor.eu/bitstream/10419/319211/1/cesifo1_wp11843.pdf",
                              "Hausman et al (2025) - CESifo - GenAI Impact on Student Achievement.pdf"),
    "kalam_etal_2025":       ("https://www.cureus.com/articles/364193-chatgpt-as-a-learning-tool-for-medical-students-results-from-a-randomized-controlled-trial.pdf",
                              "Kalam et al (2025) - Cureus - ChatGPT as Learning Tool Medical Students.pdf"),
    "kumar_etal_2025":       ("http://jakehofman.com/pdfs/llms-for-math-education.pdf",
                              "Kumar et al (2025) - AIED - Math Education with Large Language Models.pdf"),
    "lira_etal_2026":        ("https://arxiv.org/pdf/2502.02880v4",
                              "Lira et al (2026) - Coach Not Crutch.pdf"),
    "nie_etal_2025":         ("https://arxiv.org/pdf/2407.09975",
                              "Nie et al (2025) - ACM LaS - GPT Surprise Coding Class.pdf"),
    "vanzo_etal_2025":       ("https://aclanthology.org/2025.acl-long.1502.pdf",
                              "Vanzo et al (2025) - ACL - GPT-4 as Homework Tutor.pdf"),
    # wiles_etal_2024 and chung_etal_2025 are paywalled - skipped
}


def download(url, dest_name):
    dest = PDF_DIR / dest_name
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "30", "-o", str(dest), url],
            capture_output=True, timeout=40,
        )
        size = dest.stat().st_size if dest.exists() else 0
        if size > 30000:
            return True, size
        if dest.exists():
            dest.unlink()
        return False, f"too small ({size} bytes)"
    except subprocess.TimeoutExpired:
        return False, "timeout"


def main():
    for key, (url, name) in REFRESH.items():
        ok, info = download(url, name)
        print(f"  {'ok    ' if ok else 'FAIL  '} {key}: {info if not ok else f'{info} bytes -> {name}'}")


if __name__ == "__main__":
    main()
