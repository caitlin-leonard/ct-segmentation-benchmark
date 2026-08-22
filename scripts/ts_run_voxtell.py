"""
SCRIPT 3 - RUN VOXTELL ON 50 SUBJECTS, PER-ORGAN BINARY OUTPUT
==================================================================
CHANGED: no longer uses --save-combined. Instead, VoxTell writes one
binary .nii.gz file PER ORGAN, named "ct_{organ_name}.nii.gz" (confirmed
by test run — e.g. prompt "right kidney" -> "ct_right_kidney.nii.gz").

WHY THIS CHANGED: --save-combined merges all per-organ predictions into
a single multilabel volume. At voxel-level overlaps between adjacent
organs (e.g. adrenal gland vs. kidney, adjacent lung lobes), the
combining step can only assign one label per voxel — silently
corrupting boundary regions in a way that has nothing to do with
VoxTell's actual per-organ segmentation quality. Perfint's own official
report explicitly avoided --save-combined for this reason. This version
matches that methodology.

Resumability: a subject is considered done only when ALL expected
per-organ files exist for it.
"""

import os
import sys
import time
import json
import traceback
import subprocess
from huggingface_hub import snapshot_download

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ts_subject_sample import get_subjects

# ─────────────────────────────────────────────
# PATHS  ← change here if needed
# ─────────────────────────────────────────────
DATASET_DIR  = r"E:\Totalsegmentator_dataset\Totalsegmentator_dataset"
OUTPUT_DIR   = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\voxtell"
MODEL_DIR    = r"D:\voxtell_model"
LOG_FILE     = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\voxtell_run_log.txt"
CONFIG_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ts_organ_config.json")

# Subjects to skip entirely (e.g. s0224 has hung/timed out repeatedly across
# multiple runs — likely a genuinely problematic input, not transient flakiness).
# Add subject IDs here as strings to skip them without waiting out the timeout.
SKIP_SUBJECTS = {"s0224"}

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

# ─────────────────────────────────────────────
# LOAD ORGAN CONFIG (built by ts_discover_organs.py)
# ─────────────────────────────────────────────
if not os.path.exists(CONFIG_FILE):
    print(f"ERROR: {CONFIG_FILE} not found. Run ts_discover_organs.py first.")
    sys.exit(1)

with open(CONFIG_FILE, "r") as f:
    organ_config = json.load(f)

organs_sorted = sorted(organ_config.items(), key=lambda kv: kv[1]["voxtell"])
ORGAN_KEYS = [name for name, _ in organs_sorted]                    # e.g. "kidney_right"
PROMPTS    = [cfg["voxtell_prompt"] for _, cfg in organs_sorted]     # e.g. "kidney right"

# ─────────────────────────────────────────────
# STEP 1 - DOWNLOAD VOXTELL MODEL (only once)
# ─────────────────────────────────────────────
model_path = os.path.join(MODEL_DIR, "voxtell_v1.1")

if not os.path.exists(model_path):
    log("Downloading VoxTell model from HuggingFace (~2-3 GB)...")
    snapshot_download(
        repo_id="mrokuss/VoxTell",
        allow_patterns=["voxtell_v1.1/*", "*.json"],
        local_dir=MODEL_DIR
    )
    log(f"Model downloaded to: {model_path}\n")
else:
    log(f"Model already exists at: {model_path}\n")

# ─────────────────────────────────────────────
# STEP 2 - GET SAMPLED SUBJECTS
# ─────────────────────────────────────────────
subjects = get_subjects(DATASET_DIR)

log(f"\n{'='*50}\nRUN STARTED: {time.strftime('%Y-%m-%d %H:%M:%S')}")
log(f"Running VoxTell on {len(subjects)} subjects, PER-ORGAN OUTPUT (no --save-combined)")
log(f"Organs ({len(PROMPTS)}): {PROMPTS}")
log("="*50 + "\n")

# ─────────────────────────────────────────────
# STEP 3 - RUN VOXTELL ON EACH SUBJECT
# ─────────────────────────────────────────────
failures = []
run_start = time.time()
n_processed = 0

for i, subject_id in enumerate(subjects):
    image_path     = os.path.join(DATASET_DIR, subject_id, "ct.nii.gz")
    subject_output = os.path.join(OUTPUT_DIR, subject_id)
    os.makedirs(subject_output, exist_ok=True)

    if subject_id in SKIP_SUBJECTS:
        log(f"[{i+1}/{len(subjects)}] {subject_id}: in SKIP_SUBJECTS, skipping permanently.")
        continue

    if not os.path.exists(image_path):
        log(f"[{i+1}/{len(subjects)}] {subject_id}: CT not found, skipping.")
        continue

    # a subject is "done" only if EVERY expected per-organ file exists
    expected_files = [os.path.join(subject_output, f"ct_{organ}.nii.gz") for organ in ORGAN_KEYS]
    if all(os.path.exists(p) for p in expected_files):
        log(f"[{i+1}/{len(subjects)}] {subject_id}: already done, skipping.")
        continue

    subj_start = time.time()
    try:
        cmd = [
            "voxtell-predict",
            "-i", image_path,
            "-o", subject_output,
            "-m", model_path,
            "-p"
        ] + PROMPTS + ["--device", "cuda"]   # NOTE: no --save-combined

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

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
        log(f"[{i+1}/{len(subjects)}] {subject_id}: TIMEOUT (>60 min), skipping.")
    except Exception as e:
        failures.append(subject_id)
        log(f"[{i+1}/{len(subjects)}] {subject_id}: EXCEPTION — {e}")
        log(traceback.format_exc()[-500:])

log(f"\n{'='*50}")
log("VOXTELL COMPLETE!")
log(f"Total time: {(time.time()-run_start)/60:.1f} min")
log(f"Results saved in: {OUTPUT_DIR}")
if failures:
    log(f"\n{len(failures)} subject(s) FAILED: {failures}")
    log("Re-run this script to retry them (already-done subjects are skipped automatically).")
log("="*50)