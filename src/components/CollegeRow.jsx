import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import LikelihoodChip from "./LikelihoodChip.jsx";

export default function CollegeRow({ college }) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate(`/college/${college.slug}`, { state: { college } })}
      className="w-full flex items-center gap-3 bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-3 text-left hover:shadow-level2 transition-shadow"
    >
      <div className="w-12 h-12 shrink-0 rounded bg-primary-fixed flex items-center justify-center text-on-primary-fixed">
        <Building2 size={20} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-semibold text-[13.5px] text-on-surface truncate">{college.name}</div>
        <div className="text-[12px] text-on-surface-variant truncate">{college.state || "All-India"}</div>
        <div className="flex items-center gap-1.5 mt-1">
          {college.like && <LikelihoodChip tone={college.like.tone} label={college.like.label} />}
          <span className="text-[10.5px] px-2 py-0.5 rounded-full border border-outline-variant text-on-surface-variant">
            {college.quota === "AIQ" ? "General" : "State"}
          </span>
        </div>
      </div>
    </button>
  );
}
