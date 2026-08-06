import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { SlidersHorizontal, X, ArrowUpDown, Search } from "lucide-react";
import CollegeCard from "../components/CollegeCard.jsx";
import { CATEGORIES } from "../lib/predictor.js";
import { predict } from "../lib/api.js";

function useQueryParams() {
  const { search } = useLocation();
  return useMemo(() => Object.fromEntries(new URLSearchParams(search)), [search]);
}

export default function MatchingColleges() {
  const navigate = useNavigate();
  const location = useLocation();
  const qp = useQueryParams();

  const initial = location.state || (qp.score ? { score: Number(qp.score), category: qp.category, state: qp.state } : null);

  const [params] = useState(initial);
  const [matches, setMatches] = useState(null);
  const [category, setCategory] = useState(initial?.category);
  const [showFilter, setShowFilter] = useState(false);
  const [sort, setSort] = useState("cutoff");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!params) return;
    (async () => {
      const result = await predict({ score: params.score, category, state: params.state });
      setMatches(result.matches);
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

  const displayed = (matches || [])
    .filter((c) => (query ? c.name.toLowerCase().includes(query.toLowerCase()) : true))
    .slice()
    .sort((a, b) => {
      if (sort === "cutoff") return a.cutoff - b.cutoff;
      const rank = { High: 0, Likely: 1, Moderate: 2, Low: 3 };
      return rank[a.like.label] - rank[b.like.label];
    });

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
        <button
          onClick={() => setSort((s) => (s === "cutoff" ? "chance" : "cutoff"))}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full border border-outline-variant text-[13px] font-medium text-on-surface hover:bg-surface-container-low transition"
        >
          <ArrowUpDown size={14} /> Sort: {sort === "cutoff" ? "Lowest Cutoff" : "Highest Chance"}
        </button>
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

      <div className="relative mt-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search colleges…"
          className="w-full pl-9 pr-8 py-2.5 rounded-full border border-outline-variant bg-surface-container-lowest text-[13.5px] focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
        />
        {query && (
          <button onClick={() => setQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
            <X size={14} />
          </button>
        )}
      </div>

      <div className="mt-4 space-y-3">
        {matches === null && <p className="text-on-surface-variant text-sm">Loading matches…</p>}
        {matches !== null && displayed.length === 0 && (
          <p className="text-on-surface-variant text-sm">No colleges match this search.</p>
        )}
        {displayed.map((c) => <CollegeCard key={c.slug} college={c} />)}
      </div>
    </div>
  );
}
