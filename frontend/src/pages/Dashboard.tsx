import { StatCard } from "../components/dashboard/StatCard";
import { Link } from "react-router-dom";
import {
  AudioLines,
  CheckCheck,
  Clock3,
  FileText,
  Mic,
  CircleAlert,
  Languages,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useResource } from "../hooks/useResource";
import { State } from "../components/common/State";
import { duration, languageName } from "../utils/format";
import type { Page, Stats } from "../types";
export default function Dashboard() {
  const { name } = useAuth();
  const stats = useResource<Stats>("/dashboard/stats");
  const recent = useResource<Page>("/transcriptions?page_size=5");
  const cards = stats.data
    ? [
        {
          label: "Total transcriptions",
          value: stats.data.total,
          icon: FileText,
          color: "violet",
        },
        {
          label: "Completed",
          value: stats.data.completed,
          icon: CheckCheck,
          color: "green",
        },
        {
          label: "Recording time",
          value: duration(stats.data.duration),
          icon: Clock3,
          color: "blue",
        },
        {
          label: "Failed",
          value: stats.data.failed,
          icon: CircleAlert,
          color: "orange",
        },
      ]
    : [];
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">YOUR WORKSPACE, AT A GLANCE</p>
          <h1>
            Welcome back, {name} <span className="greeting">✦</span>
          </h1>
          <p>Good conversations deserve to be remembered.</p>
        </div>
        <Link className="button primary" to="/live">
          <Mic size={18} />
          New transcription
        </Link>
      </div>
      <section className="hero-card">
        <div>
          <span className="pill">LISTEN. CAPTURE. CREATE.</span>
          <h2>
            Let your voice
            <br />
            do the writing.
          </h2>
          <p>
            Ideas move fast. Capture them in real time,
            <br className="hidden md:block" /> in the language that feels
            natural.
          </p>
          <Link to="/live" className="button white">
            <Mic size={18} />
            Start recording
          </Link>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orb">
            <AudioLines size={64} strokeWidth={1.3} />
          </div>
          <span className="float-tag english">Hello, world</span>
          <span className="float-tag hindi">नमस्ते दुनिया</span>
          <div className="hero-wave">
            {Array.from({ length: 25 }, (_, i) => (
              <i
                key={i}
                style={{ height: `${12 + Math.abs(Math.sin(i * 1.2)) * 45}px` }}
              />
            ))}
          </div>
        </div>
      </section>
      {stats.loading || stats.error ? (
        <State loading={stats.loading} error={stats.error} />
      ) : (
        <div className="stats-grid">
          {cards.map((card) => (
            <StatCard key={card.label} {...card} />
          ))}
        </div>
      )}
      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Recent transcriptions</h2>
            <Link to="/history">View all</Link>
          </div>
          {recent.loading || recent.error || !recent.data?.items.length ? (
            <State
              loading={recent.loading}
              error={recent.error}
              empty="Your next idea starts here"
            />
          ) : (
            <div className="recent-list">
              {recent.data.items.map((item) => (
                <Link
                  to={`/history?record=${item.id}`}
                  key={item.id}
                  className="recent-row"
                >
                  <span className="file-icon">
                    <FileText size={21} />
                  </span>
                  <div>
                    <strong>{item.title}</strong>
                    <small>
                      {new Date(item.created_at).toLocaleDateString()} ·{" "}
                      {languageName(item.language)}
                    </small>
                  </div>
                  <span className={`badge ${item.status}`}>{item.status}</span>
                  <span className="muted">{duration(item.duration)}</span>
                </Link>
              ))}
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Languages</h2>
            <Languages size={20} className="muted" />
          </div>
          <div className="language-list">
            {stats.data?.languages.length ? (
              stats.data.languages.map((row) => (
                <div key={row.language}>
                  <div className="flex justify-between">
                    <strong>{languageName(row.language)}</strong>
                    <span>{row.count}</span>
                  </div>
                  <div className="progress">
                    <span
                      style={{
                        width: `${(100 * row.count) / stats.data!.total}%`,
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <State
                loading={stats.loading}
                error={stats.error}
                empty="Every language belongs"
              />
            )}
          </div>
          <p className="panel-foot">
            Language is detected automatically from your audio.
          </p>
        </section>
      </div>
    </>
  );
}
