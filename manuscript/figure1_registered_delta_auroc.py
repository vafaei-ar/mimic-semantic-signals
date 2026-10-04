from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "manuscript" / "figure1_registered_delta_auroc_data.json"
OUTDIR = ROOT / "outputs" / "manuscript"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "figure1_registered_delta_auroc.svg"

with DATA.open("r", encoding="utf-8") as f:
    payload = json.load(f)

W, H = 1400, 1120
LEFT = 500
RIGHT = 1325
TOP = 95
XMIN, XMAX = -0.032, 0.032

def sx(x: float) -> float:
    return LEFT + (x - XMIN) / (XMAX - XMIN) * (RIGHT - LEFT)

def esc(s: str) -> str:
    return html.escape(str(s))

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
svg.append('<rect width="100%" height="100%" fill="white"/>')
svg.append('<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.title{font-size:26px;font-weight:700}.panel{font-size:24px;font-weight:700}.head{font-size:20px;font-weight:700}.lab{font-size:17px}.axis{font-size:16px}.note{font-size:14px;fill:#333}.grid{stroke:#e4e4e4;stroke-width:1}.zero{stroke:#666;stroke-width:1.5;stroke-dasharray:6 5}.ci{stroke:#111;stroke-width:2}.cap{stroke:#111;stroke-width:2}.sep{stroke:#ddd;stroke-width:1}</style>')
svg.append('<text x="45" y="42" class="title">Incremental discrimination from low-dimensional semantic scores</text>')

def draw_panel(rows, y0, row_h, title, panel, panel_h):
    svg.append(f'<text x="45" y="{y0-28}" class="panel">{panel}</text>')
    svg.append(f'<text x="90" y="{y0-28}" class="head">{esc(title)}</text>')

    ticks = [-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03]
    bottom = y0 + row_h * len(rows)
    for t in ticks:
        x = sx(t)
        cls = "zero" if t == 0 else "grid"
        svg.append(f'<line x1="{x:.1f}" y1="{y0-8}" x2="{x:.1f}" y2="{bottom-5}" class="{cls}"/>')
        svg.append(f'<text x="{x:.1f}" y="{bottom+24}" text-anchor="middle" class="axis">{t:+.2f}</text>')

    last_outcome = None
    for i, r in enumerate(rows):
        y = y0 + i * row_h + row_h * 0.45
        if last_outcome is not None and r["outcome"] != last_outcome:
            svg.append(f'<line x1="45" y1="{y-row_h*0.55:.1f}" x2="{RIGHT}" y2="{y-row_h*0.55:.1f}" class="sep"/>')
        last_outcome = r["outcome"]
        label = f'{r["outcome"]} | {r["analysis"]}'
        svg.append(f'<text x="{LEFT-18}" y="{y+6:.1f}" text-anchor="end" class="lab">{esc(label)}</text>')

        x1, x2, xm = sx(r["lo"]), sx(r["hi"]), sx(r["estimate"])
        svg.append(f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" class="ci"/>')
        svg.append(f'<line x1="{x1:.1f}" y1="{y-6:.1f}" x2="{x1:.1f}" y2="{y+6:.1f}" class="cap"/>')
        svg.append(f'<line x1="{x2:.1f}" y1="{y-6:.1f}" x2="{x2:.1f}" y2="{y+6:.1f}" class="cap"/>')

        cat = r["category"]
        if cat == "Primary":
            svg.append(f'<circle cx="{xm:.1f}" cy="{y:.1f}" r="7" fill="#111" stroke="#111"/>')
        elif cat == "Replication":
            svg.append(f'<circle cx="{xm:.1f}" cy="{y:.1f}" r="7" fill="#777" stroke="#111" stroke-width="1.5"/>')
        elif cat == "H7 shuffled control":
            pts = f'{xm:.1f},{y-8:.1f} {xm+8:.1f},{y:.1f} {xm:.1f},{y+8:.1f} {xm-8:.1f},{y:.1f}'
            svg.append(f'<polygon points="{pts}" fill="white" stroke="#111" stroke-width="2"/>')
        else:
            svg.append(f'<rect x="{xm-6.5:.1f}" y="{y-6.5:.1f}" width="13" height="13" fill="white" stroke="#111" stroke-width="2"/>')

    svg.append(f'<text x="{(LEFT+RIGHT)/2:.1f}" y="{bottom+54}" text-anchor="middle" class="axis">Delta AUROC (augmented minus comparator)</text>')
    return bottom + 78

y = 100
y = draw_panel(
    payload["primary_and_h6"], y, 48,
    "Registered primary and principal semantic-instrument sensitivity analyses", "A", 650
)
y += 35
y = draw_panel(
    payload["replication_and_negative_controls"], y, 50,
    "Source replication and patient-shuffled negative controls", "B", 330
)

svg.append(f'<text x="45" y="{H-28}" class="note">Points are delta AUROC estimates; horizontal lines are 95% patient-cluster refit-bootstrap intervals. All displayed intervals span zero.</text>')
svg.append('</svg>')

OUT.write_text("\n".join(svg), encoding="utf-8")
print(json.dumps({
    "status": "completed",
    "data_file": str(DATA.relative_to(ROOT)),
    "svg": str(OUT.relative_to(ROOT)),
    "rows_panel_a": len(payload["primary_and_h6"]),
    "rows_panel_b": len(payload["replication_and_negative_controls"]),
}, indent=2))
