import Header from "./Header.jsx";
import Footer from "./Footer.jsx";

export default function Layout({ children }) {
  return (
    <div className="site">
      <Header />
      <main className="site-main">{children}</main>
      <Footer />
    </div>
  );
}
