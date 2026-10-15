const TOKEN_KEY = "quqyq:auth:v1";

export const readAuthToken = () => {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
};

export const clearAuthToken = () => {
  try { localStorage.removeItem(TOKEN_KEY); } catch { /* браузер запрещает доступ к хранилищу */ }
};

function saveAuthToken(token) {
  try { localStorage.setItem(TOKEN_KEY, token); } catch { throw new Error("Не удалось сохранить вход в этом браузере"); }
}

async function request(url, options = {}, authenticated = true) {
  const { parseBlob, ...fetchOptions } = options;
  const headers = { ...(typeof FormData !== "undefined" && fetchOptions.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...(fetchOptions.headers || {}) };
  const token = authenticated && readAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(url, { ...fetchOptions, headers });
  const data = parseBlob ? await r.blob() : await r.json().catch(() => ({}));
  if (!r.ok) {
    const error = new Error(data.error || "Ошибка сервера");
    error.status = r.status;
    throw error;
  }
  return data;
}

const post = (url, body, authenticated = true) => request(url, { method: "POST", body: JSON.stringify(body) }, authenticated);

export async function registerAccount(body) {
  const data = await post("/api/auth/register/", body, false);
  saveAuthToken(data.token);
  return data.user;
}

export async function loginAccount(body) {
  const data = await post("/api/auth/login/", body, false);
  saveAuthToken(data.token);
  return data.user;
}

export const currentAccount = () => request("/api/auth/me/");
export const listAccountChats = () => request("/api/chats/");
export const getAccountChat = (id) => request(`/api/chats/${encodeURIComponent(id)}/`);
export const deleteAccountChat = (id) => request(`/api/chats/${encodeURIComponent(id)}/`, { method: "DELETE" });
export const clearAccountChats = () => request("/api/chats/", { method: "DELETE" });

export async function logoutAccount() {
  try { await post("/api/auth/logout/", {}); } finally { clearAuthToken(); }
}

export const chat = (message, lang, history = [], chatId = null) => {
  const body = { message, lang, history };
  if (readAuthToken()) body.chat_id = chatId || "new";
  return post("/api/chat/", body);
};
export const createRoom = (lang) => post("/api/rooms/", { lang });
export const draftComplaint = (body) => post("/api/complaint/draft/", body);

export async function downloadDocx(body) {
  const blob = await request("/api/complaint/docx/", { method: "POST", body: JSON.stringify(body), parseBlob: true });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: "zhaloba.docx" });
  a.click();
  URL.revokeObjectURL(url);
}

export async function analyzeImage(file, lang) {
  const fd = new FormData();
  fd.append("image", file);
  fd.append("lang", lang);
  return request("/api/analyze/", { method: "POST", body: fd });
}

export function courtSocket(code) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${proto}://${location.host}/ws/court/${code}/`);
}
