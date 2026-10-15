"""WebSocket суда. Судья (ИИ) говорит по ходам: позиции → вопросы → вердикт."""
import asyncio
import time
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from . import rooms, services
from .security import clean_text, looks_like_injection

ROLES = ("plaintiff", "respondent", "witness")


class CourtConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.code = self.scope["url_route"]["kwargs"]["code"]
        self.room = rooms.get_room(self.code)
        self.group = f"court_{self.code}"
        self.pid = None
        self.stamps = []
        if not self.room:
            await self.close(code=4404)
            return
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "state", "room": rooms.public_state(self.room)})

    async def disconnect(self, code):
        if getattr(self, "group", None):
            await self.channel_layer.group_discard(self.group, self.channel_name)
        if self.pid and self.room and self.pid in self.room["players"]:
            self.room["players"][self.pid]["online"] = False
            await self.broadcast()

    # ----- вспомогательное -----
    def too_fast(self):
        now = time.time()
        self.stamps = [t for t in self.stamps if now - t < 60] + [now]
        return len(self.stamps) > 30

    async def broadcast(self):
        await self.channel_layer.group_send(self.group, {"type": "push"})

    async def push(self, event):
        await self.send_json({"type": "state", "room": rooms.public_state(self.room)})

    async def error(self, text):
        await self.send_json({"type": "error", "text": text})

    # ----- обработка сообщений -----
    async def receive_json(self, content, **kwargs):
        if self.too_fast():
            return await self.error("Слишком много сообщений. Подождите минуту.")
        room, kind = self.room, content.get("type")

        if kind == "join":
            if self.pid:
                return
            role = content.get("role") if content.get("role") in ROLES else "plaintiff"
            token = content.get("token")
            if token in room["players"]:  # переподключение
                self.pid = token
                room["players"][token]["online"] = True
            else:
                if room["phase"] != "lobby":
                    return await self.error("Заседание уже началось.")
                self.pid = rooms.add_player(room, clean_text(content.get("name"), 24), role)
                if not self.pid:
                    return await self.error("Комната заполнена.")
            await self.send_json({"type": "joined", "you": self.pid})
            return await self.broadcast()

        if not self.pid:
            return await self.error("Сначала войдите в комнату.")
        is_host = self.pid == room["host"]

        if kind == "set_case" and is_host and room["phase"] == "lobby":
            room["case"] = clean_text(content.get("text"), 600)
            return await self.broadcast()

        if kind == "start" and is_host and room["phase"] == "lobby":
            if len(room["case"]) < 10:
                return await self.error("Опишите дело (хотя бы одно предложение).")
            room["phase"] = "statements"
            room["judge"] = {"mood": "listening", "text": ""}
            return await self.broadcast()

        if kind == "statement" and room["phase"] == "statements":
            text = clean_text(content.get("text"), 1200)
            if len(text) < 5:
                return await self.error("Изложите позицию подробнее.")
            if looks_like_injection(text):
                return await self.error("Опишите факты по делу, без команд для ИИ.")
            room["statements"][self.pid] = text
            await self.broadcast()
            online = [p for p, v in room["players"].items() if v["online"]]
            if all(p in room["statements"] for p in online):
                await self.run_questions()
            return

        if kind == "force_next" and is_host:
            if room["phase"] == "statements" and room["statements"]:
                return await self.run_questions()
            if room["phase"] == "questions":
                return await self.run_verdict()

        if kind == "answer" and room["phase"] == "questions":
            text = clean_text(content.get("text"), 1000)
            if looks_like_injection(text):
                return await self.error("Отвечайте по существу дела.")
            for q in room["questions"]:
                if q["id"] == content.get("qid") and q["to"] == self.pid and not q.get("answer") and text:
                    q["answer"] = text
            await self.broadcast()
            if all(q.get("answer") for q in room["questions"]):
                await self.run_verdict()

    # ----- ходы судьи -----
    async def run_questions(self):
        room = self.room
        if room["busy"] or room["phase"] != "statements":
            return
        room["busy"], room["judge"] = True, {"mood": "thinking", "text": ""}
        await self.broadcast()
        try:
            res = await asyncio.to_thread(services.judge_questions, room)
            room["questions"] = [{"id": f"q{i}", "to": q["to"], "text": q["text"], "answer": ""} for i, q in enumerate(res["questions"])]
            room["judge"] = {"mood": res["mood"], "text": res["opening"]}
            room["phase"] = "questions"
        finally:
            room["busy"] = False
        await self.broadcast()

    async def run_verdict(self):
        room = self.room
        if room["busy"] or room["phase"] != "questions":
            return
        room["busy"], room["judge"] = True, {"mood": "thinking", "text": ""}
        await self.broadcast()
        try:
            room["verdict"] = await asyncio.to_thread(services.judge_verdict, room)
            room["judge"] = {"mood": room["verdict"]["mood"], "text": room["verdict"]["headline"]}
            room["phase"] = "verdict"
        finally:
            room["busy"] = False
        await self.broadcast()
