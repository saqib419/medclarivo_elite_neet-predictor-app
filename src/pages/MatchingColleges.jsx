import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { SlidersHorizontal } from "lucide-react";
import { CATEGORIES } from "../lib/predictor.js";
import { predict } from "../lib/api.js";

function useQueryParams() {
  const { search } = useLocation();
  return new URLSearchParams(search);
}

export default function MatchingColleges() {
  const navigate = useNavigate();
  const location = useLocation();
  const qp = useQueryParams();

  const initial =
    location.state ||
    (qp.get("score")
      ? { score: Number(qp.get("score")), category: qp.get("category"), state: qp.get("state"), quota: qp.get("quota") }
      : null);

  const [params] = useState(initial);
  const [category, setCategory] = useState(initial?.category);
  const [showFilter, setShowFilter] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!params) return;
    (async () => {
      const r = await predict({ score: params.score, category, state: params.state, quota: params.quota });
      setResult(r);
    })();
  }, [params, category]);

  if (!params) {
    return (
      <div className="max-w-app mx-auto px-4 sm:px-gutter py-10 text-center">
        <p className="text-on-surface-variant">No prediction data yet.</p>
        <button
          onClick={() => navigate("/predict")}
          className="mt-4 px-5 py-2.5 rounded bg-primary text-on-primary text-sm font-semibold"
        >
          Run a Prediction
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-app mx-auto px-4 sm:px-gutter py-6">
      <h1 className="font-display font-semibold text-2xl text-on-surface">Prediction Results</h1>
      <p className="text-on-surface-variant text-sm mt-1">
        Based on your score of <span className="font-semibold text-on-surface">{params.score}</span> and category{" "}
        <span className="font-semibold text-on-surface">{category}</span>
      </p>

      <div className="flex items-center gap-2 mt-4 flex-wrap">
        <button
          onClick={() => setShowFilter((v) => !v)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full border border-outline-variant text-[13px] font-medium text-on-surface hover:bg-surface-container-low transition"
        >
          <SlidersHorizontal size={14} /> Filter
        </button>
        <span className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full border border-outline-variant text-[13px] font-medium text-on-surface">
          State: {params.state}
        </span>
      </div>

      {showFilter && (
        <div className="mt-3 flex items-center gap-2 flex-wrap bg-surface-container-low rounded-lg p-3">
          <span className="text-[12px] font-semibold text-on-surface-variant mr-1">Category:</span>
          {CATEGORIES.map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-3 py-1.5 rounded-full text-[12.5px] font-medium border transition ${
                c === category
                  ? "bg-primary text-on-primary border-primary"
                  : "border-outline-variant text-on-surface hover:bg-surface-container-lowest"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      {!result && <p className="mt-6 text-on-surface-variant text-sm">Calculating your chances…</p>}

      {result && (
        <div className="mt-6 space-y-4">
          <div className="rounded-2xl border border-outline-variant p-5 text-center">
            <p className="text-sm text-on-surface-variant">Estimated rank</p>
            {result.rankRange ? (
              <p className="text-3xl font-display font-semibold text-on-surface mt-1">
                ~{result.rankRange.low.toLocaleString("en-IN")} &ndash; {result.rankRange.high.toLocaleString("en-IN")}
              </p>
            ) : (
              <p className="text-3xl font-display font-semibold text-on-surface mt-1">
                {result.rank.toLocaleString("en-IN")}
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-outline-variant p-5">
            <p className="text-lg font-semibold text-on-surface">{result.headline}</p>
            <p className="text-sm text-on-surface-variant mt-1">
              Out of {result.totalColleges} colleges matching your category and state filter,{" "}
              <span className="font-semibold text-on-surface">{result.inReach}</span> are within reach.
            </p>
            <button
              onClick={() => navigate(
                `/colleges?score=${params.score}&category=${category}&state=${encodeURIComponent(params.state || "")}&quota=${encodeURIComponent(params.quota || "")}`
              )}
              className="mt-3 w-full py-2.5 rounded bg-primary text-on-primary font-semibold text-[13.5px] hover:brightness-110 transition"
            >
              View Matching Colleges
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <ChanceStat label="High chance" value={result.counts.High} tone="high" />
            <ChanceStat label="Likely" value={result.counts.Likely} tone="high" />
            <ChanceStat label="Moderate chance" value={result.counts.Moderate} tone="moderate" />
            <ChanceStat label="Low chance" value={result.counts.Low} tone="low" />
          </div>
        </div>
      )}
    </div>
  );
}

function ChanceStat({ label, value, tone }) {
  const toneClass = tone === "high" ? "text-emerald-600" : tone === "moderate" ? "text-amber-600" : "text-rose-600";
  return (
    <div className="rounded-xl border border-outline-variant p-4 text-center">
      <p className={`text-2xl font-semibold ${toneClass}`}>{value}</p>
      <p className="text-xs text-on-surface-variant mt-1">{label}</p>
    </div>
  );
}
