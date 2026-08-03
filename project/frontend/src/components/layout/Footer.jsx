import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-top">
          <div>
            <Link to="/" className="brand">
              <span className="brand-mark">اع</span>
              <span className="brand-name">Lecture Companion</span>
            </Link>
            <p className="footer-tagline">
              Turns mixed Urdu/English/Arabic lecture recordings into a clean transcript,
              a grounded chat, and revision quizzes.
            </p>
          </div>

          <div className="footer-links">
            <div className="footer-col">
              <div className="footer-col-title">Product</div>
              <a href="/#how-it-works">How it works</a>
              <a href="/#features">Features</a>
              <Link to="/app">Open app</Link>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} AI Lecture Companion</span>
          <span>Built for students studying across languages</span>
        </div>
      </div>
    </footer>
  );
}
