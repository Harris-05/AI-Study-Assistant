import { useEffect, useRef, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import ErrorBanner from "../components/ErrorBanner";

export default function ChatPage() {
  useOutletContext(); // lecture available if needed later
  const { lectureId } = useParams();
  const [messages, setMessages] = useState(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const logEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    setMessages(null);
    api
      .getChatHistory(lectureId)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [lectureId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, asking]);

  const handleAsk = async (e) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || asking) return;

    setAsking(true);
    setError("");
    setQuestion("");
    try {
      const msg = await api.askQuestion(lectureId, q);
      setMessages((prev) => [...(prev || []), msg]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not get an answer.");
      setQuestion(q); // give the question back so it isn't lost
    } finally {
      setAsking(false);
      textareaRef.current?.focus();
    }
  };

  return (
    <div className="chat-shell">
      <div className="chat-scroll">
        {messages === null && (
          <p className="muted">
            <span className="spinner" /> Loading conversation...
          </p>
        )}

        {messages?.length === 0 && (
          <div className="chat-empty">
            <ChatEmptyIcon />
            <p>Ask anything about this lecture.</p>
            <p className="muted" style={{ maxWidth: "40ch" }}>
              Answers are grounded strictly in what this lecture actually covers -- if it doesn't
              cover something, you'll be told that directly instead of getting a guess.
            </p>
          </div>
        )}

        {messages?.map((m) => <ChatExchange key={m.id} message={m} />)}

        {asking && (
          <div className="chat-row chat-row-assistant">
            <div className="chat-bubble chat-bubble-assistant chat-thinking">
              <span className="spinner" /> Thinking...
            </div>
          </div>
        )}

        <div ref={logEndRef} />
      </div>

      {error && (
        <div style={{ padding: "0 2px" }}>
          <ErrorBanner message={error} />
        </div>
      )}

      <form className="chat-composer" onSubmit={handleAsk}>
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about this lecture..."
          rows={1}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleAsk(e);
            }
          }}
        />
        <button className="chat-send-btn" type="submit" disabled={asking || !question.trim()} aria-label="Send">
          {asking ? <span className="spinner" /> : <SendIcon />}
        </button>
      </form>
    </div>
  );
}

function ChatExchange({ message }) {
  const [showSources, setShowSources] = useState(false);
  const hasSources = message.sources?.length > 0;

  return (
    <>
      <div className="chat-row chat-row-user">
        <div className="chat-bubble chat-bubble-user">{message.question}</div>
      </div>
      <div className="chat-row chat-row-assistant">
        <div className="chat-bubble chat-bubble-assistant">
          <div className="chat-answer-text">{message.answer}</div>

          {hasSources && (
            <>
              <button className="chat-sources-toggle" onClick={() => setShowSources((v) => !v)}>
                {showSources ? "Hide" : "Show"} {message.sources.length} source
                {message.sources.length === 1 ? "" : "s"}
                <ChevronIcon open={showSources} />
              </button>
              {showSources && (
                <div className="chat-sources">
                  {message.sources.map((s, i) => (
                    <div key={i} className="chat-source">
                      <div className="chat-source-meta">
                        chunk #{s.chunk_index} · confidence {(s.confidence * 100).toFixed(0)}%
                      </div>
                      <div className="chat-source-text">{s.text.slice(0, 220)}...</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

function SendIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
      <path d="M2.5 9l13-6-4.5 13-2.5-5.5L2.5 9z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}
    >
      <path d="M2.5 4.5L6 8l3.5-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChatEmptyIcon() {
  return (
    <svg width="36" height="36" viewBox="0 0 18 18" fill="none" style={{ marginBottom: 4 }}>
      <path
        d="M3 4.5h12a1 1 0 011 1V12a1 1 0 01-1 1H8l-3.5 3V13H3a1 1 0 01-1-1V5.5a1 1 0 011-1z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
    </svg>
  );
}
