import { Outlet } from "react-router-dom";
import FloatingNav from "./FloatingNav.jsx";
import Footer from "./Footer.jsx";

/* Used only for the marketing/auth routes (/, /login, /signup) -- the
   /app workspace has its own shell (AppShell.jsx) with a sidebar
   instead of this floating nav, and no footer. */
export default function Layout() {
  return (
    <div className="site">
      <FloatingNav />
      <main className="site-main">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}