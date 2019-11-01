import requests

from necsus import db

def interact(params):
  endpoint_url = db.bots.find(endpoint='interactivity')
  reply = requests.post(endpoint_url, params=params)

  if reply.status_code == requests.codes.ok:
    return reply.json() 
  else:
    return {
      'author': 'necsus',
      'text': f'Something went wrong. There was a {reply.status_code} error',
    }
