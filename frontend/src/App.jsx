import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Chat from "./components/Chat";
import Court from "./components/Court";
import Mascot from "./components/Mascot";
import AccountDialog from "./components/AccountDialog";
import BackgroundField from "./components/BackgroundField";
import { T } from "./i18n";
import { clearAuthToken, currentAccount, logoutAccount, readAuthToken } from "./api";

const initialCode = new URLSearchParams(location.search).get("code")?.toUpperCase() || "";

function HeroVisual({ t }) {
  return (
    <div className="hero-visual" aria-label={t.heroVisualLabel}>
      <div className="hero-orbit orbit-one" />
      <div className="hero-orbit orbit-two" />
      <div className="hero-orbit orbit-three" />
      <div className="hero-halo" />
      <motion.div
        className="hero-mascot"
        initial={{ opacity: 0, y: 22, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.2, 0.8, 0.2, 1] }}
      >
        <Mascot mood="idle" robe />
      </motion.div>
      <motion.div
        className="floating-card source-float"
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 4.2, ease: "easeInOut", repeat: Infinity }}
      >
        <span className="float-icon">↗</span>
        <span><small>{t.heroCardEyebrow}</small><strong>{t.heroCardTitle}</strong></span>
      </motion.div>
      <motion.div
        className="floating-card answer-float"
        animate={{ y: [0, 7, 0] }}
        transition={{ duration: 3.8, ease: "easeInOut", repeat: Infinity, delay: 0.25 }}
      >
        <span className="answer-check">✓</span>
        <span><small>{t.heroAnswerEyebrow}</small><strong>{t.heroAnswerTitle}</strong></span>
      </motion.div>
      <div className="hero-corner-note"><span className="status-dot" />{t.heroVisualNote}</div>
    </div>
  );
}

export default function App() {
  const [lang, setLang] = useState("ru");
  const [tab, setTab] = useState(initialCode ? "court" : "chat");
  const [authMode, setAuthMode] = useState(null);
  const [user, setUser] = useState(null);
  const [accountLoading, setAccountLoading] = useState(false);
  const t = T[lang];

  useEffect(() => { document.documentElement.lang = lang === "kk" ? "kk" : "ru"; }, [lang]);

  useEffect(() => {
    if (!readAuthToken()) return undefined;
    let mounted = true;
    setAccountLoading(true);
    currentAccount()
      .then((account) => { if (mounted) setUser(account); })
      .catch((error) => {
        if (error.status === 401) clearAuthToken();
      })
      .finally(() => { if (mounted) setAccountLoading(false); });
    return () => { mounted = false; };
  }, []);

  const startQuestion = () => {
    document.getElementById("assistant")?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => document.querySelector("#assistant textarea")?.focus(), 450);
  };

  const switchTab = (nextTab) => {
    setTab(nextTab);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const signOut = async () => {
    try { await logoutAccount(); } catch { clearAuthToken(); }
    setUser(null);
  };

  return (
    <div className="app">
      <BackgroundField />
      <header className="top">
        <button className="brand" onClick={() => { setTab("chat"); window.scrollTo({ top: 0, behavior: "smooth" }); }} aria-label="Qūqyq AI — на главную">
          <span className="brand-name">Qūqyq AI</span>
        </button>
        <nav aria-label={t.sections}>
          <button className={tab === "chat" ? "nav-link on" : "nav-link"} onClick={() => switchTab("chat")}>
            {t.tabChat}
          </button>
          <button className={tab === "court" ? "nav-link on" : "nav-link"} onClick={() => switchTab("court")}>
            {t.tabCourt}
          </button>
        </nav>
        <div className="header-actions">
          <div className="lang" role="group" aria-label={t.language}>
            <button className={lang === "ru" ? "on" : ""} aria-pressed={lang === "ru"} onClick={() => setLang("ru")}>RU</button>
            <button className={lang === "kk" ? "on" : ""} aria-pressed={lang === "kk"} onClick={() => setLang("kk")}>ҚАЗ</button>
          </div>
          <span className="header-divider" aria-hidden="true" />
          {user ? (
            <div className="account-actions">
              <span className="account-chip" title={user.email}>
                <span className="account-avatar">{(user.name || user.email || "Q").slice(0, 1).toUpperCase()}</span>
                <span className="account-name">{user.name || user.email}</span>
              </span>
              <button className="logout-button" onClick={signOut}>{t.signOut}</button>
            </div>
          ) : (
            <div className="account-actions">
              <button className="login-button" onClick={() => setAuthMode("login")} disabled={accountLoading}>{t.signIn}</button>
              <button className="signup-button" onClick={() => setAuthMode("register")} disabled={accountLoading}>{t.signUp}</button>
            </div>
          )}
        </div>
      </header>

      <main>
        <div hidden={tab !== "chat"}>
          <section className="hero">
            <div className="hero-copy">
              <div className="eyebrow"><span className="eyebrow-mark">✳</span>{t.heroKicker}</div>
              <h1>{t.heroTitleA}<br /><span>{t.heroTitleB}</span></h1>
              <p className="hero-lead">{t.heroLead}</p>
              <div className="hero-actions">
                <button className="primary hero-primary" onClick={startQuestion}>{t.heroAsk}<span aria-hidden="true">↗</span></button>
                <button className="secondary hero-secondary" onClick={() => switchTab("court")}>{t.heroCourt}<span aria-hidden="true">→</span></button>
              </div>
              <div className="hero-proof">
                <p><strong>{t.heroProofTitle}</strong><br /><span>{t.heroProofText}</span></p>
              </div>
            </div>
            <HeroVisual t={t} />
            <div className="hero-index" aria-hidden="true">01 <span /> 02</div>
          </section>

          <section className="value-strip" aria-label={t.benefitsLabel}>
            <div className="value-item"><span className="value-num">01</span><div><strong>{t.benefitOne}</strong><small>{t.benefitOneText}</small></div></div>
            <div className="value-item"><span className="value-num">02</span><div><strong>{t.benefitTwo}</strong><small>{t.benefitTwoText}</small></div></div>
            <div className="value-item"><span className="value-num">03</span><div><strong>{t.benefitThree}</strong><small>{t.benefitThreeText}</small></div></div>
          </section>

          <section id="assistant" className="assistant-section">
            <div className="section-heading">
              <div>
                <div className="eyebrow"><span className="status-dot" />{t.workspaceKicker}</div>
                <h2>{t.workspaceTitle}</h2>
              </div>
              <p>{t.workspaceLead}</p>
            </div>
            <Chat lang={lang} t={t} account={user} />
          </section>
        </div>

        <div className="court-screen" hidden={tab !== "court"}>
          <div className="court-eyebrow eyebrow"><span className="status-dot" />{t.courtKicker}</div>
          <Court lang={lang} t={t} initialCode={initialCode} />
        </div>
      </main>

      <footer className="site-footer">
        <span className="footer-brand">Qūqyq AI</span>
        <span>{t.disclaimer}</span>
        <span className="footer-caption">{t.footerCaption}</span>
      </footer>

      <AnimatePresence>
        {authMode && <AccountDialog mode={authMode} setMode={setAuthMode} lang={lang} t={t} onClose={() => setAuthMode(null)} onAuthenticated={(account) => { setUser(account); setAuthMode(null); }} />}
      </AnimatePresence>
    </div>
  );
}
