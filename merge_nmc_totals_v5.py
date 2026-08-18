"""
Merge official NMC total-seat data into data.json — v5.

New bugs found in v4's dry-run that this version fixes:

1. Generic/common-surname single-token false matches.
   "Dr. DY Patil Medical College" matched "Dr. Ulhas Patil Medical
   College, Jalgaon" (score 0.469) purely because both contain
   "patil" -- a very common Maharashtrian surname, not a real
   identifier. Same pattern: "DR.S.N. MEDICAL COLLEGE" -> "Dr S S
   Tantia Medical College" (score 0.52, only "dr" overlapping after
   normalization). v5 adds a GENERIC_TOKENS set (common Indian
   surnames/titles that show up across many unrelated college names:
   patil, reddy, singh, gandhi, nehru, rao, sharma, dr, shri, etc.).
   If the overlap between target and candidate is ENTIRELY generic
   tokens (no non-generic word shared), the match is held to a much
   higher threshold (0.85) instead of the normal one.

2. Duplicate-target collisions.
   "Malla Reddy Institute of Medical Sciences" and "Malla Reddy
   Medical College for Women" both resolved to the same official
   record ("Malla Reddy Institute of Medical Sciences, Hyderabad") --
   they are different campuses and can't both be right. v5 tracks
   which official record each app college maps to; if more than one
   app college maps to the same official record, ALL of them are
   pulled out of "changes" and into a separate
   v5_nmc_duplicate_targets.txt for manual review, instead of
   silently applying a guess to either.

Usage:
    python3 merge_nmc_totals_v5.py --dry-run
    python3 merge_nmc_totals_v5.py --apply
"""

import json
import re
import sys
import argparse
import difflib
from collections import defaultdict

STOPWORDS = {
    "government", "medical", "college", "institute", "hospital", "of",
    "and", "sciences", "research", "centre", "center", "the", "for",
    "govt", "science", "institution", "dist", "district", "state",
    "new", "national", "university", "regional", "instt"
}

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

# Common Indian surnames/titles/honorifics that recur across dozens of
# UNRELATED college names. A shared word from this set is not, by
# itself, good evidence two names refer to the same college -- it
# only counts toward the ordinary threshold when paired with at least
# one non-generic shared word; on its own it requires a much higher
# bar (see GENERIC_ONLY_THRESHOLD below).
GENERIC_TOKENS = {
    "dr", "shri", "smt", "pt", "sri", "shree",
    "patil", "reddy", "singh", "gandhi", "nehru", "rao", "sharma",
    "kumar", "prasad", "verma", "gupta", "yadav", "mishra", "das",
    "sen", "roy", "chandra", "lal", "devi", "bai", "raj", "kiran",
    "acharya", "azad", "bose", "chatterjee", "chandran",
}

GENERIC_ONLY_THRESHOLD = 0.85

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
    if not mgmt:
        return None
    m = mgmt.lower().strip()
    if any(k in m for k in ("government", "govt", "state", "central", "public")):
        return "government"
    if any(k in m for k in ("private", "trust", "society", "deemed")):
        return "private"
    return None

def score_candidate(target_name, target_tokens, cand_name, cand_tokens):
    overlap_set = target_tokens & cand_tokens
    overlap = len(overlap_set)
    union = len(target_tokens | cand_tokens) if (target_tokens or cand_tokens) else 1
    jaccard = overlap / union
    char_score = difflib.SequenceMatcher(None, normalize(target_name), normalize(cand_name)).ratio()
    combined = jaccard * 0.75 + char_score * 0.25
    non_generic_overlap = overlap_set - GENERIC_TOKENS
    return combined, overlap, len(non_generic_overlap)

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
    best_non_generic = 0
    for cand_name, cand_tokens, cand_mgmt in candidates:
        if target_mgmt and cand_mgmt and target_mgmt != cand_mgmt:
            continue
        score, overlap, non_generic = score_candidate(name, target_tokens, cand_name, cand_tokens)
        if score > best_score:
            best_score = score
            best_name = cand_name
            best_overlap = overlap
            best_non_generic = non_generic

    if not target_tokens:
        effective_threshold = max(threshold, 0.93)
        if best_score >= effective_threshold:
            return best_name, best_score, used_fallback, "empty-target-high-bar"
        return None, best_score, used_fallback, None

    if best_overlap == 0:
        return None, best_score, used_fallback, None

    # GENERIC-ONLY GATE: if every shared word is a generic
    # surname/title, demand a much higher score.
    if best_non_generic == 0:
        if best_score >= GENERIC_ONLY_THRESHOLD:
            return best_name, best_score, used_fallback, "generic-only-high-bar"
        return None, best_score, used_fallback, None

    effective_threshold = threshold if not used_fallback else max(threshold, 0.92)
    if best_score >= effective_threshold:
        return best_name, best_score, used_fallback, "normal"
    return None, best_score, used_fallback, None

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
    skipped_ini = []
    unmatched = []
    already_correct = 0

    # First pass: figure out every college's proposed match (if any),
    # without applying anything, so we can detect duplicate targets.
    proposals = []  # list of dicts
    target_to_apps = defaultdict(list)  # official_name -> [app names]

    for college in colleges:
        name = college.get("name", "")
        if is_ini(name):
            skipped_ini.append(f"{name}  (state: {college.get('state','')}) -- INI, excluded from NMC source, left as-is")
            continue

        official_name, score, used_fallback, reason = best_match(college, official_by_state, official_all, args.threshold)
        if not official_name:
            unmatched.append(f"{name}  (state: {college.get('state','')}, best score seen: {score:.2f})")
            continue

        entry = official[official_name]
        old_total = college.get("totalSeats")
        new_total = entry["totalSeats"]

        proposals.append({
            "college_obj": college,
            "app_name": name,
            "app_state": college.get("state", ""),
            "official_name": official_name,
            "official_state": entry["state"],
            "score": round(score, 3),
            "old_total": old_total,
            "new_total": new_total,
            "mgmt": entry.get("mgmt"),
            "used_fallback": used_fallback,
            "reason": reason,
        })
        target_to_apps[official_name].append(name)

        if old_total == new_total:
            already_correct += 1

    # Second pass: split proposals into clean changes vs duplicate-target conflicts.
    changes = []
    duplicate_conflicts = []
    for p in proposals:
        if len(target_to_apps[p["official_name"]]) > 1:
            duplicate_conflicts.append(p)
            continue
        if p["old_total"] != p["new_total"]:
            changes.append(p)
            if args.apply:
                p["college_obj"]["totalSeats"] = p["new_total"]

    matched_clean = len(proposals) - len(duplicate_conflicts)

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"Skipped (AIIMS/INI, excluded from NMC source): {len(skipped_ini)}")
    print(f"Matched cleanly (single target, mgmt-checked): {matched_clean}")
    print(f"  already correct (no change needed): {already_correct - sum(1 for p in duplicate_conflicts if p['old_total']==p['new_total'])}")
    print(f"  totalSeats changes to apply: {len(changes)}")
    print(f"Held for manual review (duplicate target -- 2+ app colleges -> same official record): {len(duplicate_conflicts)}")
    print(f"Not matched at all (no reliable overlap / below threshold): {len(unmatched)}")

    print(f"\n=== CHANGES ===")
    for c in changes:
        flag = "  ⚠️ FALLBACK" if c["used_fallback"] else ""
        flag += "  ⚠️ GENERIC-ONLY" if c["reason"] == "generic-only-high-bar" else ""
        print(f"\n{c['app_name']} [{c['app_state']}]  -->  {c['official_name']} [{c['official_state']}]  (score {c['score']}){flag}")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")

    print(f"\n=== DUPLICATE-TARGET CONFLICTS (not applied, needs manual pick) ===")
    seen_targets = set()
    for official_name, app_names in target_to_apps.items():
        if len(app_names) > 1 and official_name not in seen_targets:
            seen_targets.add(official_name)
            print(f"\nOfficial record: {official_name}")
            for an in app_names:
                print(f"  <- {an}")

    with open("v5_nmc_unmatched.txt", "w") as f:
        f.write("\n".join(unmatched))
    with open("v5_nmc_changes.json", "w") as f:
        json.dump(changes, f, indent=2, default=str)
    with open("v5_nmc_duplicate_targets.txt", "w") as f:
        for official_name, app_names in target_to_apps.items():
            if len(app_names) > 1:
                f.write(f"Official record: {official_name}\n")
                for an in app_names:
                    f.write(f"  <- {an}\n")
                f.write("\n")
    with open("v5_nmc_skipped_ini.txt", "w") as f:
        f.write("\n".join(skipped_ini))

    print(f"\nWrote v5_nmc_unmatched.txt, v5_nmc_changes.json, v5_nmc_duplicate_targets.txt, v5_nmc_skipped_ini.txt")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} totalSeats corrections to {args.data}")
    else:
        print(f"\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
