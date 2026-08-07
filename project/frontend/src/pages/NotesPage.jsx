import { useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { api, ApiError } from "../api";
import ErrorBanner from "../components/ErrorBanner";

const staggerList = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };
const fadeUp = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.16, 1, 0.3, 1] } },
};

export default function NotesPage() {
  useOutletContext();
  const { lectureId } = useParams();
  const [notesList, setNotesList] = useState(null);
  const [activeNotes, setActiveNotes] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setNotesList(null);
    setActiveNotes(null);
    api
      .listNotes(lectureId)
      .then((list) => {
        setNotesList(list);
        if (list.length > 0) setActiveNotes(list[0]);
      })
      .catch(() => setNotesList([]));
  }, [lectureId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const notes = await api.generateNotes(lectureId);
      setNotesList((prev) => [notes, ...(prev || [])]);
      setActiveNotes(notes);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Notes generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  if (notesList === null) {
    return (
      <p className="muted">
        <span className="spinner" /> Loading notes...
      </p>
    );
  }

  const data = activeNotes?.data;

  return (
    <div>
      <div className="notes-toolbar">
        <div className="notes-toolbar-left">
          {notesList.length > 0 && (
            <select
              className="quiz-select"
              value={activeNotes?.id || ""}
              onChange={(e) => setActiveNotes(notesList.find((n) => n.id === Number(e.target.value)))}
            >
              {notesList.map((n) => (
                <option key={n.id} value={n.id}>
                  {new Date(n.created_at).toLocaleString()} · {n.num_sections} sections
                </option>
              ))}
            </select>
          )}
        </div>
        <button className="btn btn-secondary btn-sm" onClick={handleGenerate} disabled={generating}>
          {generating && <span className="spinner" />}
          {generating ? "Generating..." : notesList.length > 0 ? "Regenerate notes" : "Generate notes"}
        </button>
      </div>

      <ErrorBanner message={error} />

      {!activeNotes && !generating && (
        <div className="empty-state">
          <p>No notes generated yet for this lecture.</p>
          <p className="muted" style={{ marginTop: 6 }}>
            We'll read the whole transcript and pull out the important stuff -- definitions, key
            facts, and conclusions -- and drop the filler.
          </p>
        </div>
      )}

      {generating && !activeNotes && (
        <div className="empty-state">
          <p>
            <span className="spinner" /> Reading the transcript and condensing it...
          </p>
          <p className="muted" style={{ marginTop: 6 }}>
            Long lectures are summarized in batches, so this can take a little while.
          </p>
        </div>
      )}

      {activeNotes && data && (
        <motion.div key={activeNotes.id} initial="hidden" animate="show" variants={staggerList}>
          <div className="export-row" style={{ marginBottom: 20 }}>
            <a className="btn-icon-text" href={api.notesExportUrl(lectureId, activeNotes.id, "md")}>
              <DownloadIcon /> .md
            </a>
            <a className="btn-icon-text" href={api.notesExportUrl(lectureId, activeNotes.id, "json")}>
              <DownloadIcon /> .json
            </a>
          </div>

          {data.summary && (
            <motion.div className="card notes-summary-card" variants={fadeUp}>
              <div className="section-eyebrow">Summary</div>
              <p>{data.summary}</p>
            </motion.div>
          )}

          {(data.sections || []).map((section, i) => (
            <motion.div key={i} className="card notes-section-card" variants={fadeUp}>
              <h3 className="notes-section-heading">{section.heading}</h3>
              <ul className="notes-points">
                {(section.points || []).map((point, j) => (
                  <li key={j}>{point}</li>
                ))}
              </ul>
            </motion.div>
          ))}

          {data.key_terms?.length > 0 && (
            <motion.div className="card" variants={fadeUp}>
              <h3 className="notes-section-heading">Key Terms</h3>
              <div className="notes-glossary">
                {data.key_terms.map((kt, i) => (
                  <div key={i} className="notes-term-card">
                    <div className="notes-term-name">{kt.term}</div>
                    <div className="notes-term-def">{kt.definition}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  );
}

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
      <path
        d="M7 1.5v8M4 6.5L7 9.5l3-3M2 11.5h10"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}