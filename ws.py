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

from necsus import app, get_db

class Broker:
  queues_by_room: defaultdict[str, set[asyncio.Queue]]

  def __init__(self):
    self.queues_by_room = defaultdict(set)

  def publish_message(self, room: str, message):
    msg = {'kind': 'message', 'data': message}
    for queue in self.queues_by_room.get(room, set()):
      queue.put_nowait(msg)

  async def subscribe(self, room: str, init_messages=None) -> AsyncGenerator:
    queue = asyncio.Queue()
    self.queues_by_room[room].add(queue)

    for message in (init_messages or []):
      queue.put_nowait({'kind': 'message', 'data': message})

    try:
      while True:
        msg = await queue.get()
        yield msg
    finally:
      self.queues_by_room[room].remove(queue)


broker = Broker()

@app.websocket('/ws/<room>')
async def ws(room: str):
  """
  Subscribe to a stream of events from a particular room at /ws/<room>?since=msg_id.
  Upon connecting, all messages since the given since_id will be streamed in, and then the connection will remain open
  and stream further messages.
  """

  await websocket.accept()

  # For some reason the <room> capture in @Quart.websocket doesn't drop the query params.
  # if '?' in room:
  #   room, = room.split('?', 1)

  # Parse since_id to an integer no matter what.
  since_id = -1
  try:
    since_id = int(websocket.args.get('since', since_id))
  except:
    pass

  db = await get_db()
  new_messages = list(db.messages.new(since_id, room=room))

  async for message in broker.subscribe(room, init_messages=new_messages):
    await websocket.send(json.dumps(message))
