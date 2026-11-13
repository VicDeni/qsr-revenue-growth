"""Render tableau/reference_layout.png: the target layout for the Tableau Public dashboard,
drawn from the same exports/orders.csv extract Tableau will use. Run after `python -m pipeline run`."""
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import style as S  # noqa: E402

S.apply()
o = pd.read_csv(ROOT / "exports" / "orders.csv")
for c in ["Is App Order", "Is Rewards Member"]:
    o[c] = o[c].astype(str).str.lower().eq("true")

fig = plt.figure(figsize=(14, 10.6))
gs = fig.add_gridspec(3, 10, height_ratios=[2.1, 2.1, 2.0], hspace=0.62, wspace=1.4,
                      left=0.05, right=0.97, top=0.765, bottom=0.05)

# header + filter pills
ax = fig.add_axes([0.05, 0.925, 0.92, 0.065]); ax.axis("off")
ax.text(0, 0.75, "QSR Revenue Growth Command Center", fontsize=19, fontweight="bold", color=S.INK, transform=ax.transAxes)
ax.text(0, 0.05, "100,000 orders  |  500 stores  |  Jan 2024 - Dec 2025  |  source: BigQuery qsr_reporting.rpt_orders_tableau",
        fontsize=10, color=S.INK_2, transform=ax.transAxes)
for i, label in enumerate(["Order Month: All", "Region: All", "Age Group: All", "Store Type: All"]):
    x = 0.6 + i * 0.1
    ax.add_patch(FancyBboxPatch((x, 0.55), 0.092, 0.4, boxstyle="round,pad=0.01,rounding_size=0.02",
                                transform=ax.transAxes, facecolor="white", edgecolor=S.BASELINE, lw=0.8))
    ax.text(x + 0.046, 0.75, label + "  v", ha="center", va="center", fontsize=8.5, color=S.INK_2, transform=ax.transAxes)

# KPI tiles
rev, n = o.Revenue.sum(), len(o)
kpis = [("Revenue", f"${rev / 1e6:.2f}M"), ("Orders", f"{n:,}"), ("Avg Ticket", f"${rev / n:.2f}"),
        ("App % of Revenue", f"{o.loc[o['Is App Order'], 'Revenue'].sum() / rev:.1%}"),
        ("Avg Satisfaction", f"{o['Satisfaction Score'].mean():.2f} / 5")]
for i, (label, value) in enumerate(kpis):
    ax = fig.add_axes([0.05 + i * 0.186, 0.835, 0.17, 0.065]); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.0,rounding_size=0.06", transform=ax.transAxes,
                                facecolor="white", edgecolor="#e1e0d9", lw=0.8))
    ax.text(0.07, 0.68, label, fontsize=9.5, color=S.INK_2, transform=ax.transAxes)
    ax.text(0.07, 0.18, value, fontsize=20, fontweight="bold", color=S.INK, transform=ax.transAxes)

# 1. avg ticket by channel
ax = fig.add_subplot(gs[0, :5])
t = o.groupby("Order Channel").Revenue.mean().reindex(S.CHANNEL_ORDER[::-1])
ax.barh(t.index, t.values, color=[S.CHANNEL_COLORS[c] for c in t.index], height=0.55)
for i, v in enumerate(t.values):
    ax.text(v + 0.2, i, f"${v:.2f}", va="center", fontsize=9.5)
ax.set_xlim(0, 21); ax.grid(axis="y", visible=False); ax.set_title("Avg ticket by channel", fontsize=11.5)
S.subtitle(ax, "Click a channel to filter the dashboard")

# 2. channel mix by age group
ax = fig.add_subplot(gs[0, 5:])
mix = pd.crosstab(o["Age Group"], o["Order Channel"], normalize="index")[S.CHANNEL_ORDER].iloc[::-1] * 100
left = np.zeros(len(mix))
for ch in S.CHANNEL_ORDER:
    ax.barh(mix.index, mix[ch], left=left, color=S.CHANNEL_COLORS[ch], height=0.6, edgecolor=S.SURFACE, lw=1.5)
    for i, (lv, w) in enumerate(zip(left, mix[ch])):
        if w >= 9:
            ax.text(lv + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=8.5,
                    color=S.INK if ch == "Kiosk" else "white")
    left += mix[ch].values
ax.set_xlim(0, 100); ax.grid(False); ax.set_title("Channel mix by age group", fontsize=11.5)
S.subtitle(ax, "Blue = Mobile App, orange = Drive-Thru, aqua = In-Store, yellow = Kiosk")

# 3. rewards check
ax = fig.add_subplot(gs[1, :5])
rows = ["Grand Total"] + S.CHANNEL_ORDER
for i, r in enumerate(rows[::-1]):
    g = o if r == "Grand Total" else o[o["Order Channel"] == r]
    a = g.loc[~g["Is Rewards Member"], "Revenue"].mean(); b = g.loc[g["Is Rewards Member"], "Revenue"].mean()
    ax.scatter(a, i, s=55, color=S.ORANGE, zorder=2)
    ax.scatter(b, i, s=130, facecolor="none", edgecolor=S.BLUE, lw=2, zorder=3)
    ax.text(max(a, b) + 0.35, i, f"{b - a:+.2f}", va="center", fontsize=9)
ax.set_yticks(range(len(rows)), rows[::-1]); ax.set_xlim(11.5, 20); ax.grid(axis="y", visible=False)
ax.set_title("Rewards vs non-member ticket", fontsize=11.5)
S.subtitle(ax, "Ring = rewards member, dot = non-member")

# 4. satisfaction vs wait
ax = fig.add_subplot(gs[1, 5:])
cur = o.groupby(["Order Channel", "Fulfillment Bucket (min)"])["Satisfaction Score"].agg(["mean", "size"]).reset_index()
cur = cur[cur["size"] >= 300]
for ch in S.CHANNEL_ORDER:
    c = cur[cur["Order Channel"] == ch]
    ax.plot(c["Fulfillment Bucket (min)"], c["mean"], color=S.CHANNEL_COLORS[ch], marker="o", ms=4)
    ax.text(c["Fulfillment Bucket (min)"].iloc[-1] + 0.2, c["mean"].iloc[-1], ch, fontsize=8.5, va="center")
ax.set_xlim(0.5, 11.5); ax.set_ylim(3.25, 4.0); ax.set_title("Satisfaction vs wait time", fontsize=11.5)
S.subtitle(ax, "Avg satisfaction by fulfillment minute (buckets with 300+ orders)")

# 5. heatmap
ax = fig.add_subplot(gs[2, :])
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
grid = pd.crosstab(o["Weekday"], o["Order Hour"]).reindex(index=days, columns=range(24), fill_value=0)
cmap = LinearSegmentedColormap.from_list("b", ["#f4f8fd"] + S.SEQ_BLUES)
ax.imshow(grid.values / grid.values.sum() * 100, aspect="auto", cmap=cmap)
ax.set_yticks(range(7), days); ax.set_xticks(range(24), [str(h) for h in range(24)], fontsize=8.5)
ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Orders by weekday and hour", fontsize=11.5)
S.subtitle(ax, "% of orders; darker = busier")

out = Path(__file__).resolve().parent / "reference_layout.png"
fig.savefig(out, dpi=110)
print("wrote", out)
