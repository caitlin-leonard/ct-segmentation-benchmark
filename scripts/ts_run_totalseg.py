"""
SCRIPT 1 - RUN TOTALSEGMENTATOR ON 50 RANDOMLY SAMPLED TOTALSEG SUBJECTS
==========================================================================
Dataset structure:
  E:\Totalsegmentator_dataset\Totalsegmentator_dataset\
    s0000\
      ct.nii.gz          <- input CT
      segmentations\     <- ground truth (per-organ binary files)
    s0001\ ...

Output: one multilabel .nii.gz per subject in results\totalseg\

Uses ts_subject_sample.py so the same 50 subjects are used across
ts_run_totalseg.py, ts_run_moose.py, and ts_run_voxtell.py.
Re-running this script is safe — already-done subjects are skipped.
"""

import os
import sys
import time
import traceback
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ts_subject_sample import get_subjects

# ─────────────────────────────────────────────
# PATHS  ← change here if needed
# ─────────────────────────────────────────────
DATASET_DIR = r"E:\Totalsegmentator_dataset\Totalsegmentator_dataset"
OUTPUT_DIR  = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\totalseg"
LOG_FILE    = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\totalseg_run_log.txt"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

subjects = get_subjects(DATASET_DIR)

log(f"\n{'='*50}\nRUN STARTED: {time.strftime('%Y-%m-%d %H:%M:%S')}")
log(f"Running TotalSegmentator on {len(subjects)} randomly sampled subjects (seed=42).")
log("="*50 + "\n")

failures = []
run_start = time.time()
n_processed = 0

for i, subject_id in enumerate(subjects):
    image_path  = os.path.join(DATASET_DIR, subject_id, "ct.nii.gz")
    output_path = os.path.join(OUTPUT_DIR, f"{subject_id}.nii.gz")

    if not os.path.exists(image_path):
        log(f"[{i+1}/{len(subjects)}] {subject_id}: CT not found, skipping.")
        continue

    if os.path.exists(output_path):
        log(f"[{i+1}/{len(subjects)}] {subject_id}: already done, skipping.")
        continue

    subj_start = time.time()
    try:
        cmd = [
            "TotalSegmentator",
            "-i", image_path,
            "-o", output_path,
            "-ml",        # single multilabel output file
            "-d", "gpu",
            "-f",         # fast mode (3mm)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

        if result.returncode == 0:
            n_processed += 1
            elapsed = time.time() - subj_start
            avg = (time.time() - run_start) / n_processed
            remaining = len(subjects) - i - 1
            eta_min = (avg * remaining) / 60
            log(f"[{i+1}/{len(subjects)}] {subject_id}: OK ({elapsed:.0f}s) | ETA ~{eta_min:.0f} min remaining")
        else:
            failures.append(subject_id)
            log(f"[{i+1}/{len(subjects)}] {subject_id}: ERROR — {result.stderr[-300:]}")

    except subprocess.TimeoutExpired:
        failures.append(subject_id)
        log(f"[{i+1}/{len(subjects)}] {subject_id}: TIMEOUT (>30 min), skipping.")
    except Exception as e:
        failures.append(subject_id)
        log(f"[{i+1}/{len(subjects)}] {subject_id}: EXCEPTION — {e}")
        log(traceback.format_exc()[-500:])

log(f"\n{'='*50}")
log("TOTALSEGMENTATOR COMPLETE")
log(f"Total time: {(time.time()-run_start)/60:.1f} min")
log(f"Results saved in: {OUTPUT_DIR}")
if failures:
    log(f"\n{len(failures)} subject(s) FAILED: {failures}")
    log("Re-run this script to retry them (already-done subjects are skipped automatically).")
log("="*50)
