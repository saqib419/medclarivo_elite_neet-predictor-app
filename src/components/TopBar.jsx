import { useNavigate } from "react-router-dom";
import { Menu, ArrowLeft, User } from "lucide-react";

export default function TopBar({ title = "MedPredict", back = false }) {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-10 bg-surface-container-lowest/95 backdrop-blur border-b border-outline-variant/60">
      <div className="max-w-app mx-auto flex items-center justify-between px-4 sm:px-gutter h-14">
        <div className="flex items-center gap-3">
          {back ? (
            <button
              onClick={() => navigate(-1)}
              aria-label="Go back"
              className="p-1.5 -ml-1.5 rounded text-on-surface hover:bg-surface-container transition-colors"
            >
              <ArrowLeft size={22} />
            </button>
          ) : (
            <button
              aria-label="Menu"
              className="p-1.5 -ml-1.5 rounded text-on-surface hover:bg-surface-container transition-colors"
            >
              <Menu size={22} />
            </button>
          )}
          <span className="font-display font-bold text-lg text-primary tracking-tight">{title}</span>
        </div>
        <button
          onClick={() => navigate("/profile")}
          aria-label="Profile"
          className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high/80 transition-colors"
        >
          <User size={17} />
        </button>
      </div>
    </header>
  );
}
