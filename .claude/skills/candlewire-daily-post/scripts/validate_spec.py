#!/usr/bin/env python3
"""Validate a Candlewire post spec BEFORE rendering. Exit code 1 = fix the problems listed."""
import json, re, sys
BANNED = ["guaranteed", "can't lose", "cant lose", "buy now", "sell now", "easy money", "price target",
          "to the moon", "sure thing", "risk-free", "risk free", "you should buy", "you should sell"]
def strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, dict):
        for v in x.values(): yield from strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x: yield from strings(v)
def main(path):
    d = json.load(open(path)); err = []; warn = []
    slot = d.get("slot")
    if slot not in ("premarket", "midday", "close"): err.append("slot must be premarket, midday or close")
    sl = d.get("slides", [])
    if not 5 <= len(sl) <= 10: err.append(f"{len(sl)} slides; need 5 to 10")
    if not sl or sl[0].get("type") != "cover": err.append("first slide must be a cover")
    if not sl or sl[-1].get("type") != "cta": err.append("last slide must be the cta/sources slide")
    for i, s in enumerate(sl, 1):
        if s.get("type") != "cta" and not str(s.get("footer", "")).strip() and s.get("type") != "cover":
            err.append(f"slide {i} ({s.get('type')}) has no source footer")
    cap = d.get("caption", "")
    if not cap.strip(): err.append("caption missing")
    if len(cap) > 2200: err.append(f"caption {len(cap)} chars (max 2200)")
    if cap.count("#") > 5: err.append(f"{cap.count('#')} hashtags; use at most 5 (they categorize, they do not add reach)")
    first = cap.strip().split("\n")[0]
    if len(first) > 125: warn.append(f"caption first line is {len(first)} chars; only ~125 show before 'more'. Lead with the hook")
    if not re.search(r"\d", first): warn.append("caption first line has no number; lead with the key figure")
    if not re.search(r"\bsend\b", cap, re.I): warn.append("caption has no 'send this to a friend' line (sends per reach is the top reach signal)")
    if len(sl) > 7: warn.append(f"{len(sl)} slides; 6 to 7 keeps swipe-through high")
    if "not financial advice" not in cap.lower(): err.append("caption must contain 'Not financial advice'")
    if len(cap.split()) > 140: warn.append(f"caption is {len(cap.split())} words (target 120 or fewer)")
    blob = " ".join(strings(d)).lower()
    for b in BANNED:
        if b in blob: err.append(f"banned phrase: '{b}'")
    if re.search(r"TODO|XXX|lorem", blob, re.I): err.append("placeholder text found")
    if sl and sl[0].get("type") == "cover":
        k = sl[0].get("kicker", "")
        if slot in ("premarket", "midday") and not re.search(r"\d{1,2}:\d{2}\s?(AM|PM)\s?ET", k): err.append("cover kicker needs the snapshot time, e.g. '9:03 AM ET'")
        hl = " ".join(t for t, _ in sl[0].get("headline", []))
        if len(hl.split()) > 10: warn.append(f"cover headline is {len(hl.split())} words (aim for 10 or fewer)")
    claims = d.get("claims", [])
    if len(claims) < 3: err.append("need at least 3 entries in 'claims'")
    for i, c in enumerate(claims, 1):
        for k in ("claim", "source", "as_of", "confidence"):
            if not str(c.get(k, "")).strip(): err.append(f"claim {i} missing '{k}'")
    for w in warn: print("WARN:", w)
    for e in err: print("ERROR:", e)
    print("OK" if not err else f"{len(err)} error(s)")
    sys.exit(1 if err else 0)
if __name__ == "__main__": main(sys.argv[1])
