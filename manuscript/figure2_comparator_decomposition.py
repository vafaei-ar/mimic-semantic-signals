from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "manuscript" / "figure2_comparator_decomposition_data.json"
OUTDIR = ROOT / "outputs" / "manuscript"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "figure2_comparator_decomposition.svg"

with DATA.open("r", encoding="utf-8") as f:
    payload = json.load(f)

W, H = 1120, 1180
LEFT, RIGHT = 180, 1050
TOP = 105
PANEL_H = 300
GAP = 65
YMIN, YMAX = -0.010, 0.025
levels = payload["levels"]

def esc(s):
    return html.escape(str(s))

def sx(i):
    return LEFT + i * (RIGHT - LEFT) / 3.0

def sy(v, y0):
    return y0 + PANEL_H - 45 - (v - YMIN) / (YMAX - YMIN) * (PANEL_H - 85)

svg=[]
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
svg.append('<rect width="100%" height="100%" fill="white"/>')
svg.append('<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.title{font-size:25px;font-weight:700}.panel{font-size:21px;font-weight:700}.tick{font-size:14px}.xlab{font-size:14px}.note{font-size:13px;fill:#333}.grid{stroke:#e5e5e5;stroke-width:1}.zero{stroke:#555;stroke-width:1.4;stroke-dasharray:6 5}.secondary{stroke:#aaa;stroke-width:1.4;fill:none}.primary{stroke:#111;stroke-width:2.8;fill:none}.open{fill:white;stroke:#888;stroke-width:1.5}.filled{fill:#111;stroke:#111}</style>')
svg.append('<text x="40" y="40" class="title">Open-Jev increment across nested structured comparators</text>')

ticks=[-0.01,0.0,0.01,0.02]
for pi,(outcome,repeats) in enumerate(payload["outcomes"].items()):
    y0=TOP + pi*(PANEL_H+GAP)
    panel=chr(ord("A")+pi)
    svg.append(f'<text x="40" y="{y0-22}" class="panel">{panel}</text>')
    svg.append(f'<text x="80" y="{y0-22}" class="panel">{esc(outcome)}</text>')

    for t in ticks:
        y=sy(t,y0)
        cls="zero" if abs(t)<1e-12 else "grid"
        svg.append(f'<line x1="{LEFT}" y1="{y:.1f}" x2="{RIGHT}" y2="{y:.1f}" class="{cls}"/>')
        svg.append(f'<text x="{LEFT-18}" y="{y+5:.1f}" text-anchor="end" class="tick">{t:+.2f}</text>')

    # secondary frozen partitions first
    for ri,vals in enumerate(repeats[1:],start=2):
        pts=" ".join(f'{sx(i):.1f},{sy(v,y0):.1f}' for i,v in enumerate(vals))
        svg.append(f'<polyline points="{pts}" class="secondary"/>')
        for i,v in enumerate(vals):
            x,y=sx(i),sy(v,y0)
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.8" class="open"/>')

    # primary partition
    vals=repeats[0]
    pts=" ".join(f'{sx(i):.1f},{sy(v,y0):.1f}' for i,v in enumerate(vals))
    svg.append(f'<polyline points="{pts}" class="primary"/>')
    for i,v in enumerate(vals):
        x,y=sx(i),sy(v,y0)
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.2" class="filled"/>')

    for i,label in enumerate(["A","B","C","D"]):
        svg.append(f'<text x="{sx(i):.1f}" y="{y0+PANEL_H-13}" text-anchor="middle" class="xlab">{label}</text>')

    svg.append(f'<text x="{(LEFT+RIGHT)/2:.1f}" y="{y0+PANEL_H+18}" text-anchor="middle" class="note">A: structured 34    B: + treatment/support    C: + documentation behavior    D: + note context</text>')

svg.append(f'<text x="30" y="{H-50}" class="note">Filled black line: prespecified primary partition. Open gray lines: four additional frozen patient-grouped partitions.</text>')
svg.append(f'<text x="30" y="{H-28}" class="note">No new bootstrap was performed; across-partition spread is a stability summary, not a confidence interval.</text>')
svg.append('</svg>')

OUT.write_text("\n".join(svg),encoding="utf-8")
print(json.dumps({"status":"completed","svg":str(OUT.relative_to(ROOT)),"outcomes":len(payload["outcomes"])},indent=2))
