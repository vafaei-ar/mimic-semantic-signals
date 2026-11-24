"""Generate the two JAMIA main figures from preverified project aggregate JSON.

Scientific inputs: manuscript/figure1_nature_style_data.json
The three plotted primary effects and confidence intervals are frozen H1-H3
Open-Jev results. This script performs no model fitting, resampling or outcome
analysis and never reads patient-level data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK = "#252B33"
SUB = "#55616D"
MUTED = "#77838E"
BLUE = "#245D88"
PALE = "#ECF3F8"
LIGHT = "#D5DEE6"
WHITE = "#FFFFFF"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.linewidth": 0.7,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.facecolor": "white",
})


def _box(ax, xy, wh, title, details, *, selected=False, small=False):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.015",
        edgecolor=BLUE if selected else LIGHT,
        facecolor=PALE if selected else WHITE,
        linewidth=1.05 if selected else 0.8,
        transform=ax.transAxes, clip_on=False,
    )
    ax.add_patch(patch)
    fs = 7.2 if small else 8.1
    ax.text(x + .015, y + h - .033, title, fontsize=fs,
            fontweight="bold", color=INK, ha="left", va="top",
            transform=ax.transAxes)
    ax.text(x + .015, y + h - .077, details, fontsize=6.65 if small else 7.05,
            linespacing=1.35, color=SUB, ha="left", va="top",
            transform=ax.transAxes)


def _arrow(ax, x1, y1, x2, y2, *, color=MUTED):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), transform=ax.transAxes,
        arrowstyle="-|>", mutation_scale=8, lw=0.85, color=color,
        clip_on=False,
    ))


def _validate(data):
    design = data["design"]
    assert design["landmark_hours"] == 12
    assert design["horizon_hours"] == 12
    main = design["cohorts"][:3]
    assert [(c["n"], c["cases"]) for c in main] == [
        (11116, 279), (19395, 314), (19811, 214)
    ], "Cohort counts disagree with registered result freeze"
    rows = [r for r in data["forest"] if r["kind"] == "primary"]
    assert len(rows) == 3, "Exactly three registered primary rows required"
    expected = [
        ("Invasive ventilation", -0.00005, -0.02173, 0.01910),
        ("Renal replacement therapy", -0.00079, -0.00323, 0.00275),
        ("ICU death", -0.00212, -0.00802, 0.00531),
    ]
    for row, (label, est, lo, hi) in zip(rows, expected):
        assert row["group"] == label
        for key, value in [("estimate", est), ("lo", lo), ("hi", hi)]:
            assert abs(float(row[key]) - value) < 1e-7, (
                f"Frozen primary {label} {key} unexpectedly changed"
            )
        assert row["lo"] <= row["estimate"] <= row["hi"]
    assert len(design["semantic_constructs"]) == 8
    return main, rows


def _save(fig, out, name):
    out.mkdir(parents=True, exist_ok=True)
    base = out / name
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight",
                metadata={"Title": name, "Subject": "Registered ICU prediction: study figure"})
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight",
                metadata={"Title": name})
    fig.savefig(base.with_suffix(".png"), bbox_inches="tight", dpi=300)
    plt.close(fig)


def figure_1(design, cohorts, out):
    fig = plt.figure(figsize=(7.2, 4.45), facecolor=WHITE)
    ax = fig.add_axes([.025, .08, .95, .85])
    ax.set_axis_off()

    ax.text(0, .985, "a  Fixed observation and prediction windows",
            transform=ax.transAxes, color=INK, fontsize=9, weight="bold", va="top")
    y = .865
    x0, xmid, xend = .06, .50, .94
    ax.plot([x0, xend], [y, y], color=LIGHT, linewidth=7,
            solid_capstyle="butt", transform=ax.transAxes, clip_on=False)
    ax.plot([x0, xmid], [y, y], color=BLUE, linewidth=7,
            solid_capstyle="butt", transform=ax.transAxes, clip_on=False)
    ax.plot(xmid, y, "o", color=INK, markersize=5, transform=ax.transAxes)
    ax.text(x0, y + .050, "ICU admission", transform=ax.transAxes, color=SUB,
            ha="left", fontsize=7)
    ax.text(xmid, y + .050, "12-h landmark", transform=ax.transAxes,
            color=INK, ha="center", fontsize=8, fontweight="bold")
    ax.text(xend, y + .050, "24 h", transform=ax.transAxes, color=SUB,
            ha="right", fontsize=7)
    ax.text(.25, y - .055, "Pre-landmark information", ha="center",
            transform=ax.transAxes, color=SUB, fontsize=7)
    ax.text(.73, y - .055, "New outcome in next 12 h", ha="center",
            transform=ax.transAxes, color=SUB, fontsize=7)

    ax.text(0, .730, "b  Prespecified semantic augmentation",
            transform=ax.transAxes, color=INK, fontsize=9, weight="bold", va="top")
    _box(ax, (.01, .285), (.20, .355), "Eligible stays",
         "Adult MetaVision ICU\nstays at 12 h\n\nVentilation: n=11,116\nRRT: n=19,395\nICU death: n=19,811", small=True)
    _box(ax, (.25, .285), (.26, .355), "Two input modalities",
         "Structured: 34 core features\n+ treatment and support\n+ documentation behavior\n+ ordinary note context\n\nLatest eligible bedside note\n(before landmark, prespecified\nendpoint terms removed)", small=True)
    _box(ax, (.55, .285), (.21, .355), "Model comparison",
         "Rich structured model\n\nVERSUS\n\nSame model + eight\nsemantic scores", selected=True, small=True)
    _box(ax, (.80, .285), (.19, .355), "Three outcomes",
         "Ventilation: 279 events\n\nRRT: 314 events\n\nICU death: 214 events", small=True)
    for a, b in [(.21, .25), (.51, .55), (.76, .80)]:
        _arrow(ax, a + .006, .465, b - .006, .465)

    ax.text(.025, .195, "Eight predefined scores", fontsize=7.6,
            fontweight="bold", color=INK, transform=ax.transAxes)
    constructs = design["semantic_constructs"]
    left = "   • ".join(constructs[:4])
    right = "   • ".join(constructs[4:])
    ax.text(.025, .130, left, fontsize=6.6, color=SUB, transform=ax.transAxes)
    ax.text(.025, .083, right, fontsize=6.6, color=SUB, transform=ax.transAxes)
    ax.text(.025, .005, "Each outcome was analyzed separately. CareVue ICU death was a separate sensitivity cohort.",
            fontsize=6.3, color=MUTED, transform=ax.transAxes)
    _save(fig, out, "JAMIA_Figure_1_Study_design")


def figure_2(rows, cohorts, out):
    fig = plt.figure(figsize=(7.2, 3.1), facecolor=WHITE)
    ax = fig.add_axes([.30, .28, .57, .66])
    ax.set_facecolor(WHITE)
    ordered = list(zip(rows, cohorts))
    ys = [2, 1, 0]
    for (row, cohort), y in zip(ordered, ys):
        est, lo, hi = (float(row[k]) for k in ("estimate", "lo", "hi"))
        ax.errorbar(est, y, xerr=[[est-lo], [hi-est]],
                    fmt="o", markersize=6, color=BLUE, ecolor=BLUE,
                    elinewidth=1.4, capthick=1.2, capsize=3, zorder=3)
    ax.axvline(0, color=INK, linewidth=0.9, linestyle="--", zorder=1)
    ax.set_xlim(-.026, .024)
    ax.set_ylim(-.60, 2.65)
    ax.set_yticks(ys, ["Invasive ventilation", "Renal replacement therapy", "ICU death"])
    ax.tick_params(axis="y", length=0, labelsize=8, pad=10)
    ax.set_xticks([-.02, -.01, 0, .01, .02])
    ax.set_xticklabels(["−0.02", "−0.01", "0", "+0.01", "+0.02"])
    ax.tick_params(axis="x", labelsize=7)
    ax.set_xlabel("ΔAUROC (Open-Jev augmented minus rich structured comparator)",
                  fontsize=8, color=INK, labelpad=9)
    for spine in ["top", "left", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(LIGHT)
    ax.grid(axis="x", color=LIGHT, alpha=.55, linewidth=.55, zorder=0)

    # Figure description and interval method belong in the manuscript legend,
    # not as overlapping plot annotations. The figure contains one unlabelled panel.
    _save(fig, out, "JAMIA_Figure_2_Primary_delta_AUROC")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="outputs/manuscript/jamia_v1")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    infile = root / "manuscript" / "figure1_nature_style_data.json"
    raw = json.loads(infile.read_text(encoding="utf-8"))
    cohorts, rows = _validate(raw)
    out = (root / args.out).resolve()
    if root not in out.parents:
        raise ValueError("Output must stay inside project root")
    figure_1(raw["design"], cohorts, out)
    figure_2(rows, cohorts, out)
    print(json.dumps({"status": "completed", "input": str(infile.relative_to(root)),
                      "source_status": raw.get("status"),
                      "figures": ["JAMIA_Figure_1_Study_design",
                                  "JAMIA_Figure_2_Primary_delta_AUROC"],
                      "primary_rows": len(rows), "model_fitting": False}))


if __name__ == "__main__":
    main()
