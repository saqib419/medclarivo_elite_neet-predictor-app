#!/usr/bin/env python3
"""
parse_cutoff_pdf.py

Reads an official MCC (mcc.nic.in) "Final/Revised Result for Round-N of
UG Counselling" PDF and computes a closing rank per college.

REAL FORMAT NOTE (found by testing against the actual Round 3 2025 PDF):
These PDFs are NOT a simple one-row-per-candidate cutoff table. Each row
is one candidate RANK, with columns for their status in Round 1, Round 2,
AND Round 3 side by side (colleges change as candidates upgrade across
rounds). The "Allotted Category" column is mostly blank ("-") except in
rows where the candidate was freshly upgraded that round — most rows just
say "Reported" with no category listed for later rounds.

Because of this, category-wise cutoffs aren't reliably extractable from
this PDF alone. This script instead computes a CATEGORY-BLIND closing
rank per college: the worst (highest) rank whose FINAL settled institute
(last non-blank round column) was that college. This is a reasonable
first-pass approximation — General category closing rank is usually close
to the overall closing rank, since General is typically the last category
to fill each seat. Reserved-category candidates will see a slightly more
conservative (lower) number than their true cutoff.

USAGE
  python parse_cutoff_pdf.py input.pdf --out raw_extracted.csv
  python parse_cutoff_pdf.py input.pdf --out raw_extracted.csv --course MBBS

Always inspect the output CSV before feeding it to build_data_json.py.
"""

import argparse
import csv
import re
import sys
from collections import defaultdict

import pdfplumber

BLANK_MARKERS = {"", "-", "--"}

# Tokens used for the "Candidate Category" column in clean single-round
# PDFs (e.g. Round 1's format). If we see one of these while scanning
# right-to-left before we reach the institute name, that's the real
# category for this candidate — much more useful than defaulting
# everything to General.
CATEGORY_TOKENS = {
    "GENERAL": "General", "GEN": "General", "OPEN": "General", "UR": "General",
    "OBC": "OBC", "OBC-NCL": "OBC", "BC": "OBC",
    "SC": "SC", "ST": "ST",
    "EWS": "EWS",
    "PWD": "PwD",
}

# Indian states + UTs, used to pull the physical state out of the address
# text that trails the institute name in these PDF cells. Ordered longest
# first so e.g. "Uttar Pradesh" matches before a shorter substring could.
INDIAN_STATES = sorted([
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Tamilnadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "NCT of Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry", "Pondicherry",
], key=len, reverse=True)


def find_state(text):
    """Search address text for a known Indian state/UT name."""
    if not text:
        return None
    upper = text.upper()
    for state in INDIAN_STATES:
        if state.upper() in upper:
            # Normalize a couple of common alt-spellings.
            if state in ("Tamilnadu",):
                return "Tamil Nadu"
            if state in ("Pondicherry",):
                return "Puducherry"
            if state in ("NCT of Delhi",):
                return "Delhi"
            return state
    return None


def is_blank(cell):
    if cell is None:
        return True
    return cell.strip() in BLANK_MARKERS


def extract_rows(pdf_path, course_filter=None):
    """
    Walks every table on every page. For each candidate row, finds the
    LAST round-block (rightmost group of columns) that has a real
    institute name, and treats that as the final settled allotment.
    """
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

                sample = table[1:6] if len(table) > 6 else table[1:]
                candidate_cols = []
                for col_idx in range(len(table[0]) if table[0] else 0):
                    hits = 0
                    values = []
                    for r in sample:
                        if col_idx < len(r) and r[col_idx] and re.match(r"^\d+$", r[col_idx].strip()):
                            hits += 1
                            values.append(int(r[col_idx].strip()))
                    if sample and hits >= max(1, len(sample) - 1):
                        candidate_cols.append((col_idx, sum(values) / len(values) if values else 0))

                if not candidate_cols:
                    skipped_tables += 1
                    continue

                rank_col = max(candidate_cols, key=lambda c: c[1])[0]

                readable_tables += 1
                ncols = len(table[0]) if table[0] else 0

                for r in table[1:]:
                    if rank_col >= len(r) or not r[rank_col]:
                        continue
                    rank_raw = re.sub(r"[^\d]", "", r[rank_col] or "")
                    if not rank_raw:
                        continue
                    rank = int(rank_raw)

                    final_institute = None
                    final_course = None
                    final_state = None
                    final_category = None
                    remaining = list(range(rank_col + 1, min(ncols, len(r))))
                    for idx in reversed(remaining):
                        cell = r[idx] if idx < len(r) else None
                        if is_blank(cell):
                            continue
                        text = cell.strip()
                        if text.upper() in {"MBBS", "BDS", "B.SC NURSING", "BSC NURSING"}:
                            final_course = text.upper()
                            continue
                        if final_category is None:
                            # Category cells aren't always a single clean
                            # token — PwD (disability) candidates get a
                            # compound cell like "OBC\nPwD" or "OBC PwD"
                            # (PwD is a horizontal quota stacked on a
                            # vertical category, not a substitute for one).
                            # Split on whitespace and match any token,
                            # preferring the non-PwD one as the true
                            # category.
                            words = text.upper().replace("\n", " ").split()
                            matches = [CATEGORY_TOKENS[w] for w in words if w in CATEGORY_TOKENS]
                            if matches:
                                non_pwd = [m for m in matches if m != "PwD"]
                                final_category = non_pwd[0] if non_pwd else matches[0]
                                continue
                        if len(text) > 8 and re.search(r"[A-Za-z]{4,}", text):
                            # Institute cells often contain the full mailing
                            # address after the name (e.g. "Govt Medical
                            # College Barmer Rajasthan,NH-15, JAISALMER
                            # ROAD, ..., 344001"). Truncating at the first
                            # comma works for those — but some institutes'
                            # REAL names contain a comma themselves (e.g.
                            # "AIIMS, New Delhi", "AIIMS, Bhopal"), where
                            # everything before the first comma alone is
                            # too generic/ambiguous (many campuses share
                            # "AIIMS"). Heuristic: if the text before the
                            # first comma is short (<=8 chars, i.e. an
                            # acronym like AIIMS/ESIC/PGIMER) AND is in
                            # ALL CAPS, keep the next comma-segment too so
                            # the city stays attached to the name.
                            parts = text.split(",")
                            first = parts[0].strip()
                            if len(parts) > 1 and len(first) <= 8 and first.isupper():
                                final_institute = f"{first}, {parts[1].strip()}"
                            else:
                                final_institute = first
                            final_state = find_state(text)
                            break

                    if not final_institute:
                        continue
                    if course_filter and final_course and course_filter.upper() != final_course:
                        continue

                    rows.append({
                        "rank": rank,
                        "institute": re.sub(r"\s+", " ", final_institute).strip(),
                        "course": final_course or "",
                        "state": final_state,
                        "category": final_category,  # None if not a clean-format PDF
                        "page": page_num,
                    })

    print(f"\nReadable tables: {readable_tables}   Skipped (no rank column found): {skipped_tables}", file=sys.stderr)
    if skipped_tables and not readable_tables:
        print(
            "WARNING: No tables were readable. Open the PDF and check it's a "
            "text-based table (not scanned/image), and that it has a column "
            "of plain candidate rank numbers.",
            file=sys.stderr,
        )
    return rows


def aggregate(rows):
    """Closing rank per (institute, category) = the worst (max) rank seen
    for candidates of that category who landed at that institute.

    Rows with no detected category are only used as 'General' when an
    institute has NO categorized rows at all in this PDF (true
    category-blind PDFs, e.g. Round 3's multi-round tracker format). If an
    institute DOES have real per-category rows elsewhere in this PDF, a
    stray uncategorized row is dropped instead of being folded into
    'General' — otherwise one uncategorized outlier can blow up General's
    max() far past its real value.

    State = the most frequently seen state for that institute name (a
    college should always resolve to one state; this guards against a
    stray bad match)."""
    has_category = defaultdict(bool)
    for r in rows:
        if r.get("category"):
            has_category[r["institute"]] = True

    agg = defaultdict(lambda: {"closing_rank": 0, "count": 0, "states": defaultdict(int)})
    for r in rows:
        category = r.get("category")
        if category is None:
            if has_category[r["institute"]]:
                continue
            category = "General"
        key = (r["institute"], category)
        agg[key]["closing_rank"] = max(agg[key]["closing_rank"], r["rank"])
        agg[key]["count"] += 1
        if r.get("state"):
            agg[key]["states"][r["state"]] += 1
    for vals in agg.values():
        vals["state"] = max(vals["states"], key=vals["states"].get) if vals["states"] else ""
    return agg


def main():
    ap = argparse.ArgumentParser(description="Parse an MCC multi-round allotment PDF into closing-rank data.")
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

    categorized = sum(1 for r in rows if r.get("category"))
    agg = aggregate(rows)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["institute", "quota", "category", "closing_rank", "candidates_seen", "state"])
        for (institute, category), vals in sorted(agg.items()):
            writer.writerow([institute, "AIQ", category, vals["closing_rank"], vals["count"], vals["state"]])

    print(f"\nWrote {len(agg)} (college, category) rows to {args.out}", file=sys.stderr)
    if categorized:
        pct = 100 * categorized // len(rows)
        print(
            f"\n{categorized}/{len(rows)} rows ({pct}%) had a real detected candidate "
            "category — those get accurate per-category cutoffs. Rows without "
            "one fell back to 'General' as a placeholder. Sanity-check a few "
            "rows against the PDF, then run build_data_json.py.",
            file=sys.stderr,
        )
    else:
        print(
            "\nNOTE: no candidate-category column was detected in this PDF — "
            "every row used 'General' as a placeholder. Sanity-check a few "
            "rows against the PDF, then run build_data_json.py.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
