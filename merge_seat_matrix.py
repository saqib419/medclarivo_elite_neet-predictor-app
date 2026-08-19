"""
Merge official MCC AIQ seat matrix into data.json.

Usage:
    python3 merge_seat_matrix.py --dry-run     # just show what would match/change
    python3 merge_seat_matrix.py --apply       # actually write changes to data.json

Requires: mcc_aiq_seat_matrix_clean.json in the same folder.
"""

import json
import re
import sys
import argparse
import difflib

def normalize(name):
    """Strip punctuation, lowercase, collapse whitespace, drop common noise words."""
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)  # drop parenthetical codes like (200502)
    name = re.sub(r"[.,\-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def best_match(target_name, official_names_normalized, official_lookup, threshold=0.55):
    target_norm = normalize(target_name)
    best_score = 0
    best_name = None
    for official_norm, official_orig in zip(official_names_normalized, official_lookup):
        # Quick containment check first (cheap + often correct for these datasets)
        if target_norm in official_norm or official_norm.split(",")[0].strip() in target_norm:
            score = 1.0
        else:
            score = difflib.SequenceMatcher(None, target_norm, official_norm).ratio()
        if score > best_score:
            best_score = score
            best_name = official_orig
    if best_score >= threshold:
        return best_name, best_score
    return None, best_score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes to data.json")
    parser.add_argument("--dry-run", action="store_true", help="Only report, don't write")
    parser.add_argument("--data", default="public/data.json")
    parser.add_argument("--official", default="mcc_aiq_seat_matrix_clean.json")
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
        official_name, score = best_match(name, official_names_norm, official_names)
        if official_name:
            matched += 1
            official_entry = official[official_name]
            old_total = college.get("totalSeats")
            old_matrix = college.get("seatMatrix")
            new_total = official_entry["totalSeats"]
            new_matrix = official_entry["seatMatrix"]

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
                    college["seatMatrix"] = {
                        "General (UR)": new_matrix.get("General", 0),
                        "OBC": new_matrix.get("OBC", 0),
                        "SC": new_matrix.get("SC", 0),
                        "ST": new_matrix.get("ST", 0),
                        "EWS": new_matrix.get("EWS", 0),
                    }
        else:
            unmatched.append(name)

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"Matched against official MCC data: {matched}")
    print(f"Unmatched (likely state-quota / not in AIQ file): {len(unmatched)}")
    print(f"Changes needed: {len(changes)}")

    print(f"\n=== SAMPLE CHANGES (first 10) ===")
    for c in changes[:10]:
        print(f"\n{c['app_name']}  -->  matched: {c['official_name']}  (score {c['score']})")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")
        print(f"  seatMatrix: {c['old_matrix']} -> {c['new_matrix']}")

    with open("unmatched_colleges.txt", "w") as f:
        f.write("\n".join(unmatched))
    print(f"\nFull unmatched list written to unmatched_colleges.txt")

    with open("all_changes.json", "w") as f:
        json.dump(changes, f, indent=2)
    print(f"Full change list written to all_changes.json")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} changes directly to {args.data}")
    else:
        print(f"\n(Dry run only — no files were changed. Re-run with --apply to write changes.)")

if __name__ == "__main__":
    main()
