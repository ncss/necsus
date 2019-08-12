import requests

from neccsus import db

def run(bot, text, user=None):
  name = bot.get('name', 'bot')
  endpoint_url = bot.get('url') 

  if endpoint_url:
    params = {
      'author': user,
      'command': name,
      'text': text,
    }
    reply = requests.post(endpoint_url, params=params)

    if reply.status_code == requests.codes.ok:
      return reply.json()
    else:
      return {
        'author': 'neccsus',
        'text': f'Something went wrong. There was a {reply.status_code} error',
      }
  else:
    return {
      'author': 'neccsus',
      'text': f'I don\'t understand the "{name}" command.',
    }
