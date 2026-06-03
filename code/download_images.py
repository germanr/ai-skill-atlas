"""Download one Unsplash image per paper to public/images/.

Uses curl + concurrent.futures for fast, robust parallel downloads.

Run:
  python download_images.py
"""
from __future__ import annotations
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SITE = Path(r"C:/Users/greyes/Dropbox/Admin/website/ai-skill-atlas")
IMG_DIR = SITE / "public" / "images"
PAPERS_JSON = SITE / "src" / "papers.json"
CREDITS = IMG_DIR / "CREDITS.md"

UNSPLASH_BASE = "https://images.unsplash.com/photo-{id}?w=800&h=500&fit=crop&q=80&auto=format"

# paper_key -> (unsplash_photo_id, photographer, photo_url)
# Verified 200 OK on Unsplash CDN; bad IDs replaced.
PHOTO_MAP = {
    "contractor_reyes_2026":  ("1523240795612-9a054b0db644", "Vasily Koloda",        "https://unsplash.com/photos/8CqDvPuo_kI"),
    "bastani_etal_2025":      ("1571260899304-425eee4c7efc", "Mufid Majnun",         "https://unsplash.com/photos/dz5dQ2DjJBM"),
    "de_simone_etal_2025":    ("1497633762265-9d179a990aa6", "Annie Spratt",         "https://unsplash.com/photos/QckxruozjRg"),
    "fan_etal_2025":          ("1456513080510-7bf3a84b82f8", "J. Kelly Brito",       "https://unsplash.com/photos/PeUJyoylfe4"),
    "hausman_etal_2025":      ("1576267423048-15c0040fec78", "Tim Mossholder",       "https://unsplash.com/photos/_15Ofvkebvg"),
    "henkel_etal_2024":       ("1497486751825-1233686d5d80", "Sigmund",              "https://unsplash.com/photos/HsTnjCVQ798"),
    "kalam_etal_2025":        ("1551601651-2a8555f1a136",    "National Cancer Institute", "https://unsplash.com/photos/W7aXY5F2pBo"),
    "kazemitabaar_etal_2023": ("1532619675605-1ede6c2ed2b0", "James Wheeler",        "https://unsplash.com/photos/RRZM3cwS1DU"),
    "kestin_etal_2025":       ("1635070041078-e363dbe005cb", "Thomas T",             "https://unsplash.com/photos/_zZWO_T2X0c"),
    "kim_etal_2025":          ("1503676260728-1c00da094a0b", "Annie Spratt",         "https://unsplash.com/photos/QckxruozjRg"),
    "kreijkes_etal_2026":     ("1488998427799-e3362cec87c3", "Susan Q Yin",          "https://unsplash.com/photos/2JIvboGLeho"),
    "kumar_etal_2023":        ("1554415707-6e8cfc93fe23",    "Andrew Neel",          "https://unsplash.com/photos/cckf4TsHAuw"),
    "learnlm_team_2025":      ("1606761568499-6d2451b23c66", "Compare Fibre",        "https://unsplash.com/photos/4_jhDO54BYg"),
    "lehmann_etal_2024":      ("1517694712202-14dd9538aa97", "Christopher Gower",    "https://unsplash.com/photos/m_HRfLhgABo"),
    "lira_etal_2025":         ("1455390582262-044cdead277a", "Aaron Burden",         "https://unsplash.com/photos/y02jEX_B0O0"),
    "nie_etal_2025":          ("1610563166150-b34df4f3bcd6", "Sigmund",              "https://unsplash.com/photos/uXAW9SLgQfk"),
    "vanzo_etal_2024":        ("1457369804613-52c61a468e7d", "Patrick Tomasso",      "https://unsplash.com/photos/Oaqk7qqNh_c"),
    "wang_etal_2025":         ("1580582932707-520aed937b7b", "Note Thanun",          "https://unsplash.com/photos/PaC8ohsK_yE"),
    "wiles_etal_2024":        ("1454165804606-c3d57bc86b40", "Helloquence",          "https://unsplash.com/photos/5fNmWej4tAA"),
    "xu_etal_2025":           ("1492538368677-f6e0afe31dcc", "Mimi Thian",           "https://unsplash.com/photos/vdXMSiX-n6M"),
    "chung_etal_2025":        ("1546410531-bb4caa6b424d",    "Compare Fibre",        "https://unsplash.com/photos/IiZjcdNHCwk"),
    "liu_etal_2026":          ("1606326608606-aa0b62935f2b", "Wes Hicks",            "https://unsplash.com/photos/Y_TKbVHzZdg"),
    "shen_and_tamkin_2026":   ("1542831371-29b0f74f9713",    "Markus Spiske",        "https://unsplash.com/photos/iar-afB0QQw"),
    "barcaui_2025":           ("1497633762265-9d179a990aa6", "Annie Spratt",         "https://unsplash.com/photos/QckxruozjRg"),
}


def download_one(args):
    key, photo_id, dest = args
    if dest.exists():
        return key, "skip"
    url = UNSPLASH_BASE.format(id=photo_id)
    try:
        res = subprocess.run(
            ["curl", "-sL", "--max-time", "10", "-o", str(dest), url],
            capture_output=True, timeout=15,
        )
        if dest.exists() and dest.stat().st_size > 5000:
            return key, "ok"
        if dest.exists():
            dest.unlink()
        return key, f"too_small (exit={res.returncode})"
    except subprocess.TimeoutExpired:
        if dest.exists():
            dest.unlink()
        return key, "timeout"


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    papers = json.load(open(PAPERS_JSON, encoding="utf-8"))

    tasks = []
    for p in papers:
        key = p["paper_key"]
        photo = PHOTO_MAP.get(key)
        if not photo:
            print(f"  no mapping for {key}")
            continue
        tasks.append((key, photo[0], IMG_DIR / f"paper-{key}.jpg"))

    with ThreadPoolExecutor(max_workers=8) as ex:
        for fut in as_completed([ex.submit(download_one, t) for t in tasks]):
            key, status = fut.result()
            print(f"  {status:8s} {key}")

    # write credits
    lines = [
        "# Image Credits", "",
        "All images are from [Unsplash](https://unsplash.com) under the [Unsplash License](https://unsplash.com/license), which permits free commercial and non-commercial use without attribution. Credits below are provided as a courtesy.", "",
    ]
    for key, (_pid, photographer, url) in PHOTO_MAP.items():
        lines.append(f"- `paper-{key}.jpg` — photo by [{photographer}]({url})")
    CREDITS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote credits to {CREDITS}")


if __name__ == "__main__":
    main()
