"""
SCRIPT 2 - RUN MOOSE ON 50 RANDOMLY SAMPLED TOTALSEG SUBJECTS
=================================================================
Dataset structure:
  E:\Totalsegmentator_dataset\Totalsegmentator_dataset\
    s0000\ct.nii.gz
    s0001\ct.nii.gz ...

MOOSE needs a folder per subject with the CT file named CT_*.nii.gz
This script sets that structure up and runs moosez.

Uses ts_subject_sample.py so this is the SAME 50 subjects as
ts_run_totalseg.py and ts_run_voxtell.py.
"""

import os
import sys
import time
import shutil
import subprocess
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ts_subject_sample import get_subjects

# ─────────────────────────────────────────────
# PATHS  ← change here if needed
# ─────────────────────────────────────────────
DATASET_DIR     = r"E:\Totalsegmentator_dataset\Totalsegmentator_dataset"
MOOSE_INPUT_DIR = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\moose_input"
LOG_FILE        = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\moose_run_log.txt"

os.makedirs(MOOSE_INPUT_DIR, exist_ok=True)

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")

subjects = get_subjects(DATASET_DIR)

log(f"\n{'='*50}\nRUN STARTED: {time.strftime('%Y-%m-%d %H:%M:%S')}")
log(f"Setting up MOOSE folder structure for {len(subjects)} randomly sampled subjects (seed=42)...")

# ─────────────────────────────────────────────
# SET UP FOLDER STRUCTURE FOR MOOSE
# MOOSE needs: <moose_input>/<subject_id>/CT_<subject_id>.nii.gz
# ─────────────────────────────────────────────
copy_failures = []
for subject_id in subjects:
    src_path    = os.path.join(DATASET_DIR, subject_id, "ct.nii.gz")
    subject_dir = os.path.join(MOOSE_INPUT_DIR, subject_id)
    os.makedirs(subject_dir, exist_ok=True)

    dest_path = os.path.join(subject_dir, f"CT_{subject_id}.nii.gz")

    if not os.path.exists(src_path):
        copy_failures.append(subject_id)
        continue
    if not os.path.exists(dest_path):
        try:
            shutil.copy2(src_path, dest_path)
            log(f"  Copied: {subject_id}")
        except Exception as e:
            copy_failures.append(subject_id)
            log(f"  Copy failed for {subject_id}: {e}")
    else:
        log(f"  Already exists: {subject_id}")

log(f"Folder structure ready at: {MOOSE_INPUT_DIR}")
if copy_failures:
    log(f"  {len(copy_failures)} subject(s) missing/failed to copy: {copy_failures}")

# ─────────────────────────────────────────────
# RUN MOOSE ON ALL SAMPLED SUBJECTS AT ONCE
# (moosez processes every subject folder in MOOSE_INPUT_DIR; since only
#  the 50 sampled subjects' folders exist there, it naturally scopes to them.
#  It also skips subjects that already have a moosez-*/segmentations/ output,
#  so re-running this script after an interruption is safe.)
# ─────────────────────────────────────────────
log("\n" + "="*50)
log("STARTING MOOSE")
log("="*50 + "\n")

run_start = time.time()
try:
    cmd = ["moosez", "-d", MOOSE_INPUT_DIR, "-m", "clin_ct_organs"]
    log(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    success = (result.returncode == 0)
except Exception as e:
    log(f"MOOSE run raised an exception: {e}")
    success = False

elapsed_min = (time.time() - run_start) / 60

if success:
    log(f"\n{'='*50}")
    log("MOOSE COMPLETE!")
    log(f"Total time: {elapsed_min:.1f} min")
    log(f"Outputs are inside each subject folder in: {MOOSE_INPUT_DIR}")
    log("="*50)
else:
    n_done = len(glob.glob(os.path.join(MOOSE_INPUT_DIR, "*", "moosez-*", "segmentations")))
    log(f"\nMOOSE encountered an error after {elapsed_min:.1f} min.")
    log(f"{n_done}/{len(subjects)} subjects appear to have completed segmentations already.")
    log("Just re-run this script — moosez will skip finished subjects and pick up where it left off.")
