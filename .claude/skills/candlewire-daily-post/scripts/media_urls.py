#!/usr/bin/env python3
"""Print public raw.githubusercontent.com URLs for a rendered run's JPEGs and wait until they are fetchable.

  python media_urls.py --run runs/2026-11-09_premarket --branch claude/2026-11-09-premarket --out urls.txt
Needs config.json "media_repo": "<owner>/<repo>" and a PUBLIC repo, with the branch already pushed.
"""
import argparse, json, sys, time
from pathlib import Path
import requests
CFG = Path(__file__).resolve().parent.parent / "config.json"
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True); ap.add_argument("--branch", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--wait", type=int, default=120)
    ap.add_argument("--host", default="https://raw.githubusercontent.com", help="override for tests")
    a = ap.parse_args()
    repo = json.load(open(CFG)).get("media_repo", "")
    if not repo or "/" not in repo or repo.startswith("<"):
        sys.exit("Set media_repo in config.json to 'owner/repo' (a public repository)")
    files = sorted(Path(a.run, "jpg").glob("slide_*.jpg"), key=lambda p: int(p.stem.split("_")[1]))
    if not files: sys.exit(f"No JPEGs in {a.run}/jpg")
    urls = [f"{a.host}/{repo}/{a.branch}/{p.as_posix()}" for p in files]
    deadline = time.time() + a.wait; pending = list(urls)
    while pending and time.time() < deadline:
        still = []
        for u in pending:
            try:
                r = requests.get(u, stream=True, timeout=20); ok = r.status_code == 200 and "image/jpeg" in r.headers.get("Content-Type", ""); r.close()
            except requests.RequestException: ok = False
            if not ok: still.append(u)
        pending = still
        if pending: time.sleep(5)
    if pending: sys.exit("Not publicly fetchable yet (is the branch pushed and the repo public?):\n  " + "\n  ".join(pending))
    Path(a.out).write_text("\n".join(urls) + "\n"); print(f"OK: {len(urls)} public URLs written to {a.out}")
if __name__ == "__main__": main()
