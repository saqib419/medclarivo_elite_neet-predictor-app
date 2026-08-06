import { useNavigate } from "react-router-dom";
import { MapPin } from "lucide-react";
import LikelihoodChip from "./LikelihoodChip.jsx";
import { fmt } from "../lib/predictor.js";

export default function CollegeCard({ college }) {
  const navigate = useNavigate();
  return (
    <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-4 hover:shadow-level2 transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display font-semibold text-[15px] leading-snug text-on-surface">{college.name}</h3>
        {college.like && <LikelihoodChip tone={college.like.tone} label={college.like.label} />}
      </div>
      <div className="flex items-center gap-1 mt-1 text-on-surface-variant text-[13px]">
        <MapPin size={13} />
        {college.state || "All-India"}
      </div>

      <div className="h-px bg-outline-variant/60 my-3" />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-wide text-on-surface-variant">Prev. Cutoff</div>
          <div className="font-display font-semibold text-lg text-on-surface tabular-nums">{fmt(college.cutoff)}</div>
        </div>
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-wide text-on-surface-variant">Annual Fee</div>
          <div className="font-display font-semibold text-lg text-on-surface tabular-nums">
            ₹{fmt(college.annualFee)}
          </div>
        </div>
      </div>

      <button
        onClick={() => navigate(`/college/${college.slug}`, { state: { college } })}
        className="mt-4 w-full py-2.5 rounded text-sm font-semibold text-primary border border-primary hover:bg-primary-fixed/40 transition-colors"
      >
        View Details
      </button>
    </div>
  );
}
