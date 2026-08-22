"""
SCRIPT 0 - DISCOVER THE TRUE COMMON-ORGAN INTERSECTION
==========================================================
Run this ONCE (after you've run ts_run_moose.py on at least one subject)
to build ts_organ_config.json — the authoritative organ list + label IDs
used by ts_run_voxtell.py, ts_evaluate.py, and ts_results_table.py.

Why this exists instead of a hardcoded 4-organ dict:
  - TotalSegmentator's label map is pulled directly from the installed
    `totalsegmentator` package (totalsegmentator.map_to_binary.class_map),
    so it's always correct for whatever version you have installed.
  - MOOSE's clin_ct_organs label map is NOT hardcoded anywhere reliable —
    moosez writes it out itself as organ_indices.json inside every
    segmentations/ output folder it creates. This script reads that file
    from your existing MOOSE run rather than guessing IDs.
  - Ground truth availability is checked against the actual GT files in
    the TotalSegmentator dataset's segmentations/ folder.
  - VoxTell has no fixed label set — it segments whatever you prompt it
    with — so it's included automatically once an organ passes the other
    two checks, with prompt order defining its label IDs.

Output: ts_organ_config.json — ALL organs common to TotalSegmentator,
MOOSE, and the ground truth (no fixed target count — uses whatever the
true intersection turns out to be). Review the printed report before
trusting it blindly, especially the "near misses" section, which flags
organs that exist in two tools but under slightly different names
(e.g. a naming convention mismatch) — worth a manual look so you don't
silently drop a real match.
"""

import os
import sys
import glob
import json

# ─────────────────────────────────────────────
# PATHS  ← change here if needed
# ─────────────────────────────────────────────
DATASET_DIR     = r"E:\Totalsegmentator_dataset\Totalsegmentator_dataset"
MOOSE_INPUT_DIR = r"C:\Users\admin\Documents\caitlin\segmodels_accuracy_ts\results\moose_input"
CONFIG_OUT      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ts_organ_config.json")

# ─────────────────────────────────────────────
# 1. TOTALSEGMENTATOR LABEL MAP (from installed package, authoritative)
# ─────────────────────────────────────────────
try:
    from totalsegmentator.map_to_binary import class_map
    ts_id_to_name = class_map["total"]              # {id: name}
    ts_name_to_id = {v: k for k, v in ts_id_to_name.items()}
    print(f"TotalSegmentator: {len(ts_name_to_id)} labels loaded from installed package.")
except Exception as e:
    print(f"ERROR: could not import totalsegmentator.map_to_binary — is it installed? ({e})")
    sys.exit(1)

# ─────────────────────────────────────────────
# 2. MOOSE LABEL MAP (from moosez's own auto-generated organ_indices.json)
# ─────────────────────────────────────────────
organ_indices_files = glob.glob(
    os.path.join(MOOSE_INPUT_DIR, "*", "moosez-*", "segmentations", "*organ_indices.json")
)
if not organ_indices_files:
    print("ERROR: no organ_indices.json found under MOOSE_INPUT_DIR.")
    print("Run ts_run_moose.py on at least one subject first, then re-run this script.")
    sys.exit(1)

with open(organ_indices_files[0], "r") as f:
    moose_raw = json.load(f)["organ_indices"]
# keys come back as strings from JSON — convert to int
moose_id_to_name = {int(k): v["name"] for k, v in moose_raw.items()}
moose_name_to_id = {v: k for k, v in moose_id_to_name.items()}
print(f"MOOSE clin_ct_organs: {len(moose_name_to_id)} labels loaded from {organ_indices_files[0]}")

# ─────────────────────────────────────────────
# 3. GROUND TRUTH ORGANS (from an actual subject's segmentations/ folder)
# ─────────────────────────────────────────────
all_subjects = sorted([
    d for d in os.listdir(DATASET_DIR)
    if os.path.isdir(os.path.join(DATASET_DIR, d)) and d.startswith("s")
])
gt_names = set()
for subject_id in all_subjects[:3]:  # check a few subjects in case one is missing files
    seg_dir = os.path.join(DATASET_DIR, subject_id, "segmentations")
    if os.path.isdir(seg_dir):
        for fname in os.listdir(seg_dir):
            if fname.endswith(".nii.gz"):
                gt_names.add(fname[:-len(".nii.gz")])
print(f"Ground truth: {len(gt_names)} organ files found (checked {min(3,len(all_subjects))} subjects).")

# ─────────────────────────────────────────────
# 4. COMPUTE INTERSECTION (exact name match first)
# ─────────────────────────────────────────────
ts_names    = set(ts_name_to_id.keys())
moose_names = set(moose_name_to_id.keys())

exact_common = ts_names & moose_names & gt_names

# ─────────────────────────────────────────────
# 5. FLAG NEAR-MISSES (same organ, different naming convention)
#    so nothing is silently dropped due to a naming mismatch
# ─────────────────────────────────────────────
def normalize(name):
    return name.lower().replace("-", "_").strip()

norm_ts    = {normalize(n): n for n in ts_names}
norm_moose = {normalize(n): n for n in moose_names}
norm_gt    = {normalize(n): n for n in gt_names}

near_misses = []
all_norm_keys = set(norm_ts) | set(norm_moose) | set(norm_gt)
for nk in sorted(all_norm_keys):
    in_ts, in_moose, in_gt = nk in norm_ts, nk in norm_moose, nk in norm_gt
    n_present = sum([in_ts, in_moose, in_gt])
    if n_present == 2 and nk not in {normalize(x) for x in exact_common}:
        near_misses.append((nk, in_ts, in_moose, in_gt))

# ─────────────────────────────────────────────
# 6. BUILD FINAL CONFIG
# ─────────────────────────────────────────────
final_organs = sorted(exact_common)
organ_config = {}
for i, organ in enumerate(final_organs, start=1):
    organ_config[organ] = {
        "gt": organ,
        "totalseg": ts_name_to_id[organ],
        "moose": moose_name_to_id[organ],
        "voxtell": i,
        "voxtell_prompt": organ.replace("_", " ")
    }

with open(CONFIG_OUT, "w") as f:
    json.dump(organ_config, f, indent=2)

# ─────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"COMMON ORGANS (present in TotalSeg + MOOSE + GT): {len(final_organs)}")
print("=" * 60)
for organ in final_organs:
    cfg = organ_config[organ]
    print(f"  {organ:<25} totalseg={cfg['totalseg']:<3} moose={cfg['moose']:<3} voxtell={cfg['voxtell']}")

if near_misses:
    print("\n" + "-" * 60)
    print(f"NEAR MISSES ({len(near_misses)}) — present in 2/3 sources under this name.")
    print("Check if these are the same organ under a different name in the third source:")
    print("-" * 60)
    for nk, in_ts, in_moose, in_gt in near_misses:
        sources = []
        if in_ts: sources.append("TotalSeg")
        if in_moose: sources.append("MOOSE")
        if in_gt: sources.append("GT")
        print(f"  {nk:<25} found in: {', '.join(sources)}")

print(f"\nConfig saved to: {CONFIG_OUT}")
print("This file is used by ts_run_voxtell.py, ts_evaluate.py, and ts_results_table.py.")
if near_misses:
    print(f"\nNOTE: {len(near_misses)} near-miss(es) found above — review them, since a naming")
    print("mismatch could be hiding a real match that should be part of the common set.")
