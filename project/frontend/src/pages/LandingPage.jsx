import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <>
      <Hero />
      <HowItWorks />
      <Features />
      <FinalCta />
    </>
  );
}

function Hero() {
  return (
    <section className="hero">
      <div className="container hero-grid">
        <div>
          <span className="eyebrow">Built for Urdu · English · Arabic lectures</span>
          <h1 className="hero-title">
            Turn code-switched lectures into notes you can <em>actually</em> study from.
          </h1>
          <p className="hero-subtitle">
            Upload a Zoom recording that mixes Urdu, English, and Arabic. Get a cleaned
            transcript, a chat that only answers from what your instructor said, and quizzes
            generated straight from the lecture.
          </p>
          <div className="hero-ctas">
            <Link to="/app" className="btn btn-lg">
              Upload a lecture
            </Link>
            <a href="#how-it-works" className="btn btn-secondary btn-lg">
              See how it works
            </a>
          </div>
        </div>

        <TransformCard />
      </div>
    </section>
  );
}

function TransformCard() {
  return (
    <div className="transform-card" aria-hidden="true">
      <div className="transform-panel">
        <div className="transform-label">
          <span className="dot" /> Raw transcript
        </div>
        <p className="transform-raw-text">
          آپ <span className="en">inheritance</span> کے <span className="en">concept</span> کو
          سمجھیں۔ اگلا <span className="en">topic</span> ہے <span className="en">polymorphism</span>۔
        </p>
      </div>

      <div className="transform-arrow">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M9 3v11M4 10l5 5 5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <div className="transform-panel">
        <div className="transform-label clean">
          <span className="dot" /> Cleaned & structured
        </div>
        <ul className="transform-clean-list">
          <li>
            Script corrected, grammar fixed — <span className="term">Inheritance</span> kept in
            English
          </li>
          <li>Next topic flagged: Polymorphism</li>
          <li>Indexed and ready for chat + quiz generation</li>
        </ul>
      </div>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    {
      n: "01",
      title: "Upload",
      desc: "Add a Zoom recording or audio file — video or audio, no prep needed beforehand.",
    },
    {
      n: "02",
      title: "Process",
      desc: "Speech-to-text, script correction, and language cleanup run automatically, preserving technical terms and Arabic phrases exactly as spoken.",
    },
    {
      n: "03",
      title: "Study",
      desc: "Ask questions grounded strictly in the lecture, or generate a quiz from what was actually covered.",
    },
  ];

  return (
    <section id="how-it-works" className="section section-border-top">
      <div className="container">
        <div className="section-head">
          <div className="section-eyebrow">How it works</div>
          <h2 className="section-title">Three steps, start to finish</h2>
          <p className="section-desc">From a raw recording to something you can question and be quizzed on.</p>
        </div>
        <div className="steps">
          {steps.map((s) => (
            <div key={s.n}>
              <div className="step-number">{s.n}</div>
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Features() {
  const features = [
    {
      icon: <GlobeIcon />,
      title: "Multilingual by default",
      desc: "Handles Urdu, English, and Arabic in the same recording, including correcting Hindi-script speech-to-text output back to Urdu.",
    },
    {
      icon: <ChatIcon />,
      title: "Grounded chat",
      desc: "Answers come only from your lecture. If something wasn't covered, the chat says so instead of guessing.",
    },
    {
      icon: <LinkIcon />,
      title: "Traceable sources",
      desc: "Every answer points back to the exact transcript excerpt it came from, with a confidence score attached.",
    },
    {
      icon: <ListIcon />,
      title: "Quizzes from the lecture",
      desc: "Generate MCQs, short-answer, and long-answer questions straight from what was taught — nothing invented.",
    },
  ];

  return (
    <section id="features" className="section section-subtle section-border-top">
      <div className="container">
        <div className="section-head">
          <div className="section-eyebrow">Features</div>
          <h2 className="section-title">Built around one rule: don't make things up</h2>
          <p className="section-desc">
            Every feature traces back to the lecture itself — the transcript, not the model's own
            knowledge, is the source of truth.
          </p>
        </div>
        <div className="feature-grid">
          {features.map((f) => (
            <div key={f.title} className="feature-card">
              <div className="feature-icon">{f.icon}</div>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="section">
      <div className="cta-band">
        <h2>Ready to stop re-watching recordings?</h2>
        <p>Upload your first lecture and start asking it questions in a couple of minutes.</p>
        <Link to="/app" className="btn btn-lg">
          Upload a lecture
        </Link>
      </div>
    </section>
  );
}

/* ── Icons (inline, no external dependency) ────────────── */
function GlobeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="7.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M2.5 10h15M10 2.5c2.2 2 3.4 4.8 3.4 7.5s-1.2 5.5-3.4 7.5c-2.2-2-3.4-4.8-3.4-7.5S7.8 4.5 10 2.5z" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
function ChatIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M3 4.5h14a1 1 0 011 1V13a1 1 0 01-1 1H8l-3.5 3V14H3a1 1 0 01-1-1V5.5a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}
function LinkIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M8.5 11.5l3-3M7 13l-2 2a2.5 2.5 0 01-3.5-3.5l2-2M13 7l2-2a2.5 2.5 0 013.5 3.5l-2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function ListIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M7 5h9M7 10h9M7 15h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="3.2" cy="5" r="1" fill="currentColor" />
      <circle cx="3.2" cy="10" r="1" fill="currentColor" />
      <circle cx="3.2" cy="15" r="1" fill="currentColor" />
    </svg>
  );
}
