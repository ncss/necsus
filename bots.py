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
      message = reply.json()
      if 'room' not in message:
        message['room'] = room
      return message
    else:
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. There was a {reply.status_code} error',
      }
