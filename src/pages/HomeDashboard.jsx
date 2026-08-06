import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart3, Target, History, ChevronRight, ArrowRight } from "lucide-react";
import CollegeRow from "../components/CollegeRow.jsx";
import { fmt } from "../lib/predictor.js";
import { predict } from "../lib/api.js";
import { getLastPrediction, getRecentSearches, clearRecentSearches } from "../lib/storage.js";

function RankRing({ rank }) {
  // Purely illustrative fill — closer to 0 rank fills the ring more.
  const pct = Math.max(0.06, 1 - Math.min(rank, 1_200_000) / 1_200_000);
  const r = 54;
  const c = 2 * Math.PI * r;
  return (
    <svg width="140" height="140" viewBox="0 0 140 140" className="mx-auto">
      <circle cx="70" cy="70" r={r} fill="none" stroke="#e1e2e4" strokeWidth="12" />
      <circle
        cx="70" cy="70" r={r} fill="none" stroke="#003d9b" strokeWidth="12" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 70 70)"
      />
      <text x="70" y="76" textAnchor="middle" className="font-display font-semibold" fontSize="20" fill="#191c1e">
        Top
      </text>
    </svg>
  );
}

export default function HomeDashboard() {
  const navigate = useNavigate();
  const [last, setLast] = useState(() => getLastPrediction());
  const [recent, setRecent] = useState(() => getRecentSearches());
  const [recommended, setRecommended] = useState([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (last) {
        const result = await predict({ score: last.score, category: last.category, state: last.state });
        if (!cancelled) setRecommended(result.matches.slice(0, 2));
      } else {
        const result = await predict({ score: 650, category: "General", state: "All-India only" });
        if (!cancelled) setRecommended(result.matches.slice(0, 2));
      }
    })();
    return () => { cancelled = true; };
  }, [last]);

  return (
    <div className="max-w-app mx-auto px-4 sm:px-gutter py-6 space-y-5">
      <div>
        <h1 className="font-display font-semibold text-2xl text-on-surface">Welcome back</h1>
        <p className="text-on-surface-variant text-sm mt-1">
          {last ? "Here's your current standing based on your last prediction." : "Run your first prediction to see where you stand."}
        </p>
      </div>

      {last ? (
        <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-5">
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold text-on-surface-variant">Your NEET Score</span>
            <BarChart3 size={18} className="text-on-surface-variant" />
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="font-display font-bold text-4xl text-primary tabular-nums">{last.score}</span>
            <span className="text-on-surface-variant font-medium">/ 720</span>
          </div>
          <p className="text-[13px] text-on-surface-variant mt-1">{last.category} · {last.state}</p>
          <button
            onClick={() => navigate("/predict")}
            className="mt-4 w-full py-2.5 rounded bg-primary text-on-primary text-sm font-semibold hover:brightness-110 transition"
          >
            Update Prediction
          </button>
        </div>
      ) : (
        <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-6 text-center">
          <Target size={28} className="mx-auto text-primary" />
          <p className="mt-2 font-display font-semibold text-on-surface">No prediction yet</p>
          <p className="text-[13px] text-on-surface-variant mt-1">Enter your score to estimate your rank and matching colleges.</p>
          <button
            onClick={() => navigate("/predict")}
            className="mt-4 inline-flex items-center gap-1.5 px-5 py-2.5 rounded bg-primary text-on-primary text-sm font-semibold hover:brightness-110 transition"
          >
            Start Predicting <ArrowRight size={15} />
          </button>
        </div>
      )}

      {last && (
        <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[13px] font-semibold text-on-surface-variant">Predicted Rank</span>
            <Target size={18} className="text-on-surface-variant" />
          </div>
          <RankRing rank={last.rank} />
          <div className="text-center mt-1">
            <div className="font-display font-bold text-xl text-on-surface tabular-nums">{fmt(last.rank)}</div>
            <div className="text-[10.5px] font-semibold uppercase tracking-wide text-on-surface-variant">All India Rank</div>
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="font-display font-semibold text-on-surface">Recommended for You</h2>
          <button onClick={() => navigate("/colleges")} className="text-[13px] font-semibold text-primary">View All</button>
        </div>
        <div className="space-y-2.5">
          {recommended.map((c) => <CollegeRow key={c.slug} college={c} />)}
          {recommended.length === 0 && <p className="text-[13px] text-on-surface-variant">Loading recommendations…</p>}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="font-display font-semibold text-on-surface">Recent Searches</h2>
          {recent.length > 0 && (
            <button
              onClick={() => { clearRecentSearches(); setRecent([]); }}
              className="text-[13px] font-semibold text-primary"
            >
              Clear
            </button>
          )}
        </div>
        {recent.length === 0 ? (
          <p className="text-[13px] text-on-surface-variant">No searches yet.</p>
        ) : (
          <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg divide-y divide-outline-variant/60">
            {recent.map((s, i) => (
              <button
                key={i}
                onClick={() => navigate("/results", { state: s })}
                className="w-full flex items-center gap-3 p-3.5 text-left hover:bg-surface-container-low transition-colors"
              >
                <History size={16} className="text-on-surface-variant shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="text-[13.5px] font-medium text-on-surface truncate">Score {s.score} · {s.category}</div>
                  <div className="text-[12px] text-on-surface-variant truncate">{s.state}</div>
                </div>
                <ChevronRight size={16} className="text-on-surface-variant shrink-0" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
