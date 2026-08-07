# Landing Page Redesign — Warm Tonal System + Scroll Storyboard

Date: 2026-08-06
Scope: `src/pages/LandingPage.jsx`, the landing token block in `src/index.css`,
`src/components/layout/Footer.jsx` (styling only).

## Problem

Two distinct problems, only one of which was in the original ask.

1. **Section boundaries collide.** The landing alternates `.section-ink`
   (`#0a0a0a`) with `.section-paper` (`#ffffff`). Every boundary is a hard slam
   between the two extremes of the value scale with nothing in between.

2. **The hero visual decorates rather than demonstrates.** The right column is
   an inline SVG (note card + connector lines + language badges) that GSAP pops
   in on mount and then floats on idle sine loops. It is not a static image, but
   its motion is ambient — it plays once and then says nothing further about what
   the product does.

A third issue found while reading the file, in scope because it is dead weight in
the component being rewritten: `FinalCta()` (line 586) builds a live GSAP
ScrollTrigger timeline against `ctaRef` and then returns an empty `<div>`. It is
rendered by `LandingPage`. `BentoCard` (line 514) and `ListIcon` (line 635) are
defined and never referenced — leftovers from the earlier bento-grid version of
the Features section.

## Decisions

| Decision | Choice | Constraint that forced it |
|---|---|---|
| Palette | Warm tonal: white → cream → skin, gold accent | User preference, arrived at after considering indigo, silver/graphite, and monochrome directions |
| Ramp depth | Light page, one espresso anchor at CTA + footer | An all-light page reads flat without very careful shadow work; the anchor gives the page a climax without reintroducing the hue clash |
| Accent | Existing `#e2a13a`, unchanged | It is already the sitewide `--accent`; keeping it means the landing finally agrees with the app's buttons instead of running a separate system |
| Hero visual | Live pipeline loop (waveform → notes → quiz) | Chosen from three live animated mockups; it demonstrates the product rather than decorating around it |
| How It Works | Pinned horizontal storyboard | User choice, made with the scroll-jacking and mobile-fallback tradeoffs stated |
| Features | Scrubbed parallax, no pin | Assumption: two consecutive pinned sections is exhausting and doubles the fragility |
| Hero CTA behaviour | Unchanged | User's explicit call — this is a visual pass, not a behaviour change |

## Known issue, accepted and not fixed

`/app` is behind `ProtectedRoute`, so the hero CTA ("Upload a lecture" → `/app`)
bounces a logged-out visitor to `/login` with no explanation. The user chose to
leave this as-is for this pass. Recorded here so it is not rediscovered as a bug.

## 1. Tokens

Replace the landing-only block in `index.css`. The sitewide `--accent` / `--ink`
/ `--bg` tokens used by nav, forms, chat, and quiz are not touched — the existing
comment in that file promises this and the promise holds.

```
--warm-50   #fffdf8   warm white     hero
--warm-100  #faf3e8   cream          how it works
--warm-200  #f4e9d8   skin           features
--warm-300  #ecdcc2   sand           dividers, insets
--warm-400  #e0cba6   deep sand      borders on tinted ground

--espresso-800 #2a2118   final CTA
--espresso-900 #1c150e   footer

--warm-ink        #3a2e1e   body text on light
--warm-ink-muted  #6b5b45
--warm-line       rgba(58,46,30,.12)

--gold      #e2a13a   unchanged, same as sitewide --accent
--gold-deep #b07a1c   gold text on light backgrounds
```

**Contrast constraint.** `--gold` on `--warm-50` is ~2.1:1 and fails WCAG AA for
body text. Gold is therefore only ever used as a fill (CTA background with dark
text), as large or decorative elements, or as `--gold-deep` when it must be small
text on a light ground. On espresso it is ~6.9:1 and safe.

**Migration strategy.** Old landing variable names are repointed to new values
where the mapping is honest, so most of the existing CSS follows without edits.
This explicitly does *not* work for `.section-ink`, which is near-black with light
text today and becomes cream with dark text — that requires a real inversion of
its text, border, and marker colors, not a token swap.

## 2. Section ladder

```
hero          #fffdf8
how-it-works  #faf3e8
features      #f4e9d8
final CTA     #2a2118
footer        #1c150e
```

Adjacent light sections differ by one step, so no boundary reads as a seam. Each
section carries a short gradient at its top bleeding from the previous tone. The
single espresso jump is the deliberate climax; being in the same hue family it
reads as depth rather than collision.

## 3. Hero

Structure unchanged: two-column grid, eyebrow, one headline, one CTA, scroll cue.
The right column's SVG scene is replaced.

**Pipeline panel.** One panel cycling three states on a ~9s GSAP loop:

1. **Recording** — equalizer bars, with the EN / اردو / عربي badges retained so
   the multilingual claim survives the redesign
2. **Notes** — structured lines drawing in
3. **Quiz** — options, one filling gold

Cross-fade plus a small y-translate between states, ~3s dwell each.

**Reduced motion:** renders the Notes state statically, no loop. Follows the
existing `prefersReducedMotion()` pattern already in the file.

## 4. Animated background

Two to three large radial gold/cream fields behind the hero, drifting on 14–20s
loops.

Implemented as **CSS keyframes, not GSAP**. They animate only `transform` and
`opacity`, so they stay on the compositor and cost no JS frame budget, and the
existing global reduced-motion override in `index.css` disables them with no extra
code. GSAP is reserved for motion that genuinely needs scroll-linking.

## 5. How It Works — pinned horizontal storyboard

The section pins to the viewport; the six steps translate horizontally as the user
scrolls down.

**Single-DOM requirement.** The "desktop and mobile versions drift apart" failure
mode is only real when the fallback is duplicate markup. `gsap.matchMedia()` drives
two behaviours off the *same* step markup:

- `(min-width: 900px)` and no reduced-motion preference → pinned horizontal
  translation, scrubbed
- otherwise → the existing vertical scrubbed timeline, unchanged

Step content is authored once. It cannot diverge.

**Bounded pin.** Pin length is set so the six steps consume roughly 1.5 viewport
heights of scroll. The progress rail stays visible throughout, so the user can see
how long the pin lasts — this is what makes a hijacked scroll tolerable rather than
alarming.

**Active-step highlighting** stays state-driven and remains on under reduced
motion, as it does today: it aids comprehension rather than adding motion.

## 6. Features — scrubbed parallax, no pin

Ground becomes skin; the floating cards become warm-white with `--warm-line`
borders.

Motion upgraded from one-shot enter triggers to scroll-position-scrubbed:

- the three scene cards drift at three different depths tied to scroll progress
- the checklist reveals progressively across the section's scroll range rather
  than in a single burst on enter
- existing idle float loops are retained on top of the scrubbed transforms

Reversible on scroll-up, since scrubbed animation follows the scrollbar in both
directions.

## 7. Final CTA and footer

`FinalCta()` is rebuilt as a real espresso section carrying a headline and the gold
CTA, replacing the current empty-`<div>`-with-a-live-timeline. Its button uses the
same label and destination as the hero CTA ("Upload a lecture" → `/app`) — no new
behaviour, consistent with the decision above.

`Footer` gets `--espresso-900`. Note this footer is shared via `Layout` with
`/login` and `/signup`, so the change appears on those two pages as well. This is
accepted; no other part of those pages is touched.

## 8. Dead code removed

- `BentoCard` (line 514) — defined, never rendered
- `ListIcon` (line 635) — defined, never referenced
- the empty-return body of `FinalCta` — replaced, not deleted

## 9. Verification plan

Behavioral, run against `npm run dev`:

1. Each section rendered at 1440 / 768 / 390 px width, checking the ladder shows no
   hard seam at any boundary.
2. Hero pipeline loop watched through two full cycles, checking for jank at the
   state transitions.
3. How It Works scrolled at ≥900px — confirm pin engages, six steps traverse, pin
   releases cleanly, and the following section is not overlapped.
4. Same section scrolled at 390px — confirm the vertical fallback path runs and the
   pin never engages.
5. Window resized across the 900px breakpoint mid-page — confirm `matchMedia`
   swaps cleanly without leaving a stuck pin or orphaned ScrollTrigger.
6. `prefers-reduced-motion: reduce` toggled in devtools — confirm the hero loop
   stops, the background fields stop, and How It Works takes the vertical path.
7. Contrast spot-checked on gold-on-light, the one pairing likely to fail.

Item 5 is the one most likely to surface a real bug; `matchMedia` teardown with
pinning is where this kind of implementation usually breaks.

## Out of scope

- App workspace pages (chat, quiz, notes, transcript, lecture list)
- `FloatingNav`, `/login`, `/signup` (beyond the shared footer's background)
- Any backend, API, or auth behaviour
