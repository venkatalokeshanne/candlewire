#!/usr/bin/env python3
"""Suggest today's post format so the account does not repeat itself.
  python pick_format.py --slot close [--date YYYY-MM-DD] [--runs runs]
Reads "format" from runs/*_<slot>/data.json. Picks the format unused for longest, never one of the last 3, Fridays favour week-in-numbers."""
import argparse, datetime, glob, hashlib, json, os
from pathlib import Path
from zoneinfo import ZoneInfo
F = json.load(open(Path(__file__).resolve().parent.parent / "formats.json", encoding="utf-8"))
ap = argparse.ArgumentParser(); ap.add_argument("--slot", required=True, choices=list(F)); ap.add_argument("--date"); ap.add_argument("--runs", default="runs")
a = ap.parse_args()
today = datetime.date.fromisoformat(a.date) if a.date else datetime.datetime.now(ZoneInfo("America/New_York")).date()
hist = []
for p in glob.glob(f"{a.runs}/*_{a.slot}/data.json"):
    try:
        d = datetime.date.fromisoformat(os.path.basename(os.path.dirname(p)).split("_")[0]); fm = json.load(open(p, encoding="utf-8")).get("format")
        if fm and d < today: hist.append((d, fm))
    except Exception: pass
hist.sort(reverse=True); recent = [f for _, f in hist[:3]]
cands = [f for f in F[a.slot] if not f.get("friday_only") or today.weekday() == 4]
allowed = [f for f in cands if f["name"] not in recent] or cands
def age(f):
    ds = [d for d, n in hist if n == f["name"]]; return (today - max(ds)).days if ds else 999
fri = [f for f in allowed if f.get("friday_only") and age(f) > 6]
pick = fri[0] if fri else max(allowed, key=lambda f: (age(f), hashlib.sha1((str(today) + f["name"]).encode()).hexdigest()))
print(json.dumps({"format": pick["name"], "pattern": pick["pattern"].split(","), "use": pick["use"], "avoid_repeating": recent}))
