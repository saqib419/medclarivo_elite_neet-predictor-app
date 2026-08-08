import { estimateRank, estimateRankRange, computeChanceSummary, slugify } from "./predictor.js";

let cachedData = null;
async function loadLocalData() {
  if (cachedData) return cachedData;
  const res = await fetch("/data.json");
  cachedData = await res.json();
  return cachedData;
}

async function tryApi(path, options) {
  try {
    const res = await fetch(path, options);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchColleges({ state, category, q } = {}) {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  if (category) params.set("category", category);
  if (q) params.set("q", q);
  const qs = params.toString();

  const viaApi = await tryApi(`/api/colleges${qs ? `?${qs}` : ""}`);
  if (viaApi) return viaApi.colleges;

  const data = await loadLocalData();
  let colleges = data.colleges.map((c) => ({ ...c, slug: slugify(c.name) }));
  if (state) colleges = colleges.filter((c) => c.quota === "AIQ" || c.state === state);
  if (q) {
    const needle = q.toLowerCase();
    colleges = colleges.filter((c) => c.name.toLowerCase().includes(needle));
  }
  if (category) {
    colleges = colleges
      .filter((c) => c.cutoffs[category] != null)
      .map((c) => ({ ...c, cutoff: c.cutoffs[category] }))
      .sort((a, b) => a.cutoff - b.cutoff);
  }
  return colleges;
}

export async function fetchCollegeBySlug(slug) {
  const viaApi = await tryApi(`/api/colleges/${slug}`);
  if (viaApi) return viaApi.college;

  const data = await loadLocalData();
  const college = data.colleges.find((c) => slugify(c.name) === slug);
  return college ? { ...college, slug: slugify(college.name) } : null;
}

export async function predict({ score, category, state, quota }) {
  const viaApi = await tryApi("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ score, category, state, quota }),
  });
  if (viaApi) return viaApi;

  const data = await loadLocalData();
  const rank = estimateRank(Number(score), data.scoreRankTable);
  const rankRange = estimateRankRange(Number(score), data.scoreRankTable);
  const summary = computeChanceSummary(data.colleges, rank, category, state, quota);
  return { score: Number(score), category, state: state || null, quota: quota || null, rank, rankRange, ...summary };
}
