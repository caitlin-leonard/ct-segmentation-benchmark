"""
SCRIPT 4 - EVALUATE ALL 3 TOOLS ON 50 SUBJECTS, ALL COMMON ORGANS
=====================================================================
CHANGED: VoxTell is now read from per-organ binary files
("ct_{organ}.nii.gz") instead of a combined multilabel volume — see
ts_run_voxtell.py for why. This removes a real confound: label-combining
could corrupt organ boundaries in ways unrelated to VoxTell's actual
per-organ segmentation accuracy.

Still idempotent, still per-tool/per-subject resumable, still strictly
scoped to the current 50-subject sample (see prior versions' bug notes
for TotalSeg/MOOSE — those are unaffected by this change and don't need
re-running).
"""

import os
import sys
import glob
import json
import time
import numpy as np
import nibabel as nib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ts_subject_sample import get_subjects

# ─────────────────────────────────────────────
# PATHS  ← change here if needed
# ─────────────────────────────────────────────
DATASET_DIR    = r"E:\Totalsegmentator_dataset\Totalsegmentator_dataset"
TOTALSEG_DIR   = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\totalseg"
MOOSE_DIR      = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\moose_input"
VOXTELL_DIR    = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\voxtell"
RESULTS_FILE   = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\all_results.json"
CONFIG_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ts_organ_config.json")

os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)

if not os.path.exists(CONFIG_FILE):
    print(f"ERROR: {CONFIG_FILE} not found. Run ts_discover_organs.py first.")
    sys.exit(1)

with open(CONFIG_FILE, "r") as f:
    ORGANS = json.load(f)   # {organ_name: {gt, totalseg, moose, voxtell, voxtell_prompt}}

TOOLS = ["TotalSegmentator", "MOOSE", "VoxTell"]

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────
def dice_score(pred, gt):
    pred = pred.astype(bool)
    gt   = gt.astype(bool)
    if pred.sum() == 0 and gt.sum() == 0: return 1.0
    if pred.sum() == 0 or  gt.sum() == 0: return 0.0
    return 2.0 * (pred & gt).sum() / (pred.sum() + gt.sum())

def iou_score(pred, gt):
    pred = pred.astype(bool)
    gt   = gt.astype(bool)
    if pred.sum() == 0 and gt.sum() == 0: return 1.0
    if pred.sum() == 0 or  gt.sum() == 0: return 0.0
    return (pred & gt).sum() / (pred | gt).sum()

def load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    for tool in TOOLS:
        data.setdefault(tool, {})
        for organ in ORGANS:
            data[tool].setdefault(organ, {})
    return data

def save_results(results):
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

def prune_to_current_sample(results, valid_subjects):
    n_dropped = 0
    for tool in TOOLS:
        for organ in ORGANS:
            stale = [s for s in results[tool][organ] if s not in valid_subjects]
            for s in stale:
                del results[tool][organ][s]
                n_dropped += 1
    if n_dropped:
        print(f"Pruned {n_dropped} stale score(s) from subjects outside the current sample.\n")
    return results

# ─────────────────────────────────────────────
# GET SAMPLED SUBJECTS
# ─────────────────────────────────────────────
subjects = get_subjects(DATASET_DIR)
valid_subjects = set(subjects)

results = load_results()
results = prune_to_current_sample(results, valid_subjects)

print("=" * 65)
print(f"EVALUATING ALL 3 TOOLS ON {len(subjects)} SUBJECTS, {len(ORGANS)} ORGANS")
print("VoxTell now scored from per-organ binary files (not combined volume)")
print("=" * 65 + "\n")

run_start = time.time()

for idx, subject_id in enumerate(subjects):
    seg_dir = os.path.join(DATASET_DIR, subject_id, "segmentations")
    if not os.path.isdir(seg_dir):
        print(f"[{idx+1}/{len(subjects)}] {subject_id}: no segmentations folder, skipping.")
        continue

    any_new_work = False
    line_status = []

    # ── TotalSegmentator ── (unchanged)
    ts_path = os.path.join(TOTALSEG_DIR, f"{subject_id}.nii.gz")
    if os.path.exists(ts_path):
        needs_work = any(subject_id not in results["TotalSegmentator"][organ] for organ in ORGANS)
        if needs_work:
            ts = nib.load(ts_path).get_fdata().astype(np.int32)
            for organ, cfg in ORGANS.items():
                if subject_id in results["TotalSegmentator"][organ]:
                    continue
                gt_path = os.path.join(seg_dir, f"{cfg['gt']}.nii.gz")
                if not os.path.exists(gt_path):
                    continue
                gt   = (nib.load(gt_path).get_fdata() > 0).astype(np.int32)
                pred = (ts == cfg["totalseg"])
                results["TotalSegmentator"][organ][subject_id] = {
                    "dice": dice_score(pred, gt), "iou": iou_score(pred, gt)
                }
            any_new_work = True
        line_status.append("TotalSeg:OK")
    else:
        line_status.append("TotalSeg:missing")

    # ── MOOSE ── (unchanged)
    moose_files = glob.glob(os.path.join(MOOSE_DIR, subject_id, "moosez-*", "segmentations", "*.nii.gz"))
    if moose_files:
        needs_work = any(subject_id not in results["MOOSE"][organ] for organ in ORGANS)
        if needs_work:
            ms = nib.load(moose_files[0]).get_fdata().astype(np.int32)
            for organ, cfg in ORGANS.items():
                if subject_id in results["MOOSE"][organ]:
                    continue
                gt_path = os.path.join(seg_dir, f"{cfg['gt']}.nii.gz")
                if not os.path.exists(gt_path):
                    continue
                gt   = (nib.load(gt_path).get_fdata() > 0).astype(np.int32)
                pred = (ms == cfg["moose"])
                results["MOOSE"][organ][subject_id] = {
                    "dice": dice_score(pred, gt), "iou": iou_score(pred, gt)
                }
            any_new_work = True
        line_status.append("MOOSE:OK")
    else:
        line_status.append("MOOSE:missing")

    # ── VoxTell ── (CHANGED: per-organ binary files instead of combined volume)
    needs_work = any(subject_id not in results["VoxTell"][organ] for organ in ORGANS)
    voxtell_any_found = False
    if needs_work:
        for organ, cfg in ORGANS.items():
            if subject_id in results["VoxTell"][organ]:
                continue
            vt_path = os.path.join(VOXTELL_DIR, subject_id, f"ct_{organ}.nii.gz")
            if not os.path.exists(vt_path):
                continue
            gt_path = os.path.join(seg_dir, f"{cfg['gt']}.nii.gz")
            if not os.path.exists(gt_path):
                continue
            voxtell_any_found = True
            vt = (nib.load(vt_path).get_fdata() > 0).astype(np.int32)
            gt = (nib.load(gt_path).get_fdata() > 0).astype(np.int32)
            results["VoxTell"][organ][subject_id] = {
                "dice": dice_score(vt, gt), "iou": iou_score(vt, gt)
            }
        any_new_work = any_new_work or voxtell_any_found
        line_status.append("VoxTell:OK" if voxtell_any_found else "VoxTell:missing (not run yet)")
    else:
        line_status.append("VoxTell:OK (cached)")

    print(f"[{idx+1}/{len(subjects)}] {subject_id}: {' | '.join(line_status)}")

    if any_new_work:
        save_results(results)

print(f"\nDone in {(time.time()-run_start)/60:.1f} min.")
print(f"Results saved to: {RESULTS_FILE}")
print("\nNow run ts_results_table.py to see the final comparison table!")