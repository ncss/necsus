import bots
import interactivity

import re

def trigger_message_post(db, message):
  special_state = db.messages.room_state(room_name=message['room'])
  message_result = db.messages.add(**message)

  if special_state:
    bot_id, state = special_state
    bots = db.bots.find_all(id=bot_id)
    if len(bots) != 1:
      return message_result

    bot = bots[0]
    trigger_bot(db, message, bot, {}, state=state, user=message.get('author', ''))
  else:
    trigger_bots(db, message)

  return message_result


def trigger_clear_room_state(db, room):
  """Post an emptyish message to a room to clear any state left over from the last
  message. This is meant to be used for debugging and development purposes."""

  if db.messages.room_state(room_name=room):
    clearing_message = {
      'room': room,
      'author': 'NeCSuS',
      'text': 'The room state has been cleared',
    }
    db.messages.add(**clearing_message)


def trigger_bots(db, message):
  text = message.get('text')
  user = message.get('author')
  room = message.get('room', '')
  room_bots = db.bots.find_all(room=room)

  replies = []

  for bot in room_bots:
    search =  bot.get('responds_to') or bot.get('name')
    try:
      match = re.search(search, text, flags=re.IGNORECASE)
    except:
      name = bot.get('name')
      t = 'responds_to' if bot.get('responds_to') else 'name'
      db.messages.add(
        room=room,
        author='necsus',
        text=f'A bot with name {name!r} in this room has this invalid {t} regex: <pre>{search}</pre>'
      )
      continue

    if search and match:
      reply = trigger_bot(db, message, bot, match.groupdict(), user)
      replies.append(reply)

  return replies

def trigger_bot(db, message, bot, params, user=None, state=None):
  text = message.get('text')
  room = message.get('room')
  reply_message = bots.run(room, bot, text, params, user=user, state=state)
  if reply_message:
    reply_message_result = db.messages.add(**reply_message)

  return reply_message

def trigger_interaction(db, interaction):
  reply_message = interactivity.interact(interaction)
  reply_message_result = db.messages.add(**reply_message)
  return reply_message

def trigger_room_reset(db, room):
  db.messages.delete(room=room)
  return room
