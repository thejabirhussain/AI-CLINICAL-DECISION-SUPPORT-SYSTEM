"""Render the poster figures from the fault-injection results.

Outputs vector PDF (for print) and 300 dpi PNG (for drafts) sized for a
185 mm-wide panel on an A2 poster. Fonts are set in points so that the PDF,
placed at 185 mm, reads correctly at 1-1.5 m.

Usage: python make_figures.py --results results/ --outdir figures/
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

# Validated two-slot categorical palette (dataviz reference instance, light mode)
BLUE, RED = "#2a78d6", "#e34948"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8b8a85"
SURFACE = "#fcfcfb"

PANEL_IN = 185 / 25.4   # 185 mm panel width

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 13,
    "axes.labelsize": 14,
    "axes.titlesize": 15,
    "xtick.labelsize": 12.5,
    "ytick.labelsize": 12.5,
    "legend.fontsize": 12.5,
    "axes.edgecolor": MUTED,
    "axes.linewidth": 0.8,
    "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.labelcolor": INK, "text.color": INK,
    "grid.color": "#e4e3df", "grid.linewidth": 0.7,
    "pdf.fonttype": 42,
})


def fig_resolution(res: Path, out: Path) -> None:
    """Figure 2 - the dissociation: text looks clean while values corrupt.

    Both series are error FRACTIONS on one 0-1 axis. Never a dual axis.
    """
    s = pd.read_csv(res / "summary.csv")
    r = s[s.family.isin(["baseline", "resolution"])].sort_values("dpi")
    dpi = r.dpi.to_numpy()
    cer = r.cer_mean.to_numpy()
    verr = 1.0 - r.value_acc_mean.to_numpy()

    fig, ax = plt.subplots(figsize=(PANEL_IN, PANEL_IN * 0.60))
    ax.set_axisbelow(True)
    ax.yaxis.grid(True)

    ax.plot(dpi, verr, "-o", color=RED, lw=2.0, ms=9,
            mec=SURFACE, mew=1.6, label="Laboratory values read incorrectly",
            zorder=3, clip_on=False)
    ax.plot(dpi, cer, "-o", color=BLUE, lw=2.0, ms=9,
            mec=SURFACE, mew=1.6, label="Characters read incorrectly (OCR text)",
            zorder=3, clip_on=False)

    ax.invert_xaxis()                      # degradation increases rightwards
    ax.set_xscale("log")
    ax.set_xticks(dpi)
    ax.set_xticklabels([str(int(d)) for d in dpi])
    ax.minorticks_off()
    ax.set_xlabel("Scan resolution (dpi)  —  degradation increases →")
    ax.set_ylabel("Error rate")
    ax.set_ylim(-0.03, 0.88)
    ax.set_yticks([0, .1, .2, .3, .4, .5, .6, .7, .8])
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.spines["left"].set_bounds(0, 0.8)

    # ONE selective callout carrying both numbers: two separate callouts
    # collide here, and the contrast is the whole point of the figure.
    i150 = list(dpi).index(150)
    ax.annotate(f"At {int(dpi[i150])} dpi: {verr[i150]:.0%} of values are wrong\n"
                f"— but only {cer[i150]:.1%} of characters are",
                xy=(dpi[i150], verr[i150]), xytext=(-8, 40),
                textcoords="offset points", ha="center", va="bottom",
                color=INK, fontsize=12.5, fontweight="bold", linespacing=1.45,
                arrowprops=dict(arrowstyle="-", color=RED, lw=1.2, shrinkB=7))

    ax.legend(loc="upper left", frameon=False, handlelength=1.8)
    ax.set_title("OCR text quality does not predict value-level safety",
                 loc="left", pad=12, fontweight="bold", fontsize=14)
    fig.tight_layout()
    fig.savefig(out / "fig2_resolution.pdf", bbox_inches="tight")
    fig.savefig(out / "fig2_resolution.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_factors(res: Path, out: Path) -> None:
    """Figure 2b - small multiples. One series per panel, so no legend needed."""
    s = pd.read_csv(res / "summary.csv")
    fams = [("blur", "Blur (\u03c3, px)"),
            ("jpeg", "JPEG quality \u2193"),
            ("rotation", "Rotation (\u00b0)"),
            ("noise", "Noise (\u03c3)")]
    fig, axes = plt.subplots(1, 4, figsize=(PANEL_IN, PANEL_IN * 0.36),
                             sharey=True)
    for ax, (fam, lab) in zip(axes, fams):
        f = s[s.family == fam].sort_values("level")
        x = f.level.to_numpy()
        y = 1.0 - f.value_acc_mean.to_numpy()
        if fam == "jpeg":
            ax.invert_xaxis()
        ax.set_axisbelow(True)
        ax.yaxis.grid(True)
        ax.plot(x, y, "-o", color=RED, lw=2.0, ms=7, mec=SURFACE, mew=1.4,
                clip_on=False, zorder=3)
        ax.set_xlabel(lab, fontsize=11.5)
        ax.tick_params(labelsize=11)
        ax.set_ylim(-0.02, 1.02)
    axes[0].set_ylabel("Values wrong", fontsize=12)
    axes[0].yaxis.set_major_formatter(PercentFormatter(1.0))
    fig.suptitle("All four held at 300 dpi: each is harmless until a cliff",
                 x=0.005, ha="left", fontsize=12.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.84), w_pad=1.8)
    fig.savefig(out / "fig2b_factors.pdf", bbox_inches="tight")
    fig.savefig(out / "fig2b_factors.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_taxonomy(res: Path, out: Path) -> None:
    """Figure 3 - what the flagging layer does with a corrupted value.

    Segment labels are carried by a legend rather than centred under each
    segment: the three smaller segments are far too narrow for in-place text.
    """
    from matplotlib.patches import Patch

    c = pd.read_csv(res / "corruptions_classified.csv")
    order = ["Silent (flag unchanged)",
             "False alarm (normal -> flagged)",
             "Flag changed (wrong direction/severity)",
             "Missed alarm (abnormal -> normal)"]
    short = ["Flag unchanged — invisible",
             "Normal read as abnormal",
             "Flag inverted: low \u2192 high",
             "Abnormal read as normal"]
    n = len(c)
    counts = [int((c.klass == k).sum()) for k in order]
    # one hue, stepped by how well the error is concealed - sequential, not categorical
    shades = ["#b3251f", "#d4584e", "#e8938c", "#f3c4bf"]

    fig, ax = plt.subplots(figsize=(PANEL_IN, PANEL_IN * 0.40))
    left = 0.0
    for v, sh in zip(counts, shades):
        ax.barh(0, v, left=left, height=0.52, color=sh,
                edgecolor=SURFACE, linewidth=2)   # 2px surface gap between fills
        if v / n > 0.09:
            ax.text(left + v / 2, 0, str(v), ha="center", va="center",
                    color="white" if sh in shades[:2] else INK,
                    fontsize=16, fontweight="bold")
        left += v
    ax.set_xlim(0, n)
    ax.set_ylim(-0.42, 0.42)
    ax.axis("off")

    handles = [Patch(facecolor=sh, edgecolor=SURFACE,
                     label=f"{lbl}  ({v})")
               for sh, lbl, v in zip(shades, short, counts)]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.06),
              ncol=2, frameon=False, fontsize=11.5, handlelength=1.1,
              handleheight=1.1, columnspacing=1.6, labelspacing=0.8,
              borderpad=0)
    ax.set_title(f"{counts[0]} of {n} corrupted values ({counts[0]/n:.0%}) kept the "
                 f"true value's flag —\nnothing in the pipeline signals the error",
                 loc="left", pad=12, fontweight="bold", fontsize=13,
                 linespacing=1.4)
    fig.tight_layout()
    fig.savefig(out / "fig3_taxonomy.pdf", bbox_inches="tight")
    fig.savefig(out / "fig3_taxonomy.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--outdir", default="figures")
    a = ap.parse_args()
    res, out = Path(a.results), Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    fig_resolution(res, out)
    fig_factors(res, out)
    fig_taxonomy(res, out)
    fig_architecture(out)
    print(f"wrote figures to {out}/")




# --------------------------------------------------------------------------
# Figure 1 - architecture. Appended as a separate entry point so the data
# figures and the diagram can be rebuilt independently.
# --------------------------------------------------------------------------
def fig_architecture(out: Path) -> None:
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

    W, H = PANEL_IN, PANEL_IN * 0.92
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    BOXW, BOXX = 46.0, 3.0
    NOTEX = 52.0
    stages = [
        ("Patient document\nPDF scan or phone photo", "#dbe7f7", "vision"),
        ("OCR\nTesseract 5.5", "#dbe7f7", "vision"),
        ("Raw text", "#f0f0ee", None),
        ("Structured extraction\n13 analytes → JSON", "#f0f0ee", None),
        ("Abnormal-value flagging\n17 hardcoded ranges", "#f0f0ee", None),
        ("Prompt assembly\n+ retrieved guideline passages", "#fae0dd", "lang"),
        ("Generated clinical\nrecommendation", "#fae0dd", "lang"),
    ]
    notes = [
        None,
        "15% of values misread at 150 dpi,\nwhile 98.3% of characters are correct",
        "decimal points are the first casualty:\n'12.0 - 15.5' is read as '120-155'",
        None,
        "ranges are not age- or sex-aware;\n65% of misreads keep the true flag",
        "“Quote patient values EXACTLY\nas listed”  — core/prompts.py",
        None,
    ]
    n = len(stages)
    top, bot = 94.0, 5.0
    gap = (top - bot) / n
    bh = gap * 0.54

    centres = []
    for i, ((label, fc, kind), note) in enumerate(zip(stages, notes)):
        yc = top - gap * (i + 0.5)
        centres.append(yc)
        ax.add_patch(FancyBboxPatch(
            (BOXX, yc - bh / 2), BOXW, bh,
            boxstyle="round,pad=0,rounding_size=1.2",
            facecolor=fc, edgecolor="#9aa0a6", linewidth=0.9))
        ax.text(BOXX + BOXW / 2, yc, label, ha="center", va="center",
                fontsize=11.5, color=INK, linespacing=1.35)
        if note:
            ax.text(NOTEX + 1.5, yc, note, ha="left", va="center",
                    fontsize=10.5, color=INK2, linespacing=1.35)
            ax.plot([BOXX + BOXW + 0.8, NOTEX], [yc, yc],
                    color="#c8c8c4", lw=0.8, zorder=0)

    for i in range(n - 1):
        ax.add_patch(FancyArrowPatch(
            (BOXX + BOXW / 2, centres[i] - bh / 2),
            (BOXX + BOXW / 2, centres[i + 1] + bh / 2),
            arrowstyle="-|>", mutation_scale=13,
            color="#6f7479", lw=1.3, shrinkA=0, shrinkB=0))

    # the gap: between flagging and prompt assembly, nothing checks plausibility
    ygap = (centres[4] - bh / 2 + centres[5] + bh / 2) / 2
    ax.add_patch(Rectangle((BOXX + 0.5, ygap - 1.8), BOXW - 1.0, 3.6,
                           facecolor="#fff2f1", edgecolor=RED,
                           linewidth=1.3, linestyle=(0, (4, 2.4)), zorder=4))
    ax.text(BOXX + BOXW / 2, ygap,
            "no physiological plausibility check",
            ha="center", va="center", fontsize=9.2, color=RED,
            fontweight="bold", zorder=5)

    ax.text(1.0, 99.0, "Potassium 5.8 enters here. "
            "58.0 leaves there, labelled “High” either way.",
            ha="left", va="top", fontsize=12, fontweight="bold", color=INK)
    ax.text(BOXX - 0.4, centres[0] + bh / 2 + 1.4, "VISION", fontsize=9.5,
            color="#2a78d6", fontweight="bold", ha="left")
    ax.text(BOXX - 0.4, centres[6] - bh / 2 - 2.2, "LANGUAGE", fontsize=9.5,
            color=RED, fontweight="bold", ha="left", va="top")

    fig.tight_layout(pad=0.2)
    fig.savefig(out / "fig1_architecture.pdf", bbox_inches="tight")
    fig.savefig(out / "fig1_architecture.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
