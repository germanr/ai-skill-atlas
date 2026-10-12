"""Run a screening tool with its inputs read in parallel first.

Usage: python run_prefetched.py <script.py> [args...]

Today every file open inside Dropbox costs about 2 seconds (the Dropbox filter), but opens overlap. This wrapper reads
the screening folder's JSON, Markdown, HTML, and job-log files with a thread pool, then serves read-only opens of those
paths from memory. Writes go to disk as usual and drop the path from the cache. The tool runs unchanged (runpy)."""
import builtins
import io
import os
import runpy
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = "C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening"
SKIP_DIRS = {"audit", "jobs", "_superseded", "raw"}
EXTS = (".json", ".jsonl", ".md", ".html")
key = lambda p: os.path.normcase(os.path.realpath(os.fspath(p)))

t0 = time.time()
paths = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    rel = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
    # codex-jobs: only the top-level job logs, not the per-job folders
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not (rel == "codex-jobs")]
    paths += [os.path.join(dirpath, f) for f in filenames if f.endswith(EXTS)]
cache = {}


def read(p):
    with open(p, "rb") as fh:
        cache[key(p)] = fh.read()


with ThreadPoolExecutor(96) as pool:
    list(pool.map(read, paths))
print(f"[prefetch] {len(cache)} files in {time.time() - t0:.0f} s", file=sys.stderr, flush=True)

_open = io.open


def cached_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if isinstance(file, int):
        return _open(file, mode, buffering, encoding, errors, newline, closefd, opener)
    k = key(file)
    if any(c in mode for c in "wax+"):
        cache.pop(k, None)
        return _open(file, mode, buffering, encoding, errors, newline, closefd, opener)
    if k in cache:
        data = cache[k]
        if "b" in mode:
            return io.BytesIO(data)
        return io.TextIOWrapper(io.BytesIO(data), encoding=encoding or "utf-8", errors=errors, newline=newline)
    return _open(file, mode, buffering, encoding, errors, newline, closefd, opener)


io.open = cached_open
builtins.open = cached_open
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name="__main__")
print(f"[prefetch] done in {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
