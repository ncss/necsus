"""
Test bots is a Flask server containing examples of simple bots.
These are also used to run automated tests on the NeCSuS server.

The bots below are in ascending order of complexity (ish).
"""

import html
import pprint
import re
import time

from flask import Flask, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Required to load resource-linked Javascript from /static or any other handler.


@app.post('/hellobot')
def hellobot():
    """HelloBot responds with 'Hello, world!'"""

    return {'author': 'HelloBot', 'text': 'Hello, world!'}


@app.post('/echobot')
def echobot():
    """EchoBot responds with the original message text."""

    data = request.json
    return {'author': 'EchoBot', 'text': data['text']}


@app.post('/debugbot')
def debugbot():
    """
    DebugBot responds with a <pre>-formatted, pretty-printed copy of the complete JSON it was sent to the bot.
    It also includes a button so that the different JSON for a form activation can be seen.
    """

    pretty = pprint.pformat(request.json, indent=2)
    return {
        'author': 'DebugBot',
        'text': f'''
            <pre>{html.escape(pretty)}</pre>
            <p>Here's a button if you want to check that too: <form><button name="some-name" value="some-value">Click me!</button></form></p>
            <p>The button should trigger me again.</p>
        ''',
    }


@app.post('/imagebot')
def animal():
    """ImageBot responds with a picture of a 'randomly' chosen animal in the special 'image' field."""
    return {
        'author': 'ImageBot',
        'text': 'Here is a capybara.',
        'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Hydrochoeris_hydrochaeris_in_Brazil_in_Petr%C3%B3polis%2C_Rio_de_Janeiro%2C_Brazil_09.jpg/800px-Hydrochoeris_hydrochaeris_in_Brazil_in_Petr%C3%B3polis%2C_Rio_de_Janeiro%2C_Brazil_09.jpg',
    }


@app.post('/mediabot')
def media():
    """MediaBot responds with an audio file."""
    return {
        'author': 'MediaBot',
        'text': 'Here is some media.',
        'media': 'https://upload.wikimedia.org/wikipedia/commons/transcoded/d/de/Back_Rounds.ogg/Back_Rounds.ogg.mp3',
    }


@app.post('/statebot')
def statebot():
    """
    StateBot is an example of how state can be used. Once activated, it will respond with the conversation so far (in
    bullet-point form), and ask for another line. It can be stopped by writing 'stop' somewhere in the line, which will
    cause the state to be removed.
    - 'stop' by itself will return a JSON object with a missing 'state' key, which should end the conversation.
    - 'stop null' will return a JSON object with {state: null}, which should end the conversation.
    - 'stop empty string' will return a JSON object with {state: ''}, which should *not* end the conversation.
    """
    name = 'StateBot'

    data = request.json
    text = data['text']
    conversation = [*data.get('state', []), text]

    html_lines = [
        f'<p>I am the {name}. Here is your conversation so far:</p>',
        '<ol>',
        *[f'<li>{line}</li>' for line in conversation],
        '</ol>',
    ]
    response = {'author': name, 'state': conversation}

    if 'stop' in text.lower() and 'null' in text.lower():
        html_lines += ['<p>I am stopping the conversation by returning <code>null</code> in the state</p>']
        response['state'] = None
    elif 'stop' in text.lower() and 'empty string' in text.lower():
        html_lines += ['<p>I am trying to break stuff by returning the empty string as a state</p>']
        response['state'] = ''
    elif 'stop' in text.lower():
        html_lines += ['<p>I am stopping the conversation by not returning a <code>state</code> key in the JSON object.</p>']
        del response['state']
    else:
        html_lines += ['<p>Please enter another line, or say "stop", "stop null", or "stop empty string" (or any line with those words in them).<p>']

    response['text'] = '\n'.join(html_lines)
    return response


@app.post('/sleepbot')
def sleepbot():
    """
    Slow route for testing a bot taking a long time to respond.
    Takes the first whole number found in the prompt and sleeps for that many seconds, otherwise sleeps for 10.
    """
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
        guess = 'lower' if 'lower' in data['text'].lower() else 'higher' if 'higher' in data[
            'text'].lower() else 'correct'

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


@app.post('/buttonbot')
def buttonbot():
    """ButtonBot is an example of how to use resource-linked CSS and Javascript."""
    return {
        'author': 'ButtonBot',
        'text': '''
            <p>Click this button to run good Javascript: <button class="buttonbot" onclick="buttonBotClick()">Click me!</button></p>
            <p>Click this button to throw a JS error: <button class="buttonbot-error" onclick="buttonBotError()">Don't click me!</button></p>
        ''',
        'css': '/static/buttonbot.css',
        'js': '/static/buttonbot.js',
    }
