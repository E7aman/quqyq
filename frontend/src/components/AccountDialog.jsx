import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { loginAccount, registerAccount } from "../api";

export default function AccountDialog({ mode, setMode, t, onClose, onAuthenticated }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const emailRef = useRef(null);
  const dialogRef = useRef(null);
  const busyRef = useRef(busy);
  const closeRef = useRef(onClose);
  busyRef.current = busy;
  closeRef.current = onClose;

  useEffect(() => {
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    emailRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === "Escape" && !busyRef.current) closeRef.current();
      if (event.key === "Tab") {
        const items = dialogRef.current?.querySelectorAll('button:not(:disabled), input:not(:disabled)');
        if (!items?.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus?.();
    };
  }, []);

  useEffect(() => { emailRef.current?.focus(); }, [mode]);

  const switchMode = (next) => {
    setError("");
    setMode(next);
  };

  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const account = mode === "register"
        ? await registerAccount({ name, email, password })
        : await loginAccount({ email, password });
      onAuthenticated(account);
    } catch (err) {
      setError(err.message || t.authError);
    } finally {
      setBusy(false);
    }
  };

  const isRegister = mode === "register";

  return (
    <motion.div
      className="auth-backdrop"
      role="presentation"
      onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <motion.section
        ref={dialogRef}
        className="auth-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
        initial={{ opacity: 0, y: 18, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        transition={{ duration: 0.25, ease: [0.2, 0.8, 0.2, 1] }}
      >
        <button className="auth-close" type="button" aria-label={t.close} onClick={onClose} disabled={busy}>×</button>
        <p className="auth-kicker">{t.authKicker}</p>
        <h2 id="auth-title">{isRegister ? t.authRegisterTitle : t.authLoginTitle}</h2>
        <p className="auth-description">{isRegister ? t.authRegisterLead : t.authLoginLead}</p>

        <form className="auth-form" onSubmit={submit}>
          {isRegister && (
            <label>{t.authName}
              <input value={name} onChange={(event) => setName(event.target.value)} maxLength={40} autoComplete="name" required />
            </label>
          )}
          <label>{t.authEmail}
            <input ref={emailRef} value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="email" maxLength={254} required />
          </label>
          <label>{t.authPassword}
            <span className="password-wrap">
              <input value={password} onChange={(event) => setPassword(event.target.value)} type={showPassword ? "text" : "password"} autoComplete={isRegister ? "new-password" : "current-password"} minLength={8} maxLength={128} required />
              <button className="password-toggle" type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? t.hidePassword : t.showPassword}>{showPassword ? t.hidePassword : t.showPassword}</button>
            </span>
            {isRegister && <small>{t.authPasswordHint}</small>}
          </label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="primary auth-submit" type="submit" disabled={busy}>
            {busy ? <><span className="button-spinner" aria-hidden="true" />{t.authWait}</> : isRegister ? t.authCreate : t.authContinue}
            {!busy && <span aria-hidden="true">↗</span>}
          </button>
        </form>

        <p className="auth-switch">
          {isRegister ? t.authHasAccount : t.authNoAccount}{" "}
          <button type="button" onClick={() => switchMode(isRegister ? "login" : "register")} disabled={busy}>
            {isRegister ? t.signIn : t.signUp}
          </button>
        </p>
        <p className="auth-footnote">{t.authPrivacy}</p>
      </motion.section>
    </motion.div>
  );
}
