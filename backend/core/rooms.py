"""Комнаты суда в памяти процесса. Один игрок = комната на одного (тот же код)."""
import random
import time
import uuid

ROOMS = {}
MAX_PLAYERS = 6
TTL = 3 * 3600
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _cleanup():
    now = time.time()
    for code in [c for c, r in ROOMS.items() if now - r["created"] > TTL]:
        ROOMS.pop(code, None)


def create_room(lang="ru"):
    _cleanup()
    while True:
        code = "".join(random.choice(_ALPHABET) for _ in range(5))
        if code not in ROOMS:
            break
    ROOMS[code] = {"code": code, "lang": lang if lang in ("ru", "kk") else "ru", "phase": "lobby", "case": "",
                   "players": {}, "statements": {}, "questions": [], "judge": {"mood": "idle", "text": ""},
                   "verdict": None, "busy": False, "created": time.time(), "host": None}
    return code


def get_room(code):
    return ROOMS.get(code)


def add_player(room, name, role):
    if len(room["players"]) >= MAX_PLAYERS:
        return None
    pid = uuid.uuid4().hex[:8]
    room["players"][pid] = {"name": name[:24] or "Игрок", "role": role, "online": True}
    if room["host"] is None:
        room["host"] = pid
    return pid


def public_state(room):
    reveal = room["phase"] in ("questions", "verdict")
    return {
        "code": room["code"], "lang": room["lang"], "phase": room["phase"], "case": room["case"],
        "host": room["host"], "busy": room["busy"], "judge": room["judge"],
        "players": [{"id": pid, "name": p["name"], "role": p["role"], "online": p["online"],
                     "submitted": pid in room["statements"]} for pid, p in room["players"].items()],
        "statements": room["statements"] if reveal else {},
        "questions": room["questions"], "verdict": room["verdict"],
    }
