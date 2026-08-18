"""
Merge official NMC total-seat data into data.json — v4.

Bugs found in v3's dry-run output that this version fixes:

1. AIIMS / INI false matches.
   The official NMC dataset behind this merge explicitly EXCLUDES seats
   of INIs (Institutes of National Importance) -- AIIMS, JIPMER,
   PGIMER, NIMHANS, etc. are INIs. So no AIIMS/INI college can have a
   legitimate match in this file. In v3 they were still being run
   through the matcher and landing on nonsense matches (e.g. "AIIMS
   Jammu" -> "Govt Medical College Jammu"). v4 detects these by name
   and skips them entirely -- never matched, never changed. They keep
   whatever totalSeats they already have (originally seeded from AIQ
   central-quota data).

2. State-name tokens counted as "distinguishing".
   "ASSAM MEDICAL COLLEGE" was matching "Diphu Medical College...Assam"
   because "assam" survived the stopword filter and looked like a
   real shared distinctive word -- but it's just the state name
   showing up in lots of unrelated in-state college names. v4 adds
   every known state/UT name (plus their aliases) into the stopword
   set used for token extraction, so state names never count toward
   the overlap score.

3. No Government vs Private cross-check.
   "Government Medical College, Palakkad" (100 seats) was wrongly
   matched to an unrelated *private* college (-> 150 seats) because
   the correct official entry's name has extra location words
   ("Yakkara") that diluted its similarity score, while the wrong
   private candidate's name was a near-exact textual subset and won
   on raw score. v4 adds a hard gate: if both sides carry a
   Government/Private-style category and they disagree, the candidate
   is disqualified outright, regardless of text score.

Usage:
    python3 merge_nmc_totals_v4.py --dry-run
    python3 merge_nmc_totals_v4.py --apply
"""

import json
import re
import sys
import argparse
import difflib

STOPWORDS = {
    "government", "medical", "college", "institute", "hospital", "of",
    "and", "sciences", "research", "centre", "center", "the", "for",
    "govt", "science", "institution", "dist", "district", "state",
    "new", "national", "university", "regional", "instt"
}

# Indian states/UTs (+ common aliases/spelling variants) -- these show
# up constantly inside college names ("Assam Medical College", "West
# Bengal ... College") without being distinguishing at all, so they're
# folded into the stopword set for token extraction.
STATE_NAME_WORDS = {
    "andhra", "pradesh", "arunachal", "assam", "bihar", "chhattisgarh",
    "chattisgarh", "goa", "gujarat", "haryana", "himachal", "jharkhand",
    "karnataka", "kerala", "madhya", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "orissa", "punjab",
    "rajasthan", "sikkim", "tamil", "nadu", "telangana", "tripura",
    "uttar", "uttarakhand", "uttaranchal", "bengal", "west",
    "andaman", "nicobar", "chandigarh", "dadra", "nagar", "haveli",
    "daman", "diu", "delhi", "jammu", "kashmir", "ladakh",
    "lakshadweep", "puducherry", "pondicherry", "islands"
}
STOPWORDS |= STATE_NAME_WORDS

# Institutes of National Importance -- explicitly excluded from the
# NMC "excluding seats of INIs" source file this script merges from.
# Any college matching these patterns is skipped outright, never
# passed through the matcher.
INI_PATTERNS = [
    r"\baiims\b",
    r"\ball india institute of medical sciences\b",
    r"\bjipmer\b",
    r"\bpgimer\b",
    r"\bnimhans\b",
    r"\bnimhans\b",
    r"\bsctimst\b",
]
INI_RE = re.compile("|".join(INI_PATTERNS), re.IGNORECASE)

def is_ini(name):
    return bool(INI_RE.search(name or ""))

def normalize(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[.,\-&]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def distinctive_tokens(name):
    norm = normalize(name)
    tokens = [t for t in norm.split() if t not in STOPWORDS]
    return set(tokens)

def normalize_state(state):
    if not state:
        return ""
    s = state.lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"\s+", " ", s)
    aliases = {"orissa": "odisha", "pondicherry": "puducherry", "uttaranchal": "uttarakhand"}
    return aliases.get(s, s)

def normalize_mgmt(mgmt):
    """Collapse a management/category field down to 'government',
    'private', or None (unknown / not comparable)."""
    if not mgmt:
        return None
    m = mgmt.lower().strip()
    if any(k in m for k in ("government", "govt", "state", "central", "public")):
        return "government"
    if any(k in m for k in ("private", "trust", "society", "deemed")):
        return "private"
    return None

def score_candidate(target_name, target_tokens, cand_name, cand_tokens):
    overlap = len(target_tokens & cand_tokens)
    union = len(target_tokens | cand_tokens) if (target_tokens or cand_tokens) else 1
    jaccard = overlap / union
    char_score = difflib.SequenceMatcher(None, normalize(target_name), normalize(cand_name)).ratio()
    combined = jaccard * 0.75 + char_score * 0.25
    return combined, overlap

def best_match(college, official_by_state, official_all, threshold):
    name = college.get("name", "")
    state = normalize_state(college.get("state", ""))
    target_tokens = distinctive_tokens(name)
    target_mgmt = normalize_mgmt(college.get("mgmt") or college.get("type") or college.get("category"))

    candidates = official_by_state.get(state, [])
    used_fallback = False
    if not candidates:
        candidates = official_all
        used_fallback = True

    best_score = 0
    best_name = None
    best_overlap = 0
    for cand_name, cand_tokens, cand_mgmt in candidates:
        # HARD GATE: Government/Private mismatch disqualifies a
        # candidate outright, before any scoring happens.
        if target_mgmt and cand_mgmt and target_mgmt != cand_mgmt:
            continue
        score, overlap = score_candidate(name, target_tokens, cand_name, cand_tokens)
        if score > best_score:
            best_score = score
            best_name = cand_name
            best_overlap = overlap

    # HARD GATE: require at least one real shared distinctive word
    # (state names no longer count -- see STATE_NAME_WORDS above).
    if not target_tokens:
        effective_threshold = max(threshold, 0.93)
        if best_score >= effective_threshold:
            return best_name, best_score, used_fallback
        return None, best_score, used_fallback

    if best_overlap == 0:
        return None, best_score, used_fallback

    effective_threshold = threshold if not used_fallback else max(threshold, 0.92)
    if best_score >= effective_threshold:
        return best_name, best_score, used_fallback
    return None, best_score, used_fallback

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data", default="public/data.json")
    parser.add_argument("--official", default="nmc_total_seats_clean.json")
    parser.add_argument("--threshold", type=float, default=0.4)
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        print("Specify --dry-run or --apply")
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(args.official, "r", encoding="utf-8") as f:
        official = json.load(f)

    official_by_state = {}
    official_all = []
    for name, entry in official.items():
        state = normalize_state(entry.get("state", ""))
        tokens = distinctive_tokens(name)
        mgmt = normalize_mgmt(entry.get("mgmt"))
        official_by_state.setdefault(state, []).append((name, tokens, mgmt))
        official_all.append((name, tokens, mgmt))

    colleges = data.get("colleges", [])
    matched = 0
    unmatched = []
    changes = []
    fallback_matches = []
    skipped_ini = []

    for college in colleges:
        name = college.get("name", "")

        if is_ini(name):
            skipped_ini.append(f"{name}  (state: {college.get('state','')}) -- INI, excluded from NMC source, left as-is")
            continue

        official_name, score, used_fallback = best_match(college, official_by_state, official_all, args.threshold)
        if official_name:
            matched += 1
            entry = official[official_name]
            old_total = college.get("totalSeats")
            new_total = entry["totalSeats"]
            if used_fallback:
                fallback_matches.append(f"{name} --> {official_name} (score {score:.3f}, no state match)")
            if old_total != new_total:
                changes.append({
                    "app_name": name,
                    "app_state": college.get("state", ""),
                    "official_name": official_name,
                    "official_state": entry["state"],
                    "score": round(score, 3),
                    "old_total": old_total,
                    "new_total": new_total,
                    "mgmt": entry.get("mgmt"),
                    "used_fallback": used_fallback,
                })
                if args.apply:
                    college["totalSeats"] = new_total
        else:
            unmatched.append(f"{name}  (state: {college.get('state','')}, best score seen: {score:.2f})")

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"Skipped (AIIMS/INI, excluded from NMC source): {len(skipped_ini)}")
    print(f"Matched (state-filtered, overlap-required, mgmt-checked): {matched}")
    print(f"  of which cross-state fallback: {len(fallback_matches)}")
    print(f"Not matched (no reliable overlap found): {len(unmatched)}")
    print(f"totalSeats changes to apply: {len(changes)}")

    print(f"\n=== ALL CHANGES ===")
    for c in changes:
        flag = "  ⚠️ FALLBACK" if c["used_fallback"] else ""
        print(f"\n{c['app_name']} [{c['app_state']}]  -->  {c['official_name']} [{c['official_state']}]  (score {c['score']}){flag}")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")

    if skipped_ini:
        print(f"\n=== SKIPPED (AIIMS/INI) ===")
        for s in skipped_ini:
            print(s)

    with open("v4_nmc_unmatched.txt", "w") as f:
        f.write("\n".join(unmatched))
    with open("v4_nmc_changes.json", "w") as f:
        json.dump(changes, f, indent=2)
    with open("v4_nmc_fallback_matches.txt", "w") as f:
        f.write("\n".join(fallback_matches))
    with open("v4_nmc_skipped_ini.txt", "w") as f:
        f.write("\n".join(skipped_ini))

    print(f"\nWrote v4_nmc_unmatched.txt, v4_nmc_changes.json, v4_nmc_fallback_matches.txt, v4_nmc_skipped_ini.txt")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} totalSeats corrections to {args.data}")
    else:
        print(f"\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
