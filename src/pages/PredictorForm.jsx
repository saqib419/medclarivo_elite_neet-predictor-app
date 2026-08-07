import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Calculator, Lock, ChevronDown } from "lucide-react";
import { CATEGORIES, STATES } from "../lib/predictor.js";
import { predict } from "../lib/api.js";
import { addRecentSearch, setLastPrediction } from "../lib/storage.js";

const QUOTAS = ["Both", "All India Quota", "State Quota"];
const STEPS = 3;

function ProgressBar({ step }) {
  return (
    <div className="flex gap-1.5 mb-6">
      {Array.from({ length: STEPS }).map((_, i) => (
        <div key={i} className={`h-1 flex-1 rounded-full ${i <= step ? "bg-primary" : "bg-surface-container-high"}`} />
      ))}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block mb-4">
      <span className="block text-[13px] font-medium text-on-surface-variant mb-1.5">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded border border-outline-variant bg-surface-container-lowest px-3.5 py-3 text-[15px] text-on-surface placeholder:text-outline focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition";

export default function PredictorForm() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [score, setScore] = useState("");
  const [category, setCategory] = useState("");
  const [quota, setQuota] = useState("");
  const [stateSel, setStateSel] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function next() {
    if (step === 0) {
      const n = Number(score);
      if (!score || Number.isNaN(n) || n < 0 || n > 720) {
        setError("Enter a valid score between 0 and 720.");
        return;
      }
    }
    if (step === 1 && (!category || !quota)) {
      setError("Select both a category and a quota.");
      return;
    }
    setError("");
    setStep((s) => Math.min(s + 1, STEPS - 1));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!stateSel) {
      setError("Select your home state.");
      return;
    }
    setSubmitting(true);
    const result = await predict({ score: Number(score), category, state: stateSel, quota });
    const entry = { score: Number(score), category, state: stateSel, quota, rank: result.rank };
    setLastPrediction(entry);
    addRecentSearch(entry);
    setSubmitting(false);
    navigate("/results", { state: entry });
  }

  return (
    <div className="max-w-app mx-auto px-4 sm:px-gutter py-8">
      <h1 className="font-display font-semibold text-2xl text-on-surface text-center">Admission Predictor</h1>
      <p className="text-on-surface-variant text-sm text-center mt-2 max-w-xs mx-auto">
        Enter your details to estimate your chances of securing a medical seat.
      </p>

      <form
        onSubmit={step === STEPS - 1 ? handleSubmit : (e) => { e.preventDefault(); next(); }}
        className="mt-6 bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-5 shadow-level2"
      >
        <ProgressBar step={step} />

        {step === 0 && (
          <Field label="NEET Score (out of 720)">
            <input
              type="number" inputMode="numeric" min="0" max="720" placeholder="e.g. 650"
              value={score} onChange={(e) => setScore(e.target.value)} autoFocus className={inputCls}
            />
          </Field>
        )}

        {step === 1 && (
          <>
            <Field label="Category">
              <div className="relative">
                <select value={category} onChange={(e) => setCategory(e.target.value)} className={`${inputCls} appearance-none pr-9`}>
                  <option value="" disabled>Select Category</option>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none" />
              </div>
            </Field>
            <Field label="Quota">
              <div className="relative">
                <select value={quota} onChange={(e) => setQuota(e.target.value)} className={`${inputCls} appearance-none pr-9`}>
                  <option value="" disabled>Select Quota</option>
                  {QUOTAS.map((q) => <option key={q} value={q}>{q}</option>)}
                </select>
                <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none" />
              </div>
            </Field>
          </>
        )}

        {step === 2 && (
          <Field label="Home State">
            <div className="relative">
              <select value={stateSel} onChange={(e) => setStateSel(e.target.value)} className={`${inputCls} appearance-none pr-9`}>
                <option value="" disabled>Select your domicile state</option>
                {STATES.filter((s) => s !== "All-India only").map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none" />
            </div>
          </Field>
        )}

        {error && <p className="text-error text-[13px] font-medium mb-3">{error}</p>}

        <div className="flex gap-3 mt-2">
          {step > 0 && (
            <button
              type="button" onClick={() => setStep((s) => s - 1)}
              className="flex-1 py-3 rounded border border-outline-variant text-on-surface font-semibold text-sm hover:bg-surface-container-low transition"
            >
              Back
            </button>
          )}
          <button
            type="submit" disabled={submitting}
            className="flex-1 py-3 rounded bg-primary text-on-primary font-semibold text-[13.5px] whitespace-nowrap flex items-center justify-center gap-1.5 hover:brightness-110 transition disabled:opacity-60"
          >
            <Calculator size={16} />
            {step === STEPS - 1 ? (submitting ? "Calculating…" : "Calculate Probability") : "Continue"}
          </button>
        </div>
      </form>

      <p className="flex items-center justify-center gap-1.5 text-[12px] text-on-surface-variant text-center mt-4">
        <Lock size={12} /> Your data is secure and will only be used for prediction.
      </p>
    </div>
  );
}
