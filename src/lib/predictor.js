// Shared rank-estimation + college-matching logic.
// Mirrors api/_lib/predictor.js on the server so the client can
// compute instantly and the API can verify/recompute the same way.

export const CATEGORIES = ["General", "EWS", "OBC", "SC", "ST", "PwD"];

export const STATES = [
  "All-India only",
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
  "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
  "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
  "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Delhi",
  "Jammu and Kashmir", "Ladakh", "Puducherry",
];

export function estimateRank(score, table) {
  if (score >= table[0][0]) return table[0][1];
  for (let i = 0; i < table.length - 1; i++) {
    const [s1, r1] = table[i];
    const [s2, r2] = table[i + 1];
    if (score <= s1 && score >= s2) {
      const t = (s1 - score) / (s1 - s2 || 1);
      return Math.round(r1 + t * (r2 - r1));
    }
  }
  return table[table.length - 1][1];
}

export function likelihood(rank, cutoff) {
  if (rank <= cutoff * 0.7) return { label: "High", tone: "high" };
  if (rank <= cutoff) return { label: "Likely", tone: "high" };
  if (rank <= cutoff * 1.3) return { label: "Moderate", tone: "moderate" };
  return { label: "Low", tone: "low" };
}

export function fmt(n) {
  return Number(n).toLocaleString("en-IN");
}

/**
 * Computes the sorted list of matching colleges for a rank/category/state.
 * `state` may be "All-India only" or empty to mean AIQ-only.
 */
export function computeMatches(colleges, rank, category, state) {
  return colleges
    .filter((c) => c.quota === "AIQ" || c.state === state)
    .map((c) => ({
      ...c,
      cutoff: c.cutoffs[category],
      like: likelihood(rank, c.cutoffs[category]),
    }))
    .sort((a, b) => a.cutoff - b.cutoff);
}

export function slugify(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}
