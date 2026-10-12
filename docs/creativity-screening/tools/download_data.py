"""Download the public participant-level data deposits found by the data check (forms/data/<cid>.json) to D:.

Germ\u00e1n, 2026-10-09: "Downloads of data should go to D:\\ (dataman)".

Each deposit goes to its own folder, D:/projects/ai-skill-atlas/creativity-data/<repository>-<id>/, once, even when several
papers share it. manifest.json there records, for every file, the source URL, the local path, the size, the SHA-256 hash,
and the download time, plus which papers use which deposit. A copy of the manifest is kept in the screening folder as
data-manifest.json. Downloads are untrusted data: nothing in them is ever executed, and zip files are unpacked with a
path check into an 'unpacked' folder next to the zip.

Deposits downloaded: access "public" and contents participant_level, output_level_with_participant_id, or unclear.
Repositories handled: OSF (including view-only links), GitHub (repository zip), Zenodo, Dryad, Harvard Dataverse,
Figshare. Other links are listed in the manifest as "manual" and not fetched.

Usage: python tools/download_data.py [--only c006 c010 ...] [--max-file-gb 2]
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

SCREEN = Path("C:/Dropbox/Admin/website/ai-skill-atlas/docs/creativity-screening")
DEST = Path("D:/projects/ai-skill-atlas/creativity-data")
UA = {"User-Agent": "atlas-data/0.1"}
KEEP = {"participant_level", "output_level_with_participant_id", "unclear"}


def get(url, binary=False, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
                return data if binary else json.loads(data.decode("utf-8"))
        except Exception as e:  # rate limits and transient errors
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"GET failed: {url}: {last}")


def stream(url, path, max_bytes):
    """Download url to path; return (size, sha256). Refuses files above max_bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    size = 0
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, open(str(path) + ".part", "wb") as fh:
        clen = r.headers.get("Content-Length")
        if clen and int(clen) > max_bytes:
            raise RuntimeError(f"file larger than the limit ({int(clen):,} bytes)")
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise RuntimeError("file larger than the limit")
            h.update(chunk)
            fh.write(chunk)
    os.replace(str(path) + ".part", path)
    return size, h.hexdigest()


def safe_name(s):
    s = re.sub(r"[<>:\"|?*\x00-\x1f]", "_", str(s)).strip().rstrip(".")
    return s or "file"


def unpack(zpath):
    """Unpack a zip next to itself, refusing members that would land outside the target folder."""
    target = zpath.parent / (zpath.stem + "-unpacked")
    if target.exists():
        return str(target)
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():
            dest = (target / m.filename).resolve()
            if not str(dest).startswith(str(target.resolve())):
                raise RuntimeError(f"unsafe path in zip: {m.filename}")
        z.extractall(target)
    return str(target)


# ------------------------------------------------------------------ repositories -> list of (relative path, url)
def osf_files(url):
    m = re.search(r"osf\.io/([a-z0-9]{5})", url, flags=re.I)
    vo = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("view_only", [None])[0]
    if not m:
        raise RuntimeError("no OSF id in URL")
    gid = m.group(1).lower()
    q = f"?view_only={vo}" if vo else ""

    def tok(u):
        # API links can already carry the view-only token; add it once, with the right separator.
        if not vo or "view_only=" in u:
            return u
        return u + ("&" if "?" in u else "?") + f"view_only={vo}"
    g = get(tok(f"https://api.osf.io/v2/guids/{gid}/?resolve=false"))
    kind = (g.get("data") or {}).get("type")
    out = []
    if kind == "files":
        f = get(tok(f"https://api.osf.io/v2/files/{gid}/"))["data"]
        out.append((f["attributes"]["name"], tok(f["links"]["download"]), f["attributes"].get("size")))
        return f"osf-{gid}", out

    def walk(listing_url, prefix):
        nxt = tok(listing_url)
        while nxt:
            page = get(nxt)
            for it in page.get("data", []):
                a = it["attributes"]
                if a.get("kind") == "folder":
                    walk(it["relationships"]["files"]["links"]["related"]["href"], prefix + a["name"] + "/")
                else:
                    out.append((prefix + a["name"], tok(it["links"]["download"]), a.get("size")))
            nxt = (page.get("links") or {}).get("next")
            nxt = tok(nxt) if nxt else None

    def node(nid, prefix):
        walk(f"https://api.osf.io/v2/nodes/{nid}/files/osfstorage/", prefix)
        ch = get(tok(f"https://api.osf.io/v2/nodes/{nid}/children/"))
        for c in ch.get("data", []):
            node(c["id"], prefix + safe_name(c["attributes"]["title"]) + f" ({c['id']})/")

    node(gid, "")
    return f"osf-{gid}", out


def github_files(url):
    m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url)
    if not m:
        raise RuntimeError("no GitHub repository in URL")
    owner, repo = m.group(1), re.sub(r"\.git$", "", m.group(2))
    return f"github-{owner}-{repo}", [(f"{repo}.zip", f"https://codeload.github.com/{owner}/{repo}/zip/HEAD", None)]


def zenodo_files(url):
    m = re.search(r"zenodo\.org/(?:records?|deposit)/(\d+)", url) or re.search(r"10\.5281/zenodo\.(\d+)", url)
    if not m:
        raise RuntimeError("no Zenodo record in URL")
    rid = m.group(1)
    rec = get(f"https://zenodo.org/api/records/{rid}")
    out = []
    for f in rec.get("files", []):
        link = (f.get("links") or {}).get("content") or (f.get("links") or {}).get("self")
        out.append((f.get("key") or f.get("filename"), link, f.get("size")))
    return f"zenodo-{rid}", out


def dryad_files(url):
    m = re.search(r"(10\.5061/dryad\.[a-z0-9]+)", url, flags=re.I)
    if not m:
        raise RuntimeError("no Dryad DOI in URL")
    doi = m.group(1)
    ds = get("https://datadryad.org/api/v2/datasets/" + urllib.parse.quote("doi:" + doi, safe=""))
    ver = ds["_links"]["stash:version"]["href"]
    files = get("https://datadryad.org" + ver + "/files")
    out = []
    for f in (files.get("_embedded") or {}).get("stash:files", []):
        out.append((f["path"], "https://datadryad.org" + f["_links"]["stash:download"]["href"], f.get("size")))
    return "dryad-" + doi.split("dryad.")[1], out


def dataverse_files(url):
    m = re.search(r"(10\.7910/DVN/[A-Z0-9]+)", url, flags=re.I)
    if not m:
        raise RuntimeError("no Dataverse DOI in URL")
    doi = m.group(1)
    ds = get("https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:" + doi)
    out = []
    for f in ds["data"]["latestVersion"].get("files", []):
        df = f["dataFile"]
        name = (f.get("directoryLabel") + "/" if f.get("directoryLabel") else "") + (df.get("originalFileName") or df.get("filename"))
        out.append((name, f"https://dataverse.harvard.edu/api/access/datafile/{df['id']}?format=original", df.get("originalFileSize") or df.get("filesize")))
    return "dataverse-" + doi.split("/")[-1], out


def figshare_files(url):
    m = re.search(r"figshare\.com/(?:articles/[^/]+/[^/]+/|ndownloader/articles/)(\d+)", url) or re.search(r"figshare\.(\d+)", url)
    if not m:
        raise RuntimeError("no Figshare article in URL")
    aid = m.group(1)
    art = get(f"https://api.figshare.com/v2/articles/{aid}")
    return f"figshare-{aid}", [(f["name"], f["download_url"], f.get("size")) for f in art.get("files", [])]


def mendeley_files(url):
    m = re.search(r"data\.mendeley\.com/datasets/([a-z0-9]+)(?:/(\d+))?", url)
    if not m:
        raise RuntimeError("no Mendeley Data dataset in URL")
    did, ver = m.group(1), m.group(2) or "1"
    files = get(f"https://data.mendeley.com/public-api/datasets/{did}/files?folder_id=root&version={ver}")
    out = []
    for f in files:
        cd = f.get("content_details") or {}
        link = cd.get("download_url") or f"https://data.mendeley.com/public-files/datasets/{did}/files/{f['id']}/file_downloaded"
        out.append((f.get("filename"), link, cd.get("size") or f.get("size")))
    return f"mendeley-{did}-v{ver}", out


def handler(dep):
    u = str(dep.get("url") or "")
    r = (str(dep.get("repository") or "") + " " + u).lower()
    if "osf.io" in r:
        return osf_files
    if "github.com" in r:
        return github_files
    if "zenodo" in r:
        return zenodo_files
    if "dryad" in r:
        return dryad_files
    if "dataverse" in r or "10.7910/dvn" in r:
        return dataverse_files
    if "figshare" in r:
        return figshare_files
    if "data.mendeley.com" in r:
        return mendeley_files
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--max-file-gb", type=float, default=2.0)
    a = ap.parse_args()
    max_bytes = int(a.max_file_gb * (1 << 30))
    DEST.mkdir(parents=True, exist_ok=True)
    mpath = DEST / "manifest.json"
    manifest = json.load(io.open(mpath, encoding="utf-8")) if mpath.exists() else {"deposits": {}, "papers": {}, "manual": []}
    manifest["manual"] = []  # rebuilt on every run
    manifest["errors"] = []
    records = sorted(glob.glob(str(SCREEN / "forms" / "data" / "c*.json")))
    for rp in records:
        d = json.load(io.open(rp, encoding="utf-8"))
        cid = d.get("cid")
        if a.only and cid not in a.only:
            continue
        for dep in d.get("deposits") or []:
            if dep.get("access") != "public" or dep.get("contents") not in KEEP:
                continue
            h = handler(dep)
            if h is None:
                item = {"cid": cid, "url": dep.get("url"), "repository": dep.get("repository"), "contents": dep.get("contents")}
                if item not in manifest["manual"]:
                    manifest["manual"].append(item)
                continue
            try:
                key, files = h(dep.get("url"))
            except Exception as e:
                print(f"{cid}: listing failed for {dep.get('url')}: {e}")
                manifest.setdefault("errors", []).append({"cid": cid, "url": dep.get("url"), "error": str(e)[:300],
                                                          "at": datetime.now().isoformat(timespec="seconds")})
                continue
            manifest["papers"].setdefault(cid, [])
            if key not in manifest["papers"][cid]:
                manifest["papers"][cid].append(key)
            entry = manifest["deposits"].setdefault(key, {"source_url": dep.get("url"), "repository": dep.get("repository"),
                                                         "license": dep.get("license"), "files": {}})
            folder = DEST / key
            for rel, url, size in files:
                rel = "/".join(safe_name(p) for p in str(rel).split("/"))
                if rel in entry["files"] and (folder / rel).exists():
                    continue
                if size and int(size) > max_bytes:
                    entry["files"][rel] = {"url": url, "skipped": f"larger than {a.max_file_gb} GB ({int(size):,} bytes)"}
                    continue
                try:
                    for attempt in range(4):
                        try:
                            n, sha = stream(url, folder / rel, max_bytes)
                            break
                        except urllib.error.HTTPError as e:
                            if e.code in (401, 403, 404, 410) or attempt == 3:
                                raise
                            time.sleep(10 * (attempt + 1))
                        except (TimeoutError, OSError) as e:
                            if attempt == 3:
                                raise
                            time.sleep(10 * (attempt + 1))
                    rec = {"url": url, "path": str(folder / rel), "bytes": n, "sha256": sha,
                           "downloaded_at": datetime.now().isoformat(timespec="seconds")}
                    if rel.lower().endswith(".zip"):
                        try:
                            rec["unpacked"] = unpack(folder / rel)
                        except Exception as e:
                            rec["unpack_error"] = str(e)[:200]
                    entry["files"][rel] = rec
                    print(f"{cid}: {key}/{rel} ({n:,} bytes)")
                except Exception as e:
                    entry["files"][rel] = {"url": url, "error": str(e)[:300]}
                    print(f"{cid}: FAILED {key}/{rel}: {e}")
                time.sleep(0.5)
            with io.open(mpath, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, ensure_ascii=False, indent=1)
    with io.open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    shutil.copyfile(mpath, SCREEN / "data-manifest.json")
    n_files = sum(1 for dep in manifest["deposits"].values() for f in dep["files"].values() if f.get("sha256"))
    n_bytes = sum(f.get("bytes", 0) for dep in manifest["deposits"].values() for f in dep["files"].values())
    print(f"deposits: {len(manifest['deposits'])} | files downloaded: {n_files} | {n_bytes / 1e6:,.1f} MB | papers: {len(manifest['papers'])} "
          f"| manual: {len(manifest['manual'])} | errors: {len(manifest.get('errors', []))}")


if __name__ == "__main__":
    main()
