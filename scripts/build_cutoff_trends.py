#!/usr/bin/env python3
"""
build_cutoff_trends.py

Takes a CSV from parse_cutoff_pdf.py (one closing rank per college for a
GIVEN YEAR + ROUND) and merges it into each college's `cutoffTrends` array
in data.json — the year-over-year history shown on the college details page.

Unlike build_data_json.py (which updates the CURRENT `cutoffs` object),
this appends/updates one entry per year in `cutoffTrends`, e.g.:

  "cutoffTrends": [
    {"year": 2025, "round1": 1181, "round2": null, "round3": null},
    {"year": 2024, "round1": 1050, "round2": null, "round3": null}
  ]

Run this once per (year, round) PDF you've already parsed with
parse_cutoff_pdf.py. Re-running for the same year+round updates that
entry in place rather than duplicating it.

USAGE
  python build_cutoff_trends.py aiq_round1_2024.csv --year 2024 --round round1 --data public/data.json
  python build_cutoff_trends.py aiq_round3_2025.csv --year 2025 --round round3 --data public/data.json
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

VALID_CATEGORIES = {"General", "EWS", "OBC", "SC", "ST", "PwD"}
VALID_ROUNDS = {"round1", "round2", "round3", "stray", "specialStray"}


def norm_name(name):
    return re.sub(r"\s+", " ", name.strip().lower())


def load_csv_rows(path, category_filter):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            category = r["category"].strip()
            if category not in VALID_CATEGORIES:
                continue
            if category_filter and category != category_filter:
                continue
            rows.append({
                "institute": r["institute"].strip(),
                "category": category,
                "closing_rank": int(r["closing_rank"]),
            })
    return rows


def main():
    ap = argparse.ArgumentParser(description="Merge a year's closing-rank CSV into each college's cutoffTrends.")
    ap.add_argument("csv_path", help="CSV from parse_cutoff_pdf.py (reviewed)")
    ap.add_argument("--year", required=True, type=int, help="e.g. 2024")
    ap.add_argument("--round", required=True, choices=sorted(VALID_ROUNDS), help="Which round this PDF was")
    ap.add_argument("--category", default="General", help="Which category's rank to use for the trend line (default: General, since that's what's usually shown)")
    ap.add_argument("--data", default="public/data.json", help="Path to data.json (default: public/data.json)")
    args = ap.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        ap.error(f"{data_path} not found — run this from your project root, or pass --data")

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    colleges = data.setdefault("colleges", [])
    by_name = {norm_name(c["name"]): c for c in colleges}

    rows = load_csv_rows(args.csv_path, args.category)

    updated_colleges = 0
    unmatched = []
    for row in rows:
        key = norm_name(row["institute"])
        college = by_name.get(key)
        if college is None:
            # Don't create new colleges from historical data alone — a
            # college that only shows up in an old PDF but never in the
            # current dataset is more likely a renamed/closed institute
            # than a genuinely new one. Just report it for a human to check.
            unmatched.append(row["institute"])
            continue

        trends = college.setdefault("cutoffTrends", [])
        entry = next((t for t in trends if t.get("year") == args.year), None)
        if entry is None:
            entry = {"year": args.year}
            trends.append(entry)
            trends.sort(key=lambda t: -t["year"])
        # The UI only renders two columns: round1 and round2 — it doesn't
        # know about round3/stray/etc. Regardless of which actual round
        # this PDF was, write into whichever of those two display slots
        # is still empty for this year, so the number actually shows up.
        if "round1" not in entry or entry["round1"] is None:
            entry["round1"] = row["closing_rank"]
        elif "round2" not in entry or entry["round2"] is None:
            entry["round2"] = row["closing_rank"]
        else:
            entry["round1"] = row["closing_rank"]  # overwrite as last resort
        updated_colleges += 1

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Updated cutoffTrends for {updated_colleges} colleges ({args.year} {args.round}, {args.category}) in {data_path}", file=sys.stderr)
    if unmatched:
        print(f"\n{len(unmatched)} colleges in the CSV had no name match in data.json — not added (could be renamed/closed, or a name-spelling mismatch). First few:", file=sys.stderr)
        for name in unmatched[:15]:
            print(f"  - {name}", file=sys.stderr)
    print("Review the diff (git diff public/data.json) before committing.", file=sys.stderr)


if __name__ == "__main__":
    main()
