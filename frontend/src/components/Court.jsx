import { useCallback, useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import Mascot from "./Mascot";
import Sources from "./Sources";
import Complaint from "./Complaint";
import { createRoom, courtSocket } from "../api";
import { useDictation, useSpeech, voiceInputSupported } from "../hooks";

const ROLES = ["plaintiff", "respondent", "witness"];

export default function Court({ lang, t, initialCode }) {
  const [session, setSession] = useState(null);
  if (!session) return <Entry lang={lang} t={t} initialCode={initialCode} onEnter={setSession} />;
  return <Room key={session.code} session={session} lang={lang} t={t} onExit={() => setSession(null)} />;
}

function Entry({ lang, t, initialCode, onEnter }) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("plaintiff");
  const [code, setCode] = useState(initialCode || "");
  const [err, setErr] = useState("");
  const create = async (solo) => {
    try { onEnter({ code: (await createRoom(lang)).code, name, role, solo }); } catch (e) { setErr(e.message); }
  };
  return (
    <div className="court-entry">
      <div className="stage"><Mascot mood="stern" /></div>
      <div className="entry-form">
        <h2>{t.courtTitle}</h2>
        <p className="lead">{t.courtLead}</p>
        <label>{t.yourName}<input value={name} maxLength={24} onChange={(e) => setName(e.target.value)} /></label>
        <fieldset>
          <legend>{t.role}</legend>
          {ROLES.map((r) => (
            <label key={r} className={`radio ${role === r ? "on" : ""}`}>
              <input type="radio" name="role" checked={role === r} onChange={() => setRole(r)} />{t[r]}
            </label>
          ))}
        </fieldset>
        <div className="row">
          <button className="primary" onClick={() => create(true)}>{t.solo}</button>
          <button className="ghost" onClick={() => create(false)}>{t.create}</button>
        </div>
        <div className="row join">
          <input placeholder={t.code} value={code} maxLength={8} onChange={(e) => setCode(e.target.value.toUpperCase())} />
          <button className="ghost" disabled={code.length < 4} onClick={() => onEnter({ code, name, role })}>{t.enter}</button>
        </div>
        {err && <p className="error">{err}</p>}
      </div>
    </div>
  );
}

function Room({ session, lang, t, onExit }) {
  const { code, name, role } = session;
  const [room, setRoom] = useState(null);
  const [me, setMe] = useState(null);
  const [err, setErr] = useState("");
  const [gavel, setGavel] = useState(0);
  const [stmt, setStmt] = useState("");
  const [answers, setAnswers] = useState({});
  const [caseText, setCaseText] = useState("");
  const ws = useRef(null);
  const lastPhase = useRef("lobby");
  const speech = useSpeech(room?.lang || lang);
  const dict = useDictation(lang, setStmt);
  const send = useCallback((m) => ws.current?.readyState === 1 && ws.current.send(JSON.stringify(m)), []);

  useEffect(() => {
    const sock = courtSocket(code);
    ws.current = sock;
    sock.onopen = () => send({ type: "join", name: name || "Игрок", role, token: sessionStorage.getItem(`court:${code}`) });
    sock.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.type === "joined") { setMe(m.you); sessionStorage.setItem(`court:${code}`, m.you); }
      if (m.type === "state") setRoom(m.room);
      if (m.type === "error") setErr(m.text);
    };
    sock.onclose = (e) => {
      if (e.code === 4404) { setErr(t.badRoom); setTimeout(onExit, 1500); }
      else setErr((prev) => prev || t.noConn); // сервер недоступен / соединение оборвалось
    };
    return () => { sock.onclose = null; sock.close(); };
  }, [code]); // eslint-disable-line

  useEffect(() => {
    if (!room) return;
    if (room.phase !== lastPhase.current && ["statements", "verdict"].includes(room.phase)) setGavel((g) => g + 1);
    lastPhase.current = room.phase;
  }, [room?.phase]); // eslint-disable-line

  useEffect(() => { if (room?.judge?.text) speech.speak(room.judge.text); }, [room?.judge?.text]); // eslint-disable-line

  if (!room) return (
    <div className="status">
      <p>{err || t.thinking}</p>
      {err && <button className="ghost" onClick={onExit}>{t.newCourt}</button>}
    </div>
  );
  const isHost = room.host === me;
  const mine = room.players.find((p) => p.id === me);
  const mood = room.busy ? "thinking" : room.judge.mood === "listening" ? "listening" : speech.speaking ? "speaking" : room.judge.mood || "idle";
  const joinUrl = `${location.origin}/?code=${code}`;
  const nameOf = (id) => room.players.find((p) => p.id === id)?.name || "";

  return (
    <div className="court-layout">
      <aside className="stage bench">
        <Mascot mood={mood} speaking={speech.speaking} gavelKey={gavel} />
        {room.judge.text && <div className="panel judge-say"><p>{room.judge.text}</p></div>}
        <button className="ghost small" aria-pressed={speech.enabled} onClick={() => { speech.stop(); speech.setEnabled(!speech.enabled); }}>
          {speech.enabled ? t.voiceOn : t.voiceOff}
        </button>
      </aside>

      <section className="proceedings">
        <header className="room-head">
          <h2>{t.courtTitle} <span className="code">{code}</span></h2>
          <ul className="players" aria-label={t.players}>
            {room.players.map((p) => (
              <li key={p.id} className={`${p.online ? "" : "off"} ${p.submitted ? "done" : ""}`}>
                {p.name} <small>{t[p.role]}{p.online ? "" : ` · ${t.offline}`}</small>
              </li>
            ))}
          </ul>
        </header>
        {err && <p className="error" role="alert">{err}</p>}

        {room.phase === "lobby" && (
          <div className="lobby">
            {!session.solo && <div className="qr">
              <QRCodeSVG value={joinUrl} size={150} bgColor="#FFFFFF" fgColor="#1C2530" level="M" marginSize={2} />
              <small>{t.scan}</small>
              <small className="url">{joinUrl}</small>
            </div>}
            {isHost ? (
              <div className="case-form">
                <label>{t.caseLabel}
                  <textarea rows={4} maxLength={600} value={caseText} onChange={(e) => { setCaseText(e.target.value); send({ type: "set_case", text: e.target.value }); }} />
                </label>
                <div className="chips"><span>{t.presets}:</span>{t.cases.map((c) => (
                  <button key={c} onClick={() => { setCaseText(c); send({ type: "set_case", text: c }); }}>{c.slice(0, 48)}…</button>))}</div>
                <button className="primary" onClick={() => send({ type: "start" })}>{t.start}</button>
              </div>
            ) : <p className="lead">{room.case || t.waitHost}</p>}
          </div>
        )}

        {room.phase !== "lobby" && <blockquote className="case">{room.case}</blockquote>}

        {room.phase === "statements" && (
          <div className="statement">
            {mine?.submitted ? <p className="lead">{t.submitted}. {t.waitOthers}</p> : (
              <>
                <label>{t.yourPosition}<textarea rows={5} maxLength={1200} value={stmt} onChange={(e) => setStmt(e.target.value)} /></label>
                <div className="row">
                  {voiceInputSupported && <button className="ghost" onClick={dict.listening ? dict.stop : dict.start}>{dict.listening ? t.micStop : t.pickMic}</button>}
                  <button className="primary" disabled={stmt.trim().length < 5} onClick={() => send({ type: "statement", text: stmt })}>{t.submit}</button>
                </div>
              </>
            )}
            {isHost && <button className="ghost small" onClick={() => send({ type: "force_next" })}>{t.forceNext}</button>}
          </div>
        )}

        {room.phase === "questions" && (
          <div className="questions">
            {Object.entries(room.statements).map(([id, s]) => <p key={id} className="stmt"><b>{nameOf(id)}:</b> {s}</p>)}
            {room.questions.map((q) => (
              <div key={q.id} className={`q ${q.answer ? "answered" : ""}`}>
                <p><b>{t.judgeAsks} → {nameOf(q.to)}:</b> {q.text}</p>
                {q.answer ? <p className="ans">{q.answer}</p> : q.to === me && (
                  <>
                    <textarea rows={2} maxLength={1000} placeholder={t.yourAnswer} value={answers[q.id] || ""} onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })} />
                    <button className="primary small" disabled={!(answers[q.id] || "").trim()} onClick={() => send({ type: "answer", qid: q.id, text: answers[q.id] })}>{t.answer}</button>
                  </>
                )}
              </div>
            ))}
            {isHost && <button className="ghost small" onClick={() => send({ type: "force_next" })}>{t.toVerdict}</button>}
          </div>
        )}

        {room.phase === "verdict" && room.verdict && (
          <div className="verdict">
            <h3>{t.verdict}</h3>
            <p className="headline">{room.verdict.headline}</p>
            {room.verdict.strong.length > 0 && <><h4>{t.strong}</h4><ul>{room.verdict.strong.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
            {room.verdict.weak.length > 0 && <><h4>{t.weak}</h4><ul>{room.verdict.weak.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
            {room.verdict.next_steps.length > 0 && <><h4>{t.next}</h4><ul>{room.verdict.next_steps.map((x, i) => <li key={i}>{x}</li>)}</ul></>}
            <Sources sources={room.verdict.sources} t={t} />
            <small className="disclaimer">{room.verdict.disclaimer}</small>
            {!room.verdict.refused && <Complaint situation={[room.case, ...Object.values(room.statements)].join(" ")} lang={lang} t={t} />}
            <button className="ghost" onClick={onExit}>{t.newCourt}</button>
          </div>
        )}
      </section>
    </div>
  );
}
