import { useState } from "react";
import { Link, NavLink } from "react-router-dom";

export default function Header() {
  const [open, setOpen] = useState(false);

  const links = [
    { to: "/#how-it-works", label: "How it works" },
    { to: "/#features", label: "Features" },
  ];

  return (
    <header className="site-header">
      <div className="container site-header-inner">
        <Link to="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">اع</span>
          <span className="brand-name">Lecture Companion</span>
        </Link>

        <nav className="nav-desktop">
          <div className="nav-links">
            {links.map((l) => (
              <a key={l.to} href={l.to} className="nav-link">
                {l.label}
              </a>
            ))}
          </div>
          <NavLink to="/app" className="btn">
            Open app
          </NavLink>
        </nav>

        <button
          className="nav-toggle"
          aria-label="Toggle navigation menu"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <CloseIcon /> : <MenuIcon />}
        </button>
      </div>

      <div className={`container nav-mobile ${open ? "open" : ""}`}>
        {links.map((l) => (
          <a key={l.to} href={l.to} className="nav-link" onClick={() => setOpen(false)}>
            {l.label}
          </a>
        ))}
        <Link to="/app" className="btn btn-block" style={{ marginTop: 10 }} onClick={() => setOpen(false)}>
          Open app
        </Link>
      </div>
    </header>
  );
}

function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M2 5h14M2 9h14M2 13h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M4 4l10 10M14 4L4 14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
