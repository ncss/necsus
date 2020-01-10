import requests

from necsus import db

def run(room, bot, text, params, user=None, state=None):
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

    reply = requests.post(endpoint_url, json=data)

    if reply.status_code == requests.codes.ok:
      safe_message = {}

      try:
        message = reply.json()
      except ValueError:
        raw = reply.text
        # still allow the bot to return an empty response to signify no message
        # was intended to be sent.
        if raw:
          return {
            'room': room,
            'author': 'necsus',
            'text': f'The bot returned invalid json. The response was:<br><pre>{raw}</pre>',
          }

      if isinstance(message, dict) and message.get('text'):
        safe_message['text'] = str(message['text'])
      else:
        return None

      if message.get('author'):
        safe_message['author'] = str(message['author'])
      else:
        safe_message['author'] = name

      if message.get('room'):
        safe_message['room'] = str(message['room'])
      else:
        safe_message['room'] = room

      if message.get('state') is not None:
        safe_message['state'] = message['state']
        safe_message['reply_to'] = bot.get('id')

      if message.get('image'):
        safe_message['image'] = str(message['image'])

      if message.get('media'):
        safe_message['media'] = str(message['media'])

      return safe_message

    else:
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. There was a {reply.status_code} error',
      }
