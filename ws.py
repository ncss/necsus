"""
Websocket endpoint for Necsus: clients may connect to the websocket, specifying a room, and optionally a "since" (as in,
subscribe to the message stream for all messages coming strictly after this id). The server will then notify them of new
messages as they come in.
"""

import asyncio
import json
from typing import AsyncGenerator
from collections import defaultdict

from quart import websocket

from necsus import app

class Broker:
  queues_by_room: defaultdict[str, set[asyncio.Queue]]

  def __init__(self):
    self.queues_by_room = defaultdict(set)

  def publish(self, room: str, message):
    for queue in self.queues_by_room.get(room, set()):
      queue.put_nowait(message)

  async def subscribe(self, room: str) -> AsyncGenerator:
    queue = asyncio.Queue()
    self.queues_by_room[room].add(queue)
    try:
      while True:
        yield await queue.get()
    finally:
      self.queues_by_room[room].remove(queue)


broker = Broker()


@app.websocket('/ws/<room>')
async def ws(room:str):
  await websocket.accept()
  async for message in broker.subscribe(room):
    await websocket.send(json.dumps(message))
