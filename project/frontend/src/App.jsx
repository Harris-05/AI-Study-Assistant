import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout.jsx";
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
    <Layout>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <LectureListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/app/lectures/:lectureId"
          element={
            <ProtectedRoute>
              <LectureLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="transcript" replace />} />
          <Route path="transcript" element={<TranscriptPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="quiz" element={<QuizPage />} />
          <Route path="notes" element={<NotesPage />} />
        </Route>
      </Routes>
    </Layout>
  );
}
