"""
SHARED HELPER - Consistent random subject sample across all scripts
======================================================================
Import this in every script (ts_run_totalseg.py, ts_run_moose.py,
ts_run_voxtell.py, ts_evaluate.py) so all three tools are evaluated
on the EXACT SAME 50 subjects. This matters for a fair comparison —
if each script picked its own random subset, Dice scores wouldn't be
directly comparable across tools.

Usage:
    from ts_subject_sample import get_subjects
    subjects = get_subjects(DATASET_DIR)
"""

import os
import random

N_SUBJECTS = 50     # bump to 100 later if pancreas Dice variance looks too noisy
SEED       = 42     # fixed seed = reproducible sample every time you re-run

def get_subjects(dataset_dir):
    all_subjects = sorted([
        d for d in os.listdir(dataset_dir)
        if os.path.isdir(os.path.join(dataset_dir, d)) and d.startswith("s")
    ])
    rng = random.Random(SEED)
    sample = rng.sample(all_subjects, min(N_SUBJECTS, len(all_subjects)))
    return sorted(sample)  # sorted for readable, deterministic ordering in logs/tables
