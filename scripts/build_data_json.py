#!/usr/bin/env python3
"""
build_data_json.py

Takes the CSV produced (and reviewed) from parse_cutoff_pdf.py and merges
it into the app's public/data.json — updating cutoffs for colleges that
already exist there, and adding new ones.

Run this once per PDF you process. State-quota PDFs only cover one state,
so pass --state each time; the AIQ (mcc.nic.in) PDF has no single state,
so pass --quota AIQ instead.

USAGE
  # All-India Quota PDF (from mcc.nic.in)
  python build_data_json.py aiq_extracted.csv --quota AIQ --data public/data.json

  # A state counselling PDF
  python build_data_json.py up_extracted.csv --quota State --state "Uttar Pradesh" --data public/data.json

Institutes are matched by name, case-insensitively, with whitespace
normalized. If a college in the CSV doesn't match anything already in
data.json, it's added as a new entry — review the diff before committing.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

VALID_CATEGORIES = {"General", "EWS", "OBC", "SC", "ST", "PwD"}


def norm_name(name):
    return re.sub(r"\s+", " ", name.strip().lower())


def load_csv_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            category = r["category"].strip()
            if category not in VALID_CATEGORIES:
                print(f"  skipping row with unrecognized category '{category}' for {r['institute']}", file=sys.stderr)
                continue
            rows.append({
                "institute": r["institute"].strip(),
                "category": category,
                "closing_rank": int(r["closing_rank"]),
            })
    return rows


def main():
    ap = argparse.ArgumentParser(description="Merge a closing-rank CSV into public/data.json")
    ap.add_argument("csv_path", help="CSV from parse_cutoff_pdf.py (reviewed)")
    ap.add_argument("--quota", required=True, choices=["AIQ", "State"], help="Quota type for every row in this CSV")
    ap.add_argument("--state", default=None, help='Domicile state, required if --quota State (e.g. "Uttar Pradesh")')
    ap.add_argument("--data", default="public/data.json", help="Path to data.json (default: public/data.json)")
    args = ap.parse_args()

    if args.quota == "State" and not args.state:
        ap.error("--state is required when --quota State")

    data_path = Path(args.data)
    if not data_path.exists():
        ap.error(f"{data_path} not found — run this from your project root, or pass --data")

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    colleges = data.setdefault("colleges", [])
    by_name = {norm_name(c["name"]): c for c in colleges}

    rows = load_csv_rows(args.csv_path)

    updated, added = 0, 0
    for row in rows:
        key = norm_name(row["institute"])
        college = by_name.get(key)
        if college is None:
            college = {
                "name": row["institute"],
                "quota": args.quota,
                "state": args.state if args.quota == "State" else None,
                "cutoffs": {},
            }
            colleges.append(college)
            by_name[key] = college
            added += 1
        college["cutoffs"][row["category"]] = row["closing_rank"]
        updated += 1

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Updated {updated} cutoff values ({added} new colleges added) in {data_path}", file=sys.stderr)
    print("Review the diff (git diff public/data.json) before committing.", file=sys.stderr)


if __name__ == "__main__":
    main()
