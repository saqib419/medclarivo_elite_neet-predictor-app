"""
Merge verified duplicate-row groups found by find_duplicate_pairs.py.

Every group below was individually fact-checked (web search) before
inclusion -- name-similarity + complementary-data-gap alone was NOT
enough evidence, since that same pattern produced false positives for
Dr. DY Patil Medical College (Pune) vs Dr. D Y Patil Medical College,
Kolhapur, and vs Dr. Ulhas Patil Medical College, Jalgaon -- all
confirmed to be genuinely DIFFERENT, unrelated colleges that merely
share the "Patil" surname. Same for Sri Siddhartha Medical College,
Tumkur vs Sri Siddhartha Institute of Medical Sciences, Bengaluru --
confirmed different real institutions under the same academy name.
None of those are included here.

Each group: the entries with real cutoffs get merged INTO the entry
that has totalSeats/category/seatMatrix (the fuller schema), the
same pattern used for the SKIMS/Sher-I-Kashmir merge. Source rows are
then removed.

Usage:
    python3 merge_verified_duplicates.py --dry-run
    python3 merge_verified_duplicates.py --apply
"""

import json
import sys
import argparse

# Each group: list of "cutoffs-only" source names to merge INTO the
# single "target" name (which holds seats/category/seatMatrix).
MERGE_GROUPS = [
    {
        "target": "Uttar Pradesh University of Medical Sciences, (Prev. UP Rural Inst.of Med.Sc&R) Etawah",
        "sources": ["Uttar Pradesh University of Medical Sciences"],
    },
    {
        "target": "Chhattisgarh Institute of Medical Sciences, Bilaspur",
        "sources": ["CHHATTISGARH INSTITUTE OF MEDICAL SCIENCES"],
    },
    {
        "target": "Gandhi Medical College, Bhopal",
        "sources": ["GANDHI MEDICAL COLLEGE"],
    },
    {
        "target": "Nagaland Institute of Medical Sciences & Research",
        "sources": ["NAGALAND INSTITUTE OF MEDICAL SCIENCE AND RESEARCH PHIREBAGIE"],
    },
    {
        "target": "North Bengal Medical College, Darjeeling",
        "sources": ["NORTH BENGAL MED.COLL"],
    },
    {
        "target": "Institute Of Medical Sciences & SUM Hospital, Bhubaneswar",
        "sources": [
            "Institute of Medical Sciences & SUM Hospital",
            "Institute of Medical Sciences and SUM Host.",
        ],
    },
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
    merges_done = 0

    print(f"=== PROCESSING {len(MERGE_GROUPS)} MERGE GROUPS ===\n")

    for group in MERGE_GROUPS:
        target_name = group["target"]
        source_names = group["sources"]

        target = by_name.get(target_name)
        if not target:
            print(f"⚠️  TARGET NOT FOUND: {target_name} -- skipping this group\n")
            continue

        print(f"Target: {target_name}")
        print(f"  before: cutoffs={'yes' if target.get('cutoffs') else 'no'}  totalSeats={target.get('totalSeats')}")

        merged_cutoffs = target.get("cutoffs")
        merged_trends = target.get("cutoffTrends") or []

        for sname in source_names:
            source = by_name.get(sname)
            if not source:
                print(f"  ⚠️  source not found: {sname}")
                continue
            print(f"  <- merging in: {sname}  (cutoffs={'yes' if source.get('cutoffs') else 'no'})")
            if source.get("cutoffs") and not merged_cutoffs:
                merged_cutoffs = source["cutoffs"]
            if source.get("cutoffTrends"):
                merged_trends = source["cutoffTrends"]
            names_to_remove.add(sname)

        target["cutoffs"] = merged_cutoffs
        target["cutoffTrends"] = merged_trends
        if target.get("dataStatus") == "seatsOnly" and merged_cutoffs:
            del target["dataStatus"]

        print(f"  after:  cutoffs={'yes' if target.get('cutoffs') else 'no'}  totalSeats={target.get('totalSeats')}\n")
        merges_done += 1

    print(f"=== SUMMARY ===")
    print(f"Groups processed: {merges_done}")
    print(f"Source rows to remove: {len(names_to_remove)}")
    for n in names_to_remove:
        print(f"  - {n}")

    if args.apply:
        new_colleges = [c for c in colleges if c.get("name") not in names_to_remove]
        data["colleges"] = new_colleges
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied. Total colleges: {len(colleges)} -> {len(new_colleges)}")
    else:
        print(f"\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
