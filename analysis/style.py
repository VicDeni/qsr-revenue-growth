"""Shared chart style: one validated categorical palette, recessive chrome, thin marks.

Channel colours are fixed per channel (never re-assigned by rank) so every figure agrees.
Palette checked with a colour-vision-deficiency validator; yellow/aqua sit below 3:1
contrast on white, so charts that use them carry direct labels.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
NEUTRAL = "#c3c2b7"   # de-emphasised marks

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
CHANNEL_COLORS = {"Mobile App": BLUE, "Drive-Thru": ORANGE, "In-Store Cashier": AQUA, "Kiosk": YELLOW}
CHANNEL_ORDER = ["Mobile App", "Drive-Thru", "In-Store Cashier", "Kiosk"]
SEQ_BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

FIG_DIR = Path(__file__).resolve().parent / "figures"


def apply() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": BASELINE, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 22,
        "axes.axisbelow": True, "text.parse_math": False,
        "axes.titlecolor": INK, "legend.frameon": False, "lines.linewidth": 2,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
    })


def subtitle(ax, text: str) -> None:
    """Secondary line under the title, in secondary ink."""
    ax.annotate(text, xy=(0, 1), xycoords="axes fraction", xytext=(0, 5), textcoords="offset points",
                fontsize=9.5, color=INK_2, va="bottom", ha="left")


def source(fig, text: str) -> None:
    fig.text(0.01, -0.02, text, fontsize=8, color=MUTED, ha="left", va="top")


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path)  # the notebook's inline backend still displays the figure
    return path
