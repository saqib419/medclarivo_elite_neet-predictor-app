"""
Merge official NMC total-seat data into data.json — STATE-FILTERED VERSION.

Fixes a real problem found in v1: pure character-similarity matching
(difflib) can confidently match two totally different colleges that
happen to share generic words like "Government Medical College and
Hospital" (e.g. Chandigarh matched to Balangir, Odisha — wrong state,
wrong college). This version:

  1. Filters candidates to the SAME STATE first (using data.json's own
     "state" field) — this alone kills most false positives.
  2. Scores remaining same-state candidates using DISTINCTIVE token
     overlap (ignoring generic words like "government", "medical",
     "college", "institute", "hospital", "of", "and", "sciences",
     "research", "centre") rather than raw character similarity.
  3. Falls back to char-similarity only as a tiebreaker within the
     same state.
  4. Anything that can't be confidently matched within its own state
     is left unmatched and reported — NOT guessed.

Usage:
    python3 merge_nmc_totals_v2.py --dry-run
    python3 merge_nmc_totals_v2.py --apply
"""

import json
import re
import sys
import argparse
import difflib

STOPWORDS = {
    "government", "medical", "college", "institute", "hospital", "of",
    "and", "sciences", "research", "centre", "center", "the", "for",
    "govt", "science", "institution", "&", "dist", "district", "state",
    "new", "national", "university", "regional", "instt"
}

def normalize(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[.,\-&]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def distinctive_tokens(name):
    norm = normalize(name)
    tokens = [t for t in norm.split() if t not in STOPWORDS and len(t) > 2]
    return set(tokens)

def normalize_state(state):
    if not state:
        return ""
    s = state.lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"\s+", " ", s)
    # a few common aliasing fixes
    aliases = {
        "orissa": "odisha",
        "pondicherry": "puducherry",
        "uttaranchal": "uttarakhand",
    }
    return aliases.get(s, s)

def score_candidate(target_name, target_tokens, cand_name, cand_tokens):
    if not target_tokens or not cand_tokens:
        char_score = difflib.SequenceMatcher(None, normalize(target_name), normalize(cand_name)).ratio()
        return char_score
    overlap = len(target_tokens & cand_tokens)
    union = len(target_tokens | cand_tokens)
    jaccard = overlap / union if union else 0
    char_score = difflib.SequenceMatcher(None, normalize(target_name), normalize(cand_name)).ratio()
    # weight token overlap heavily, char similarity as tiebreaker
    return jaccard * 0.75 + char_score * 0.25

def best_match(college, official_by_state, official_all, threshold):
    name = college.get("name", "")
    state = normalize_state(college.get("state", ""))
    target_tokens = distinctive_tokens(name)

    candidates = official_by_state.get(state, [])
    used_fallback = False
    if not candidates:
        # no state on the app side, or state didn't match any official entry —
        # fall back to searching everything, but require a much higher bar
        candidates = official_all
        used_fallback = True

    best_score = 0
    best_name = None
    for cand_name, cand_tokens in candidates:
        score = score_candidate(name, target_tokens, cand_name, cand_tokens)
        if score > best_score:
            best_score = score
            best_name = cand_name

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
    parser.add_argument("--threshold", type=float, default=0.55)
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        print("Specify --dry-run or --apply")
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(args.official, "r", encoding="utf-8") as f:
        official = json.load(f)

    # index official colleges by normalized state
    official_by_state = {}
    official_all = []
    for name, entry in official.items():
        state = normalize_state(entry.get("state", ""))
        tokens = distinctive_tokens(name)
        official_by_state.setdefault(state, []).append((name, tokens))
        official_all.append((name, tokens))

    colleges = data.get("colleges", [])
    matched = 0
    unmatched = []
    changes = []
    fallback_matches = []

    for college in colleges:
        name = college.get("name", "")
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
                    "mgmt": entry["mgmt"],
                    "used_fallback": used_fallback,
                })
                if args.apply:
                    college["totalSeats"] = new_total
        else:
            unmatched.append(f"{name}  (state: {college.get('state','')}, best score seen: {score:.2f})")

    print(f"\n=== SUMMARY ===")
    print(f"Total colleges in data.json: {len(colleges)}")
    print(f"Matched (state-filtered, token-aware): {matched}")
    print(f"  of which matched via cross-state fallback (double-check these!): {len(fallback_matches)}")
    print(f"Not matched: {len(unmatched)}")
    print(f"totalSeats changes to apply: {len(changes)}")

    print(f"\n=== ALL CHANGES ===")
    for c in changes:
        flag = "  ⚠️ FALLBACK (no state match)" if c["used_fallback"] else ""
        print(f"\n{c['app_name']} [{c['app_state']}]  -->  {c['official_name']} [{c['official_state']}]  (score {c['score']}){flag}")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")

    with open("v2_nmc_unmatched.txt", "w") as f:
        f.write("\n".join(unmatched))
    with open("v2_nmc_changes.json", "w") as f:
        json.dump(changes, f, indent=2)
    with open("v2_nmc_fallback_matches.txt", "w") as f:
        f.write("\n".join(fallback_matches))

    print(f"\nWrote v2_nmc_unmatched.txt, v2_nmc_changes.json, v2_nmc_fallback_matches.txt")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} totalSeats corrections to {args.data}")
    else:
        print(f"\n(Dry run — nothing written. Check v2_nmc_fallback_matches.txt especially closely.)")

if __name__ == "__main__":
    main()
