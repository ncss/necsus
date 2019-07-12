from neccsus import db
import commands
import interactivity

def trigger_command(message, command, text, endpoint=None, user=None):
  if message.get('reponse_type') == 'in_channel':
    command_result = db.messages.add(**message)

  reply_message = commands.run(command, text, endpoint, user)
  reply_message_result = db.messages.add(**reply_message)

  return reply_message

def trigger_message_post(message):
  message_result = db.messages.add(**message)
  return message_result

def trigger_interaction(interaction):
  reply_message = interactivity.interact(interaction)
  reply_message_result = db.messages.add(**reply_message)
  return reply_message 
