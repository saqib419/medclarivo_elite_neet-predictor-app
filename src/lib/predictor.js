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

// Leftover counselling-status strings that got scraped in as if they were colleges.
const JUNK_NAME_PATTERN = /^(did not|not allotted|no upgradation|upgraded\s*\(|fresh allotted)/i;

export function cleanColleges(colleges) {
  return colleges.filter((c) => !JUNK_NAME_PATTERN.test(c.name.trim()));
}

/**
 * Aggregates chances across all eligible colleges without exposing
 * individual college names — just counts per tier plus a headline.
 */
export function computeChanceSummary(colleges, rank, category, state, quota = "Both") {
  const eligible = cleanColleges(colleges)
    .filter((c) => {
      if (quota === "All India Quota") return c.quota === "AIQ";
      if (quota === "State Quota") return c.quota === "State" && c.state === state;
      return c.quota === "AIQ" || (c.quota === "State" && c.state === state);
    })
    .filter((c) => c.cutoffs[category] != null);

  const counts = { High: 0, Likely: 0, Moderate: 0, Low: 0 };
  for (const c of eligible) {
    counts[likelihood(rank, c.cutoffs[category]).label] += 1;
  }

  const inReach = counts.High + counts.Likely + counts.Moderate;
  const strongRatio = eligible.length > 0 ? (counts.High + counts.Likely) / eligible.length : 0;
  const reachRatio = eligible.length > 0 ? inReach / eligible.length : 0;

  const headline =
    strongRatio >= 0.5
      ? "Strong chance of a seat"
      : reachRatio >= 0.5
      ? "Moderate chance of a seat"
      : inReach > 0
      ? "Low chance of a seat"
      : "Very low chance with current filters";

  return { totalColleges: eligible.length, counts, inReach, headline };
}

export function slugify(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}
