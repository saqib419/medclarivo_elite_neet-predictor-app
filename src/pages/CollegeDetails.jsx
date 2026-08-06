import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { BarChart3, Wallet, Armchair, CalendarDays, Building2, BookOpen, Stethoscope, BookmarkPlus, BookmarkCheck } from "lucide-react";
import { fetchCollegeBySlug } from "../lib/api.js";
import { fmt } from "../lib/predictor.js";
import { isShortlisted, toggleShortlist } from "../lib/storage.js";

const INFRA_ICONS = { building: Building2, library: BookOpen, stethoscope: Stethoscope };

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-3.5">
      <Icon size={17} className="text-primary" />
      <div className="text-[12px] text-on-surface-variant mt-2">{label}</div>
      <div className="font-display font-semibold text-[17px] text-on-surface tabular-nums">{value}</div>
    </div>
  );
}

export default function CollegeDetails() {
  const { slug } = useParams();
  const location = useLocation();
  const [college, setCollege] = useState(location.state?.college || null);
  const [shortlisted, setShortlisted] = useState(() => isShortlisted(slug));

  useEffect(() => {
    if (!college) {
      fetchCollegeBySlug(slug).then(setCollege);
    }
  }, [slug]);

  if (!college) {
    return <div className="max-w-app mx-auto px-4 py-10 text-on-surface-variant text-sm">Loading college…</div>;
  }

  return (
    <div className="max-w-app mx-auto pb-24">
      <div className="relative h-44 bg-gradient-to-br from-primary to-secondary flex items-end p-4 overflow-hidden">
        <Building2 size={120} className="absolute -right-4 -top-4 text-white/10" />
        <div className="relative">
          <span className="inline-block bg-primary text-on-primary text-[11px] font-semibold px-2.5 py-1 rounded-full mb-2">
            {college.category || "Government"}
          </span>
          <h1 className="font-display font-bold text-xl text-white leading-tight">{college.name}</h1>
          <p className="text-white/85 text-[13px] mt-0.5">{college.state || "All-India"}</p>
        </div>
      </div>

      <div className="px-4 sm:px-gutter py-5">
        <div className="grid grid-cols-2 gap-3">
          <StatCard icon={BarChart3} label="NIRF Rank" value={`#${college.nirfRank}`} />
          <StatCard icon={Wallet} label="Annual Fee" value={`₹${fmt(college.annualFee)}`} />
          <StatCard icon={Armchair} label="Total Seats" value={college.totalSeats} />
          <StatCard icon={CalendarDays} label="Est. Year" value={college.establishedYear} />
        </div>

        {college.seatMatrix && (
          <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-4 mt-4">
            <h2 className="font-display font-semibold text-on-surface mb-2">Seat Matrix Detail</h2>
            <div className="divide-y divide-outline-variant/60">
              {Object.entries(college.seatMatrix).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between py-2.5 text-[13.5px]">
                  <span className="text-on-surface-variant">{k}</span>
                  <span className="font-semibold text-on-surface tabular-nums">{v} Seats</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {college.cutoffTrends && (
          <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-4 mt-4">
            <h2 className="font-display font-semibold text-on-surface mb-2">NEET Cutoff Trends (General)</h2>
            <table className="w-full text-[13.5px]">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-on-surface-variant">
                  <th className="font-semibold pb-2">Year</th>
                  <th className="font-semibold pb-2">Round 1 Rank</th>
                  <th className="font-semibold pb-2">Round 2 Rank</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60">
                {college.cutoffTrends.map((t) => (
                  <tr key={t.year}>
                    <td className="py-2.5 text-on-surface-variant">{t.year}</td>
                    <td className="py-2.5 font-semibold text-on-surface tabular-nums">{fmt(t.round1)}</td>
                    <td className="py-2.5 font-semibold text-on-surface tabular-nums">{t.round2 ? fmt(t.round2) : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {college.infrastructure && (
          <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-4 mt-4">
            <h2 className="font-display font-semibold text-on-surface mb-3">Infrastructure</h2>
            <div className="space-y-3.5">
              {college.infrastructure.map((f, i) => {
                const Icon = INFRA_ICONS[f.icon] || Building2;
                return (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-9 h-9 shrink-0 rounded bg-secondary-fixed/60 flex items-center justify-center text-secondary">
                      <Icon size={16} />
                    </div>
                    <div>
                      <div className="font-semibold text-[13.5px] text-on-surface">{f.title}</div>
                      <div className="text-[12.5px] text-on-surface-variant">{f.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <p className="text-[11px] text-on-surface-variant mt-4 text-center">
          Illustrative data for demonstration — verify against official NTA/MCC/college sources before relying on it.
        </p>
      </div>

      <div className="fixed bottom-16 left-0 right-0 px-4 sm:px-gutter">
        <div className="max-w-app mx-auto">
          <button
            onClick={() => setShortlisted(toggleShortlist(slug).includes(slug))}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-full bg-primary text-on-primary font-semibold text-sm shadow-level3"
          >
            {shortlisted ? <BookmarkCheck size={17} /> : <BookmarkPlus size={17} />}
            {shortlisted ? "Shortlisted" : "Add to Shortlist"}
          </button>
        </div>
      </div>
    </div>
  );
}
