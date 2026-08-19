"""
Remove confirmed junk / garbled-duplicate entries from public/data.json.

CONFIRMED JUNK (not real colleges — PDF-parsing artifacts):
  - "B.Sc. Nursing"            -> course/category label, not a college
  - "No Upgradati on"          -> a remarks-column status ("No Upgradation"), not a college
  - "ESIC, Medical College and Hospital" -> bare/generic header-row artifact

CONFIRMED GARBLED DUPLICATES (mid-word space corruption; the CORRECT
version of each already exists elsewhere in data.json with a real
totalSeats value, so these broken rows are pure duplicates and safe
to delete outright rather than merge):
  - "Chikkamagalu ru Institute of Medical Sciences"
      -> correct row: "Chikkamagaluru Institute of Medical Sciences, Chikkamagaluru"
  - "Dr.Radhakrish nan Government Medical College"
      -> correct row: "Dr.Radhakrishnan Government Medical College, Hamirpur, H.P" (or similar)
  - "Thiruvannamal ai MC"
      -> correct row: "Thiruvannamalai MC" / "Government Thiruvannamalai Medical College"

Usage:
    python3 cleanup_junk_entries.py --dry-run
    python3 cleanup_junk_entries.py --apply
"""

import json
import sys
import argparse

NAMES_TO_REMOVE = {
    "B.Sc. Nursing",
    "No Upgradati on",
    "ESIC, Medical College and Hospital",
    "Chikkamagalu ru Institute of Medical Sciences",
    "Dr.Radhakrish nan Government Medical College",
    "Thiruvannamal ai MC",
}

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

    colleges = data.get("colleges", [])
    before = len(colleges)

    removed = [c for c in colleges if c.get("name") in NAMES_TO_REMOVE]
    kept = [c for c in colleges if c.get("name") not in NAMES_TO_REMOVE]

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges before: {before}")
    print(f"Matched for removal: {len(removed)} (expected 6)")
    print(f"Total colleges after: {len(kept)}")

    print(f"\n=== ENTRIES BEING REMOVED ===")
    for c in removed:
        print(f"  - {c.get('name')}  (state: {c.get('state')}, totalSeats: {c.get('totalSeats')})")

    missing = NAMES_TO_REMOVE - {c.get("name") for c in removed}
    if missing:
        print(f"\n⚠️  WARNING: expected to remove these but didn't find them (name mismatch?):")
        for m in missing:
            print(f"  - {m}")

    if args.apply:
        data["colleges"] = kept
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Removed {len(removed)} junk/duplicate entries. {args.data} now has {len(kept)} colleges.")
    else:
        print(f"\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
