import { NavLink } from "react-router-dom";
import { motion, LayoutGroup } from "framer-motion";

/* Same sliding-pill mechanic as a typical local-state segmented control,
   adapted for real routes: each tab is a NavLink (so the URL, back
   button, and refresh all behave normally), and the active one's
   background is a motion.div sharing layoutId "workspace-tab-pill" --
   framer-motion animates it from wherever it was to wherever the newly
   active tab is whenever the route changes. */
export default function WorkspaceTabs({ tabs }) {
  return (
    <LayoutGroup>
      <nav className="pill-tabs" aria-label="Lecture sections">
        {tabs.map((tab) => (
          <NavLink key={tab.id} to={tab.to} className="pill-tab" end>
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId="workspace-tab-pill"
                    className="pill-tab-bg"
                    transition={{ type: "spring", stiffness: 380, damping: 30, mass: 0.9 }}
                  />
                )}
                <motion.span layout="position" className={`pill-tab-label ${isActive ? "active" : ""}`}>
                  {tab.icon}
                  {tab.label}
                </motion.span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </LayoutGroup>
  );
}