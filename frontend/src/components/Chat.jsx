import { useCallback, useEffect, useRef, useState } from "react";
import Comic from "./Comic";
import Sources from "./Sources";
import Complaint from "./Complaint";
import { chat, analyzeImage, listAccountChats, getAccountChat, deleteAccountChat, clearAccountChats } from "../api";
import { useDictation, useSpeech, voiceInputSupported } from "../hooks";
import { applyUpdate, loadStore, saveStore, uid } from "../store";

export default function Chat({ lang, t, account }) {
  const [store, setStore] = useState(loadStore);
  const [showHist, setShowHist] = useState(false);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [openComplaint, setOpenComplaint] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const endRef = useRef(null);
  const activeRef = useRef(null);
  const accountRef = useRef(account);
  accountRef.current = account;
  const speech = useSpeech(lang);
  const dict = useDictation(lang, setText);

  const visibleChats = store.chats.filter((c) => !c.serverOwner || c.serverOwner === account?.email);
  const active = visibleChats.find((c) => c.id === store.activeId);
  const msgs = active?.msgs || [];
  activeRef.current = active?.id || null;
  useEffect(() => saveStore(store), [store]);
  useEffect(() => {
    const owner = account?.email;
    if (!owner) return undefined;
    let cancelled = false;
    setHistoryError("");
    listAccountChats()
      .then(({ chats = [] }) => {
        if (cancelled) return;
        setStore((s) => {
          const existing = new Set(s.chats.filter((c) => c.serverOwner === owner).map((c) => c.serverId));
          const imported = chats.filter((c) => !existing.has(String(c.id))).map((c) => ({
            id: uid(), serverId: String(c.id), serverOwner: owner, title: c.title, msgs: [], updated: Date.parse(c.updated) || Date.now(),
          }));
          return { ...s, chats: [...imported, ...s.chats].slice(0, 40) };
        });
      })
      .catch((error) => { if (!cancelled) setHistoryError(error.message || t.error); });
    return () => { cancelled = true; };
  }, [account?.email, t.error]);
  // ответ дописывается в тот чат, из которого задали вопрос, даже если пользователь успел переключиться
  const update = useCallback((id, upd) => setStore((s) => applyUpdate(s, id, upd)), []);

  const newChat = () => { speech.stop(); setStore((s) => ({ ...s, activeId: null })); setText(""); setOpenComplaint(null); setShowHist(false); };
  const openChat = async (entry) => {
    speech.stop(); setOpenComplaint(null); setShowHist(false);
    setStore((s) => ({ ...s, activeId: entry.id }));
    if ((entry.msgs || []).length || !entry.serverId || entry.serverOwner !== account?.email) return;
    setHistoryLoading(entry.id); setHistoryError("");
    try {
      const detail = await getAccountChat(entry.serverId);
      const msgs = (detail.messages || []).map((m) => m.role === "user"
        ? { role: "user", text: m.text }
        : m.data ? { role: "bot", data: m.data } : { role: "bot", error: m.text });
      setStore((s) => ({ ...s, chats: s.chats.map((c) => c.id === entry.id ? { ...c, title: detail.title, msgs, updated: Date.parse(detail.updated) || c.updated } : c) }));
    } catch (error) {
      setHistoryError(error.message || t.error);
    } finally {
      setHistoryLoading((current) => current === entry.id ? null : current);
    }
  };
  const removeChat = async (id) => {
    const entry = store.chats.find((c) => c.id === id);
    if (entry?.serverId && entry.serverOwner === account?.email) {
      try { await deleteAccountChat(entry.serverId); }
      catch (error) { setHistoryError(error.message || t.error); return; }
    }
    setStore((s) => ({ chats: s.chats.filter((c) => c.id !== id), activeId: s.activeId === id ? null : s.activeId }));
  };
  const clearAll = async () => {
    if (!window.confirm(t.clearConfirm)) return;
    try {
      if (account?.email) await clearAccountChats();
      setStore((s) => ({ chats: s.chats.filter((c) => c.serverOwner && c.serverOwner !== account?.email), activeId: null }));
      setHistoryError("");
    } catch (error) {
      setHistoryError(error.message || t.error);
    }
  };
  const fmt = (ts) => new Date(ts).toLocaleString(lang === "kk" ? "kk-KZ" : "ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, loading]);

  const send = useCallback(async (q) => {
    const message = (q ?? text).trim();
    if (!message || loading) return;
    const id = activeRef.current || uid();
    setText(""); setLoading(true); speech.stop();
    if (!activeRef.current) setStore((s) => ({ ...s, activeId: id }));
    update(id, (m) => [...m, { role: "user", text: message }]);
    const here = () => activeRef.current === id;
    // последние реплики пользователя в этом чате: бот поймёт «а если я его…» (до текущего сообщения)
    const history = (active?.msgs || []).filter((m) => m.role === "user").slice(-3).map((m) => m.text);
    try {
      const serverChatId = active?.serverId && active.serverOwner === account?.email ? active.serverId : null;
      const data = await chat(message, lang, history, serverChatId);
      if (data.chat_id && account?.email && accountRef.current?.email === account.email) {
        setStore((s) => ({
          ...s,
          chats: s.chats.map((c) => c.id === id ? { ...c, serverId: data.chat_id, serverOwner: account.email } : c),
        }));
      }
      update(id, (m) => [...m, { role: "bot", data }]);
      if (here()) {
        speech.speak(data.panels.map((p) => p.bubble).join(" "));
      }
    } catch (e) {
      update(id, (m) => [...m, { role: "bot", error: e.message || t.error }]);
    }
    setLoading(false);
  }, [text, loading, lang, speech, t.error, update, active, account?.email]);

  const onPhoto = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const id = activeRef.current || uid();
    if (!activeRef.current) setStore((s) => ({ ...s, activeId: id }));
    setLoading(true);
    try { const doc = await analyzeImage(f, lang); update(id, (m) => [...m, { role: "bot", doc }]); }
    catch (err) { update(id, (m) => [...m, { role: "bot", error: err.message }]); }
    setLoading(false);
  };

  return (
    <div className="chat-layout">
      <section className="thread">
        <div className="thread-head">
          <button className="ghost small" onClick={newChat}>{t.newChat}</button>
          <button className="ghost small" aria-expanded={showHist} onClick={() => setShowHist(!showHist)}>{t.history} ({visibleChats.length})</button>
        </div>
        {showHist && (
          <section className="history" aria-label={t.history}>
            {visibleChats.length === 0 ? <p className="hint">{t.noHistory}</p> : (
              <ul>
                {visibleChats.map((c) => (
                  <li key={c.id} className={c.id === store.activeId ? "on" : ""}>
                    <button className="open" onClick={() => openChat(c)}><span className="ttl">{c.title || t.untitled}</span><small>{fmt(c.updated)}</small></button>
                    <button className="del" aria-label={t.deleteChat} title={t.deleteChat} onClick={() => removeChat(c.id)}>×</button>
                  </li>
                ))}
              </ul>
            )}
            <small className="hint">{t.localOnly}</small>
            {visibleChats.length > 0 && <button className="ghost small" onClick={clearAll}>{t.clearAll}</button>}
          </section>
        )}
        {historyError && <p className="error history-error" role="alert">{historyError}</p>}
        {historyLoading === active?.id && <p className="status history-status" aria-live="polite">{t.loadingHistory}</p>}
        {msgs.length === 0 && historyLoading !== active?.id && (
          <div className="empty">
            <p className="lead">{t.tagline}</p>
            <div className="chips">{t.examples.map((ex) => <button key={ex} onClick={() => send(ex)}>{ex}</button>)}</div>
          </div>
        )}

        {msgs.map((m, i) => m.role === "user" ? (
          <div key={i} className="user-msg">{m.text}</div>
        ) : (
          <div key={i} className="bot-msg">
            {m.error && <p className="error">{m.error}</p>}
            {m.doc && (
              <div className="docinfo">
                <h4>{t.docType}: {m.doc.doc_type}</h4>
                <p><b>{t.docFound}:</b> {m.doc.found.join("; ")}</p>
                <p><b>{t.docMissing}:</b> {m.doc.missing.join("; ")}</p>
                <p>{m.doc.advice}</p>
                <small>{m.doc.disclaimer}</small>
              </div>
            )}
            {m.data && (
              <>
                {m.data.safety && <p className="safety" role="alert">{m.data.safety}</p>}
                {m.data.refused && <span className="badge none">{t.noBase}</span>}
                <Comic panels={m.data.panels} refused={m.data.refused} />
                {!m.data.refused && (
                  <details>
                    <summary>{t.details}</summary>
                    <div className="details-text">{m.data.details}</div>
                    <Sources sources={m.data.sources} t={t} />
                  </details>
                )}
                <small className="disclaimer">{m.data.disclaimer}</small>
                {!m.data.refused && (
                  <div>
                    <button className="ghost" onClick={() => setOpenComplaint(openComplaint === i ? null : i)}>{t.complaint}</button>
                    {openComplaint === i && <Complaint situation={msgs[i - 1]?.text || ""} lang={lang} t={t} />}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
        {loading && <div className="bot-msg typing"><span /><span /><span /></div>}
        <div ref={endRef} />

        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <textarea value={text} rows={2} maxLength={2000} placeholder={t.placeholder}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
          <div className="tools">
            {voiceInputSupported && (
              <button type="button" className="ghost" onClick={dict.listening ? dict.stop : dict.start}>{dict.listening ? t.micStop : t.mic}</button>
            )}
            <label className="ghost file">{t.photo}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={onPhoto} hidden /></label>
            <button type="button" className="ghost" aria-pressed={speech.enabled} onClick={() => { speech.stop(); speech.setEnabled(!speech.enabled); }}>
              {speech.enabled ? t.voiceOn : t.voiceOff}
            </button>
            <button className="primary" disabled={loading || !text.trim()}>{t.send}</button>
          </div>
        </form>
      </section>
    </div>
  );
}
