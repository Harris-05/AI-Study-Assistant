import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout.jsx";
import AppShell from "./components/layout/AppShell.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";
import LectureListPage from "./pages/LectureListPage.jsx";
import LectureLayout from "./pages/LectureLayout.jsx";
import TranscriptPage from "./pages/TranscriptPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import QuizPage from "./pages/QuizPage.jsx";
import NotesPage from "./pages/NotesPage.jsx";

export default function App() {
  return (
    <Routes>
      {/* Marketing/auth: floating nav + footer */}
      <Route element={<Layout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Route>

      {/* Workspace: sidebar shell, no footer -- one ProtectedRoute guards
          the whole /app subtree instead of every route repeating it. */}
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<LectureListPage />} />
        <Route path="lectures/:lectureId" element={<LectureLayout />}>
          <Route index element={<Navigate to="chat" replace />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="transcript" element={<TranscriptPage />} />
          <Route path="notes" element={<NotesPage />} />
          <Route path="quiz" element={<QuizPage />} />
        </Route>
      </Route>
    </Routes>
  );
}