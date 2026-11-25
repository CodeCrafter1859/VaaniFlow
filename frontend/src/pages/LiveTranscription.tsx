import { useRef, useState } from "react";
import {
  Mic,
  Pause,
  Play,
  Square,
  Upload,
  Languages,
  Save,
  Trash2,
  CheckCircle2,
} from "lucide-react";
import { useRecorder } from "../hooks/useRecorder";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { request } from "../services/api";
import { duration, languageName } from "../utils/format";
import { TranscriptActions } from "../components/common/TranscriptActions";
import { Waveform } from "../components/transcription/Waveform";
import type { Ticket, Transcript } from "../types";
export default function LiveTranscription() {
  const recorder = useRecorder();
  const { token } = useAuth();
  const toast = useToast();
  const [title, setTitle] = useState("Untitled recording");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const running = ["connecting", "recording", "paused", "stopping"].includes(
    recorder.status,
  );
  async function upload(file?: File) {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast("Choose a file smaller than 10 MB");
      return;
    }
    setBusy(true);
    try {
      const ticket = await request<Ticket>(
        "/auth/ticket?purpose=upload",
        token,
        { method: "POST" },
      );
      const body = new FormData();
      body.append("file", file);
      body.append("title", file.name.slice(0, 200));
      const record = await request<Transcript>(ticket.upload_url, "", {
        method: "POST",
        headers: { "X-Upload-Ticket": ticket.ticket },
        body,
      });
      recorder.acceptRecord(record);
      setTitle(record.title);
      toast("Audio transcribed and saved");
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }
  async function save() {
    setBusy(true);
    try {
      const record = await request<Transcript>("/transcriptions", token, {
        method: "POST",
        body: JSON.stringify({
          title: title.trim() || "Recovered recording",
          text: recorder.text,
          language: recorder.language,
          duration: recorder.seconds,
        }),
      });
      recorder.acceptRecord(record);
      toast("Transcript saved");
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">FROM SPOKEN TO WRITTEN</p>
          <h1>Live transcription</h1>
          <p>Speak naturally. We’ll take care of the words.</p>
        </div>
        <span
          className={`connection ${recorder.status === "recording" ? "connected" : ""}`}
        >
          <i />
          {running ? recorder.status : "Not connected"}
        </span>
      </div>
      <div className="live-grid">
        <div>
          <section className="panel recorder">
            <div className="panel-heading">
              <h2>
                <Mic size={18} />
                Recording studio
              </h2>
              <span className="pill">
                <Languages size={14} />
                Auto-detect language
              </span>
            </div>
            <label className="sr-only" htmlFor="title">
              Recording title
            </label>
            <input
              id="title"
              className="title-input"
              value={title}
              maxLength={200}
              disabled={running || busy}
              onChange={(e) => setTitle(e.target.value)}
            />
            <div
              className={`mic-orb ${recorder.status === "recording" ? "pulsing" : ""}`}
            >
              <Mic size={34} />
            </div>
            <div className="timer">{duration(recorder.seconds)}</div>
            <p className="text-center muted">
              {recorder.status === "recording"
                ? "Listening to your voice…"
                : recorder.status === "paused"
                  ? "Take your time. Recording is paused."
                  : recorder.status === "stopping"
                    ? "Finishing your transcript and saving…"
                    : "Ready when you are"}
            </p>
            <Waveform
              analyser={recorder.resources.current.analyser}
              recording={recorder.status === "recording"}
            />
            <div className="record-controls">
              {running ? (
                <>
                  <button
                    className="button secondary"
                    disabled={
                      !["recording", "paused"].includes(recorder.status)
                    }
                    onClick={recorder.pause}
                  >
                    {recorder.status === "paused" ? (
                      <Play size={17} />
                    ) : (
                      <Pause size={17} />
                    )}
                    {recorder.status === "paused" ? "Resume" : "Pause"}
                  </button>
                  <button
                    className="button stop"
                    onClick={recorder.stop}
                    disabled={
                      !["recording", "paused"].includes(recorder.status)
                    }
                  >
                    <Square size={16} />
                    Stop & save
                  </button>
                </>
              ) : (
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={() => recorder.start(title)}
                >
                  <Mic size={18} />
                  Start recording
                </button>
              )}
            </div>
            {recorder.error && (
              <p className="error text-center" role="alert">
                {recorder.error}
              </p>
            )}
            <p className="record-note">
              Microphone audio is sent only while recording. Up to 5 minutes per
              session.
            </p>
          </section>
          <section className="panel transcript">
            <div className="panel-heading">
              <h2>
                Transcript{" "}
                <span className="badge">{languageName(recorder.language)}</span>
              </h2>
              {recorder.record && (
                <span className="saved">
                  <CheckCircle2 size={15} />
                  Saved
                </span>
              )}
            </div>
            <div className="transcript-body" aria-live="polite">
              {recorder.text || (
                <div className="transcript-empty">
                  <span>“</span>
                  <h3>Your words will appear here</h3>
                  <p>Start recording or upload audio to begin.</p>
                </div>
              )}
            </div>
            <div className="transcript-toolbar">
              <span className="muted">
                {recorder.text.trim()
                  ? recorder.text.trim().split(/\s+/).length
                  : 0}{" "}
                words
              </span>
              <div className="flex gap-2 flex-wrap">
                <TranscriptActions text={recorder.text} title={title} />
                <button
                  className="button secondary"
                  disabled={
                    running || busy || !recorder.text || !!recorder.record
                  }
                  onClick={save}
                >
                  <Save size={16} />
                  Save
                </button>
                <button
                  className="icon-button"
                  aria-label="Clear transcript"
                  disabled={running || busy}
                  onClick={recorder.clear}
                >
                  <Trash2 size={17} />
                </button>
              </div>
            </div>
          </section>
        </div>
        <aside className="live-aside">
          <section className="panel upload-panel">
            <span className="stat-icon violet">
              <Upload size={24} />
            </span>
            <h2>Already have audio?</h2>
            <p>
              Turn a recording into a transcript. We’ll save it to your history.
            </p>
            <input
              ref={input}
              className="sr-only"
              type="file"
              accept="audio/*,.webm,.m4a,.flac"
              onChange={(e) => void upload(e.target.files?.[0])}
              aria-label="Upload audio file"
              disabled={running || busy}
            />
            <button
              className="button secondary"
              disabled={running || busy}
              onClick={() => input.current?.click()}
            >
              <Upload size={16} />
              {busy ? "Processing…" : "Choose audio file"}
            </button>
            <small>
              WAV, MP3, M4A, WebM, OGG, FLAC
              <br />
              Up to 10 MB · 5 minutes
            </small>
          </section>
          <section className="tips">
            <Languages size={24} />
            <h3>
              One conversation.
              <br />
              Multiple languages.
            </h3>
            <p>
              Speak in Hindi, English, or switch between them. Whisper detects
              language without requesting translation.
            </p>
            <hr />
            <strong>For the best results</strong>
            <p>
              Use a quiet space, keep your microphone close, and speak at a
              natural pace.
            </p>
            <small>
              Live text is provisional. Names and mixed-language phrases may
              need editing.
            </small>
          </section>
        </aside>
      </div>
    </>
  );
}
