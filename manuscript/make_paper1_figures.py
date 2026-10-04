"""Publication figures for Paper 1 (JAMIA), drawn with matplotlib from frozen aggregate data.

Inputs (frozen, manuscript-facing aggregate data already in the repository):
    manuscript/figure1_nature_style_data.json
    manuscript/figure2_nature_style_data.json

Outputs:
    outputs/manuscript/Figure_1.pdf / .svg / .png
    outputs/manuscript/Figure_2.pdf / .svg / .png

Every plotted number is read from the JSON files. Nothing is typed in by hand
except fixed design text (cohort definition, construct names, axis labels).

Usage:
    python manuscript/make_paper1_figures.py --root .
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# --------------------------------------------------------------------------
# Style: one accent hue, neutral inks, thin marks, generous whitespace.
# Sizes are in points at final print size (JAMIA full width ~7.2 in).
# --------------------------------------------------------------------------
INK = "#1d2329"        # primary text
INK2 = "#55606b"       # secondary text
INK3 = "#8a949e"       # muted text / reference marks
RULE = "#d9dfe5"       # grid, separators
CARD = "#f6f8fa"       # panel card fill
CARD_EDGE = "#dfe5ea"
BAND = "#e7eef6"       # shaded reference band
ACCENT = "#2a78d6"     # Open-Jev / primary (validated categorical slot 1)
ORANGE = "#eb6834"     # TF-IDF (slot 2)
AQUA = "#1baf7a"       # Open-Jev after TF-IDF (slot 3); always direct-labelled
WHITE = "#ffffff"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "FreeSans", "Liberation Sans", "DejaVu Sans"],
    "font.size": 7.5,
    "axes.edgecolor": INK3,
    "axes.linewidth": 0.6,
    "axes.labelcolor": INK2,
    "axes.labelsize": 7.5,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "legend.frameon": False,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,   # embed TrueType so text stays editable
    "svg.fonttype": "none",
    "savefig.dpi": 600,
})

W_IN = 7.2  # JAMIA full-page width


# --------------------------------------------------------------------------
# Layout helpers
# --------------------------------------------------------------------------
def card(fig, x, y, w, h, letter=None, title=None, title_h=0.032):
    """Draw a rounded panel card in figure coordinates; return the inner box."""
    fig.patches.append(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008",
        transform=fig.transFigure, facecolor=CARD, edgecolor=CARD_EDGE,
        linewidth=0.6, zorder=-10))
    if title:
        tx = x + 0.012
        if letter:
            fig.text(tx, y + h - 0.012, letter, fontsize=11, fontweight="bold",
                     color=INK, va="top", ha="left")
            tx += 0.026
        fig.text(tx, y + h - 0.0135, title, fontsize=8.5, fontweight="bold",
                 color=INK, va="top", ha="left")
    return x, y, w, h - (title_h if title else 0)


def clean_axis(ax, left=True, bottom=True):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    ax.set_facecolor("none")


def fmt_delta(v, nd=4):
    s = f"{v:+.{nd}f}"
    return s.replace("-", "−")


def save(fig, outdir: Path, stem: str):
    outdir.mkdir(parents=True, exist_ok=True)
    meta = {"Title": stem, "Author": None, "Creator": None, "Producer": None}
    fig.savefig(outdir / f"{stem}.pdf", metadata=meta)
    fig.savefig(outdir / f"{stem}.svg", metadata={"Title": stem})
    fig.savefig(outdir / f"{stem}.png", dpi=300)
    plt.close(fig)


# --------------------------------------------------------------------------
# Figure 1
# --------------------------------------------------------------------------
MARKERS = {   # kind -> (marker, facecolor, edgecolor, size)
    "primary":     ("o", ACCENT, ACCENT, 5.5),
    "sensitivity": ("o", WHITE, INK, 4.6),
    "endpoint":    ("s", WHITE, INK, 4.2),
    "timing":      ("^", WHITE, INK, 4.8),
    "replication": ("s", INK2, INK2, 4.2),
    "control":     ("D", WHITE, INK, 4.2),
}
KIND_LABEL = {
    "primary": "Primary (registered)",
    "sensitivity": "Instrument / text sensitivity",
    "endpoint": "Endpoint sensitivity",
    "timing": "Timing sensitivity",
    "replication": "CareVue replication",
    "control": "Patient-shuffled control",
}
PLAN_KEY = {"Invasive ventilation": "ventilation",
            "Renal replacement therapy": "rrt",
            "ICU death": "death_metavision"}


def design_schematic(fig, box, D):
    x0, y0, w, h = box
    cohorts = {c["outcome"]: c for c in D["design"]["cohorts"]}
    steps = 6
    gap = 0.012
    sw = (w - 0.024 - gap * (steps - 1)) / steps
    sy, sh = y0 + 0.012, h - 0.018
    xs = [x0 + 0.012 + i * (sw + gap) for i in range(steps)]

    def step(i, head, emph=False):
        fig.patches.append(FancyBboxPatch(
            (xs[i], sy), sw, sh, boxstyle="round,pad=0,rounding_size=0.006",
            transform=fig.transFigure, facecolor=WHITE,
            edgecolor=ACCENT if emph else CARD_EDGE, linewidth=0.9 if emph else 0.6, zorder=-9))
        fig.text(xs[i] + 0.008, sy + sh - 0.010, head, fontsize=7.5,
                 fontweight="bold", color=INK, va="top")
        if i < steps - 1:
            fig.patches.append(FancyArrowPatch(
                (xs[i] + sw + 0.001, sy + sh / 2), (xs[i + 1] - 0.001, sy + sh / 2),
                transform=fig.transFigure, arrowstyle="-|>", mutation_scale=6,
                color=INK3, linewidth=0.7, zorder=-8))

    def body(i, lines, top=0.030, dy=0.0145, size=6.6, color=INK2):
        for k, ln in enumerate(lines):
            fig.text(xs[i] + 0.008, sy + sh - top - k * dy, ln, fontsize=size,
                     color=color, va="top")

    # 1 Cohort
    step(0, "Cohort")
    body(0, ["MIMIC-III adult ICU", "stays (MetaVision)", "", "Age ≥18 y, NICU",
             "excluded, still in ICU", "at 12 h"])
    # 2 Landmark: a small timeline drawn in data coordinates
    step(1, "Landmark")
    ax = fig.add_axes([xs[1] + 0.010, sy + 0.030, sw - 0.020, sh * 0.42])
    ax.set_xlim(-1, 25)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    ax.add_patch(Rectangle((0, -0.18), 12, 0.36, color="#c9d6e4", lw=0))
    ax.add_patch(Rectangle((12, -0.18), 12, 0.36, color="#f3d2c3", lw=0))
    ax.plot([12, 12], [-0.55, 0.55], color=INK, lw=0.9)
    ax.plot(12, 0, "o", ms=4.5, color=INK)
    ax.text(6, 0.42, "predictors", ha="center", va="bottom", fontsize=6.2, color=INK2)
    ax.text(18, 0.42, "outcome", ha="center", va="bottom", fontsize=6.2, color=INK2)
    for t, lab in ((0, "0 h"), (12, "12 h"), (24, "24 h")):
        ax.text(t, -0.62, lab, ha="center", va="top", fontsize=6.2, color=INK2)
    body(1, ["Prediction at 12 h after", "ICU admission"], top=0.030)
    # 3 Narrative input
    step(2, "Narrative input")
    body(2, ["Latest eligible bedside", "note before landmark", "",
             "Direct treatment/endpoint", "terms removed (primary)", "",
             "No note: scores missing"])
    # 4 Eight scores
    step(3, "Eight typed scores")
    names = D["design"]["semantic_constructs"]
    for k, nm in enumerate(names):
        fig.text(xs[3] + 0.008, sy + sh - 0.031 - k * 0.0118, f"{k + 1}  {nm}",
                 fontsize=6.2, color=INK2, va="top")
    # 5 Model comparison
    step(4, "Model comparison", emph=True)
    body(4, ["Rich comparator:", "34 physiology/lab/urine", "+ treatment/support",
             "+ documentation", "   behaviour", "+ note context"], size=6.3, dy=0.0128)
    fig.text(xs[4] + 0.008, sy + 0.020, "versus", fontsize=6.3, color=INK2, va="bottom")
    fig.text(xs[4] + 0.008, sy + 0.007, "comparator + 8 scores", fontsize=6.4,
             fontweight="bold", color=ACCENT, va="bottom")
    # 6 Outcomes
    step(5, "Outcomes (12 h)")
    rows = [("Invasive ventilation", "Invasive ventilation"),
            ("Renal replacement", "RRT"),
            ("ICU death", "ICU death")]
    for k, (lab, key) in enumerate(rows):
        c = cohorts[key]
        yy = sy + sh - 0.031 - k * 0.030
        fig.text(xs[5] + 0.008, yy, lab, fontsize=6.6, color=INK, va="top")
        fig.text(xs[5] + 0.008, yy - 0.0125,
                 f"n = {c['n']:,}; events = {c['cases']}", fontsize=6.2,
                 color=INK2, va="top")


def forest(fig, box, D):
    x0, y0, w, h = box
    label_w = 0.27
    value_w = 0.215
    ax = fig.add_axes([x0 + label_w, y0 + 0.092, w - label_w - value_w - 0.015, h - 0.125])
    rows = D["forest"]
    groups = []
    for r in rows:
        if r["group"] not in groups:
            groups.append(r["group"])

    # y positions with a header gap between groups
    y = 0.0
    ypos, headers = [], []
    for g in groups:
        headers.append((g, y))
        y += 1.1
        for r in rows:
            if r["group"] == g:
                ypos.append((r, y))
                y += 1.0
        y += 0.55
    ymax = y

    xlim = (-0.032, 0.032)
    ax.set_xlim(*xlim)
    ax.set_ylim(ymax, -0.6)
    clean_axis(ax, left=False)
    ax.set_yticks([])
    ax.set_xticks([-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03])
    ax.set_xticklabels(["−0.03", "−0.02", "−0.01", "0",
                        "+0.01", "+0.02", "+0.03"])
    ax.set_xlabel("ΔAUROC (comparator + semantic scores − comparator)")
    for xv in (-0.03, -0.02, -0.01, 0.01, 0.02, 0.03):
        ax.axvline(xv, color=RULE, lw=0.5, zorder=0)

    plan = D["planning_magnitude"]
    for g, gy in headers:
        rows_g = [yy for r, yy in ypos if r["group"] == g]
        top, bot = min(rows_g) - 0.5, max(rows_g) + 0.5
        m = plan[PLAN_KEY[g]]
        ax.add_patch(Rectangle((-m, top), 2 * m, bot - top, color=BAND, lw=0, zorder=0))
        ax.annotate(g, xy=(0, gy), xycoords=("axes fraction", "data"),
                    xytext=(-label_w * W_IN * 72 + 10, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=7.8, fontweight="bold", color=INK)
        if g != groups[0]:
            ax.plot([xlim[0], xlim[1]], [gy - 0.8, gy - 0.8], color=RULE, lw=0.6,
                    clip_on=False, zorder=0)
    ax.axvline(0, color=INK, lw=0.8, ls=(0, (3, 2)), zorder=1)

    tx = fig.transFigure
    for r, yy in ypos:
        mk, fc, ec, ms = MARKERS[r["kind"]]
        ax.plot([r["lo"], r["hi"]], [yy, yy], color=ACCENT if r["kind"] == "primary" else INK2,
                lw=1.1 if r["kind"] == "primary" else 0.8, solid_capstyle="butt", zorder=2)
        for end in (r["lo"], r["hi"]):
            ax.plot([end, end], [yy - 0.18, yy + 0.18], color=ACCENT if r["kind"] == "primary" else INK2,
                    lw=0.8, zorder=2)
        ax.plot(r["estimate"], yy, marker=mk, ms=ms, mfc=fc, mec=ec, mew=0.8, zorder=3)
        # left label
        label = r["analysis"]
        ax.annotate(label, xy=(0, yy), xycoords=("axes fraction", "data"),
                    xytext=(-8, 0), textcoords="offset points", ha="right", va="center",
                    fontsize=7, color=INK if r["kind"] == "primary" else INK2,
                    fontweight="bold" if r["kind"] == "primary" else "normal")
        # right value column
        val = f"{fmt_delta(r['estimate'])}  ({fmt_delta(r['lo'])} to {fmt_delta(r['hi'])})"
        ax.annotate(val, xy=(1, yy), xycoords=("axes fraction", "data"),
                    xytext=(8, 0), textcoords="offset points", ha="left", va="center",
                    fontsize=6.4, color=INK if r["kind"] == "primary" else INK2,
                    fontweight="bold" if r["kind"] == "primary" else "normal")

    ax.annotate("ΔAUROC (95% CI)", xy=(1, -0.6), xycoords=("axes fraction", "data"),
                xytext=(8, 0), textcoords="offset points", ha="left", va="bottom",
                fontsize=6.6, color=INK2, fontweight="bold")
    ax.annotate("← comparator alone better", xy=(0.47, 1.0), xycoords="axes fraction",
                ha="right", va="bottom", fontsize=6.6, color=INK2, xytext=(0, 2),
                textcoords="offset points")
    ax.annotate("semantic scores better →", xy=(0.53, 1.0), xycoords="axes fraction",
                ha="left", va="bottom", fontsize=6.6, color=INK2, xytext=(0, 2),
                textcoords="offset points")

    handles = []
    for k in ("primary", "sensitivity", "endpoint", "timing", "replication", "control"):
        mk, fc, ec, ms = MARKERS[k]
        handles.append(Line2D([], [], ls="none", marker=mk, ms=ms, mfc=fc, mec=ec,
                              mew=0.8, label=KIND_LABEL[k]))
    handles.append(Rectangle((0, 0), 1, 1, color=BAND, label="Pre-analysis detectable ΔAUROC (±)"))
    fig.legend(handles=handles, loc="lower center", ncol=4, bbox_to_anchor=(x0 + w / 2, y0 + 0.004),
               bbox_transform=tx, handletextpad=0.4, columnspacing=1.2, fontsize=6.6)


def figure1(D, outdir):
    fig = plt.figure(figsize=(W_IN, 9.4))
    fig.patch.set_facecolor(WHITE)
    a = card(fig, 0.012, 0.79, 0.976, 0.20, "a",
             "Preregistered design: semantic-score augmentation at a fixed 12-hour ICU landmark")
    design_schematic(fig, a, D)
    b = card(fig, 0.012, 0.010, 0.976, 0.768, "b",
             "Registered estimates, sensitivity analyses and negative controls cluster near zero")
    forest(fig, b, D)
    save(fig, outdir, "Figure_1")


# --------------------------------------------------------------------------
# Figure 2
# --------------------------------------------------------------------------
def decomposition(fig, box, D2):
    x0, y0, w, h = box
    dec = D2["comparator_decomposition"]
    outcomes = list(dec["outcomes"].keys())
    pretty = {"Invasive ventilation": "Invasive ventilation", "RRT": "Renal replacement therapy",
              "ICU death": "ICU death (MetaVision)"}
    n = len(outcomes)
    left, right, bottom, top = x0 + 0.085, x0 + w - 0.02, y0 + 0.085, y0 + h - 0.035
    ph = (top - bottom - 0.03 * (n - 1)) / n
    xs = list(range(4))
    for i, oc in enumerate(outcomes):
        yb = top - (i + 1) * ph - i * 0.03
        ax = fig.add_axes([left, yb, right - left, ph])
        clean_axis(ax)
        series = dec["outcomes"][oc]
        for s in series[1:]:
            ax.plot(xs, s, color=INK3, lw=0.7, marker="o", ms=2.8, mfc=WHITE, mec=INK3, mew=0.6, zorder=2)
        ax.plot(xs, series[0], color=ACCENT, lw=1.6, marker="o", ms=4.2, mfc=ACCENT, mec=WHITE,
                mew=0.6, zorder=3)
        ax.axhline(0, color=INK, lw=0.7, ls=(0, (3, 2)), zorder=1)
        ax.set_ylim(-0.012, 0.024)
        ax.set_yticks([-0.01, 0, 0.01, 0.02])
        ax.set_yticklabels(["−0.01", "0", "+0.01", "+0.02"])
        ax.grid(axis="y", color=RULE, lw=0.5)
        ax.set_axisbelow(True)
        ax.set_xlim(-0.25, 3.25)
        ax.set_xticks(xs)
        ax.text(0.0, 1.0, pretty[oc], transform=ax.transAxes, fontsize=7.4, fontweight="bold",
                color=INK, va="bottom", ha="left")
        if i < n - 1:
            ax.set_xticklabels([])
        else:
            ax.set_xticklabels(["A\n34 physiology/\nlab/urine", "B\n+ treatment/\nsupport",
                                "C\n+ documentation\nbehaviour", "D\n+ note context\n(registered)"],
                               fontsize=6.3)
        if i == 1:
            ax.set_ylabel("ΔAUROC from adding Open-Jev", fontsize=7)
    fig.legend(handles=[
        Line2D([], [], color=ACCENT, lw=1.6, marker="o", ms=4.2, mec=WHITE, label="Primary partition"),
        Line2D([], [], color=INK3, lw=0.7, marker="o", ms=2.8, mfc=WHITE, mec=INK3, label="Four other partitions")],
        loc="lower left", bbox_to_anchor=(x0 + 0.01, y0 + 0.003), bbox_transform=fig.transFigure,
        ncol=2, fontsize=6.4)


def lexical(fig, box, D2):
    x0, y0, w, h = box
    ax = fig.add_axes([x0 + 0.15, y0 + 0.075, w - 0.175, h - 0.115])
    clean_axis(ax, left=False)
    data = D2["logistic_representation"]["outcomes"]
    rows = [("openjev", "+ Open-Jev", "o", ACCENT),
            ("tfidf", "+ TF-IDF", "s", ORANGE),
            ("openjev_after_tfidf", "+ Open-Jev after TF-IDF", "D", AQUA)]
    pretty = {"Invasive ventilation": "Invasive\nventilation", "RRT": "Renal replacement\ntherapy",
              "ICU death": "ICU death\n(MetaVision)"}
    y = 0
    ticks = []
    for oc in data:
        ticks.append((y + 1.0, pretty[oc["outcome"]]))
        for key, _lab, mk, col in rows:
            v = oc[key]
            ax.plot([0, v], [y, y], color=col, lw=0.9, alpha=0.55, zorder=1)
            ax.plot(v, y, marker=mk, ms=5, mfc=col, mec=WHITE, mew=0.6, zorder=3, ls="none")
            ax.annotate(fmt_delta(v), xy=(v, y), xytext=(6 if v >= 0 else -6, 0),
                        textcoords="offset points", ha="left" if v >= 0 else "right",
                        va="center", fontsize=6.3, color=INK2)
            y += 1
        y += 0.9
    ax.set_ylim(y - 0.5, -0.8)
    ax.set_yticks([])
    for ty, lab in ticks:
        ax.annotate(lab, xy=(0, ty), xycoords=("axes fraction", "data"), xytext=(-6, 0),
                    textcoords="offset points", ha="right", va="center", fontsize=7,
                    color=INK, fontweight="bold")
    ax.axvline(0, color=INK, lw=0.7, ls=(0, (3, 2)))
    ax.set_xlim(-0.0125, 0.0105)
    ax.set_xticks([-0.01, -0.005, 0, 0.005, 0.01])
    ax.set_xticklabels(["−0.010", "−0.005", "0", "+0.005", "+0.010"])
    ax.grid(axis="x", color=RULE, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("ΔAUROC within the same L2-logistic model")
    ax.legend(handles=[Line2D([], [], ls="none", marker=mk, ms=5, mfc=col, mec=WHITE, label=lab)
                       for _k, lab, mk, col in rows],
              loc="lower center", bbox_to_anchor=(0.40, 1.0), ncol=3, fontsize=6.3,
              handletextpad=0.3, columnspacing=0.9)
    fig.text(x0 + 0.012, y0 + 0.008, "Point estimates, primary partition; no interval was prespecified.",
             fontsize=6.2, color=INK3, style="italic")


def alignment(fig, box, D2):
    x0, y0, w, h = box
    ax = fig.add_axes([x0 + 0.215, y0 + 0.07, w - 0.235, h - 0.115])
    clean_axis(ax, left=False)
    rows = D2["alignment"]
    groups = []
    for r in rows:
        if r["outcome"] not in groups:
            groups.append(r["outcome"])
    y = 0
    heads = []
    for g in groups:
        heads.append((g, y))
        y += 0.9
        for r in [r for r in rows if r["outcome"] == g]:
            ax.plot([r["shuffled"], r["real"]], [y, y], color=RULE, lw=1.6, zorder=1,
                    solid_capstyle="round")
            ax.plot(r["shuffled"], y, "o", ms=4.2, mfc=WHITE, mec=INK3, mew=0.8, zorder=2)
            ax.plot(r["real"], y, "o", ms=4.8, mfc=ACCENT, mec=WHITE, mew=0.6, zorder=3)
            ax.annotate(r["pair"].replace(" vs ", " ↔ "), xy=(0, y),
                        xycoords=("axes fraction", "data"), xytext=(-6, 0),
                        textcoords="offset points", ha="right", va="center", fontsize=6.4,
                        color=INK2)
            y += 1
        y += 0.5
    for g, gy in heads:
        ax.annotate("ICU death" if g == "ICU death" else g, xy=(0, gy), xycoords=("axes fraction", "data"),
                    xytext=(-0.205 * W_IN * 72, 0), textcoords="offset points", ha="left", va="center",
                    fontsize=7, color=INK, fontweight="bold")
    ax.set_ylim(y - 0.3, -0.6)
    ax.set_yticks([])
    ax.axvline(0, color=INK, lw=0.7, ls=(0, (3, 2)))
    ax.set_xlim(-0.04, 0.20)
    ax.set_xticks([0, 0.05, 0.10, 0.15, 0.20])
    ax.set_xticklabels(["0", "0.05", "0.10", "0.15", "0.20"])
    ax.grid(axis="x", color=RULE, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_xlabel("Spearman ρ, score vs support state")
    ax.legend(handles=[
        Line2D([], [], ls="none", marker="o", ms=4.8, mfc=ACCENT, mec=WHITE, label="Real scores"),
        Line2D([], [], ls="none", marker="o", ms=4.2, mfc=WHITE, mec=INK3, label="Shuffled between patients")],
        loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=2, fontsize=6.4)
    fig.text(x0 + 0.012, y0 + 0.008, "Label-free audit; outcome labels not read.",
             fontsize=6.2, color=INK3, style="italic")


def note_available(fig, box, D2):
    x0, y0, w, h = box
    ax = fig.add_axes([x0 + 0.085, y0 + 0.085, w - 0.11, h - 0.13])
    clean_axis(ax)
    oc = D2["note_available"]["outcomes"]
    pretty = {"Ventilation": "Invasive ventilation", "RRT": "Renal replacement\ntherapy",
              "ICU death": "ICU death\n(MetaVision)"}
    offsets = [0, -0.18, -0.09, 0.09, 0.18]
    for i, o in enumerate(oc):
        d = o["deltas"]
        for j, v in enumerate(d[1:], start=1):
            ax.plot(i + offsets[j], v, "o", ms=4.2, mfc=WHITE, mec=INK3, mew=0.8, zorder=2)
        ax.plot(i, d[0], "o", ms=5.6, mfc=ACCENT, mec=WHITE, mew=0.6, zorder=3)
        ax.plot([i - 0.25, i + 0.25], [sum(d) / len(d)] * 2, color=INK2, lw=1.0, zorder=1)
        ax.text(i, 0.043, f"n = {o['n']:,}\nevents = {o['cases']}", ha="center", va="top",
                fontsize=6.2, color=INK2)
    ax.axhline(0, color=INK, lw=0.7, ls=(0, (3, 2)))
    ax.set_xlim(-0.6, len(oc) - 0.4)
    ax.set_xticks(range(len(oc)))
    ax.set_xticklabels([pretty[o["outcome"]] for o in oc], fontsize=6.8)
    ax.set_ylim(-0.022, 0.045)
    ax.set_yticks([-0.02, -0.01, 0, 0.01, 0.02, 0.03])
    ax.set_yticklabels(["−0.02", "−0.01", "0", "+0.01", "+0.02", "+0.03"])
    ax.grid(axis="y", color=RULE, lw=0.5)
    ax.set_axisbelow(True)
    ax.set_ylabel("ΔAUROC from adding Open-Jev")
    ax.legend(handles=[
        Line2D([], [], ls="none", marker="o", ms=5.6, mfc=ACCENT, mec=WHITE, label="Primary partition"),
        Line2D([], [], ls="none", marker="o", ms=4.2, mfc=WHITE, mec=INK3, label="Four other partitions"),
        Line2D([], [], color=INK2, lw=1.0, label="Mean of five")],
        loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=6.4)
    fig.text(x0 + 0.012, y0 + 0.008,
             "Frozen full-cohort out-of-fold predictions restricted to note-available stays; no refitting.",
             fontsize=6.2, color=INK3, style="italic")


def figure2(D2, outdir):
    fig = plt.figure(figsize=(W_IN, 7.6))
    fig.patch.set_facecolor(WHITE)
    gw = 0.012
    cw = (1 - 3 * gw) / 2
    ch_top, ch_bot = 0.475, 0.465
    a = card(fig, gw, 1 - gw - ch_top, cw, ch_top, "a", "Increment attenuates as the comparator becomes richer")
    decomposition(fig, a, D2)
    b = card(fig, 2 * gw + cw, 1 - gw - ch_top, cw, ch_top, "b", "TF-IDF keeps a small increment; eight scores do not")
    lexical(fig, b, D2)
    c = card(fig, gw, gw + 0.012, cw, ch_bot - 0.012, "c", "Scores track matching support states (label-free)")
    alignment(fig, c, D2)
    d = card(fig, 2 * gw + cw, gw + 0.012, cw, ch_bot - 0.012, "d", "No stable gain among patients with a note")
    note_available(fig, d, D2)
    fig.text(0.5, 0.0015, "Panels a, c and d are post-registration exploratory analyses; panel b is a registered secondary comparison.",
             ha="center", va="bottom", fontsize=6.2, color=INK3)
    save(fig, outdir, "Figure_2")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--out", default="outputs/manuscript")
    args = ap.parse_args()
    root = Path(args.root)
    D1 = json.loads((root / "manuscript/figure1_nature_style_data.json").read_text(encoding="utf-8"))
    D2 = json.loads((root / "manuscript/figure2_nature_style_data.json").read_text(encoding="utf-8"))
    out = root / args.out
    figure1(D1, out)
    figure2(D2, out)
    print(f"Wrote Figure_1 and Figure_2 (pdf/svg/png) to {out}")


if __name__ == "__main__":
    main()