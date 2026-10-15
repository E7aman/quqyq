import { useCallback, useEffect, useRef, useState } from "react";

const SR = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;
export const voiceInputSupported = !!SR;

/** Голосовой ввод (Web Speech API). Казахский зависит от браузера — проверьте заранее. */
export function useDictation(lang, onText) {
  const [listening, setListening] = useState(false);
  const rec = useRef(null);
  const start = useCallback(() => {
    if (!SR) return;
    const r = new SR();
    r.lang = lang === "kk" ? "kk-KZ" : "ru-RU";
    r.interimResults = true;
    r.onresult = (e) => onText(Array.from(e.results).map((x) => x[0].transcript).join(" "));
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  }, [lang, onText]);
  const stop = useCallback(() => rec.current?.stop(), []);
  useEffect(() => () => rec.current?.abort?.(), []);
  return { listening, start, stop };
}

/** Озвучка браузером. Рот барса двигается, пока speaking=true. */
export function useSpeech(lang) {
  const [speaking, setSpeaking] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const speak = useCallback((text) => {
    if (!enabled || !("speechSynthesis" in window) || !text) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang === "kk" ? "kk-KZ" : "ru-RU";
    u.onstart = () => setSpeaking(true);
    u.onend = u.onerror = () => setSpeaking(false);
    speechSynthesis.speak(u);
  }, [enabled, lang]);
  const stop = useCallback(() => { speechSynthesis?.cancel(); setSpeaking(false); }, []);
  return { speaking, enabled, setEnabled, speak, stop };
}
