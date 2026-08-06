import { NavLink } from "react-router-dom";
import { Home, Calculator, GraduationCap, User } from "lucide-react";

const ITEMS = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/predict", label: "Predict", icon: Calculator },
  { to: "/colleges", label: "Colleges", icon: GraduationCap },
  { to: "/profile", label: "Profile", icon: User },
];

export default function BottomNav() {
  return (
    <nav className="sticky bottom-0 z-10 bg-surface-container-lowest border-t border-outline-variant/60 pb-[env(safe-area-inset-bottom)]">
      <div className="max-w-app mx-auto grid grid-cols-4">
        {ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className="flex flex-col items-center gap-1 py-2.5 text-on-surface-variant"
          >
            {({ isActive }) => (
              <>
                <span
                  className={`px-3.5 py-1 rounded-full transition-colors ${
                    isActive ? "bg-primary-fixed text-on-primary-fixed" : "text-on-surface-variant"
                  }`}
                >
                  <Icon size={20} strokeWidth={isActive ? 2.4 : 2} />
                </span>
                <span className={`text-[11px] leading-none ${isActive ? "font-semibold text-primary" : "font-medium"}`}>
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
