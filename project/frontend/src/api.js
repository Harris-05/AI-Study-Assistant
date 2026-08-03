const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);

  let body = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!res.ok) {
    const err = body?.error;
    if (err?.code === "rate_limited") {
      throw new ApiError(
        `Too many requests -- please wait${err.retry_after_seconds ? ` ${Math.ceil(err.retry_after_seconds)}s` : ""} and try again.`,
        res.status,
        err.code
      );
    }
    throw new ApiError(err?.message || `Request failed (${res.status})`, res.status, err?.code);
  }

  return body;
}

export const api = {
  health: () => request("/api/health/"),

  listLectures: () => request("/api/lectures/"),

  getLecture: (lectureId) => request(`/api/lectures/${lectureId}/`),

  getTranscript: (lectureId) => request(`/api/lectures/${lectureId}/transcript/`),

  deleteLecture: (lectureId) =>
    request(`/api/lectures/${lectureId}/`, { method: "DELETE" }),

  uploadLecture: (formData) =>
    request("/api/lectures/", { method: "POST", body: formData }),

  getChatHistory: (lectureId) => request(`/api/lectures/${lectureId}/chat/`),

  askQuestion: (lectureId, question) =>
    request(`/api/lectures/${lectureId}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),

  listQuizzes: (lectureId) => request(`/api/lectures/${lectureId}/quiz/`),

  generateQuiz: (lectureId, params) =>
    request(`/api/lectures/${lectureId}/quiz/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }),

  quizExportUrl: (lectureId, quizId, format) =>
    `${API_BASE}/api/lectures/${lectureId}/quiz/${quizId}/export/?format=${format}`,
};

export { ApiError };
