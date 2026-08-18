import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Calculator, Lock, ChevronDown } from "lucide-react";
import { CATEGORIES, STATES } from "../lib/predictor.js";
import { predict, submitLead } from "../lib/api.js";
import { addRecentSearch, setLastPrediction } from "../lib/storage.js";

const QUOTAS = ["Both", "All India Quota", "State Quota"];
const STEPS = 4;

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

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function PredictorForm() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [score, setScore] = useState("");
  const [category, setCategory] = useState("");
  const [quota, setQuota] = useState("");
  const [stateSel, setStateSel] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("");
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
    if (step === 2 && !stateSel) {
      setError("Select your home state.");
      return;
    }
    setError("");
    setStep((s) => Math.min(s + 1, STEPS - 1));
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (!name.trim()) {
      setError("Enter your name.");
      return;
    }
    const phoneDigits = phone.replace(/\D/g, "").slice(-10);
    if (!/^[6-9]\d{9}$/.test(phoneDigits)) {
      setError("Enter a valid 10-digit phone number.");
      return;
    }
    if (!EMAIL_RE.test(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (!city.trim()) {
      setError("Enter your city.");
      return;
    }

    setError("");
    setSubmitting(true);

    const result = await predict({ score: Number(score), category, state: stateSel, quota });
    const entry = { score: Number(score), category, state: stateSel, quota, rank: result.rank, rankRange: result.rankRange };

    // Fire the lead off in the background — a webhook hiccup should never
    // block a student from seeing their result.
    submitLead({
      name: name.trim(),
      phone: phoneDigits,
      email: email.trim(),
      city: city.trim(),
      score: Number(score),
      category,
      quota,
      state: stateSel,
      rank: result.rank,
    });

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

        {step === 3 && (
          <>
            <p className="text-[13px] text-on-surface-variant -mt-1 mb-4">
              One last step — enter your details to see your predicted rank and matching colleges.
            </p>
            <Field label="Full Name">
              <input
                type="text" placeholder="e.g. Aisha Khan"
                value={name} onChange={(e) => setName(e.target.value)} autoFocus className={inputCls}
              />
            </Field>
            <Field label="Phone Number">
              <input
                type="tel" inputMode="numeric" placeholder="e.g. 98765 43210"
                value={phone} onChange={(e) => setPhone(e.target.value)} className={inputCls}
              />
            </Field>
            <Field label="Email Address">
              <input
                type="email" placeholder="e.g. aisha@example.com"
                value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls}
              />
            </Field>
            <Field label="City">
              <input
                type="text" placeholder="e.g. Srinagar"
                value={city} onChange={(e) => setCity(e.target.value)} className={inputCls}
              />
            </Field>
          </>
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
