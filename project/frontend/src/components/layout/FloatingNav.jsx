import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { AnimatePresence, motion, useScroll, useMotionValueEvent } from "framer-motion";
import { gsap } from "gsap";
import { ScrollToPlugin } from "gsap/ScrollToPlugin";
import { useAuth } from "../../context/AuthContext.jsx";

gsap.registerPlugin(ScrollToPlugin);

const LINKS = [
  { to: "/#how-it-works", label: "How it works" },
  { to: "/#features", label: "Features" },
];

/* Smooth-scrolls to an in-page section via GSAP instead of the CSS
   `scroll-behavior: smooth` this app deliberately doesn't set (see
   index.css) -- that property fights ScrollTrigger's own scroll math
   on the pinned "how it works" section. GSAP owns the scroll here
   instead, so there's nothing to fight. Off the landing page, this
   just lets the normal navigation to "/#hash" happen and leaves the
   scroll to LandingPage's own on-mount handler. */
function scrollToSection(hash, { pathname, navigate, onDone }) {
  const id = hash.replace("#", "");
  if (pathname !== "/") return false;
  const target = document.getElementById(id);
  if (!target) return false;
  gsap.to(window, {
    duration: 0.9,
    scrollTo: { y: target, offsetY: 16 },
    ease: "power2.inOut",
    onComplete: () => {
      navigate(`/#${id}`, { replace: true });
      onDone?.();
    },
  });
  return true;
}

export default function FloatingNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { scrollY } = useScroll();

  // Dynamic-Island feel: the pill tightens up (smaller radius/shadow) once
  // the page has scrolled a little, instead of staying static the whole way down.
  useMotionValueEvent(scrollY, "change", (latest) => {
    setScrolled(latest > 24);
  });

  useEffect(() => {
    setOpen(false);
  }, []);

  const handleSignOut = async () => {
    await signOut();
    setOpen(false);
    navigate("/");
  };

  const handleNavLinkClick = (e, to, closeMenu) => {
    const hash = to.slice(to.indexOf("#"));
    const handled = scrollToSection(hash, {
      pathname: location.pathname,
      navigate,
      onDone: closeMenu,
    });
    if (handled) e.preventDefault();
    else closeMenu?.();
  };

  return (
    <div className="floating-nav-wrap">
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
        <motion.header
          className="floating-nav"
          initial={{ y: -32, opacity: 0 }}
          animate={{
            y: 0,
            opacity: 1,
            boxShadow: scrolled
              ? "0 10px 34px rgba(20,22,26,0.14), 0 2px 8px rgba(20,22,26,0.08)"
              : "0 8px 30px rgba(20,22,26,0.10), 0 2px 8px rgba(20,22,26,0.06)",
          }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="floating-nav-inner">
            <Link to="/" className="brand" onClick={() => setOpen(false)}>
              <span className="brand-mark">اع</span>
              <span className="brand-name">Lecture Companion</span>
            </Link>

            <nav className="nav-desktop">
              <div className="nav-links">
                {LINKS.map((l) => (
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
        </motion.header>

        <AnimatePresence>
          {open && (
            <motion.div
              className="nav-mobile-panel"
              initial={{ opacity: 0, y: -8, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: -8, height: 0 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="nav-mobile-panel-inner">
                {LINKS.map((l) => (
                  <a key={l.to} href={l.to} className="nav-link" onClick={() => setOpen(false)}>
                    {l.label}
                  </a>
                ))}
                {user ? (
                  <>
                    <Link to="/app" className="btn btn-block" onClick={() => setOpen(false)}>
                      Open app
                    </Link>
                    <button className="btn btn-secondary btn-block" onClick={handleSignOut}>
                      Sign out
                    </button>
                  </>
                ) : (
                  <Link to="/login" className="btn btn-block" onClick={() => setOpen(false)}>
                    Sign in
                  </Link>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function MenuIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
      <path d="M2 5h14M2 9h14M2 13h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
      <path d="M4 4l10 10M14 4L4 14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}