import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import StatusBadge from "../components/StatusBadge";
import ErrorBanner from "../components/ErrorBanner";

export default function LectureLayout() {
  const { lectureId } = useParams();
  const navigate = useNavigate();
  const [lecture, setLecture] = useState(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setLecture(null);
    setError("");
    api
      .getLecture(lectureId)
      .then(setLecture)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load lecture."));
  }, [lectureId]);

  const handleDelete = async () => {
    if (!window.confirm("Delete this lecture and all its data? This can't be undone.")) return;
    setDeleting(true);
    try {
      await api.deleteLecture(lectureId);
      navigate("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
      setDeleting(false);
    }
  };

  if (error) {
    return (
      <div className="container app-page">
        <ErrorBanner message={error} />
      </div>
    );
  }

  if (!lecture) {
    return (
      <div className="container app-page">
        <p className="muted">
          <span className="spinner" /> Loading lecture...
        </p>
      </div>
    );
  }

  const ready = lecture.status === "completed";

  return (
    <div className="container app-page">
      <div className="lecture-header">
        <div className="lecture-header-main">
          <div className="page-head" style={{ marginBottom: 6 }}>
            <h1 className="page-title">{lecture.title}</h1>
            <StatusBadge status={lecture.status} />
          </div>
          <p className="page-subtitle">
            {[lecture.course, lecture.instructor, lecture.semester].filter(Boolean).join(" · ") ||
              "No course details added"}
          </p>
          {ready && (
            <div className="lecture-meta-row">
              {lecture.duration_seconds != null && <span>{Math.round(lecture.duration_seconds / 60)} min</span>}
              {lecture.num_chunks != null && <span>{lecture.num_chunks} chunks indexed</span>}
              <span>output: {lecture.output_language}</span>
            </div>
          )}
        </div>
        <button className="btn-ghost-danger" onClick={handleDelete} disabled={deleting}>
          {deleting ? "Deleting..." : "Delete lecture"}
        </button>
      </div>

      {lecture.status === "failed" && <ErrorBanner message={lecture.error_message || "Processing failed."} />}
      {lecture.status === "processing" && (
        <div className="card">
          <span className="spinner" /> Still processing -- this page will update once it's ready. Refresh to check.
        </div>
      )}
      {lecture.status === "pending" && (
        <div className="card">
          <span className="spinner" /> Queued for processing...
        </div>
      )}

      {ready && (
        <>
          <nav className="lecture-subnav">
            <NavLink
              to={`/app/lectures/${lectureId}/transcript`}
              className={({ isActive }) => `subnav-link ${isActive ? "active" : ""}`}
            >
              <TranscriptIcon /> Transcript
            </NavLink>
            <NavLink
              to={`/app/lectures/${lectureId}/chat`}
              className={({ isActive }) => `subnav-link ${isActive ? "active" : ""}`}
            >
              <ChatIcon /> Chat
            </NavLink>
            <NavLink
              to={`/app/lectures/${lectureId}/quiz`}
              className={({ isActive }) => `subnav-link ${isActive ? "active" : ""}`}
            >
              <QuizIcon /> Quiz
            </NavLink>
          </nav>

          <Outlet context={{ lecture }} />
        </>
      )}
    </div>
  );
}

function TranscriptIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
      <path
        d="M4 2.5h7l3 3v10a.5.5 0 01-.5.5h-9.5a.5.5 0 01-.5-.5v-12a.5.5 0 01.5-.5z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M6.5 8h5M6.5 10.5h5M6.5 13h3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
      <path
        d="M3 4.5h12a1 1 0 011 1V12a1 1 0 01-1 1H8l-3.5 3V13H3a1 1 0 01-1-1V5.5a1 1 0 011-1z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function QuizIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="6.5" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M7 7.2c0-1.1.9-1.9 2-1.9s2 .7 2 1.7c0 1.6-2 1.3-2 2.9"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <circle cx="9" cy="12.2" r="0.15" fill="currentColor" stroke="currentColor" strokeWidth="1.1" />
    </svg>
  );
}
