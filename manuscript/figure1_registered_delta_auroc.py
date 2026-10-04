from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "manuscript" / "figure1_registered_delta_auroc_data.json"
OUTDIR = ROOT / "outputs" / "manuscript"
OUTDIR.mkdir(parents=True, exist_ok=True)

with DATA.open("r", encoding="utf-8") as f:
    payload = json.load(f)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig = plt.figure(figsize=(7.2, 6.2))
gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1.0], hspace=0.42)
axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0])]

def draw_panel(ax, rows, title, panel_label, xlim):
    ys = np.arange(len(rows))[::-1]
    for y, row in zip(ys, rows):
        marker = "o" if row["category"] in {"Primary", "Replication"} else "s"
        mfc = "black" if row["category"] == "Primary" else "white"
        if row["category"] == "Replication":
            mfc = "0.35"
        if row["category"] == "H7 shuffled control":
            marker = "D"
        ax.errorbar(
            row["estimate"], y,
            xerr=[[row["estimate"] - row["lo"]], [row["hi"] - row["estimate"]]],
            fmt=marker, ms=5.5, mfc=mfc, mec="black", mew=0.9,
            ecolor="black", elinewidth=1.0, capsize=2.5, capthick=1.0,
            zorder=3,
        )

    ax.axvline(0, color="0.35", lw=1.0, ls="--", zorder=1)
    ax.set_xlim(*xlim)
    ax.set_yticks(ys)
    labels = [f'{r["outcome"]}  |  {r["analysis"]}' for r in rows]
    ax.set_yticklabels(labels)
    ax.set_xlabel("Delta AUROC (augmented minus comparator)")
    ax.set_title(title, loc="left", pad=8)
    ax.text(-0.07, 1.04, panel_label, transform=ax.transAxes,
            fontsize=11, fontweight="bold", va="bottom")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color="0.9", lw=0.6, zorder=0)

    # Outcome separators
    outcomes = [r["outcome"] for r in rows]
    for i in range(1, len(rows)):
        if outcomes[i] != outcomes[i-1]:
            ysep = (ys[i-1] + ys[i]) / 2
            ax.axhline(ysep, color="0.88", lw=0.7, zorder=0)

draw_panel(
    axes[0],
    payload["primary_and_h6"],
    "Registered primary and principal semantic-instrument sensitivity analyses",
    "A",
    (-0.032, 0.032),
)

draw_panel(
    axes[1],
    payload["replication_and_negative_controls"],
    "Source replication and patient-shuffled negative controls",
    "B",
    (-0.032, 0.032),
)

fig.suptitle(
    "Incremental discrimination from low-dimensional semantic scores",
    x=0.08, ha="left", fontsize=11.5, fontweight="bold", y=0.995
)

fig.text(
    0.08, 0.012,
    "Points are delta AUROC estimates; horizontal lines are 95% patient-cluster refit-bootstrap intervals. "
    "All displayed intervals span zero.",
    fontsize=7.8, ha="left", va="bottom"
)

fig.subplots_adjust(left=0.33, right=0.98, top=0.94, bottom=0.08)

pdf = OUTDIR / "figure1_registered_delta_auroc.pdf"
png = OUTDIR / "figure1_registered_delta_auroc.png"
fig.savefig(pdf, bbox_inches="tight")
fig.savefig(png, dpi=600, bbox_inches="tight")
plt.close(fig)

print(json.dumps({
    "status": "completed",
    "data_file": str(DATA.relative_to(ROOT)),
    "pdf": str(pdf.relative_to(ROOT)),
    "png": str(png.relative_to(ROOT)),
    "rows_panel_a": len(payload["primary_and_h6"]),
    "rows_panel_b": len(payload["replication_and_negative_controls"]),
}, indent=2))
