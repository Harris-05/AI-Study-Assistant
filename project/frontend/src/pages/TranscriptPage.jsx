import { useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import ErrorBanner from "../components/ErrorBanner";

export default function TranscriptPage() {
  const { lecture } = useOutletContext();
  const { lectureId } = useParams();
  const [text, setText] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setText(null);
    setError("");
    api
      .getTranscript(lectureId)
      .then((res) => setText(res.text))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load transcript."));
  }, [lectureId]);

  const handleCopy = async () => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const handleDownload = () => {
    if (!text) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${lecture.title.replace(/[^\w\-]+/g, "_") || lectureId}-transcript.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) return <ErrorBanner message={error} />;

  if (!text) {
    return (
      <p className="muted">
        <span className="spinner" /> Loading transcript...
      </p>
    );
  }

  const paragraphs = text.split(/\n{2,}/).filter((p) => p.trim());

  return (
    <div>
      <div className="transcript-toolbar">
        <span className="muted">{paragraphs.length} paragraph{paragraphs.length === 1 ? "" : "s"}</span>
        <div className="transcript-toolbar-actions">
          <button className="btn btn-secondary btn-sm" onClick={handleCopy}>
            {copied ? "Copied!" : "Copy text"}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handleDownload}>
            Download .txt
          </button>
        </div>
      </div>

      <div className="transcript-content card">
        {paragraphs.map((p, i) => (
          <p key={i} dir="auto" className="transcript-paragraph">
            {p.trim()}
          </p>
        ))}
      </div>
    </div>
  );
}
