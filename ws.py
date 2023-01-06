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

  def _notify_room(self, room: str, msg):
    """Post a message into all queues associated with a room."""
    for queue in self.queues_by_room.get(room, set()):
      queue.put_nowait(msg)

  def publish_message(self, room: str, message):
    """Notify of a new message."""
    self._notify_room(room, {'kind': 'message', 'data': message})

  def clear_room(self, room: str):
    """Clear all messages in a room"""
    self._notify_room(room, {'kind': 'clear_messages', 'data': {}})

  def put_bot(self, room: str, bot):
    """Notify of a bot created or updated."""
    self._notify_room(room, {'kind': 'put_bot', 'data': bot})

  def delete_bot(self, room: str, bot):
    """Notify of a bot deletion."""
    self._notify_room(room, {'kind': 'delete_bot', 'data': bot})

  async def subscribe(self, room: str, init_messages: list, init_bots: list, should_clear: bool) -> AsyncGenerator:
    """Subscribe to all actions associated to a particular room."""
    queue = asyncio.Queue()
    self.queues_by_room[room].add(queue)

    if should_clear:
      queue.put_nowait({'kind': 'clear_messages', 'data': {}})

    for bot in init_bots:
      queue.put_nowait({'kind': 'put_bot', 'data': bot})

    for message in init_messages:
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
  Subscribe to a stream of events from a particular room at /ws/<room>?since=42.
  Upon connecting, all current bots will be streamed in, all messages with IDs strictly larger than the since id will
  be streamed in, and then further messages and updates to bots will trickle in.
  """

  await websocket.accept()

  # Parse since_id to an integer no matter what.
  since_id = -1
  try:
    since_id = int(websocket.args.get('since', since_id))
  except:
    pass

  db = get_db()
  last_cleared_entry = db.clears.find(room=room)
  last_cleared_id = last_cleared_entry['last_cleared_id'] if last_cleared_entry is not None else None

  should_clear = False
  if last_cleared_id is not None and last_cleared_id >= since_id:
    should_clear = True
    since_id = last_cleared_id

  current_bots = list(db.bots.find_all(room=room))
  new_messages = list(db.messages.new(since_id, room=room))
  subscription = broker.subscribe(
    room=room,
    init_bots=current_bots,
    init_messages=new_messages,
    should_clear=should_clear,
  )

  async for message in subscription:
    await websocket.send(json.dumps(message))
