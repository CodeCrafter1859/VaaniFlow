import { AlertCircle, FileAudio } from "lucide-react";
export function State({
  loading,
  error,
  empty,
}: {
  loading?: boolean;
  error?: string;
  empty?: string;
}) {
  if (loading)
    return (
      <div className="state" role="status">
        <span className="spinner" />
        Loading your workspace…
      </div>
    );
  if (error)
    return (
      <div className="state error" role="alert">
        <AlertCircle />
        {error}
      </div>
    );
  return (
    <div className="state">
      <FileAudio size={36} />
      <h3>{empty || "Nothing here yet"}</h3>
      <p>Your transcriptions will appear here.</p>
    </div>
  );
}
