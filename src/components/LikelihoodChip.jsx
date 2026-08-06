import { CheckCircle2, TrendingUp, AlertTriangle } from "lucide-react";

const TONE_STYLES = {
  high: { bg: "bg-status-high-bg", text: "text-status-high-text", Icon: CheckCircle2 },
  moderate: { bg: "bg-status-moderate-bg", text: "text-status-moderate-text", Icon: TrendingUp },
  low: { bg: "bg-status-low-bg", text: "text-status-low-text", Icon: AlertTriangle },
};

export default function LikelihoodChip({ tone, label }) {
  const s = TONE_STYLES[tone] || TONE_STYLES.low;
  const Icon = s.Icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${s.bg} ${s.text}`}>
      <Icon size={12} strokeWidth={2.5} />
      {label}
    </span>
  );
}
