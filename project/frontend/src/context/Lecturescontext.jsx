import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError } from "../api";

const LecturesContext = createContext(null);

/* One fetch of the lecture list, shared by the sidebar (which renders it
   as a nav) and the workspace pages (which need to trigger a refresh
   after an upload or a delete). Without this each consumer fetched its
   own copy and had no way to tell the others "the list just changed." */
export function LecturesProvider({ children }) {
  const [lectures, setLectures] = useState(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const list = await api.listLectures();
      setLectures(list);
      setError("");
      return list;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load lectures.");
      throw err;
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  return (
    <LecturesContext.Provider value={{ lectures, error, refresh }}>{children}</LecturesContext.Provider>
  );
}

export function useLectures() {
  const ctx = useContext(LecturesContext);
  if (!ctx) throw new Error("useLectures must be used within a LecturesProvider");
  return ctx;
}