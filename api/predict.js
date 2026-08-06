import data from "../public/data.json";
import { estimateRank, computeMatches, CATEGORIES, slugify } from "../src/lib/predictor.js";

// POST /api/predict  { score: number, category: string, state?: string }
// -> { rank, matches: [...] }
export default function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const body = typeof req.body === "string" ? safeParse(req.body) : req.body || {};
  const { score, category, state } = body;

  const numScore = Number(score);
  if (!Number.isFinite(numScore) || numScore < 0 || numScore > 720) {
    return res.status(400).json({ error: "score must be a number between 0 and 720" });
  }
  if (!CATEGORIES.includes(category)) {
    return res.status(400).json({ error: `category must be one of: ${CATEGORIES.join(", ")}` });
  }

  const rank = estimateRank(numScore, data.scoreRankTable);
  const matches = computeMatches(data.colleges, rank, category, state).map((c) => ({
    ...c,
    slug: slugify(c.name),
  }));

  return res.status(200).json({
    score: numScore,
    category,
    state: state || null,
    rank,
    matchCount: matches.length,
    matches,
  });
}

function safeParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return {};
  }
}
