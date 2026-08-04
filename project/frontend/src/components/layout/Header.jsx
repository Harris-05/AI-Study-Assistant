import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";

export default function Header() {
  const [open, setOpen] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const links = [
    { to: "/#how-it-works", label: "How it works" },
    { to: "/#features", label: "Features" },
  ];

  const handleSignOut = async () => {
    await signOut();
    setOpen(false);
    navigate("/");
  };

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
          {user ? (
            <>
              <NavLink to="/app" className="btn">
                Open app
              </NavLink>
              <button className="nav-link" onClick={handleSignOut} title={user.email}>
                Sign out
              </button>
            </>
          ) : (
            <NavLink to="/login" className="btn">
              Sign in
            </NavLink>
          )}
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
        {user ? (
          <>
            <Link to="/app" className="btn btn-block" style={{ marginTop: 10 }} onClick={() => setOpen(false)}>
              Open app
            </Link>
            <button className="btn btn-block" style={{ marginTop: 10 }} onClick={handleSignOut}>
              Sign out
            </button>
          </>
        ) : (
          <Link to="/login" className="btn btn-block" style={{ marginTop: 10 }} onClick={() => setOpen(false)}>
            Sign in
          </Link>
        )}
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