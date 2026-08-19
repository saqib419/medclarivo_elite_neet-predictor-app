"""
Merge official NMC total-seat data into data.json — v8.

Builds on v7. Fixes one confirmed false match that slipped through v7's
generic-token gate:

    DR.S.N. MEDICAL COLLEGE [Rajasthan]
      --> Dr S S Tantia Medical College Hospital & Research Centre [Rajasthan]
      (score 0.52)

Root cause: normalize() splits "S.N." into two separate single-character
tokens, "s" and "n". The generic-token gate (GENERIC_TOKENS) was meant to
require a much higher score when the only overlapping tokens are common/
generic ones (surnames, honorifics, etc.) -- but a lone single-letter
token like "s" was being treated as a normal "non-generic" distinguishing
token, so a single accidental "s" overlap with "Tantia" let the match
through at the ordinary 0.4 threshold instead of the 0.85 generic-only
bar.

The fix has to preserve legitimate initials-based matches, e.g.:
    S.N. MEDICAL COLLEGE            --> S N Medical College, Agra
    M.G.M. MEDICAL COLLEGE          --> M G M Medical College
these genuinely rely on multiple single-letter tokens overlapping
together (s+n, or m+g+m). So the rule v8 adds is:

    A single-letter token only counts as "real" (non-generic) evidence
    if AT LEAST ONE OTHER single-letter token from the same name also
    overlaps with the candidate. A lone single-letter overlap by itself
    (no partner) is treated the same as a generic-token overlap and is
    held to the GENERIC_ONLY_THRESHOLD bar instead of the normal
    threshold.

Everything else (Malla Reddy conflict handling via
DISTINGUISHING_SUFFIX_WORDS, Zoram-style duplicate-row merging, the
missing-college report) is unchanged from v7.

Usage:
    python3 merge_nmc_totals_v8.py --dry-run
    python3 merge_nmc_totals_v8.py --apply
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

GENERIC_TOKENS = {
    "dr", "shri", "smt", "pt", "sri", "shree",
    "patil", "reddy", "singh", "gandhi", "nehru", "rao", "sharma",
    "kumar", "prasad", "verma", "gupta", "yadav", "mishra", "das",
    "sen", "roy", "chandra", "lal", "devi", "bai", "raj", "kiran",
    "acharya", "azad", "bose", "chatterjee", "chandran",
}

GENERIC_ONLY_THRESHOLD = 0.85

DUPLICATE_ROW_THRESHOLD = 0.60

DISTINGUISHING_SUFFIX_WORDS = {
    "women", "men", "boys", "girls", "ladies",
    "campus", "unit", "branch", "annex", "annexe", "wing",
    "north", "south", "east", "west",
}

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

def name_similarity(a, b):
    na, nb = normalize(a).replace(" and ", " "), normalize(b).replace(" and ", " ")
    ta, tb = distinctive_tokens(a), distinctive_tokens(b)
    union = len(ta | tb) if (ta or tb) else 1
    jaccard = len(ta & tb) / union
    char_score = difflib.SequenceMatcher(None, na, nb).ratio()
    return jaccard * 0.6 + char_score * 0.4

def score_candidate(target_name, target_tokens, cand_name, cand_tokens):
    """
    v8 change: overlapping tokens that are a SINGLE LETTER count as
    "real" (non-generic) evidence only if at least one other
    single-letter token from target_tokens ALSO overlaps with
    cand_tokens. A lone single-letter overlap (no partner) is folded
    into the generic set instead, so it can't singlehandedly clear the
    normal threshold -- it needs the GENERIC_ONLY_THRESHOLD bar like
    any other generic-only overlap (e.g. a bare "dr" or surname match).
    This keeps S.N.->S N Medical College and M.G.M.->M G M Medical
    College working (2+ single-letter tokens overlap together), while
    killing DR.S.N.->...Tantia... (only "s" overlaps, "n" does not).
    """
    overlap_set = target_tokens & cand_tokens
    overlap = len(overlap_set)
    union = len(target_tokens | cand_tokens) if (target_tokens or cand_tokens) else 1
    jaccard = overlap / union
    char_score = difflib.SequenceMatcher(None, normalize(target_name), normalize(cand_name)).ratio()
    combined = jaccard * 0.75 + char_score * 0.25

    single_letter_overlap = {t for t in overlap_set if len(t) == 1}
    multi_letter_non_generic_overlap = (overlap_set - GENERIC_TOKENS) - single_letter_overlap

    if len(single_letter_overlap) >= 2:
        # 2+ single-letter tokens overlapping together (e.g. s + n,
        # or m + g + m) counts as real, paired initials evidence.
        real_single_letter_overlap = single_letter_overlap
    else:
        # 0 or 1 single-letter token overlapping alone -- not
        # trustworthy on its own, treat as generic/no evidence.
        real_single_letter_overlap = set()

    non_generic_overlap = multi_letter_non_generic_overlap | real_single_letter_overlap
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

    if best_non_generic == 0:
        if best_score >= GENERIC_ONLY_THRESHOLD:
            return best_name, best_score, used_fallback, "generic-only-high-bar"
        return None, best_score, used_fallback, None

    effective_threshold = threshold if not used_fallback else max(threshold, 0.92)
    if best_score >= effective_threshold:
        return best_name, best_score, used_fallback, "normal"
    return None, best_score, used_fallback, None

def has_distinguishing_mismatch(app_names):
    per_name_words = []
    for n in app_names:
        words = distinctive_tokens(n) & DISTINGUISHING_SUFFIX_WORDS
        per_name_words.append(words)
    all_words = set().union(*per_name_words) if per_name_words else set()
    for w in all_words:
        present = [w in words for words in per_name_words]
        if any(present) and not all(present):
            return True
    return False

def group_is_duplicate_rows(app_names):
    if len(app_names) < 2:
        return True
    if has_distinguishing_mismatch(app_names):
        return False
    for i in range(len(app_names)):
        for j in range(i + 1, len(app_names)):
            if name_similarity(app_names[i], app_names[j]) < DUPLICATE_ROW_THRESHOLD:
                return False
    return True

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

    proposals = []
    target_to_apps = defaultdict(list)

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

    duplicate_row_targets = set()
    genuine_conflict_targets = set()
    for official_name, app_names in target_to_apps.items():
        if len(app_names) <= 1:
            continue
        if group_is_duplicate_rows(app_names):
            duplicate_row_targets.add(official_name)
        else:
            genuine_conflict_targets.add(official_name)

    changes = []
    duplicate_row_applied = []
    already_correct = 0
    for p in proposals:
        tgt = p["official_name"]
        if tgt in genuine_conflict_targets:
            continue

        if tgt in duplicate_row_targets:
            duplicate_row_applied.append(p)

        if p["old_total"] == p["new_total"]:
            already_correct += 1
            continue

        changes.append(p)
        if args.apply:
            p["college_obj"]["totalSeats"] = p["new_total"]

    genuine_conflict_apps = sum(len(target_to_apps[t]) for t in genuine_conflict_targets)
    matched_clean = len(proposals) - genuine_conflict_apps

    matched_official_names = {p["official_name"] for p in proposals}
    missing = []
    for name, entry in official.items():
        if name not in matched_official_names:
            missing.append({
                "name": name,
                "state": entry.get("state", ""),
                "mgmt": entry.get("mgmt", ""),
                "totalSeats": entry.get("totalSeats"),
            })

    print(f"\n=== SUMMARY (v8) ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"Skipped (AIIMS/INI, excluded from NMC source): {len(skipped_ini)}")
    print(f"Matched cleanly (incl. duplicate-row groups): {matched_clean}")
    print(f"  already correct (no change needed): {already_correct}")
    print(f"  totalSeats changes to apply: {len(changes)}")
    print(f"  of which are duplicate-row corrections (same college, multiple rows): {len(duplicate_row_applied)}")
    print(f"Held for manual review (genuine duplicate-target conflict): {genuine_conflict_apps}")
    print(f"Not matched at all (no reliable overlap / below threshold): {len(unmatched)}")
    print(f"Official NMC colleges with NO match in data.json (missing from app): {len(missing)}")

    print(f"\n=== CHANGES ===")
    for c in changes:
        flag = "  ⚠️ FALLBACK" if c["used_fallback"] else ""
        flag += "  ⚠️ GENERIC-ONLY" if c["reason"] == "generic-only-high-bar" else ""
        flag += "  🔁 DUPLICATE-ROW" if c["official_name"] in duplicate_row_targets else ""
        print(f"\n{c['app_name']} [{c['app_state']}]  -->  {c['official_name']} [{c['official_state']}]  (score {c['score']}){flag}")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")

    print(f"\n=== GENUINE DUPLICATE-TARGET CONFLICTS (not applied, needs manual pick) ===")
    for official_name in genuine_conflict_targets:
        print(f"\nOfficial record: {official_name}")
        for an in target_to_apps[official_name]:
            print(f"  <- {an}")

    print(f"\n=== DUPLICATE ROWS DETECTED (corrected, please verify/merge rows later) ===")
    for official_name in duplicate_row_targets:
        print(f"\nOfficial record: {official_name}")
        for an in target_to_apps[official_name]:
            print(f"  <- {an}")

    with open("v8_nmc_unmatched.txt", "w") as f:
        f.write("\n".join(unmatched))
    with open("v8_nmc_changes.json", "w") as f:
        json.dump(changes, f, indent=2, default=str)
    with open("v8_nmc_duplicate_targets.txt", "w") as f:
        for official_name in genuine_conflict_targets:
            f.write(f"Official record: {official_name}\n")
            for an in target_to_apps[official_name]:
                f.write(f"  <- {an}\n")
            f.write("\n")
    with open("v8_nmc_duplicate_rows.txt", "w") as f:
        for official_name in duplicate_row_targets:
            f.write(f"Official record: {official_name}\n")
            for an in target_to_apps[official_name]:
                f.write(f"  <- {an}\n")
            f.write("\n")
    with open("v8_nmc_skipped_ini.txt", "w") as f:
        f.write("\n".join(skipped_ini))
    with open("v8_nmc_missing_from_app.json", "w") as f:
        json.dump(missing, f, indent=2, default=str)

    print(f"\nWrote v8_nmc_unmatched.txt, v8_nmc_changes.json, v8_nmc_duplicate_targets.txt,")
    print(f"v8_nmc_duplicate_rows.txt, v8_nmc_skipped_ini.txt, v8_nmc_missing_from_app.json")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} totalSeats corrections to {args.data}")
    else:
        print(f"\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
