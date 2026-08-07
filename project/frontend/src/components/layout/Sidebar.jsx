import { useMemo, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "../../context/AuthContext.jsx";
import { useLectures } from "../../context/LecturesContext.jsx";

/* Desktop: a fixed-width column that can collapse to an icon rail.
   Mobile (<901px): hidden by default, opened as an off-canvas drawer via
   the hamburger button in AppShell. Both render the same `body` content
   -- only one is visible at a given viewport width (see the media
   queries in index.css), the same pattern FloatingNav already uses for
   its desktop/mobile nav. */
export default function Sidebar({ mobileOpen, onCloseMobile }) {
  const [collapsed, setCollapsed] = useState(false);
  const [query, setQuery] = useState("");
  const { lectures } = useLectures();
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const filtered = useMemo(() => {
    if (!lectures) return null;
    const q = query.trim().toLowerCase();
    if (!q) return lectures;
    return lectures.filter((l) =>
      [l.title, l.course, l.instructor].filter(Boolean).join(" ").toLowerCase().includes(q)
    );
  }, [lectures, query]);

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  const handleNewLecture = () => {
    onCloseMobile();
    navigate("/app", { state: { openUpload: true } });
  };

  const body = (
    <SidebarBody
      collapsed={collapsed}
      setCollapsed={setCollapsed}
      query={query}
      setQuery={setQuery}
      filtered={filtered}
      user={user}
      onNewLecture={handleNewLecture}
      onSignOut={handleSignOut}
      onNavigate={onCloseMobile}
    />
  );

  return (
    <>
      <aside className={`app-sidebar ${collapsed ? "collapsed" : ""}`}>{body}</aside>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="sidebar-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              onClick={onCloseMobile}
            />
            <motion.aside
              className="app-sidebar app-sidebar-drawer"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            >
              <SidebarBody
                collapsed={false}
                setCollapsed={setCollapsed}
                query={query}
                setQuery={setQuery}
                filtered={filtered}
                user={user}
                onNewLecture={handleNewLecture}
                onSignOut={handleSignOut}
                onNavigate={onCloseMobile}
                isDrawer
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function SidebarBody({
  collapsed,
  setCollapsed,
  query,
  setQuery,
  filtered,
  user,
  onNewLecture,
  onSignOut,
  onNavigate,
  isDrawer,
}) {
  return (
    <>
      <div className="sidebar-top">
        <Link to="/" className="brand sidebar-brand">
          <span className="brand-mark">اع</span>
          {!collapsed && <span className="brand-name">Lecture Companion</span>}
        </Link>
        {!isDrawer && (
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <CollapseIcon collapsed={collapsed} />
          </button>
        )}
      </div>

      <button type="button" className="sidebar-new-btn" onClick={onNewLecture}>
        <PlusIcon />
        {!collapsed && <span>New lecture</span>}
      </button>

      {!collapsed && (
        <div className="sidebar-search">
          <SearchIcon />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search lectures"
            aria-label="Search lectures"
          />
        </div>
      )}

      <nav className="sidebar-list" aria-label="Lectures">
        {filtered === null && <div className="sidebar-empty muted">Loading...</div>}
        {filtered?.length === 0 && (
          <div className="sidebar-empty muted">{query ? "No matches." : "No lectures yet."}</div>
        )}
        {filtered?.map((l) => (
          <NavLink
            key={l.lecture_id}
            to={`/app/lectures/${l.lecture_id}`}
            className={({ isActive }) => `sidebar-lecture ${isActive ? "active" : ""}`}
            onClick={onNavigate}
            title={l.title}
          >
            {collapsed ? (
              <span className="sidebar-lecture-avatar" data-status={l.status}>
                {l.title?.[0]?.toUpperCase() || "?"}
              </span>
            ) : (
              <>
                <span className={`sidebar-lecture-dot dot-${l.status}`} />
                <span className="sidebar-lecture-text">
                  <span className="sidebar-lecture-title">{l.title}</span>
                  <span className="sidebar-lecture-sub">
                    {[l.course, l.instructor].filter(Boolean).join(" · ") || l.status}
                  </span>
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-user" title={user?.email}>
          <span className="sidebar-user-avatar">{(user?.email || "?")[0].toUpperCase()}</span>
          {!collapsed && <span className="sidebar-user-email">{user?.email}</span>}
        </div>
        <button
          type="button"
          className="sidebar-signout-btn"
          onClick={onSignOut}
          aria-label="Sign out"
          title="Sign out"
        >
          <SignOutIcon />
          {!collapsed && <span>Sign out</span>}
        </button>
      </div>
    </>
  );
}

function PlusIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <path d="M8 2.5v11M2.5 8h11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
      <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M13.5 13.5L10.7 10.7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function CollapseIcon({ collapsed }) {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 16 16"
      fill="none"
      style={{ transform: collapsed ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}
    >
      <path d="M10.5 3L5.5 8l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 3v10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.4" />
    </svg>
  );
}

function SignOutIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
      <path
        d="M6 2.5H3.5a1 1 0 00-1 1v9a1 1 0 001 1H6M10.5 11l3-3-3-3M13.3 8H6"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}