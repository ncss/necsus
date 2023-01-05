"""
Events contains the business logic for receiving messages and dispatching them to bots.
"""

import re

import bots
from ws import broker


def trigger_message_post(db, room: str, author: str, text: str):
  special_state = db.messages.room_state(room_name=room)
  message = db.messages.add(room=room, author=author, text=text)
  broker.publish_message(room, message)

  if special_state:
    bot_id, state = special_state
    bots = db.bots.find_all(id=bot_id)
    if len(bots) != 1:
      return message

    bot = bots[0]
    trigger_bot(db, room, author, text, bot, {}, state=state)
  else:
    trigger_bots(db, room, author, text)

  return message


def trigger_clear_room_state(db, room: str):
  """Post an emptyish message to a room to clear any state left over from the last
  message. This is meant to be used for debugging and development purposes."""

  if db.messages.room_state(room_name=room):
    message = db.messages.add(
      room=room,
      author='NeCSuS',
      text='The room state has been cleared',
    )
    broker.publish_message(room, message)


def trigger_bots(db, room: str, author: str, text: str):
  room_bots = db.bots.find_all(room=room)

  replies = []

  for bot in room_bots:
    search =  bot.get('responds_to') or bot.get('name')
    try:
      match = re.search(search, text, flags=re.IGNORECASE)
    except:
      name = bot.get('name')
      t = 'responds_to' if bot.get('responds_to') else 'name'
      message = db.messages.add(
        room=room,
        author='necsus',
        text=f'Something went wrong. Bot {name!r} has an invalid {t} regex: <pre>{search}</pre>'
      )
      broker.publish_message(room, message)

      continue

    if search and match:
      reply = trigger_bot(db, room, author, text, bot, match.groupdict())
      replies.append(reply)

  return replies

# def trigger_bot(db, message, bot, params, user=None, state=None):
def trigger_bot(db, room: str, author: str, text: str, bot, params, state=None):
  reply = bots.run(room, bot, text, params, user=author, state=state)
  if reply:
    reply_message = db.messages.add(**reply)
    broker.publish_message(room, reply_message)

  return reply_message

def trigger_clear_room_messages(db, room):
  if (msg := db.messages.last(room=room)) is not None:
    db.clears.set_last_cleared_id(room=room, last_cleared_id=msg['id'])
    db.messages.delete(room=room)
    broker.clear_room(room)

  return room
