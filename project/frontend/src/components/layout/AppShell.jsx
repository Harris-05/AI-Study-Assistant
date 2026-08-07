import { useState } from "react";
import { Outlet } from "react-router-dom";
import { LecturesProvider } from "../../context/LecturesContext.jsx";
import Sidebar from "./Sidebar.jsx";

/* Replaces the marketing FloatingNav+Footer chrome for everything under
   /app -- this is the "Claude-AI-inspired workspace" from design.md: a
   persistent sidebar instead of a top nav, full-height, no footer. */
export default function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <LecturesProvider>
      <div className="app-shell">
        <Sidebar mobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />

        <main className="workspace">
          <button
            type="button"
            className="workspace-menu-btn"
            aria-label="Open lecture list"
            onClick={() => setMobileOpen(true)}
          >
            <MenuIcon />
          </button>
          <Outlet />
        </main>
      </div>
    </LecturesProvider>
  );
}

function MenuIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
      <path d="M2 5h14M2 9h14M2 13h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}