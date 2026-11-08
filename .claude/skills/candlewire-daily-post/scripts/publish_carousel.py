#!/usr/bin/env python3
"""Publish an image carousel to Instagram with the Instagram API (Instagram Login).

Flow (per Meta's Content Publishing docs):
  1. one container per image (is_carousel_item=true)
  2. one CAROUSEL container (children + caption)
  3. media_publish
Images must be JPEG and on a public URL. Default mode is a dry run: nothing is sent.

Auth (live mode only): either env var IG_ACCESS_TOKEN, or - in a Claude Code cloud session - a network secret
for graph.facebook.com on the environment (the proxy adds the header; no token is visible to this script).
IG_USER_ID comes from the env var or config.json.
(Candlewire's Meta app uses the Facebook-login route, so the default host is graph.facebook.com.)
Usage:
  python publish_carousel.py --urls urls.txt --caption caption.txt              # dry run + URL checks
  python publish_carousel.py --urls urls.txt --caption caption.txt --live        # really publishes
"""
import argparse, datetime, json, os, sys, time
import requests

from pathlib import Path
CONFIG_DEFAULT = Path(__file__).resolve().parent.parent / "config.json"
API_BASE_DEFAULT = "https://graph.facebook.com/v27.0"

class ApiError(Exception):
    def __init__(self, status, data):
        super().__init__(f"HTTP {status}: {json.dumps(data)[:600]}")
        self.status, self.data = status, data

def log(path, **entry):
    entry["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")          # never writes the token

def call(method, url, token, **kw):
    # token=None means "proxy mode": a cloud environment's network secret adds the Authorization header for us
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.request(method, url, headers=headers, timeout=60, **kw)
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:300]}
    if r.status_code >= 400 or "error" in data:
        raise ApiError(r.status_code, data)
    return data

def wait_finished(base, container_id, token, tries=12, delay=3):
    for _ in range(tries):
        s = call("GET", f"{base}/{container_id}", token, params={"fields": "status_code"}).get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise ApiError(200, {"container": container_id, "status_code": s})
        time.sleep(delay)
    raise TimeoutError(f"container {container_id} not FINISHED after {tries*delay}s")

def upload_temp(folder):
    """Upload slide_*.jpg (sorted) to uguu.se, a temporary anonymous host. Returns direct URLs."""
    import glob
    files = sorted(glob.glob(os.path.join(folder, "slide_*.jpg")))
    if not files:
        sys.exit(f"No slide_*.jpg in {folder}")
    urls = []
    for p in files:
        with open(p, "rb") as fh:
            r = requests.post("https://uguu.se/upload?output=text", files={"files[]": fh}, timeout=60)
        u = r.text.strip()
        if r.status_code != 200 or not u.startswith("http"):
            sys.exit(f"Upload failed for {p}: HTTP {r.status_code} {u[:120]}")
        urls.append(u)
    return urls

def check_urls(urls):
    problems = []
    for u in urls:
        try:
            r = requests.get(u, stream=True, timeout=30)
            ct = r.headers.get("Content-Type", "")
            if r.status_code != 200 or "image/jpeg" not in ct:
                problems.append(f"{u} -> HTTP {r.status_code}, Content-Type '{ct}' (need 200 + image/jpeg)")
            r.close()
        except requests.RequestException as e:
            problems.append(f"{u} -> {e}")
    return problems

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", help="text file, one public JPEG URL per line, in slide order")
    ap.add_argument("--upload-dir", help="folder of slide_*.jpg to upload to a temporary public host (uguu.se) just before publishing. Test use only: links expire in hours")
    ap.add_argument("--caption", required=True, help="text file with the caption")
    ap.add_argument("--api-base", default=None, help="default: api_base from config.json")
    ap.add_argument("--config", default=str(CONFIG_DEFAULT))
    ap.add_argument("--log", default="publish_log.jsonl")
    ap.add_argument("--live", action="store_true", help="actually publish (default is a dry run)")
    a = ap.parse_args()

    if a.upload_dir:
        urls = upload_temp(a.upload_dir)
    elif a.urls:
        urls = [l.strip() for l in open(a.urls) if l.strip()]
    else:
        sys.exit("Give --urls or --upload-dir")
    caption = open(a.caption).read().strip()
    if not 2 <= len(urls) <= 10:
        sys.exit(f"Carousels need 2 to 10 images, got {len(urls)}")
    if len(caption) > 2200 or caption.count("#") > 30:
        sys.exit("Caption over 2,200 characters or more than 30 hashtags")

    problems = check_urls(urls)
    if problems:
        log(a.log, event="url_check_failed", problems=problems)
        sys.exit("Image URL problems:\n  " + "\n  ".join(problems))
    print(f"OK: {len(urls)} public JPEG URLs, caption {len(caption)} chars")

    if not a.live:
        print("DRY RUN. Would create", len(urls), "child containers, 1 carousel container, then publish. Add --live to publish.")
        log(a.log, event="dry_run", images=len(urls))
        return

    cfg = json.load(open(a.config)) if os.path.exists(a.config) else {}
    token = os.environ.get("IG_ACCESS_TOKEN")
    uid = os.environ.get("IG_USER_ID") or cfg.get("ig_user_id")
    proxy_mode = (not token) and os.environ.get("CLAUDE_CODE_REMOTE") == "true"
    if not uid or not (token or proxy_mode):
        sys.exit("Live mode needs IG_USER_ID (or config.json) and either IG_ACCESS_TOKEN or a cloud session with a network secret for graph.facebook.com")
    base = (a.api_base or cfg.get("api_base") or API_BASE_DEFAULT).rstrip("/")
    print("auth mode:", "network secret via proxy" if proxy_mode else "IG_ACCESS_TOKEN env var")
    try:
        lim = call("GET", f"{base}/{uid}/content_publishing_limit", token, params={"fields": "quota_usage,config"})
        log(a.log, event="limit_check", response=lim)
        children = []
        for i, u in enumerate(urls, 1):
            cid = call("POST", f"{base}/{uid}/media", token, json={"image_url": u, "is_carousel_item": True})["id"]
            wait_finished(base, cid, token)
            children.append(cid)
            log(a.log, event="child_ready", index=i, container=cid)
        car = call("POST", f"{base}/{uid}/media", token,
                   json={"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})["id"]
        wait_finished(base, car, token)
        media_id = call("POST", f"{base}/{uid}/media_publish", token, json={"creation_id": car})["id"]
        link = call("GET", f"{base}/{media_id}", token, params={"fields": "permalink"}).get("permalink")
        log(a.log, event="published", media_id=media_id, permalink=link, images=len(urls))
        print("PUBLISHED:", link or media_id)
    except (ApiError, TimeoutError, requests.RequestException) as e:
        log(a.log, event="error", error=str(e))
        sys.exit(f"FAILED (nothing is retried automatically): {e}")

if __name__ == "__main__":
    main()
