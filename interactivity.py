import requests

from neccsus import db

def interact(params):
  endpoint_url = db.endpoints.find(endpoint='interactivity')
  reply = requests.post(endpoint_url, params=params)

  if reply.status_code == requests.codes.ok:
    return reply.json() 
  else:
    return {
      'author': 'neccsus',
      'text': f'Something went wrong. There was a {reply.status_code} error',
    }
