import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { UserPlus, Lock } from "lucide-react";
import { register } from "../lib/api.js";

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

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function validate() {
    if (!name.trim()) return "Enter your full name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Enter a valid email address.";
    if (!/^\d{10}$/.test(mobile)) return "Enter a valid 10-digit mobile number.";
    if (password.length < 8) return "Password must be at least 8 characters.";
    if (password !== confirmPassword) return "Passwords do not match.";
    return "";
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError("");
    setSubmitting(true);
    const result = await register({ name: name.trim(), email: email.trim(), mobile, password });
    setSubmitting(false);
    if (!result.success) {
      setError(result.message || "Registration failed. Please try again.");
      return;
    }
    navigate("/");
  }

  return (
    <div className="max-w-app mx-auto px-4 sm:px-gutter py-8">
      <h1 className="font-display font-semibold text-2xl text-on-surface text-center">Create Your Account</h1>
      <p className="text-on-surface-variant text-sm text-center mt-2 max-w-xs mx-auto">
        Sign up to save your predictions and get personalized college recommendations.
      </p>

      <form
        onSubmit={handleSubmit}
        className="mt-6 bg-surface-container-lowest border border-outline-variant/70 rounded-lg p-5 shadow-level2"
      >
        <Field label="Full Name">
          <input
            type="text" placeholder="Your full name"
            value={name} onChange={(e) => setName(e.target.value)} autoFocus className={inputCls}
          />
        </Field>

        <Field label="Email Address">
          <input
            type="email" placeholder="your@email.com"
            value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls}
          />
        </Field>

        <Field label="Mobile Number">
          <div className="flex gap-2">
            <span className="flex items-center justify-center px-3.5 rounded border border-outline-variant bg-surface-container-low text-on-surface-variant text-[15px] font-medium">
              +91
            </span>
            <input
              type="tel" inputMode="numeric" maxLength={10} placeholder="10-digit number"
              value={mobile} onChange={(e) => setMobile(e.target.value.replace(/\D/g, ""))}
              className={`${inputCls} flex-1`}
            />
          </div>
        </Field>

        <Field label="Password">
          <input
            type="password" placeholder="At least 8 characters"
            value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls}
          />
        </Field>

        <Field label="Confirm Password">
          <input
            type="password" placeholder="Re-enter your password"
            value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className={inputCls}
          />
        </Field>

        {error && <p className="text-error text-[13px] font-medium mb-3">{error}</p>}

        <button
          type="submit" disabled={submitting}
          className="w-full py-3 rounded bg-primary text-on-primary font-semibold text-[13.5px] flex items-center justify-center gap-1.5 hover:brightness-110 transition disabled:opacity-60"
        >
          <UserPlus size={16} />
          {submitting ? "Creating account…" : "Create Account"}
        </button>
      </form>

      <p className="flex items-center justify-center gap-1.5 text-[12px] text-on-surface-variant text-center mt-4">
        <Lock size={12} /> Your information is secure and never shared.
      </p>
    </div>
  );
}
