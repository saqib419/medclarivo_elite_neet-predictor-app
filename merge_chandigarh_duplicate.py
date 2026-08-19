"""
One-off merge: Chandigarh has two rows for the same real college
(GMCH-32) with conflicting seat counts:

  - "Government Medical College and Hospital, Chandigarh" -- has real
    cutoffs/cutoffTrends, but totalSeats=170 (wrong)
  - "Government Medical College, Chandigarh" -- totalSeats=200, no
    cutoffs. 200 is CONFIRMED correct against
    mcc_central_quota_seat_matrix.json (official MCC source).

Merge into one row under the fuller name, with the correct seat
count.

Usage:
    python3 merge_chandigarh_duplicate.py --dry-run
    python3 merge_chandigarh_duplicate.py --apply
"""

import json
import sys
import argparse

NAME_WITH_CUTOFFS = "Government Medical College and Hospital, Chandigarh"
NAME_WITH_SEATS = "Government Medical College, Chandigarh"
CORRECT_SEATS = 200  # verified against mcc_central_quota_seat_matrix.json

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

    a = by_name.get(NAME_WITH_CUTOFFS)
    b = by_name.get(NAME_WITH_SEATS)

    if not a or not b:
        print(f"⚠️  Could not find both rows: a={bool(a)} b={bool(b)}")
        sys.exit(0)

    print("=== BEFORE ===")
    print(json.dumps(a, indent=2))
    print(json.dumps(b, indent=2))

    merged = dict(a)
    merged["totalSeats"] = CORRECT_SEATS

    print("\n=== MERGED ===")
    print(json.dumps(merged, indent=2))

    if args.apply:
        new_colleges = [c for c in colleges if c.get("name") not in (NAME_WITH_CUTOFFS, NAME_WITH_SEATS)]
        new_colleges.append(merged)
        data["colleges"] = new_colleges
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Merged. Total colleges: {len(colleges)} -> {len(new_colleges)}")
    else:
        print("\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
