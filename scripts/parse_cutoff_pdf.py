#!/usr/bin/env python3
"""
parse_cutoff_pdf.py

Reads an official MCC (mcc.nic.in) or state counselling "allotment result"
PDF — the candidate-wise list published after each counselling round — and
aggregates it into closing ranks per (college, quota, category).

Why aggregate instead of just "extract the table"?
MCC/state PDFs list one row per admitted CANDIDATE (rank, name, category,
quota, allotted college, course) — not a ready-made cutoff table. The
"closing rank" for a college+category is simply the WORST (highest number)
rank among candidates allotted there in that category. This script computes
that.

USAGE
  python parse_cutoff_pdf.py input.pdf --out raw_extracted.csv
  python parse_cutoff_pdf.py input.pdf --out raw_extracted.csv --course MBBS

Always inspect the output CSV before feeding it to build_data_json.py —
PDF table extraction is not perfect, and this script tells you plainly
when it had to skip a table it couldn't confidently read.
"""

import argparse
import csv
import re
import sys
from collections import defaultdict

import pdfplumber

# Column-header keywords we look for (case-insensitive substring match).
# Real PDFs vary in exact wording — extend these lists if your PDF's
# headers aren't being picked up (the script will tell you if so).
HEADER_KEYWORDS = {
    "rank": ["rank"],
    "category": ["category", "cat", "caste"],
    "quota": ["quota"],
    "institute": ["institute", "college", "allotted institute", "allotted college"],
    "course": ["course", "programme", "program"],
}
REQUIRED_KEYS = ["rank", "category", "quota", "institute"]

# Common category label variants seen across MCC/state PDFs, normalized to
# the labels this app's data.json expects. Extend this if you see a label
# in the "unmapped categories" warning at the end of a run.
CATEGORY_ALIASES = {
    "ur": "General", "gen": "General", "general": "General", "unreserved": "General",
    "obc": "OBC", "obc-ncl": "OBC", "obc ncl": "OBC",
    "ews": "EWS",
    "sc": "SC",
    "st": "ST",
    "pwd": "PwD", "pwbd": "PwD", "ur pwd": "PwD", "gen pwd": "PwD",
}


def normalize_category(raw):
    key = re.sub(r"\s+", " ", raw.strip().lower())
    key = key.replace(".", "")
    return CATEGORY_ALIASES.get(key, raw.strip())


def match_columns(header_row):
    mapping = {}
    for idx, col in enumerate(header_row):
        if not col:
            continue
        c = col.strip().lower()
        for key, keywords in HEADER_KEYWORDS.items():
            if key in mapping:
                continue
            if any(kw in c for kw in keywords):
                mapping[key] = idx
    return mapping


def extract_rows(pdf_path, course_filter=None):
    rows = []
    skipped_tables = 0
    readable_tables = 0

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            if page_num % 20 == 0 or page_num == total_pages:
                print(f"  scanning page {page_num}/{total_pages}...", file=sys.stderr)
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                header = table[0]
                colmap = match_columns(header)
                if not all(k in colmap for k in REQUIRED_KEYS):
                    skipped_tables += 1
                    continue
                readable_tables += 1
                for r in table[1:]:
                    try:
                        rank_raw = r[colmap["rank"]] or ""
                        digits = re.sub(r"[^\d]", "", rank_raw)
                        if not digits:
                            continue
                        rank = int(digits)

                        category_raw = (r[colmap["category"]] or "").strip()
                        quota = (r[colmap["quota"]] or "").strip()
                        institute = (r[colmap["institute"]] or "").strip()
                        course = (r[colmap["course"]] or "").strip() if "course" in colmap else ""

                        if not (category_raw and quota and institute):
                            continue
                        if course_filter and course_filter.lower() not in course.lower():
                            continue

                        rows.append({
                            "rank": rank,
                            "category_raw": category_raw,
                            "category": normalize_category(category_raw),
                            "quota": quota,
                            "institute": institute,
                            "course": course,
                            "page": page_num,
                        })
                    except (IndexError, ValueError):
                        continue

    print(f"\nReadable tables: {readable_tables}   Skipped (unrecognized headers): {skipped_tables}", file=sys.stderr)
    if skipped_tables and not readable_tables:
        print(
            "WARNING: No tables were readable. This PDF's column headers don't match "
            "the keywords this script looks for, or the PDF is scanned (image-based). "
            "Open the PDF and check the header row wording, then extend HEADER_KEYWORDS "
            "in this script accordingly. If it's scanned, text extraction won't work — "
            "you'd need OCR first.",
            file=sys.stderr,
        )
    return rows


def aggregate(rows):
    """Closing rank per (institute, quota, category) = the worst (max) rank seen."""
    agg = defaultdict(lambda: {"closing_rank": 0, "count": 0})
    for r in rows:
        key = (r["institute"], r["quota"], r["category"])
        agg[key]["closing_rank"] = max(agg[key]["closing_rank"], r["rank"])
        agg[key]["count"] += 1
    return agg


def main():
    ap = argparse.ArgumentParser(description="Parse an MCC/state allotment PDF into closing-rank data.")
    ap.add_argument("pdf", help="Path to the allotment result PDF")
    ap.add_argument("--out", default="raw_extracted.csv", help="Output CSV path (default: raw_extracted.csv)")
    ap.add_argument("--course", default=None, help='Only keep rows matching this course, e.g. "MBBS" (skips BDS etc.)')
    args = ap.parse_args()

    print(f"Reading {args.pdf} ...", file=sys.stderr)
    rows = extract_rows(args.pdf, course_filter=args.course)
    print(f"Extracted {len(rows)} candidate rows.", file=sys.stderr)

    if not rows:
        print("Nothing extracted — see warnings above. No CSV written.", file=sys.stderr)
        sys.exit(1)

    agg = aggregate(rows)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["institute", "quota", "category", "closing_rank", "candidates_seen"])
        for (institute, quota, category), vals in sorted(agg.items()):
            writer.writerow([institute, quota, category, vals["closing_rank"], vals["count"]])

    print(f"\nWrote {len(agg)} college/quota/category rows to {args.out}", file=sys.stderr)

    # Flag any category labels that didn't get normalized, so the user can
    # extend CATEGORY_ALIASES rather than silently mis-tag data.
    unmapped = sorted({
        r["category_raw"] for r in rows
        if r["category"] not in {"General", "OBC", "EWS", "SC", "ST", "PwD"}
    })
    if unmapped:
        print(
            f"\nNOTE: these category labels weren't recognized and were kept as-is: {unmapped}\n"
            "Add them to CATEGORY_ALIASES in this script if they should map to a standard category.",
            file=sys.stderr,
        )

    print(f"\nNext: open {args.out} and sanity-check a few rows against the PDF itself, "
          f"then run build_data_json.py on it.", file=sys.stderr)


if __name__ == "__main__":
    main()
