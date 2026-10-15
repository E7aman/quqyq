export function Badge({ s, t }) {
  let text = t.badgeDemo, cls = "demo";
  if (s.constitution && s.verified) { text = t.badgeConst; cls = "const"; }
  else if (s.constitution) { text = t.badgeConstDemo; cls = "demo"; }
  else if (s.verified) { text = t.badgeOk; cls = "ok"; }
  return <span className={`badge ${cls}`}>{text}</span>;
}

export default function Sources({ sources, t }) {
  if (!sources?.length) return null;
  return (
    <div className="sources">
      {sources.map((s) => (
        <article key={s.id} className="source">
          <Badge s={s} t={t} />
          <h4>{s.title}</h4>
          <p className="article">{s.article}</p>
          <blockquote>{s.quote}</blockquote>
          <div className="meter" title={t.confidence}>
            <span style={{ width: `${Math.round((s.confidence || 0) * 100)}%` }} />
          </div>
          <small>{t.confidence}: {Math.round((s.confidence || 0) * 100)}%</small>
          {s.url && <a href={s.url} target="_blank" rel="noreferrer">{t.open}</a>}
        </article>
      ))}
    </div>
  );
}
