# NeCSuS

[NeCSuS](https://chat.ncss.cloud) is a chat app which makes it simple to connect "bots" (i.e., simple HTTP servers that reply to messages).
NeCSuS has the ability to host chats in "rooms", listen to voice commands and speak chat messages out loud.


## API

Documentation on the API can be found on [the main NeCSuS server](https://chat.ncss.cloud/docs) or at `/docs` on your local instance.

## Development

Run `python server.py` for the development server. This also inits the db if it
isn't already.

Gunicorn is used for the production server (see the `Procfile`). `python
server.py` must still be run at least once beforehand to init the db.


## FAQ

### What is NeCSuS?
An web app for chat.

### How do I post (images|links|formatted text)?
The client uses [markdown-it](https://markdown-it.github.io) to render the text.
This means you need to use plain text to post any content.
Look at the [demo page](https://markdown-it.github.io) to see examples of the plain text used to post (images|links|formatted text).
