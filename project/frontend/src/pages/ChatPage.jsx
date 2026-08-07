import { useEffect, useRef, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { api, ApiError } from "../api";
import { useAuth } from "../context/AuthContext.jsx";
import ErrorBanner from "../components/ErrorBanner";
import Markdown from "../components/Markdown.jsx";

export default function ChatPage() {
  useOutletContext(); // lecture available if needed later
  const { lectureId } = useParams();
  const { user } = useAuth();
  const [messages, setMessages] = useState(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  // Id of the message currently doing its word-reveal animation -- only
  // set right after a fresh answer comes back, never for history loaded
  // from the API, so re-opening a chat doesn't replay every answer.
  const [streamingId, setStreamingId] = useState(null);
  const logEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    setMessages(null);
    setStreamingId(null);
    api
      .getChatHistory(lectureId)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [lectureId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, asking]);

  // Auto-grow the composer with content instead of a fixed-height box.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [question]);

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
      setStreamingId(msg.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not get an answer.");
      setQuestion(q); // give the question back so it isn't lost
    } finally {
      setAsking(false);
      textareaRef.current?.focus();
    }
  };

  const userInitial = (user?.email || "?")[0].toUpperCase();

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
            <span className="chat-empty-mark">اع</span>
            <p className="chat-empty-title">Ask anything about this lecture.</p>
            <p className="muted" style={{ maxWidth: "40ch" }}>
              Answers are grounded strictly in what this lecture actually covers -- if it doesn't
              cover something, you'll be told that directly instead of getting a guess.
            </p>
          </div>
        )}

        {messages?.map((m) => (
          <ChatExchange
            key={m.id}
            message={m}
            userInitial={userInitial}
            streaming={m.id === streamingId}
            onStreamDone={() => setStreamingId(null)}
          />
        ))}

        {asking && (
          <div className="gpt-row gpt-row-assistant">
            <span className="gpt-avatar gpt-avatar-assistant">اع</span>
            <div className="gpt-content chat-thinking">
              Thinking
              <span className="loading-dots">
                <span />
                <span />
                <span />
              </span>
            </div>
          </div>
        )}

        <div ref={logEndRef} />
      </div>

      {error && (
        <div style={{ maxWidth: 780, width: "100%", margin: "0 auto", padding: "0 24px" }}>
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

function ChatExchange({ message, userInitial, streaming, onStreamDone }) {
  const [showSources, setShowSources] = useState(false);
  const [revealCount, setRevealCount] = useState(streaming ? 0 : null);
  const hasSources = message.sources?.length > 0;

  // Word-by-word reveal to simulate streaming, since the API returns the
  // full answer in one response rather than tokens over time.
  const tokens = message.answer.split(/(\s+)/);
  useEffect(() => {
    if (!streaming) return;
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setRevealCount(i);
      if (i >= tokens.length) {
        clearInterval(id);
        onStreamDone?.();
      }
    }, 16);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [streaming, message.id]);

  const displayedAnswer = streaming && revealCount !== null ? tokens.slice(0, revealCount).join("") : message.answer;
  const stillRevealing = streaming && revealCount !== null && revealCount < tokens.length;

  return (
    <>
      <motion.div
        className="gpt-row gpt-row-user"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <span className="gpt-avatar gpt-avatar-user">{userInitial}</span>
        <div className="gpt-content">{message.question}</div>
      </motion.div>
      <motion.div
        className="gpt-row gpt-row-assistant"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.05 }}
      >
        <span className="gpt-avatar gpt-avatar-assistant">اع</span>
        <div className="gpt-content">
          <div className="chat-answer-text">
            <Markdown text={displayedAnswer} />
            {stillRevealing && <span className="typing-caret" />}
          </div>

          {hasSources && !stillRevealing && (
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
      </motion.div>
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