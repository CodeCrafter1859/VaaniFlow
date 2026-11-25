import { useState } from "react";
import { AudioLines, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
export function Login() {
  const { login } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login">
      <div className="login-story">
        <span className="brand-mark">
          <AudioLines size={32} />
        </span>
        <p className="eyebrow">SPEECH TO TEXT</p>
        <h1>
          Every voice.
          <br />
          Every word.
          <br />
          <span>Captured.</span>
        </h1>
        <p>
          Turn conversations into clear, searchable text. In English, Hindi, and
          everything in between.
        </p>
        <div className="login-wave" aria-hidden="true">
          {Array.from({ length: 36 }, (_, i) => (
            <i
              key={i}
              style={{ height: `${20 + Math.abs(Math.sin(i * 0.7)) * 70}px` }}
            />
          ))}
        </div>
        <small>
          <ShieldCheck size={16} />
          Powered by self-hosted, open-source Whisper
        </small>
      </div>
      <form
        className="login-card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await login(value.trim());
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <span className="pill">YOUR PERSONAL WORKSPACE</span>
        <h2>Welcome back</h2>
        <p>
          Enter your access token to open your private transcription workspace.
        </p>
        <label htmlFor="token">Access token</label>
        <input
          id="token"
          type="password"
          autoComplete="off"
          required
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Paste your access token"
        />
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="button primary" disabled={busy}>
          {busy ? "Connecting…" : "Open workspace"}
        </button>
        <small>
          Ask your administrator for a token. It stays in memory and is cleared
          when this page closes.
        </small>
      </form>
    </div>
  );
}
