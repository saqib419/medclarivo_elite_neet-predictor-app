"""
Merge the 2 confirmed redundant duplicate pairs -- both sides have
the same quota/category/seats status (nothing complementary to
preserve), just slightly different name casing/punctuation and
different cutoffTrends array lengths. Keep whichever side has the
longer/richer cutoffTrends history.

Usage:
    python3 merge_redundant_pairs.py --dry-run
    python3 merge_redundant_pairs.py --apply
"""

import json
import sys
import argparse

# (name_to_keep, name_to_remove)
PAIRS = [
    ("ESI-MC&PGIMS&R", "ESI- MC&PGIMS& R"),
    ("GOVERNMENT MEDICAL COLLEGE AND GENERAL HOSPITAL", "Government Medical College and District General Hospital"),
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
    names_to_remove = set()

    for keep_name, remove_name in PAIRS:
        keep = by_name.get(keep_name)
        remove = by_name.get(remove_name)
        if not keep or not remove:
            print(f"⚠️  Could not find both: keep={bool(keep)} remove={bool(remove)} for pair ({keep_name!r}, {remove_name!r})")
            continue

        keep_trends = keep.get("cutoffTrends") or []
        remove_trends = remove.get("cutoffTrends") or []
        # keep whichever has more years of history
        if len(remove_trends) > len(keep_trends):
            keep["cutoffTrends"] = remove_trends
            if not keep.get("cutoffs") and remove.get("cutoffs"):
                keep["cutoffs"] = remove["cutoffs"]

        print(f"KEEP: {keep_name}  (cutoffTrends: {len(keep.get('cutoffTrends') or [])} years)")
        print(f"REMOVE: {remove_name}")
        names_to_remove.add(remove_name)
        print()

    if args.apply:
        new_colleges = [c for c in colleges if c.get("name") not in names_to_remove]
        data["colleges"] = new_colleges
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Applied. Total colleges: {len(colleges)} -> {len(new_colleges)}")
    else:
        print(f"(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
