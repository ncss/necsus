"""
Some example bots to play with.
- Debug bot (/debugbot) will just pretty-print whatever JSON the server sent it back into the chatroom.
- Botty Botsen (/botty) uses the conversation API.
"""

import html
import pprint

from flask import Flask, request

app = Flask(__name__)


@app.route('/debugbot', methods=['POST'])
def index():
  pretty = pprint.pformat(request.json, indent=2)
  return {
    'author': 'Debug bot',
    'text': f'<pre>{html.escape(pretty)}</pre>',
  }


BOTTY = 'Botty Botsen'


@app.route('/botty', methods=['POST'])
def bot():
  data = request.get_json()
  pprint.pprint(data)
  text = data['text']

  if 'stop' in text.lower():
    if 'null' in text.lower():
      return {
        'text': 'I am stopping the conversation by returning null in the state',
        'state': None,
        'author': BOTTY,
      }
    elif 'empty string' in text.lower():
      return {
        'text': 'I am trying to break stuff by returning the empty string as a state',
        'state': '',
        'author': BOTTY,
      }
    else:
      return {
        'text': 'I am stopping the conversation by not returning a state',
        'author': BOTTY,
      }

  messages = data.get('state', [])
  messages.append(text)

  return {
    'text': 'I am continuing the conversation. Here is a list of your previous messages: ' + ', '.join(messages),
    'author': 'Botty Botsen',
    'state': messages,
  }


if __name__ == '__main__':
  app.run(port=1234, debug=True)
