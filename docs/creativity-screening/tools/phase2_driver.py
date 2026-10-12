"""Start the supplement pass and the posted-data analysis for each extraction paper as soon as it is ready.

Every five minutes: ask stage_ready.py which papers are ready for the supplement pass or the analysis, and start one
subprocess per stage for the papers not already in progress (codex_supplement.py and codex_analyze.py; each skips work
already on disk). Stops when every extraction paper has a finished chain and no stage is pending or running, or after
--hours. Log: codex-jobs/driver.log.

Usage: python tools/phase2_driver.py [--hours 10] [--workers 4]
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

S = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
LOG = S / "codex-jobs" / "driver.log"


def log(msg):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now().strftime('%H:%M:%S')} {msg}\n")


def ready(stage):
    out = subprocess.run([sys.executable, str(S / "tools" / "stage_ready.py"), stage], capture_output=True, text=True, encoding="utf-8")
    return [c for c in out.stdout.split() if c.startswith("c")]


def recently_active():
    """Papers with an analysis or supplement job whose log changed in the last 15 minutes (started by anyone)."""
    cutoff = time.time() - 15 * 60
    active = set()
    for job in (S / "codex-jobs").iterdir():
        name = job.name
        if not job.is_dir() or not any(name.startswith(p) for p in ("analyzeA-", "analyzeB-", "supplement-", "supverify-", "supfix-", "supreverify-")):
            continue
        log_file = job / "run.log"
        if log_file.exists() and log_file.stat().st_mtime > cutoff:
            active.add(name.split("-")[1])
    return active


def finished_chains():
    return len(list((S / "extraction" / "status").glob("c*.json")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=10)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    stop_at = time.time() + a.hours * 3600
    running = {}  # Popen -> (stage, set of cids)
    log("driver started")
    while time.time() < stop_at:
        for p in [p for p in running if p.poll() is not None]:
            stage, cids = running.pop(p)
            log(f"done   {stage}: {' '.join(sorted(cids))} (exit {p.returncode})")
        busy = {c for _, cids in running.values() for c in cids} | recently_active()
        for stage, script in (("supplement", "codex_supplement.py"), ("analysis", "codex_analyze.py")):
            todo = [c for c in ready(stage) if c not in busy]
            if todo:
                out = open(S / "codex-jobs" / f"driver-{stage}-{datetime.now().strftime('%H%M%S')}.log", "w", encoding="utf-8")
                p = subprocess.Popen([sys.executable, str(S / "tools" / script), "--workers", str(a.workers), "--only", *todo],
                                     cwd=str(S), stdout=out, stderr=subprocess.STDOUT)
                running[p] = (stage, set(todo))
                busy |= set(todo)
                log(f"start  {stage}: {' '.join(todo)}")
        n = finished_chains()
        if n >= 84 and not running and not recently_active() and not ready("supplement") and not ready("analysis"):
            log(f"all {n} chains finished and no stage pending; driver stops")
            break
        time.sleep(300)
    for p in running:
        p.wait()
    log("driver ended")


if __name__ == "__main__":
    main()
