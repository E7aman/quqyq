import io
import json
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from . import llm, rooms


@override_settings(GEMINI_API_KEY="", PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountApiTests(TestCase):
    def setUp(self):
        cache.clear()

    # --- помощники ---
    def call(self, method, url, data=None, token=None):
        kw = {"content_type": "application/json"}
        if token:
            kw["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        body = json.dumps(data) if data is not None else None
        return getattr(self.client, method)(url, body, **kw) if body is not None else getattr(self.client, method)(url, **kw)

    def register(self, email="a@test.kz", pw="password123"):
        r = self.call("post", "/api/auth/register/", {"email": email, "password": pw, "name": "Айдар"})
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["token"]

    # --- авторизация ---
    def test_register_login_me_logout(self):
        tok = self.register()
        me = self.call("get", "/api/auth/me/", token=tok).json()
        self.assertEqual(me["email"], "a@test.kz")
        self.assertEqual(me["settings"]["lang"], "ru")
        login = self.call("post", "/api/auth/login/", {"email": "A@Test.kz", "password": "password123"})
        self.assertEqual(login.status_code, 200)  # email нечувствителен к регистру
        self.call("post", "/api/auth/logout/", token=tok)
        self.assertEqual(self.call("get", "/api/auth/me/", token=tok).status_code, 401)

    def test_register_validation(self):
        self.assertEqual(self.call("post", "/api/auth/register/", {"email": "bad", "password": "password123"}).status_code, 400)
        self.assertEqual(self.call("post", "/api/auth/register/", {"email": "b@test.kz", "password": "short"}).status_code, 400)
        self.register()
        self.assertEqual(self.call("post", "/api/auth/register/", {"email": "a@test.kz", "password": "password123"}).status_code, 409)

    def test_wrong_password_same_error(self):
        self.register()
        r1 = self.call("post", "/api/auth/login/", {"email": "a@test.kz", "password": "wrong-wrong"})
        r2 = self.call("post", "/api/auth/login/", {"email": "nobody@test.kz", "password": "wrong-wrong"})
        self.assertEqual((r1.status_code, r2.status_code), (401, 401))
        self.assertEqual(r1.json(), r2.json())

    def test_login_rate_limited(self):
        codes = [self.call("post", "/api/auth/login/", {"email": "x@test.kz", "password": "whatever1"}).status_code for _ in range(13)]
        self.assertIn(429, codes)

    def test_delete_account_removes_data(self):
        tok = self.register()
        self.call("post", "/api/chat/", {"message": "Имею ли я право на образование", "chat_id": "new"}, tok)
        self.assertEqual(self.call("delete", "/api/auth/me/", token=tok).status_code, 200)
        from .models import Chat
        self.assertEqual(Chat.objects.count(), 0)

    def test_protected_endpoints_need_login(self):
        for url in ("/api/chats/", "/api/library/", "/api/settings/", "/api/auth/me/"):
            self.assertEqual(self.call("get", url).status_code, 401, url)

    # --- чаты ---
    def test_chat_saved_listed_searched_renamed_deleted(self):
        tok = self.register()
        r = self.call("post", "/api/chat/", {"message": "Имею ли я право на образование", "chat_id": "new"}, tok).json()
        cid = r["chat_id"]
        r2 = self.call("post", "/api/chat/", {"message": "Меня уволили без причины", "chat_id": cid}, tok).json()
        self.assertEqual(r2["chat_id"], cid)  # продолжение того же чата
        listing = self.call("get", "/api/chats/", token=tok).json()["chats"]
        self.assertEqual(len(listing), 1)
        self.assertTrue(listing[0]["title"].startswith("Имею ли я право"))
        detail = self.call("get", f"/api/chats/{cid}/", token=tok).json()
        self.assertEqual([m["role"] for m in detail["messages"]], ["user", "bot", "user", "bot"])
        self.assertTrue(detail["messages"][1]["data"]["sources"])  # полный ответ с источниками сохранён
        # поиск по чатам, регистр кириллицы не важен
        hit = self.client.get("/api/chats/?q=УВОЛИЛИ", HTTP_AUTHORIZATION=f"Bearer {tok}").json()["chats"]
        self.assertEqual(len(hit), 1)
        miss = self.client.get("/api/chats/?q=плов", HTTP_AUTHORIZATION=f"Bearer {tok}").json()["chats"]
        self.assertEqual(miss, [])
        self.assertEqual(self.call("patch", f"/api/chats/{cid}/", {"title": "Моё дело"}, tok).json()["title"], "Моё дело")
        self.assertEqual(self.call("delete", f"/api/chats/{cid}/", token=tok).status_code, 200)
        self.assertEqual(self.call("get", f"/api/chats/{cid}/", token=tok).status_code, 404)

    def test_users_cannot_see_each_others_chats(self):
        a = self.register("a@test.kz")
        b = self.register("b@test.kz")
        cid = self.call("post", "/api/chat/", {"message": "Имею ли я право на образование"}, a).json()["chat_id"]
        self.assertEqual(self.call("get", f"/api/chats/{cid}/", token=b).status_code, 404)
        self.assertEqual(self.call("delete", f"/api/chats/{cid}/", token=b).status_code, 404)
        self.assertEqual(self.call("get", "/api/chats/", token=b).json()["chats"], [])
        # и дописать в чужой чат нельзя
        self.assertEqual(self.call("post", "/api/chat/", {"message": "привет", "chat_id": cid}, b).status_code, 404)

    def test_anonymous_chat_still_works_and_is_not_saved(self):
        r = self.call("post", "/api/chat/", {"message": "Имею ли я право на образование"}).json()
        self.assertNotIn("chat_id", r)
        self.assertTrue(r["sources"])

    def test_clear_all_chats(self):
        tok = self.register()
        self.call("post", "/api/chat/", {"message": "Имею ли я право на образование"}, tok)
        self.assertEqual(self.call("delete", "/api/chats/", token=tok).json()["deleted"] >= 1, True)
        self.assertEqual(self.call("get", "/api/chats/", token=tok).json()["chats"], [])

    # --- библиотека и настройки ---
    def test_library_crud_and_isolation(self):
        a, b = self.register("a@test.kz"), self.register("b@test.kz")
        item = self.call("post", "/api/library/", {"kind": "complaint", "title": "Жалоба в деканат", "payload": {"paragraphs": ["текст"]}}, a)
        self.assertEqual(item.status_code, 201)
        iid = item.json()["id"]
        self.assertEqual(len(self.call("get", "/api/library/", token=a).json()["items"]), 1)
        self.assertEqual(self.client.get("/api/library/?kind=source", HTTP_AUTHORIZATION=f"Bearer {a}").json()["items"], [])
        self.assertEqual(self.call("get", "/api/library/", token=b).json()["items"], [])
        self.assertEqual(self.call("delete", f"/api/library/{iid}/", token=b).status_code, 404)
        self.assertEqual(self.call("delete", f"/api/library/{iid}/", token=a).status_code, 200)

    def test_library_validation(self):
        tok = self.register()
        self.assertEqual(self.call("post", "/api/library/", {"kind": "hack", "title": "x"}, tok).status_code, 400)
        self.assertEqual(self.call("post", "/api/library/", {"kind": "answer", "title": "x", "payload": {"a": "я" * 30000}}, tok).status_code, 400)
        self.assertEqual(self.call("post", "/api/library/", {"kind": "answer", "title": ""}, tok).status_code, 400)

    def test_settings(self):
        tok = self.register()
        s = self.call("put", "/api/settings/", {"lang": "kk", "voice_out": True, "theme": "dark"}, tok).json()
        self.assertEqual(s, {"lang": "kk", "voice_out": True, "theme": "dark"})
        self.assertEqual(self.call("get", "/api/settings/", token=tok).json()["lang"], "kk")
        self.assertEqual(self.call("put", "/api/settings/", {"lang": "en"}, tok).status_code, 400)
        self.assertEqual(self.call("put", "/api/settings/", {"theme": "pink"}, tok).status_code, 400)

    # --- подсказки, комната, вложения, голос ---
    def test_suggestions(self):
        empty = self.client.get("/api/suggestions/?lang=ru").json()["suggestions"]
        self.assertEqual(len(empty), 6)
        typed = self.client.get("/api/suggestions/?q=уволили&lang=ru").json()["suggestions"]
        self.assertTrue(any("уволили" in s["text"].lower() for s in typed))
        art = self.client.get("/api/suggestions/?q=статья 33").json()["suggestions"]
        self.assertEqual(art[0]["kind"], "article")
        kk = self.client.get("/api/suggestions/?lang=kk").json()["suggestions"]
        self.assertIn("?", kk[0]["text"])

    def test_room_status_for_qr_join(self):
        code = rooms.create_room("ru")
        s = self.client.get(f"/api/rooms/{code}/").json()
        self.assertEqual((s["exists"], s["started"], s["full"], s["players"]), (True, False, False, 0))
        self.assertEqual(self.client.get("/api/rooms/ZZZZZ/").json(), {"exists": False})

    def test_analyze_accepts_pdf_but_needs_ai(self):
        pdf = SimpleUploadedFile("a.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.assertEqual(self.client.post("/api/analyze/", {"image": pdf}).status_code, 503)  # тип принят, ключа нет
        bad = SimpleUploadedFile("a.exe", b"MZ", content_type="application/octet-stream")
        self.assertEqual(self.client.post("/api/analyze/", {"image": bad}).status_code, 400)

    def test_transcribe(self):
        audio = lambda: SimpleUploadedFile("v.webm", b"fake", content_type="audio/webm;codecs=opus")
        self.assertEqual(self.client.post("/api/transcribe/", {"audio": audio()}).status_code, 503)  # без ключа
        with override_settings(GEMINI_API_KEY="x"), mock.patch("core.llm.generate_json", return_value={"text": "Привет, мир"}):
            r = self.client.post("/api/transcribe/", {"audio": audio(), "lang": "ru"})
        self.assertEqual(r.json()["text"], "Привет, мир")
        txt = SimpleUploadedFile("v.txt", b"x", content_type="text/plain")
        self.assertEqual(self.client.post("/api/transcribe/", {"audio": txt}).status_code, 400)
