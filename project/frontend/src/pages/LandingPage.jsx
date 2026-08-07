import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/* Checked once per mount rather than via a live media-query listener --
   this page doesn't need to react to someone toggling the OS setting
   mid-visit, just to skip all GSAP work (and the global CSS override in
   index.css catches any animation this file misses) when it's on.

   Note that the two scroll-driven sections below use gsap.matchMedia()
   instead, which DOES track the query live -- they need to, because
   their desktop path pins the viewport and a stale pin left behind by a
   resize is a visible bug rather than just a missed animation. */
const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* The one breakpoint both this file and index.css switch on. The
   horizontal storyboard's layout lives in CSS and its motion lives in
   GSAP, so the two must agree exactly or the track overflows with no
   pin driving it. Kept as constants so they can't drift apart silently. */
const DESKTOP_MQ = "(min-width: 900px) and (prefers-reduced-motion: no-preference)";
const FALLBACK_MQ = "(max-width: 899.98px), (prefers-reduced-motion: reduce)";

export default function LandingPage() {
  return (
    <>
      <ScrollRail />
      <Hero />
      <HowItWorks />
      <Journey />
      <Claims />
      <Faq />
      <FinalCta />
    </>
  );
}

/* ── Scroll-progress rail ───────────────────────────────────
   A marker travels the full page scroll against a track carrying the
   landing's warm ramp in the order the sections use it. Desktop only,
   and skipped entirely under reduced motion since it's a pure ambient
   cue. */
function ScrollRail() {
  const markerRef = useRef(null);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const ctx = gsap.context(() => {
      gsap.to(markerRef.current, {
        top: "calc(100% - 9px)",
        ease: "none",
        scrollTrigger: {
          trigger: document.documentElement,
          start: "top top",
          end: "bottom bottom",
          scrub: true,
        },
      });
    });
    return () => ctx.revert();
  }, []);

  if (prefersReducedMotion()) return null;

  return (
    <div className="landing-rail" aria-hidden="true">
      <div className="landing-rail-track" />
      <div className="landing-rail-marker" ref={markerRef} style={{ top: 0 }} />
    </div>
  );
}

/* ── Hero ───────────────────────────────────────────────────
   Deliberately short: an eyebrow, one headline, one CTA -- no
   subtitle paragraph. The headline reveals word-by-word out of a
   mask (GSAP animating a translateY on an inner span, not the paid
   SplitText plugin), and the pipeline panel beside it loops through
   the actual product transform.

   The drifting background fields are CSS keyframes rather than GSAP
   on purpose: they only touch transform/opacity so they stay on the
   compositor and cost no JS frame budget, and the global
   prefers-reduced-motion override in index.css stops them for free. */
function Hero() {
  const sectionRef = useRef(null);
  const contentRef = useRef(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const stages = gsap.utils.toArray(".pipe-stage");

      if (prefersReducedMotion()) {
        /* Show the Notes stage and stop -- it's the most legible of the
           three as a still frame, and it's the product's core output. */
        gsap.set(stages, { autoAlpha: 0 });
        gsap.set(".pipe-stage--notes", { autoAlpha: 1, y: 0 });
        return;
      }

      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.from(".hero-eyebrow", { opacity: 0, y: 10, duration: 0.5 })
        .from(
          ".reveal-word-inner",
          { yPercent: 110, duration: 0.8, stagger: 0.05, ease: "expo.out" },
          "-=0.15"
        )
        .from(".hero-ctas > *", { opacity: 0, y: 12, duration: 0.5, stagger: 0.08 }, "-=0.45")
        .from(".pipeline", { opacity: 0, scale: 0.92, duration: 0.7 }, "-=0.5")
        .from(".hero-scroll-cue", { opacity: 0, duration: 0.5 }, "-=0.1");

      /* Pipeline loop: one panel cycling recording -> notes -> quiz.
         Each stage holds for DWELL then cross-fades to the next, so the
         hero demonstrates the transform rather than decorating around
         it. */
      const DWELL = 3.4;
      gsap.set(stages, { autoAlpha: 0, y: 26, scale: 0.93 });
      const loop = gsap.timeline({ repeat: -1, delay: 0.9 });
      stages.forEach((stage, i) => {
        const at = i * DWELL;
        loop
          // Scaling up on entry (and down on exit) is what makes each
          // stage read as stepping forward rather than crossfading --
          // the same move the Journey cards make.
          .to(stage, { autoAlpha: 1, y: 0, scale: 1, duration: 0.7, ease: "power3.out" }, at)
          .to(
            stage,
            { autoAlpha: 0, y: -26, scale: 0.95, duration: 0.6, ease: "power2.in" },
            at + DWELL - 0.6
          );
        // The panel itself breathes with the stage change, so the whole
        // card participates instead of only its contents.
        loop.fromTo(
          ".pipeline",
          { scale: 0.985 },
          { scale: 1, duration: 0.7, ease: "power3.out" },
          at
        );
      });

      // Equalizer bars run on their own loop, independent of the stage cycle.
      gsap.to(".pipe-bar", {
        scaleY: 1,
        duration: 0.5,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
        stagger: { each: 0.07, from: "random" },
      });

      // Scroll-linked exit: fades/lifts/scales down as the hero leaves.
      gsap.to(contentRef.current, {
        opacity: 0.15,
        y: -50,
        scale: 0.97,
        ease: "none",
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <section className="hero" ref={sectionRef}>
      <div className="hero-fields" aria-hidden="true">
        <span className="hero-field hero-field--1" />
        <span className="hero-field hero-field--2" />
        <span className="hero-field hero-field--3" />
      </div>

      <div className="container hero-grid" ref={contentRef}>
        <div className="hero-copy">
          <span className="eyebrow hero-eyebrow">Urdu · English · Arabic — one upload</span>
          <h1 className="hero-title">
            {splitWords("Lectures, turned into notes you'll")}
            <span className="reveal-word">
              <span className="reveal-word-inner accent-word">study.</span>
            </span>
          </h1>
          <div className="hero-ctas">
            <Link to="/app" className="btn btn-lg">
              Upload a lecture
            </Link>
            <span className="hero-cta-note">No trimming or prep needed first.</span>
          </div>
        </div>

        <div className="hero-scene" aria-hidden="true">
          <PipelinePanel />
        </div>
      </div>

      {!prefersReducedMotion() && (
        <div className="hero-scroll-cue">
          <span>Scroll</span>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 5l5 5 5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      )}
    </section>
  );
}

/* One panel, three stacked stages. All three are in the DOM at once and
   absolutely positioned on top of each other; the GSAP loop above owns
   which is visible. Keeping them all mounted (rather than swapping via
   React state) means the loop never triggers a re-render. */
function PipelinePanel() {
  return (
    <div className="pipeline">
      <div className="pipe-stage pipe-stage--rec">
        <div className="pipe-label"><span className="pipe-pip" />Recording</div>
        <div className="pipe-bars">
          {Array.from({ length: 16 }).map((_, i) => (
            <i className="pipe-bar" key={i} />
          ))}
        </div>
        <div className="pipe-langs">
          <span className="pipe-lang">EN</span>
          <span className="pipe-lang pipe-lang--gold">اردو</span>
          <span className="pipe-lang">عربي</span>
        </div>
      </div>

      <div className="pipe-stage pipe-stage--notes">
        <div className="pipe-label">Notes</div>
        <div className="pipe-note-head">Bayes' theorem</div>
        <div className="pipe-line" style={{ width: "100%" }} />
        <div className="pipe-line" style={{ width: "84%" }} />
        <div className="pipe-line" style={{ width: "92%" }} />
        <div className="pipe-line" style={{ width: "66%" }} />
        <div className="pipe-cite">Transcript · 24:10</div>
      </div>

      <div className="pipe-stage pipe-stage--quiz">
        <div className="pipe-label">Quiz</div>
        <div className="pipe-question">What does Bayes' theorem update?</div>
        <div className="pipe-option is-correct">
          <span className="pipe-dot" />A prior probability
        </div>
        <div className="pipe-option">
          <span className="pipe-dot" />A sample mean
        </div>
        <div className="pipe-option">
          <span className="pipe-dot" />A standard error
        </div>
      </div>
    </div>
  );
}

/* Wraps each word of a plain string in the same overflow-hidden mask
   the accent word below uses, so the whole headline reveals as one
   consistent stagger instead of the emphasized phrase popping in on
   its own timing. The .trim() matters: split(" ") on a trailing space
   yields an empty final word, which rendered as a zero-width masked
   span butted against "study." with no gap. */
function splitWords(text) {
  return text
    .trim()
    .split(" ")
    .map((word, i) => (
      <span className="reveal-word" key={i}>
        <span className="reveal-word-inner">{word}</span>
        &nbsp;
      </span>
    ));
}

/* ── How it works ────────────────────────────────────────────
   Above 900px (and only when motion is allowed) the section pins and
   the six steps translate horizontally as the user scrolls down.
   Everywhere else the same markup falls back to the vertical scrubbed
   timeline.

   The important property here is that BOTH paths render the same step
   markup -- the layout switch lives in a CSS media query using the
   identical condition string, and only the motion is branched in JS.
   A duplicated mobile DOM is what makes this pattern rot, because the
   two copies drift apart the first time someone edits one of them.

   The pin length is bounded to ~1.8 viewport heights regardless of how
   wide the track is, so the amount of hijacked scroll stays predictable
   instead of scaling with step count, and the progress bar is visible
   throughout so the user can see how long it lasts. */
const STEPS = [
  {
    tag: "01",
    title: "Upload",
    desc: "Drop in a Zoom recording, a phone video, or a raw audio file. No trimming or prep needed first.",
    icon: <UploadIcon />,
  },
  {
    tag: "02",
    title: "Transcribe",
    desc: "Speech-to-text runs across Urdu, English, and Arabic in the same clip, correcting script and stripping filler as it goes.",
    icon: <WaveformIcon />,
  },
  {
    tag: "03",
    title: "Notes",
    desc: "Structured notes appear automatically — section by section, key terms called out, nothing invented.",
    icon: <DocIcon />,
  },
  {
    tag: "04",
    title: "Quiz",
    desc: "MCQs, short-answer, and long-answer questions generate straight from what the instructor actually taught.",
    icon: <QuizIcon />,
  },
  {
    tag: "05",
    title: "Chat",
    desc: "Ask anything about the lecture. Every answer cites the transcript line it came from, or says the lecture didn't cover it.",
    icon: <ChatIcon />,
  },
  {
    tag: "06",
    title: "Saved workspace",
    desc: "The lecture stays searchable, chat history and quiz results included, ready the next time you open it.",
    icon: <FolderIcon />,
  },
];

function HowItWorks() {
  const sectionRef = useRef(null);
  const trackRef = useRef(null);
  const progressRef = useRef(null);
  const vTrackFillRef = useRef(null);
  const [active, setActive] = useState(0);

  useLayoutEffect(() => {
    const mm = gsap.matchMedia(sectionRef);

    /* ---- Desktop: pinned horizontal storyboard ---- */
    mm.add(DESKTOP_MQ, () => {
      const track = trackRef.current;
      // Measured in a callback so invalidateOnRefresh can re-run it after
      // a resize -- a hard-coded distance goes wrong the moment the
      // viewport or font size changes.
      const distance = () => Math.max(0, track.scrollWidth - track.parentElement.clientWidth);

      gsap.to(track, {
        x: () => -distance(),
        ease: "none",
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: () => "+=" + window.innerHeight * 1.8,
          pin: true,
          scrub: 0.6,
          anticipatePin: 1,
          invalidateOnRefresh: true,
          /* With more than one pinned ScrollTrigger on a page, they must
             refresh in document order -- highest priority first. Without
             this, the Journey pin below gets its start position measured
             before this section's pin-spacer has added its height to the
             document, so both pins end up with wrong start/end values and
             neither one actually engages. Top-most section = highest. */
          refreshPriority: 2,
          onUpdate: (self) => {
            if (progressRef.current) {
              gsap.set(progressRef.current, { scaleX: self.progress });
            }
            // Only calls setState on an actual step change (6 renders
            // across the whole pin), not on every scrub frame.
            const i = Math.min(STEPS.length - 1, Math.floor(self.progress * STEPS.length));
            setActive((prev) => (prev === i ? prev : i));
          },
        },
      });
    });

    /* ---- Fallback: vertical scrubbed timeline ---- */
    mm.add(FALLBACK_MQ, () => {
      const items = gsap.utils.toArray(".hiw-item");
      const reduced = prefersReducedMotion();

      if (!reduced) {
        items.forEach((item) => {
          gsap.from(item.querySelector(".hiw-item-content"), {
            opacity: 0,
            y: 26,
            duration: 0.55,
            ease: "power2.out",
            scrollTrigger: {
              trigger: item,
              start: "top 85%",
              toggleActions: "play none none reverse",
            },
          });
        });

        if (vTrackFillRef.current) {
          gsap.set(vTrackFillRef.current, { scaleY: 0 });
          gsap.to(vTrackFillRef.current, {
            scaleY: 1,
            ease: "none",
            scrollTrigger: {
              trigger: ".hiw-timeline",
              start: "top 60%",
              end: "bottom 60%",
              scrub: true,
            },
          });
        }
      }

      // Active-step tracking is a highlight, not movement -- it stays on
      // even under reduced motion since it aids comprehension.
      items.forEach((item, i) => {
        ScrollTrigger.create({
          trigger: item,
          start: "top 60%",
          end: "bottom 60%",
          onToggle: (self) => {
            if (self.isActive) setActive(i);
          },
        });
      });
    });

    return () => mm.revert();
  }, []);

  return (
    <section id="how-it-works" className="section section-ink hiw-section" ref={sectionRef}>
      <div className="container">
        <div className="section-head">
          <div className="section-eyebrow">How it works</div>
          <h2 className="section-title">One recording becomes six things you can use</h2>
          <p className="section-desc">
            Scroll to walk through what happens between uploading a lecture and studying from it.
          </p>
        </div>
      </div>

      <div className="container hiw-viewport">
        <div className="hiw-timeline" ref={trackRef}>
          <div className="hiw-track" aria-hidden="true">
            <div className="hiw-track-fill" ref={vTrackFillRef} />
          </div>

          {STEPS.map((step, i) => (
            <div className={`hiw-item ${i === active ? "active" : ""}`} key={step.title}>
              <span className="hiw-item-marker" aria-hidden="true" />
              <div className="hiw-item-content">
                <div className="hiw-item-icon">{step.icon}</div>
                <div className="hiw-item-number">{step.tag} / 06</div>
                <h3 className="hiw-item-title">{step.title}</h3>
                <p className="hiw-item-desc">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="container">
        <div className="hiw-progress" aria-hidden="true">
          <span className="hiw-progress-fill" ref={progressRef} />
        </div>
      </div>
    </section>
  );
}

/* ── Journey: full-viewport pinned product walkthrough ───────
   The section pins and the reader scrolls through one lecture moving
   all the way across the product: upload -> transcribe -> notes. Each
   stage owns a third of the pinned scroll, gets the whole viewport
   while it's active, and scales up as it takes over so the transition
   reads as the demo stepping forward rather than a crossfade between
   two flat pictures.

   Same matchMedia contract as HowItWorks: identical condition strings
   in JS and CSS, one set of markup for both paths, and the fallback is
   the three stages simply stacked and revealed on enter. This is the
   second pinned section on the page, which is a real cost in hijacked
   scroll -- it's here because an immersive walkthrough was the explicit
   ask, and the pin is bounded to 2.4 viewport heights with the stage
   dots always visible so its length stays legible. */
const JOURNEY = [
  { tag: "01", title: "Upload the recording", desc: "A Zoom file, a phone video, or raw audio — no trimming first." },
  { tag: "02", title: "It becomes a transcript", desc: "Urdu, English and Arabic in the same clip, each kept in its own script." },
  { tag: "03", title: "Notes you can trust", desc: "Structured automatically, and every answer points back at the transcript." },
];

function Journey() {
  const sectionRef = useRef(null);
  const [stage, setStage] = useState(0);

  useLayoutEffect(() => {
    const mm = gsap.matchMedia(sectionRef);

    mm.add(DESKTOP_MQ, () => {
      const panels = gsap.utils.toArray(".journey-stage");
      gsap.set(panels, { autoAlpha: 0, scale: 0.92, y: 24 });
      gsap.set(panels[0], { autoAlpha: 1, scale: 1, y: 0 });

      /* Laid out on a 0-99 scale so each stage owns exactly 33 units --
         the numbers below read as "percent through the journey". */
      const tl = gsap.timeline({
        defaults: { ease: "power2.out" },
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: () => "+=" + window.innerHeight * 2.4,
          pin: true,
          scrub: 0.6,
          anticipatePin: 1,
          invalidateOnRefresh: true,
          // Lower than HowItWorks above it -- see the note there.
          refreshPriority: 1,
          onUpdate: (self) => {
            const i = Math.min(JOURNEY.length - 1, Math.floor(self.progress * JOURNEY.length));
            setStage((prev) => (prev === i ? prev : i));
          },
        },
      });

      panels.forEach((panel, i) => {
        const at = i * 33;
        if (i > 0) {
          tl.to(panels[i - 1], { autoAlpha: 0, scale: 0.94, y: -24, duration: 7 }, at - 4);
          tl.to(panel, { autoAlpha: 1, scale: 1, y: 0, duration: 9 }, at);
          // Inner beats, scrubbed inside this stage's own window.
          tl.fromTo(
            panel.querySelectorAll(".jrn-beat"),
            { autoAlpha: 0, y: 14 },
            { autoAlpha: 1, y: 0, duration: 7, stagger: 4 },
            at + 4
          );
        } else {
          /* Stage 1 is already on screen the instant the section pins,
             so its content must be too -- animating it in from nothing
             meant the reader arrived at an empty card and had to scroll
             before anything appeared. The progress bar filling and the
             waveform resolving (below) are this stage's motion instead. */
          gsap.set(panel.querySelectorAll(".jrn-beat"), { autoAlpha: 1, y: 0 });
        }
        const fill = panel.querySelector(".jrn-fill");
        if (fill) tl.fromTo(fill, { scaleX: 0 }, { scaleX: 1, duration: 14, ease: "none" }, at + 4);
        const ticks = panel.querySelectorAll(".jrn-tick");
        if (ticks.length) {
          tl.fromTo(
            ticks,
            { scaleY: 0.08 },
            { scaleY: () => 0.3 + Math.random() * 0.7, duration: 10, ease: "none", stagger: 0.35 },
            at + 6
          );
        }
      });
    });

    mm.add(FALLBACK_MQ, () => {
      const panels = gsap.utils.toArray(".journey-stage");
      const reduced = prefersReducedMotion();
      gsap.set(".jrn-fill", { scaleX: 1 });
      gsap.set(".jrn-tick", { scaleY: 0.6 });
      if (reduced) return;
      panels.forEach((panel) => {
        gsap.from(panel, {
          opacity: 0,
          y: 24,
          duration: 0.6,
          ease: "power2.out",
          scrollTrigger: { trigger: panel, start: "top 85%", toggleActions: "play none none reverse" },
        });
      });
    });

    return () => mm.revert();
  }, []);

  return (
    <section id="features" className="section journey-section" ref={sectionRef}>
      <div className="container journey-inner">
        <div className="section-head journey-head">
          <div className="section-eyebrow">The journey</div>
          <h2 className="section-title">Watch one lecture go through it</h2>
        </div>

        <div className="journey-stages">
          {JOURNEY.map((s, i) => (
            <div className={`journey-stage journey-stage--${i + 1}`} key={s.tag}>
              <div className="jrn-copy">
                <span className="jrn-tag">{s.tag}</span>
                <h3 className="jrn-title">{s.title}</h3>
                <p className="jrn-desc">{s.desc}</p>
              </div>
              <div className="jrn-visual" aria-hidden="true">
                {i === 0 && <JourneyUpload />}
                {i === 1 && <JourneyTranscribe />}
                {i === 2 && <JourneyNotes />}
              </div>
            </div>
          ))}
        </div>

        <div className="journey-dots" aria-hidden="true">
          {JOURNEY.map((s, i) => (
            <span className={`journey-dot ${i === stage ? "active" : ""}`} key={s.tag} />
          ))}
        </div>
      </div>
    </section>
  );
}

function JourneyUpload() {
  return (
    <div className="jrn-card">
      <div className="jrn-beat jrn-filerow">
        <span className="jrn-fileicon"><UploadIcon /></span>
        <span className="jrn-filename">stats-lecture-04.mp3</span>
        <span className="jrn-filesize">58:12</span>
      </div>
      <div className="jrn-beat jrn-progress"><span className="jrn-fill" /></div>
      <div className="jrn-beat jrn-wave">
        {Array.from({ length: 30 }).map((_, i) => <i className="jrn-tick" key={i} />)}
      </div>
    </div>
  );
}

function JourneyTranscribe() {
  return (
    <div className="jrn-card">
      <div className="jrn-beat jrn-line">
        <span className="jrn-tag-sm">EN</span>Bayes' theorem lets us update a belief…
      </div>
      <div className="jrn-beat jrn-line">
        <span className="jrn-tag-sm jrn-tag-sm--gold">اردو</span>یعنی نئی معلومات ملنے پر
      </div>
      <div className="jrn-beat jrn-line">
        <span className="jrn-tag-sm">EN</span>…as new evidence arrives at 24:10.
      </div>
      <div className="jrn-beat jrn-line jrn-line--muted">
        <span className="jrn-tag-sm jrn-tag-sm--gold">عربي</span>نفس الفكرة بصيغة أخرى
      </div>
    </div>
  );
}

function JourneyNotes() {
  return (
    <div className="jrn-card">
      <div className="jrn-beat jrn-notehead">Bayes' theorem</div>
      <div className="jrn-beat jrn-noteline" style={{ width: "100%" }} />
      <div className="jrn-beat jrn-noteline" style={{ width: "88%" }} />
      <div className="jrn-beat jrn-answer">
        Updates a prior probability as new evidence arrives.
        <span className="jrn-cite"><LinkIcon /> Transcript · 24:10</span>
      </div>
    </div>
  );
}

/* Short claims band. The journey above does the showing; this does the
   telling, in four lines rather than four paragraphs. */
function Claims() {
  const sectionRef = useRef(null);

  useLayoutEffect(() => {
    if (prefersReducedMotion()) return;
    const ctx = gsap.context(() => {
      gsap.from(".features-check-item", {
        opacity: 0,
        y: 14,
        duration: 0.5,
        stagger: 0.08,
        ease: "power2.out",
        scrollTrigger: { trigger: ".features-checklist", start: "top 88%", toggleActions: "play none none reverse" },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <section className="section section-claims" ref={sectionRef}>
      <div className="container claims-inner">
        <div className="section-head">
          <div className="section-eyebrow">Features</div>
          <h2 className="section-title">One rule: don't make things up</h2>
          <p className="section-desc">The transcript is the source of truth — never the model.</p>
        </div>

        <ul className="features-checklist">
          <li className="features-check-item">Urdu, English and Arabic in one recording</li>
          <li className="features-check-item">Every answer cites its transcript line</li>
          <li className="features-check-item">Quizzes built only from what was taught</li>
          <li className="features-check-item">Says so when the lecture didn't cover it</li>
        </ul>

        <div className="features-cta-group">
          <Link to="/app" className="btn btn-lg">
            Upload a lecture
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ── FAQ ────────────────────────────────────────────────────
   Plain accordion: one open at a time, driven by React state rather
   than <details>, because <details> can't animate its own open/close.
   The panel animates via grid-template-rows 0fr -> 1fr, which is the
   one CSS-only way to transition to a content-derived height without
   measuring anything in JS.

   The button carries aria-expanded and controls the panel by id, so
   this is operable from the keyboard and announced correctly without
   any extra scripting. */
const FAQS = [
  {
    q: "What can I upload?",
    a: "A Zoom recording, a phone video, or a raw audio file. No trimming or prep needed first — upload the recording as it came off the device.",
  },
  {
    q: "Does it handle Urdu and English in the same lecture?",
    a: "Yes. Urdu, English, and Arabic can appear in the same clip. Urdu that comes back in Hindi script is corrected back to Urdu, and filler is stripped as it goes.",
  },
  {
    q: "How long does processing take?",
    a: "Transcription, cleaning, and indexing all run before the upload finishes, so a one-hour lecture can take several minutes. Keep the tab open until it completes — there's no background job to come back to yet.",
  },
  {
    q: "Can it answer things the lecture didn't cover?",
    a: "No, and that's deliberate. If the transcript doesn't contain the answer, chat tells you the lecture didn't cover it instead of filling the gap from the model's general knowledge.",
  },
  {
    q: "Where do the quiz questions come from?",
    a: "Only from the transcript of your lecture — MCQ, short-answer, and long-answer, generated from what the instructor actually said rather than from the topic in general.",
  },
  {
    q: "Do my lectures stay available afterwards?",
    a: "Yes. Each lecture keeps its transcript, notes, chat history, and quiz results in your workspace, so you can reopen it later without re-uploading.",
  },
];

function Faq() {
  const sectionRef = useRef(null);
  const [open, setOpen] = useState(0);

  useLayoutEffect(() => {
    if (prefersReducedMotion()) return;
    const ctx = gsap.context(() => {
      gsap.from(".faq-item", {
        opacity: 0,
        y: 16,
        duration: 0.5,
        stagger: 0.07,
        ease: "power2.out",
        scrollTrigger: {
          trigger: ".faq-list",
          start: "top 85%",
          toggleActions: "play none none reverse",
        },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <section id="faq" className="section section-faq" ref={sectionRef}>
      <div className="container">
        <div className="section-head">
          <div className="section-eyebrow">FAQ</div>
          <h2 className="section-title">Questions worth asking first</h2>
        </div>

        <div className="faq-list">
          {FAQS.map((item, i) => {
            const isOpen = i === open;
            return (
              <div className={`faq-item ${isOpen ? "open" : ""}`} key={item.q}>
                <button
                  type="button"
                  className="faq-question"
                  aria-expanded={isOpen}
                  aria-controls={`faq-panel-${i}`}
                  onClick={() => setOpen(isOpen ? -1 : i)}
                >
                  <span>{item.q}</span>
                  <ChevronIcon />
                </button>
                {/* No `hidden` attribute here: it would remove the panel
                    outright and there'd be nothing left to animate. The
                    collapse is grid-template-rows 0fr, and the inner
                    element takes visibility:hidden so a closed panel
                    still leaves the tab order and the accessibility
                    tree rather than lurking invisibly in both. */}
                <div className="faq-panel" id={`faq-panel-${i}`} role="region">
                  <div className="faq-panel-inner">
                    <p>{item.a}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ── Final CTA ──────────────────────────────────────────────
   The espresso anchor at the bottom of the warm ramp. Same label and
   destination as the hero CTA -- this pass changes how the landing
   looks, not what its buttons do. */
function FinalCta() {
  const ctaRef = useRef(null);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const ctx = gsap.context(() => {
      gsap.from(ctaRef.current, {
        opacity: 0,
        y: 20,
        duration: 0.6,
        ease: "power3.out",
        scrollTrigger: { trigger: ctaRef.current, start: "top 85%", toggleActions: "play none none reverse" },
      });
    });
    return () => ctx.revert();
  }, []);

  return (
    <section className="section section-cta-outer">
      <div className="cta-band" ref={ctaRef}>
        <h2>Your next lecture doesn't have to be re-watched</h2>
        <p>
          Upload one recording and get the transcript, the notes, and the quiz back — in the
          language it was actually taught in.
        </p>
        <Link to="/app" className="btn btn-lg">
          Upload a lecture
        </Link>
      </div>
    </section>
  );
}

/* ── Icons ──────────────────────────────────────────────────
   Restrained line-art (1.5px stroke, rounded joins), only ever using
   currentColor so each card/panel can tint them via its own accent. */
function ChevronIcon() {
  return (
    <svg className="faq-chevron" width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M5 8l5 5 5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
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
    <svg width="14" height="14" viewBox="0 0 20 20" fill="none">
      <path d="M8.5 11.5l3-3M7 13l-2 2a2.5 2.5 0 01-3.5-3.5l2-2M13 7l2-2a2.5 2.5 0 013.5 3.5l-2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function UploadIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
      <path d="M10 13V3.5M10 3.5L6 7.5M10 3.5l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3.5 13v2a1.5 1.5 0 001.5 1.5h10a1.5 1.5 0 001.5-1.5v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function WaveformIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
      <path d="M2.5 10h1.5M6 6v8M9 3v14M12 6v8M15.5 8v4M18 10h-1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function DocIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
      <path d="M5 2.5h7l3.5 3.5v11a1 1 0 01-1 1H5a1 1 0 01-1-1v-13a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M7 10h6M7 13h6M7 7h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
function QuizIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
      <rect x="3" y="3" width="14" height="14" rx="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6.5 10.5l2 2 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function FolderIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
      <path d="M2.5 5.5a1 1 0 011-1H8l1.6 2h6.9a1 1 0 011 1v7.5a1 1 0 01-1 1h-13a1 1 0 01-1-1v-9.5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M7 12l2 2 4-4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
