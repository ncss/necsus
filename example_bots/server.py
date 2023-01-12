"""
Some example bots to play with.
- Debug bot (/debugbot) will just pretty-print whatever JSON the server sent it back into the chatroom.
- Botty Botsen (/botty) uses the conversation API.
"""

import html
import pprint
import re
import time

from flask import Flask, request

app = Flask(__name__)


@app.route('/debugbot', methods=['POST'])
def index():
  pretty = pprint.pformat(request.json, indent=2)
  return {
    'author': 'Debug bot',
    'text': f'''
      <pre>{html.escape(pretty)}</pre>
      <p>Here's a button if you want to check that too: <form><button name="some-name" value="some-value">Click me!</button></form></p>
    ''',
  }


@app.route('/animal', methods=['POST'])
def animal():
  """Test the image responses."""
  return {
    'author': 'Animal bot',
    'text': 'Here is a capybara',
    'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Capybara_%28Hydrochoerus_hydrochaeris%29.JPG/440px-Capybara_%28Hydrochoerus_hydrochaeris%29.JPG',
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


@app.route('/sleep', methods=['POST'])
def sleep():
  """Slow route for testing a bot taking a long time to respond."""
  if m := re.search(r'\d+', request.json['text']):
    sleep_time = int(m.group())
  else:
    sleep_time = 10

  time.sleep(sleep_time)
  return {
    'author': "SleepBot",
    'text': f"I've slept for {sleep_time} seconds."
  }


@app.route('/form', methods=['POST'])
def form():
  """Example route for forms."""
  return {
    'author': 'FormBot',
    'text': '''
      <p>You have two options:</p>
      <form method="POST" action="/form/handler">
        <button name="mybutton" value="1">Option 1</button>, or
        <button name="mybutton" value="2">Option 2</button>.
      </form>
      ''',
  }

@app.route('/form/handler', methods=['POST'])
def form_handler():
  # Expect an object of the form {room: string, form_data: object}.
  data = request.get_json()
  chosen = data['form_data']['mybutton']
  return {
    'author': 'FormBot',
    'text': f"Option {chosen} is an excellent choice.",
  }


@app.route('/numberwang', methods=['POST'])
def numberwang():
  def form_html(mid):
    return f"""
      <form>
        <p>Is your number
          <button name="guess" value="lower">Lower</button>,
          <button name="guess" value="correct">{mid}</button>, or
          <button name="guess" value="higher">Higher</button>?
      </form>
    """

  data = request.get_json()
  if 'state' not in data:
    lo, hi = 1, 100
    mid = (lo + hi) // 2
    return {
      'author': 'Numberwang',
      'text': f"<p>Pick a number between 1 and 100 and I will guess it! My first guess is {mid}.</p>{form_html(mid)}",
      'state': [lo, hi],
    }

  if 'form_data' in data:
    guess = data['form_data']['guess']
  else:
    guess = 'lower' if 'lower' in data['text'].lower() else 'higher' if 'higher' in data['text'].lower() else 'correct'

  if guess == 'correct':
    return {'author': 'Numberwang', 'text': "Woohoo, I win! Let's rotate the board!"}

  print(data)
  lo, hi = data.get('state', [1, 100])
  mid = (lo + hi) // 2
  if guess == 'lower':
    hi = mid - 1
  else:
    lo = mid + 1

  mid = (lo + hi) // 2
  return {
    'author': 'numberwang',
    'text': form_html(mid),
    'state': [lo, hi],
  }


@app.route('/ping', methods=['POST'])
def ping():
  """
  The ping bot should post a button, and upon clicking that, we should be in a conversation with the pong bot.
  If we do "ping nowhere", then it will try to ping a bot that is not in the room.
  """
  action = '/nowhere' if 'nowhere' in request.json['text'].lower() else '/pong'
  return {
    'author': 'PingBot',
    'text': f'<form action="{action}"><button>Go to {action}</button</form>',
  }

@app.route('/pong', methods=['POST'])
def pong():
  data = request.json

  if 'state' in data:
    return {'author': 'PongBot', 'text': 'Thanks for chatting. This is PongBot signing off.'}

  if 'form_data' not in data:
    return {'author': 'PongBot', 'text': 'Please activate PongBot via the PingBot.'}

  return {'author': 'PongBot', 'text': 'This is PongBot. How are you today?', 'state': 0}



if __name__ == '__main__':
  app.run(port=1234, debug=True)
