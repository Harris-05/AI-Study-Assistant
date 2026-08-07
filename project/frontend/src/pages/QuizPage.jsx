import { useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, ApiError } from "../api";
import ErrorBanner from "../components/ErrorBanner";

const staggerList = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } };
const fadeUp = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] } },
};

const SECTIONS = [
  { key: "mcqs", label: "Multiple Choice" },
  { key: "short_questions", label: "Short Answer" },
  { key: "long_questions", label: "Long Answer" },
];

export default function QuizPage() {
  useOutletContext();
  const { lectureId } = useParams();
  const [quizzes, setQuizzes] = useState(null);
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState("");
  const [counts, setCounts] = useState({ num_mcq: 10, num_short: 5, num_long: 3 });
  const [section, setSection] = useState("mcqs");

  useEffect(() => {
    setQuizzes(null);
    api
      .listQuizzes(lectureId)
      .then((list) => {
        setQuizzes(list);
        if (list.length > 0) {
          setActiveQuiz(list[0]);
          setShowSettings(false);
        } else {
          setShowSettings(true);
        }
      })
      .catch(() => {
        setQuizzes([]);
        setShowSettings(true);
      });
  }, [lectureId]);

  useEffect(() => {
    if (!activeQuiz) return;
    const firstNonEmpty = SECTIONS.find((s) => activeQuiz.data[s.key]?.length > 0);
    setSection(firstNonEmpty?.key || "mcqs");
  }, [activeQuiz]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      const quiz = await api.generateQuiz(lectureId, counts);
      setQuizzes((prev) => [quiz, ...(prev || [])]);
      setActiveQuiz(quiz);
      setShowSettings(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Quiz generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  if (quizzes === null) {
    return (
      <p className="muted">
        <span className="spinner" /> Loading quizzes...
      </p>
    );
  }

  return (
    <div>
      <div className="quiz-toolbar">
        <div className="quiz-toolbar-left">
          {quizzes.length > 0 && (
            <select
              className="quiz-select"
              value={activeQuiz?.id || ""}
              onChange={(e) => setActiveQuiz(quizzes.find((q) => q.id === Number(e.target.value)))}
            >
              {quizzes.map((q) => (
                <option key={q.id} value={q.id}>
                  {new Date(q.created_at).toLocaleString()} · {q.num_mcq} MCQ / {q.num_short} short / {q.num_long}{" "}
                  long
                </option>
              ))}
            </select>
          )}
        </div>
        <button className="btn btn-secondary btn-sm" onClick={() => setShowSettings((v) => !v)}>
          {showSettings ? "Cancel" : "Generate new quiz"}
        </button>
      </div>

      {showSettings && (
        <div className="card quiz-settings-card">
          <div className="quiz-controls">
            <div className="field">
              <label>MCQs</label>
              <input
                type="number"
                min="0"
                max="50"
                value={counts.num_mcq}
                onChange={(e) => setCounts({ ...counts, num_mcq: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label>Short</label>
              <input
                type="number"
                min="0"
                max="30"
                value={counts.num_short}
                onChange={(e) => setCounts({ ...counts, num_short: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label>Long</label>
              <input
                type="number"
                min="0"
                max="15"
                value={counts.num_long}
                onChange={(e) => setCounts({ ...counts, num_long: Number(e.target.value) })}
              />
            </div>
            <button className="btn" onClick={handleGenerate} disabled={generating}>
              {generating && <span className="spinner" />}
              {generating ? "Generating..." : "Generate"}
            </button>
          </div>
        </div>
      )}

      <ErrorBanner message={error} />

      {!activeQuiz && !showSettings && (
        <div className="empty-state">
          <p>No quiz generated yet for this lecture.</p>
        </div>
      )}

      {activeQuiz && (
        <>
          <div className="quiz-section-tabs">
            {SECTIONS.filter((s) => activeQuiz.data[s.key]?.length > 0).map((s) => (
              <button
                key={s.key}
                className={`quiz-section-tab ${section === s.key ? "active" : ""}`}
                onClick={() => setSection(s.key)}
              >
                {s.label}
                <span className="quiz-section-count">{activeQuiz.data[s.key].length}</span>
              </button>
            ))}
            <div className="export-row" style={{ marginLeft: "auto", marginBottom: 0 }}>
              <a className="btn-icon-text" href={api.quizExportUrl(lectureId, activeQuiz.id, "md")}>
                <DownloadIcon /> .md
              </a>
              <a className="btn-icon-text" href={api.quizExportUrl(lectureId, activeQuiz.id, "json")}>
                <DownloadIcon /> .json
              </a>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {section === "mcqs" && (
              <motion.div
                key="mcqs"
                className="quiz-questions"
                initial="hidden"
                animate="show"
                exit={{ opacity: 0 }}
                variants={staggerList}
              >
                {activeQuiz.data.mcqs.map((q, i) => (
                  <MCQCard key={i} index={i} question={q} />
                ))}
              </motion.div>
            )}

            {section === "short_questions" && (
              <motion.div
                key="short"
                className="quiz-questions"
                initial="hidden"
                animate="show"
                exit={{ opacity: 0 }}
                variants={staggerList}
              >
                {activeQuiz.data.short_questions.map((q, i) => (
                  <RevealCard key={i} index={i} question={q.question} answer={q.answer} answerLabel="Answer" />
                ))}
              </motion.div>
            )}

            {section === "long_questions" && (
              <motion.div
                key="long"
                className="quiz-questions"
                initial="hidden"
                animate="show"
                exit={{ opacity: 0 }}
                variants={staggerList}
              >
                {activeQuiz.data.long_questions.map((q, i) => (
                  <RevealCard
                    key={i}
                    index={i}
                    question={q.question}
                    answer={q.answer_guidance}
                    answerLabel="Answer guidance"
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}

function DifficultyBadge({ level }) {
  return <span className={`difficulty-badge difficulty-${level}`}>{level}</span>;
}

function MCQCard({ index, question }) {
  const [selected, setSelected] = useState(null);
  const answered = selected !== null;

  return (
    <motion.div className="card quiz-question-card" variants={fadeUp}>
      <div className="quiz-question-head">
        <span className="quiz-question-number">Q{index + 1}</span>
        <DifficultyBadge level={question.difficulty} />
      </div>
      <p className="quiz-question-text">{question.question}</p>

      <div className="mcq-options">
        {question.options.map((opt, j) => {
          const isCorrect = j === question.correct_index;
          const isSelected = j === selected;
          let cls = "mcq-choice";
          if (answered && isCorrect) cls += " correct";
          else if (answered && isSelected && !isCorrect) cls += " incorrect";

          return (
            <button
              key={j}
              className={cls}
              disabled={answered}
              onClick={() => setSelected(j)}
            >
              <span className="mcq-choice-marker">{String.fromCharCode(65 + j)}</span>
              {opt}
            </button>
          );
        })}
      </div>

      {answered && question.explanation && (
        <div className="quiz-explanation">
          <strong>Explanation:</strong> {question.explanation}
        </div>
      )}
    </motion.div>
  );
}

function RevealCard({ index, question, answer, answerLabel }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <motion.div className="card quiz-question-card" variants={fadeUp}>
      <div className="quiz-question-head">
        <span className="quiz-question-number">Q{index + 1}</span>
      </div>
      <p className="quiz-question-text">{question}</p>

      {revealed ? (
        <motion.div
          className="quiz-explanation"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
        >
          <strong>{answerLabel}:</strong> {answer}
        </motion.div>
      ) : (
        <button className="btn btn-secondary btn-sm" onClick={() => setRevealed(true)}>
          Reveal {answerLabel.toLowerCase()}
        </button>
      )}
    </motion.div>
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