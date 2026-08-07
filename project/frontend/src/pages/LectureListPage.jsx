import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, ApiError } from "../api";
import { useLectures } from "../context/LecturesContext.jsx";
import StatusBadge from "../components/StatusBadge";
import ErrorBanner from "../components/ErrorBanner";

/* Same easing/duration scale as the rest of the app's Framer Motion
   (FloatingNav, ChatPage) -- entrance is a quiet fade+rise, not a
   flashy reveal, and the recent-lecture grid staggers in the way the
   landing's feature grid does. */
const fadeUp = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } },
};
const staggerGrid = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
};

const OUTPUT_LANGUAGES = ["mixed", "urdu", "english", "arabic"];

const EMPTY_FORM = {
  title: "",
  course: "",
  instructor: "",
  semester: "",
  lecture_date: "",
  output_language: "mixed",
  language_code_hint: "",
  file: null,
};

/* This is the /app index route -- shown when no specific lecture is
   selected. The full lecture list now lives in the sidebar nav, so this
   pane is a "start something" screen: the upload form, plus a quick
   grid back into a few recent lectures. Sidebar's "New lecture" button
   routes here with `state: { openUpload: true }` so it opens the form
   immediately from anywhere in the workspace. */
export default function LectureListPage() {
  const location = useLocation();
  const { lectures, error: listError, refresh } = useLectures();
  const [showForm, setShowForm] = useState(Boolean(location.state?.openUpload));

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);

  useEffect(() => {
    if (location.state?.openUpload) setShowForm(true);
  }, [location.state]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!form.file) {
      setUploadError("Please choose an audio/video file.");
      return;
    }
    setUploading(true);
    setUploadError("");

    const fd = new FormData();
    fd.append("file", form.file);
    fd.append("title", form.title || form.file.name);
    if (form.course) fd.append("course", form.course);
    if (form.instructor) fd.append("instructor", form.instructor);
    if (form.semester) fd.append("semester", form.semester);
    if (form.lecture_date) fd.append("lecture_date", form.lecture_date);
    fd.append("output_language", form.output_language);
    if (form.language_code_hint) fd.append("language_code_hint", form.language_code_hint);

    try {
      await api.uploadLecture(fd);
      setForm(EMPTY_FORM);
      setShowForm(false);
      await refresh();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const recent = lectures ? lectures.slice(0, 6) : [];

  return (
    <motion.div
      className="workspace-page workspace-page-welcome"
      initial="hidden"
      animate="show"
      variants={fadeUp}
    >
      <div className="page-head">
        <div>
          <h1 className="page-title">Your lectures</h1>
          <p className="page-subtitle">
            Pick a lecture from the sidebar to chat, review notes, or take a quiz -- or upload a new one below.
          </p>
        </div>
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Upload lecture"}
        </button>
      </div>

      <AnimatePresence initial={false}>
        {showForm && (
          <motion.form
            className="card"
            onSubmit={handleUpload}
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: "hidden" }}
          >
          <ErrorBanner message={uploadError} />
          <div className="field">
            <label>Lecture file (audio or video)</label>
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.aac,.flac,.ogg,.opus,.wma,.mp4,.mov,.mkv,.webm"
              onChange={(e) => setForm({ ...form, file: e.target.files[0] })}
              required
            />
          </div>
          <div className="field">
            <label>Title</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. OOP Lecture 5 -- Inheritance"
            />
          </div>
          <div className="field-row">
            <div className="field">
              <label>Course</label>
              <input value={form.course} onChange={(e) => setForm({ ...form, course: e.target.value })} />
            </div>
            <div className="field">
              <label>Instructor</label>
              <input value={form.instructor} onChange={(e) => setForm({ ...form, instructor: e.target.value })} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label>Semester</label>
              <input value={form.semester} onChange={(e) => setForm({ ...form, semester: e.target.value })} />
            </div>
            <div className="field">
              <label>Lecture date</label>
              <input
                type="date"
                value={form.lecture_date}
                onChange={(e) => setForm({ ...form, lecture_date: e.target.value })}
              />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label>Output language</label>
              <select
                value={form.output_language}
                onChange={(e) => setForm({ ...form, output_language: e.target.value })}
              >
                {OUTPUT_LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>STT language hint (ISO 639-3, optional)</label>
              <input
                value={form.language_code_hint}
                onChange={(e) => setForm({ ...form, language_code_hint: e.target.value })}
                placeholder="e.g. urd, eng"
              />
            </div>
          </div>

          <p className="muted">
            This may take a while -- the request stays open until transcription, cleaning, and
            indexing finish. Don't close this tab.
          </p>

          <button className="btn" type="submit" disabled={uploading}>
            {uploading && <span className="spinner" />}
            {uploading ? "Processing lecture..." : "Upload & process"}
          </button>
          </motion.form>
        )}
      </AnimatePresence>

      <ErrorBanner message={listError} />

      {lectures === null && !listError && <p className="muted">Loading...</p>}

      {lectures && lectures.length === 0 && !showForm && (
        <div className="empty-state">No lectures yet -- upload your first one to get started.</div>
      )}

      {recent.length > 0 && (
        <div className="workspace-recent">
          <div className="section-eyebrow">Recent</div>
          <motion.div className="workspace-recent-grid" initial="hidden" animate="show" variants={staggerGrid}>
            {recent.map((l) => (
              <motion.div key={l.lecture_id} variants={fadeUp}>
                <Link to={`/app/lectures/${l.lecture_id}`} className="recent-card">
                  <div className="recent-card-head">
                    <span className="recent-card-title">{l.title}</span>
                    <StatusBadge status={l.status} />
                  </div>
                  <div className="muted">
                    {[l.course, l.instructor].filter(Boolean).join(" · ") || l.original_filename}
                  </div>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}