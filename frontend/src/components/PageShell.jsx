// Seed of the product shell. P4 replaces this with the three-pane SaaS layout
// (rail + conversation + evidence panel); until then it gives every secondary
// screen a real URL, a way back and consistent spacing.

import { Link, useLocation } from "react-router-dom";

const NAV = [
  { to: "/", label: "Hỏi đáp" },
  { to: "/sessions", label: "Phiên" },
  { to: "/faq", label: "Kho câu hỏi" },
  { to: "/settings", label: "Cài đặt" },
];

export default function PageShell({ title, subtitle, children }) {
  const { pathname } = useLocation();

  return (
    <div className="mx-auto flex h-dvh max-w-[1100px] flex-col px-6 pt-6 pb-8 max-sm:px-4">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <h1 className="m-0 text-[17px] font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-1 mb-0 text-[12px] text-faint">{subtitle}</p>}
        </div>
        <nav aria-label="Điều hướng chính" className="flex flex-wrap gap-1">
          {NAV.map((item) => {
            const active = item.to === pathname;
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={active ? "page" : undefined}
                className={`rounded-lg px-3 py-1.5 text-[12.5px] transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
                  active
                    ? "bg-accent/15 text-accent"
                    : "text-dim hover:bg-white/[0.06] hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="scroll-thin min-h-0 flex-1 overflow-y-auto pt-6">{children}</main>
    </div>
  );
}
