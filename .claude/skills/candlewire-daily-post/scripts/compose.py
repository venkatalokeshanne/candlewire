#!/usr/bin/env python3
"""Expand a compact post file into the full spec that render_post.py reads.

  python compose.py examples/friday_nov6_close.json --out runs/<run>/spec.json

Compact text markup (headlines, titles):  *amber*  ~red~  ^green^  #cyan#   (unmarked = white)
Row strings use | as separator. Claims: [claim, value, ref_key, as_of, confidence]; refs maps key -> [source name, url]; CTA sources default to the refs used. Colors: white, amber, red, green, cyan, slate.
"""
import argparse, json, re, sys
MARK = {"*": "amber", "~": "red", "^": "green", "#": "cyan"}
def parts(s):
    out = []
    for m in re.finditer(r"([*~^#])(.+?)\1|([^*~^#]+)", s):
        if m.group(3) is not None: out.append([m.group(3), "white"])
        else: out.append([m.group(2), MARK[m.group(1)]])
    return out
def num(x): return None if x in ("", None) else float(x)
def clean(x):
    f = float(x); return int(f) if f == int(f) else f
def cols(c): return c
def footer(s): return s.get("f") or ("Sources: " + s["src"] if s.get("src") else "")
def compose(c):
    sl = []
    cv = c["cover"]
    sl.append({"type": "cover", "kicker": cv["k"], "big": cv["big"], "bigcol": cv["bc"], "bigsub": cv["sub"], "headline": parts(cv["h"]),
               "seed": cv.get("seed", 11), "gp": cv.get("gp", 0.3), "bigsize": cv.get("bigsize", 230)})
    for s in c["slides"]:
        t = s["t"]; base = {"type": t, "kicker": s["k"], "parts": parts(s["h"]), "footer": footer(s)}
        if t == "board":
            base["rows"] = [[r[0], r[1], r[2], r[3], num(r[4])] for r in (x.split("|") for x in s["rows"])]
            if "rowh" in s: base["rowh"] = s["rowh"]
            if "valsize" in s: base["valsize"] = s["valsize"]
        elif t == "cards":
            base["cards"] = [x.split("|", 2) for x in s["cards"]]
        elif t == "bignum":
            base.update({"big": s["big"], "bigcol": s["bc"], "bigsub": s["sub"], "bullets": s["bullets"]})
        elif t == "movers":
            base["rows"] = [[r[0], float(r[1]), r[2], r[3]] for r in (x.split("|") for x in s["rows"])]
        elif t == "movers2":
            base["gain"] = [[r[0], r[1], float(r[2])] for r in (x.split("|") for x in s["gain"])]
            base["lose"] = [[r[0], r[1], float(r[2])] for r in (x.split("|") for x in s["lose"])]
        elif t == "chipbars":
            base["rows"] = [[r[0], clean(r[1]), int(r[2])] for r in (x.split("|") for x in s["rows"])]; base["avg"] = s["avg"]
        elif t == "linechart":
            base["pts"] = [[r[0], clean(r[1])] for r in (x.split("|") for x in s["pts"])]; base["note"] = s["note"]
        else:
            sys.exit(f"unknown slide type {t}")
        sl.append(base)
    refs = c.get("refs", {}); claims = []; used = []
    for x in c["claims"]:
        if len(x) == 5:                     # [claim, value, ref_key, as_of, confidence]
            name, url = refs[x[2]]; x = [x[0], x[1], name, url, x[3], x[4]]
            if name not in used: used.append(name)
        claims.append(dict(zip(("claim", "value", "source", "url", "as_of", "confidence"), x)))
    ct = c["cta"]
    sl.append({"type": "cta", "sources": ct.get("src") or used, "extra": ct.get("extra")})
    return {"slot": c["slot"], "snapshot": c["snap"], "caption": c["caption"], "slides": sl, "claims": claims}
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("data"); ap.add_argument("--out", required=True); a = ap.parse_args()
    json.dump(compose(json.load(open(a.data))), open(a.out, "w"), indent=1, ensure_ascii=False); print("spec written to", a.out)
