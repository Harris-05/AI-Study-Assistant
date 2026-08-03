import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import StatusBadge from "../components/StatusBadge";
import ErrorBanner from "../components/ErrorBanner";

const OUTPUT_LANGUAGES = ["mixed", "urdu", "english", "arabic"];

export default function LectureListPage() {
  const [lectures, setLectures] = useState(null);
  const [listError, setListError] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [form, setForm] = useState({
    title: "",
    course: "",
    instructor: "",
    semester: "",
    lecture_date: "",
    output_language: "mixed",
    language_code_hint: "",
    file: null,
  });

  const loadLectures = async () => {
    try {
      setLectures(await api.listLectures());
      setListError("");
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load lectures.");
    }
  };

  useEffect(() => {
    loadLectures();
  }, []);

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
      setForm({
        title: "",
        course: "",
        instructor: "",
        semester: "",
        lecture_date: "",
        output_language: "mixed",
        language_code_hint: "",
        file: null,
      });
      setShowForm(false);
      await loadLectures();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="container app-page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Your lectures</h1>
          <p className="page-subtitle">Upload a recording, then chat with it or generate a quiz once it's processed.</p>
        </div>
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Upload lecture"}
        </button>
      </div>

      {showForm && (
        <form className="card" onSubmit={handleUpload}>
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
        </form>
      )}

      <ErrorBanner message={listError} />

      {lectures === null && !listError && <p className="muted">Loading...</p>}

      {lectures && lectures.length === 0 && (
        <div className="empty-state">No lectures yet -- upload your first one to get started.</div>
      )}

      {lectures &&
        lectures.map((l) => (
          <Link key={l.lecture_id} to={`/app/lectures/${l.lecture_id}`} className="lecture-list-item">
            <div>
              <div className="lecture-title">{l.title}</div>
              <div className="muted">
                {[l.course, l.instructor].filter(Boolean).join(" · ") || l.original_filename}
              </div>
            </div>
            <StatusBadge status={l.status} />
          </Link>
        ))}
    </div>
  );
}
