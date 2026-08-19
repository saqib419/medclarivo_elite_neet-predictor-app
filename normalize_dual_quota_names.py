"""
Zoram Medical College, Agartala Government Medical College, and Patna
Medical College each genuinely have TWO real, distinct rows -- one
with AIQ cutoffs, one with State cutoffs -- because this app's data
model represents multi-quota colleges as separate rows per quota
(confirmed by reading PredictorForm.jsx / CollegeRow.jsx: the
predictor filters strictly by a single selected quota value, and each
row carries one quota's cutoffs).

DO NOT merge/delete either row in these pairs -- that would destroy
real cutoff data for one of the two counselling tracks. The actual
bug is just that the two rows have slightly different name casing/
spacing, making them look like accidental duplicates instead of two
quota-facets of the same college. This script only normalizes the
`name` field so both rows read identically, keeping every other field
untouched on both sides.

Usage:
    python3 normalize_dual_quota_names.py --dry-run
    python3 normalize_dual_quota_names.py --apply
"""

import json
import sys
import argparse

# (name_to_use_for_both, other_name_to_rename)
NORMALIZE_PAIRS = [
    ("Zoram Medical College, Falkawn", "ZORAM MEDICAL COLLEGE Falkawn"),
    ("Agartala Government Medical College", "AGARTALA GOVT. MEDICAL COLLEGE"),
    ("Patna Medical College, Patna", "PATNA MEDICAL COLLEGE"),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data", default="public/data.json")
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        print("Specify --dry-run or --apply")
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    colleges = data["colleges"]
    by_name = {c.get("name"): c for c in colleges}

    for keep_name, rename_from in NORMALIZE_PAIRS:
        keep = by_name.get(keep_name)
        other = by_name.get(rename_from)
        if not keep or not other:
            print(f"⚠️  Could not find both: {keep_name!r} / {rename_from!r}")
            continue

        print(f"Both rows kept, both real cutoff data preserved:")
        print(f"  Row 1: {keep['name']}  (quota={keep.get('quota')}, cutoffs={'yes' if keep.get('cutoffs') else 'no'})")
        print(f"  Row 2: {other['name']}  (quota={other.get('quota')}, cutoffs={'yes' if other.get('cutoffs') else 'no'})")
        print(f"  -> renaming Row 2 to: \"{keep_name}\"")
        print()

        if args.apply:
            other["name"] = keep_name

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Applied. Names normalized -- college count unchanged ({len(colleges)}).")
    else:
        print(f"(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
