"""
One-off merge: "SKIMS Medical College" and "Sher-I-Kashmir Instt. Of
Medical Sciences, Srinagar" are the same real college (Sher-I-Kashmir
Institute of Medical Sciences, Srinagar) represented as two partial
duplicate rows:

  - "SKIMS Medical College"        -> has real cutoffs/cutoffTrends,
                                       but no totalSeats/category/seatMatrix
  - "Sher-I-Kashmir Instt. Of..."  -> has totalSeats/category (State
                                       quota, Government, 125 seats),
                                       but no cutoffs at all

This script combines them into ONE row under the fuller official
name, keeping every real field from both sides, then deletes the
now-redundant "SKIMS Medical College" row.

Usage:
    python3 merge_skims_duplicate.py --dry-run
    python3 merge_skims_duplicate.py --apply
"""

import json
import sys
import argparse

NAME_WITH_CUTOFFS = "SKIMS Medical College"
NAME_WITH_SEATS = "Sher-I-Kashmir Instt. Of Medical Sciences, Srinagar"

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
    cutoffs_row = next((c for c in colleges if c.get("name") == NAME_WITH_CUTOFFS), None)
    seats_row = next((c for c in colleges if c.get("name") == NAME_WITH_SEATS), None)

    if not cutoffs_row or not seats_row:
        print("⚠️  Could not find both rows -- nothing to do. Found:")
        print(f"  {NAME_WITH_CUTOFFS}: {'found' if cutoffs_row else 'MISSING'}")
        print(f"  {NAME_WITH_SEATS}: {'found' if seats_row else 'MISSING'}")
        sys.exit(0)

    print("=== BEFORE ===")
    print(json.dumps(cutoffs_row, indent=2))
    print()
    print(json.dumps(seats_row, indent=2))

    # Build the merged record: keep seats_row's full structure (it has
    # the richer schema -- category, infrastructure, dataStatus, etc.)
    # but overlay the real cutoffs/cutoffTrends from cutoffs_row.
    merged = dict(seats_row)
    merged["cutoffs"] = cutoffs_row.get("cutoffs")
    merged["cutoffTrends"] = cutoffs_row.get("cutoffTrends", [])
    # This college now has real cutoff data, not just seats -- drop
    # the "seatsOnly" status flag if present.
    if merged.get("dataStatus") == "seatsOnly":
        del merged["dataStatus"]

    print("\n=== MERGED RESULT (will replace both rows with this single row) ===")
    print(json.dumps(merged, indent=2))

    if args.apply:
        new_colleges = [c for c in colleges if c.get("name") not in (NAME_WITH_CUTOFFS, NAME_WITH_SEATS)]
        new_colleges.append(merged)
        data["colleges"] = new_colleges
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Merged into one row. Total colleges: {len(colleges)} -> {len(new_colleges)}")
    else:
        print(f"\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
