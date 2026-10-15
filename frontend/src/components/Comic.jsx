import { motion } from "framer-motion";

/** Панели комикса: каждая реплика барса — облачко; появляются по очереди по действию пользователя (новый ответ). */
export default function Comic({ panels, refused, onPanel }) {
  return (
    <div className={`comic ${refused ? "refused" : ""}`}>
      {panels.map((p, i) => (
        <motion.div key={i} className="panel" initial={{ opacity: 0, scale: 0.92, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: i * 0.6, type: "spring", stiffness: 200, damping: 18 }} onAnimationStart={() => onPanel?.(p, i)}>
          <p>{p.bubble}</p>
        </motion.div>
      ))}
    </div>
  );
}
