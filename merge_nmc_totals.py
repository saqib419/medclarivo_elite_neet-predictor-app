"""
Merge official NMC total-seat data into data.json.

Source: NMC Seat Matrix for AY 2026-27 (excluding INIs) — 823 colleges,
government + private, REAL total seats (not just the 15% AIQ slice).
This is authoritative for totalSeats. It does NOT give a category
(General/OBC/SC/ST/EWS) breakdown, so seatMatrix is left untouched here.

Usage:
    python3 merge_nmc_totals.py --dry-run
    python3 merge_nmc_totals.py --apply
"""

import json
import re
import sys
import argparse
import difflib

def normalize(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[.,\-&]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def best_match(target_name, official_names_norm, official_lookup, threshold=0.85):
    target_norm = normalize(target_name)
    best_score = 0
    best_name = None
    for official_norm, official_orig in zip(official_names_norm, official_lookup):
        score = difflib.SequenceMatcher(None, target_norm, official_norm).ratio()
        if target_norm == official_norm:
            score = 1.0
        elif target_norm in official_norm or official_norm in target_norm:
            score = max(score, 0.9)
        if score > best_score:
            best_score = score
            best_name = official_orig
    if best_score >= threshold:
        return best_name, best_score
    return None, best_score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data", default="public/data.json")
    parser.add_argument("--official", default="nmc_total_seats_clean.json")
    parser.add_argument("--threshold", type=float, default=0.85)
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        print("Specify --dry-run or --apply")
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(args.official, "r", encoding="utf-8") as f:
        official = json.load(f)

    official_names = list(official.keys())
    official_names_norm = [normalize(n) for n in official_names]

    colleges = data.get("colleges", [])
    matched = 0
    unmatched = []
    changes = []

    for college in colleges:
        name = college.get("name", "")
        official_name, score = best_match(name, official_names_norm, official_names, args.threshold)
        if official_name:
            matched += 1
            entry = official[official_name]
            old_total = college.get("totalSeats")
            new_total = entry["totalSeats"]
            if old_total != new_total:
                changes.append({
                    "app_name": name,
                    "official_name": official_name,
                    "score": round(score, 3),
                    "old_total": old_total,
                    "new_total": new_total,
                    "state": entry["state"],
                    "mgmt": entry["mgmt"],
                })
                if args.apply:
                    college["totalSeats"] = new_total
        else:
            unmatched.append(f"{name}  (best score seen: {score:.2f})")

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"Matched against official NMC total-seat data: {matched}")
    print(f"Not matched (below threshold {args.threshold}): {len(unmatched)}")
    print(f"totalSeats changes to apply: {len(changes)}")

    print(f"\n=== FIRST 30 CHANGES ===")
    for c in changes[:30]:
        print(f"\n{c['app_name']}  -->  {c['official_name']}  (score {c['score']}, {c['state']}, {c['mgmt']})")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")

    with open("nmc_unmatched.txt", "w") as f:
        f.write("\n".join(unmatched))
    with open("nmc_changes.json", "w") as f:
        json.dump(changes, f, indent=2)

    print(f"\nWrote nmc_unmatched.txt ({len(unmatched)} entries) and nmc_changes.json ({len(changes)} entries)")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} totalSeats corrections to {args.data}")
    else:
        print(f"\n(Dry run — nothing written. Review nmc_changes.json fully before applying.)")

if __name__ == "__main__":
    main()
