import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import LectureListPage from "./pages/LectureListPage.jsx";
import LectureLayout from "./pages/LectureLayout.jsx";
import TranscriptPage from "./pages/TranscriptPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import QuizPage from "./pages/QuizPage.jsx";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<LectureListPage />} />
        <Route path="/app/lectures/:lectureId" element={<LectureLayout />}>
          <Route index element={<Navigate to="transcript" replace />} />
          <Route path="transcript" element={<TranscriptPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="quiz" element={<QuizPage />} />
        </Route>
      </Routes>
    </Layout>
  );
}
