"""
SCRIPT 6 - GENERATE ALL STATISTICS AND GRAPHS
=================================================
Reads all_results.json (produced by ts_evaluate.py) and generates a full
set of publication-quality figures for your report/paper — saved as
high-res PNGs ready to drop into LaTeX or Word.

Requires: matplotlib, seaborn, numpy
Install if needed:
    pip install matplotlib seaborn --break-system-packages

Outputs (all saved to results/figures/):
    01_organ_bar_dice.png       - grouped bar chart, mean Dice per organ per tool
    02_organ_bar_iou.png        - same, for IoU
    03_heatmap_dice.png         - organ x tool heatmap
    04_overall_mean_bar.png     - overall mean Dice with error bars
    05_boxplot_distribution.png - per-tool Dice distribution (box plot)
    06_violin_distribution.png  - per-tool Dice distribution (violin plot)
    07_win_count.png            - how many organs each tool "wins"
    08_std_comparison.png       - std dev per organ per tool (consistency)
    09_scatter_dice_vs_std.png  - mean Dice vs std dev per organ/tool
    10_radar_chart.png          - radar/spider chart across organs
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # no display needed, just save files

try:
    import seaborn as sns
    sns.set_theme(style="whitegrid", font_scale=1.05)
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

# ─────────────────────────────────────────────
# PATHS  ← change here if needed
# ─────────────────────────────────────────────
RESULTS_FILE = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\all_results.json"
CONFIG_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ts_organ_config.json")
FIGURES_DIR  = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\figures"

os.makedirs(FIGURES_DIR, exist_ok=True)

with open(RESULTS_FILE, "r") as f:
    results = json.load(f)

with open(CONFIG_FILE, "r") as f:
    organ_config = json.load(f)

ORGANS = sorted(organ_config.keys())
TOOLS  = ["TotalSegmentator", "MOOSE", "VoxTell"]
COLORS = {"TotalSegmentator": "#2a78d6", "MOOSE": "#1baf7a", "VoxTell": "#eda100"}
ORGAN_LABELS = [o.replace("_", " ").title() for o in ORGANS]

def get_scores(tool, organ, metric="dice"):
    """Returns list of per-subject scores for a given tool/organ."""
    data = results.get(tool, {}).get(organ, {})
    return [v[metric] for v in data.values()]

def savefig(fig, name):
    path = os.path.join(FIGURES_DIR, name)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")

# ═══════════════════════════════════════════════════════════
# Pre-compute summary stats
# ═══════════════════════════════════════════════════════════
mean_dice = {t: [np.mean(get_scores(t, o, "dice")) if get_scores(t, o, "dice") else np.nan for o in ORGANS] for t in TOOLS}
std_dice  = {t: [np.std(get_scores(t, o, "dice"))  if get_scores(t, o, "dice") else np.nan for o in ORGANS] for t in TOOLS}
mean_iou  = {t: [np.mean(get_scores(t, o, "iou"))  if get_scores(t, o, "iou")  else np.nan for o in ORGANS] for t in TOOLS}

overall_dice_all = {t: [d for o in ORGANS for d in get_scores(t, o, "dice")] for t in TOOLS}

# ═══════════════════════════════════════════════════════════
# 1. Grouped bar chart — mean Dice per organ per tool
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 8))
y = np.arange(len(ORGANS))
h = 0.25
for i, tool in enumerate(TOOLS):
    ax.barh(y + (i - 1) * h, mean_dice[tool], height=h, label=tool, color=COLORS[tool])
ax.set_yticks(y)
ax.set_yticklabels(ORGAN_LABELS)
ax.set_xlabel("Mean Dice Similarity Coefficient")
ax.set_title("Mean Dice Score per Organ by Tool")
ax.set_xlim(0.75, 1.0)
ax.legend(loc="lower right")
ax.invert_yaxis()
savefig(fig, "01_organ_bar_dice.png")

# ═══════════════════════════════════════════════════════════
# 2. Grouped bar chart — mean IoU per organ per tool
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 8))
for i, tool in enumerate(TOOLS):
    ax.barh(y + (i - 1) * h, mean_iou[tool], height=h, label=tool, color=COLORS[tool])
ax.set_yticks(y)
ax.set_yticklabels(ORGAN_LABELS)
ax.set_xlabel("Mean IoU (Jaccard Index)")
ax.set_title("Mean IoU per Organ by Tool")
ax.set_xlim(0.6, 1.0)
ax.legend(loc="lower right")
ax.invert_yaxis()
savefig(fig, "02_organ_bar_iou.png")

# ═══════════════════════════════════════════════════════════
# 3. Heatmap — organ x tool Dice matrix
# ═══════════════════════════════════════════════════════════
matrix = np.array([mean_dice[t] for t in TOOLS]).T  # organs x tools
fig, ax = plt.subplots(figsize=(6, 9))
if HAS_SEABORN:
    sns.heatmap(matrix, annot=True, fmt=".3f", cmap="RdYlGn", vmin=0.75, vmax=1.0,
                xticklabels=TOOLS, yticklabels=ORGAN_LABELS, cbar_kws={"label": "Mean Dice"}, ax=ax)
else:
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0.75, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(TOOLS))); ax.set_xticklabels(TOOLS)
    ax.set_yticks(range(len(ORGANS))); ax.set_yticklabels(ORGAN_LABELS)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i,j]:.3f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="Mean Dice")
ax.set_title("Dice Score Heatmap: Organ x Tool")
savefig(fig, "03_heatmap_dice.png")

# ═══════════════════════════════════════════════════════════
# 4. Overall mean Dice with error bars (std across all organ-subject scores)
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(6, 5))
means = [np.mean(overall_dice_all[t]) for t in TOOLS]
stds  = [np.std(overall_dice_all[t]) for t in TOOLS]
bars = ax.bar(TOOLS, means, yerr=stds, capsize=8, color=[COLORS[t] for t in TOOLS])
for bar, m in zip(bars, means):
    ax.text(bar.get_x() + bar.get_width()/2, m + 0.02, f"{m:.4f}", ha="center", fontweight="bold")
ax.set_ylabel("Mean Dice Similarity Coefficient")
ax.set_title("Overall Mean Dice Across All Organs (± SD)")
ax.set_ylim(0, 1.05)
savefig(fig, "04_overall_mean_bar.png")

# ═══════════════════════════════════════════════════════════
# 5. Box plot — per-tool Dice distribution (all organ-subject scores pooled)
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 6))
data_to_plot = [overall_dice_all[t] for t in TOOLS]
bp = ax.boxplot(data_to_plot, labels=TOOLS, patch_artist=True, showmeans=True)
for patch, tool in zip(bp["boxes"], TOOLS):
    patch.set_facecolor(COLORS[tool])
    patch.set_alpha(0.7)
ax.set_ylabel("Dice Similarity Coefficient")
ax.set_title("Dice Score Distribution by Tool (All Organs Pooled)")
savefig(fig, "05_boxplot_distribution.png")

# ═══════════════════════════════════════════════════════════
# 6. Violin plot — same data, different view
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 6))
if HAS_SEABORN:
    import pandas as pd
    rows = [(t, d) for t in TOOLS for d in overall_dice_all[t]]
    df = pd.DataFrame(rows, columns=["Tool", "Dice"])
    sns.violinplot(data=df, x="Tool", y="Dice", palette=COLORS, ax=ax)
else:
    parts = ax.violinplot(data_to_plot, showmeans=True)
    ax.set_xticks(range(1, len(TOOLS) + 1))
    ax.set_xticklabels(TOOLS)
ax.set_ylabel("Dice Similarity Coefficient")
ax.set_title("Dice Score Distribution by Tool (Violin Plot)")
savefig(fig, "06_violin_distribution.png")

# ═══════════════════════════════════════════════════════════
# 7. Win count — how many organs each tool wins (by mean Dice)
# ═══════════════════════════════════════════════════════════
win_counts = {t: 0 for t in TOOLS}
for oi, organ in enumerate(ORGANS):
    scores = {t: mean_dice[t][oi] for t in TOOLS if not np.isnan(mean_dice[t][oi])}
    if scores:
        winner = max(scores, key=scores.get)
        win_counts[winner] += 1

fig, ax = plt.subplots(figsize=(6, 5))
bars = ax.bar(win_counts.keys(), win_counts.values(), color=[COLORS[t] for t in win_counts])
for bar, v in zip(bars, win_counts.values()):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.1, str(v), ha="center", fontweight="bold")
ax.set_ylabel("Number of Organs Won (by mean Dice)")
ax.set_title(f"Per-Organ Win Count (out of {len(ORGANS)} organs)")
ax.set_ylim(0, len(ORGANS) + 1)
savefig(fig, "07_win_count.png")

# ═══════════════════════════════════════════════════════════
# 8. Std dev comparison — consistency per organ per tool
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 8))
for i, tool in enumerate(TOOLS):
    ax.barh(y + (i - 1) * h, std_dice[tool], height=h, label=tool, color=COLORS[tool])
ax.set_yticks(y)
ax.set_yticklabels(ORGAN_LABELS)
ax.set_xlabel("Std Dev of Dice Score (lower = more consistent)")
ax.set_title("Consistency per Organ by Tool (Std Dev)")
ax.legend(loc="lower right")
ax.invert_yaxis()
savefig(fig, "08_std_comparison.png")

# ═══════════════════════════════════════════════════════════
# 9. Scatter — mean Dice vs std dev (accuracy vs consistency tradeoff)
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 6))
for tool in TOOLS:
    ax.scatter(std_dice[tool], mean_dice[tool], label=tool, color=COLORS[tool], s=70, alpha=0.8, edgecolors="white")
ax.set_xlabel("Std Dev (variability across subjects)")
ax.set_ylabel("Mean Dice")
ax.set_title("Accuracy vs. Consistency, per Organ")
ax.legend()
savefig(fig, "09_scatter_dice_vs_std.png")

# ═══════════════════════════════════════════════════════════
# 10. Radar / spider chart across organs
# ═══════════════════════════════════════════════════════════
angles = np.linspace(0, 2 * np.pi, len(ORGANS), endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(9, 9), subplot_kw={"projection": "polar"})
for tool in TOOLS:
    values = [v if not np.isnan(v) else 0 for v in mean_dice[tool]]
    values += values[:1]
    ax.plot(angles, values, label=tool, color=COLORS[tool], linewidth=2)
    ax.fill(angles, values, color=COLORS[tool], alpha=0.08)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(ORGAN_LABELS, fontsize=8)
ax.set_ylim(0.7, 1.0)
ax.set_title("Mean Dice Across All Organs (Radar View)", pad=30)
ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
savefig(fig, "10_radar_chart.png")

print(f"\nAll figures saved to: {FIGURES_DIR}")
print("Ready to drop into your LaTeX report or Word doc.")
