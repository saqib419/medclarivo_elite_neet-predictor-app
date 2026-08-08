import data from "../public/data.json" with { type: "json" };
import { slugify } from "../src/lib/predictor.js";

// GET /api/colleges
// GET /api/colleges?state=Delhi&category=General&q=aiims
export default function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { state, category, q } = req.query;

  let colleges = data.colleges.map((c) => ({ ...c, slug: slugify(c.name) }));

  if (state) {
    colleges = colleges.filter((c) => c.quota === "AIQ" || c.state === state);
  }
  if (q) {
    const needle = String(q).toLowerCase();
    colleges = colleges.filter((c) =>
      c.name.toLowerCase().includes(needle) || (c.state || "").toLowerCase().includes(needle)
    );
  }
  if (category) {
    colleges = colleges
      .filter((c) => c.cutoffs[category] != null)
      .map((c) => ({ ...c, cutoff: c.cutoffs[category] }))
      .sort((a, b) => a.cutoff - b.cutoff);
  }

  res.setHeader("Cache-Control", "public, max-age=300, stale-while-revalidate=600");
  return res.status(200).json({ count: colleges.length, colleges });
}
