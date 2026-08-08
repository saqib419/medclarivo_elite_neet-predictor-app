import data from "../../public/data.json" with { type: "json" };
import { slugify } from "../../src/lib/predictor.js";

// GET /api/colleges/:slug
export default function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { slug } = req.query;
  const college = data.colleges.find((c) => slugify(c.name) === slug);

  if (!college) {
    return res.status(404).json({ error: "College not found" });
  }

  res.setHeader("Cache-Control", "public, max-age=300, stale-while-revalidate=600");
  return res.status(200).json({ college: { ...college, slug: slugify(college.name) } });
}
