"""
Merge official MCC seat matrix into data.json — SAFE VERSION.

Only touches colleges that are AIIMS / Central University / Deemed
University / ESIC / JIPMER, because those report their FULL seat count
through MCC. Regular state government colleges only show their 15% AIQ
slice in this file, so they are deliberately left untouched here.

Usage:
    python3 merge_seat_matrix_v2.py --dry-run
    python3 merge_seat_matrix_v2.py --apply
"""

import json
import re
import sys
import argparse
import difflib

def normalize(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[.,\-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def best_match(target_name, official_names_normalized, official_lookup, threshold=0.80):
    target_norm = normalize(target_name)
    best_score = 0
    best_name = None
    for official_norm, official_orig in zip(official_names_normalized, official_lookup):
        score = difflib.SequenceMatcher(None, target_norm, official_norm).ratio()
        # boost score if target name appears as a clean prefix/substring of official name
        official_first_part = official_norm.split(",")[0].strip()
        if target_norm == official_first_part:
            score = 1.0
        elif target_norm in official_norm and len(target_norm) > 8:
            score = max(score, 0.92)
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
    parser.add_argument("--official", default="mcc_central_quota_seat_matrix.json")
    parser.add_argument("--threshold", type=float, default=0.80)
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
    rejected_low_confidence = []

    for college in colleges:
        name = college.get("name", "")
        official_name, score = best_match(name, official_names_norm, official_names, args.threshold)
        if official_name:
            matched += 1
            entry = official[official_name]
            old_total = college.get("totalSeats")
            old_matrix = college.get("seatMatrix")
            new_total = entry["totalSeats"]
            new_matrix = {
                "General (UR)": entry["seatMatrix"].get("General", 0),
                "OBC": entry["seatMatrix"].get("OBC", 0),
                "SC": entry["seatMatrix"].get("SC", 0),
                "ST": entry["seatMatrix"].get("ST", 0),
                "EWS": entry["seatMatrix"].get("EWS", 0),
            }
            if old_total != new_total or old_matrix != new_matrix:
                changes.append({
                    "app_name": name,
                    "official_name": official_name,
                    "score": round(score, 2),
                    "old_total": old_total,
                    "new_total": new_total,
                    "old_matrix": old_matrix,
                    "new_matrix": new_matrix,
                })
                if args.apply:
                    college["totalSeats"] = new_total
                    college["seatMatrix"] = new_matrix
        else:
            unmatched.append(f"{name}  (best score seen: {score:.2f})")

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"Matched against 100%-quota official institutes: {matched}")
    print(f"Not matched (not AIIMS/Central/Deemed/ESIC/JIPMER, or below threshold): {len(unmatched)}")
    print(f"Changes to apply: {len(changes)}")

    print(f"\n=== ALL CHANGES ===")
    for c in changes:
        print(f"\n{c['app_name']}  -->  {c['official_name']}  (score {c['score']})")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")
        print(f"  seatMatrix: {c['old_matrix']} -> {c['new_matrix']}")

    with open("v2_unmatched.txt", "w") as f:
        f.write("\n".join(unmatched))
    with open("v2_changes.json", "w") as f:
        json.dump(changes, f, indent=2)

    print(f"\nWrote v2_unmatched.txt and v2_changes.json")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} changes to {args.data}")
    else:
        print(f"\n(Dry run — nothing written. Review v2_changes.json, then re-run with --apply.)")

if __name__ == "__main__":
    main()
