"""One style for every figure of the paper, taken from the Nature papers used as the benchmark
(Köbis et al. 2025, Betley et al. 2026, CAIS 2026).

Every figure builder imports this module and uses only these colours, these sizes and these
helpers, so the nine figures share one ground, one palette and one type. Nothing else about the
look is decided inside a builder.

Rules the module enforces or supports:
- pure white ground, no panel backgrounds, no shaded regions, no in-figure titles, subtitles,
  footnotes or notes: the caption carries them;
- panel letters a, b, c in bold lower case at the top left of each panel, nothing else bold;
- Arial (Helvetica) throughout, 7 pt labels, 6.5 pt tick labels, 7 pt value labels in regular
  weight, at the final printed width (88 mm single column, 180 mm double column);
- one purple with one tint, one grey with one tint, one red used only for harm, black text;
- thin whiskers with small caps; top and right spines off; no grid lines.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

# ---------------------------------------------------------------- palette
PURPLE = "#5B54D6"        # the one accent: the measured quantity
PURPLE_TINT = "#C9C6F1"   # its tint: a secondary series or a comparison
GREY = "#8C8C8C"          # references, baselines, the control
GREY_TINT = "#DADADA"     # a lighter comparison
RED = "#C8453A"           # harm only, used sparingly
INK = "#1A1A1A"           # text and spines
WHITE = "#FFFFFF"

# ---------------------------------------------------------------- type and sizes
FONT = "Arial"
PT_LABEL = 7.0
PT_TICK = 6.5
PT_VALUE = 7.0
PT_PANEL = 8.0
MM = 1 / 25.4
SINGLE_MM = 88.0
DOUBLE_MM = 180.0
LINE = 0.6               # spines, whiskers, connectors, in points


def apply():
    """Set matplotlib for the paper. Call once at the top of every builder."""
    rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "font.size": PT_LABEL,
        "axes.labelsize": PT_LABEL,
        "axes.titlesize": PT_LABEL,
        "xtick.labelsize": PT_TICK,
        "ytick.labelsize": PT_TICK,
        "legend.fontsize": PT_LABEL,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "axes.linewidth": LINE,
        "xtick.major.width": LINE,
        "ytick.major.width": LINE,
        "xtick.major.size": 2.0,
        "ytick.major.size": 2.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "savefig.facecolor": WHITE,
        "legend.frameon": False,
        "legend.handlelength": 1.0,
        "legend.handleheight": 0.7,
        "legend.columnspacing": 1.2,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })


def figure(width_mm: float, height_mm: float):
    """A white figure at its final printed size."""
    apply()
    return plt.figure(figsize=(width_mm * MM, height_mm * MM), facecolor=WHITE)


def panel_label(ax, letter: str, dx: float = -0.12, dy: float = 1.04):
    """The bold lower-case panel letter, top left, outside the axes."""
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=PT_PANEL, fontweight="bold",
            ha="left", va="bottom", color=INK)


def clean(ax):
    """Top and right spines off, no grid, ticks out, black ink."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(LINE)
        ax.spines[side].set_color(INK)
    ax.grid(False)
    ax.tick_params(direction="out", length=2.0, width=LINE, colors=INK, labelsize=PT_TICK)
    ax.set_facecolor(WHITE)


def whisker_kw():
    """Thin error bars with small caps."""
    return dict(ecolor=INK, elinewidth=LINE, capsize=1.5, capthick=LINE)


def value_label(ax, x, y, text, dy_pt: float = 2.0):
    """A regular-weight value above a bar or a whisker end."""
    ax.annotate(text, (x, y), xytext=(0, dy_pt), textcoords="offset points",
                ha="center", va="bottom", fontsize=PT_VALUE, color=INK)


def legend_row(ax, handles, labels, y: float = 1.02):
    """One legend row above the axes, no frame."""
    return ax.legend(handles, labels, loc="lower left", bbox_to_anchor=(0.0, y), ncol=len(labels),
                     frameon=False, fontsize=PT_LABEL, handlelength=1.0, borderaxespad=0.0)


def save(fig, stem: str, folder: Path, dpi: int = 300):
    """PNG at 300 dpi and a vector PDF, white ground, tight but with a small margin."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(folder / f"{stem}.{ext}", dpi=dpi, facecolor=WHITE, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return folder / f"{stem}.png"


if __name__ == "__main__":
    # a self-check: a single-column bar panel in the style, written to a temp folder
    import numpy as np
    import tempfile
    fig = figure(SINGLE_MM, 60)
    ax = fig.add_axes([0.16, 0.18, 0.80, 0.74])
    x = np.arange(2)
    ax.bar(x, [95, 20], color=[PURPLE, GREY], width=0.6)
    ax.errorbar(1, 20, yerr=[[8], [9]], fmt="none", **whisker_kw())
    value_label(ax, 0, 95, "95"); value_label(ax, 1, 29, "20")
    ax.set_xticks(x); ax.set_xticklabels(["Asked", "Acting"])
    ax.set_ylabel("Share (%)"); ax.set_ylim(0, 105)
    clean(ax); panel_label(ax, "a")
    out = save(fig, "figstyle-selftest", Path(tempfile.gettempdir()))
    print("figstyle self-check written:", out)
