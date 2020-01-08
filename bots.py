import requests
import json

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
      data['state'] = json.loads(state)

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

      if 'state' in message and message['state'] != None:
        safe_message['state'] = json.dumps(message['state'])
        safe_message['reply_to'] = bot.get('id')

      return safe_message

    else:
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. There was a {reply.status_code} error',
      }
