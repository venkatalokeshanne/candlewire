#!/usr/bin/env python3
"""Render a Candlewire carousel from a spec file.

  python render_post.py specs/<spec>.json --out /path/to/output_dir

Writes slide_1.png.., jpg/slide_1.jpg.., caption.txt, claim_log.md, review_sheet.png.
Nothing is sent to Instagram by this script.
"""
import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as E
from PIL import Image

COLORS = {"amber": E.AMB, "green": E.GREEN, "red": E.RED, "cyan": E.CYAN, "white": E.TXT, "slate": E.MUT}
SLOTS = {"premarket": ("PRE-MARKET", E.AMB), "midday": ("MIDDAY UPDATE", E.CYAN), "close": ("MARKET CLOSE", E.TXT)}

def col(c):
    return COLORS[c] if isinstance(c, str) else tuple(c)

def parts(p):
    return [(t, col(c)) for t, c in p]

def rows_col(rows, idx):
    out = []
    for r in rows:
        r = list(r); r[idx] = col(r[idx]); out.append(tuple(r))
    return out

def render(spec, out_dir):
    tag, tagcol = SLOTS[spec["slot"]]
    slides = spec["slides"]
    P = E.Post(out_dir, len(slides), tag, tagcol)
    for s in slides:
        t = s["type"]; P.nx = s.get("nx")
        if t == "cover":
            P.cover(s["kicker"], s["big"], col(s["bigcol"]), s["bigsub"], parts(s["headline"]), s.get("seed", 11), s.get("gp", 0.3), s.get("bigsize", 230))
        elif t == "board":
            P.board(s["kicker"], parts(s["parts"]), rows_col(s["rows"], 3), s["footer"], s.get("rowh", 170), s.get("valsize", 84))
        elif t == "cards":
            P.cards(s["kicker"], parts(s["parts"]), s["cards"], s["footer"], s.get("cardh", 215))
        elif t == "bignum":
            P.bignum(s["kicker"], parts(s["parts"]), s["big"], col(s["bigcol"]), s["bigsub"], s["bullets"], s["footer"])
        elif t == "movers":
            P.movers(s["kicker"], parts(s["parts"]), s["rows"], s["footer"], s.get("rowh", 120))
        elif t == "movers2":
            P.movers2(s["kicker"], parts(s["parts"]), s["gain"], s["lose"], s["footer"])
        elif t == "chipbars":
            P.chipbars(s["kicker"], parts(s["parts"]), s["rows"], s["avg"], s["footer"])
        elif t == "linechart":
            P.linechart(s["kicker"], parts(s["parts"]), s["pts"], s["note"], s["footer"])
        elif t == "stat":
            P.stat(s["kicker"], s["big"], col(s["bigcol"]), s["label"], s["ctx"], s["footer"], s.get("bigsize", 300))
        elif t == "versus":
            P.versus(s["kicker"], parts(s["parts"]), [*s["left"][:3], col(s["left"][3])], [*s["right"][:3], col(s["right"][3])], s.get("win", ""), s["verdict"], s["footer"])
        elif t == "chain":
            P.chain(s["kicker"], parts(s["parts"]), [(n[0], n[1], col(n[2])) for n in s["nodes"]], s["footer"])
        elif t == "react":
            P.react(s["kicker"], s["top"], s["bottom"], s["mood"], s["footer"])
        elif t == "approve":
            P.approve(s["kicker"], s["no"], s["yes"], s["footer"])
        elif t == "ev":
            P.ev(s["kicker"], s["left"], s["right"], s["footer"])
        elif t == "react":
            P.react(s["kicker"], s["top"], s["bottom"], s["mood"], s["footer"])
        elif t == "approve":
            P.approve(s["kicker"], s["no"], s["yes"], s["footer"])
        elif t == "ev":
            P.ev(s["kicker"], s["left"], s["right"], s["footer"])
        elif t == "cta":
            P.cta(s["sources"], s.get("extra"))
        else:
            raise ValueError(f"unknown slide type {t}")
    out = Path(out_dir); (out / "jpg").mkdir(exist_ok=True)
    (out / "qa_report.json").write_text(json.dumps(P.qa, indent=1)); (out / "qa_notes.json").write_text(json.dumps(P.notes, indent=1))
    for i in range(1, len(slides) + 1):
        Image.open(out / f"slide_{i}.png" if (out / f"slide_{i}.png").exists() else out / f"slide{i}.png").convert("RGB").save(out / "jpg" / f"slide_{i}.jpg", "JPEG", quality=95, subsampling=0, optimize=True)
    (out / "caption.txt").write_text(spec["caption"].strip() + "\n")
    lines = ["# Claim log", "", f"Slot: {spec['slot']}  |  Snapshot: {spec.get('snapshot','')}", "",
             "| Claim | Value | Source | URL | As of | Confidence |", "| --- | --- | --- | --- | --- | --- |"]
    for c in spec.get("claims", []):
        lines.append("| " + " | ".join(str(c.get(k, "")) for k in ("claim", "value", "source", "url", "as_of", "confidence")) + " |")
    (out / "claim_log.md").write_text("\n".join(lines) + "\n")
    # review sheet
    th = [Image.open(out / "jpg" / f"slide_{i}.jpg").resize((360, 450)) for i in range(1, len(slides) + 1)]
    sheet = Image.new("RGB", (360 * len(th), 450)); [sheet.paste(im, (i * 360, 0)) for i, im in enumerate(th)]
    sheet.save(out / "review_sheet.png")
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    out = render(spec, a.out)
    qa = json.load(open(Path(out) / "qa_report.json", encoding="utf-8"))
    print("Rendered", len(spec["slides"]), "slides to", out)
    print("QA:", "no layout problems" if not qa else f"{len(qa)} problem(s)")
    for q in qa: print("  -", q)
    for n in json.load(open(Path(out) / "qa_notes.json", encoding="utf-8")): print("  note:", n)
    sys.exit(2 if qa else 0)
