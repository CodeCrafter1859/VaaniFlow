import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  AudioLines,
  LayoutDashboard,
  Mic,
  History,
  Moon,
  Sun,
  LogOut,
  Menu,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { config } from "../../config/env";
const links = [
  { path: "/", label: "Overview", icon: LayoutDashboard },
  { path: "/live", label: "Live transcription", icon: Mic },
  { path: "/history", label: "Transcription history", icon: History },
];
export function Layout() {
  const { name, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains("dark"),
  );
  const location = useLocation();
  function theme() {
    document.documentElement.classList.toggle("dark", !dark);
    localStorage.setItem("stt-theme", dark ? "light" : "dark");
    setDark(!dark);
  }
  return (
    <div className="app-shell">
      {open && (
        <button
          className="scrim"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside className={open ? "sidebar open" : "sidebar"}>
        <NavLink to="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">
            <AudioLines />
          </span>
          <span>
            {config.name}
            <small>YOUR VOICE, IN WORDS</small>
          </span>
        </NavLink>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {links.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} end onClick={() => setOpen(false)}>
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={22} />
          <strong>Private by design</strong>
          <p>
            Open-source Whisper. Your audio is processed on your own worker.
          </p>
        </div>
        <div className="profile">
          <span className="avatar">{name.slice(0, 1).toUpperCase()}</span>
          <div>
            <strong>{name}</strong>
            <small>Personal workspace</small>
          </div>
          <button aria-label="Sign out" onClick={logout}>
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="flex items-center gap-3">
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <Menu />
            </button>
            <span>
              Workspace <span className="muted mx-2">/</span>{" "}
              <strong>
                {location.pathname === "/live"
                  ? "Live transcription"
                  : location.pathname === "/history"
                    ? "History"
                    : "Overview"}
              </strong>
            </span>
          </div>
          <button
            className="icon-button"
            onClick={theme}
            aria-label={dark ? "Use light mode" : "Use dark mode"}
          >
            {dark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </header>
        <main>
          <Outlet />
        </main>
        <footer>
          Built for every voice. <span>English · हिन्दी · Multilingual</span>
        </footer>
      </div>
    </div>
  );
}
