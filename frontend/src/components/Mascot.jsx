import { useEffect, useId, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

/**
 * Барс-судья. Слои: хвост, тело, уши, голова, глаза (следят за курсором), веки (моргают),
 * брови, рот, лапа у подбородка, молоток.
 * mood: idle | listening | thinking | speaking | stern | surprised | happy | pointing
 */
const FUR = "#E9E4F2", FUR_DARK = "#9B91AB", SPOT = "#332447", COAT_MARK = "#100D13", ROBE = "#15111F", WOOD = "#0B0910", GOLD = "#8B5CF6", IRIS = "#A78BFA";

export default function Mascot({ mood = "idle", speaking = false, gavelKey = 0, robe = true }) {
  const reduce = useReducedMotion();
  const glowId = `bars-glow-${useId().replaceAll(":", "")}`;
  const svg = useRef(null);
  const [gaze, setGaze] = useState({ x: 0, y: 0 });
  const [blink, setBlink] = useState(false);
  const [mouth, setMouth] = useState(0);
  const [earTwitch, setEarTwitch] = useState(0);

  // Глаза следят за курсором
  useEffect(() => {
    if (reduce) return;
    const move = (e) => {
      const r = svg.current?.getBoundingClientRect();
      if (!r) return;
      const dx = (e.clientX - (r.left + r.width / 2)) / r.width;
      const dy = (e.clientY - (r.top + r.height * 0.4)) / r.height;
      setGaze({ x: Math.max(-1, Math.min(1, dx * 2)) * 4, y: Math.max(-1, Math.min(1, dy * 2)) * 3 });
    };
    window.addEventListener("pointermove", move);
    return () => window.removeEventListener("pointermove", move);
  }, [reduce]);

  // Моргание и подёргивание уха в случайные моменты
  useEffect(() => {
    if (reduce) return;
    let t1, t2;
    const loopBlink = () => { setBlink(true); setTimeout(() => setBlink(false), 130); t1 = setTimeout(loopBlink, 2200 + Math.random() * 3200); };
    const loopEar = () => { setEarTwitch((n) => n + 1); t2 = setTimeout(loopEar, 4000 + Math.random() * 5000); };
    t1 = setTimeout(loopBlink, 1800); t2 = setTimeout(loopEar, 3000);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [reduce]);

  // Рот двигается, пока идёт озвучка / реплика
  const talking = speaking || mood === "speaking";
  useEffect(() => {
    if (!talking) { setMouth(0); return; }
    if (reduce) { setMouth(4); return; }
    const id = setInterval(() => setMouth(Math.random() > 0.3 ? 3 + Math.random() * 5 : 1), 130);
    return () => clearInterval(id);
  }, [talking, reduce]);

  const listening = mood === "listening";
  const thinking = mood === "thinking";
  const stern = mood === "stern";
  const surprised = mood === "surprised";
  const happy = mood === "happy";
  const lookUp = thinking ? { x: 3, y: -4 } : null;
  const g = lookUp || (listening ? { x: gaze.x * 0.5, y: 2 } : gaze);
  const browL = stern ? "M108 98 L138 106" : surprised ? "M110 92 Q124 84 138 92" : thinking ? "M110 98 Q124 92 138 97" : "M110 100 Q124 96 138 100";
  const browR = stern ? "M192 98 L162 106" : surprised ? "M190 92 Q176 84 162 92" : "M190 100 Q176 96 162 100";
  const eyeRy = surprised ? 10 : happy ? 5 : 8;

  return (
    <svg ref={svg} viewBox="0 0 300 300" className="mascot" role="img" aria-label="Барс-судья">
      <defs>
        <linearGradient id={`${glowId}-ear`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#C4B5FD" stopOpacity=".9" />
          <stop offset="1" stopColor="#7C3AED" stopOpacity=".48" />
        </linearGradient>
        <filter id={glowId} x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="2.5" result="blur" />
          <feFlood floodColor="#A78BFA" floodOpacity=".78" result="purple" />
          <feComposite in="purple" in2="blur" operator="in" result="aura" />
          <feMerge><feMergeNode in="aura" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {/* хвост */}
      <motion.path d="M236 270 Q290 250 280 205 Q276 188 262 196" fill="none" stroke={FUR} strokeWidth="16" strokeLinecap="round"
        style={{ originX: "0%", originY: "100%", filter: "drop-shadow(0 0 6px rgba(139,92,246,.5))" }} animate={reduce ? {} : { rotate: [0, 6, -3, 0] }} transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }} />
      <path d="M262 196 Q270 190 276 200" fill="none" stroke={COAT_MARK} strokeWidth="5" strokeLinecap="round" opacity=".96" />

      {/* тело */}
      <motion.g animate={reduce ? {} : { y: [0, -2, 0] }} transition={{ repeat: Infinity, duration: 3.6, ease: "easeInOut" }}>
        <path d="M62 300 Q66 196 150 176 Q234 196 238 300 Z" fill={robe ? ROBE : FUR}
          style={robe ? { filter: "drop-shadow(0 0 6px rgba(139,92,246,.24))" } : undefined} />
        {robe && <path d="M126 182 L150 222 L174 182 Q150 174 126 182Z" fill="#E8E0F3" />}
        {robe && <path d="M150 222 L150 300" stroke="#2A2038" strokeWidth="2" />}
        {robe && <path d="M80 244 Q105 215 126 210 M220 244 Q195 215 174 210" fill="none" stroke="#5A427B" strokeWidth="1.5" opacity=".7" />}

        {/* голова */}
        <motion.g style={{ originX: "50%", originY: "92%" }} animate={{ rotate: listening ? 7 : thinking ? -4 : 0, y: surprised ? -4 : 0 }} transition={{ type: "spring", stiffness: 120, damping: 14 }}>
          {/* уши */}
          <motion.g style={{ originX: "75%", originY: "100%" }} animate={{ rotate: listening ? -10 : earTwitch % 2 ? [0, -9, 0] : 0 }} transition={{ duration: 0.25 }}>
            <path d="M90 90 Q82 44 112 54 Q128 62 130 84 Z" fill={FUR} stroke="#B7A6D4" strokeWidth="2.2" />
            <path d="M99 82 Q96 58 112 62 Q120 68 121 80 Z" fill={`url(#${glowId}-ear)`} stroke="#A78BFA" strokeWidth=".7" filter={`url(#${glowId})`} />
            <path d="M89 87 Q82 45 111 54" fill="none" stroke="#C4B5FD" strokeWidth="1.2" opacity=".78" filter={`url(#${glowId})`} />
          </motion.g>
          <motion.g style={{ originX: "25%", originY: "100%" }} animate={{ rotate: listening ? 10 : 0 }} transition={{ duration: 0.25 }}>
            <path d="M210 90 Q218 44 188 54 Q172 62 170 84 Z" fill={FUR} stroke="#B7A6D4" strokeWidth="2.2" />
            <path d="M201 82 Q204 58 188 62 Q180 68 179 80 Z" fill={`url(#${glowId}-ear)`} stroke="#A78BFA" strokeWidth=".7" filter={`url(#${glowId})`} />
            <path d="M211 87 Q218 45 189 54" fill="none" stroke="#C4B5FD" strokeWidth="1.2" opacity=".78" filter={`url(#${glowId})`} />
          </motion.g>
          {/* голова и щёки */}
          <ellipse cx="150" cy="122" rx="64" ry="54" fill={FUR} stroke={FUR_DARK} strokeWidth="2" />
          <path d="M92 130 Q80 150 98 160 Q108 150 104 136Z M208 130 Q220 150 202 160 Q192 150 196 136Z" fill={FUR} />
          {[[120, 80], [150, 74], [180, 80], [100, 108], [200, 108]].map(([x, y], i) => (
            <g key={i}>
              <ellipse cx={x} cy={y} rx="5.4" ry="3.6" fill={COAT_MARK} opacity=".98" />
              <ellipse cx={x - 1} cy={y - 1} rx="1.5" ry=".8" fill="#A78BFA" opacity=".72" filter={`url(#${glowId})`} />
            </g>
          ))}
          {/* глаза */}
          {[127, 173].map((cx) => (
            <g key={cx}>
              <ellipse cx={cx} cy="118" rx="13" ry={eyeRy} fill="#F7F3FC" stroke={SPOT} strokeWidth="1.5" />
              <circle cx={cx + g.x} cy={118 + g.y} r={happy ? 0 : 6.2} fill={IRIS} filter={`url(#${glowId})`} />
              <circle cx={cx + g.x} cy={118 + g.y} r={happy ? 0 : 3} fill="#160E21" />
              {happy && <path d={`M${cx - 10} 120 Q${cx} 110 ${cx + 10} 120`} fill="none" stroke="#160E21" strokeWidth="3" strokeLinecap="round" />}
              <motion.ellipse cx={cx} cy="118" rx="14" fill={FUR} initial={{ ry: 0 }} animate={{ ry: blink ? 11 : 0 }} transition={{ duration: 0.06 }} />
            </g>
          ))}
          <motion.path animate={{ d: browL }} d={browL} stroke={SPOT} strokeWidth="4" strokeLinecap="round" fill="none" />
          <motion.path animate={{ d: browR }} d={browR} stroke={SPOT} strokeWidth="4" strokeLinecap="round" fill="none" />
          {/* нос, рот, усы */}
          <path d="M142 136 L158 136 L150 146 Z" fill="#C98E8E" stroke={SPOT} strokeWidth="1.2" strokeLinejoin="round" />
          {mouth > 1.5 ? <ellipse cx="150" cy={152 + mouth / 2} rx="8" ry={mouth} fill="#5A2E35" /> :
            <path d={happy ? "M134 150 Q150 166 166 150" : stern ? "M138 156 Q150 150 162 156" : "M138 152 Q144 158 150 150 Q156 158 162 152"} fill="none" stroke={SPOT} strokeWidth="2.2" strokeLinecap="round" />}
          <path d="M101 140 L68 134 M101 148 L66 150 M199 140 L232 134 M199 148 L234 150" stroke={COAT_MARK} strokeWidth="1.6" strokeLinecap="round" />
          {/* лапа у подбородка: «думает» */}
          <motion.g initial={false} animate={{ opacity: thinking ? 1 : 0, y: thinking ? 0 : 24 }} transition={{ duration: 0.3 }}>
            <ellipse cx="164" cy="178" rx="17" ry="12" fill={FUR} stroke={FUR_DARK} strokeWidth="2" />
            <path d="M154 176 v-5 M164 174 v-6 M174 176 v-5" stroke={FUR_DARK} strokeWidth="2" strokeLinecap="round" />
          </motion.g>
        </motion.g>
      </motion.g>

      {/* стол, лапы, молоток */}
      <rect x="0" y="262" width="300" height="38" fill={WOOD} />
      <rect x="0" y="262" width="300" height="5" fill="#64458F" />
      <rect x="120" y="274" width="60" height="14" rx="3" fill={GOLD} />
      <ellipse cx="108" cy="262" rx="20" ry="11" fill={FUR} stroke={FUR_DARK} strokeWidth="2" />
      <motion.ellipse cx="196" cy="262" rx="20" ry="11" fill={FUR} stroke={FUR_DARK} strokeWidth="2" animate={{ y: mood === "pointing" ? -8 : 0 }} />
      <motion.g key={gavelKey} style={{ originX: "50%", originY: "100%" }} animate={gavelKey ? { rotate: [0, -50, 8, 0] } : {}} transition={{ duration: 0.5, times: [0, 0.4, 0.6, 1] }}>
        <rect x="259" y="228" width="5" height="32" rx="2" fill="#251B32" />
        <rect x="248" y="222" width="28" height="12" rx="3" fill="#39274F" stroke="#8B5CF6" strokeWidth="1.2" />
      </motion.g>
    </svg>
  );
}
