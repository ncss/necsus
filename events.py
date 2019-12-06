import bots 
import interactivity

import re

def trigger_message_post(db, message):
  message_result = db.messages.add(**message)
  replies = trigger_bots(db, message)

  return message_result

def trigger_bots(db, message):
  text = message.get('text')
  user = message.get('author')
  room = message.get('room', '')
  room_bots = db.bots.find_all(room=room)

  replies = []

  for bot in room_bots:
    search =  bot.get('responds_to') or bot.get('name')
    match = re.search(search, text, flags=re.IGNORECASE)
    if search and match:
      reply = trigger_bot(db, message, bot, match.groupdict(), user)
      replies.append(reply)

  return replies 

def trigger_bot(db, message, bot, params, user=None):
  text = message.get('text')
  room = message.get('room')
  reply_message = bots.run(room, bot, text, params, user=user)
  reply_message_result = db.messages.add(**reply_message)

  return reply_message

def trigger_interaction(db, interaction):
  reply_message = interactivity.interact(interaction)
  reply_message_result = db.messages.add(**reply_message)
  return reply_message 
