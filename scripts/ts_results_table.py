"""
SCRIPT 5 - PRINT FINAL COMPARISON TABLE (50-subject sample, all common organs)
=================================================================================
Reads results from the FIXED ts_evaluate.py (dict-of-subject-scores format).
Organ list comes from ts_organ_config.json.

Flags any organ/tool combo where N is below the expected subject count —
that's your signal a tool hasn't finished running yet, NOT a real result
to draw conclusions from. Comparing tools with mismatched N is not valid.
"""

import os
import json
import numpy as np
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ts_subject_sample import get_subjects

DATASET_DIR  = r"E:\Totalsegmentator_dataset\Totalsegmentator_dataset"
RESULTS_FILE = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\all_results.json"
CONFIG_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ts_organ_config.json")

with open(RESULTS_FILE, "r") as f:
    results = json.load(f)

with open(CONFIG_FILE, "r") as f:
    organ_config = json.load(f)

ORGANS = sorted(organ_config.keys())
TOOLS  = ["TotalSegmentator", "MOOSE", "VoxTell"]

EXPECTED_N = len(get_subjects(DATASET_DIR))  # should be 50

print("\n")
print("=" * 65)
print("   SEGMENTATION ACCURACY: MOOSE vs TotalSegmentator vs VoxTell")
print(f"   Dataset: TotalSegmentator ({EXPECTED_N}-subject random sample)")
print(f"   Organs: {len(ORGANS)} (full intersection of all 3 tools)")
print("=" * 65)

incomplete_tools = set()

for tool in TOOLS:
    print(f"\n{tool}")
    print(f"{'Organ':<25} {'Dice':>8} {'Std':>8} {'IoU':>8} {'N':>4}")
    print("-" * 57)

    all_dice = []
    all_iou  = []

    for organ in ORGANS:
        organ_data = results.get(tool, {}).get(organ, {})  # {subject_id: {dice, iou}}
        n = len(organ_data)

        if n == 0:
            print(f"  {organ.replace('_',' ').title():<23} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'0':>4}")
            continue

        dice_scores = [v["dice"] for v in organ_data.values()]
        iou_scores  = [v["iou"]  for v in organ_data.values()]
        mean_dice   = np.mean(dice_scores)
        std_dice    = np.std(dice_scores)
        mean_iou    = np.mean(iou_scores)

        flag = "  ⚠ incomplete" if n < EXPECTED_N else ""
        if n < EXPECTED_N:
            incomplete_tools.add(tool)

        all_dice.extend(dice_scores)
        all_iou.extend(iou_scores)

        print(f"  {organ.replace('_',' ').title():<23} {mean_dice:>8.4f} {std_dice:>8.4f} {mean_iou:>8.4f} {n:>4}{flag}")

    if all_dice:
        print("-" * 57)
        print(f"  {'Mean':<23} {np.mean(all_dice):>8.4f} {np.std(all_dice):>8.4f} {np.mean(all_iou):>8.4f}")

print("\n" + "=" * 65)

if incomplete_tools:
    print(f"\n⚠ WARNING: {', '.join(sorted(incomplete_tools))} has fewer than {EXPECTED_N} subjects")
    print("for at least one organ. Comparing mean Dice across tools with different N")
    print("is NOT valid — the numbers below (and the 'winner' summary) should be")
    print("treated as PRELIMINARY until all three tools have completed all 50 subjects.")
    print("Re-run ts_evaluate.py after the missing tool run(s) finish.\n")

# ── WINNER SUMMARY ──
print("SUMMARY - Best tool per organ (by Dice):")
print("-" * 45)
for organ in ORGANS:
    best_tool = None
    best_dice = -1
    ns = {}
    for tool in TOOLS:
        organ_data = results.get(tool, {}).get(organ, {})
        ns[tool] = len(organ_data)
        if organ_data:
            mean_dice = np.mean([v["dice"] for v in organ_data.values()])
            if mean_dice > best_dice:
                best_dice = mean_dice
                best_tool = tool
    n_note = "" if len(set(ns.values())) == 1 else f"  (N mismatch: {ns})"
    print(f"  {organ.replace('_',' ').title():<23} → {best_tool} ({best_dice:.4f}){n_note}")

print("\nOverall best tool (mean Dice across all organs):")
tool_means = {}
for tool in TOOLS:
    all_dice = []
    for organ in ORGANS:
        organ_data = results.get(tool, {}).get(organ, {})
        all_dice.extend([v["dice"] for v in organ_data.values()])
    if all_dice:
        tool_means[tool] = np.mean(all_dice)
        print(f"  {tool:<22} {np.mean(all_dice):.4f}")

if tool_means and not incomplete_tools:
    best_overall = max(tool_means, key=tool_means.get)
    print(f"\n  ★ WINNER: {best_overall} ({tool_means[best_overall]:.4f} mean Dice)")
elif tool_means:
    print("\n  (Winner not declared — results are incomplete, see warning above.)")

print("=" * 65)