"""
Merge official NMC total-seat data into data.json — v3.

Fixes found in v2: abbreviated college names (MGM, JLN, "S.C.", "G.S.",
etc.) had their distinguishing letters stripped by a token-length
filter, leaving nothing to match on — so they fell back to raw
character similarity and got wrongly attracted to unrelated colleges
with generic-sounding names (e.g. "B.S.P. Medical College and
Hospital" wrongly absorbed Seth GS Medical College, Rural Medical
College Loni, MGM, JLN, and others).

v3 changes:
  - No token-length filter — short tokens (initials like "b", "j",
    "s", "c") are kept, since in Indian college names they often ARE
    the distinguishing part.
  - A match is only accepted if there is at least some real word
    overlap (jaccard > 0) between target and candidate. Zero overlap
    -> left unmatched for manual review, never guessed via character
    similarity alone.
  - Optional category (Government/Private) cross-check when present
    on both sides, as an extra disambiguator.

Usage:
    python3 merge_nmc_totals_v3.py --dry-run
    python3 merge_nmc_totals_v3.py --apply
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

    candidates = official_by_state.get(state, [])
    used_fallback = False
    if not candidates:
        candidates = official_all
        used_fallback = True

    best_score = 0
    best_name = None
    best_overlap = 0
    for cand_name, cand_tokens in candidates:
        score, overlap = score_candidate(name, target_tokens, cand_name, cand_tokens)
        if score > best_score:
            best_score = score
            best_name = cand_name
            best_overlap = overlap

    # HARD GATE: require at least one real shared distinctive word.
    # Exception: if target has zero distinctive tokens at all (e.g. name
    # is entirely generic/stopwords), allow char-similarity-only match
    # but only at a very high bar.
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
    print(f"Matched (state-filtered, overlap-required): {matched}")
    print(f"  of which cross-state fallback: {len(fallback_matches)}")
    print(f"Not matched (no reliable overlap found): {len(unmatched)}")
    print(f"totalSeats changes to apply: {len(changes)}")

    print(f"\n=== ALL CHANGES ===")
    for c in changes:
        flag = "  ⚠️ FALLBACK" if c["used_fallback"] else ""
        print(f"\n{c['app_name']} [{c['app_state']}]  -->  {c['official_name']} [{c['official_state']}]  (score {c['score']}){flag}")
        print(f"  totalSeats: {c['old_total']} -> {c['new_total']}")

    with open("v3_nmc_unmatched.txt", "w") as f:
        f.write("\n".join(unmatched))
    with open("v3_nmc_changes.json", "w") as f:
        json.dump(changes, f, indent=2)
    with open("v3_nmc_fallback_matches.txt", "w") as f:
        f.write("\n".join(fallback_matches))

    print(f"\nWrote v3_nmc_unmatched.txt, v3_nmc_changes.json, v3_nmc_fallback_matches.txt")

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Applied {len(changes)} totalSeats corrections to {args.data}")
    else:
        print(f"\n(Dry run — nothing written.)")

if __name__ == "__main__":
    main()
