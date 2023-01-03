import requests

BOT_TIMEOUT = (3.05, 42) # seconds

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

    try:
      reply = requests.post(endpoint_url, json=data, timeout=BOT_TIMEOUT)
    except requests.exceptions.Timeout as e:
      # Annoyingly there isn't a super-nice way of getting the timeout which was
      # broken by the request other than matching based on the exception type and
      # the passed argument.
      timeout = {
          requests.exceptions.ConnectTimeout: BOT_TIMEOUT[0],
          requests.exceptions.ReadTimeout: BOT_TIMEOUT[1],
      }.get(e.__class__, "a few")
      # Return a timeout warning.
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. Bot {name!r} timed out after {timeout} second(s).',
      }


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
        safe_message['state'] = message['state']
        safe_message['reply_to'] = bot.get('id')

      if 'image' in message and isinstance(message['image'], str):
        safe_message['image'] = message['image']

      if 'media' in message and isinstance(message['media'], str):
        safe_message['media'] = message['media']

      return safe_message

    else:
      return {
        'room': room,
        'author': 'necsus',
        'text': f'Something went wrong. Bot {name!r} responded with a {reply.status_code} error',
      }
