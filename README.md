# NeCSuS

[NeCSuS](https://chat.ncss.cloud) is a chat app which makes it simple to connect "bots" (i.e., simple HTTP servers that reply to messages).
NeCSuS has the ability to host chats in "rooms", listen to voice commands and speak chat messages out loud.


## API

Documentation on the API can be found on [the main NeCSuS server](https://chat.ncss.cloud/docs) or at `/docs` on your local instance.

## Development

For development in debug mode, run

    python server.py

For deployment, run

    hypercorn --bind localhost:6277 --workers 1 server:app


## FAQ

### What is NeCSuS?
A web app that allows you to create rooms in which you can import and interact with chatbots.

### Is there a simple guide?
Yes, there is a [simple guide to NeCSuS](https://docs.google.com/document/d/1oc9wd0pRq0u19OOFDLk5njxTkp3etfgGf6mmATac6Qc/edit).
You can also look at the [NeCSuS API docs](https://chat.ncss.cloud/docs/) and the [bot API docs](https://chat.ncss.cloud/bot/docs/).

### How do I post (images|links|formatted text)?

You can render a single image by putting an `image` key in your response.

```
{"text": "A cute dog!", "image": "https://images.dog.ceo/breeds/terrier-norfolk/n02094114_1505.jpg"}
```

The client also renders HTML in messages. All the usual HTML elements for images,
links, and text formatting will work. For example, the bot can respond with:

```
{"text": "Lasagna <i>is</i> a <b>sandwich</b>!"}
```

Note that some characters should be escaped using [character
references](https://en.wikipedia.org/wiki/Character_encodings_in_HTML#HTML_character_references)
if you do not wish them to be interpreted as HTML. For example: `{"text": "1 &lt; 2"}` would produce `1 < 2`.

### How do I post (music|sound|video|movies)?

You can embed a sound or video using the `media` key.

```
{"text": "Ring!", "media": "https://upload.wikimedia.org/wikipedia/commons/transcoded/d/de/Back_Rounds.ogg/Back_Rounds.ogg.mp3"}
```

### How do I create a room?
The simplest way to create a room is to add your name onto the end of your group's room such that it has the form:
`https://chat.ncss.cloud/group<group_number>-<your_name>`

For example: `https://chat.ncss.cloud/group4-kenni`

### How do I create a bot?
All bots should consist of 3 main elements:
  * route
  * [input](#how-do-i-send-input-from-necsus-to-my-bot)
  * [output](#what-output-should-i-send-from-my-bot-back-to-necsus)

### How do I link my bot to a room?

Clicking on the **"open settings"** button at the top right hand section of the page, we can see a new side panel open up.
Under the red **reset room** button - press the "add bot" button to create a new blank bot.
From there, fill in the bot name (preferably something unique and not normally used in a sentence).
You can then post the base link for the bot. This is the link to your bot endpoint in Flask (e.g. `<url>/<app route>`.

### How do I send input from NeCSuS to my bot?

Every time a message is sent by a user to a room - NeCSuS scans the message to see if there is a message that matches either an existing `bot name`, or the `Responds to` field for all active bots in the chatroom.
Depending on the contents of the `Responds to` field - the data will be sent to the bot either as plain text or it will have additional `key:value` pairs

#### I want key value pairs!!
Awesome! You can use named capturing groups to do this. For example, [repeat bot](https://repl.it/@kennib/repeat-bot) requires two things from a message:
  * A string to repeat (lets call this `word`)
  * How many times to repeat it (lets call this `count`)

We can then use the following regex string in the `Responds to` field of our NeCSuS bot to get these:

`repeat (?P<word>\w+) (?P<count>\d+) times`

So, if I sent the message `repeat hello 5 times` to a chatroom with repeat bot - NeCSuS would send data in the following way.
```JSON
{
    "room": "shrey",
    "author": "Anonymous",
    "text": "repeat hello 5 times",
    "params": {
                "word": "hello",
                "count": "5"
              }
}
```

>you can get this data by using request.get_json() in your python server :)

### What output should I send from my bot back to NeCSuS

NeCSuS expects two things to be returned as JSON from bot.
So, a basic server that sends the same message every time should look like:

```py3
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/', methods=['POST'])
def home_handler():
  # Create a message to send to NeCSuS
  message = {
    'author': 'Appreciation Bot',
    'text': "Yay! I'm here to tell you that you did a great job!",
  }

  # Return the JSON
  return jsonify(message)

app.run(host='0.0.0.0')
```

So, every time this bot is activated - it will send the same message back: `Yay! I'm here to tell you that you did a great job!"`

### Advanced conversation mode

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

By returning some extra state from your bot, you will switch necsus into a mode where it only talks to that one bot, and forwards all messages to that one bot. So by returning

```JSON
{
  'text': 'Where did you see the cat?',
  'state': ['any', 'non', 'null', {'json': 'object'}]
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
