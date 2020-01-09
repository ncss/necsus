import requests

from necsus import db

def run(room, bot, text, params, user=None):
  name = bot.get('name', 'bot')
  endpoint_url = bot.get('url')

  if endpoint_url:
    data = {
      'room': room,
      'author': user,
      'text': text,
      'params': params,
    }
    reply = requests.post(endpoint_url, json=data)

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

      if 'image' in message and isinstance(message['image'], str):
        safe_message['image'] = message['image']

      if 'media' in message and isinstance(message['media'], str):
        safe_message['media'] = message['media']

      return safe_message

    else:
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. There was a {reply.status_code} error',
      }
