from collections import defaultdict

import anyio.streams.memory


class Broker:
  """
  The Broker is used as a singleton, and facilitates broadcasting to WebSockets. It manages a collection of unbounded
  queues, and each action .publish_message(), .clear_room(), etc will post into those queues.
  """
  queues_by_room: defaultdict[str, set[anyio.streams.memory.MemoryObjectSendStream]]

  def __init__(self):
    self.queues_by_room = defaultdict(set)

  def _notify_room(self, room: str, msg):
    """Post a message into all queues associated with a room."""
    for queue in self.queues_by_room.get(room, set()):
      queue.send_nowait(msg)

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

  def subscribe(self, room: str, init_messages: list, init_bots: list, should_clear: bool):
    """
    Subscribe to all actions associated to a particular room.
    A pair (recv, tag) is returned, where recv is a stream (queue) which messages are fed into,
    and tag is an opaque tag which can then be used to unsubscribe.
    """

    # Joel: It is generally bad practice to use unbounded queues. We didn't see any problems from this in 2023, but
    #       perhaps we should add some monitoring, and log a warning if any queue looks like it's filling up over time.
    send, recv = anyio.create_memory_object_stream(max_buffer_size=float('inf'))
    self.queues_by_room[room].add(send)

    if should_clear:
      send.send_nowait({'kind': 'clear_messages', 'data': {}})

    for bot in init_bots:
      send.send_nowait({'kind': 'put_bot', 'data': bot})

    for message in init_messages:
      send.send_nowait({'kind': 'message', 'data': message})

    return recv, (room, send)

  def unsubscribe(self, tag):
    room, send = tag
    send.close()
    self.queues_by_room[room].remove(send)
