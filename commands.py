import requests

from neccsus import db

def parse(text):
  if text.startswith('/'):
    try:
      command, arg_text = text.split(maxsplit=1)
      return command[1:], arg_text
    except ValueError:
      return text[1:].rstrip(), ''
  else:
    return None

def run(name, text):
  author = db.members.find('kenni')
  endpoint_url = db.endpoints.find(command=name)
  if endpoint_url:
    params = {
      'author': author.get('id'),
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
