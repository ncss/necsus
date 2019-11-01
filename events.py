from necsus import db
import bots 
import interactivity

def trigger_message_post(message):
  message_result = db.messages.add(**message)

  replies = trigger_bots(message)

  return message_result

def trigger_bots(message):
  text = message.get('text')
  user = message.get('author')
  room = message.get('room', '')
  room_bots = db.bots.find_all(room=room)

  replies = []

  for bot in room_bots:
    if bot.get('name').lower() in text.lower():
      reply = trigger_bot(message, bot, user)
      replies.append(reply)

  return replies 

def trigger_bot(message, bot, user=None):
  text = message.get('text')
  room = message.get('room')
  reply_message = bots.run(room, bot, text, user=user)
  reply_message_result = db.messages.add(**reply_message)

  return reply_message

def trigger_interaction(interaction):
  reply_message = interactivity.interact(interaction)
  reply_message_result = db.messages.add(**reply_message)
  return reply_message 
