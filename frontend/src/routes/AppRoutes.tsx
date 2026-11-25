import { Route, Routes } from "react-router-dom";
import { Layout } from "../components/layout/Layout";
import Dashboard from "../pages/Dashboard";
import LiveTranscription from "../pages/LiveTranscription";
import TranscriptionHistory from "../pages/TranscriptionHistory";
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="live" element={<LiveTranscription />} />
        <Route path="history" element={<TranscriptionHistory />} />
        <Route
          path="*"
          element={
            <div className="state">
              Page not found. Use the navigation to return to your workspace.
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
