import { useState } from "react";
import { draftComplaint, downloadDocx } from "../api";
import Sources from "./Sources";

export default function Complaint({ situation, lang, t }) {
  const [applicant, setApplicant] = useState("");
  const [recipient, setRecipient] = useState("");
  const [doc, setDoc] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const make = async () => {
    setBusy(true); setErr("");
    try { setDoc(await draftComplaint({ situation, lang, applicant, recipient })); }
    catch (e) { setErr(e.message || t.error); }
    setBusy(false);
  };
  const setPara = (i, v) => setDoc({ ...doc, paragraphs: doc.paragraphs.map((p, j) => (j === i ? v : p)) });
  const setDemand = (i, v) => setDoc({ ...doc, demands: doc.demands.map((p, j) => (j === i ? v : p)) });

  return (
    <section className="complaint">
      {!doc && (
        <>
          <label>{t.applicant}<input value={applicant} onChange={(e) => setApplicant(e.target.value)} maxLength={120} /></label>
          <label>{t.recipient}<input value={recipient} onChange={(e) => setRecipient(e.target.value)} maxLength={200} /></label>
          <button className="primary" onClick={make} disabled={busy}>{busy ? t.thinking : t.draft}</button>
        </>
      )}
      {err && <p className="error">{err}</p>}
      {doc && (
        <>
          <p className="hint">{t.draftHint}</p>
          <label>{t.recipient}<input value={doc.recipient} onChange={(e) => setDoc({ ...doc, recipient: e.target.value })} /></label>
          <label>{t.applicant}<input value={doc.applicant || ""} onChange={(e) => setDoc({ ...doc, applicant: e.target.value })} /></label>
          {doc.paragraphs.map((p, i) => <textarea key={i} rows={4} value={p} onChange={(e) => setPara(i, e.target.value)} />)}
          <h5>{t.demands}</h5>
          {doc.demands.map((d, i) => <textarea key={i} rows={2} value={d} onChange={(e) => setDemand(i, e.target.value)} />)}
          <Sources sources={doc.sources} t={t} />
          <button className="primary" onClick={() => downloadDocx({ ...doc, lang }).catch((e) => setErr(e.message))}>{t.download}</button>
        </>
      )}
    </section>
  );
}
