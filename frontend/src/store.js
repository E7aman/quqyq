// Локальная копия истории хранится в браузере; авторизованные диалоги дополнительно сохраняются в аккаунте.
const KEY = "quqyq:chats:v1";
const MAX_CHATS = 40;
const MAX_MSGS = 120;

export const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

export function loadStore() {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || "null");
    if (s && Array.isArray(s.chats)) return { chats: s.chats, activeId: s.activeId ?? null };
  } catch { /* хранилище недоступно или повреждено: начинаем с пустого */ }
  return { chats: [], activeId: null };
}

export function saveStore(s) {
  try {
    const chats = s.chats.slice(0, MAX_CHATS).map((c) => ({ ...c, msgs: c.msgs.slice(-MAX_MSGS) }));
    localStorage.setItem(KEY, JSON.stringify({ chats, activeId: s.activeId }));
  } catch { /* переполнено или запрещено: чат продолжает работать без сохранения */ }
}

const titleFrom = (msgs) => {
  const u = msgs.find((m) => m.role === "user");
  return u ? u.text.replace(/\s+/g, " ").slice(0, 48) : "";
};

/** Чистая функция: обновляет сообщения чата id (создаёт чат, если его нет) и поднимает его наверх списка. */
export function applyUpdate(s, id, updater) {
  const cur = s.chats.find((c) => c.id === id) || { id, title: "", msgs: [], updated: Date.now() };
  const msgs = typeof updater === "function" ? updater(cur.msgs) : updater;
  const next = { ...cur, msgs, title: cur.title || titleFrom(msgs), updated: Date.now() };
  return { chats: [next, ...s.chats.filter((c) => c.id !== id)].slice(0, MAX_CHATS), activeId: s.activeId };
}
