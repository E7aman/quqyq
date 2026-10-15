
import os
import asyncio

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from channels.testing import WebsocketCommunicator
from config.asgi import application
from core.rooms import create_room


async def main():
    code = create_room()

    ws = WebsocketCommunicator(
        application,
        f"/ws/court/{code}/"
    )

    connected, _ = await ws.connect()
    print("WebSocket connected:", connected)

    if not connected:
        print("FAIL: connection rejected")
        return

    try:
        state = await ws.receive_json_from(timeout=5)
        print("Initial message:", state.get("type"))

        await ws.send_json_to({
            "type": "join",
            "name": "Tester",
            "role": "plaintiff"
        })

        joined = await ws.receive_json_from(timeout=5)
        print("Join response:", joined.get("type"))

        updated = await ws.receive_json_from(timeout=5)
        print("Room update:", updated.get("type"))

        if (
            state.get("type") == "state"
            and joined.get("type") == "joined"
            and updated.get("type") == "state"
        ):
            print("PASS: WebSocket works locally")
        else:
            print("CHECK: unexpected response; inspect output")

    finally:
        await ws.disconnect()


asyncio.run(main())
