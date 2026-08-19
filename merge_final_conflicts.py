"""
Resolve the "genuine duplicate-target conflict" list from the
original NMC merge work. Each pair was individually researched
before inclusion here.

MERGED (verified same real college):
  - Osmania Medical College, Hyderabad / Koti -- Koti is just the
    Hyderabad locality the college is in (confirmed via Wikipedia +
    multiple local listings)
  - Nilratan Sircar/Sirkar Medical College -- spelling variant
  - BHU Institute of Medical Sciences Varanasi/Varansi -- typo
  - Karimnagar, Purnea Government Medical Colleges -- OCR "T " split
    artifact, same pattern fixed elsewhere in this project
  - Government Villupuram Medical College / GVMC -- abbreviation
  - GMC Rajamahendravaram / GMC abbreviation
  - Thiruvarur Govt Medical College / GTMC abbreviation
  - Government Medical College, Ongole / RIMS Ongole -- the official
    record's own name confirms "(previously Rajiv Gandhi Institute of
    Medical Sciences, Ongole)"
  - Rural Medical College and PIMS / Rural Medical College, Loni --
    PIMS (Pravara Institute of Medical Sciences) is based in Loni

LEFT ALONE (confirmed or likely genuinely different colleges -- do
NOT merge):
  - G.S.V.M. Medical College (Kanpur) vs G.S. Medical College & Hospital
    (Hapur) -- CONFIRMED different via web search (a comparison site
    lists them as separate, comparable colleges)
  - Malla Reddy Institute of Medical Sciences vs Malla Reddy Medical
    College for Women -- already confirmed different in earlier work
    ("for Women" is a real distinguishing suffix, not noise)
  - Sri Siddhartha Academy T Begur vs Sri Siddhartha Medical College DU
    -- same ambiguity family as the already-confirmed Tumkur vs
    Bengaluru split; left for manual review rather than guessed

Usage:
    python3 merge_final_conflicts.py --dry-run
    python3 merge_final_conflicts.py --apply
"""

import json
import sys
import argparse

MERGE_GROUPS = [
    {"target": "Osmania Medical College, Hyderabad", "sources": ["Osmania Medical College Koti"]},
    {"target": "Nilratan Sircar Medical College, Kolkata", "sources": ["NILRATAN SIRKAR MEDICAL COLLEGE"]},
    {"target": "Institute of Medical Sciences, BHU, Varanasi", "sources": ["Institute of Medical Sciences, BHU, Varansi"]},
    {"target": "GOVERNMENT MEDICAL COLLEGE Karimnagar Telangana", "sources": ["GOVERNMEN T MEDICAL COLLEGE Karimnagar Telangana"]},
    {"target": "GOVERNMENT MEDICAL COLLEGE PURNEA", "sources": ["GOVERNMEN T MEDICAL COLLEGE PURNEA"]},
    {"target": "Government Villupuram Medical College", "sources": ["GVMC, VILLUPURAM"]},
    {"target": "Government Medical College, Rajamahendravaram", "sources": ["GMC, Rajamahendravaram"]},
    {"target": "Thiruvarur Govt. Medical College, Thiruvarur", "sources": ["GTMC, THIRUVARUR"]},
    {"target": "Government Medical College, Ongole", "sources": ["RIMS, Ongole"]},
    {"target": "Rural Medical College, Loni", "sources": ["Rural Medical College and PIMS"]},
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

    print(f"=== PROCESSING {len(MERGE_GROUPS)} MERGE GROUPS ===\n")

    for group in MERGE_GROUPS:
        target_name = group["target"]
        target = by_name.get(target_name)
        if not target:
            print(f"⚠️  TARGET NOT FOUND: {target_name} -- skipping\n")
            continue

        print(f"Target: {target_name}")
        print(f"  before: cutoffs={'yes' if target.get('cutoffs') else 'no'}  totalSeats={target.get('totalSeats')}")

        for sname in group["sources"]:
            source = by_name.get(sname)
            if not source:
                print(f"  ⚠️  source not found: {sname}")
                continue
            print(f"  <- merging in: {sname}  (cutoffs={'yes' if source.get('cutoffs') else 'no'}, totalSeats={source.get('totalSeats')})")
            # fill in whichever fields the target is missing
            if not target.get("cutoffs") and source.get("cutoffs"):
                target["cutoffs"] = source["cutoffs"]
            if not target.get("cutoffTrends") and source.get("cutoffTrends"):
                target["cutoffTrends"] = source["cutoffTrends"]
            if target.get("totalSeats") is None and source.get("totalSeats") is not None:
                target["totalSeats"] = source["totalSeats"]
            if not target.get("category") and source.get("category"):
                target["category"] = source["category"]
            if not target.get("seatMatrix") and source.get("seatMatrix"):
                target["seatMatrix"] = source["seatMatrix"]
            names_to_remove.add(sname)

        if target.get("dataStatus") == "seatsOnly" and target.get("cutoffs"):
            del target["dataStatus"]

        print(f"  after:  cutoffs={'yes' if target.get('cutoffs') else 'no'}  totalSeats={target.get('totalSeats')}\n")

    print(f"=== LEFT ALONE (confirmed/likely different colleges) ===")
    for n in ["G.S.V.M. MEDICAL COLLEGE", "G.S. Medical College & Hospital, Hapur, UP",
              "Malla Reddy Institute of Medical Sciences", "Malla Reddy Medical College for Women",
              "Sri Siddhartha Academy T Begur", "Sri Siddhartha Medical College DU"]:
        print(f"  - {n}")

    print(f"\n=== SUMMARY ===")
    print(f"Source rows to remove: {len(names_to_remove)}")

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
