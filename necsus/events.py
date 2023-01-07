"""
Events contains the business logic for receiving messages and dispatching them to bots.
"""

import re

import requests


def trigger_message_post(db, broker, room: str, author: str, text: str):
  special_state = db.messages.room_state(room_name=room)
  message = db.messages.add(room=room, author=author, text=text)
  broker.publish_message(room, message)

  if special_state:
    bot_id, state = special_state
    bots = db.bots.find_all(id=bot_id)
    if len(bots) != 1:
      return message

    bot = bots[0]
    trigger_bot(db, broker, room, author, text, bot, {}, state=state)
  else:
    trigger_bots(db, broker, room, author, text)

  return message


def trigger_clear_room_state(db, broker, room: str):
  """Post an emptyish message to a room to clear any state left over from the last
  message. This is meant to be used for debugging and development purposes."""

  if db.messages.room_state(room_name=room):
    message = db.messages.add(
      room=room,
      author='NeCSuS',
      text='The room state has been cleared',
    )
    broker.publish_message(room, message)


def trigger_bots(db, broker, room: str, author: str, text: str):
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
      reply = trigger_bot(db, broker, room, author, text, bot, match.groupdict())
      replies.append(reply)

  return replies

# def trigger_bot(db, message, bot, params, user=None, state=None):
def trigger_bot(db, broker, room: str, author: str, text: str, bot, params, state=None):
  reply = run_bot(room, bot, text, params, user=author, state=state)
  if reply:
    reply_message = db.messages.add(**reply)
    broker.publish_message(room, reply_message)

  return reply_message

def trigger_clear_room_messages(db, broker, room):
  if (msg := db.messages.last(room=room)) is not None:
    db.clears.set_last_cleared_id(room=room, last_cleared_id=msg['id'])
    db.messages.delete(room=room)
    broker.clear_room(room)

  return room


BOT_TIMEOUT = (3.05, 42) # seconds

def run_bot(room, bot, text, params, user=None, state=None):
  name = bot.get('name', 'bot')
  endpoint_url = bot.get('url')

  if endpoint_url:
    data = {
      'room': room,
      'author': user,
      'text': text,
      'params': params,
    }

    if state != None:
      data['state'] = state

    try:
      reply = requests.post(endpoint_url, json=data, timeout=BOT_TIMEOUT)
    except requests.exceptions.Timeout as e:
      # Annoyingly there isn't a super-nice way of getting the timeout which was
      # broken by the request other than matching based on the exception type and
      # the passed argument.
      timeout = {
          requests.exceptions.ConnectTimeout: BOT_TIMEOUT[0],
          requests.exceptions.ReadTimeout: BOT_TIMEOUT[1],
      }.get(e.__class__, "a few")
      # Return a timeout warning.
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. Bot {name!r} timed out after {timeout} second(s).',
      }


    if reply.status_code == requests.codes.ok:
      safe_message = {}

      message = reply.json()
      if isinstance(message, dict) and 'text' in message and isinstance(message['text'], str):
        safe_message['text'] = message['text']
      else:
        return None

      if 'author' in message and isinstance(message['author'], str):
        safe_message['author'] = message['author']
      else:
        safe_message['author'] = name

      if 'room' in message and isinstance(message['room'], str):
        safe_message['room'] = message['room']
      else:
        safe_message['room'] = room

      if 'state' in message and message['state'] != None:
        safe_message['state'] = message['state']
        safe_message['reply_to'] = bot.get('id')

      if 'image' in message and isinstance(message['image'], str):
        safe_message['image'] = message['image']

      if 'media' in message and isinstance(message['media'], str):
        safe_message['media'] = message['media']

      return safe_message

    else:
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. Bot {name!r} responded with a {reply.status_code} error',
      }
