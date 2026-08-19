"""
Reseed totalSeats (and seatMatrix, where available) for AIIMS/INI
colleges in data.json, using the verified MCC central-quota seat data
(mcc_central_quota_seat_matrix.json).

Why a separate, narrow script instead of running the general NMC
matcher on these: the NMC seat-matrix source used by
merge_nmc_totals_v8.py explicitly EXCLUDES INIs (AIIMS, JIPMER,
PGIMER, NIMHANS, SCTIMST) -- that's exactly why v8 skips them. Their
real seat counts live in a different official source: the MCC
central/All-India-Quota seat matrix, which *does* cover them (AIIMS
Delhi checked out at exactly 132 seats against an external source
during extraction).

This script:
  1. Only touches colleges in data.json whose name matches an
     AIIMS/INI pattern (same detection used in v8).
  2. Matches each one against mcc_central_quota_seat_matrix.json by
     simple substring/token overlap (small, well-defined list, so a
     light heuristic is safe here -- no need for the heavier
     state/mgmt-aware matcher used for the general 918-college merge).
  3. Reports every match with its score for manual eyeballing before
     applying -- still a dry-run/apply split, same safety pattern as
     the other scripts.
  4. Leaves totalSeats untouched for anything it can't confidently
     match (never guesses).

Usage:
    python3 reseed_aiims_ini.py --dry-run
    python3 reseed_aiims_ini.py --apply
"""

import json
import re
import sys
import argparse
import difflib

INI_PATTERNS = [
    r"\baiims\b",
    r"\ball india institute of medical sciences\b",
    r"\bjipmer\b",
    r"\bpgimer\b",
    r"\bnimhans\b",
    r"\bsctimst\b",
]
INI_RE = re.compile("|".join(INI_PATTERNS), re.IGNORECASE)

def is_ini(name):
    return bool(INI_RE.search(name or ""))

def normalize(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)   # drop parenthetical codes e.g. (200510)
    name = re.sub(r"[.,\-&]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def extract_city_token(name):
    """Pull out a likely city/location word from an AIIMS name, e.g.
    'AIIMS Guwahati' -> 'guwahati', 'AIIMS, New Delhi, ...' -> 'delhi'."""
    norm = normalize(name)
    skip = {"aiims", "all", "india", "institute", "of", "medical", "sciences", "the"} | GENERIC_GEO_WORDS
    tokens = [t for t in norm.split() if t not in skip]
    return tokens

# The specific institution keyword each name must share -- prevents
# a false match like "JIPMER Puducherry" -> "Chettinad Institute of
# Medical Education and Research" (both share the generic word
# "research", nothing else) or "AIIMS Bibi Nagar" -> "AIIMS-Bhopal"
# (both share the generic word "aiims" but different cities). This
# gate requires the SAME specific keyword AND, if both names have a
# recognizable location word, that they overlap too.
INSTITUTION_KEYWORDS = ["aiims", "jipmer", "pgimer", "nimhans", "sctimst"]

def institution_keyword(name):
    # Check the RAW lowercased name, not the parenthesis-stripped one --
    # some app-side names only carry the keyword inside parentheses,
    # e.g. "...Research (JIPMER), Puducherry". Stripping parens first
    # (as normalize() does) would silently lose that signal and let
    # the gate below no-op, which is exactly the bug that let JIPMER
    # match to an unrelated Chettinad college.
    raw = (name or "").lower()
    for kw in INSTITUTION_KEYWORDS:
        if kw in raw:
            return kw
    return None

# Generic geography words that appear inside many unrelated Indian
# place names/addresses -- NOT reliable evidence of a real match on
# their own (e.g. "nagar" appears in hundreds of place names; it let
# "AIIMS, Bibi Nagar" wrongly match "AIIMS-Bhopal...SAKET NAGAR").
GENERIC_GEO_WORDS = {
    "nagar", "road", "sector", "phase", "district", "post", "pin",
    "colony", "marg", "east", "west", "north", "south", "near",
    "opp", "dist", "po", "ps",
}

def best_match(app_name, official_list):
    app_kw = institution_keyword(app_name)
    app_tokens = set(extract_city_token(app_name))
    best_score = 0
    best_key = None
    for official_name in official_list:
        # HARD GATE: must be the same institution type (aiims-to-aiims,
        # jipmer-to-jipmer, etc.) -- never cross-match between them.
        # Both sides must carry a recognized keyword and it must be
        # identical; if either side has none, refuse to match rather
        # than silently falling through to unrestricted scoring.
        off_kw = institution_keyword(official_name)
        if not app_kw or not off_kw or app_kw != off_kw:
            continue

        off_tokens = set(extract_city_token(official_name))
        overlap = len(app_tokens & off_tokens)
        char_score = difflib.SequenceMatcher(None, normalize(app_name), normalize(official_name)).ratio()
        # HARD GATE: when there's more than one candidate of the same
        # institution type (e.g. many AIIMS), a real location/city
        # token must overlap -- generic words alone don't count.
        if app_tokens and not overlap:
            continue
        score = char_score
        if score > best_score:
            best_score = score
            best_key = official_name
    return best_key, best_score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data", default="public/data.json")
    parser.add_argument("--official", default="mcc_central_quota_seat_matrix.json")
    parser.add_argument("--threshold", type=float, default=0.35)
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        print("Specify --dry-run or --apply")
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(args.official, "r", encoding="utf-8") as f:
        official = json.load(f)

    official_names = list(official.keys())

    colleges = data.get("colleges", [])
    ini_colleges = [c for c in colleges if is_ini(c.get("name", ""))]

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"AIIMS/INI colleges found: {len(ini_colleges)}")

    changes = []
    unmatched = []

    for college in ini_colleges:
        name = college.get("name", "")
        official_name, score = best_match(name, official_names)
        if official_name and score >= args.threshold:
            entry = official[official_name]
            old_total = college.get("totalSeats")
            new_total = entry["totalSeats"]
            changes.append({
                "college_obj": college,
                "app_name": name,
                "official_name": official_name,
                "score": round(score, 3),
                "old_total": old_total,
                "new_total": new_total,
                "seatMatrix": entry.get("seatMatrix"),
                "instituteType": entry.get("instituteType"),
            })
        else:
            unmatched.append(f"{name}  (best score seen: {score:.2f})")

    print(f"Matched: {len(changes)}")
    print(f"Unmatched (left as-is, needs manual check): {len(unmatched)}")

    print(f"\n=== MATCHES (review before applying) ===")
    for c in changes:
        print(f"\n{c['app_name']}")
        print(f"  --> {c['official_name']}  (score {c['score']}, type: {c['instituteType']})")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")
        if c["seatMatrix"]:
            print(f"  seatMatrix: {c['seatMatrix']}")
        if args.apply:
            c["college_obj"]["totalSeats"] = c["new_total"]
            if c["seatMatrix"]:
                c["college_obj"]["seatMatrix"] = c["seatMatrix"]

    if unmatched:
        print(f"\n=== UNMATCHED (left untouched -- review manually) ===")
        for u in unmatched:
            print(f"  - {u}")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} AIIMS/INI totalSeats corrections to {args.data}")
    else:
        print(f"\n(Dry run — nothing written. Review scores/matches above, especially anything below 0.5.)")

if __name__ == "__main__":
    main()
