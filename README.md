# NeCSuS

[NeCSuS](https://chat.ncss.cloud) is a chat application which makes it simple to write and connect to simple "bots" (simple HTTP servers that reply to messages).

<!-- TOC -->
* [NeCSuS](#necsus)
* [NeCSuS Guide](#necsus-guide)
  * [Creating and installing a bot](#creating-and-installing-a-bot)
  * [Using "Responds to" and capture groups](#using-responds-to-and-capture-groups)
  * [Returning rich replies](#returning-rich-replies)
  * [Stateful conversations](#stateful-conversations)
  * [NeCSuS and forms](#necsus-and-forms)
    * [Alternative endpoints](#alternative-endpoints)
* [NeCSuS development and deployment](#necsus-development-and-deployment)
  * [Installation and usage](#installation-and-usage)
    * [Reverse proxies](#reverse-proxies)
    * [Backups](#backups)
  * [Example bots server](#example-bots-server)
  * [Server overview](#server-overview)
  * [Configuration](#configuration)
  * [Frontend overview](#frontend-overview)
* [NeCSuS Reference](#necsus-reference)
  * [Chat rooms](#chat-rooms)
  * [Bot matching (usual mode of operation)](#bot-matching-usual-mode-of-operation)
  * [Stateful conversations](#stateful-conversations-1)
  * [Forms and buttons](#forms-and-buttons)
  * [`Message` schema](#message-schema)
  * [`Bot` schema](#bot-schema)
  * [Websocket stream](#websocket-stream)
<!-- TOC -->


# NeCSuS Guide

**Note**: This guide is incomplete so far, start with the [Simple guide to NeCSuS](https://docs.google.com/document/d/1oc9wd0pRq0u19OOFDLk5njxTkp3etfgGf6mmATac6Qc/edit).


## Creating and installing a bot

To create a bot, start with a simple Flask server hosted somewhere like replit.
An example bot is below, copy-paste that to begin with, and we'll dig into how it works.

```python
import pprint

from flask import Flask, request

app = Flask(__name__)

@app.get('/')
def index():
    """Not used by the bot, but handy to check that your HTTP server is up and going."""
    return 'Hello, world! The server is running.'

@app.post('/echo')
def echo_bot():
    # Print out the message so we can see it.
    message = request.json
    print(f"\nIncoming message to {request.path}:")
    pprint.pprint(message, indent=2)

    message_text = message['text']
    return {
        'author': 'EchoBot',
        'text': f"Hello! Your message was: {message_text}"
    }

app.run(host='0.0.0.0', debug=True)
```

Once this is in `main.py` in Replit, it should start running, and you will see the "Hello world! The server is running." message.
Click the "New tab" button on that message, which will give you the external address of that Replit.
For me, the external address is <https://echobot.joelgibson1.repl.co/>.

Next we will create a room, add this bot to the room, send it a message and (hopefully) get a message back.

- Open up <https://chat.ncss.cloud/> and create a new chat room, using the room name `group{n}-{name}`, for instance `group2-joel`.
- Open the settings, and scroll down to "Add a bot...".
- Give it the name "EchoBot", with the endpoint URL `<replit>/echo`, for instance mine is `<https://echobot.joelgibson1.repl.co/echo>`.
- Send it a message: say "Hi EchoBot".

You should receive a reply from your bot.
There should also see some debugging output show up in your Replit's console:

```
Incoming message to /echo:
{'author': 'Joel', 'params': {}, 'room': 'group2-joel', 'text': 'Hello echobot'}
172.31.196.1 - - [31/Dec/2023 03:28:31] "POST /echo HTTP/1.1" 200 -
```

Keep this debugging output around: it will be very handy.


## Using "Responds to" and capture groups

To make a smarter virtual assistant, it might want to respond to more than just its name.
In the NeCSuS chat room there is a "Responds to" field on your bot, which will switch it away from listening for its name, into listening for a regular expression pattern.

The pattern can have *named capturing groups*, which will be returned to your bot.
Let's say we want to write a bot which repeats a word a number of times, for instance this interaction:

```
Me:  "Please repeat hello 5 times."
Bot: "hello hello hello hello hello"
```

First we write a regular expression pattern for the "Responds to" field which matches this pattern and gives names to the captured parts:

```
repeat (?P<word>\w+) (?P<count>\d+) times`
```

After putting this pattern in the "Responds to" field, and sending the message ..., your bot will show that it has received the object:

```
{
    'author': 'Joel',
    'params': {'count': '5', 'word': 'hello'},
    'room': 'group2-joel',
    'text': 'Please repeat hello 5 times.'
}
```

You can then get this data out of the `params` key and start using it.


## Returning rich replies

Your bot doesn't just need to return text, in fact it can return images, multimedia, and anything supported by HTML.
Firstly, we have some shortcuts in NeCSuS just for images and multimedia objects.
To show a single image, return an `image` key along with your message:

```
{"text": "A cute dog!", "image": "https://images.dog.ceo/breeds/terrier-norfolk/n02094114_1505.jpg"}
```

To embed a sound or view, use the `media` key:

```
{"text": "Ring!", "media": "https://upload.wikimedia.org/wikipedia/commons/transcoded/d/de/Back_Rounds.ogg/Back_Rounds.ogg.mp3"}
```

The richest sort of reply is HTML.
All of the usual HTML for formatting, links, images, Spotify embeds, and so on, will work in the NeCSuS chat room.
For example, if you just want to use a little formatting your bot can reply with

```
{"text": "Lasagna <i>is</i> a <b>sandwich</b>!"}
```

Since HTML treats some characters like `<` specially, this means that if you want to return an actual `<` symbol, you will need to _escape it_, which means to substitute it by its [character reference](https://en.wikipedia.org/wiki/Character_encodings_in_HTML#HTML_character_references) `&lt;`.
For example: `{"text": "1 &lt; 2"}` would produce `1 < 2`.
This can be annoying to do by hand, so you can also `import html` from the Python standard library, and use `html.escape(...)`.


## Stateful conversations

You may have noticed that it is easy with necsus to facilitate an interaction like

```
> I saw a cat behind the college
Catbot: I've recorded the sighting of the cat behind the college
```

and quite difficult to facilitate one like

```
> I saw a cat!
Catbot: Where did you see the cat?
> Behind the college
Catbot: I've recorded the sighting of the cat behind the college
```

because you will somehow need a regular expression to dispatch on `Behind the college`. Furthermore, in a longer conversation you may have to query the user multiple times to learn a lot of information before performing an action, and so your conversation needs to have some `state` associated with it.

By returning some extra state from your bot, you will switch NeCSuS into a mode where it only talks to that one bot, and forwards all messages to that one bot. So by returning

```JSON
{
  "text": "Where did you see the cat?",
  "state": ["any", "non", "null", {"json": "object"}]
}
```

all further messages will be forwarded to the bot which returned that state, and no other bot. The state will also be returned: the next message that bot might see will be

```JSON
{
    "room": "catspot",
    "author": "Joel",
    "text": "Behind the college",
    "params": {},
    "state": ["any", "non", "null", {"json": "object"}]
}
```

in other words, the same state it previously sent gets handed back. At this point the bot can choose to not return `state` (or return a `null` json object for state), in which case necsus switches back to normal mode. Otherwise, the stateful conversation continues.

## NeCSuS and forms

The NeCSuS client has special support for HTML forms.
Whenever a bot returns some HTML containing a `<form>` element, a special Javascript handler is attached to the form, which will redirect the submit action of the form back to the  NeCSuS server.
The NeCSuS server then makes a POST request back to the bot responsible to the original form, with an object containing the `form_data` key, and the bot may return a message as usual.

For example, let's suppose that the "desserts" bot at the endpoint `https://example.com/bots/desserts` has returned the following HTML, as part of its `text` field in a previous interaction:
```html
<form>
    <button name="dessert" value="apple-crumble">Apple crumble</button>
    <button name="dessert" value="ice-cream">Ice cream</button>
    <button name="dessert" value="affogato">Affogato</button>
</form>
```
When the user clicks on the "Apple crumble" button, the same bot endpoint `https://example.com/bots/desserts` will recieve a POST request with the following data:
```JSON
{
    "room": "some-room-name",
    "form_data": {
        "dessert": "apple-crumble"
    }
}
```
Note that this object is a *different* shape to a regular message to a bot, which would have the `text` field for example.
The bot can then return a JSON object as usual, and say something like "I see that Apple Crumble is your favourite."


### Alternative endpoints

The `method=` on a `<form>` is ignored (the system will always make a POST request to the bot, no matter what), but the `action=` attribute can be used to change which endpoint the form data gets posted to.
The action is considered relative to the bot endpoint, so for example if the bot endpoint is `https://example.com/bots/desserts`, then:

- `<form>` or `<form action="">` will POST to `https://example.com/bots/desserts`,
- `<form action="foo">` will POST to `https://example.com/bots/foo`
- `<form action="/foo">` will POST to `https://example.com/foo`
- `<form action="https://some.other.domain/baz">` will POST to `https://some.other.domain/baz`


# NeCSuS development and deployment

Read this section if you want to run or develop the NeCSuS server, not just use it.

## Installation and usage

To get going, install the [Poetry](https://python-poetry.org/) package manager (I recommend installing it using [pipx](https://pipx.pypa.io/stable/), if you already use that).
Then select a Python version (I've been testing on Python 3.10), install the packages, run the tests, and launch the server.

```shell
$ poetry env use python3.10
$ poetry install
$ poetry run pytest
$ poetry run python -m necsus
```

Once the server is started, go to <http://localhost:6277/>.
The server will also make a local Sqlite3 database called `necsus.db`.


### Reverse proxies

The command line above is suitable for production use (at least as far as NCSS goes), but only  binds to `http://localhost:6277` so is not accessible from outside the local machine.
It is intended to be run behind a reverse proxy server which will terminate HTTPS and be exposed to the internet.
In 2023 we used [Caddy](https://caddyserver.com/docs/) which worked very well -- there is an example [`Caddyfile`](./Caddyfile) in the repository.
If you have Caddy installed, then you can try out this reverse proxy, which will bind to all addresses on port `8000` by default.
Go to `<http://localhost:8000>` to see if it worked (and try accessing it from a different machine on the same network).

```shell
$ caddy run --config Caddyfile
```

Note that in a production installation, Caddy/Nginx/whatever would usually be managed elsewhere, since it might be terminating many domain names into different reverse proxies.


### Backups

There is a backup script for taking a timestamped snapshot of the NeCSuS database, and saving it to a gzipped file.
The backup script is one-shot, so it should be run in a loop:

```shell
$ cd backups

$ ./backup-necsus.sh  # One shot
Backed up to 2023-12-31T15:03:57.db.gz

$ while true; do sleep 15m; ./backup-necsus.sh; done  # Run me in a tmux or something lol
```


## Example bots server

There are also some example bots, used for both automated and manual testing.
These which start up at <http://localhost:1234> after running

```shell
$ poetry run python -m example_bots
```


## Server overview

The NeCSuS server is a web server written in async Python, which writes to a local Sqlite3 database, and communicates with user-written bots on the internet using standard HTTP requests.
It is designed to be run single-threaded in a single process, with async enabling it to service many requests concurrently while coping with user-written bots which may be very slow to respond.

The packages we use in NeCSuS are (in roughly the order they would be encountered during an HTTP request):

- [Uvicorn](https://www.uvicorn.org/) is an ASGI web server, an async analogue of Gunicorn. This terminates HTTP and turns it into ASGI calls into the web application.
- [Starlette](https://www.starlette.io/) is an ASGI web framework (think Flask, but async). It is used for routing URLs, request handling, and websocket connections.
- [Httpx](https://www.python-httpx.org/) is like an async-enabled `requests`. It is used to make HTTP requests to user-written bots.
- [Sqlite3](https://docs.python.org/3/library/sqlite3.html) (standard library) is used for the database, with [pypika](https://pypika.readthedocs.io/en/latest/) as a query builder.
- [AnyIO](https://anyio.readthedocs.io/en/stable/) is used for async coordination, queues between coroutines etc.

There are also several other packages which are not used in the main server process:

- [Flask](https://flask.palletsprojects.com/) is used for the example bot server. We could have used another Starlette, but the students will be writing their servers in Flask so why not.
- [pytest](https://docs.pytest.org/en/7.4.x/) is used for testing. During testing, we also use a library called [respx](https://lundberg.github.io/respx/) to mock `httpx` calls from the NeCSuS server into the example bot server.


## Configuration

Mostly if you need to configure NeCSuS, just hack on the source code.

There is one environment variable, `NECSUS_DB`, which configures the location of the database.
We use this for testing, setting `NECSUS_DB=:memory:` for isolated tests.


## Frontend overview

The NeCSuS frontend is a [Vue.js](https://vuejs.org/) application sitting in [`client/`](./client/).
It makes HTTP requests (GET/POST/DELETE) to the server in order to post new messages, add and remove bots, and take other actions like clearing the messages in a room.
Each HTTP request comes back with a sensible reply, but this is mostly ignored by the frontend --- instead the frontend mostly updates itself via a websocket stream.
Every client gets the exact same stream of events via the websocket (one stream per room), which makes it simple to keep different clients in sync.

In addition to the usual frontend, there is also a [Swagger UI](https://swagger.io/tools/swagger-ui/) hosted at `/docs`.
This is just a static webapp, which reads the hand-written [`api.yaml`](./api.yaml) file, which is hosted at `/api/spec`.


# NeCSuS Reference

In this reference we try to describe the actual semantics of how the NeCSuS server matches, activates, and communicates with bots.
If you are starting out, you should read the [Guide](#necsus-guide) first.


## Chat rooms

Chat rooms are identified by nonempty case-sensitive strings (we decided to [keep them case-sensitive](https://github.com/ncss/necsus/issues/76)).
They are implicit in the database, so they really only "exist" if they either have messages or bots in them.


## Bot matching (usual mode of operation)

Each bot has a name, a URL, and an optional regular expression pattern.
Upon receiving a new chat message, the NeCSuS server will first save the message and broadcast that message to all clients.
Then, it will check if any bots should be activated by the message:

- If the bot has no regular expression pattern, it is just activated by its name (in a case-insensitive way).
- If the bot has a regular expression `pattern`, it is activated if `re.search(pattern, text, flags=re.IGNORECASE)` matches the message `text`.

The NeCSuS server will make an HTTP POST request to each matching bot (in order of bot id, waiting for each bot to complete before it makes a request to the next).
The incoming JSON payload to the bot has the following schema:

```
type BotActivationViaMatch = {
    room: str      # Room the message is from.
    author: str    # Name of the user who wrote the message.
    text: str      # Text of the message.
    params: {...}  # Named regular expression capture groups.
}
```

If the bot was activated via a regular expression which has [named capture groups](https://docs.python.org/3/howto/regex.html#non-capturing-and-named-groups), then these names and their matching substrings will be unpacked into the `params` dict.
Otherwise, this dict will be empty.

The bot can do whatever it likes while handling the post request, then needs to return another JSON payload which is expected to have the following schema:

```
type BotResponse = {
    text: str      # Response text/html, always required (even if empty).
    author?: str   # Optional name, defaults to name of bot record in the room.
    image?: str    # Optional image URL
    media?: str    # Optional media URL.
    state?: JSON   # Optional state for a stateful conversation.
    room?: str     # Joel: Should this be allowed?
}
```

Note that only the `text` field is required, all other fields may be omitted.
Furthermore, `text` can in fact be any HTML --- the frontend will make sure that this HTML gets properly injected into the chat room.

As each bot completes its HTTP request, the message returned by the bot is posted to the room.
The NeCSuS server will not allow a bot to be activated by another bot's message (to prevent some infinite loop footguns).


## Stateful conversations

A bot may return a non-null `state` field in its JSON message back to the server (see the `BotResponse` schema above).
The server will store this state, and the next message in the room will be forwarded directly to the bot that left the `state` field (and only to that bot, unconditionally).
This is called the _stateful conversation_ mode.

The incoming JSON payload to the bot during a stateful conversation has the schema:

```
type BotActivationViaState = {
    room: str
    author: str
    text: str
    state: JSON  # The last piece of state the bot sent.
```

The bot can gracefully exit this mode by returning a `BotResponse` with either no `state` key at all, or a `None` value for the `state` key.
The frontend will also add a "Leave conversation with <bot>" button when in a stateful conversation, so that it can be exited forcibly during development.


## Forms and buttons

If a bot returns some HTML with a `<form>` element, then the frontend will transform the submit action on this form into a `POST` request back to the bot, with the form data attached as JSON.
This is called a _form activation_ of a bot.
The bot will receive a POST request with a JSON payload of the following schema:

```
type BotActivationViaForm = {
    room: str
    author: str
    form_data: JSON
}
```

Note that the `text` field is missing from this schema!

This can be used to activate a _different_ bot when a button is pressed.


## `Message` schema

A `Message` record is the server's format for a fully-processed message which should appear in the chat stream for a room.
It has the following schema:

```
type Message = {
    id: int               # Server-internal message ID from the server, monotonically increasing.
    room: str             # Room name
    author: str           # Name of user (or bot) who sent the message 
    kind: str             # "user", "bot", "system".
    text: str             # Message text or HTML.
    when: float           # Seconds since the UTC Epoch 1970-01-01.
    image: str | None     # ???
    media: str | None     # ???
    from_bot: int | None  # A bot ID if this message is from a bot, otherwise None.
    state: JSON | None    # None in normal operation, any non-null JSON object in a stateful conversation.
}
```

There are a few fields to point out here:

- The `id` field monotonically increases, and should be used to order messages in a room. It is also used for when a client needs to play catch-up for whatever reason (a disconnect from the server, for example): the client may send the last message `id` it saw, and the server will only send back messages which are new since then.
- The `kind` field indicates whether a message was from the user, a bot, or the NeCSuS system. This should be used to visually distinguish messages: the `system` messages are usually errors.
- The `state` field is covered below in <<INSERT LINK TO STATEFUL CONVERSATIONS HERE>>.


## `Bot` schema

A `Bot` record is the server's format for the name, activation text, and URL of a bot which lives in a room.
It has the following schema:

```
type Bot = {
    id: int           # Server-internal bot ID.
    room: str         # Room this bot record belongs to.
    name: str         # Name of the bot.
    responds_to: str  # Regular expression.
    url: str          # URL of the bot.
}
```


## Websocket stream

The websocket stream is designed to make it dead-simple to write the NeCSuS frontend and have it manage as little state as possible: all updates (messages, bot updates, clear-room, etc) are delivered straight from the server via the websocket.
To connect, open a websocket to `/ws/{room}`, optionally passing the query parameter `?since={last_id}` where `last_id` is the last message ID you saw (for instance if you are re-connecting after a disconnect).
The websocket will receive the following kinds of updates, each as a single websocket message:

- `{kind: "clear_messages", data: {}}`: Clear the message list completely.
- `{kind: "message", data: {...}}`: Append a message to the list. The `data` property is a `Message`.
- `{kind: "put_bot", data: {...}}`: A bot has been created or updated. The `data` property is a `Bot`, and the `id` should be user for the upsert.
- `{kind: "delete_bot", data: {...}}`: A bot has been deleted. The `data` property is a `Bot`, and the `id` should be used for the delete.
