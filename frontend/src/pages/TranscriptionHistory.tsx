import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Search,
  Mic,
  FileText,
  Trash2,
  Pencil,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useResource } from "../hooks/useResource";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { request } from "../services/api";
import { duration, languageName } from "../utils/format";
import { State } from "../components/common/State";
import { Dialog } from "../components/common/Dialog";
import { TranscriptActions } from "../components/common/TranscriptActions";
import type { Page, Transcript } from "../types";
export default function TranscriptionHistory() {
  const { token } = useAuth();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [language, setLanguage] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("created_at:desc");
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<Transcript | null>(null);
  const [deleting, setDeleting] = useState<Transcript | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(search);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);
  useEffect(() => {
    const id = params.get("record");
    if (id)
      request<Transcript>(`/transcriptions/${id}`, token)
        .then(setSelected)
        .catch((e: Error) => toast(e.message));
  }, [params, token, toast]);
  const query = new URLSearchParams({
    search: debounced,
    sort: sort.split(":")[0],
    order: sort.split(":")[1],
    page: String(page),
    page_size: "10",
    ...(language ? { language } : {}),
    ...(status ? { status } : {}),
  });
  const result = useResource<Page>(`/transcriptions?${query}`, revision);
  function close() {
    if (!busy) {
      setSelected(null);
      setParams({});
    }
  }
  async function save() {
    if (!selected) return;
    setBusy(true);
    try {
      await request(`/transcriptions/${selected.id}`, token, {
        method: "PATCH",
        body: JSON.stringify({ title: selected.title, text: selected.text }),
      });
      setSelected(null);
      setParams({});
      setRevision((x) => x + 1);
      toast("Changes saved");
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    if (!deleting) return;
    setBusy(true);
    try {
      await request(`/transcriptions/${deleting.id}`, token, {
        method: "DELETE",
      });
      setDeleting(null);
      setPage(1);
      setRevision((x) => x + 1);
      toast("Transcription deleted");
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
          <p className="eyebrow">YOUR WORDS, ALL IN ONE PLACE</p>
          <h1>Transcription history</h1>
          <p>Revisit, refine, and share your conversations.</p>
        </div>
        <Link className="button primary" to="/live">
          <Mic size={18} />
          New transcription
        </Link>
      </div>
      <section className="panel history-panel">
        <div className="filters">
          <div className="search-field">
            <Search size={18} />
            <input
              aria-label="Search transcriptions"
              placeholder="Search your transcriptions…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            aria-label="Filter language"
            value={language}
            onChange={(e) => {
              setLanguage(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All languages</option>
            <option value="hi">Hindi</option>
            <option value="en">English</option>
            <option value="hi-en">Hindi + English</option>
            <option value="auto">Undetected</option>
          </select>
          <select
            aria-label="Filter status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <select
            aria-label="Sort transcriptions"
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
          >
            <option value="created_at:desc">Newest first</option>
            <option value="created_at:asc">Oldest first</option>
            <option value="title:asc">Title A–Z</option>
            <option value="duration:desc">Longest first</option>
          </select>
        </div>
        {result.loading || result.error || !result.data?.items.length ? (
          <State
            loading={result.loading}
            error={result.error}
            empty={
              search || language || status
                ? "No matching transcriptions"
                : "A fresh page for your ideas"
            }
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Transcription</th>
                  <th>Language</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.data.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <button
                        className="record-title"
                        onClick={() => setSelected(item)}
                      >
                        <span className="file-icon">
                          <FileText size={19} />
                        </span>
                        <span>
                          <strong>{item.title}</strong>
                          <small>
                            {item.text.slice(0, 70) || "No speech detected"}
                          </small>
                        </span>
                      </button>
                    </td>
                    <td>{languageName(item.language)}</td>
                    <td>{duration(item.duration)}</td>
                    <td>
                      <span className={`badge ${item.status}`}>
                        {item.status}
                      </span>
                    </td>
                    <td>{new Date(item.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="flex gap-1">
                        <button
                          className="icon-button"
                          aria-label={`Edit ${item.title}`}
                          onClick={() => setSelected(item)}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="icon-button danger"
                          aria-label={`Delete ${item.title}`}
                          onClick={() => setDeleting(item)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="pagination">
          <span>{result.data?.total ?? 0} transcriptions</span>
          <div className="flex items-center gap-3">
            <button
              className="icon-button"
              aria-label="Previous page"
              disabled={page === 1 || result.loading}
              onClick={() => setPage((x) => x - 1)}
            >
              <ChevronLeft size={18} />
            </button>
            <span>
              Page {page} of{" "}
              {Math.max(1, Math.ceil((result.data?.total ?? 0) / 10))}
            </span>
            <button
              className="icon-button"
              aria-label="Next page"
              disabled={
                !result.data || page * 10 >= result.data.total || result.loading
              }
              onClick={() => setPage((x) => x + 1)}
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </section>
      {selected && (
        <Dialog title="Your transcription" close={close}>
          <form
            className="dialog-content"
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <label htmlFor="edit-title">Title</label>
            <input
              id="edit-title"
              required
              maxLength={200}
              value={selected.title}
              onChange={(e) =>
                setSelected({ ...selected, title: e.target.value })
              }
            />
            <label htmlFor="edit-text">Transcript</label>
            <textarea
              id="edit-text"
              rows={10}
              maxLength={100000}
              value={selected.text}
              onChange={(e) =>
                setSelected({ ...selected, text: e.target.value })
              }
            />
            <div className="dialog-actions">
              <button type="submit" className="button primary" disabled={busy}>
                {busy ? "Saving…" : "Save changes"}
              </button>
            </div>
          </form>
          <div className="dialog-export">
            <TranscriptActions text={selected.text} title={selected.title} />
          </div>
        </Dialog>
      )}
      {deleting && (
        <Dialog
          title="Delete transcription?"
          close={() => {
            if (!busy) setDeleting(null);
          }}
        >
          <div className="dialog-content">
            <p>
              “{deleting.title}” will be permanently deleted. This cannot be
              undone.
            </p>
            <div className="dialog-actions">
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => setDeleting(null)}
              >
                Cancel
              </button>
              <button className="button stop" disabled={busy} onClick={remove}>
                {busy ? "Deleting…" : "Delete transcription"}
              </button>
            </div>
          </div>
        </Dialog>
      )}
    </>
  );
}
